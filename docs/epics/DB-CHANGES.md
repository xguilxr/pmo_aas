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

## EP016 — IA local (Ollama vía Tailscale)

Sin schema nuevo. La config del endpoint vive en
`tenants.settings.ai.ollama` (JSONB) — `{base_url, model, timeout_sec}`
tras US-047. Secrets CF-Access legacy, si existieran, quedan
archivados bajo `tenants.settings.ai.ollama.auth_legacy.*` (no borrados
para auditoría).

---

## EP012 — ❌ CANCELADO

Ver `docs/archive/cancelled-epics/EP012-db-migration.md` y **DEC-013**.
No hay trabajo de BD pendiente por esta épica.
