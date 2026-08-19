---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-08-19
revisar_cada: 30d
---

# Reestructura — Fase 2: Navegación y diseño

> Mapa de navegación objetivo y especificación de las vistas nuevas/
> reestructuradas. Insumo para wireframes/mockups que el owner aprueba antes
> de tocar frontend (Fase 2 del plan). Principios: simplificar vistas,
> aprovechar el ancho horizontal, pulir el diseño sobre los tokens vivos de
> `globals.css`.

## 1. Contexto activo (header)

El cambio estructural de navegación: el **contexto deja de estar disperso**
(tenant fijado al login, org como select ad-hoc por página, árbol duplicado
en sidebar) y se concentra en el header:

```
[Logo] [⌄ Tenant] [⌄ Organización]        [búsqueda] [🔔] [usuario]
```

- **Switcher de tenant**: visible solo si el usuario tiene >1 membresía.
  Cambiar re-emite JWT (`switch-context`) y recarga el shell.
- **Switcher de organización**: lista las orgs asignadas del tenant activo;
  opción «Todas» solo para vistas que agregan (dashboard ejecutivo). Todo lo
  demás opera dentro de la org activa.
- Consecuencia: las páginas cross dejan de cargar su propio select de org;
  los filtros de página quedan solo para **portafolio/programa** y filtros
  propios de la vista.

## 2. Sidebar objetivo

La navegación baja de "todo al mismo nivel" a tres grupos estables. El árbol
`OrgTreeNav` desaparece del sidebar (la org vive en el header; el drill
portafolio→programa se hace con filtros dentro de las vistas):

```
ORGANIZACIÓN (org activa)
  ⌂ Dashboard              ← ejecutivo, nivel org, filtros portafolio/programa
  ▦ Portafolio             ← vista maestra (control tower)
  ▤ Proyectos              ← lista operativa + alta directa
  ▥ Solicitudes
  ⚒ Recursos               ← catálogo + capacity planning
  ▧ Reportes               ← nivel org/portafolio + programados
TRANSVERSAL
  ☰ RAID · Cambios · Minutas (vistas cross, filtros P/P)
  🔔 Notificaciones
ADMIN (según permisos)
  Usuarios · Roles · Organizaciones · IA · Plan · Auditoría
SUPERADMIN (igual que hoy)
```

Dentro de un proyecto, la navegación actual por tabs se conserva
(`project-tabs-bar`): Resumen · Charter · Plan · RAID · Recursos (ex-Áreas) ·
Artefactos (ex-Documentos) · Minutas · Reportes · Cambios · Lecciones ·
IA-contexto.

## 3. Vistas nuevas / reestructuradas

### 3.1 Dashboard ejecutivo (reemplaza `/dashboard` + `/pmo`)

Una sola vista a nivel organización (o «Todas»), pregunta que responde en
30 s: *¿qué proyectos requieren atención ejecutiva esta semana?*

- **Fila 1 — KPIs**: proyectos activos, salud (V/A/R), avance promedio
  plan-vs-real, presupuesto total/comprometido/consumido/restante,
  riesgos severos abiertos, recursos sobreasignados.
- **Fila 2 — Atención**: top proyectos en riesgo · top atrasados · top con
  sobrecarga de recursos (listas accionables, click → proyecto).
- **Fila 3 — Distribuciones**: por salud, por fase, por portafolio/programa,
  por sponsor (componentes `Pie`/`Bars` existentes).
- **Fila 4 — Tendencias**: series bi-semanales desde snapshots
  (`TrendLines`), semáforo consolidado por dimensión (cronograma,
  presupuesto, riesgos, recursos, alcance).
- Filtros de página: Portafolio → Programa (cascada). Export PDF status
  (existente) + PPT (nuevo, backend).
- Ancho completo: sin `max-w-7xl`.

### 3.2 Vista maestra de portafolio — control tower (nueva, evoluciona `/pmo/projects`)

