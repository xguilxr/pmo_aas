---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# DB-CHANGES.md — Cambios de schema por epic

> **Política activa (2026-04-21):**
> - Productivo v1.0 corre en **Railway Postgres** (DEC-013). No hay plan
>   de migrar a otro motor.
> - Una migración Alembic por US. Nunca combina múltiples cambios
>   estructurales en un solo archivo.
> - Este archivo **no es la fuente de verdad del schema**. Solo indexa
>   qué epic disparó qué migración y lo pendiente de BD para POST-MVP.
>   El schema vigente se describe en
>   [`docs/architecture/database.md`](../architecture/database.md) y se
>   materializa en `apps/api/alembic/versions/*.py`.

---

## Migraciones aplicadas (v1.0)

| # | Archivo | Epic | Contenido |
|---|---|---|---|
| 0001 | `20260101_0001_initial.py` | EP001 | Tablas base: `tenants`, `users`, `roles`, `user_roles`, `permissions`, `role_permissions`, `organizations`, `audit_logs`, `refresh_tokens` |
| 0002 | `20260101_0002_org_program.py` | EP001 / EP002 | Tabla `programs` + FKs a `organizations` |
| 0003 | `20260101_0003_project_requests.py` | EP003 | Tabla `project_requests` (shape inicial) |
| 0004 | `20260101_0004_projects.py` | EP005 | Tabla `projects` + índices |
| 0005 | `20260101_0005_project_members.py` | EP005 | Tabla `project_members` |
| 0006 | `20260101_0006_modules.py` | EP006 | Tablas `risks`, `issues`, `documents`, `meeting_minutes`, `lessons_learned` |
| 0007 | `20260101_0007_ai_and_reports.py` | EP008 | Tablas `ai_jobs`, `reports` |
| 0008 | `20260101_0008_tasks.py` | EP005 | Tabla `tasks` (plan del proyecto) |
| 0009 | `20260420_0009_business_units_departments.py` | EP002 | Tablas `business_units`, `departments` + FKs en `programs`, `projects`, `project_requests` (ver §EP002) |
| 0010 | `20260420_0010_users_preferences.py` | EP001 | Columnas de preferencias en `users` (tema, idioma) |
| 0011 | `20260420_0011_project_requests_extra_fields.py` | EP003 | Columnas adicionales de solicitud (ver §EP003) |
| 0012 | `20260420_0012_project_charters.py` | EP003 | Tabla `project_charters` (ver §EP003) |
| 0013 | `20260420_0013_project_areas.py` | EP005 | Tabla `project_areas` (actores/áreas sin login) |
| 0014 | `20260420_0014_reports_period.py` | EP014 | Columnas de período en `reports` |
| 0015 | `20260420_0015_reports_generator_cut_off.py` | EP014 | `reports.generator` + `reports.cut_off_date` |
| 0016 | `20260421_0016_notifications.py` | EP011 | Tabla `notifications` (US-027) |
| 0017 | `20260421_0017_platform_ai_settings.py` | EP008/EP010 | Tabla singleton `platform_ai_settings` con 1 row seed `id='default'` — defaults de plataforma editables por superadmin (US-054) |
| 0018 | `20260423_0018_scheduled_reports.py` | EP014 + EP011 | Tabla `scheduled_reports` — programaciones automáticas de reportes (Avance/Seguimiento) con cadencia daily/weekly/monthly, destinatarios y `next_run_at` para dispatch por Celery beat (US-056) |
| 0019 | `20260423_0019_project_area_resources.py` | EP002 + EP006 | `project_areas.area_leader_id` (FK → users, nullable) + tabla `project_area_resources` para soportar múltiples recursos internos (`user_id`) o externos (`name` + `email`) por área (ENH-020, US-062) |
| 0020 | `20260423_0020_risks_comments.py` | EP006 | `risks.comments` JSON (lista de `{text, author_id, created_at}`) para soportar comentarios tipo Jira desde el panel editable (US-058) |
| 0021 | `20260423_0021_tenant_ai_mode.py` | EP008 + EP002 | `platform_ai_settings.groq_api_key_encrypted` + `groq_model` + `ai_jobs.provider` indexado + data migration: todos los tenants existentes quedan en `settings.ai.mode = "disabled"` (opt-in, US-057) |
| 0022 | `20260423_0022_migrate_ollama_legacy_to_byo.py` | EP008 + EP002 | Data-only: traslada `tenants.settings.ai.ollama` (US-048 legacy) al shape `settings.ai.byo = {provider: "ollama", base_url, model}` con `mode = "byo"`. Idempotente (US-057) |
| 0023 | `20260424_0023_password_reset_tokens.py` | EP001 + EP011 | Tabla `password_reset_tokens` (`id`, `token_hash` SHA-256 del plaintext, `user_id`, `expires_at`, `used_at`, `ip_address`, `created_at`) con índice `(user_id, used_at)` para el flujo "Olvidé mi contraseña" (US-063) |

---

## EP001 — Auth / usuarios

Schema cubierto por migraciones **0001** + **0010**.

## EP002 — Jerarquía org

Migración **0009** (`20260420_0009_business_units_departments.py`):

- Crea `business_units(id, tenant_id, organization_id, name, …)` y
  `departments(id, tenant_id, business_unit_id, name, …)`.
- Agrega `programs.department_id` (nullable): un programa puede colgar
  directo de la organización o de un departamento.
- Agrega `projects.department_id` y `projects.business_unit_id`
  (nullable): se llenan desde la cadena del programa cuando aplica.
- Agrega `project_requests.business_unit_id` y
  `project_requests.department_id` como FK.

Los campos legacy `project_requests.business_unit` y
`project_requests.department` (texto libre) se conservan por
retro-compatibilidad. Pueden dropearse cuando se valide que ningún
tenant productivo los lee.

## EP003 — Solicitudes y Project Charter

Migración **0011** (`project_requests_extra_fields`): añade
`requester_name`, `requester_email`, `sponsor_email`, `key_people`,
`if_not_done`, `observations`, `entregables`.

Migración **0012** (`project_charters`): crea tabla completa con las 4
secciones (información general, stakeholders, clasificación, datos de
gestión). Los campos de gestión se sincronizan dinámicamente desde
`projects` por el servicio `app.services.charters`, no por trigger SQL
(DEC-008).

## EP005 — Proyectos

Schema cubierto por **0004** + **0005** + **0008** + **0013**.

Migración **0013** (`project_areas`): actores y áreas del proyecto sin
cuenta en la plataforma (DEC-009). Campo `type` acepta
`'area'|'actor'|'team'`.

## EP006 — RAID consolidado

**Sin migración nueva.** RAID es una **vista** sobre `risks` + `issues`
(DEC-007). Risks viene de la tabla `risks`. Actions/Incidents/Decisions
vienen de la tabla `issues`, discriminados por `issues.type ∈
{'action','incident','decision'}`. El validator se hace en el modelo,
no en BD.

## EP007 — Admin

Sin schema nuevo. Toda la funcionalidad reutiliza tablas existentes
(`tenants`, `users`, `roles`, `audit_logs`, `organizations`, `portfolios`,
`programs`). Hasta US-199 la sección de jerarquía del panel leía
`business_units` y `departments`; ADR-037 las retiró.

## EP008 — IA

Schema cubierto por migración **0007** (`ai_jobs`, `reports`).

## EP010 — Super admin panel

Sin schema nuevo. `users.is_superadmin` ya existe desde
`20260101_0001_initial.py`. El panel reusa `tenants`, `users` y
`audit_logs` cross-tenant.

## EP011 — Notificaciones (POST-MVP)

**Migración pendiente** para US-027. Plan de shape:

```sql
CREATE TABLE notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    user_id uuid NOT NULL REFERENCES users(id),
    type text NOT NULL,  -- 'request_approved'|'pm_assigned'|'aid_overdue'|'comment_added'|…
    title text NOT NULL,
    body text,
    entity_type text,    -- 'project'|'risk'|'request'|…
    entity_id uuid,
    link text,           -- URL relativa al destino
    is_read bool DEFAULT false,
    read_at timestamptz,
    created_at timestamptz DEFAULT now()
);
CREATE INDEX idx_notif_user_unread ON notifications(user_id, is_read, created_at DESC)
    WHERE is_read = false;
CREATE INDEX idx_notif_tenant ON notifications(tenant_id, created_at DESC);
```

US-028 (email via Resend) no requiere schema adicional. La cola sale de
`notifications.type`, leída por un worker Celery.

## EP013 / EP015 — Refactor navegación

