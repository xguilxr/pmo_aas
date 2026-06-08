# DB-CHANGES.md — Cambios de schema por epic

> **Política activa (2026-04-21):**
> - Productivo v1.0 corre en **Railway Postgres** (DEC-013). No hay plan
>   de migrar a otro motor.
> - Una migración Alembic por US; nunca combinar múltiples cambios
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
- Agrega `programs.department_id` (nullable — un programa puede colgar
  directo de la organización o de un departamento).
- Agrega `projects.department_id` y `projects.business_unit_id`
  (nullable — se llenan desde la cadena del programa cuando aplica).
- Agrega `project_requests.business_unit_id` y
  `project_requests.department_id` como FK.

Los campos legacy `project_requests.business_unit` y
`project_requests.department` (texto libre) se conservaron por
retro-compatibilidad; pueden dropearse cuando se valide que ningún
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
(DEC-007): Risks de la tabla `risks`, y Actions/Incidents/Decisions de
la tabla `issues` discriminados por `issues.type ∈
{'action','incident','decision'}`. El validator se hace en el modelo,
no en BD.

## EP007 — Admin

Sin schema nuevo. Toda la funcionalidad reutiliza tablas existentes
(`tenants`, `users`, `roles`, `audit_logs`, `business_units`,
`departments`).

## EP008 — IA

Schema cubierto por migración **0007** (`ai_jobs`, `reports`).

## EP010 — Super admin panel

Sin schema nuevo. `users.is_superadmin` ya existe desde
`20260101_0001_initial.py`; el panel reusa `tenants` + `users` + `audit_logs`
cross-tenant.

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

US-028 (email via Resend) no requiere schema adicional; la cola sale
del `notifications.type` leído por un worker Celery.

## EP013 / EP015 — Refactor navegación

Sin migraciones nuevas. `tenants.logo_url` ya existía; US-031 reusa
el campo + el storage local.

## EP014 — Entregables operativos

Migraciones **0014** (`reports_period`) + **0015**
(`reports_generator_cut_off`): añaden `reports.generator` (`'manual' |
'ai' | 'avance' | 'seguimiento'`) y `reports.cut_off_date` + columnas de
período. US-040 (formato estandarizado de minuta IA) es
post-procesamiento sobre `meeting_minutes`; no toca BD.

Migración **0018** (`scheduled_reports`): tabla nueva para US-056
(calendarización automática de envíos). Columnas: `id`, `tenant_id`,
`project_id`, `report_type` (`'avance' | 'seguimiento'`), `cadence`
(`'daily' | 'weekly' | 'monthly'`), `recipients` (JSON list de
emails), `enabled`, `last_run_at`, `next_run_at`, `last_error`,
`created_by`. Índices: `(tenant_id, project_id)` y `(enabled,
next_run_at)` para el dispatch del beat.

## EP006 — RAID con área responsable (US-064)

Migración **0024** (`raid_area_id`): agrega `area_id` a `risks` e
`issues` como FK nullable a `project_areas.id` con
`ON DELETE SET NULL`, más índice compuesto `(tenant_id, project_id,
area_id)` para el ordenamiento de las tablas RAID.

Regla de legacy: ítems previos a la migración se quedan con
`area_id = NULL`; la obligatoriedad en creación vive a nivel de
schema Pydantic (`422` en POST si falta), NO en la DB. Los endpoints
GET ordenan por `CASE WHEN area_id IS NULL THEN 1 ELSE 0 END` (legacy
al final) → `project_areas.name ASC` → `identified_at DESC` (risks) o
`reported_at DESC` (issues) → `severity/priority DESC`. Nuevo filtro
`?area_id=` en `/projects/{id}/risks`, `/projects/{id}/issues`,
`/tenant/risks` y `/tenant/issues`.

## EP016 — IA local (Ollama vía Tailscale) — ❌ ARCHIVADA

Toda la epic quedó superseded por DEC-017 y eliminada en BUG-053
(2026-05-08). `OllamaProvider` se quitó del runtime. Los datos
legacy en `tenants.settings.ai.ollama` quedaron en BD por auditoría
pero ya no se leen — el resolver de provider falla con
`unsupported_provider` para `provider="ollama"`.

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

Sin cambio de schema; solo data normalization. `viewer` queda
eliminado del vocabulario (DEC-024) — el endpoint `/auth/me/permissions`
deja de aceptarlo y `capabilities_for("viewer")` retorna `set()` por
fail-safe. `Literal[RoleType] = ["admin", "user"]`.

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

Modelo opt-out: tabla vacía = user accede a TODAS las orgs del tenant.
El admin agrega filas para excluir orgs puntuales desde
`/admin/users/{id}`.

**Pendiente (ENH separado):** filtrado efectivo en queries de
proyectos/riesgos/minutas por orgs accesibles del user. Hoy solo se
almacena el dato.

### Tablas deprecated (US-077, borrado físico → US-081 Sprint 7)

`roles` y `user_roles` quedan presentes pero **sin UI editor** (la
página `/admin/roles/*` y endpoints `admin_roles.py` se borraron en
US-077). El gate ignora `Role.permissions` JSON desde US-076; las
tablas viven solo por compat hasta validar Sprint 6 en producción.

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
- `private` → sólo el `owner_id` puede ver/modificar.
- `project` → todos los miembros del `project_id` la ven; sólo el owner publica/despublica.
- `tenant` → reservado, no usado en v1.0.
- Seeds (`is_seed=True`, `tenant_id=NULL`) siguen visibles para todos los users (no respetan visibility).