Tabla de ancho completo, sticky header + primera columna, columnas
configurables (mostrar/ocultar, orden persistido por usuario), edición
inline donde ya existe (salud declarada, prioridad):

Columnas: Proyecto · Organización/área · Sponsor · PM · Portafolio ·
Programa · Tipo · Fase · Prioridad · Salud · Avance plan/real · Presupuesto
plan/real · Inicio · Fin · Riesgos severos · Issues abiertos · Recursos
críticos · Próximo hito · Última actualización · Estatus de reporte ·
Completitud.

- Filtros: portafolio/programa/fase/salud/tipo/PM + búsqueda.
- Densidad compacta por default; export XLSX directo.
- Con >20 columnas y cientos de filas: virtualización o paginación server
  (decidir en implementación; hoy no hay tabla virtualizada).

### 3.3 Recursos y capacity (evoluciona `/pmo/resources` + `/admin/areas`)

Dos pestañas bajo «Recursos» de la org activa:

- **Catálogo**: personas/recursos de la organización (tipo, rol, área,
  equipo, empresa, skills, capacidad FTE, costo, vínculo a usuario).
  Absorbe el admin de áreas/equipos como sub-sección.
- **Capacidad**: heatmap persona×semanas y área×semanas (componente
  `Heatmap` existente), capacidad vs demanda, sobreasignados, recursos
  críticos compartidos entre proyectos, ventanas Hoy/Semana/Mes/Trimestre.
  What-if queda P2.

### 3.4 Boards (P1)

- **Project Board**: kanban del proyecto (base `raid-kanban`) con carriles
  configurables y el snapshot bi-semanal como corte.
- **Portfolio Board**: cadencia PMO — proyectos como tarjetas por estado de
  reporte (al día / vencido / con decisiones pendientes).

### 3.5 Admin reorganizado

- **Organizaciones**: CRUD + jerarquía Portafolio⊃Programa (US-200) +
  branding por org.
- **Usuarios**: membresías, scope de visibilidad, vínculo a recurso.
- **IA**: provider BYOK + catálogo skills/prompts + roles de agente.
- **Plan**: tier y consumo de límites (solo lectura hasta que haya billing).

## 4. Principios de diseño (pulido)

1. **Ancho completo por default** en vistas de tabla/heatmap/gantt; `max-w`
   solo en formularios y detalle de texto.
2. **Densidad**: las vistas ejecutivas priorizan filas visibles (compacto);
   el detalle de proyecto respira como hoy.
3. **Tokens vivos** (`globals.css` + `paleta.py`) como única fuente; el
   pulido es consistencia (espaciado, jerarquía tipográfica, estados vacíos)
   — no una paleta nueva. Reescribir `design-system/tokens.md` contra lo
   vigente forma parte de esta fase (ya anotado en SPRINT).
4. **Semáforos con porqué**: todo indicador de salud enlaza a su desglose
   (`HealthWhyPanel`) — nada decorativo.
5. **Estados estándar** (vacío/cargando/error/sin-permiso) en toda vista
   nueva, componentes `ui/` existentes.

## 5. Ruta de aprobación

1. Owner revisa este mapa (secciones 1–3) y marca ajustes.
2. Mockups de las 4 vistas clave (dashboard ejecutivo, control tower,
   capacidad, header con switchers) para aprobación visual.
3. Aprobado → los bloques B3/B8 del plan se convierten en issues con
   `triage`, cada pantalla amarrada a su mockup.

## 6. Dependencias con el modelo de datos

| Vista | Necesita de W1–W5 |
|---|---|
| Header switchers | W2 (membresía + claim org activa) |
| Dashboard ejecutivo | W1 (portafolios) + W5 (snapshots bi-semanales para tendencias) |
| Control tower | W1; columnas de reporte/completitud maduran con W5 |
| Capacity | W4 (org obligatoria en actors, costo-snapshot) |
| Boards | W5 |

El header y el dashboard con filtros portafolio/programa pueden empezar en
cuanto W1–W2 estén en main; nada de la Fase 2 bloquea a la Fase 1.