Sin migraciones nuevas. `tenants.logo_url` ya existía. US-031 reusa el
campo y el storage local.

## EP014 — Entregables operativos

Migraciones **0014** (`reports_period`) + **0015**
(`reports_generator_cut_off`): añaden `reports.generator` (`'manual' |
'ai' | 'avance' | 'seguimiento'`) y `reports.cut_off_date` + columnas de
período. US-040 (formato estandarizado de minuta IA) es
post-procesamiento sobre `meeting_minutes`. No toca BD.

Migración **0018** (`scheduled_reports`): tabla nueva para US-056
(calendarización automática de envíos). Columnas: `id`, `tenant_id`,
`project_id`, `report_type` (`'avance' | 'seguimiento'`), `cadence`
(`'daily' | 'weekly' | 'monthly'`), `recipients` (JSON list de
emails), `enabled`, `last_run_at`, `next_run_at`, `last_error`,
`created_by`. Índices: `(tenant_id, project_id)` y `(enabled,
next_run_at)` para el dispatch del beat.

## EP006 — RAID con área responsable (US-064)

Migración **0024** (`raid_area_id`): agrega `area_id` a `risks` e
`issues`, como FK nullable a `project_areas.id` con
`ON DELETE SET NULL`. Suma un índice compuesto `(tenant_id, project_id,
area_id)` para el ordenamiento de las tablas RAID.

Regla de legacy: los ítems previos a la migración quedan con
`area_id = NULL`. La obligatoriedad en creación vive a nivel de
schema Pydantic (`422` en POST si falta), NO en la DB. Los endpoints
GET ordenan por: `CASE WHEN area_id IS NULL THEN 1 ELSE 0 END` (legacy
al final) → `project_areas.name ASC` → `identified_at DESC` (risks) o
`reported_at DESC` (issues) → `severity/priority DESC`. Nuevo filtro
`?area_id=` en `/projects/{id}/risks`, `/projects/{id}/issues`,
`/tenant/risks` y `/tenant/issues`.

## EP016 — IA local (Ollama vía Tailscale) — ❌ ARCHIVADA

Toda la epic queda superseded por DEC-017. Se elimina en BUG-053
(2026-05-08). `OllamaProvider` se quita del runtime. Los datos legacy
en `tenants.settings.ai.ollama` quedan en BD por auditoría, pero ya no
se leen: el resolver de provider falla con `unsupported_provider`
para `provider="ollama"`.

Ver `docs/archive/cancelled-epics/EP016-local-ai-tunnel.md`.

---

## EP012 — ❌ CANCELADO

Ver `docs/archive/cancelled-epics/EP012-db-migration.md` y **DEC-013**.
No hay trabajo de BD pendiente por esta épica.

---

## EP001 — Permission model overhaul (Sprint 6, DEC-024)

### Migración **0028** — `role_type` normalize viewer→user (US-076)

`UPDATE users SET role_type='user' WHERE role_type='viewer'` +
`UPDATE users SET role_type='user' WHERE role_type IS NULL` (backfill
de cualquier registro legacy que no haya tocado la migración 0026).

Sin cambio de schema, solo data normalization. `viewer` queda
eliminado del vocabulario (DEC-024): el endpoint
`/auth/me/permissions` deja de aceptarlo, y `capabilities_for("viewer")`
retorna `set()` por fail-safe. `Literal[RoleType] = ["admin", "user"]`.

### Migración **0029** — `organization_user_exclusions` (US-078)

Tabla nueva para membership opt-out user↔organización:

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `VARCHAR(36)` PK | UUID |
| `user_id` | `VARCHAR(36)` FK `users.id` `ON DELETE CASCADE` | indexed |
| `organization_id` | `VARCHAR(36)` FK `organizations.id` `ON DELETE CASCADE` | indexed |
| `created_at` | `TIMESTAMPTZ` | server_default now() |
| `created_by_user_id` | `VARCHAR(36)` FK `users.id` `ON DELETE SET NULL` | nullable |

Constraint `UNIQUE (user_id, organization_id)` (`uq_org_user_excl_pair`).

Modelo opt-out: una tabla vacía significa que el user accede a TODAS
las orgs del tenant. El admin agrega filas para excluir orgs puntuales
desde `/admin/users/{id}`.

**Pendiente (ENH separado):** falta el filtrado efectivo en queries de
proyectos, riesgos y minutas por orgs accesibles del user. Hoy solo se
almacena el dato.

### Tablas deprecated (US-077, borrado físico → US-081 Sprint 7)

`roles` y `user_roles` quedan presentes, pero **sin UI editor**: la
página `/admin/roles/*` y los endpoints de `admin_roles.py` se borran
en US-077. El gate ignora el JSON `Role.permissions` desde US-076. Las
tablas viven solo por compat, hasta validar Sprint 6 en producción.

### Migración futura prevista — **0030** (US-081, Sprint 7)

`DROP TABLE user_roles` + `DROP TABLE roles`. Sin downgrade real
(no se reconstruye la matriz JSON de permisos eliminada). Programado
para Sprint 7 tras 1-2 sprints de validación productiva del modelo
capability-based.

---

## EP020 Report Builder — visibility + scheduled custom (2026-05-25)

### Migración **0073** — `report_builder_templates` visibility (US-126)

Columnas nuevas en `report_builder_templates`:

| Campo | Tipo | Notas |
|---|---|---|
| `owner_id` | `VARCHAR(36)` FK `users.id` `ON DELETE SET NULL` | indexed (`ix_report_builder_templates_owner`) |
| `project_id` | `VARCHAR(36)` FK `projects.id` `ON DELETE CASCADE` | indexed |
| `visibility` | `VARCHAR(16)` NOT NULL DEFAULT `'private'` | `'private' \| 'project' \| 'tenant'` |

Reglas:
- `private`: solo el `owner_id` puede ver/modificar.
- `project`: todos los miembros del `project_id` la ven. Solo el owner
  publica/despublica.
- `tenant`: reservado, no usado en v1.0.
- Seeds (`is_seed=True`, `tenant_id=NULL`) siguen visibles para todos
  los users: no respetan visibility.

### Migración **0074** — `scheduled_reports.report_builder_template_id` (US-131)

| Campo | Tipo | Notas |
|---|---|---|
| `report_builder_template_id` | `VARCHAR(36)` FK `report_builder_templates.id` `ON DELETE SET NULL` | indexed (`ix_scheduled_reports_builder_template`) |

Cuando `scheduled_reports.report_type='custom'`, este campo apunta a
la plantilla del Report Builder. El worker
(`apps/api/app/workers/tasks/scheduled_reports.py`) invoca el motor
de US-123 (`render_template`) sobre la plantilla. Manda el HTML
resultante por `html_to_pdf`, antes de adjuntarlo al email vía Resend.
`REPORT_TYPES` se extiende a `("avance", "seguimiento", "custom")`.

---

## EP019 Minutas — generador unificado (2026-05-23)

### Migración **0075** — `meeting_minutes.origin` admite `'minute_ai'` (US-143)

Extiende el CHECK constraint `ck_meeting_minutes_origin` para incluir el
nuevo valor `'minute_ai'`. Sin cambio de tipo de columna.

| Valor | Significado |
|---|---|
| `manual` | POST normal o `source_type=manual` del generador unificado |
| `transcript_ai` | job de IA procesó un transcript |
| `minute_ai` | **nuevo**: job de IA normalizó una minuta YA redactada (US-143) |
| `import_file` | importada desde archivo |
| `import_paste` | pegada en bloque |

Sin backfill: solo abre el valor para futuras inserciones.

---

## BUG-063 — Re-seed idempotente de report_sections (2026-05-24)

### Migración **0076** — re-seed `report_sections` si está vacío

El owner reporta "el catálogo de secciones sigue vacío" en
`/pmo/projects/[id]/reports/builder`, tras el deploy del Sprint 26-32.
La migración 0070 (US-120) crea la tabla y debía sembrar 22 secciones,
pero las rows aparecen ausentes en su DB (posible reset post-deploy, o
`bulk_insert` sin commit).

La migración 0076 es **idempotente**: si `report_sections` ya tiene
rows, no hace nada. Si está vacía, inserta las 22 secciones canónicas
de EP020, con el mismo contenido que el seed original.

Sin cambio de schema, solo backfill de datos. Downgrade es no-op.

---

## BUG-063 — Cambios de shape JSON (sin migración) (2026-05-24)

Refactor del shape de `meeting_minutes.raid_suggestions` de:
```
{risks, issues, lessons, changes}
```
a:
```
{actions, risks, decisions, issues, lessons?, changes?, _meta?: {free_notes}}
```

