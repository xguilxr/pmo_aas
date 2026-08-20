---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

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

Reemplaza la jerarquía actual `Area → Team → Actor` (que mezcla 3 dimensiones) por un modelo que separa explícitamente las 4 dimensiones del feedback:

| Dimensión | Hoy | Nuevo |
|---|---|---|
| Área funcional | `actors.area_id` (mezclado con jerarquía) | Atributo **estable** de la persona (1 FK) |
| Equipo operativo | `actors.team_id` + `teams.area_id` | Atributo **por proyecto** (Testing, Deployment, Diseño) |
| Rol proyecto | implícito en `project_members.role_in_project` | Catálogo editable `project_roles` (PM, SME, Key User…) |
| Participación temporal | inexistente | `start_date` / `end_date` en participation |

El sistema gana 4 ejes de reporte: por persona, área funcional, equipo operativo y rol.

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

- **DEC-XXX** — Área funcional vive en la persona (1 FK). Equipo operativo y rol viven en `project_participations`. Una persona puede tener N participations en un proyecto (varios equipos/roles); una se marca `is_primary` para agrupadores.
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
- `POST /areas` — nuevo: acepta `project_id` o `program_id` (además de `organization_id`). Cuando se crea un área desde un proyecto, el backend deriva `organization_id` y crea automáticamente el `AreaAssignment` del scope correcto: proyecto → queda en ese proyecto; programa → se propaga a sus proyectos; organización → cascada de lectura. **Agregado 2026-06-29 (BUG-085).**

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
> tenant**. Se extiende con clasificación y capacidad. La saturación no
> vive en el actor, sino en la **relación** actor↔proyecto
> (`project_participations`), consistente con el modelo de este epic:
> la participación temporal ya vivía ahí.

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

### US-186 / US-187 — Organigrama con utilización (XLSX) por scope (`fa200bd`, 2026-07-09)

Export XLSX descargable del organigrama de recursos con su % de
utilización. Se genera on-demand desde el mismo motor de saturación de
US-183 (`services/capacity.py::monthly_utilization`). 2 hojas:

- **"Organigrama"** — recursos activos del scope + %FTE en el scope +
  %FTE total del tenant (un recurso puede participar en varios
  proyectos/organizaciones; las participaciones se **suman** por
  recurso a través de todos los proyectos del scope).
- **"Uso mensual"** — matriz Recurso × Mes (12 meses rolling), con
  fill condicional: **amarillo ≥80%**, **rojo >100%** de la capacidad
  disponible para proyectos (`project_capacity_pct`, US-182).

**Scopes y endpoints** (`services/organigrama_export.py` +
`api/v1/endpoints/organigrama.py`), todos autenticados y con
`Content-Disposition: attachment` (filename ya resuelto server-side
vía `filename_slug.artifact_filename`):

| Scope | Endpoint | Desde dónde se descarga |
|---|---|---|
| Programa | `GET /api/v1/programs/{id}/organigrama/export` | Botón "Organigrama (XLSX)" en el header de `/pmo/programs/[id]`, junto a "Status (PDF)" |
| Organización/portafolio | `GET /api/v1/organizations/{id}/organigrama/export` | Botón "Organigrama (XLSX)" en el header de `/pmo/organizations/[id]`, junto a "Reporte de Status (PDF)" |
| Tenant (global) | `GET /api/v1/capacity/organigrama/export` | Botón "Organigrama global (XLSX)" en el header de `/pmo/resources`, junto al selector de ventana |

Frontend: helpers `downloadOrganizationOrganigrama` /
`downloadProgramOrganigrama` / `downloadGlobalOrganigrama` en
`lib/api/analytics.ts` (fetch autenticado + Blob, filename parseado
del `Content-Disposition` en vez de fijo en cliente, a diferencia del
PDF de status).

**Test Cases:** `test_us186_organigrama_utilizacion.py` (backend).
**Estado de integración:** DONE (US-186 backend + US-187 frontend).

---

