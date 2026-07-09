# EP017 — Directorio de Proyecto (áreas funcionales, equipos operativos, roles, participaciones)

| Campo | Valor |
|---|---|
| **ID** | EP017 |
| **Prioridad** | Alta — Sprint 25 |
| **Dependencias** | EP002 (org hierarchy), EP005 (projects), EP006 (project modules), US-097/098/103 (áreas catálogo) |
| **Módulo** | `areas`, `actors`, `teams`, `project_participations` |
| **Estado** | # PENDING |
| **Versión objetivo** | v1.24 |
| **Issue origen** | Feedback owner 2026-05-10 (rediseño de modelo de áreas/recursos) |

## Objetivo de negocio

Reemplazar la jerarquía actual `Area → Team → Actor` (que mezcla 3 dimensiones) por un modelo que separa explícitamente las 4 dimensiones del feedback:

| Dimensión | Hoy | Nuevo |
|---|---|---|
| Área funcional | `actors.area_id` (mezclado con jerarquía) | Atributo **estable** de la persona (1 FK) |
| Equipo operativo | `actors.team_id` + `teams.area_id` | Atributo **por proyecto** (Testing, Deployment, Diseño) |
| Rol proyecto | implícito en `project_members.role_in_project` | Catálogo editable `project_roles` (PM, SME, Key User…) |
| Participación temporal | inexistente | `start_date` / `end_date` en participation |

El sistema gana 4 ejes de reporte: por persona, por área funcional, por equipo operativo, por rol.

## Modelo conceptual

```
actors (catálogo tenant — personas)
  ├─ functional_area_id  → areas       (1:1 estable)
  ├─ manager_actor_id    → actors      (autoref)
  ├─ user_id             → users       (opc.)
  └─ company, job_title

areas (catálogo tenant plano — áreas funcionales)
teams (catálogo tenant plano — equipos operativos; SIN area_id)
project_roles (catálogo tenant — PM, SME, Key User…)

project_participations (N por (project_id, actor_id))
  ├─ project_id          → projects
  ├─ actor_id            → actors
  ├─ operational_team_id → teams         (opc.)
  ├─ project_role_id     → project_roles (opc.)
  ├─ is_area_lead        bool   (líder del área DENTRO del proyecto)
  ├─ is_primary          bool   (UNIQUE por (project_id, actor_id) cuando true)
  ├─ start_date, end_date date
  └─ is_active           bool
```

## DEC a registrar en DECISIONS.md al cierre del bloque

- **DEC-XXX** — Área funcional vive en la persona (1 FK). Equipo operativo y rol viven en `project_participations`, una persona puede tener N participations en un proyecto (varios equipos/roles); una se marca `is_primary` para agrupadores.
- **DEC-XXX** — Catálogo de equipos operativos (`teams`) queda **plano** (drop `teams.area_id`). Catálogo de roles de proyecto pasa a tabla editable `project_roles`.
- **DEC-XXX** — Plan/RAID/Cambios usan **solo `*_actor_id`** como responsable. Drop de `tasks.area_id`, `risks.area_id`, `issues.area_id` (snapshot a `legacy_area_id` por rollback). Filtros y agrupadores derivan área/equipo/rol via join.
- **DEC-XXX** — `project_members` legacy se mantiene en MVP; consolidación con `project_participations` queda como Bloque E post-MVP (ENH separado por blast radius en RBAC).

## Bloques

- **Bloque A — Schema (US-114).** Migración Alembic 0061: nuevas tablas, drops, backfill desde `actors.team_id`, `tasks/risks/issues.area_id`, `actors.is_lead`, `project_members`.
- **Bloque B — API (US-115).** Endpoints de participations + project_roles; refactor `/actors`, `/teams`, `/areas`. Responses de tasks/risks/issues incluyen dimensiones derivadas.
- **Bloque C — UI (US-116).** Rediseño `/pmo/projects/[id]/areas` con dos toggles (directorio del proyecto + 4 sub-tabs de catálogos); rediseño de `/admin/areas`. **Actualizado 2026-06-29 (ENH-183):** el panel "Áreas y Equipos" lista solo áreas asignadas al proyecto (no catálogo completo); modal de área nueva permite crear nueva o traer existente del catálogo.
- **Bloque D — Asignación (US-117).** Dropdowns filtrados por participations en plan/RAID/cambios/lecciones/minutas. Botón "+ agregar al proyecto". **Actualizado 2026-06-29 (BUG-086):** servicio `area_visibility` como fuente única de cascada de visibilidad; actores con `area_id` directo son asignables (antes heurística los excluía si no tenían team/user/is_lead).
- **Bloque E — Consolidación legacy (US-118, post-MVP).** Migrar permisos RBAC de `project_members` a `project_participations` y dropear tabla legacy.
- **Bloque F — Pool de recursos y capacidad (US-182/183/184, 2026-07-09, Revamp 1.0).** El `Actor` se extiende como el resource pool del tenant (clasificación + capacidad) y `project_participations` gana FTE% + ciclo de vida de asignación; motor de saturación + alertas in-app. Ver sección dedicada abajo.

