---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-19
revisar_cada: 30d
---

# Fase 2 — Navegación y diseño: desglose de construcción

> **De dónde sale esto.** Los mockups aprobados por el owner el 2026-08-19
> (artefacto «Mockups Reestructura PMO», 20 artboards) son la especificación.
> `reestructura-navegacion.md` es el mapa; este documento es el desglose en USs
> con su dependencia de oleada, para construir una por una.

## Lo que los mockups revelaron

La Fase 2 se planeó como «navegación y diseño». Al leer los 20 artboards
completos, **14 marcan items `· NUEVO`**: no son re-layout, son capacidades que
no existen. Línea base del plan, dependencias entre proyectos, RACI, boards,
importación masiva, completitud de datos, membresía multi-tenant,
costo-snapshot, catálogo de skills de IA, plan de suscripción.

Es decir: los mockups cubren la Fase 2 **y** el contenido de los bloques B2–B10
del plan. Por eso este desglose los separa en tres oleadas por dependencia, en
vez de tratarlo como un solo pase de diseño.

## Oleada 2A — desbloqueada hoy

Nada de esto toca el modelo de datos. Es el pase que hace que las pantallas se
vean como los mockups con lo que ya hay detrás.

| US | Qué | Mockup |
|---|---|---|
| **US-203** | Ancho completo en vistas de datos; `max-w` solo en formularios y detalle de texto | §4.1 + todos |
| **US-204** | Sidebar en tres grupos (ORGANIZACIÓN · TRANSVERSAL · ADMIN); renombres «Documentos → Artefactos» y «Áreas → Recursos» | Main, WArtefactos, WProyectoRecursos |
| **US-205** | Header con switcher de organización; las páginas sueltan su propio select de org | Header |

**Corrección sobre US-206.** Este desglose decía que US-206 «fusiona `/dashboard`
y `/pmo`». Al construirla se vio que el mockup dice lo contrario: su sidebar
lleva **Dashboard** y **Portafolio** como dos items del grupo Organización. Los
mockups son la especificación, así que US-206 se queda en rehacer `/dashboard`
y `/pmo` sigue siendo la vista de portafolio. Lo que sí absorbe parte de `/pmo`
es US-207, cuando la vista maestra reemplace sus tablas.

**Nota sobre US-205.** El mockup del header lleva **dos** switchers. El de
organización se puede hacer hoy: las orgs asignadas salen de
`UserScopeAssignment`. El de **tenant** necesita membresía multi-tenant (W2), que
no existe — hoy el inquilino se fija al iniciar sesión. US-205 entrega el de
organización y deja el de tenant declarado como US-214.

## Oleada 2B — vistas nuevas sobre datos que ya existen

| US | Qué | Qué le falta y de dónde sale |
|---|---|---|
| **US-206** | Dashboard ejecutivo: `/dashboard` en las 4 filas del mockup | Tendencias: hoy los snapshots son **semanales**, el mockup pide bi-semanales (US-213). Sale con los semanales y se cambia la cadencia después |
| **US-207** | Vista maestra (control tower): tabla de ancho completo, header y primera columna fijos, columnas configurables, export XLSX | 3 de sus 16 columnas no existen: «Próximo hito», «Reporte» y «Completitud» (US-210, US-211). Sale con 13 |
| **US-208** | Recursos con dos pestañas: Catálogo y Capacidad (heatmap persona×semana) | El heatmap se apoya en `/capacity/resource-load`, que existe. Costo por recurso es W4 (US-215) |
| **US-209** | Reportes a nivel organización y portafolio | El nivel portafolio es nuevo; los otros tres existen |

## Oleada 2C — necesitan modelo de datos nuevo

La mayoría lleva su migración y, cuando toca contrato, su ADR. Ordenadas por lo
que desbloquean.

**Corrección sobre US-210 y US-211.** Ninguna lleva migración. La completitud se
**deriva** de campos que ya existen —un porcentaje guardado se queda viejo el día
que alguien edita el proyecto por un camino que se olvidó de recalcularlo—, y los
hitos ya viven en `tasks.is_milestone` con la cadencia de reporte como ajuste del
inquilino. La suposición de que las doce necesitaban esquema nuevo era del
desglose, no del mockup: conviene comprobarla US por US antes de escribir una
migración.

| US | Qué | Desbloquea |
|---|---|---|
| **US-210** ✅ | Completitud de datos por proyecto (campos mínimos + checklist de onboarding). **Derivada, sin migración** | Columna del control tower · WProyectoResumen · WImportacion |
| **US-211** ✅ | Próximo hito y estatus de reporte como datos consultables. **Sin migración**: los hitos ya son `tasks.is_milestone` y la cadencia es un ajuste del inquilino | Dos columnas del control tower · Portfolio Board |
| **US-212** | Línea base del plan (D-6) + comparación plan/base/real | WPlan · «desviación» deja de no tener referente |
| **US-213** ✅ | Tendencia por corte + historial de cortes. **Sin migración**: se muestrea al leer, no al capturar — bajar la frecuencia del job sería irreversible | Tendencias del dashboard · WReportesOrg · boards |
| **US-214** | Membresía multi-tenant + switcher de tenant (W2) | Header completo · WAdminUsuarios |
| **US-215** | Costo-snapshot en participaciones (W4) | WProyectoRecursos · costo en el catálogo |
| **US-216** | Importación masiva: proyectos, planes y recursos (B5) | WImportacion — la carga inicial sin captura manual |
| **US-217** | RACI y stakeholders clave del proyecto | WProyectoRecursos |
| **US-218** | Dependencias entre proyectos en el Gantt | WPlan |
| **US-219** | Boards: project (kanban) y portfolio (por estatus de reporte) | WBoards |
| **US-220** | Catálogo de IA (skills · tools · prompts · workflows) + roles de agente | WAdminIA |
| **US-221** | Plan de suscripción: tier, límites y consumo (solo lectura) | WAdminPlan |

## Lo que estos mockups **no** cambian

`WNotifCuenta` lo dice explícitamente («sin cambios funcionales») y
`WArtefactos` es «solo renombre + consolidación». `WProyectos`,
`WSolicitudes` y `WCross` describen lo que W1 ya dejó, más el pase de ancho.
No generan US propia: entran en US-203 y US-204.

## Orden de construcción

2A completa primero, porque toca todas las pantallas y hacerlo después de
añadir vistas nuevas significaría tocarlas dos veces. Luego 2B, que es donde
está el valor visible. 2C se ataca por lo que más desbloquea: US-210 y US-211
completan el control tower, US-213 completa el dashboard.

Una US = un commit = un issue, como siempre. Los issues de cada oleada se crean
al arrancarla, no todos de golpe: un issue abierto seis semanas antes de tocarse
es un issue que hay que releer.
