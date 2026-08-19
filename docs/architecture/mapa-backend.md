---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-19
revisar_cada: 90d
---

# Mapa de componentes — Backend (`apps/api`)

> Para sesiones de desarrollo: qué existe y dónde, sin re-explorar. Derivado
> del inventario Fase 0 (2026-08-19). Se abre **bajo demanda** al tocar
> backend; si contradice el código, gana el código y se corrige aquí.
> Actualizar la fila afectada en el mismo commit que cambia el componente.

## Estructura

```
apps/api/app/
  models/          ← SQLAlchemy, 1 archivo ≈ 1 dominio (59 tablas)
  api/v1/endpoints/  ← routers FastAPI; registro en api/v1/router.py
  api/deps.py      ← auth/scoping: TODO pasa por aquí
  services/        ← lógica de negocio (project_health, msproject/, …)
  core/            ← permissions, compatibilidad, paleta, magnitudes
  alembic/versions/  ← migraciones (última: 20260819_0108); 1 US = 1 migración
```

## Modelos por dominio (archivo → tablas clave)

| Archivo | Tablas | Notas para la reestructura |
|---|---|---|
| `tenant.py` | tenants (slug, settings JSON: BYOK en `settings.ai.byo`, org_label, report_builder) | plan_code (W7) va aquí |
| `organization.py` | organizations, **portfolios** (US-198), business_units†, departments†, programs | portfolios: `name` único por org, `code`, `owner_actor_id`→actors, soft-delete. `programs.portfolio_id` **NOT NULL**; `department_id` sin lectores nuevos. † endpoints se retiran en US-199, tablas en W8 (ADR-037) |
| `user.py` | users (tenant_id nullable, role_type, is_superadmin, lockout) | email único por tenant → global (W2); membresía nueva (W2) |
| `user_scope_assignment.py` | user_scope_assignments (scope_type org/program/project, sin FK real) | base de visibilidad PM |
| `auth.py` | refresh_tokens, password_reset_tokens, admin_otp_codes, dispositivos_confiables | JWT: claims tenant_ids, active_tenant_id (falta active_organization_id, W2) |
| `tenant_permission.py` | tenant_role_permission_overrides | overrides capability×tenant (DEC-021) |
| `project.py` | projects (**portfolio_id nullable** US-198; phase default "planning"; health_status/source/reason US-180; manually_edited_fields US-084), project_health_evaluations (US-191: 5+1 dimensiones, histórico) | quitar business_unit_id/department_id: US-199, con sus lectores |
| `project_request.py` / `project_charter.py` | project_requests, project_charters | limpiar BU/depto: US-199; folios SOL- via folio_sequences |
| `task.py` | tasks (wbs_code, parent_id, is_milestone, position US-176, predecessors JSON), task_dependencies (FS/SS/FF/SF + lag) | baseline y hito clave: W6 |
| `modules.py` | risks, issues (type action/issue/decision), change_requests, documents†, lessons, meeting_minutes (raid_suggestions JSON → flujo minuta→RAID ya existe) | † legacy, fusionar en project_artifacts (W8) |
| `project_artifact.py` | project_artifacts | el "Artefactos" nuevo ya es esta tabla |
| `area.py` | areas (org nullable), teams, actors (**el resource pool**: nominal/project_capacity_pct, fte_cost_rate, skills_tags, user_id?), area_assignments (cascada org/program/project) | actors.organization_id → NOT NULL + costo-snapshot (W4) |
| `project_participation.py` | project_participations (allocation_pct FTE, periodo, status ciclo de vida) | + cost_rate_snapshot (W4) |
| `project_role.py` / `stakeholder.py` / `project_member.py` | project_roles; stakeholders†; project_members† | † duplicados de actors/participations, consolidar (W8) |
| `report_*.py`, `scheduled_*.py` | reports, report_history/sections/templates, report_builder_templates, scheduled_reports/minutes (cadence weekly/monthly) | cadencia biweekly + scope portfolio (W5) |
| `metric_snapshot.py` | metric_snapshots (US-151: scope tenant/org/program/project, extras JSON) | + scope portfolio + cadence (W5) |
| `ai.py`, `assistant.py`, `ai_report_template.py`, `project_ai_context.py`, `platform_settings.py` | ai_jobs, assistant_*, ai_report_templates, project_ai_contexts, platform_ai_settings (groq key Fernet) | catálogo skills/roles de agente: W7 |
| `notification.py`, `audit.py`, `permission_request.py` | notifications, audit_log (actor_type humano/IA), permission_change_requests | estables |
| `role.py` | roles, user_roles — **DEPRECATED** (DEC-024) | drop pendiente (US-081/W8) |

