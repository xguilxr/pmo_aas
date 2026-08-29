---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-08-29
revisar_cada: nunca
---

# Reestructura — Fase 0: Inventario de reutilización

> Salida de la Fase 0 del plan (`reestructura-plan.md`). Barrido con 4
> sub-agentes (docs, schema, API, UI) el 2026-08-19 contra el árbol de
> `reestructura-conceptos.md`. Veredictos: REUTILIZAR (sobrevive casi igual)
> · ADAPTAR (cambia scoping/jerarquía) · REESCRIBIR · RETIRAR.

## TL;DR

**No se empieza de cero — se confirma.** De ~59 tablas, ~25 routers, ~40
pantallas y 14 epics, lo único que se **reescribe** es la jerarquía
organizacional (EP002 + pantalla admin de organizaciones) y lo único que se
**retira** neto es BU/Departamento. Los 8 módulos de proyecto, el motor de
reportes, la importación de planes (MPP/XML/XLSX/CSV), el RAID, recursos con
FTE/costo y la base de IA/BYOK se reutilizan o adaptan.

**Las 5 brechas grandes** (todo lo demás son ajustes):

1. **Portafolio no existe** como entidad — ni tabla, ni endpoint, ni
   pantalla (ADR-021 vetó incluso la palabra). Todo lo "portfolio" actual
   significa "el tenant entero".
2. **RLS no existe** — ADR-003 lo aceptó en diseño pero las 107 migraciones
   no tienen ni un `CREATE POLICY`; el aislamiento es 100% filtrado ORM.
3. **Usuario mono-tenant** — `users.tenant_id` es columna directa; el JWT ya
   trae `tenant_ids` M:N y `switch-tenant`, pero falta la tabla de membresía
   y el `active_organization_id`.
4. **Snapshot bi-semanal / salud explicable** — hay `metric_snapshots`
   (semanal, on-demand) y `project_health_evaluations` (declarada), pero sin
   cadencia bi-semanal, pesos configurables ni calc-vs-declarada.
5. **Vistas ejecutivas** — no hay control tower (`/pmo/projects` tiene 7 de
   ~18 columnas), ni heatmap de capacidad, ni importación masiva de
   proyectos/recursos (solo de planes).

---

## 1. Documentación (epics y drafts)

| Doc | Hoy | Veredicto | Qué cambia |
|---|---|---|---|
| EP001 auth-users | Capability-based (DEC-024), user de 1 tenant, opt-out por org | ADAPTAR | Membresía M:N; roles globales = el replanteo que DEC-018 difirió a v2.0 |
| **EP002 org-hierarchy** | tenant→org→BU→depto→programa→proyecto (6 niveles) | **REESCRIBIR** | Epic-ancla del árbol viejo; se rescatan CRUD de orgs y provisión de tenants |
| EP003 project-requests | Solicitud→revisión→proyecto, folio SOL- | ADAPTAR | Quitar BU/depto del form; sumar portafolio/programa |
| EP004 dashboard | KPIs a nivel tenant ("portafolio"=tenant) | ADAPTAR | Re-agregar por org/portafolio/programa |
| EP005 projects | Fases planning/execution/hypercare/closed/cancelled | ADAPTAR | Mapear a solicitud→preparación→ejecución→cierre (decisión de vocabulario, toca ADR-019/022); FK a portafolio; tipar `type` |
| EP006 project-modules | 6 módulos patrón común | REUTILIZAR | Rename Documentos→Artefactos (ya en EP018) |
| EP007 admin | Panel admin; US-038 (matriz roles) obsoleta | ADAPTAR | Purgar US-038; alinear a roles globales |
| EP008 ai | Modos disabled/platform/byo, minutas IA, memoria | ADAPTAR | Skills/tools/prompts/workflows + roles de agente = epic nueva encima |
| EP009 ms-project | Import MPP/XML/XLSX/CSV + Gantt | REUTILIZAR | Alimenta módulo Plan tal cual |
| EP010 superadmin | Panel plataforma, columna `plan` en tenants | REUTILIZAR | Sumar gestión formal de planes |
| EP017 project-directory | actors/areas/teams/participations (FTE) | ADAPTAR | Catálogo de recursos pasa de tenant a organización; falta costo-snapshot |
| EP018 documents-artifacts | 4 artefactos, organigrama derivado | REUTILIZAR | Es el módulo "Artefactos" ya |
| EP019 changes-approval | Cambios con aprobación externa (pending) | REUTILIZAR | Implementar sobre el árbol nuevo directo |
| EP020 report-builder | 4 niveles, 22 secciones, snapshots semanales | ADAPTAR | Sumar scope portafolio; bi-semanal; salud explicable |
| draft portfolio-recursos-capacidad | "Org≈Portafolio, no hace falta la entidad" | ADAPTAR | Contenido de capacidad/saturación es oro; re-anclar su jerarquía |
| draft plan-import-revamp | As-is import/export plan | REUTILIZAR | Mayormente ejecutado |
| draft feedback-16jul | Salud 5+1 con historial (US-191/192), FTE teórico | REUTILIZAR | Semilla de "salud explicable"; diseñar bloques C/D contra árbol nuevo |
| draft EP020-secciones | 22 secciones S-XX con niveles | ADAPTAR | Extender niveles con Portafolio/Programa |
| drafts auto-wbs / minute-gold | Entregado / formato normativo | REUTILIZAR | auto-wbs candidato a archivar |

