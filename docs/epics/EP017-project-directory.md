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

## Notas

- IDs de DEC-### a asignar al cierre, mirando el último libre en `DECISIONS.md`.
- ADR potencial: "drop de `*_area_id` con snapshot a `legacy_area_id` para rollback de 1 sprint".
- **2026-06-29 — Actualización batch:** BUG-085 (creación de áreas desde proyecto con propagación automática), BUG-086 (servicio `area_visibility` + actores asignables por área), ENH-183 (listar solo asignados + reuso de catálogo). Ver secciones Bloques B/C/D para detalles.
