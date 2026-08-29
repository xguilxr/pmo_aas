---
tipo: epica
responsable: propietario
estado: borrador
revisado: 2026-08-29
revisar_cada: 30d
---

# Reestructura de plataforma — Mapa de conceptos

> Resultado de la sesión de planeación 2026-08-18 con el owner. Define el
> árbol de conceptos, módulos e información que el sistema debe recopilar y
> mantener en la v2 de la plataforma. Complementado (no redefinido) con el
> feedback de un cliente prospecto que arranca con 23 proyectos de portafolio
> (§ Anexo). El plan de ejecución vivía en `reestructura-plan.md`, ahora
> recortado a lo que queda por construir.

> **Estado real (2026-08-29):** el árbol de conceptos —jerarquía, módulos,
> vocabulario— ya es la plataforma (ADR-037/038, `EP002-org-hierarchy.md` y
> las epics de módulo). Dos piezas que este documento da por construidas
> **todavía no lo están**: el **RLS en Postgres** que la §1 (Tenant) describe
> como «existente» sigue sin implementarse (issues #599-#601), y el claim de
> sesión `active_organization_id` no se construyó — el contexto de
> organización activa vive del lado del cliente, no en el JWT. La sección de
> IA (§1.3) describe roles de agente con permisos propios; el owner decidió
> lo contrario después (DEC-033, EP021): el agente actúa siempre en nombre
> de una persona. El resto —incluida la jerarquía y el árbol de módulos— es
> una descripción razonablemente fiel de lo que hay hoy.

## Definiciones

- **Concepto**: lo grande que encapsula casi todo (Tenant, Organización,
  Proyecto…).
- **Módulo**: componente de sistema con funcionalidades (Plan, RAID,
  Minutas…).
- **Información**: atributos que se recopilan y mantienen de cada concepto o
  módulo.

## Árbol de conceptos

```
Tenant
├── Organizaciones (1:N)
│   ├── Proyectos (1:N)
│   │   ├── Agrupadores: Portafolio ⊃ Programa (anidados)
│   │   ├── Módulos (proyecto aprobado): Plan · RAID · Recursos asignados ·
│   │   │   Artefactos · Minutas · Reportes · Cambios · Lecciones
│   │   └── Solicitudes → Project Charter → Proyecto
│   └── Recursos (catálogo por organización, asignables a N proyectos)
├── Usuarios → Roles → Permisos (globales entre tenants)
├── AI (skills/tools/prompts/workflows · modelo BYOK · roles de agente)
└── Plan (suscripción)
```

---

## 1. Tenant

Instancia lógica de la plataforma. **Decisión: shared-DB + RLS, no
aislamiento físico** (DB/schema por tenant). Razones: (a) usuario puede
pertenecer a 2+ tenants y hacer shift, trivial con membresía M:N e inviable
limpio con DBs separadas; (b) consistente con DEC-003/ADR-024 y el RLS
existente; (c) costo operativo de N bases no se justifica sin driver de
compliance. Se formaliza:

- `tenant_id` en toda tabla tenant-scoped con **RLS en Postgres** (no solo
  filtro de ORM).
- Usuario = entidad global; pertenencia vía `user_tenant_membership` (M:N,
  rol por tenant).
- JWT/sesión lleva `active_tenant_id` + `active_organization_id`; el shift
  de organización o tenant re-emite contexto sin re-login.

**Información**: identificador, nombre, slug/subdominio, estado (trial,
activo, suspendido, cancelado), fecha de alta/renovación, datos de
facturación (futuro), branding default del tenant, contacto owner, plan
(§1.4).

## 1.1 Organización

Unidad de negocio real. Punto donde viven el catálogo de Recursos y los
agrupadores.

**Información**: nombre, identificador, estado (activa/archivada), branding
propio (override del tenant; aplica a reportes y archivos generados desde la
org), moneda, zona horaria, calendario laboral, fecha de creación,
owner/admin.

**Reglas**: los límites del Plan (máx. orgs, máx. proyectos) se cuentan **por
tenant sumando todas las orgs**.

## 1.1.1 Proyecto

Unidad central de trabajo.

**Información**: nombre, código, descripción, estado/fase, portafolio
(nullable), programa (nullable), sponsor, PM asignado, organización/área,
tipo (transformación, operación, innovación, BAU), prioridad, fechas inicio/
fin plan y real, presupuesto plan/comprometido/consumido, salud (calculada y
declarada, §M-Reportes), referencia a la Solicitud origen, tamaño
(grande/pequeño — determina plantilla), flag «incluido en portafolio
inicial» (onboarding masivo), completitud de datos (%), última
actualización, próximo hito, estatus de reporte.

**Fases**: `Solicitud (borrador → revisión → aprobada/rechazada)` →
`Aprobado: Preparación (fase 1)` → fases de ejecución (a detallar con el
módulo Plan) → cierre.

**Reglas**:
- Puede tener Portafolio y Programa a la vez; si tiene Programa, su
  Portafolio debe ser el del Programa (consistencia del anidado).
- Dos vías de creación: (a) Solicitud → aprobación → Proyecto; (b) botón
  «Crear proyecto» que captura los campos del charter y entra directo a
  Preparación.

### 1.1.1.1 Portafolio (agrupador)

**Información**: nombre, código, descripción, owner, estado, métricas
agregadas (derivadas, no capturadas): conteo de proyectos, salud agregada,
presupuesto agregado.

### 1.1.1.2 Programa (agrupador)

Pertenece a un Portafolio (anidado). **Información**: los mismos campos que
Portafolio + `portfolio_id` (obligatorio).

### 1.1.1.3 Módulos de un proyecto aprobado

| Módulo | Función | Información |
|---|---|---|
| **Plan** | Cronograma/WBS | Tareas, fechas, dependencias, hitos (con flag «hito clave»/«crítico»), % avance, línea base (baseline vs real), atrasos por tarea/hito, importación Excel/MS Project/CSV, dependencias entre proyectos |
| **RAID** | Riesgos, Acciones, Issues, Decisiones | Tipo, descripción, severidad (prob×impacto), owner (obligatorio para gobernar), fecha compromiso, estado, escalamiento requerido, sponsor decisor; impacta salud automáticamente |
| **Recursos asignados** | Áreas/Equipos del proyecto | Área/equipo, recurso, rol en el proyecto, % dedicación / FTE asignado, periodo de asignación, costo snapshot (§1.1.2), RACI, stakeholders clave |
| **Artefactos** (ex-Documentos) | Exports consolidados | Tipo (Charter, Plan, RAIDs, Organigrama — el organigrama **se deriva** de Recursos asignados, no se captura), versión, fecha de generación, origen, formato |
| **Minutas** | Actas de reunión | Fecha, asistentes, agenda, acuerdos; **generan entradas RAID automáticamente** |
| **Reportes** | Informes de estado | Tipo/plantilla, periodo, snapshot bi-semanal, comentario ejecutivo del PM, cambios desde el último reporte, salud (historial), generado IA/manual, export PPT/PDF/Excel |
| **Cambios** | Gestión de cambios | Descripción, impacto (alcance/tiempo/costo), estado de aprobación, aprobador. **Siempre manuales** — sin auto-generación, por gobierno |
| **Lecciones** | Lecciones aprendidas | Categoría, descripción, contexto, recomendación, fecha. Candidato: generación periódica por IA (evaluar) |

**Salud del proyecto** (transversal a Plan/RAID/Reportes): fórmula visible,
pesos por dimensión configurables (cronograma, presupuesto, riesgos,
recursos, alcance), salud calculada vs declarada por el PM con motivo
obligatorio al divergir, historial de cambios, alertas automáticas (atraso,
riesgo severo, falta de actualización, sobrecarga de recursos).

### 1.1.1.4 Solicitud

Punto de entrada; contiene el Project Charter.

**Información**: solicitante, fecha, justificación/objetivo de negocio,
campos del charter (alcance, sponsor, presupuesto estimado, fechas
estimadas), estado, aprobadores, fecha de decisión, comentarios.

## 1.1.2 Recursos (catálogo de organización)

Un recurso es único por organización, asignable a N proyectos. Las personas
con acceso a la plataforma (Usuarios) deben existir como Recurso en una
organización para ser asignables.

**Información**: nombre, tipo de recurso (negocio, IT, PMO, proveedor), rol,
puesto, área funcional, equipo, empresa, responsable funcional, skills/
especialidad, **capacidad disponible** (mensual/semanal, FTE), costo/tarifa
base, vínculo a Usuario (nullable), estado.

**Reglas**: capacidad y costo se definen a nivel Recurso; el costo de cada
asignación se calcula con snapshot del costo vigente al momento de asignar
(no se recalcula si el costo base cambia). FTE asignado por proyecto y
periodo viven en la asignación → de ahí se derivan sobrecarga/
subutilización, heatmaps y capacity planning (§ Anexo).

## 1.2 Usuarios

Cuentas de acceso; ven solo las organizaciones/proyectos asignados
(visibilidad por asignación, PMs típicamente).

**Información**: nombre, email, auth, estado, membresías de tenant (M:N con
rol por tenant), organizaciones/proyectos asignados (scope), recurso
vinculado, último acceso, fecha de alta.

### 1.2.1 Roles → Permisos

**Roles globales entre tenants** (catálogo único de plataforma; custom por
tenant se revisa después). Rol: nombre, descripción, permisos. Permiso:
identificador, módulo que controla, acción (ver/crear/editar/eliminar/
aprobar), scope (tenant/organización/proyecto).

## 1.3 AI

### 1.3.1 Skills / tools / prompts / workflows

**Información**: nombre, tipo, descripción, scope (plataforma/tenant/org),
definición (prompt, tool schema, workflow steps), estado, versión.

### 1.3.2 Modelo (BYOK) + roles de agente

Selector estilo pi: provider, modelo, agentes/subagentes.

**Información**: provider, modelo, API key del tenant (cifrada), límites de
consumo/alertas, defaults con override por org/proyecto.

**Roles de agente**: catálogo **totalmente separado** de 1.2.1 —
personalidades funcionales del asistente (redactor de minutas, analista de
riesgos…), con **su propio esquema de permisos de plataforma** (qué puede
leer/escribir cada agente), paralelo al RBAC de usuarios, no reutilizándolo.

## 1.4 Plan (suscripción)

Se modela el esquema desde ahora, sin paywall ni tiers definitivos.

**Información**: nombre/tier, límites (máx. organizaciones, máx. proyectos
**sumados por tenant**, máx. usuarios, consumo de IA), precio (futuro),
vigencia, estado. Free tier: 1 org, 3 proyectos.

## Capas transversales (consumidores, no conceptos)

- **Dashboard ejecutivo**: a nivel organización, con filtros de portafolio y
  programa. Detalle en Anexo §A2.
- **Vista maestra de portafolio** (control tower): Anexo §A1.
- **Reporte de asignación de recursos** a nivel organización
  (portafolio/programa/proyecto) + capacity planning: Anexo §A3.
- **Reportes**: refinar existentes + generación especializada con IA.

---

## Anexo — Feedback cliente prospecto (23 proyectos, 2026-08-18)

Complementa la definición del owner; no la redefine. Diagnóstico: la base
PMO es buena pero opera «proyecto por proyecto»; faltan la capa ejecutiva de
portafolio y capacity planning real. Los atributos que pedía ya quedaron
absorbidos arriba (tipo de proyecto, FTE/capacidad, snapshot bi-semanal,
salud explicable, etc.); aquí queda lo que es **vista/funcionalidad**:

### A1. Vista maestra de portafolio (control tower)

Pantalla central con columnas ejecutivas por proyecto: organización/área,
sponsor, PM, programa, tipo, fase, prioridad, salud, avance plan vs real,
presupuesto plan vs real, fechas, riesgos severos, issues abiertos, recursos
críticos, próximo hito, última actualización, estatus de reporte. Todos esos
campos ya existen en §1.1.1 — la vista es agregación, no captura nueva.

### A2. Dashboard ejecutivo de portafolio

Responde en 30 s «¿qué proyectos requieren atención ejecutiva esta
semana?»: proyectos por salud/fase/organización/sponsor, top en riesgo/
atraso/sobrecarga, presupuesto total-comprometido-consumido-restante,
roadmap general, semáforo consolidado por dimensión, tendencias
bi-semanales (requiere snapshots).

### A3. Capacity planning

Sobre §1.1.2: heatmap persona×semanas y área×semanas, demanda por proyecto,
capacidad disponible vs demandada, sobreasignados, recursos críticos
compartidos, escenarios what-if (P2).

### A4. Onboarding masivo

Importación Excel/CSV de proyectos, planes y recursos; validación de datos
mínimos; estado de completitud; checklist de onboarding; plantilla
simplificada según tamaño de proyecto.

### A5. Gantt/roadmap consolidado

Gantt de todos los proyectos, roadmap por programa/organización/sponsor,
vista de milestones ejecutivos (próximas 2/4/8/12 semanas), baseline vs
actual, dependencias entre proyectos.

### A6. Cadencia bi-semanal

Snapshot bi-semanal por proyecto y de portafolio (base de las tendencias),
Project Board por proyecto y Portfolio Board para la PMO.

### A7. Completitud de datos

Métricas de calidad: proyecto sin sponsor/PM/plan/recursos/presupuesto/
fecha de próximo reporte/salud actualizada; RAID sin responsable o sin
fecha; tareas vencidas sin acción. El dashboard no es confiable sin esto.

### Prioridad sugerida por el cliente

- **P0**: vista maestra, capacity planning básico, dashboard ejecutivo,
  snapshot bi-semanal, importación masiva.
- **P1**: Gantt consolidado, heatmap de capacidad, project boards,
  RACI/stakeholders/organigrama, alertas automáticas.
- **P2**: what-if, priorización avanzada, forecast, automatización de
  reportes ejecutivos.