### US-208 — Recursos en dos pestañas: Catálogo y Capacidad ✅ (2026-08-20)

De los mockups aprobados el 2026-08-19, artboards «Recursos › Capacidad» y
«Recursos — Catálogo».

**Como** PMO Manager
**Quiero** ver la carga de cada persona **semana a semana**
**Para** encontrar el pico que hay que renivelar antes de que ocurra.

**El corte entre las dos pestañas es de tiempo verbal.** El catálogo contesta
«¿quién hay y cómo está **hoy**?» —una ventana, un número por recurso—. La
capacidad contesta «¿qué va a pasar?» —doce semanas, un número por recurso y
semana—. Son la misma tabla leída con dos preguntas, y tenerlas como cuatro
secciones planas (US-183) era lo que hacía que ninguna se leyera bien. Las
cuatro secciones de US-183 pasan a vivir dentro de Catálogo, sin cambios.

**Por qué no bastaba la matriz mensual de US-186.** Alguien al 90 % de media en
septiembre puede estar al 160 % la semana del corte y al 40 % el resto: el
promedio mensual esconde exactamente el pico que hay que renivelar. Las
decisiones de capacidad se toman por semana («lo movemos a la s37»), y por eso
la etiqueta de columna es el número de semana ISO.

**Criterios de aceptación:**
- [x] `GET /capacity/weekly-load?weeks=&organization_id=` — una serie semanal de
  % FTE por recurso, más los otros tres paneles de la pestaña en la **misma**
  respuesta: capacidad vs demanda por mes, críticos compartidos y sugerencias.
  Van juntos porque miran las mismas asignaciones: con un endpoint por panel,
  cuatro consultas leen la misma tabla y pueden leerla en momentos distintos —el
  heatmap diría 160 % mientras el panel de al lado ya no lista a esa persona.
- [x] Las semanas empiezan el **lunes de la semana en curso**, no hoy: media
  semana como primera columna daría un porcentaje incomparable con las de al
  lado. El horizonte tiene techo de 52 semanas — la respuesta lleva una serie
  por recurso y el ancho multiplica.
- [x] Una asignación **sin fechas** cuenta en todas las semanas: `None` es «sin
  plazo», no «no aplica». Tratarlo al revés hace desaparecer del heatmap a quien
  está asignado indefinidamente, que es la mitad de los casos reales.
- [x] Las filas de equipo **promedian** a sus miembros, no los suman: sumar seis
  daría 720 %, que como «carga del equipo» no significa nada. El contrato lo
  dice (`kind: "team"`, `members`) y la fila lo rotula. Un equipo de uno no
  genera fila: repetiría la de su único miembro.
- [x] La demanda de una persona cuenta **todos** sus proyectos aunque el filtro
  sea de una organización: quien está saturado lo está por la suma de todo lo
  que tiene encima. Es la misma regla de `/projects/{id}/resource-load`.
- [x] **Los asignados sin `%` capturado no entran, y se cuentan.** Una fila en
  cero para quien sí está asignado se lee como «libre», cuando lo que pasa es
  que no se sabe cuánto pesa. El caso más común es el PM que la sincronización
  de membresía (US-118) asigna sola. El panel dice cuántos son y dónde
  capturarlo, porque es accionable.
- [x] Clic en una celda: los proyectos que componen esa carga, **sin** ida al
  servidor — la fila trae sus asignaciones con fechas. El cliente decide qué
  toca cada semana con la misma regla que el servidor; discrepar ahí haría que
  el desglose sumara distinto de la celda que lo abrió.
- [x] Escala de cinco tramos (0 · ≤50 · ≤80 · ≤100 · >100) y no un degradado:
  un degradado obliga a comparar tonos entre celdas lejanas, y lo que hay que
  ver de un golpe es dónde se cruza el 100 %. Los tramos son fijos y **no**
  derivados de los umbrales del inquilino: los umbrales configuran cuándo
  avisar, y la escala dice cuánto hay asignado, que es un hecho.
