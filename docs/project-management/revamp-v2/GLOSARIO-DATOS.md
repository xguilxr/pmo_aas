# Glosario de datos por entidad (FASE-9, pasada 2)

> Campo por campo: qué tiene el modelo, dónde se pide en la UI, y qué
> discrepancias hay. Generado 2026-09-12 contra `main` post-PR #612.
> "EN NINGÚN LADO" = ningún formulario lo pide. Derivado = correcto que
> no se pida (id, timestamp, calculado server-side). Configurable = campo
> de negocio que debería tener un input y no lo tiene.

## Organization

| Campo | Tipo | Dónde se pide | Notas |
|---|---|---|---|
| name, reason_social, industry, country, contact_email, logo_url, client_logo_url, is_active | — | `organization-form.tsx` | OK |
| id, tenant_id, created_at, updated_at | — | — | Derivado |

Sin discrepancias.

## Portfolio

| Campo | Tipo | Dónde se pide | Notas |
|---|---|---|---|
| name, code, description, owner_actor_id, is_active | — | `portfolio-form.tsx` | OK |
| organization_id | — | parámetro de ruta, no input | OK |
| id, tenant_id, deleted_at, created_by, created_at, updated_at | — | — | Derivado |
| program_count, active_project_count (solo frontend) | — | — | Derivado, calculado; el modelo no guarda métricas propias a propósito (ADR-037) |

Sin discrepancias.

## Program

| Campo | Tipo | Dónde se pide | Notas |
|---|---|---|---|
| organization_id, portfolio_id, name, description, strategic_alignment, start_date, end_date, is_active | — | `program-modal.tsx` | OK — `portfolio_id` puede ir `null` desde el form; el backend resuelve "Portafolio General" server-side (DEC-030), confirmar que ese fallback sigue vivo |
| id, tenant_id, created_at, updated_at | — | — | Derivado |

Sin discrepancias de fondo.

## Project

| Campo | Dónde se pide | Notas |
|---|---|---|
| organization_id | Crear (no editable después) | OK |
| program_id, portfolio_id, name, description, type, priority, pm_id, sponsor, start_date, end_date, currency, budget | Crear y editar (`project-form.tsx`) | OK |
| actual_budget | Solo editar | OK, no aplica al crear |
| phase | Crear (select); editar solo vía "Cambiar fase" (`changePhase`, transición controlada) | OK por diseño — no está en `ProjectUpdateBody` a propósito |
| health_status, health_reason | Detalle → tarjeta de Salud (`declareHealth`) | OK |
| health_source | Se fija implícito al declarar/resetear salud | Derivado |
| **progress** | **EN NINGÚN LADO como input manual** — `ProjectUpdateBody` lo acepta pero `project-form.tsx` no tiene campo; solo llega por agregado de tareas en `/plan` | **Confirmar con owner si es intencional** (nadie debería "inventar" avance a mano) o si falta el input |
| folio, request_id, deleted_at, manually_edited_fields, created_at, updated_at | — | Derivado |

**Discrepancias reales:**
1. `resetPlanAggregateOverride()` existe en `lib/api/projects.ts` (revierte overrides manuales de `start_date/end_date/budget/progress`) pero **no se invoca desde ninguna pantalla** — no hay forma de volver a automático esos 4 campos (sí la hay para salud).
2. `sponsor`, `type`/`project_type`, `priority`, `pm_id` existen como columnas propias en `Project` **y** en `ProjectCharter`, sin sincronización visible — pueden divergir.
3. `ProjectCharter.portfolio_id`/`program_id` existen en modelo y tipo TS pero el formulario del charter no los expone (el comentario dice que el charter "hereda" la clasificación, pero no hay UI que lo confirme ni lo edite).

## Risk

| Campo | Dónde se pide | Notas |
|---|---|---|
| title, description, probability, impact, mitigation_strategy, owner_actor_id, area_id, identified_at, due_date | Crear y editar (`raid-create-modal.tsx` / `raid-edit-fields.tsx`) | OK |
| **category** | **Solo editar** — falta en `raid-create-modal.tsx` | **HUECO confirmado (runbook), fix en este PR** |
| status, closure_note, on_hold_* | Solo editar (correcto, no aplica al crear) | OK |
| severity | — | Derivado, calculado client-side |
| owner_id (legacy) | EN NINGÚN LADO | Reemplazado por `owner_actor_id` (ENH-079); campo muerto, no requiere form |

## Issue (acción / incidente / decisión)