## Convergencia con sprint 13

US-097 (#240 áreas jerarquía), US-098 (#241 plan area), US-103 (#263 áreas catálogo compartido) tocan el mismo dominio. Al arrancar EP017 hay que decidir si las absorbe US-116 o conviven; recomendado revisar al iniciar Bloque C.

---

## # PENDING — US-114 — Schema directorio de proyecto

**Como** sistema PMO
**Quiero** un schema que separe área funcional / equipo operativo / rol proyecto / participación temporal
**Para** habilitar reportes y filtros multi-dimensión sobre los recursos.

**Alcance schema:**
- Crear `project_participations` (con `is_primary` UNIQUE parcial por `(project_id, actor_id) WHERE is_primary`).
- Crear `project_roles` (id, tenant_id, name, description, is_active).
- `actors`: agregar `company`, `job_title`, `manager_actor_id`; drop `team_id`, `is_lead`.
- `teams`: drop `area_id`.
- `tasks`, `risks`, `issues`: drop `area_id` con snapshot a `legacy_area_id`.
- Backfill: cada `actor.team_id` activo → genera participation por proyecto donde el actor tiene tareas/RAID. `project_member` → genera participation con `project_role_id` resuelto contra `project_roles`. `actor.is_lead=true` → `is_area_lead=true` en participations correspondientes. `actor.user_id` se crea si no existe vinculación.

**Criterios de aceptación:**
- [ ] Migración Alembic `0061_project_directory.py` upgrade + downgrade ambos verdes.
- [ ] Backfill no pierde asignaciones de tareas/RAID existentes.
- [ ] Tests: smoke contra cada drop (`tasks.area_id` no existe, `tasks.legacy_area_id` sí).
- [ ] Tests: backfill genera al menos 1 participation por (proyecto, actor con tareas).
- [ ] DECISIONS.md actualizado con los 4 DEC del epic.
- [ ] DB-CHANGES.md actualizado.

**Test Cases:**
- TC-114-1: migración upgrade limpia + downgrade.
- TC-114-2: backfill con actor con team_id en 2 proyectos genera 2 participations.
- TC-114-3: actor con `is_lead=true` y `area_id` poblada → todas sus participations tienen `is_area_lead=true`.
- TC-114-4: drop `tasks.area_id` no rompe queries existentes (acceso a tareas).
- TC-114-5: `project_member` con `role_in_project='pm'` → participation con `project_role_id` apuntando a "PM" en `project_roles`.

---

## # PENDING — US-115 — API directorio de proyecto

**Como** frontend
**Quiero** endpoints REST de participations + project_roles + actors enriquecidos
**Para** consumir el directorio del proyecto y los catálogos del Toggle 2.

**Endpoints nuevos:**
- `GET/POST/PATCH/DELETE /projects/{id}/participations` (+ `?include=actor,area,team,role`).
- `GET/POST/PATCH/DELETE /project-roles`.
- `POST /areas` — nuevo: acepta `project_id` o `program_id` (además de `organization_id`). Cuando se crea un área desde un proyecto, backend deriva `organization_id` y crea automáticamente `AreaAssignment` del scope correcto (proyecto → queda en ese proyecto; programa → se propaga a sus proyectos; organización → cascada de lectura). **Agregado 2026-06-29 (BUG-085).**

**Endpoints refactor:**
- `/actors`: nuevos campos `company`, `job_title`, `manager_actor_id`; quita `team_id`, `is_lead` del payload.
- `/teams`: catálogo plano (sin `area_id`); CRUD plano.
- `/areas`: sigue igual; respuesta sin tree anidado de teams.
- Tasks/risks/issues responses: agregar bloque `derived = { functional_area, operational_team, project_role, is_area_lead }` calculado vía join con primary participation.

**Criterios de aceptación:**
- [ ] OpenAPI actualizada y publicada.
- [ ] Tests por endpoint con factories.
- [ ] Performance: `GET /projects/{id}/participations` < 200ms con 100 participations.
- [ ] Endpoint `/actors` legacy con `team_id` → 422 con mensaje claro de migración.

**Test Cases:**
- TC-115-1: CRUD participation completo.
- TC-115-2: marcar `is_primary=true` desmarca la primary anterior del mismo (project, actor).
- TC-115-3: GET task incluye `derived.functional_area` correcto.
- TC-115-4: borrar actor → cascada o restrict (definir en US-114).
- TC-115-5: project_role en uso no se puede borrar (restrict).

---

## # PENDING — US-116 — UI rediseño /pmo/projects/[id]/areas + /admin/areas

**Como** PM
**Quiero** una página de Áreas con dos toggles (directorio del proyecto + catálogos)
**Para** gestionar personas, áreas, equipos, roles y participaciones desde un solo lugar.

**Toggle 1 — Directorio del proyecto (default):**
Tabla de actores participando: nombre, área funcional, equipo operativo (primary), rol proyecto (primary), líder área, ventana temporal, contacto. Acciones: + agregar persona del catálogo tenant, + crear nueva persona inline, editar participations (modal con N filas), desactivar. **Actualizado 2026-06-29 (ENH-183):** lista solo áreas asignadas al proyecto (y equipos cuya área está asignada), no catálogo completo.

**Toggle 2 — Catálogos (4 sub-tabs):**
- Áreas funcionales (CRUD `areas` — nueva: modal de creación permite crear nueva o traer existente del catálogo; al traer, se asigna al proyecto vía `AreaAssignment`). **Actualizado 2026-06-29 (ENH-183).**
- Equipos operativos (CRUD `teams` plano)
- Roles de proyecto (CRUD `project_roles`)
- Participaciones (vista plana auditoría + reasignación masiva)

**`/admin/areas` rediseño:** mismos 4 sub-tabs + tab "Personas globales del tenant" (catálogo de actores).

**Criterios de aceptación:**
- [ ] Página `/pmo/projects/[id]/areas` con toggles funcional.
- [ ] Página `/admin/areas` rediseñada (5 sub-tabs).
- [ ] Modal "agregar persona" permite (a) seleccionar del catálogo tenant, (b) crear nueva inline con campos básicos.
- [ ] Modal "nueva área" permite (a) crear nueva, (b) traer existente del catálogo (asigna al proyecto). **Actualizado 2026-06-29 (ENH-183).**
- [ ] Modal de participation soporta múltiples filas por persona; flag `is_primary` resaltado.
- [ ] Convergencia evaluada con US-097, US-098, US-103 (decidir absorción o coexistencia).

**Test Cases:**
- TC-116-1: Toggle 1 lista correctamente actores con primary participation.
- TC-116-2: Crear persona inline + asignar a proyecto en 1 flow.
- TC-116-3: CRUD de project_role desde Toggle 2 sub-tab "Roles".
- TC-116-4: Reasignación masiva en sub-tab "Participaciones".
- TC-116-5: `/admin/areas` Toggle "Personas globales" muestra todos los actores del tenant.

---

## # PENDING — US-117 — Dropdowns filtrados por participation en plan/RAID/cambios/lecciones/minutas

**Como** usuario que asigna responsables
**Quiero** que los dropdowns de "responsable" listen solo personas habilitadas en este proyecto
**Para** no asignar a alguien fuera del directorio del proyecto.

**Aplica a:**
- Plan: `tasks.assignee_actor_id` (única FK; sin área).
- Risks: `risks.owner_actor_id`.
- Issues: `issues.owner_actor_id`.
- Change approvers: `change_approvers.actor_id`.
- Risk action assignees: `risk_action_assignees.actor_id`.
- Lessons: agregar `lessons.owner_actor_id` (nuevo).
- Meeting minutes participants: actores del proyecto.

**Filtros y agrupadores en Plan (ENH-077 — composición chips × agrupador × nivel):**
- Por persona, área funcional, equipo operativo, rol proyecto, líder área, sin asignar.
- Todo derivado vía join con `actors` + `project_participations` (filtro por `is_primary` para grupo único, opción "expandir todos los roles" para mostrar tarea en N grupos).

**Criterios de aceptación:**
- [ ] Cada dropdown afectado lista solo personas con participation activa (`is_active=true`, fecha actual entre `start_date` y `end_date`). **Actualizado 2026-06-29 (BUG-086):** incluye actores con `area_id` directo a un área visible (vía servicio `area_visibility`), antes heurística los excluía.
- [ ] Botón "+ agregar al proyecto" en cada dropdown abre modal del Toggle 1.
- [ ] Filtros/agrupadores en Plan funcionan con las 6 dimensiones.
- [ ] Performance: render de WBS con 500 tareas + 50 personas < 1s.

**Test Cases:**
- TC-117-1: dropdown de assignee en task no muestra actores sin participation.
- TC-117-2: agrupar por equipo operativo respeta `is_primary`.
- TC-117-3: filtro "líder de área" devuelve solo tareas asignadas a actor con `is_area_lead=true`.
- TC-117-4: + agregar al proyecto desde dropdown crea participation y refresca el dropdown.
- TC-117-5: assignee con participation expirada (end_date pasada) aparece en gris en filtros históricos.

---

## # PENDING — US-118 — (post-MVP) Consolidar project_members en project_participations + migrar permisos RBAC

**Como** sistema
**Quiero** una sola fuente de verdad sobre quién está en el proyecto
**Para** simplificar permisos y eliminar drift entre `project_members` y `project_participations`.

**Plan:**
- Fase 1: doble escritura — toda mutación en `project_members` también escribe en `project_participations` y viceversa.
- Fase 2: lectura desde `project_participations` en RBAC y filtros "mis proyectos".
- Fase 3: drop tabla `project_members`.

**Criterios de aceptación:**
- [ ] RBAC sigue funcionando en cada fase (tests de regresión).
- [ ] No se pierde ningún member al migrar.
- [ ] Endpoint `/projects/{id}/members` deprecado en favor de `/projects/{id}/participations`.

**Riesgo:** alto — toca permisos. Se trabaja como bloque separado tras Bloque D estabilizado.

---

## Bloque F — US-182 / US-183 / US-184 — Pool de recursos, motor de saturación y alertas (2026-07-09)

> **Decisión de diseño (extender-no-duplicar):** en vez de crear una
> tabla `resource_pool` nueva, **el `Actor` ES el resource pool del
> tenant** — se extiende con clasificación y capacidad. La saturación no
> vive en el actor sino en la **relación** actor↔proyecto
> (`project_participations`), consistente con el modelo de este epic
> (participación temporal ya vivía ahí).

### US-182 — Actors como pool de recursos con capacidad (`c3fdf7e`)

Migración `20260708_0092_actors_resource_pool.py` agrega a `actors`
(sin backfill; actores existentes quedan "sin clasificar" con capacidad
default 100/100):

| Campo | Notas |
|---|---|
| `organization_id` | opcional; `NULL` = recurso tenant-global (no atado a una org) |
| `resource_type` | `cliente_negocio`\|`cliente_it`\|`e4_pmo`\|`e4_tecnologia`\|`vendor_externo` |
| `portfolio_function` | `pm`\|`pmo`\|`arquitectura`\|`infraestructura`\|`aplicaciones`\|`datos`\|`seguridad`\|`integraciones`\|`negocio`\|`change`\|`testing`\|`vendor` |
| `seniority` | `junior`\|`mid`\|`senior`\|`lead` |
| `scarcity_level` | `alta`\|`media`\|`baja` |
| `location` | texto libre |
| `skills_tags` | JSON array |
| `nominal_capacity_pct` | capacidad nominal (default 100) |
| `project_capacity_pct` | capacidad **disponible para proyectos** — base de todo el cálculo de saturación (US-183), nunca se compara contra 100 fijo |
| `is_key_resource` | flag "recurso clave" (alimenta alertas US-184 y dimensión "recursos" del semáforo, US-180) |
| `is_shared_resource` | default `true`; `false` = especialista dedicado/no compartido |
| `fte_cost_rate` | costo opcional |

- `/actors`: acepta y devuelve los campos nuevos; filtros
  `resource_type` / `portfolio_function` / `organization_id` en el
  listado.
- Admin de actores (`TenantActorsPanel`): sección "Recurso y capacidad"
  en el form + columnas Tipo/Función/Cap. proyectos/🔑 ordenables y
  filtrables.

**Test Cases:** `test_us182_resource_pool.py` (5 TC).
**Estado de integración:** DONE (US-182).

### US-183 — Participations con FTE% + motor de saturación (`4aec20c`)

Migración `20260708_0093_participation_allocation.py` agrega a
`project_participations`:

| Campo | Notas |
|---|---|
| `allocation_pct` | FTE% de la asignación; `NULL` = sin cuantificar (no suma demanda) |
| `assignment_type` | `directa`\|`advisory`\|`backup`\|`shared_service`\|`steerco_only` |
| `status` | `tentativa`\|`activa`\|`cerrada`\|`cancelada` — **solo `activa` suma demanda**; backfill: `activa` si `is_active=true`, si no `cerrada` |
| `is_critical` | flag de asignación crítica |
| `phase` | fase del proyecto en la que aplica la asignación |

- `services/capacity.py` — motor de saturación:
  - Demanda por ventana (`hoy` / `semana` / `3 semanas` / `mes`) contra
    `actors.project_capacity_pct` (nunca contra 100 fijo).
  - Niveles de agregación: individual / rol / área / equipo.
  - Vista de **conflictos**: proyectos en choque de un mismo recurso +
    recomendación.
  - Umbrales configurables por tenant (`tenants.settings.capacity_thresholds`).
- **Activa la dimensión "recursos" del semáforo de salud** (US-180,
  EP005): demanda TOTAL del recurso en todos sus proyectos; recurso
  clave sobreasignado → rojo.
- Endpoints nuevos:
  - `GET /api/v1/capacity/summary`
  - `GET /api/v1/capacity/conflicts`
  - `GET /api/v1/projects/{id}/resource-load`
- Frontend: página nueva `/pmo/resources` (tabs Personas / Roles /
  Áreas-Equipos / Conflictos, selector de ventana, tablas ordenables) +
  link "Recursos" en el sidebar; campos FTE% / tipo / estado / crítico
  visibles en el directorio del proyecto (`/pmo/projects/{id}/areas`).

**Test Cases:** 7 TC (incluye caso canónico "Eli 65/50 → rojo").
**Estado de integración:** DONE (US-183).

### US-184 — Alertas de capacidad (`595dc4f`)

3 reglas sobre el sistema de notificaciones de EP011 (in-app, sin
email por default), en `services/capacity_alerts.py`:

| Alerta | Condición |
|---|---|
| `capacity_overload` | demanda > capacidad + umbral rojo en ventana de 30 días |
| `capacity_key_resource_risk` | recurso clave (`is_key_resource`) con asignación activa en ≥3 proyectos 🟡/🔴 |
| `capacity_solo_specialist` | recurso `is_shared_resource=false` con >1 proyecto activo |

- Destinatarios: los PMs de los proyectos afectados. Link a
  `/pmo/resources`.
- Dedupe: no repite la misma alerta (tipo + actor) dentro de 7 días.
- Triggers: sweep semanal desde el job de snapshot
  (`analytics/snapshots.snapshot_tenant`, no tumba el snapshot si falla)
  + fast-path al crear/editar una participation con FTE%
  (`project_directory`).

**Test Cases:** 5 TC nuevos (`test_us184_capacity_alerts.py`).
**Estado de integración:** DONE (US-184).

---

## Notas

- IDs de DEC-### a asignar al cierre, mirando el último libre en `DECISIONS.md`.
- ADR potencial: "drop de `*_area_id` con snapshot a `legacy_area_id` para rollback de 1 sprint".
- **2026-06-29 — Actualización batch:** BUG-085 (creación de áreas desde proyecto con propagación automática), BUG-086 (servicio `area_visibility` + actores asignables por área), ENH-183 (listar solo asignados + reuso de catálogo). Ver secciones Bloques B/C/D para detalles.
- **2026-07-09 — Batch Revamp 1.0:** US-182 (`c3fdf7e`), US-183 (`4aec20c`), US-184 (`595dc4f`) — Bloque F nuevo: pool de recursos con capacidad sobre `actors`, motor de saturación sobre `project_participations` + página `/pmo/resources`, alertas de capacidad in-app. Ver sección "Bloque F" arriba.