- Buckets nuevos canónicos A/R/D/I, alineados con el modelo RAID.
- `lessons` y `changes` siguen aceptados por retro-compat con minutas
  existentes: el LLM ya no los genera, el validator los descarta.
- `_meta.free_notes` persiste las notas libres opcionales del PM
  (evita una migración de columna).

Sin migración de schema: la columna `raid_suggestions` es JSON. El
formatter (`minutes_formatter.py`) lee los 6 buckets. El frontend y el
endpoint aceptan ambos shapes en input.

`meeting_minutes.description` se reutiliza para el resumen de 2-3
oraciones (campo heredado de `_ModuleBase`, antes no usado por minute).

---

## US-151 — Fundación de datos analíticos / dashboards N1-N2 (2026-05-26)

### Migración **0079** — tabla `metric_snapshots`

Foto periódica (cadencia **semanal**, lunes 02:00 UTC vía Celery beat)
de las métricas de *stock* del portafolio, a los 4 niveles de scope
(`tenant` / `organization` / `program` / `project`). Sin historia
persistida no hay líneas de tendencia en los dashboards ni en los
reportes Nivel 1/2. Esta tabla es esa historia: desbloquea las
secciones S-05 (tendencia) y S-07 (curva-S), que EP020 había diferido
por falta de datos.

Columnas: `scope_type`, `scope_id`, `snapshot_date` + métricas escalares
(`projects_total/active`, `health_green/yellow/red`, `avg_progress`,
`budget_plan/actual`, `open_risks`, `severe_risks`, `open_issues`,
`changes_in_review`, `requests_in_review`, `tasks_total/done`,
`milestones_due_7/14/30`) y `extras` (JSONB, bolsa flexible para métricas
futuras sin migración). `UNIQUE(tenant_id, scope_type, scope_id,
snapshot_date)` garantiza idempotencia del job. FK `tenant_id` → `tenants`
con `ON DELETE CASCADE`. Downgrade hace `drop_table`.

Las métricas de *flujo* (cycle-time, throughput) NO viven aquí: se
calculan on-the-fly desde timestamps existentes
(`requested_at`/`approved_at`, etc.).

---

## BUG-068 — `organizations.logo_url` / `client_logo_url` → TEXT (2026-05-26)

### Migración **0082** — widen logo columns

`organizations.logo_url` y `client_logo_url` pasan de `String(500)` a
`Text`. Antes, subir un PNG (que se almacena como data-URL base64)
excedía los 500 caracteres y se truncaba o rechazaba: "subir PNG no se
guarda bien". Las URLs externas cortas sí cabían. Ahora ambas columnas
admiten data-URLs base64 de logos subidos directamente
(PNG/JPG/SVG/WEBP), además de URLs externas. El cap de longitud vive
en el schema Pydantic (`_LOGO_MAX = 3_000_000`, ~imagen de 2 MB
codificada). `alter_column` vía `batch_alter_table` (compat SQLite +
PG). Downgrade revierte a `String(500)`.

### Migración **0083** — `tenants.logo_url` → TEXT

Mismo problema en el logo del **tenant**. Antes se guardaba en disco
(efímero en Railway) y se servía por `GET /branding/tenants/{id}/logo`,
un endpoint autenticado que un `<img src>` del navegador no puede
consumir. Mandaba 401: el logo nunca se mostraba. Con URLs externas sí
funcionaba. Ahora el logo del tenant se guarda como **data-URL base64
en `tenants.logo_url`** y renderiza directo. La columna pasa de
`String(500)` a `Text`. El endpoint de serve se conserva por
retro-compat de logos viejos en disco. Las subidas nuevas ya no lo
usan. Downgrade revierte a `String(500)`.

---

## US-114 — Chat asistente tenant (EP008, 2026-05-28)

### Migración **0084** — `assistant_conversations` + `assistant_messages`

Tablas para el historial persistente del chat IA por tenant/usuario:
- `assistant_conversations`: id, tenant_id, user_id, title, created_at, updated_at
- `assistant_messages`: id, conversation_id, role (user/assistant), content, created_at

Índices en `tenant_id`, `user_id`, `conversation_id`.

---

## US-167 — UserScopeAssignment (EP001, 2026-06-08)

### Migración **0085** — `user_scope_assignments`

Tabla de asignaciones de visibilidad positivas para usuarios PM (`role_type='user'`):
- `id` PK, `tenant_id` FK→tenants CASCADE, `user_id` FK→users CASCADE
- `scope_type` VARCHAR(16): `'organization'` | `'program'` | `'project'`
- `scope_id` VARCHAR(36): FK lógico (sin constraintDB) al recurso correspondiente
- `created_at`, `created_by_user_id` FK→users SET NULL

Unique constraint `(user_id, scope_type, scope_id)`.
Índices en `tenant_id`, `user_id`, `scope_id`.
Admin y pm_sr ignoran esta tabla (always-visible).
Herencia: org → todos sus programas + proyectos. program → proyectos +
org contexto. project → proyecto + org + program contexto.

---

## US-171 — tasks.closed_at (EP009, 2026-06-28)

### Migración **0086** — `tasks.closed_at`

Columna `closed_at DATE NULL` en `tasks`: fecha de cierre **real** de la
actividad (editable por el PM). Lógica de atraso:
- Tarea NO completada → retrasada si `end_date < hoy`.
- Tarea completada → retrasada sólo si `closed_at > end_date` (cerró tarde).
- Sin `closed_at`, una tarea completada no se considera retrasada.

El endpoint auto-setea `closed_at = hoy` al pasar a `completed` sin
fecha provista. El PATCH permite editarla (incluye `null` para
limpiar). Nullable, sin backfill: las tareas completadas legacy
quedan sin fecha, y no se consideran retrasadas.

---

## ENH-177 — issues.category (EP006, 2026-06-28)

### Migración **0087** — `issues.category`

Columna `category VARCHAR(100) NULL` en `issues`, en paralelo a
`risks.category` ya existente, para clasificar acciones / incidencias /
decisiones (alineación de campos RAID). Nullable, sin backfill.

---

## US-176 — tasks.position (EP009, 2026-06-28)

### Migración **0088** — `tasks.position`

Columna `position INTEGER NULL` + index `ix_tasks_project_position
(project_id, position)`. Orden manual del plan (drag por fila). Null = sin
reordenar → orden natural por WBS (comportamiento actual). Cuando hay
posiciones, mandan sobre el WBS tanto en `list_tasks` como en `renumber-wbs`.
El endpoint `POST /projects/{id}/tasks/{id}/move {after_id}` normaliza
`position` secuencial de todo el proyecto. Nullable, sin backfill.

---

## US-179 — RAID estados a 4 + detención (EP006, 2026-06-29)

### Migración **0089** — `risks`/`issues` on_hold + remap de estados

Agrega a `risks` e `issues`:
- `on_hold_reason VARCHAR(2000) NULL` — razón de detención (obligatoria al
  pasar a `on_hold`).
- `on_hold_area_id VARCHAR(36) NULL` (FK `areas`, SET NULL) — área de la que
  depende la detención.
- `on_hold_actor_id VARCHAR(36) NULL` (FK `actors`, SET NULL) — responsable
  de la dependencia.
- `on_hold_since DATE NULL` — fecha desde la que está detenido (el server la
  setea al entrar a `on_hold`, para calcular el tiempo detenido).

**Data migration (remap de estados a los 4 canónicos** `open | in_progress |
on_hold | resolved`**):**
- Risks: `identified`→`open`; `analyzing`/`mitigating`→`in_progress`;
  `materialized`/`closed`→`resolved`.
- Issues: `closed`→`resolved` (`open`/`in_progress` ya válidos).

El downgrade quita las columnas pero NO revierte el remap: hay
pérdida de datos. `materialized` y `closed` se fundieron en `resolved`.

---

## US-177 — rename sección S-17 Atrasadas (EP009, 2026-06-29)

### Migración **0090** — `report_sections` S-17 rename

`UPDATE report_sections SET name = 'Atrasadas' WHERE code = 'S-17' AND name
= 'Retrasadas'` (la tabla usa `code`, no `folio`). Alinea el catálogo del
Report Builder con el renombre de terminología (Retrasada → Atrasada). Es
idempotente. El downgrade revierte.

---

## US-180 — Salud única híbrida (EP004/EP005, 2026-07-08)

### Migración **0091** — `projects` health unificado