- [x] «Compartido» es **medido**, no declarado: estar en dos o más proyectos a
  la vez lo es, con `is_shared_resource` puesto o sin él.
- [x] Las sugerencias son derivadas y nombran recurso y semanas concretas
  («L. Fuentes pasa de su capacidad en s35 a s36: pico de 160 %»). Sin
  sobrecarga no se emite ninguna: inventar un consejo cuando no hay nada que
  hacer entrena a la gente a ignorar el panel.
- [x] Header y primera columna fijos, como en la vista maestra (US-207).
- [x] Los escenarios what-if quedan **pendientes** y la pantalla lo dice — el
  propio mockup los marca «próximamente».
- [x] Costo por recurso sigue siendo US-215 (W4): no está en esta US.

**Test Cases:** `test_us208_carga_semanal.py`
- `TC-208.1` — Las semanas: arrancan en lunes, son consecutivas y la etiqueta es
  la semana ISO.
- `TC-208.2` — Una asignación pesa en las semanas que toca y solo en esas; dos
  que solapan se suman; sin fechas cuenta en todas.
- `TC-208.3` — La fila de equipo promedia; un equipo de uno no genera fila.
- `TC-208.4` — Sin asignación no hay fila; sin recursos se devuelven las semanas
  igual (DIS-03 necesita las columnas para decir «no hay nadie»).
- `TC-208.5` — Capacidad vs demanda en FTE; críticos compartidos desde dos
  proyectos; la sugerencia nombra recurso y semanas, y sin sobrecarga no hay.
- `TC-208.6` — El endpoint devuelve el desglose de la celda y rechaza un
  horizonte absurdo (422).

**Estado de integración:** DONE (US-208).

---

### US-217 — RACI y stakeholders clave ✅ (2026-08-20)

Del artboard «Proyecto — Recursos» de los mockups aprobados el 2026-08-19,
marcado como nuevo: «RACI / stakeholders clave».

**Como** PMO Manager
**Quiero** que cada persona del proyecto tenga declarado si responde, ejecuta,
se le consulta o se le informa
**Para** saber a quién llamar cuando algo se atora, y que no haya dos
«responsables» de lo mismo.

**El valor no está en las cuatro letras, está en que la A sea una.** Un proyecto
con dos responsables últimos no tiene ninguno: cada uno supone que responde el
otro. Es la única de las cuatro que el sistema limita; R, C e I se reparten
cuanto haga falta y limitarlas no protegería nada.

**Por qué es un campo de la participación y no una tabla nueva.** Una
participación ya dice «esta persona está en este proyecto con este rol y este %
de FTE». El RACI dice, de esa misma participación, **de qué tipo** es la
responsabilidad. Una tabla aparte obligaría a mantener dos listas de las mismas
personas y a decidir qué hacer cuando alguien está en una y no en la otra — y la
respuesta a eso siempre acaba siendo «depende».

**Por qué la unicidad de la A no es una restricción de base de datos.** Sería un
índice único parcial (`WHERE raci = 'A'`), que Postgres soporta y SQLite no. Los
tests corren sobre SQLite: una restricción que solo existe en producción es una
restricción que nadie prueba. La regla vive en la frontera de la API, donde
además puede decir **quién** ya tiene la A — «Ana ya es la responsable última»
es accionable; «ya hay una A» obliga a ir a buscarla.

**Por qué se valida a nivel de proyecto y no de tarea.** Las participaciones son
del proyecto. Un RACI por tarea es un modelo distinto —una matriz de N personas
por M entregables— y sería otra US; ponerlo aquí a medias daría un dato que no
se puede leer en ninguna de las dos escalas.

**Criterios de aceptación:**
- [x] `raci` (`A`/`R`/`C`/`I`, nulable) e `is_key_stakeholder` (booleano) en
  `project_participations`. Nulable porque estar en un proyecto sin papel
  declarado es el estado normal de la mayoría de las participaciones, y
  obligarlo llenaría la columna de letras puestas al azar.
- [x] Una sola A por proyecto, exigida en `POST` y en `PATCH`. El 400
  (`VALIDATION_ERROR`) nombra a quien ya la tiene.