**Convenciones**: IDs `String(36)` UUID texto · `TimestampMixin` · `tenant_id`
indexado (sin FK en tasks/ai_jobs/reports/_ModuleBase — se corrige en W3) ·
soft-delete `deleted_at` · **no hay RLS en Postgres** (solo filtrado ORM; W3).

## Routers (api/v1/endpoints/) — 1 línea cada uno

auth (login 2FA, switch-tenant, /me) · users (perfil/ARCO) · admin_users ·
admin_panel (bulk, métricas, tenant settings, audit export) · admin_ai +
superadmin_ai (BYOK) · organizations (CRUD orgs + programs + BU†/deptos†) ·
project_requests (CRUD + review + create-project; BU en L97–157†) · projects
(CRUD, health, phase, export, papelera) · project_charters · project_artifacts
(exports plan/raid/changes/lessons/organigrama) · modules (CRUD RAID/cambios/
docs/lessons/minutas + convert-agreement) · risk_actions · change_approvals
(token público JWT) · stakeholders · tasks (CRUD + renumber-wbs + **import
MPP/XML/XLSX/CSV** con preview/IA — base de importación masiva) · areas
(áreas→equipos→actores, sync-users) · project_directory (project_roles +
participations + eligible-actors) · capacity (/summary /conflicts
/resource-load) + organigrama · dashboard (kpis, charts, trends, heatmap,
risk/health-matrix, treemap, **snapshots/capture**, reports/portfolio) ·
tenant_cross (RAID/cambios/minutas/reportes cross con filtros) · reports +
report_templates/sections + report_builder (+ai-chat) + scheduled_* · ai
(minutas IA, drafts, jobs) + assistant (chat) + ai_context · superadmin +
superadmin_panel (tenants, join-as-admin, freeze) · branding ·
permission_requests · gantt_snapshot · entity_history · notifications.

## Scoping y permisos (leer antes de tocar cualquier endpoint)

- `api/deps.py` → `get_current_user` → `CurrentUser` con `tenant_ids` (M:N ya
  en JWT), `active_tenant_id`, `effective_tenant_id`. Cada endpoint filtra a
  mano `tenant_id == cu.effective_tenant_id`. Org llega como query param.
- Permisos: sin middleware; dependencias `require_capability(name)`
  fail-closed contra `core/permissions.py::ADMIN_CAPABILITIES` + overrides
  por tenant. Gates automarcados `__pmoaas_gate__`; trinquete:
  `tests/test_permission_matrix.py`. Modelo DEC-024: role_type
  admin/pm_sr/user + is_superadmin.
- Visibilidad PM: `scoped_project_ids` (dashboard) respeta
  user_scope_assignments.

## Services clave

`services/jerarquia.py` (US-198: «Portafolio General» por defecto + regla `program_id ⇒ portfolio_id = program.portfolio_id`; la aplica todo endpoint que acepte programa o portafolio) · `services/project_health.py` (motor semáforo US-180) · `services/msproject/`
(parsers MPP/XML) · `core/compatibilidad.py` (ventanas de compat, contador
por `compat.nombre_viejo`) · `core/paleta.py` (colores gráficos, espejo de
globals.css, trinquete test_adr023) · `core/magnitudes.py` (tipos Escala/
Importe/Porcentaje).

## Verificación

Skill `verificar` manda. Gates de CI relevantes: lint+typecheck+tests API
(exit 0), `test_permission_matrix.py`, `test_mca_aut01_guard.py`,
`scripts/check_contexto.py` (techo de contexto), `test_adr023_paleta`.