**Columnas nuevas en `projects`:**
- `health_source VARCHAR(8) NOT NULL DEFAULT 'auto'` (check `auto|manual`):
  fuente del semáforo. `auto` lo mantiene el motor de reglas
  (`services/project_health.py`). `manual` = declarado por el PM.
- `health_reason VARCHAR(2000) NULL` — razón de la declaración manual
  (obligatoria vía API al declarar amarillo/rojo).

**Data migration:** donde `status_rag` estaba seteado (ENH-101), pasa a
ser el semáforo efectivo: `health_status = status_rag` (con
`amber`→`yellow`) y `health_source = 'manual'`.

**Drop:** `projects.status_rag` + check `ck_projects_status_rag`. La
dualidad semáforo manual vs RAG declarado se unifica en un solo
semáforo.

El downgrade re-crea `status_rag` solo para los overrides manuales
(`yellow`→`amber`), y dropea las columnas nuevas (pierde la razón).

---

## US-182 — Actors como pool de recursos con capacidad (EP017, 2026-07-08)

### Migración **0092** — `actors` resource pool

**Columnas nuevas en `actors`:** `organization_id` (FK organizations, SET
NULL; NULL = tenant-global), `resource_type` (check: cliente_negocio |
cliente_it | e4_pmo | e4_tecnologia | vendor_externo), `portfolio_function`
(check: pm|pmo|arquitectura|infraestructura|aplicaciones|datos|seguridad|
integraciones|negocio|change|testing|vendor), `seniority` (junior|mid|
senior|lead), `scarcity_level` (alta|media|baja), `location`,
`skills_tags JSON DEFAULT []`, `nominal_capacity_pct NUMERIC(5,2) DEFAULT
100`, `project_capacity_pct NUMERIC(5,2) DEFAULT 100` (capacidad REAL para
proyectos — base de la saturación), `is_key_resource BOOL DEFAULT false`,
`is_shared_resource BOOL DEFAULT true`, `fte_cost_rate NUMERIC(10,2) NULL`.
Índices: `(tenant_id, resource_type)` y `(tenant_id, organization_id)`.
Sin backfill: actores existentes quedan "sin clasificar" (NULL) con
capacidad 100/100.

---

## US-183 — Asignaciones con FTE% + motor de saturación (EP017, 2026-07-08)

### Migración **0093** — `project_participations` allocation

**Columnas nuevas en `project_participations`:** `allocation_pct
NUMERIC(5,2) NULL` (FTE% asignado; NULL = sin cuantificar, no suma
saturación), `assignment_type` (check: directa|advisory|backup|
shared_service|steerco_only, default directa), `status` (check:
tentativa|activa|cerrada|cancelada, default activa — solo 'activa' suma
demanda), `is_critical BOOL DEFAULT false`, `phase VARCHAR(32) NULL`.
**Backfill:** `status='cerrada'` donde `is_active=false`.

La saturación se calcula en `services/capacity.py`: la demanda es la
suma de `allocation_pct` de participations activas que intersectan la
ventana (today/week/3weeks/month), contra `actors.project_capacity_pct`
(US-182). Los umbrales por tenant viven en `settings.capacity_thresholds`
(yellow_over=0, red_over=10 puntos). Endpoints: `/capacity/summary`,
`/capacity/conflicts`, `/projects/{id}/resource-load`. Activa la
dimensión "recursos" del semáforo (US-180).

---

## US-185 — Memoria de proyecto para IA (EP008, 2026-07-08)

### Migración **0094** — tabla `project_ai_contexts`

Tabla nueva 1:1 con `projects` (unique en project_id): `context_md`
(contexto/glosario/reglas curado por el PM), `instructions_md`
(instrucciones permanentes de generación), `auto_summary_md` (resumen
acumulativo mantenido por IA al guardar minutas) +
`auto_summary_updated_at`, `updated_by`, timestamps. FKs CASCADE a
tenants/projects. Se inyecta como bloque `<CONTEXTO_DEL_PROYECTO>` en
minutas (worker `_run_minute`) y en reportes (`/reports/ai-generate`).
El resumen lo actualiza la task Celery `ai.update_project_context`.

---

## BUG-091 — Barrido de estados RAID legacy (EP006, 2026-07-18)

### Migración **0095** — data-only, sin cambios de schema

Re-aplica el remap de estados de la 0089 (US-179), de forma
idempotente. El flujo de minutas IA seguía creando riesgos con
`status='identified'` después del remap original, y esos riesgos
quedaban ineditables (422 al guardar). El fix de código corrige el
origen: `modules.py` crea con `open`, y suma un validator Pydantic
tolerante a legacy en create/update. Esta migración limpia las filas
ya existentes.

---

## US-191 — Evaluación de salud 5+1 con historial (EP004/EP005, 2026-07-18)

### Migración **0096** — tabla `project_health_evaluations`

Evaluación periódica del PM: 5 dimensiones (schedule/budget/risks/
decisions/resources, nullable) más `overall` (la "sexta", obligatoria),
con `evaluated_at` (fecha libre) y `note`. Cada guardado es un registro
histórico: registra la evolución de la salud en el tiempo. El
`overall` se aplica al semáforo del proyecto
(`health_status/source/reason`) como declaración manual (US-180), y
convive con el motor automático. Índice (project_id, evaluated_at).
FKs CASCADE a tenants/projects, SET NULL a users.

---

## AM-08 / MCS SEG-07 — `audit_log` de solo anexado (2026-08-05)

### Migración **0097** — disparadores de inmutabilidad sobre `audit_log`

**No cambia el schema.** No toca columnas, índices ni claves. Añade dos
disparadores y una función, y revoca privilegios. Se indexa aquí porque
cambia lo que se puede *hacer* con la tabla. Eso es lo que sorprende a
quien escriba código contra ella.

`audit_log` era una tabla ordinaria. **AM-06 se apoya en ella como
único control.** Ahora rechaza `UPDATE`, `DELETE` y `TRUNCATE`.

**Por qué disparadores y no solo `REVOKE`**, que es lo que proponía el
modelo de amenazas. En Railway, la aplicación se conecta con el rol
dueño de las tablas. En PostgreSQL, el dueño conserva sus privilegios
pase lo que pase con el `REVOKE`. Verificado contra Postgres 16: con
`REVOKE UPDATE, DELETE` aplicado al dueño, el `UPDATE` pasa igual. Con
el disparador puesto, no pasa ni siendo superusuario.

El `REVOKE` a `PUBLIC` se aplica igual: cuesta una línea. Empieza a
sumar valor el día que la aplicación deje de conectarse como dueño,
que es lo correcto.

**Lo que no detiene:** quien administra la base puede quitar el
disparador. Es una defensa contra la aplicación: contra un fallo que
permita ejecutar SQL con sus credenciales, y contra el borrado
accidental. Cerrar el resto exige encadenamiento por hash o envío a un
almacén externo. Es otra decisión.

**Reversible.** El `downgrade` deja la tabla como estaba. Se verificó
contra Postgres real, no solo por lectura.

**Fuera de PostgreSQL no hace nada.** La suite corre en SQLite, y ahí
el control lo pone el guardián del ORM en `app/models/audit.py`. Cubre
el camino de la aplicación, pero no las sentencias masivas. Esa
división está escrita en los dos sitios, y comprobada en
`tests/test_am08_auditoria_solo_anexa.py`.


---

## D-2 / ADR-019 — la fase `support` pasa a `hypercare` (2026-08-05)

### Migración **0098** — renombrado de valor en `projects.phase` y `lessons_learned.phase`

**Sin cambio de esquema.** Las dos columnas son `String(32)`, sin
`CHECK` ni enum. Por eso esto es una migración de datos: `UPDATE … SET
phase='hypercare' WHERE phase='support'`. Es la razón por la que
ADR-019 la clasificó de coste medio.

**Dos tablas, y la segunda es fácil de olvidar.** `lessons_learned.phase`
comparte vocabulario con `projects.phase` (`LessonPhase` en el frontend).

**La ventana de compatibilidad no está en la migración**, está en
`schemas/project.py`. El API sigue aceptando `support` a la entrada, y
lo normaliza a `hypercare`. Así, un cliente que no se haya
actualizado —una pestaña abierta, un filtro guardado— no se rompe. La
salida es siempre canónica. Hacen falta las dos mitades: una sin la
otra deja medio producto hablando el idioma viejo.

**Reversible, con una salvedad honesta.** Ejercitada contra Postgres
16: sube y baja sin tocar el resto de fases ni los nulos. Lo que la
bajada no puede distinguir es una fila que ya fuera `hypercare` de una
renombrada. Antes del 2026-08-05 ese valor no existía en el
vocabulario, así que con datos reales no pasa.