- [x] Poner la A a quien ya la tiene es idempotente, no conflicto. Y **quitarla
  se permite**: un proyecto sin A es incompleto, no inválido —así está antes de
  que alguien la asigne—, y rechazarlo impediría corregir una A puesta a la
  persona equivocada.
- [x] El `PATCH` borra el papel con `""`, no con `null`. El schema usa
  `exclude_unset`, así que `undefined` ya significa «no lo mandes»; hacía falta
  un valor que viajara y que dijera «déjalo vacío». Queda en el contrato en vez
  de escondido.
- [x] La columna RACI en el directorio ordena por rango (A, R, C, I, sin papel),
  no alfabéticamente: que «A» vaya antes de «C» en el alfabeto es coincidencia, y
  el orden que se quiere leer es el de jerarquía.
- [x] Una franja sobre la tabla dice quién es la A, cuántos R/C/I hay y cuántos
  stakeholders clave. Sin A, lo dice con esas palabras: «Sin asignar — nadie
  responde por el resultado». El hueco es lo que la matriz existe para hacer
  visible (DAT-12).
- [x] El selector muestra la descripción de la letra elegida. Sin eso, A y R se
  confunden en cada conversación: las dos palabras españolas empiezan por
  «responsable».
- [x] Índice `(project_id, raci)` — la consulta que importa es «la A de este
  proyecto», y se hace una vez por cada guardado de papel.

**Tests (`tests/test_us217_raci.py`, 16):**
- `TC-217.1` — Crear participación con cada una de las cuatro letras.
- `TC-217.2` — Segunda A en el mismo proyecto → 400 nombrando a la primera.
- `TC-217.3` — Segunda A vía `PATCH` → 400; la primera queda intacta.
- `TC-217.4` — Reasignar la A a quien ya la tiene → 200 (idempotente).
- `TC-217.5` — Quitar la A con `""` → 200 y el proyecto queda sin A.
- `TC-217.6` — Dos proyectos, una A cada uno → los dos 201: el límite es por
  proyecto, no por tenant.
- `TC-217.7` — Letra inválida → 422 del schema.
- `TC-217.8` — `is_key_stakeholder` viaja en create, read y update.
- `TC-217.9` — Sin `raci` en el `PATCH`, el papel existente no se toca.
- `TC-217.10` — Aislamiento por tenant: la A de otro tenant no cuenta.

**Estado de integración:** DONE (US-217).

---

### US-215 — Costo con la tarifa congelada ✅ (2026-08-20)

Del artboard «Proyecto — Recursos» y del bloque W4 del rediseño de modelo de
datos: «costo-snapshot en participaciones».

**Como** PMO Manager
**Quiero** que el costo de una asignación se calcule con la tarifa que estaba
vigente cuando se asignó
**Para** que subir una tarifa hoy no reescriba el gasto de hace seis meses.

**El defecto, en una frase.** `actors.fte_cost_rate` guarda la tarifa **de hoy**.
Si en marzo alguien sube la tarifa de un consultor, el costo del trabajo de enero
cambia solo y el gasto acumulado del proyecto se reescribe hacia atrás. Es el
mismo problema que la línea base resuelve para las fechas (US-212): la historia
no se puede mover.

**El campo existía y no se podía llenar.** `fte_cost_rate` está en la API desde
US-182 y **ninguna pantalla lo capturaba**. Un campo que nadie puede llenar es un
campo que no existe (CLAUDE.md §13), así que esta US también trae el formulario.

**Por qué la unidad de tiempo es una columna nueva y no una convención.**
«Tarifa de un FTE» puede ser por hora, por día o por mes, y las tres son
ciframientos legítimos según el contrato. Multiplicar por los días de la
asignación asumiendo una de ellas da un número que **parece** autoritativo y está
equivocado en un factor de 21 o de 168. Mientras nadie calculaba nada, la
ambigüedad no costaba —era un número que una persona leía y sabía interpretar—;
al derivar un costo se vuelve el dato más importante del cálculo.