| Campo | Dónde se pide | Notas |
|---|---|---|
| title, description, priority, owner_actor_id, area_id, committed_date | Crear y editar | OK |
| type | Crear (implícito por qué modal se abre), editar (Select libre) | OK |
| reported_at | Crear (reusa "fecha de creación") | OK |
| **category** (ENH-177) | **EN NINGÚN LADO** — ni create ni edit | **HUECO nuevo, no estaba en el runbook. Fix en este PR** (mismo propósito que `Risk.category` según el propio comentario del modelo) |
| resolution | Solo editar | OK |
| owner_id (legacy) | EN NINGÚN LADO | Reemplazado por `owner_actor_id`, campo muerto |

## ChangeRequest

| Campo | Dónde se pide | Notas |
|---|---|---|
| title, description, impact | Crear y editar (`change-detail-page.tsx`) | **El runbook decía "sin edición" — desactualizado, ya existe.** Gate real: `status === "in_review"`, no `"draft"` como decía el runbook |
| type | Crear; editar solo inline desde la tabla de listado, no desde el detalle | Inconsistencia de superficie menor |
| status | Vía `approveChange`/`rejectChange`/`cancelChange` | OK, máquina de estados |
| requested_by, requested_at, approved_by, approved_at | — | Derivado |

## Actor (recurso)

| Campo | Dónde se pide | Notas |
|---|---|---|
| name, email, company, team_id, area_id | Alta (`actor-form-modal.tsx`) y edición inline (`DirectoryView.tsx`) | OK |
| phone, job_title | **Solo edición inline** — faltan en el alta | Hueco chico |
| **resource_type, discipline, seniority, scarcity_level, location, skills_tags, nominal_capacity_pct, project_capacity_pct, is_key_resource, is_shared_resource, fte_cost_rate, cost_rate_period** | **EN NINGÚN LADO** — ni alta ni edición | **Hueco grande**: todo el "pool de recursos" existe en modelo, está tipado en frontend y se usa en reportes/cálculos de capacidad/saturación, pero nadie puede cargarlo desde la UI |
| is_lead, verified, manager_actor_id, user_id | EN NINGÚN LADO | Configurable sin UI (jerarquía de reportes, vínculo a cuenta de usuario, flags de liderazgo/verificación) |
| is_active, auto_created, deleted_at, created_by, organization_id, created_at | — | Derivado / gestionado por otros flujos (alta/baja, matcher de minutas) |

## User

Sin discrepancias reales. Los campos sin formulario (`avatar_url`, `locale`, `preferences`, `privacy_accepted_at/version`, `is_superadmin`) son derivados de otros flujos (login, consentimiento, gestión de superadmin aparte) o están deliberadamente fuera de `admin/users`.

## ProjectRequest

| Campo | Dónde se pide | Notas |
|---|---|---|
| title, description, objective, organization_id, business_unit, department, portfolio_id, program_id, sponsor, sponsor_email, benefits, scope, entregables, key_people, if_not_done, observations, currency, budget, requester_name, requester_email, delivery_constraint_date, attachments | **Solo en creación** | — |
| status | Vía botones de revisión (`reviewRequest`) | OK |
| review_comment | Solo el revisor, en el modal de revisión | OK |

**Discrepancia confirmada (runbook):** `pmo/requests/[id]/page.tsx` no permite editar ningún campo del solicitante mientras `status ∈ {in_review, needs_info}` — todos se muestran como texto plano. `updateRequest()` ya existe en `lib/api/requests.ts` con su body tipado, pero es código muerto: ningún componente lo llama. **Hueco sigue abierto.**

---

## Resumen de acción

**Se corrigen en este PR** (chicos, acotados, sin ambigüedad de diseño):
1. `Risk.category` en `raid-create-modal.tsx`.
2. `Issue.category` en `raid-create-modal.tsx` y `raid-edit-fields.tsx`.
3. Corrección de comentario/gate de `ChangeRequest` edit (`draft` → `in_review`) — ya funcionaba, solo estaba mal documentado en el runbook.

**Fueron a triage** (grandes o con decisión de diseño pendiente, exceden el alcance de "agregar un campo a un form existente"):
- ENH-205 #613 — Actor: sección completa de "pool de recursos" (11 campos).
- ENH-206 #614 — Actor: `phone`/`job_title` en alta; `is_lead`/`verified`/`manager_actor_id`/`user_id` sin UI.
- BUG-101 #615 — Project/ProjectCharter: sincronización `sponsor`/`type`/`priority`/`pm_id`.
- ENH-207 #616 — Project: UI para `resetPlanAggregateOverride`.
- ENH-208 #617 — ProjectCharter: exponer `portfolio_id`/`program_id` en el form.
- BUG-102 #618 — ProjectRequest: edición de campos del solicitante en `in_review`/`needs_info`.
- ENH-209 #619 — ChangeRequest: `type` editable también desde el detalle.

**Decidido, sin issue:** `Project.progress` sin input manual es intencional (owner, 2026-09-12) — el avance siempre sale del rollup de tareas.