**Decisiones/ADRs a tocar** (cada una exige entrada nueva, no edición):

- **ADR-024/DEC-003**: fija tablas BU/depto — retirarlas es migración de
  datos productivos → ADR nuevo con plan de migración.
- **ADR-016**: programa cuelga de org — re-parenting a portafolio.
- **ADR-017**: hard-delete enumera BU/Department — podar y sumar Portfolio.
- **ADR-021**: veto de la palabra "portafolio" — levantar el veto del
  glosario (el renombre a `discipline` sigue válido).
- **ADR-003**: RLS aceptado y no implementado — pasa de deuda a trabajo.
- **DEC-018/020/024**: modelo de permisos — roles globales es el replanteo
  diferido; DEC-005 obsoleta.
- **ENH-190**: label "Organización/Portafolio" cosmético — ✅ retirado (DEC-032, migración 0111).
- **ADR-019/022**: vocabulario de fases — decisión de mapeo explícita.

## 2. Schema (59 tablas, migración actual 20260807_0107)

| Dominio | REUTILIZAR | ADAPTAR | RETIRAR | NUEVO |
|---|---|---|---|---|
| Auth | refresh/reset/otp/dispositivos, audit_log, overrides por tenant, permission_change_requests | `users` (globalizar email, sacar role_type a membresía), `user_scope_assignments` | `roles`+`user_roles` (ya deprecated), `organization_user_exclusions` | **`user_tenant_memberships`** |
| Jerarquía | `tenants`, `organizations` | `programs` (quitar department_id, +portfolio_id NOT NULL) | `business_units`, `departments` | **`portfolios`** |
| Proyectos | `folio_sequences` | `projects` (quitar BU/depto, +portfolio_id?, enum type, fases), `project_requests`, `project_charters`, `project_health_evaluations` | `project_members` (fusionar en participations) | consistencia portafolio-programa (constraint/validación) |
| Módulos | risks, issues, change_requests(+approvers/tokens), lessons, `project_artifacts`, meeting_minutes (minuta→RAID ya existe), risk_actions | tasks (+baseline, hito clave), task_dependencies (inter-proyecto), reports/scheduled (+bi-semanal) | `documents` (legacy, fusionar en artifacts) | **`plan_baselines`**, **`project_dependencies`**, snapshot bi-semanal |
| Recursos | areas, teams, area_assignments, project_roles | `actors` (org obligatoria), `project_participations` (+costo-snapshot) | — | consolidar `stakeholders` vs `actors` (dos catálogos de personas) |
| IA | ai_jobs, platform_ai_settings, assistant_*, project_ai_contexts | ai_report_templates (→catálogo prompts) | — | **ai_skills/tools/prompts/workflows, ai_agent_roles + permisos de agente**, BYOK como tabla (hoy JSON en tenants.settings) |
| Plan/otros | notifications, metric_snapshots | — | — | **subscription_plans** + plan en tenant, completitud de datos, pesos de salud |

Hallazgos transversales: IDs `String(36)` (UUID texto — RLS/particionado lo
hereda); `tenant_id` sin FK en tasks/ai_jobs/reports; RLS = **cero policies**
en Postgres, todo ORM.

## 3. API (~25 routers)