---

## D-8 / ADR-021 — `portfolio_function` pasa a `discipline` (2026-08-05)

### Migración **0099** — renombrado de columna en `actors`

`ALTER TABLE actors RENAME COLUMN portfolio_function TO discipline`, vía
`batch_alter_table`. Así SQLite —donde corre la suite— lo resuelve
recreando la tabla. Los **valores no cambian**: `String(24)` sin `CHECK`.

El glosario veta «portafolio» para un área (brecha B-6). Un portafolio
es un conjunto de proyectos y programas: esa entidad no existe en el
producto. Lo que la columna guarda es la disciplina del recurso.

**Ventana de compatibilidad en dos puertas**, porque el nombre era público:

- el cuerpo de creación acepta `portfolio_function` vía `AliasChoices`.
- el parámetro de consulta de `GET /actors` lo acepta, marcado `deprecated`.

La **salida es siempre `discipline`**. La clave de agregación de
capacidad pasa de `by_function` a `by_discipline`, para no reabrir el
mismo desajuste.

**Reversible**, ejercitada contra Postgres 16: sube, baja y los datos
—incluidos los nulos— quedan intactos en los dos sentidos.

---

## Migración 0100 — `tasks.wbs` → `tasks.wbs_code` (D-3 / ADR-020)

`ALTER TABLE tasks RENAME COLUMN wbs TO wbs_code`, vía `batch_alter_table`,
por la misma razón que 0099. **No toca datos**: `String(64)` sin `CHECK`
ni índice.

La columna guardaba el **código** de la EDT (`1.2.3`), no la
estructura: esa vive en `parent_id` y `outline_level`. El propio
modelo lo delataba: documentaba «predecessors / successors como JSON
array de **wbs_code**», mientras la columna se llamaba `wbs`.

**`predecessors` y `successors` no se migran.** Son listas JSON de
códigos, no claves foráneas: su contenido es el mismo antes y después.
Lo que sí se revisó, en el mismo commit, es todo el código que las
cruzaba contra `task.wbs`.

**La palabra «WBS» no se retira, y ahí está la parte delicada.** Sigue
igual en:

- la cabecera `WBS` del Excel que descarga y sube el usuario (`plan-template.ts`).
- los alias que el importador acepta como cabecera (`wbs`, `edt`, `código`…).
- los códigos de diagnóstico `WBS_MISSING`, `WBS_DUPLICATED`, `WBS_ORPHAN_LEVELS`,
  `WBS_GAPS`, `WBS_NUMERIC_GENERAL`.
- el elemento `<WBS>` de MS Project y la clave `wbs` del JSON de MPXJ.
- la ruta `POST /projects/{id}/tasks/renumber-wbs`.
- la clave `plan-wbs-level:<id>` de `localStorage`: guarda el nivel de
  agrupación. Renombrarla habría reseteado la preferencia de todo el
  mundo, sin un solo error.

**Ventana de compatibilidad** en las dos puertas del cuerpo —`TaskCreate`
y `TaskUpdate`— vía `AliasChoices`. La del PATCH importa más de lo que
parece: sin alias, mandar `wbs` no fallaría. Simplemente **no cambiaría
nada**.

La salida es siempre `wbs_code`. Se cuenta por `compat.nombre_viejo`.

**Reversible**, ejercitada contra el esquema real de `Base.metadata`:
sube, baja y el código sobrevive en los dos sentidos.

---

## 0101 — `task_load_thresholds.amber_max` → `yellow_max` (DAT-06 / ADR-030)

**No es una columna.** Es una llave dentro del JSON de
`tenants.settings`, en el bloque `report_builder`. La migración lee
las filas, reescribe el diccionario en Python y actualiza. **SQL
portable a propósito:** la suite corre sobre SQLite, y `jsonb_set`
solo existe en Postgres. Una migración que solo corre en un motor se
descubre recién en producción.

Toca **solo** las filas que tienen el bloque. Reescribir las demás
ensuciaría el `updated_at` de medio producto, sin cambiarles nada.

**Ventana de compatibilidad** en `core/compatibilidad.py`, con una
diferencia respecto a las tres anteriores: cubre la **lectura**,
además de la entrada. Un inquilino restaurado de una copia anterior al
despliegue traería la llave vieja. Perder su umbral en silencio sería
peor que aceptarlo. El semáforo de carga caería a los valores por
defecto. Nadie lo notaría hasta ver un informe con los colores
cambiados.

Lo que se **guarda** es siempre `yellow_max`. Si el guardado volviera
a escribir el nombre viejo, la migración se desharía sola con el
primer cambio de ajustes.

**Reversible**: `downgrade` hace el camino inverso sobre los mismos datos.

---

## `20260806_0102` — `audit_log.actor_type` (MCS IA-02)

Columna nueva: `actor_type VARCHAR(16) NOT NULL DEFAULT 'humano'`, más el índice
`idx_audit_actor_type_time (actor_type, occurred_at)`.

**Qué problema resuelve.** IA-02 pide que una acción ejecutada por un
componente de IA quede registrada, **y sea distinguible de una acción
humana**. Lo primero ya se cumplía: la IA sí escribía en `audit_log`.
Lo segundo no. Los tres campos que parecían servir no servían:

- `module="ai"` significa «el módulo de IA», no «lo hizo la IA».
  `report.send` es una persona pulsando enviar, y también lo lleva.
- El prefijo `ai.` en el nombre era inconsistente: `ai.minute.generate`
  lo tiene, y `report.draft` —que redacta el modelo— no lo tiene.
- `user_id`, en una acción de IA, guarda **quién la pidió**.
  Atribuirle el texto generado a esa persona es justo lo que el
  requisito evita.

**Las filas existentes quedan en `humano`, y es la lectura correcta**,
no una comodidad. Hasta esta migración, el producto no tenía forma de
que el modelo actuara sin que alguien lo pidiera. Lo que no se puede
reconstruir hacia atrás es cuáles de esas peticiones acabaron en texto
generado. Por eso la distinción se guarda desde ahora, en vez de
inferirse.

**`server_default` y no `default`.** `audit_log` es de solo anexado
desde la 0097: hay disparadores que rechazan `UPDATE` y `DELETE`. Una
migración que rellenara la columna fila a fila chocaría con ellos. El
`server_default` lo resuelve en la definición de la columna, sin tocar
una sola fila. Hay un caso que lo vigila (`test_ia02_auditoria_ia.py`).

**El valor por defecto es seguro, pero no es el control.** Son 144
sitios de escritura, y casi todos son humanos. Lo que impide que una
ruta de IA nueva se registre como humana es el trinquete. Barre por
**ubicación** —cualquier `write_audit` en código que ejecuta el
modelo— y por **nombre** —cualquier acción `ai.*`—. Las dos reglas
juntas: la de ubicación caza `report.draft`, que no lleva el prefijo.
La de nombre caza un `ai.*` en un módulo que nadie añadió a la lista.

**Ejercitada contra Postgres real** con una fila de historia previa.
Queda en `humano` sin reescribirse. El índice se crea. `downgrade`
deja la tabla como estaba.

**Reversible**: `downgrade` quita índice y columna. Se pierde la
distinción de lo registrado mientras estuvo. Es inevitable, y no
destruye ningún otro dato.

---

## `20260806_0103` — `metric_snapshots.avg_progress` admite nulo (MCS DAT-09)

`ALTER COLUMN ... DROP NOT NULL` sobre una columna `NUMERIC(5,2)`. Sin datos que
convertir y sin índices que tocar.

**Por qué.** La columna era `NOT NULL DEFAULT 0`. El recolector diario
no tenía dónde escribir «no hay proyectos activos»: guardaba `0`, el
mismo valor que significa «la cartera está al 0 %».

La ficha del indicador, firmada por el owner el 2026-08-06, dice lo
contrario: «Sin proyectos → `null`, que se pinta «—». **Cero
proyectos no es cero por ciento**». El tablero en vivo se corrigió ese
día. La instantánea no: calculaba el mismo indicador con su propia
división, el defecto que DAT-09 describe. Consecuencia visible: la
gráfica de tendencia de los informes lee instantáneas y **dibujaba
una caída a cero** en carteras recién creadas.

**Nulable y no centinela.** Un `-1` vuelve a ser un número que alguien
promedia. `NULL` no se promedia por accidente.