### Migración **0074** — `scheduled_reports.report_builder_template_id` (US-131)

| Campo | Tipo | Notas |
|---|---|---|
| `report_builder_template_id` | `VARCHAR(36)` FK `report_builder_templates.id` `ON DELETE SET NULL` | indexed (`ix_scheduled_reports_builder_template`) |

Cuando `scheduled_reports.report_type='custom'`, este campo apunta a la plantilla del Report Builder. El worker (`apps/api/app/workers/tasks/scheduled_reports.py`) invoca el motor de US-123 (`render_template`) sobre la plantilla y manda el HTML resultante por `html_to_pdf` antes de adjuntar al email via Resend. `REPORT_TYPES` se extiende a `("avance", "seguimiento", "custom")`.

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

Sin backfill (sólo abre el valor para futuras inserciones).

---

## BUG-063 — Re-seed idempotente de report_sections (2026-05-24)

### Migración **0076** — re-seed `report_sections` si está vacío

Owner reportó "el catálogo de secciones sigue vacío" en
`/pmo/projects/[id]/reports/builder` tras el deploy del Sprint 26-32.
La migración 0070 (US-120) creó la tabla y debía sembrar 22 secciones,
pero las rows aparecen ausentes en su DB (posible reset post-deploy,
o `bulk_insert` quedó sin commit).

La migración 0076 es **idempotente**: si `report_sections` ya tiene
rows, no hace nada. Si está vacía, inserta las 22 secciones canónicas
EP020 con el mismo contenido que el seed original.

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

- Buckets nuevos canónicos A/R/D/I alineados con el modelo RAID.
- `lessons` y `changes` siguen aceptados para retro-compat con
  minutas existentes (el LLM ya no los genera; validator descarta).
- `_meta.free_notes` persiste las notas libres opcionales del PM
  (evita migración de columna).

Sin migración de schema (columna `raid_suggestions` es JSON). El
formatter (`minutes_formatter.py`) lee los 6 buckets; el frontend
y el endpoint endpoint aceptan ambos shapes en input.

`meeting_minutes.description` se reutiliza para el resumen de 2-3
oraciones (campo heredado de `_ModuleBase`, antes no usado por minute).

---

## US-151 — Fundación de datos analíticos / dashboards N1-N2 (2026-05-26)

### Migración **0079** — tabla `metric_snapshots`

Foto periódica (cadencia **semanal**, lunes 02:00 UTC vía Celery beat) de
las métricas de *stock* del portafolio a los 4 niveles de scope
(`tenant` / `organization` / `program` / `project`). Sin historia persistida
no hay líneas de tendencia en los dashboards ni en los reportes Nivel 1/2;
esta tabla es esa historia y desbloquea las secciones S-05 (tendencia) y
S-07 (curva-S) que EP020 había diferido por falta de datos.

Columnas: `scope_type`, `scope_id`, `snapshot_date` + métricas escalares
(`projects_total/active`, `health_green/yellow/red`, `avg_progress`,
`budget_plan/actual`, `open_risks`, `severe_risks`, `open_issues`,
`changes_in_review`, `requests_in_review`, `tasks_total/done`,
`milestones_due_7/14/30`) y `extras` (JSONB, bolsa flexible para métricas
futuras sin migración). `UNIQUE(tenant_id, scope_type, scope_id,
snapshot_date)` garantiza idempotencia del job. FK `tenant_id` → `tenants`
con `ON DELETE CASCADE`. Downgrade hace `drop_table`.

Las métricas de *flujo* (cycle-time, throughput) NO viven aquí: se calculan
on-the-fly desde timestamps existentes (`requested_at`/`approved_at`, etc.).

---

## BUG-068 — `organizations.logo_url` / `client_logo_url` → TEXT (2026-05-26)

### Migración **0082** — widen logo columns

`organizations.logo_url` y `client_logo_url` pasan de `String(500)` a `Text`.
Antes, subir un PNG (que se almacena como data-URL base64) excedía los 500
caracteres y se truncaba/rechazaba — "subir PNG no se guarda bien"; las URLs
externas cortas sí cabían. Ahora ambas columnas admiten data-URLs base64 de
logos subidos directamente (PNG/JPG/SVG/WEBP) además de URLs externas. El cap
de longitud vive en el schema Pydantic (`_LOGO_MAX = 3_000_000`, ~imagen de
2 MB codificada). `alter_column` vía `batch_alter_table` (compat SQLite + PG).
Downgrade revierte a `String(500)`.

### Migración **0083** — `tenants.logo_url` → TEXT

Mismo problema en el logo del **tenant**: antes se guardaba en disco (efímero
en Railway) y se servía por `GET /branding/tenants/{id}/logo`, un endpoint
autenticado que un `<img src>` del navegador no puede consumir (mandaba 401 →
el logo nunca se mostraba; con URLs externas sí funcionaba). Ahora el logo del
tenant se guarda como **data-URL base64 en `tenants.logo_url`** y renderiza
directo. La columna pasa de `String(500)` a `Text`. El endpoint de serve se
conserva por retro-compat de logos viejos en disco; las subidas nuevas ya no
lo usan. Downgrade revierte a `String(500)`.

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
Herencia: org → todos sus programas + proyectos; program → proyectos + org contexto; project → proyecto + org + program contexto.