**Por qué la tarifa no se acepta desde el cliente.** Ni al crear ni al editar.
Aceptarla permitiría registrar un costo que no corresponde a ninguna tarifa
aprobada, y el snapshot dejaría de ser una copia verificable de algo. Se congela
del catálogo, o se pide explícitamente con `freeze-cost-rate`.

**Lo que recongelar cuesta, dicho de frente.** Revalúa la asignación entera al
nuevo importe, incluido el trabajo ya hecho. Es la limitación de tener un solo
snapshot por participación. La salida correcta cuando la tarifa cambia a mitad de
camino ya está en el modelo: cerrar la participación en la fecha del cambio y
abrir otra con el periodo nuevo — las participaciones llevan
`start_date`/`end_date` y ciclo de vida (US-183) justamente para eso. Una tabla
de historial de tarifas resolvería lo mismo duplicando el mecanismo.

**Criterios de aceptación:**
- [x] `cost_rate_snapshot`, `cost_currency`, `cost_rate_period` y
  `cost_rate_captured_at` en `project_participations`; `cost_rate_period` en
  `actors`. Migración `0114`.
- [x] La tarifa se congela **al crear** la participación. Que el actor no tenga
  tarifa capturada es lo normal y **no** impide asignarlo: la participación queda
  sin costo calculable, que es la verdad.
- [x] Hacen falta las **dos** cosas, tarifa y periodo. Con la tarifa sola el
  importe no tiene unidad de tiempo, y congelarlo así dejaría un número que
  parece utilizable y no lo es.
- [x] `POST .../{id}/freeze-cost-rate` para congelar después. Falla con 400 —y no
  en silencio— si el catálogo no tiene tarifa y periodo: alguien lo pidió
  explícitamente, y un 200 sin haber congelado nada lo dejaría creyendo que ya
  está.
- [x] La moneda es la **del proyecto** (cascada de `dominio/moneda.resolver`,
  decisión del owner en BUG-092) y se congela con la tarifa. Si el proyecto cambia
  de moneda después, los costos ya congelados conservan la suya — cambiarlos
  convertiría importes sin tipo de cambio.
- [x] El costo se **deriva al leer**, no se guarda. Un costo almacenado se queda
  viejo el día que alguien mueve las fechas o el % de dedicación por un camino que
  se olvidó de recalcularlo — misma razón que la completitud de US-210.
- [x] Sin cualquiera de los cinco datos —tarifa, periodo, % FTE, y las dos
  fechas— el costo es `None`, no cero. Un cero se sumaría al total del proyecto
  haciéndolo parecer completo (MCS DAT-12). **No se supone 100 % de dedicación**:
  la mayoría de las asignaciones compartidas no lo son, y suponerlo infla el costo
  de todo el portafolio.
- [x] `GET .../cost-summary` devuelve **un importe por moneda**, nunca un total
  único: dos personas facturadas en monedas distintas no tienen un costo total
  (misma regla que `dominio/moneda.py`).
- [x] `without_rate` viene en la **misma** respuesta que el total. Un total sin
  ese número miente por omisión: «$400.000 en recursos» con doce asignaciones sin
  tarifa es un presupuesto a medias presentado como completo. En llamadas
  separadas se puede mostrar uno sin el otro, y eso es lo que hay que impedir.
- [x] Solo cuentan las asignaciones con estado `activa` — una tentativa no es un
  compromiso de gasto y una cancelada no lo fue nunca—, el mismo criterio que el
  motor de saturación de US-183.
- [x] Un mes son **21 días laborables**, la misma convención que
  `ensure_duration_max_21` ya usa en el plan. Dos convenciones distintas para el
  mismo mes en el mismo producto es peor que elegir la imperfecta.
- [x] UI: tarifa + unidad en el catálogo de recursos; columna de costo en el
  directorio del proyecto, con botón «Congelar tarifa» donde falta y el hueco
  nombrado —«sin tarifa» y «sin fechas o % FTE» llevan a acciones distintas—; y
  una franja con el total por moneda y lo que falta.