**Los ceros históricos NO se convierten.** Un `0` ya guardado puede
significar las dos cosas: no hay forma de saber cuál. Reinterpretarlos
hacia atrás sería inventar datos. Desde esta migración, los nuevos
distinguen. Los viejos siguen siendo ambiguos, y así se quedan.

**Reversible, con pérdida declarada.** `downgrade` rellena los nulos
con `0` y vuelve a `NOT NULL`. No pierde filas, pero **sí pierde la
distinción**: los «no hay proyectos» vuelven a ser ceros
indistinguibles. Está escrito en el `downgrade()`, porque el runbook
de DES-02 §3.3 manda leerlo antes de bajar.

---

## `20260807_0104` — `currency` en proyectos y solicitudes (BUG-092)

`ADD COLUMN currency VARCHAR(3) NULL` en `projects` y en `project_requests`.
Sin datos que convertir, sin índices y sin restricción de valores.

**Por qué.** `tenant.settings.currency` ofrecía MXN, USD y EUR, pero
**el formulario que la guardaba era el único sitio que la leía**. Las
diez superficies que muestran dinero traían `currency: "MXN"` escrito.
Un inquilino en dólares —el propio sembrado crea uno— veía sus
importes rotulados en pesos. El número no estaba mal. La unidad era
mentira, y en un importe eso es lo mismo que estar mal.

Decisión del owner (2026-08-07): la preferida se queda a nivel de
inquilino como **valor inicial**, y la moneda efectiva la elige cada
**proyecto**. La solicitud también la lleva, porque su importe
precede al proyecto.

**Nulable, y el nulo significa algo:** no es «sin moneda», es «la que
diga el inquilino». Rellenar las filas existentes con `MXN` habría
congelado la respuesta de hoy. Habría roto justo lo que se viene a
arreglar: quien cambie su preferida espera que sus proyectos sin
elección la sigan.

**Sin `CHECK` de valores.** La lista admitida vive en
`app/dominio/moneda.py`. Una restricción de columna obligaría a una
migración por cada moneda nueva. El conjunto lo valida el esquema
Pydantic en la frontera.

**Reversible, con pérdida declarada.** `downgrade` quita la columna:
no pierde filas, pero **sí la elección**. Los proyectos que hubieran
escogido una moneda distinta de la preferida vuelven a mostrarse con
la del inquilino. Está escrito en el `downgrade()`, porque el runbook
de DES-02 §3.3 manda leerlo antes de bajar.

---

## 0105 — Consentimiento del aviso de privacidad (ASVS 8.3.3)

`users.privacy_accepted_at` y `users.privacy_version`, las dos nulables.

**Dos columnas y no una.** Con solo la fecha, «aceptó» responde
*cuándo*, no *qué*. El día que cambie lo que se recoge, no habría
forma de saber a quién preguntarle de nuevo sin cruzar fechas a mano
contra el historial del documento. Con la versión al lado, la
pregunta se responde comparando contra `aviso_privacidad.VERSION`. Por
eso la pantalla puede volver a salir sola cuando el aviso cambia, que
es lo que pidió el owner.

**El nulo significa algo.** Las cuentas anteriores al aviso no
aceptaron nada. Rellenarlas con la fecha de la migración habría
fabricado un consentimiento que nadie dio: justo lo que el control
quiere impedir. Verán la pantalla al entrar, que es lo correcto.

Al bajar se pierde el consentimiento registrado, y todo el mundo
vuelve a verla. Es molesto y es lo correcto: conservarlo fuera de la
columna para «restaurarlo» sería inventar un consentimiento a partir
de algo que el esquema ya no modela.

## 0106 — Códigos de segundo factor de administración (ASVS 4.3.1)

Tabla `admin_otp_codes`. Decisión del owner en ADR-035.

**Tabla propia y no columnas en `users`**, porque un código es un
hecho con vida corta, no un atributo de la persona: nace, caduca a
los diez minutos y se consume. En `users` habría que limpiar a mano lo
que aquí caduca solo.

Se guarda el **resumen** del código, no el código. Seis dígitos no
resisten una tabla precalculada: el resumen no protege de eso.
Protege de que un volcado de la base entregue códigos utilizables tal
cual, que es el caso realista.

`desafio` ata el código a **una** petición de inicio de sesión
concreta (ASVS 2.7.3). Sin él, un código pedido en una pestaña
serviría para completar el inicio de sesión que otra persona empezó
en otra parte. `intentos` acota la fuerza bruta: un millón de
combinaciones se prueban enteras en minutos.

Reversible, sin pérdida de nada que importe: lo único que se tira son
códigos con diez minutos de vida.

## 0107 — Equipos de confianza para el segundo factor (ASVS 4.3.1)

Tabla `dispositivos_confiables`. Decisión del owner en ADR-035
§Ventana: el código se pide una vez por equipo cada treinta días, no
en cada entrada. Pedirlo siempre es lo que hace que un control acabe
desactivado.

**Sigue habiendo dos factores dentro de la ventana.** La cookie es un
secreto de 256 bits que solo tiene ese navegador: «algo que tienes».
La contraseña sigue haciendo falta. Cambia el soporte del segundo
factor, no su existencia.

Se guarda **solo el resumen** del token. `user_id` no es decoración:
la comprobación exige que el resumen **y** la cuenta coincidan. Si no,
la cookie de un equipo de confianza de una cuenta saltaría el segundo
factor de otra. El flujo seguiría funcionando igual, así que nadie lo
vería.

`revocado` en vez de borrar la fila: el cambio de contraseña revoca
todos los equipos. Conviene poder ver después cuántos había y cuándo
se usaron.

Al bajar, todo el mundo vuelve a pasar por el código en su siguiente
entrada. Es molesto y seguro: el lado correcto por el que equivocarse
al revertir.

## 0108 — `portfolios`, y los programas se mudan dentro (US-198)

La jerarquía pasa de `organización → BU → departamento → programa →
proyecto` a `organización → portafolio ⊃ programa → proyecto`
(ADR-037). Tabla nueva `portfolios` por organización, más
`programs.portfolio_id` (NOT NULL) y `projects.portfolio_id`
(nullable).

**No hay migración de datos desde BU/departamento**, y eso es un dato:
el owner nunca los usó en producción. Un mapeo BU→portafolio habría
inventado una taxonomía a partir de tablas vacías. La migración
**cuenta** las referencias vivas de las siete columnas BU/departamento
y deja el conteo en el registro, para que US-199 las suelte con la
evidencia delante y no de memoria.

`programs.portfolio_id` nace nullable, se rellena y se endurece a NOT
NULL **en la misma migración**. Al revés no se puede: `SET NOT NULL`
sobre una columna con nulos falla. Y dejar el endurecimiento para
después es como se acumulan las columnas «temporalmente nullable» que
nunca se endurecen.

El relleno crea un **«Portafolio General» por organización que tenga
programas** — no uno global, que rompería el aislamiento entre
organizaciones, ni uno por organización, que sería basura en la
pantalla de quien nunca usó programas.

`projects.portfolio_id` se rellena **desde el programa**. Sin ese paso
la regla de consistencia de `services/jerarquia.py` nacería violada por
todos los proyectos existentes: tendrían programa y no tendrían su
portafolio.

Hay una rama por motor en el DDL. SQLite no sabe endurecer una columna
existente ni añadirle una restricción, y emularlo recrea la tabla —en
`projects`, reconstruir a mano su índice único y once claves ajenas—.
Lo que la rama se salta es lo que en SQLite ya está puesto por otro
camino (`create_all` la crea NOT NULL con su FK); lo que corre en los
dos motores es el **relleno**, que es donde una migración de datos se
equivoca.

Al bajar desaparecen la tabla y las dos columnas, y con ellas la
clasificación por portafolio que se hubiera capturado: el esquema
anterior no tiene dónde guardarla. Es destructiva de información nueva,
que es lo esperable en un `downgrade` que retira una entidad. Lo
anterior queda intacto: `programs.department_id`,
`projects.business_unit_id` y `projects.department_id` no se tocan
aquí.

## 0109 — se sueltan las columnas de BU/departamento (US-199)

La 0108 creó lo nuevo y no tocó lo viejo a propósito. Esta va con el
commit que retira sus lectores —los sub-routers de unidades de negocio
y departamentos, y los campos BU/departamento de los payloads de
solicitudes y actas—, así que aquí sí se sueltan.

**Se van** siete columnas: `programs.department_id`,
`projects.{business_unit_id, department_id}`,
`project_requests.{business_unit_id, department_id}` y
`project_charters.{business_unit_id, department_id}`.