- **REUTILIZAR** (12): users, admin_ai/superadmin_ai (BYOK ya existe),
  project_artifacts, modules (RAID/cambios/lessons/minutas), risk_actions,
  change_approvals, stakeholders, gantt_snapshot, entity_history,
  notifications, tasks (import MPP/XML/XLSX/CSV incluido), reports+builder+
  scheduled, ai/assistant/ai_context, branding, permission_requests.
- **ADAPTAR** (11): auth (`switch-tenant` → switch tenant+org; claim
  `active_organization_id`), admin_users (membresía M:N), admin_panel,
  organizations (quitar BU/depto, sumar CRUD portafolios), project_requests
  (limpiar BU/depto L97–157), projects, project_charters, areas +
  project_directory + capacity/organigrama (re-scope a org, FTE/costo ya
  existen), dashboard (filtro portafolio + vista maestra; snapshots existen,
  falta cadencia), tenant_cross (candidato natural a control tower),
  superadmin (plan de suscripción).
- **RETIRAR** (2): sub-routers business-units y departments.

Scoping hoy: `deps.py` → `CurrentUser` con `tenant_ids` (M:N ya en JWT),
`active_tenant_id`, `effective_tenant_id`; filtrado manual por endpoint. No
hay middleware de permisos: dependencias con `require_capability` fail-closed
+ test de matriz (`test_permission_matrix.py`) — los roles globales
**extienden ese mecanismo, no lo reemplazan**.

## 4. UI (Next.js 15 App Router + Tailwind v4, ~40 pantallas)

- **REUTILIZAR**: los 8 módulos de proyecto (plan/gantt, raid+kanban,
  minutas, reportes+builder, cambios, lecciones, charter, ai-context),
  admin (salvo organizaciones), superadmin, auth, landing, notifications.
- **ADAPTAR**: `/dashboard` y `/pmo` (consolidar en dashboard ejecutivo
  org-level con drill portafolio→programa→proyecto), `/pmo/projects`
  (embrión de control tower: 7 de ~18 columnas; necesitará sticky
  header/columnas y quizá virtualización — no hay tabla avanzada hoy),
  `/pmo/resources` (base capacity; falta heatmap persona×tiempo — el
  componente `Heatmap` SVG es reutilizable), vistas cross RAID/cambios/
  minutas (re-scope + filtro portafolio), requests (quitar BU/depto),
  project-form (select portafolio/programa anidado), `/pmo/organizations`
  y `/pmo/programs` (paneles de agrupador).
- **REESCRIBIR**: `/admin/organizations` + `org-hierarchy-section.tsx`
  (núcleo BU/depto → Portafolio⊃Programa).

**Componentes reutilizables**: dashboard-charts.tsx (Pie/Bars/Gauge/Trend/
RiskMatrix/Heatmap/Treemap SVG propio), kpi-card, health-panel (5+1 +
HealthWhyPanel), gantt-view, raid-kanban (base de boards), module-shell,
sortable-th + use-sortable-rows, tenant-cross-filters, org-tree-nav,
import-wizard, exports PDF (backend) y XLSX (exceljs). **No hay export PPT**
(pedido del cliente — sería backend).

**Navegación**: header no tiene switcher de tenant/org (tenant activo en
auth-storage al login; org como Select ad-hoc por página; org-tree-nav
duplica la elección en el sidebar). El shift tenant/org al header toca
app-shell + cross-filters + estado de cada página cross. **Layout**: el
chrome es full-width pero el contenido se limita con `max-w-6xl/7xl` — para
aprovechar el horizontal basta soltar esos límites por página. **Design
system**: tokens vivos y enforced en `globals.css` (CI de contraste y
literales); `docs/design-system/tokens.md` desincronizado (ya anotado en
SPRINT).

---

## Lecturas para la Fase 1 (modelo de datos)

1. La migración BU/depto→Portafolio necesita decidir **qué pasa con los
   datos productivos existentes** de business_units/departments (¿mapear a
   portafolios/programas? ¿archivar?). Es el ADR más caro de la fase.
2. Orden natural de construcción confirmado: la tabla `portfolios` +
   membresía + RLS (B1) desbloquean todo; recursos (B2) es el dominio más
   avanzado (solo falta costo-snapshot y re-scope); las vistas ejecutivas
   (B3) son mayormente frontend sobre datos que ya existen.
3. Deudas a resolver de paso: consolidar `actors` vs `stakeholders`,
   `documents` vs `project_artifacts`, `project_members` vs
   `project_participations`; FKs de tenant_id faltantes; BYOK de JSON a
   tabla.