**Imprecisión conocida y declarada:** `dias_laborables` no conoce los feriados.
El calendario laboral por país o por inquilino es un frente propio, y descontar
los feriados de México a un equipo en Polonia sería peor que no descontar ninguno.

**Tests (`tests/test_us215_costo_snapshot.py`, 24):**
- `TC-215.1` — La regla sin base de datos (MCS DEV-02, 12 casos): días laborables
  inclusivos y sin fin de semana, rango invertido, la única frontera de conversión
  de tiempo, periodo desconocido sin default, el costo completo, los cinco datos
  obligatorios uno por uno, no se supone dedicación completa, dos monedas no se
  suman, un costo desconocido no cuenta como cero, moneda inválida descartada.
- `TC-215.2` — Contra la API (12 casos): la tarifa se congela al asignar;
  **subir la tarifa del catálogo no cambia lo ya asignado** —el defecto entero en
  un test—; sin tarifa se puede asignar igual; con tarifa y sin unidad no se
  congela; congelar después; congelar sin tarifa falla y lo dice; la moneda es la
  del proyecto; el resumen da total y lo que falta; una tentativa no cuenta;
  sin fechas no hay costo; la tarifa no se puede dictar desde el cliente.

**Estado de integración:** DONE (US-215).

---

## Notas

- IDs de DEC-### a asignar al cierre, mirando el último libre en `DECISIONS.md`.
- ADR potencial: "drop de `*_area_id` con snapshot a `legacy_area_id` para rollback de 1 sprint".
- **2026-06-29 — Actualización batch:** BUG-085 (creación de áreas desde proyecto con propagación automática), BUG-086 (servicio `area_visibility` + actores asignables por área), ENH-183 (listar solo asignados + reuso de catálogo). Ver secciones Bloques B/C/D para detalles.
- **2026-07-09 — Batch Revamp 1.0:** US-182 (`c3fdf7e`), US-183 (`4aec20c`), US-184 (`595dc4f`) — Bloque F nuevo: pool de recursos con capacidad sobre `actors`, motor de saturación sobre `project_participations` + página `/pmo/resources`, alertas de capacidad in-app. Ver sección "Bloque F" arriba.
- **2026-07-09 — US-186/US-187:** organigrama con utilización (XLSX, 2 hojas: %FTE + uso mensual con alertas amarillo/rojo) descargable por scope programa/organización/tenant. Ver sub-sección "US-186 / US-187" en Bloque F arriba.
- **2026-07-18 — Batch feedback 16-jul:** ENH-198 (`828774f`) — tab Personas en `/pmo/resources` agrega columna "% Uso" (FTE asignado / capacidad teórica, color al 80/100%) + filtros por área funcional y equipo operativo (sub-área acotado al área elegida). Backend: `capacity.py` agrega campos `area_name`, `team_name`, `usage_pct` por recurso en responses de listado.
- **2026-08-20 — US-217:** RACI (`A`/`R`/`C`/`I`) e `is_key_stakeholder` en
  `project_participations` (migración `20260820_0112`). Regla de la A única en la
  frontera de la API (`app/dominio/raci.py`), no en el esquema, porque el índice
  único parcial que haría falta no existe en SQLite y los tests corren ahí. UI:
  columna RACI ordenada por rango, franja de resumen que nombra a la A o dice
  que falta, y marca de stakeholder clave en el directorio.
- **2026-08-20 — US-215:** costo-snapshot en `project_participations`
  (`cost_rate_snapshot`, `cost_currency`, `cost_rate_period`,
  `cost_rate_captured_at`) + `actors.cost_rate_period`, migración `0114`. La
  tarifa se congela del catálogo al asignar y no se recalcula; el costo se deriva
  al leer. `fte_cost_rate` pasa a capturarse desde la UI —existía en la API desde
  US-182 sin ninguna pantalla que lo llenara—. Regla en `app/dominio/costo.py`.