**Llegan** cuatro: `project_requests.{portfolio_id, program_id}` y
`project_charters.{portfolio_id, program_id}`. La solicitud se clasifica
antes de que el proyecto exista; sin estas columnas el proyecto aprobado
nacería sin clasificación y habría que ponérsela otra vez a mano.

**Se quedan** las tablas `business_units` y `departments`. Retirar una
tabla entera es irreversible y va en W8, cuando el contador de compat
confirme que nadie la lee. Lo que esta oleada quita son las referencias.

La verificación de vacío no es ceremonia. «Nunca se usaron» es una
afirmación sobre **una** instalación: la migración cuenta antes de
soltar, y si encuentra filas **para**, con el conteo por columna en el
mensaje y el residuo anotado en `audit_log` como
`us199.residuo_bu_depto`. No borra ni convierte nada — una migración que
descarta datos que no esperaba es peor que una que se niega a correr.
El caso está ejercido en `tests/test_us199_portfolios_api.py`.

Hay rama por motor en las cuatro columnas nuevas, por lo mismo que en la
0108: SQLite no sabe añadir una restricción a una tabla existente, y en
SQLite esas claves ajenas ya llegan puestas por `create_all`.

La bajada devuelve las siete y quita las cuatro. **No devuelve los
valores** —ninguno, si la subida corrió—, que es la razón por la que la
subida se niega a correr con datos: después de soltar la columna ya no
hay a dónde volver.

## 0110 — el vocabulario de fases y tipos, al español (US-202)

`planning → preparacion`, `execution → ejecucion`, `closed → cerrado`,
`cancelled → cancelado` (ADR-038). **`hypercare` no se toca**: ADR-019 lo
renombró hace dos semanas y no tiene traducción que no sea peor. Y
`projects.type` deja el texto libre: `transformation → transformacion`,
`operation → operacion`, `innovation → innovacion`; `bau` ya estaba bien.

**Dos tablas con fase, no una.** `projects.phase` y `lessons.phase`
comparten vocabulario —la fase de una lección es «en qué fase se aprendió
esto»— y la segunda es la que se olvida: le pasó a la 0098, cuya primera
versión tocaba solo `projects`. La tercera, `project_participations.phase`,
queda fuera a propósito: es texto libre, no el vocabulario controlado, y
renombrar ahí sería editar lo que escribió un usuario.

**Los tipos que no están en el mapa se dejan como están**, con sus
valores y su conteo en el registro del despliegue. No se convierten a la
fuerza ni se vacían: adivinar que «Mejora continua» es `operacion` es
inventarse la clasificación de un proyecto de alguien, y vaciarlo es
perder el único dato que había. La columna sigue siendo texto, así que
esos valores se **leen** igual; lo que ya no se puede es volver a
escribirlos, porque el enum de la API los rechaza.

Cada `UPDATE` va acotado por valor viejo y no como un `CASE` sobre todas
las filas: reescribir filas que ya están bien les mueve el `updated_at`
sin haber cambiado nada. Es la lección de la 0101, y se verifica
contando sentencias (`tests/test_us202_vocabulario.py`).

La bajada es exacta: renombrados uno a uno, sin colisión —ninguno de los
nombres nuevos existía antes del 2026-08-19—. Lo único que no puede
distinguir es una fila que **ya** dijera `preparacion` de una que lo diga
por esta migración; el caso no se da con datos reales, pero conviene
saberlo antes de volver a subir tras una bajada parcial.

---

## 0111 — se borra `tenants.settings.org_label` (DEC-032)

No toca ninguna columna: la clave vive dentro del JSON de
`tenants.settings`, y lo que hace la migración es sacarla de ahí.

**Por qué hay migración para una clave de JSON.** Porque sin ella la clave
se queda escrita y sin lectores, y un `"org_label": "portfolios"` en
`settings` es una invitación a que alguien la vuelva a leer dentro de seis
meses sin saber por qué se retiró.

Y porque el conteo es la única forma de contestar la pregunta que importa:
**¿alguien la estaba usando?** El registro del despliegue dice cuántos
inquilinos la tenían y con qué valor. Si sale alguno con `"portfolios"`, ese
cliente va a ver el cambio de nombre en su interfaz y hay que avisarle; si
no sale ninguno, no hay nada que comunicar.

**Lee y reescribe fila por fila** en vez de usar un operador de JSON del
motor: los operadores de `jsonb` de Postgres (`settings - 'org_label'`) no
existen en SQLite, y esta migración se ensaya en la suite. El precio es
recorrer `tenants`, que es la tabla más pequeña del esquema.

**La bajada no repone el valor.** No queda dónde haberlo guardado, y una
tabla de residuo para una etiqueta de interfaz es peor que el problema. Lo
que deja la bajada es la clave ausente, que es exactamente lo que el
accesor viejo interpretaba como el default «organizations»: para un dato de
presentación con default, «ausente» y «restaurado al default» son el mismo
estado visible. Si hubiera que reponer un inquilino concreto a mano, el
conteo de la subida está en el registro.

---

## 0112 — `raci` e `is_key_stakeholder` en participaciones (US-217)

Dos columnas en `project_participations` y un índice:

| Columna | Tipo | Nulo | Por qué |
|---|---|---|---|
| `raci` | `VARCHAR(1)` | sí | `A`/`R`/`C`/`I`. Nulable porque estar en un proyecto sin papel declarado es el estado normal de la mayoría de las participaciones |
| `is_key_stakeholder` | `BOOLEAN NOT NULL DEFAULT false` | no | Marca de interés, no de responsabilidad: `false` es una respuesta, no un hueco |

Índice `ix_participations_project_raci` sobre `(project_id, raci)`. La consulta
que importa es «¿quién es la A de este proyecto?», y se hace una vez por cada
guardado de papel para validar la unicidad.

**La unicidad de la A no está en el esquema, y es a propósito.** Expresarla
requeriría un índice único parcial (`UNIQUE (project_id) WHERE raci = 'A'`), que
Postgres soporta y SQLite no. La suite corre sobre SQLite: una restricción que
solo existe en producción es una restricción que nadie prueba, y la primera vez
que se entera alguien es con un 500 en vez de un mensaje. Vive en la frontera de
la API (`app/dominio/raci.py`), donde además puede nombrar a quien ya la tiene.

**La bajada suelta el índice antes que las columnas.** No es cosmético: en
Postgres, soltar una columna se lleva en silencio todo índice que dependa de
ella, así que un `drop_index` después del `drop_column` muere con «index does not
exist». Es el fallo que la 0109 dejó en el CI del 2026-08-19. Ahora lo vigila un
trinquete sobre **todas** las revisiones
(`tests/test_dat_indices_antes_de_columnas.py`), no solo sobre esta.

**Verificada en los dos sentidos** sobre SQLite en memoria antes de pushear —
subida, fila preexistente con `raci = NULL`, bajada, fila intacta. Usa
`batch_alter_table` porque SQLite no tiene `ALTER` en sitio.

---

## 0113 — `plan_baselines` y `plan_baseline_tasks` (US-212 / D-6)

Dos tablas nuevas. Cierra la brecha B-1: sin línea base, «desviación»,
«retraso» y «sobrecosto» son palabras sin referente.

| Tabla | Qué guarda |
|---|---|
| `plan_baselines` | La captura: nombre, nota, `captured_at`, quién, y cuántas tareas tenía el plan |
| `plan_baseline_tasks` | Una fila por tarea retratada: `task_id`, código EDT, nombre, fechas, duración, si era hito |

Índices: `(tenant_id)`, `(project_id)` y `(project_id, captured_at)` en la
madre —el listado siempre pide «las de este proyecto, la más reciente
primero»—, y `(baseline_id)` en la hija.

**Dos tablas y no dos columnas en `tasks`.** `baseline_start`/`baseline_end`
junto a las fechas vivas es más barato y solo aguanta **una** línea base: la
segunda captura pisa la primera, y con ella el histórico de replanificaciones
—que es justo lo que un comité de cambios pide ver—.

**`plan_baseline_tasks.task_id` no lleva clave ajena, a propósito.** Una línea
base es una foto: si la tarea se borra del plan, su fila en la foto tiene que
seguir ahí. Con `CASCADE` desaparecería y la promesa se encogería
retroactivamente —parecería que nunca se prometió esa tarea, que es la dirección
cómoda de mentir—; con `SET NULL` la fila sobreviviría sin emparejamiento y se
contaría como una promesa anónima. Mismo criterio que `metric_snapshots.scope_id`.
Por eso también se copian `wbs_code` y `name`: la fila tiene que poder leerse
cuando lo que retrataba ya no existe.

**`captured_by_user_id` tampoco lleva clave ajena.** Borrar un usuario no puede
borrar la trazabilidad de una promesa; el nombre se resuelve al leer, si existe,
y queda en `null` si no.

**No captura ninguna línea base automáticamente**, y es la decisión más
importante de esta migración. Hacerlo inventaría una promesa que nadie hizo, con
la fecha de hoy, y todo proyecto aparecería con desviación cero. La ausencia de
línea base es un estado que la interfaz **dice** (MCS DAT-12), no uno que se
rellena.

**La bajada** suelta los índices antes que sus tablas y la hija antes que la
madre. Destruye las capturas: no hay dónde guardarlas, y eso es lo esperable en
un `downgrade` que retira una entidad. Verificada en los dos sentidos sobre
SQLite en memoria antes de pushear.

---

## 0114 — costo-snapshot en participaciones + unidad de la tarifa (US-215)

Cuatro columnas en `project_participations` y una en `actors`. Ningún índice.

| Tabla | Columna | Por qué |
|---|---|---|
| `project_participations` | `cost_rate_snapshot NUMERIC(12,2)` | La tarifa, copiada del catálogo y nunca recalculada |
| | `cost_currency VARCHAR(3)` | Un importe sin moneda es una unidad mentida (BUG-092) |
| | `cost_rate_period VARCHAR(8)` | `hora`/`dia`/`mes`. Sin la unidad de tiempo el número no significa nada |
| | `cost_rate_captured_at TIMESTAMPTZ` | Distingue la tarifa tomada al asignar de una recongelada después |
| `actors` | `cost_rate_period VARCHAR(8)` | La unidad de `fte_cost_rate`, que existía sin ella desde US-182 |

**El defecto que arregla.** `actors.fte_cost_rate` guarda la tarifa de hoy. Si
en marzo alguien la sube, el costo del trabajo de enero cambia solo y el gasto
acumulado del proyecto se reescribe hacia atrás. Es el mismo problema que la
0113 resuelve para las fechas: la historia no se mueve.

**Por qué el periodo entra ahora.** Mientras nadie calculaba nada con
`fte_cost_rate`, su ambigüedad no costaba: era un número que una persona leía y
sabía interpretar. Al derivar un costo se vuelve el dato más importante del
cálculo — multiplicar una tarifa mensual por los días de la asignación da un
número 21 veces mayor que el real, con toda la apariencia de un dato bueno.

**Ninguna columna se rellena, y esa es la decisión.** Sería fácil y sería un
error en las dos:

- **El periodo con `mes` por defecto** inventaría la unidad de tarifas que
  alguien capturó pensando en horas.
- **La tarifa desde el catálogo** —el borrador de W4 lo proponía con la salvedad
  escrita— fecharía hoy una tarifa que quizá se pactó hace un año, y quedaría
  registrada como si fuera la del momento de asignar.

Un `NULL` dice «no se congeló», que es la verdad y es accionable: la interfaz
ofrece congelarla en un clic. Un `NULL` en cualquiera de las cuatro significa
«no hay costo calculable», no cero (MCS DAT-12), y el total del proyecto viene
acompañado de cuántas asignaciones quedaron sin tarifa.

**La bajada** suelta las columnas y con ellas las tarifas congeladas. Es
información nueva sin sitio en el esquema anterior. `actors.fte_cost_rate` no se
toca: existía antes. Verificada en los dos sentidos sobre SQLite en memoria, con
filas previas, antes de pushear: sobreviven intactas y las columnas nuevas nacen
nulas.

---

## 0115 — `user_tenant_memberships` (US-214 / AM-16)

Una tabla y un índice. Es un cambio de **seguridad** antes que de modelo, y el
análisis de amenazas se escribió antes de la migración (CLAUDE.md §0.3): está en
`modelo-amenazas.md` como **AM-16**.

| Columna | Por qué |
|---|---|
| `user_id`, `tenant_id` | La pareja, con unicidad `(user_id, tenant_id)` **sin importar el estado** |
| `granted_by_user_id` | Quién la concedió. Sin clave ajena: borrar a quien la concedió no debe borrar la traza |
| `revoked_at`, `revoked_by_user_id` | Se **marca** en vez de borrar la fila |

Índice `ix_membership_user_tenant` sobre `(user_id, tenant_id)`: es la consulta de
**cada petición autenticada**.

**Por qué la unicidad ignora el estado.** Dos filas para la misma pareja —una
revocada y otra viva— obligarían a decidir cuál manda cada vez que se lee, y esa
es una decisión que no hace falta tomar. Conceder sobre una revocada la reactiva.

**Por qué se marca y no se borra.** «¿Quién tuvo acceso a este cliente y cuándo se
le quitó?» no se contesta con una fila borrada, y es exactamente la pregunta de
una auditoría.

**Sí hay relleno, al contrario que en la 0114.** La migración siembra una
membresía por cada usuario con `tenant_id`. No es inventar un dato: el inquilino
de origen **es** la membresía, y sin la siembra la tabla diría que nadie pertenece
a nada — con la comprobación por petición puesta, eso deja a todo el mundo fuera.
La diferencia con la 0114 es qué se sabe: allí la tarifa del catálogo no era la
del momento de asignar, así que copiarla fechaba hoy una cifra de hace un año.
Aquí no hay nada que suponer.

**`users.tenant_id` no se toca.** Sigue siendo el inquilino de origen. La
membresía añade inquilinos; no reemplaza el de origen.

---

## 0116 — FKs de `tenant_id` faltantes (US-240 / ADR-003)

Primer paso de la oleada **W3** (RLS de Postgres, `reestructura-modelo-datos.md`
§8): antes de activar RLS por tabla hace falta que **toda** tabla tenant-scoped
tenga un FK real de `tenant_id` a `tenants.id`. Una policy `USING (tenant_id =
current_setting('app.tenant_id', true))` confía en el valor de la columna tal
cual está — si puede apuntar a un tenant inexistente, la policy no lo detecta.

No agrega columnas ni tablas: solo el `ForeignKey` que faltaba en 13 tablas que
ya tenían la columna sin protección — `change_approvers`, `approval_tokens`
(`ON DELETE CASCADE`), `plan_baselines`, `risks`, `issues`, `change_requests`,
`documents`, `lessons`, `meeting_minutes` (las seis últimas vía `_ModuleBase`,
un solo cambio de modelo para seis tablas físicas), `risk_actions`, `ai_jobs`,
`reports`, `tasks` — todas `ON DELETE CASCADE`, igual que el resto del esquema.

**`audit_log` es la excepción: `ON DELETE SET NULL`, no `CASCADE`.** El registro
es de solo anexado (AM-08); la fila que audita el propio `tenant.hard_delete` no
puede desaparecer con el tenant que describe. La columna ya era nullable
(eventos platform-wide del superadmin), así que `SET NULL` no cambia su
contrato.

**Hallazgo de paso, no alcance nuevo.** `ai_jobs` y `reports` no tenían **ningún**
FK — ni a `tenants` ni a `projects`. `superadmin.py::hard_delete_tenant` borra
el tenant confiando en "cascada elimina todo" (comentario del propio endpoint),
pero `Tenant` no declara ningún `relationship()`: esa cascada es 100% de FK de
Postgres. Sin FK, esas dos tablas quedaban huérfanas tras un hard-delete. Esta
migración lo cierra igual que a las demás, sin ampliar el issue.

**Se para antes de escribir el constraint.** Ninguna de estas columnas estuvo
nunca protegida por FK, así que no hay garantía de que todo valor existente
apunte a un tenant real. La migración cuenta huérfanos antes de tocar el
esquema y falla con la lista completa si encuentra alguno — mismo criterio que
la 0108 con `programs.portfolio_id`. Rama de SQLite: no soporta `ADD CONSTRAINT`
sin recrear la tabla, y no hace falta emularlo — el esquema de tests nace de
`Base.metadata.create_all`, que ya lee el FK desde el modelo actualizado en el
mismo commit.

**Esta migración no activa RLS.** Eso es US-241 (jerarquía) y US-242
(proyectos) — el aislamiento real sigue siendo solo de capa de aplicación hasta
que esas dos cierren (`security-multitenant.md` §1, `ADR-003`).

**La bajada** suelta el índice antes que la tabla y pierde las membresías
**adicionales**; las de origen siguen en `users.tenant_id`. Verificada en los dos
sentidos sobre SQLite con usuarios previos: la siembra da dos membresías, el
usuario sin inquilino no gana ninguna, y al bajar `users.tenant_id` queda intacto.

