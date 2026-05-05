# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
2026-05-05 — Sprint 9 v1.8 — Bloque 1: hard delete two-step ✅ EJECUTADO
Branch sesión: claude/resolve-merge-conflicts-4MmJK

Owner reportó (2026-05-05): "Como admin de tenant intenté borrar
permanentemente un programa duplicado pero solo se desactiva".
Decisión owner (AskUserQuestion): scope = las 6 entidades admin
(programs, orgs, BUs, depts, users, stakeholders); cascada = borrado
físico con conteo explícito en confirm modal.

Resultado:
  · US-088 #189 → (sha por commitear) feat(api,web) — hard delete
    two-step para 6 entidades + ADR-017.

Cambios entregados:
- Backend (`apps/api/app/`):
  - `core/hard_delete.py` (nuevo): helper `confirm_slug` +
    `ensure_inactive` + `ensure_confirm`.
  - `schemas/hard_delete.py` (nuevo): `HardDeletePreview`.
  - `api/v1/endpoints/organizations.py`: 8 endpoints nuevos
    (preview + DELETE permanent para program/org/BU/dept).
  - `api/v1/endpoints/admin_users.py`: 2 endpoints + cascade SET NULL
    en ~15 FKs nullable; bloqueante si hay project_request o
    permission_change_request con NOT NULL FK al user.
  - `api/v1/endpoints/stakeholders.py`: 2 endpoints (cascade trivial).
- Frontend (`apps/web/`):
  - `components/hard-delete-button.tsx` (nuevo): reusable component
    con preview → modal → typed slug confirm → delete.
  - `lib/api/{organizations,admin,stakeholders}.ts`: clientes nuevos.
  - Wired en: `programs-section.tsx`, `org-hierarchy-section.tsx`
    (BUs y depts), `admin/organizations/[id]/edit/page.tsx`,
    `admin/users/[id]/page.tsx`, `admin/stakeholders/page.tsx`.
- Tests: `apps/api/tests/test_us088_hard_delete.py` — 9/9 passing
  (3 program incl. cascade, 1 org, 1 BU, 1 dept, 1 stakeholder,
  2 user). Suites EP002 + EP007 + US-042 = 42/42 sin regresión.
- Docs: `docs/adr/README.md` ADR-017 nuevo. CLAUDE.md próximo
  libre ahora US-089.

Pendiente owner:
- Revisar PR + verificar el flujo en /admin/organizations/<id>/edit:
  el botón "Eliminar" rojo aparece para programas inactivos. Click →
  modal con conteo de proyectos en cascada + input typed-confirm.
- Confirmar typed-slug funciona en otras 5 entidades.
- Cerrar issue #189 cuando todo verde.

Diferidos (documentados como follow-up):
- Hard-delete de User cuando hay `project_request.requested_by` =
  bloqueado. Futuro: agregar endpoint de reasignación interactiva.
- Lista organizations (cards) no tiene botón inline de hard-delete,
  hay que entrar al detalle. Bajo impacto: la lista solo se ve para
  navegar; el detalle es el lugar natural de borrado.

Próximo libre: US-090, BUG-042, ENH-047.

--- contexto ronda Sprint 9 (mismo branch) ---
2026-05-05 — Sprint 9 v1.8 — Bloque 2: 3 items batch ✅ EJECUTADO
Branch sesión: claude/resolve-merge-conflicts-4MmJK (mismo)

Owner pidió 3 items en una ronda:
  · ENH-045 #192 → 990d138  feat(auth) — password policy 12 → 8 chars.
  · US-089  #193 → 77ac31b  feat(api) — email bienvenida con creds al
    crear usuario (template Resend + must_change_password=true).
  · ENH-046 #194 → (sha por commitear) feat(api,web) — reportes
    programados con día de semana + hora (recurrentes) y fecha + hora
    one-time. Migración 0036 + nuevos campos del schema + UI condicional.

Tests: 29/29 verde (US-088 + US-056 + ENH-046 + US-089).
Frontend: tsc + next build OK.

--- contexto post-US088 (mismo branch) ---
2026-05-05 — Sprint 9 v1.8 — BUG-041 + UX polish ✅ EJECUTADO
Branch sesión: claude/resolve-merge-conflicts-4MmJK (mismo)

Owner reportó tras testear US-088:
1. README desactualizado → actualizado al estado Sprint 9 v1.8.
2. Botón "Desactivar" sin icono propio ni texto visible → cambio a
   `PowerOff` + label "Desactivar" en programs/BUs/depts/orgs/users/
   stakeholders. Commit: chore(web).
3. Documentos exportados bajan como `.file` → BUG-041 #191. Causa
   raíz: `a.download = ""` con blob URL hace que Chrome use filename
   genérico. Fix: parsear `Content-Disposition` y settear `a.download`
   con el filename real (incl. extensión). Commit: fix(web).

Files cambiados (3 commits separados):
- README.md (docs)
- CLAUDE.md numbering (BUG-042 next free)
- programs-section.tsx, org-hierarchy-section.tsx, organizations
  [id] edit, stakeholders page, users [id] page (UX)
- apps/web/lib/api/modules.ts (BUG-041)

Limpieza branches (2026-05-05):
- `claude/sprint-issues-backlog-setup-EMiLA` → SAFE TO DELETE.
  Owner reportó la branch tras cleanup; tiene 6 commits ahead de
  main pero todos están superseded:
  · 5bf7d22 BUG-033 → ya en main como 711be4e (Sprint 8 cherry-pick).
  · d85e642 BUG-035 → ya en main como 4193f24 (Sprint 8 cherry-pick).
  · 7e21280 BUG-040 → ya en main como a5c3a2c (Sprint 8 cherry-pick).
  · f7e3279 BUG-032 → fue un fix con scope distinto al issue real;
    issue #159 cerró con 2f86f38 (otro scope, /superadmin/me email).
  · 8de1051, bae45f3 — sprint coordination docs ya superseded.
  Conflictos en `modules.py` (US-086) + `SPRINT.md` confirman
  staleness. Owner puede borrar la remote sin merge.

--- contexto Sprint 8 cleanup ---
2026-04-29 — Sprint 8 v1.7 — BATCH CLEANUP ✅ EJECUTADO
Branch sesión: claude/fix-issue-resolution-S3i4e

Owner pidió "ejecuta TODOS los issues abiertos, saltándote las
reglas de bloques pero respetando 1 issue = 1 commit". Decisión:
priorizar SOLUCIONAR > documentar (ver CLAUDE.md §0 nuevo).

13 issues procesados en una ronda. 12 cerrados como completed,
1 cerrado como not_planned (sin repro). Tests verdes en cada commit.

Commits agregados a la branch (en orden):
  · BUG-033  #160 → 711be4e (cherry-pick) fix(api,web) — role_type editable modal
  · BUG-035  #163 → 4193f24 (cherry-pick) fix(api,web) — RAID owner sidebar nombre
  · BUG-040  #186 → a5c3a2c (cherry-pick) fix(api,web) — documents extensión + 1MB
  · BUG-037  #171 → 09af27c  fix(web) — solicitud expone campos faltantes UX
  · ENH-038  #170 → 86d5936  feat(api,web) — fecha solicitud + restricción entrega
  · ENH-039  #172 → 04cf8a7  feat(api,web) — cambios solicitante/aprobador con UserMini
  · ENH-040  #173 → c62109b  feat(api,web) — presupuesto opcional + ocultar si NULL
  · ENH-041  #174 → b04818e  feat(web) — BU select + "Otra…" inline
  · ENH-042  #176 → 58ee920  feat(web) — minutas IA como acción primaria
  · US-084   #175 → a6f5b7a  feat(api,web) — plan agregados manualmente editados
  · US-085   #177 → 21eb835  feat(api,web) — solicitud "Otra…" org + notif inactiva
  · US-086   #178 → (sha en branch) feat(api,web) — stakeholders catálogo MVP
  · US-087   #179 → deee5a8  feat(api) — reporte avance KPIs numéricos
  · ENH-043  #180 → 6cf20c4  docs — cross-empresa workaround + ADR-016
  · ENH-044  #185 → 2f9c458  ci(infra) — alembic upgrade head Postgres efímero
  · BUG-038  #181 → cerrado not_planned (sin repro; código ya usa single source).
  · ENH-036  #162 → ya implementado en a48aa2b (Sprint 7), verificado y cerrado.
  · US-082   #164 → ya implementado en 3533d21 (Sprint 7), verificado y cerrado.
  · US-083   #165 → ya implementado en c740a59 (Sprint 7), verificado y cerrado.

Migraciones agregadas (auto-aplican al deploy via Dockerfile CMD):
- 0032 project_request_delivery_date (ENH-038).
- 0033 project_request_budget_nullable (ENH-040).
- 0034 project_manual_edited_fields (US-084).
- 0035 stakeholders_catalog (US-086).

Pendiente owner:
- Revisar PR (1 solo PR con todos los commits del batch).
- Validar uno por uno con la matriz de cambios del comment de
  cada issue cerrado (los 13 tienen TC verificados).
- Confirmar redeploy Railway aplica las 4 migraciones nuevas
  sin issues (ENH-044 nuevo gate Postgres validará que sí).
- BUG-038 #181: si reproduce el bug, reabrir con ID/screenshot.

Decisión filosofía CLAUDE.md (sec §0 nueva):
- Solucionar > documentar.
- Si hay implementación previa, cherry-pick y verificar (no
  re-triagear).
- Scope grande → MVP funcional + diferidos documentados.
- Tests + typecheck verdes son la condición única.
- Council de 3 agentes interno por default (no spawneamos
  sub-agents salvo arquitectura > 1 día).

Próximo libre tras Sprint 8 cleanup:
  - US-088, BUG-040 (ya tomado), ENH-045

--- contexto Sprint 8 hotfix ---
2026-04-28 (PM) — Sprint 8 v1.7 — Bloque 0 hotfix prod ✅ EJECUTADO
Branch sesión: claude/fix-api-deploy-failure-LIFac

Hotfix detectado tras revisión de logs Railway: el redeploy del api
post-merge Sprint 7 fallaba en `alembic upgrade head` con
DatatypeMismatch sobre la migración 0031 (US-082). Causa: server_default
=sa.text("1") sobre columna BOOLEAN — Postgres rechaza, SQLite acepta
(por eso CI no lo cazó).

  · BUG-039 #184 → 62c4f96  fix(db) — boolean default Postgres-compatible
    en permission_change_requests (server_default "1" → "true").

Fuera de orden de bloques (atendido directo como hotfix por bloqueo de
producción). Owner debe mergear ASAP para que Railway redespliegue api.

--- contexto Sprint 8 triage ---
2026-04-28 (AM) — Sprint 8 v1.7 — TRIAGE COMPLETO, esperando status:ready
Branch triage: claude/create-issues-sprint-planning-9Ke3t (PR #182 mergeado)

Owner mandó feedback DRC Consultores + propuestas (16 items).
Tras AskUserQuestion 2026-04-28 con 4 decisiones del owner, se crean
11 issues nuevos en 5 bloques + 1 INBOX placeholder (esperando repro).

Items creados (en orden de bloques):
  Bloque 1 — Solicitud chicos (3 items, ≤2h c/u):
    · ENH-038 #170 — Fecha solicitud + restricción entrega (item 4)
    · BUG-037 #171 — Botón Enviar UX faltantes (item 5)
    · ENH-039 #172 — Cambios mostrar aprobador + fechas (item 15)

  Bloque 2 — Solicitud medianos (2 items, 1-2 días c/u):
    · ENH-040 #173 — Presupuesto opcional (item 3)
    · ENH-041 #174 — BU select + "Otra…" (item 2)

  Bloque 3 — Plan + Minutas UX (2 items):
    · US-084 #175 — Plan editable manual con flag (item 8)
    · ENH-042 #176 — Minutas IA jerarquía visual (item 13)

  Bloque 4 — Cambios grandes (3 items, 3-4 días c/u):
    · US-085 #177 — Org libre + creación inactiva + notif (item 1)
    · US-086 #178 — Stakeholders Opción B catálogo tenant (item 11)
    · US-087 #179 — Reportes KPIs + fechas explícitas (item 14)

  Bloque 5 — Workaround docs (1 item, 1-2h):
    · ENH-043 #180 — Programas cross-empresa workaround + ADR (item 16)

INBOX (esperando repro):
  · BUG-038 #181 — Solicitud "Pendiente" + "Aprobada" simultáneo (item 6)

Decisiones owner (vía AskUserQuestion 2026-04-28):
  1. US-085 (item 1): activación org manual sin requisitos previos
     (no se exige logo/TZ/moneda como gate).
  2. US-086 (item 11): Opción B — catálogo tenant (no global con
     tabla de participación). DEC-025 a registrar.
  3. ENH-043 (item 16): posponer cross-empresa, doc workaround.
  4. BUG-038 (item 6): INBOX hasta repro.

Items "ya resueltos" — verificación owner en deploy actual:
  · Item 7 (Editar Charter en revisión) — ya solo aparece si proyecto.
  · Item 9 (RAID A/I/D solo descripción) — ya está así (US-064).
  · Item 10 (RAID editable durante ejecución) — Sprint 7 ENH-036.
  · Item 12 (Documentos no funciona) — Sprint 7 BUG-034.

Pendiente owner:
  - Revisar los 12 issues nuevos (#170-#181).
  - Asignar `status:ready` a los que apruebe (orden default: 1→2→3→4→5).
  - Verificar items "ya resueltos" en deploy actual.
  - BUG-038 #181: cuando reproduzca el bug, comentar con ID/screenshot
    para mover a un Bloque del Sprint 8 (o Sprint 9).

Próximo libre tras Sprint 8 triage + hotfix BUG-039 + ENH-044 (CI gate):
  - US-088, BUG-040, ENH-045
```

```
--- contexto Sprint 7 cerrado ---
2026-04-25 — Sprint 7 v1.6 ✅ EJECUTADO EN BLOQUE + MERGEADO A MAIN.
Branch: claude/review-and-triage-issues-EUsvX → PR #169 (merge 34fc716).

Owner pidió "ejecuta TODO de golpe para hacer un solo PR" tras triage.
9 items entregados en commits limpios (1 por item) según regla
sagrada CLAUDE.md §7. ENH-035 (#158) queda diferido a v2.0
(post-MVP, marcado por el owner).

Items entregados (en orden de implementación):
  · ENH-037 #167 → c5798bf  feat(web) — botón Nuevo Programa en /pmo/orgs/[id]
  · BUG-035  #163 → 7766281  fix(api,web) — RAID comments con nombre del autor
  · BUG-033  #160 → 3ad5e9a  fix(api,web) — UI superadmin dropdown role inline
  · BUG-032  #159 → 2f86f38  fix(api,web) — SA /me email change con take-over
  · ENH-036  #162 → a48aa2b  feat(web) — RAID detail edit form
  · BUG-034  #161 → 49358e8  fix(api,web) — documents download via presigned URL
  · BUG-036  #166 → e441a07  fix(api,web,infra) — scheduled reports (beat embed + run-now)
  · US-083   #165 → c740a59  feat(api,web) — charter universal + descarga DOCX/PDF
  · US-082   #164 → 3533d21  feat(api,web) — tickets de permisos tenant→SA

Migraciones agregadas (auto-aplican al deploy via Dockerfile CMD):
- 0030 charter_for_legacy_projects (data — backfill rows vacías)
- 0031 permission_change_requests

Pendiente owner:
- Revisar PR (1 solo PR con todos los commits).
- En Railway: confirmar que el redeploy del worker aplica el cambio
  del worker.railway.toml (--beat embedded para BUG-036).
- BUG-032: probar el flow de take-over de email si hay clash al
  cambiar a daguilar1601@gmail.com.
- BUG-036: validar que el botón "Enviar ahora" dispara el correo
  end-to-end.

Naming convention nueva (próxima sesión):
- Per instrucción del owner 2026-04-25, las próximas branches
  seguirán el formato: sprint{N}-{ddmmyy}-{merge_order}-{code}
  (ej. sprint8-280426-1-cleanup).

--- contexto Sprint 7 triage ---
Triage 2026-04-25:
- 9 issues needs-rework analizados (#50, #78, #105, #111, #113, #125,
  #126, #127, #130).
- 9 cerrados como `completed` (scope original cumplido en cada uno;
  gaps reportados se separan en issues nuevos).
- 10 issues nuevos creados (Sprint 7):
  · #158 ENH-035 — Análisis profundo CI tests (post-MVP, v2.0).
  · #159 BUG-032 — SuperAdmin /me no permite cambiar email.
  · #160 BUG-033 — UI gestión users sin opción modificar rol.
  · #161 BUG-034 — Documents R2: link "Abrir" da 404 (presigned URL).
  · #162 ENH-036 — RAID página detalle sin opción editar.
  · #163 BUG-035 — RAID comments muestran user ID en vez de nombre.
  · #164 US-082 — Tenant admin: ticket cambio permisos → SuperAdmin.
  · #165 US-083 — Charter universal: migración legacy + descarga DOCX/PDF.
  · #166 BUG-036 — Reportes calendarizados no envían correo (Resend/beat).
  · #167 ENH-037 — /pmo/organizations/[id]: botón "Nuevo Programa".

Decisiones owner (vía AskUserQuestion 2026-04-25):
- PR #156 (Sprint 6) está mergeado y deployed → bugs de #125/#127/#113
  son reales, no cache stale.
- Charter legacy: migración data Alembic (no lazy on-demand).
- US-082: tabla + flujo nuevos, no se reutiliza Solicitudes EP005.
- ENH-036 alcance: solo página detalle dedicada (no preview panel).

Pendiente owner para arrancar Sprint 7:
- Revisar los 10 issues nuevos (#158-#167).
- Asignar `status:ready` a los que apruebe (mínimo recomendado:
  Bloque 0 hotfix → BUG-032 + BUG-033).
- Confirmar orden de bloques (default: 0 → 1 → 2 → 3 → 4 → 5).

--- contexto Sprint 6 cerrado ---
Sprint 6 v1.5 ✅ COMPLETO. Branch: claude/debug-admin-permissions-n3Yop
PR #156 mergeado a main (confirmado por owner 2026-04-25).

5/5 items entregados (US-076 a US-080). Suite 339 pass / 1 skip.

PRs / commits:
- US-076 (#151) → fabf8c3  feat(api) — capability model + migración 0028
- US-077 (#152) → fc93bb3  feat(web,api) — borra /admin/roles legacy
- US-079 (#154) → 2a0315a  test(api) — matriz role × endpoint
- US-078 (#153) → 1fc8ad8  feat(api,web) — UI users + exclusions + migración 0029
- US-080 (#155) → consolidación de docs

Migraciones aplican automáticamente al deploy (CMD del Dockerfile).
```

---

## 📥 INBOX / TRIAGE

> Issues recién creados que todavía no han sido asignados a un Bloque.
> Vacío al cierre del Sprint 8. BUG-038 #181 cerrado como `not_planned`
> (sin repro disponible; código auditado usa single source of truth).

```
(vacío)
```

---

## ⏳ QUEUE

**Sprint 10 (v1.9) — TRIAGE COMPLETO 2026-05-05.**
**Bloque 6 (reportes) marcado `status:ready` por owner 2026-05-05.**

Owner pidió planeación de los próximos 2 sprints + mejoras a la página de reportes.
15 issues en total: 10 en 5 bloques plan/RAID/áreas + 3 reportes (Bloque 6, ready) + 2 bugs Sprint 11.

### Sprint 10 — Bloque 1: Plan visualización (3 ENHs)
- [ ] ENH-047 #196 — Toggle agrupación WBS en lista de tareas
- [ ] ENH-048 #197 — Filtros chip multi-select Hitos / Críticos / Retrasados
- [ ] ENH-049 #198 — Columna Responsable visible en lista

### Sprint 10 — Bloque 2: Plan template + columnas (3 items)
- [ ] ENH-050 #199 — Campo "Hito Relacionado" en form de tarea
- [ ] ENH-051 #200 — Campo "Criticidad" en form de tarea
- [ ] US-090  #201 — Columnas Outline Level (auto), Duration (auto, max 21d), Predecessors/Successors (asignables)

### Sprint 10 — Bloque 3: Plan import/export UX (2 ENHs)
- [ ] ENH-052 #202 — Botones Plantilla / Descargar / Importar en misma fila + colores distintos
- [ ] ENH-053 #203 — Mapeo de columnas asistido por IA al importar

### Sprint 10 — Bloque 4: RAID editable completo (1 ENH)
- [ ] ENH-054 #204 — Toda la información de ítems RAID editable inline/modal

### Sprint 10 — Bloque 5: Áreas / Equipos / Actores (1 US)
- [ ] US-091  #205 — Jerarquía Área→Equipo→Actor + teléfono + UI rediseñada (vista por área / por actor) + toggle de filtro

### Sprint 10 — Bloque 6: Reportes 3 vistas + cadencia mensual ✅ status:ready
- [ ] ENH-055 #209 — Reportes: layout 3 vistas (Catálogo / Historial / Creación) + implementa vista Catálogo
- [ ] US-092  #210 — Reportes: Historial de reportes generados (persistencia DB + R2)
- [ ] US-093  #211 — Reportes: Creación nueva con IA + preview (tercera vista)
- [ ] ENH-056 #212 — Reportes programados: cadencia mensual con día del mes (1-31) + clamp al último día
- Orden de implementación: ENH-055 → US-092 → ENH-056 → US-093 (US-093 depende de ENH-055 + US-092).

### Sprint 11 (v1.10) — Bloque 1: Nav review (2 BUGs)
- [ ] BUG-042 #206 — Breadcrumb desde Programa → link Org va a PMO en lugar de Admin
- [ ] BUG-043 #207 — Panel de Programa en vista PMO Org no es clicable
- [ ] (pasada con `ui-reviewer` agent comenzando por RAID, luego nav)

**Decisiones owner (vía clarificación 2026-05-05):**
1. US-090: Outline Level + Duration auto-calculadas (Duration max 21 días); Predecessors/Successors asignables como referencias WBS.
2. ENH-053: approach mínimo (heurística + LLM del tenant si AI habilitada; manual override siempre disponible).
3. US-091: mantener tabla `project_areas` con `type ∈ {area,actor,team}` pero agregar FK explícitas `team_id` + `area_id` + campo `phone`.
4. BUG-042/043: van a Sprint 11 como parte del nav review (no Bloque 0 hotfix).
5. Reportes Bloque 6: 3 vistas (Catálogo, Historial, Creación IA). ENH-055/US-092/US-093 = `status:ready`.

**Pendiente owner:**
- Revisar y asignar `status:ready` a los 12 issues plan/RAID/áreas (#196-#207, excluyendo reportes que ya están ready).
- Confirmar versión target (default propuesto: v1.9 Sprint 10, v1.10 Sprint 11).

**Próximo libre tras este triage:** US-094, BUG-044, ENH-057.

### Follow-ups identificados (Sprint 9+)
- US-081 — Borrar físicamente tablas `roles` + `user_roles` (migración 0036+) tras validación de Sprint 6 en producción.
- ENH futuro — Filtrado efectivo de queries por `organization_user_exclusions`.
- Cross-empresa nativo (post-ENH-043): si ≥3 grupos lo solicitan, abrir US con `program_organizations` + redesign listados.
- US-086 fase 2 — Cablear stakeholders FK en Charter (sponsor / business lead / technical lead) + migración data charters strings → stakeholders.
- US-084 fase 2 — Banner de divergencias cuando importadores MPP/XLSX detecten diferencia entre manual y calculado; botón "Resetear a calculado" en UI (endpoint backend ya existe).
- US-087 fase 2 — Campos `Task.hours_estimated/hours_actual` para que `compute_kpis` exponga horas plan/real.

---

## 🗂️ Sprint 8 (v1.7) — CERRADO

**13 items entregados (12 completed + 1 not_planned). Branch `claude/fix-issue-resolution-S3i4e`. Cerrado 2026-04-29 por batch cleanup (decisión owner: solucionar > documentar, ver CLAUDE.md §0).**

### Bloque 0 — Hotfix prod api deploy (1 item) ✅
- [x] BUG-039 — Boolean default Postgres-compatible en permission_change_requests — #184 ✅ 62c4f96

### Bloque 1 — Solicitud cambios chicos (3 items) ✅
- [x] ENH-038 — Mostrar fecha solicitud + agregar restricción entrega — #170 ✅ 86d5936
- [x] BUG-037 — Botón "Enviar" UX con indicadores de campos faltantes — #171 ✅ 09af27c
- [x] ENH-039 — Cambios: mostrar aprobador + fechas — #172 ✅ 04cf8a7

### Bloque 2 — Solicitud cambios medianos (2 items) ✅
- [x] ENH-040 — Presupuesto opcional — #173 ✅ c62109b
- [x] ENH-041 — BU select catálogo + "Otra…" — #174 ✅ b04818e

### Bloque 3 — Plan + Minutas UX (2 items) ✅
- [x] US-084 — Plan: edición manual con flag — #175 ✅ a6f5b7a
- [x] ENH-042 — Minutas: IA como primary action — #176 ✅ 58ee920

### Bloque 4 — Cambios grandes (3 items) ✅ (MVP foundation)
- [x] US-085 — Solicitud "Otra…" org + creación inactiva + notif — #177 ✅ 21eb835
- [x] US-086 — Stakeholders catálogo Opción B — #178 ✅ (sha en branch)
- [x] US-087 — Reportes KPIs numéricos + fechas — #179 ✅ deee5a8

### Bloque 5 — Workaround docs (1 item) ✅
- [x] ENH-043 — Programas cross-empresa workaround + ADR-016 — #180 ✅ 6cf20c4

### Bloque 6 — CI improvement (1 item) ✅
- [x] ENH-044 — CI gate alembic upgrade head Postgres efímero — #185 ✅ 2f9c458

### Reverificados — ya implementados en Sprint 7 ✅
- [x] BUG-035 — RAID detail sidebar muestra nombre — #163 ✅ 4193f24 (cherry-pick d85e642)
- [x] BUG-040 — Documents extensión preserva + 1MB — #186 ✅ a5c3a2c (cherry-pick 7e21280)
- [x] BUG-033 — role_type editable modal — #160 ✅ 711be4e (cherry-pick 5bf7d22)
- [x] ENH-036 — RAID detail edit form — #162 ✅ a48aa2b (Sprint 7)
- [x] US-082 — Tickets de permisos tenant→SA — #164 ✅ 3533d21 (Sprint 7)
- [x] US-083 — Charter universal + DOCX/PDF — #165 ✅ c740a59 (Sprint 7)

### Cerrados sin código (no_planned)
- [-] BUG-038 — Solicitud "Pendiente" + "Aprobada" simultáneo — #181 cerrado `not_planned`. Código auditado usa single source de `request.status` en todos los renders. Reabrir si el owner reproduce con ID + screenshot.

### Diferido a v2.0 (no bloqueante)
- ENH-035 #158 — Análisis profundo optimización CI tests pesados (post-MVP).

### Migraciones Alembic agregadas
- 0032 project_request_delivery_date (ENH-038).
- 0033 project_request_budget_nullable (ENH-040).
- 0034 project_manual_edited_fields (US-084).
- 0035 stakeholders_catalog (US-086).

---

## 🗂️ Sprint 7 (v1.6) — CERRADO

**10 items en 6 bloques (1 diferido a v2.0). PR #169 mergeado a main 2026-04-28.**

### Bloque 0 — Hotfix verificación post-Sprint 6 (2 items) ✅
- [x] BUG-032 — SuperAdmin /me email change con take-over — #159 ✅ 2f86f38
- [x] BUG-033 — UI superadmin dropdown role inline — #160 ✅ 3ad5e9a

### Bloque 1 — Charter universal + downloads (2 items) ✅
- [x] BUG-034 — Documents download via presigned URL R2 — #161 ✅ 49358e8
- [x] US-083 — Charter universal + descarga DOCX/PDF — #165 ✅ c740a59

### Bloque 2 — RAID polish (2 items) ✅
- [x] ENH-036 — RAID detail page edit form — #162 ✅ a48aa2b
- [x] BUG-035 — RAID comments con nombre del autor — #163 ✅ 7766281

### Bloque 3 — Reportes Resend funcional (1 item) ✅
- [x] BUG-036 — Scheduled reports beat + run-now — #166 ✅ e441a07

### Bloque 4 — Tenant ↔ SuperAdmin permission tickets (1 item) ✅
- [x] US-082 — Tickets de permisos con notif email — #164 ✅ 3533d21

### Bloque 5 — UX programas (1 item) ✅
- [x] ENH-037 — Botón Nuevo Programa /pmo/orgs/[id] — #167 ✅ c5798bf

### Diferido a v2.0
- ENH-035 #158 — Análisis profundo optimización CI tests pesados (post-MVP).

---

## 🗂️ Sprint 6 (v1.5) — CERRADO

**5 items en 5 bloques. PR #156 mergeado a main 2026-04-25.**

### Bloque 1 — Refactor backend del modelo de permisos (1 item) ✅
- [x] US-076 — Modelo capability-based + migración 0028 + barrido endpoints — #151 ✅ fabf8c3

### Bloque 2 — Eliminar UI/endpoints legacy de roles (1 item) ✅
- [x] US-077 — Borrar `/admin/roles/*`, `role-editor.tsx`, `admin_roles.py`, limpiar `admin.ts` — #152 ✅ fc93bb3

### Bloque 3 — UI nueva gestión users + capabilities + org membership (1 item) ✅
- [x] US-078 — `/admin/users/[id]` (10 acciones) + `/admin/permissions` + migración 0029 (exclusions) — #153 ✅ 1fc8ad8

### Bloque 4 — Tests de matriz role × endpoint (1 item) ✅
- [x] US-079 — `test_permission_matrix.py` con clasificación estática + fail-on-unknown — #154 ✅ 2a0315a

### Bloque 5 — Cierre: actualización de documentación (1 item) ✅
- [x] US-080 — Consolidar EP001, DECISIONS (anotaciones DEC-020/021), DB-CHANGES, CLAUDE.md §2, SPRINT.md — #155 ✅

---

## 🗂️ Sprint 5 (v1.4) — CERRADO

**10 items en 6 bloques + 1 follow-up. Todos mergeados a main.**

### Bloque 0 — Hotfix admin lockout (1 item) ✅ MERGEADO
- [x] BUG-031 — Admin lockout post-US-059/060 — #121 ✅ PR #129

### Bloque 0.5 — Infra CI (3 items) ✅ COMPLETO
- [x] ENH-030 — Acelerar suite de tests + CI (Fase 1/2/3) — #130 ✅ PR #131
- [x] ENH-032 + ENH-033 — Ruff cleanup + path filters + concurrency cancel — #133/#138 ✅ PR #139 (consolidados)
- [x] ENH-031 — Engine session-scoped + clean tables per test — #132 ✅ PR #141 (a5cfab1)

### Bloque 1 — SuperAdmin safety net (3 items) ✅ COMPLETO
- [x] US-072 — SuperAdmin: editar `role_type` de usuarios — #125 ✅ PR #134
- [x] US-073 — SuperAdmin: overrides permisos por tenant (DEC-021) — #126 ✅ PR #140 (migración 0027)
- [x] US-074 — SuperAdmin: cambiar email + password — #127 ✅ PR #134

### Bloque 2 — Import inteligente de planes (3 items) ✅ COMPLETO
- [x] US-069 — Import MPP nativo vía MPXJ (OpenJDK 21 + MPXJ 13.7.0) — #122 ✅ PR #143
- [x] US-070 — Wizard de mapeo de columnas Excel/CSV/MPP — #123
  - [x] Sub-bloque A: backend `/preview` + `/confirm` + Redis + CSV parser (PR #146)
  - [x] Sub-bloque B: frontend `import-wizard.tsx` + plan/page.tsx wired
- [x] US-071 — Plantilla vacía descargable del plan — #124 ✅ PR #135

### Bloque 3 — Refactor navegación TO-BE (1 item — mega-US completa) ✅
- [x] US-075 — Recursos de proyecto bajo `/pmo/*` (DEC-022) — #128
  - [x] Sub-bloque A: mover rutas + redirects 301 (33b0c7a)
  - [x] Sub-bloque C: sidebar OrgTreeNav + ADMIN_NAV gate (33b0c7a)
  - [x] Sub-bloque B: páginas informativas (`/pmo/programs/*` cards +
        KPIs en `/pmo/organizations/[id]`)

### Follow-ups detectados durante ejecución
- [x] ENH-034 — Diagnosticar bottleneck 38s en 9 tests (cierra CA2 <60s de ENH-031) — #142 ✅ fix-committed (causa: Celery .delay() esperaba broker Redis ausente)

---

## ✅ DONE

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo de Sprint 1 (v1.0 MVP, 94 items) y Sprint 2 (v1.1, 18 items).**

Sprint 2 v1.1 cerrado 2026-04-23. 4 bloques completos + hotfix Railway.

Sprint 3 v1.2 cerrado 2026-04-24 — 2 bloques:
- Bloque 1 (2 items): ENH-021 #96 + US-063 #95.
- Bloque 2 (3 items): BUG-027 #100 + ENH-022 #102 + ENH-023 #103.

---

## 📋 Backlog Sprint 2 (v1.1 — CERRADO)

### Bloque 1 — Sprint 2 Setup: navegación + bugs + permisos (7 items) ✅ COMPLETO
- [x] BUG-026 — Auth: timeout de inactividad a 15 minutos — #87 ✅ 77dc093
- [x] US-055 — Export tareas (CSV/Excel) — Opción A: botón descarga instantánea — #71 ✅ 023a99c
- [x] ENH-012 — Sidebar: reorganizar con módulo "Módulos de Proyecto" — #72 ✅ e2e420f
- [x] ENH-013 — Botón "Nuevo Programa" abre modal en Organizaciones — #73 ✅ b47f19a
- [x] BUG-023 — Project Charter: link a editor cuando no hay archivo (404) — #74 ✅ d81d036
- [x] BUG-024 — Lógica de uploads no configurada — #75 ✅ 3cd997d
- [x] BUG-025 — Rol "Reportes" sin módulo de permisos — #76 ✅ b1954c7

### Bloque 2 — Sprint 2 Reportes + Dashboard (5 items) ✅ COMPLETO
- [x] ENH-014 — Reportes: renombrar archivo con datetime + preview PDF — #77 ✅ 02cfaa6
- [x] US-056 — Calendarizar envío automático de reportes vía Resend — #78 ✅ 51947ef
- [x] ENH-015 — Dashboard: expandir barra de navegación — #80 ✅ 55956f9
- [x] ENH-017 — RAID: filtros en línea horizontal — #82 ✅ 6832199
- [x] ENH-016 — Solicitudes: permitir reabrir si proyecto no existe — #81 ✅ ade6ee7

### Bloque 3 — Sprint 2 RAID + Áreas (5 items) ✅ COMPLETO
- [x] ENH-019 — RAID: filtros avanzados (status + severidad/prioridad) — #85 ✅ fe3b001
- [x] ENH-018 — RAID: agregar toggle Kanban — #84 ✅ c894f12
- [x] US-058 — RAID: preview panel editable con comentarios (parcial — ver issue) — #83 ✅ e239caa
- [x] ENH-020 — Áreas: permitir múltiples recursos/contactos — #86 ✅ 009c0f2
- [x] US-062 — Áreas/Recursos: Area Leader + recursos asignados (moved from v1.2) — #91 ✅ 009c0f2

### Bloque 4 — Sprint 2 IA multi-modo (1 item) ✅ COMPLETO
- [x] US-057 — IA multi-modo por tenant: disabled / platform (Groq) / byo — #79 ✅ (9 commits, 8e4c385…be2a2ac; hotfix 40c4176)

---

## 📋 Backlog Sprint 3 (v1.2 — CERRADO)

### Bloque 1 — Sprint 3 Limpieza post-v1.1 + Auth self-service (2 items) ✅ COMPLETO
- [x] ENH-021 — Superadmin AI: quitar defaults editables de Ollama — #96 ✅ b70c887
- [x] US-063 — Recuperación y cambio de contraseña con envío por correo — #95 ✅ (6 commits, af4c9c3…7222dac)

### Bloque 2 — Sprint 3 Cleanup IA legacy post-DEC-017 (3 items) ✅ COMPLETO (pending merge)
- [x] BUG-027 — /admin/tenant config: retirar dropdown "Modo IA" + form Ollama Tailscale + endpoint backend + runbooks archivados + runbook BYO nuevo — #100 ✅ 1b62045
- [x] ENH-022 — Housekeeping docs/ai/ (4 archivos legacy a archive) + archivar EP016 + actualizar refs cruzadas — #102 ✅ 6315d19
- [x] ENH-023 — Retirar sidecar Tailscale del worker (start-worker.sh + Dockerfile custom + env vars TS_AUTHKEY/HOSTNAME + tailscale-setup.md archivado) — #103 ✅ f541171

---

## 📋 Backlog Sprint 4 (v1.3 — ACTIVO)

> Sprint arranca 2026-04-24 tras cerrar el review post-Sprint 2/3 con
> el owner. Scope: **reworks del review + infra + RAID robusto + import
> project/excel + página PMO de organización**. Los 3 items de v2.0
> (US-059/060/061) siguen diferidos por DEC-018.
>
> **Reshuffle 2026-04-24:** BUG-028 movido a Bloque 2 (depende de
> US-066 + BUG-029). #40 y #50 reintegrados. US-068 creada para sub-B
> de #50. Total 14 items.

### Bloque 1 — Reworks del review (8 items)
- [x] BUG-015 — Dashboard: botón "Exportar CSV" en 2 líneas (rework) — #40 ✅ d3523bb
- [x] BUG-029 — Upload de Excel falla + botón "Choose file" sin styling — #105 ✅ 3f6ac90
- [x] ENH-003 — Modal directo "Nuevo programa" en `/admin/organizations` y `/admin/programs` (sub-A) — #50 ✅ b47f19a (ya resuelto por ENH-013 Sprint 2; owner re-valida en deploy actual)
- [x] ENH-024 — Reporte: filename correcto al descargar — #106 ✅ 33c043c
- [x] ENH-025 — Filtros RAID siguen apilados (rework definitivo horizontales) — #107 ✅ ca9dc1d
- [x] ENH-026 — Consolidar "Panel de Gestión Avanzada" RAID en `/admin/raid` — #108 ✅ 8d69623
- [x] ENH-027 — Panel editable RAID (US-058) debe funcionar en `/admin/projects/[id]/raid` — #109 ✅ 3001959
- [x] ENH-028 — Export tareas: Excel MPP-like + naming PLAN-{Proyecto}-{Fecha} + CSV BOM UTF-8 — #110 ✅ f1db32a

### Bloque 2 — Infra + RAID robusto + charter + PMO (5 items) ✅ COMPLETO

- [x] US-066 — Uploads: object storage S3-compatible (Cloudflare R2) + runbook — #113 ✅ e0f9c2e (runbook ca5dd0c)
- [x] BUG-028 — Charter .docx real en bucket + editable desde documents — #104 ✅ 342e2b3
- [x] US-064 — RAID: área obligatoria + responsable + fechas + ordenamiento — #111 ✅ 798c89f
- [x] US-065 — RAID: página dedicada por ítem + historial — #112 ✅ 76277ac
- [x] US-068 — Página PMO de organización separada de admin — #116 ✅ 8f78d9b

### Bloque 3 — Import Project/Excel (1 item) ✅ COMPLETO
- [x] US-067 — Import XLSX → tareas (MPP follow-up documentado) — #114 ✅ e9ef28b

### Bloque 4 — Auth simplificada post-DEC-020 (2 items) ✅ COMPLETO
- [x] US-059 — Roles Admin/User/Viewer + backend gate — #88 ✅ 13eca87
- [x] US-060 — Hook useMyPermissions + gate UI — #89 ✅ 4fd19ca

---

## 📋 Backlog v2.0 (post-v1.3)

> **Contexto (DEC-020, 2026-04-24):** los 3 items originales de v2.0
> fueron recuperados o cancelados tras la decisión de no implementar
> aprobaciones jerárquicas. US-059 (#88) + US-060 (#89) bajaron a
> Sprint 4 v1.3 Bloque 4 con scope simplificado. US-061 (#90) está
> cancelada.

- [ ] (posibles items futuros: 2FA, SSO, magic-link login)

---

## Notas y cambios

- **2026-04-28 (Sprint 8 triage — feedback DRC Consultores):** owner
  manda documento con 16 items (feedback del socio) ya analizados.
  Triage:
  - **6 items "ya resueltos"** según owner — verificación en deploy
    actual sin issue nuevo: 2 (BU texto libre — REVIVIDO como ENH-041
    porque ahora pide patrón select+otra), 7, 9, 10, 12, 13 (existencia
    minutas IA — pero la jerarquía visual SÍ es cambio nuevo: ENH-042).
  - **11 issues nuevos creados (#170-#180):** distribuidos en 5 bloques
    (3 chicos + 2 medianos + 2 plan/UX + 3 grandes + 1 workaround).
  - **1 INBOX placeholder (#181 BUG-038):** esperando repro del owner.
  - **Sprint 8 v1.7 organizado en 5 bloques** + INBOX.
  - Decisiones owner (vía AskUserQuestion 2026-04-28):
    1. US-085 (Org libre #177): activación manual sin requisitos previos.
    2. US-086 (Stakeholders #178): **Opción B** — catálogo tenant.
       DEC-025 a registrar.
    3. ENH-043 (Cross-empresa #180): posponer cambio estructural,
       documentar workaround + ADR de diferimiento.
    4. BUG-038 (Estado simultáneo #181): postergar hasta repro.
  - Cleanup Sprint 7: las 9 issues #159-#167 (excepto #158 ENH-035) se
    movieron de `status:ready` a `status:fix-committed` (PR #169
    mergeado 2026-04-28). #158 ENH-035 pasó a `post-mvp` + `v2.0` sin
    `status:ready` (no se trabajará en v1.x).
- **2026-04-25 (Sprint 7 triage post-Sprint 6):** owner revisa los 9
  items con `status:needs-rework` y deja comments. Triage:
  - **9 cerrados como `completed`** (#50, #78, #105, #111, #113, #125,
    #126, #127, #130). Scope original cumplido en cada uno; los gaps
    se separan en issues nuevos.
  - **10 issues nuevos creados:** #158 ENH-035, #159 BUG-032, #160
    BUG-033, #161 BUG-034, #162 ENH-036, #163 BUG-035, #164 US-082,
    #165 US-083, #166 BUG-036, #167 ENH-037.
  - **Sprint 7 v1.6 organizado en 6 bloques** (Bloque 0 hotfix
    SuperAdmin → Bloque 1 charter+downloads → Bloque 2 RAID polish →
    Bloque 3 reportes Resend → Bloque 4 permission tickets → Bloque 5
    UX programas).
  - Decisiones owner (vía AskUserQuestion):
    1. PR #156 (Sprint 6) está mergeado y deployed → bugs reportados
       son reales, no cache stale.
    2. Charter legacy: **migración data Alembic** autogenera row vacía
       en `project_charters` para todo project sin charter (no lazy).
    3. US-082: **tabla + flujo nuevos** (`permission_change_requests`),
       no se reutiliza el módulo de Solicitudes (EP005).
    4. ENH-036: alcance solo página detalle dedicada (no preview panel).
  - Override CLAUDE.md: ENH-030 (#130) cerrado como `completed` aunque
    no llega a CA2 <60s — owner acepta el resultado actual ~3min para
    v1.x; análisis profundo se difiere a #158 (post-MVP / v2.0).
- **2026-04-24 (Sprint 5 sesión US-069):** entregada US-069 Import
  MPP nativo (commit `5ef2677`, branch `claude/sprint-pending-tasks-YhSdj`).
  Decisiones clave:
  - MPXJ 13.7.0 pinned en build-stage del Dockerfile (no hay
    `apps/worker/` separado — imagen compartida con api).
  - Wrapper Java propio (`MpxjCli.java`) en vez de CLI de terceros
    porque MPXJ no ships uno que emita el shape `ParsedTask`.
  - JRE 21 headless copiado desde `eclipse-temurin:21-jre-jammy`
    porque Debian Bookworm (base de python:3.12-slim) no trae
    openjdk-21 en repos default.
  - Tamaño incremental: ~225 MB (JRE 180 + MPXJ 45).
  - Tests mockean `subprocess.run` (sin fixture binario .mpp en repo).
  - Contrato `parse_mpp(data) -> XlsxParseResult` matchea el shape
    del parser XLSX — reutiliza `_TaskShim` del endpoint sin
    duplicar lógica de persistencia.
  Orden confirmado con owner para próximas sesiones: US-075 refactor
  `/pmo/*` → US-070 wizard (para que el wizard aterrice directo en
  `/pmo/projects/[id]/plan`).
- **2026-04-24 (Sprint 5 sesión ejecución):** entregados 7 items en
  ~8h (5 nuevos en sesión + BUG-031 + ENH-030 que venían). Branches
  recomendadas para mergear (orden por dependencia):
  1. PR #131 `claude/optimize-ci-tests-ac3u8` (ENH-030 — infra CI).
  2. `claude/sprint-5-cleanup-ruff` (ENH-032 — limpieza cosmética).
  3. `claude/sprint-5-superadmin-block` (US-072 + US-074).
  4. `claude/sprint-5-superadmin-overrides` (US-073 — incluye
     migración 0027 + cambio en `CurrentUser.has()`).
  5. `claude/sprint-5-import-block` (US-071 — plantilla vacía,
     independiente).
  Conflictos esperados: `apps/web/lib/api/superadmin.ts` se toca
  en branches 3 y 4 (anexos al final, fácil resolver). `SPRINT.md`
  se toca en varias branches (el último merge gana). `apps/api/app/
  api/v1/endpoints/superadmin.py` también — conflicto trivial
  porque cada branch agrega bloques distintos al final del archivo.
  Migraciones a aplicar en Railway: **0024, 0025, 0026, 0027**.
- **2026-04-24 (Sprint 5 kickoff):** owner reporta BUG crítico de
  admin lockout post-Sprint 4 (todas las rutas `/admin/*` devuelven
  "Falta permiso admin.X:read"). Diagnóstico: US-059 introdujo
  mapping estático sin prefijo `admin.*` pero los endpoints siguen
  exigiendo `"admin.users"`, `"admin.roles"`, etc. BUG-031 creado
  con `status:ready` directo (hotfix P0).
- **2026-04-24 (Sprint 5 triage):** owner aprobó 8 items para el
  sprint distribuidos en 4 bloques:
  - Bloque 0: BUG-031 hotfix (#121).
  - Bloque 1 SuperAdmin safety net: US-072 (#125), US-073 (#126),
    US-074 (#127). DEC-021 registrada (overrides permisos por tenant).
  - Bloque 2 Import inteligente: US-069 MPP (#122), US-070 wizard de
    mapeo (#123), US-071 plantilla vacía (#124).
  - Bloque 3 Refactor navegación: US-075 `/pmo/*` namespace (#128).
    DEC-022 registrada (namespaces `/pmo` negocio vs `/admin`
    sistema). Evaluación DEC-023 (`/{tenant_slug}` prefix) queda
    como follow-up ADR. ENH-029 absorbido por US-075.
- **2026-04-24 (reshuffle #2 — US-066 promovida):** owner reporta que
  los docs de Railway Volume (`SETUP.md` §4.1, `DEPLOYMENT.md` §4)
  están incorrectos — Railway no permite compartir volumes entre
  servicios. Sin storage persistente los uploads se pierden en cada
  redeploy, bloqueando el resto del testing. **US-066 (#113)
  promovida a prioridad inmediata** antes de seguir el Bloque 1.
  Nueva estrategia: **object storage S3-compatible (Cloudflare R2)**,
  cero egress fees + free tier 10 GB. Runbook completo entregado en
  `docs/runbooks/infra/uploads-storage.md` con 12 secciones
  (bucket + token + env vars + smoke + código + backup + rollback +
  troubleshooting). SETUP.md y DEPLOYMENT.md corregidos.
- **2026-04-24 (DEC-020 mid-Sprint 4):** owner redefine la plataforma
  como herramienta de apoyo/visualización — sin aprobaciones
  jerárquicas. Consecuencia: US-059 (#88) + US-060 (#89) bajan de v2.0
  al Bloque 4 del Sprint 4 v1.3 con scope reducido (3 roles fijos:
  Admin/User/Viewer + permisos estáticos por rol). US-061 (#90)
  cancelada. El permiso `reports` pendiente de BUG-025 se absorbe en
  US-060 como parte del rol `User`. Total Sprint 4: 16 items (8+5+1+2).
- **2026-04-24 (Sprint 4 reshuffle):** owner revisa el plan inicial
  y pide considerar #40, #50, #103 + mover BUG-028 al Bloque 2 por
  dependencia con US-066 + BUG-029 (charter real requiere storage
  persistente + upload funcional). Acciones:
  - BUG-015 #40 y ENH-003 #50 reintegrados al Bloque 1 con scope
    clarificado en comentarios.
  - BUG-028 #104 re-scoped a "generar PDF real del charter" + movido
    a Bloque 2 después de US-066.
  - Nueva US-068 #116 para sub-problema B de #50 (página PMO de
    organización separada de admin) en Bloque 2.
  - #103 identificado como pending-merge (no requiere issue nuevo;
    documentado en comentario).
  - US-060 (#89) y US-061 (#90) documentados con contexto DEC-018
    para que owner pueda cerrarlos con `not_planned`.
  - Introducido label `status:ready` en CLAUDE.md §5 como gate de
    arranque: Claude espera `status:ready` antes de tocar código.
  - Total Sprint 4: 14 items (8+5+1).
- **2026-04-24 (Sprint 4 kickoff):** owner revisa Sprint 2/3 y reporta
  7 items con `needs-rework` + pide RAID robusto (área obligatoria,
  fechas, página dedicada, ordenamiento) + import XLSX/MPP. Se crean
  11 issues (#104-#114) en 3 bloques. Scope completo confirmado por
  owner (ningún corte). Import MPP requiere Java 21 + MPXJ en worker
  (flag de riesgo dentro del issue US-067).
- **2026-04-23 (post-v1.1):** owner define scope de Sprint 3 v1.2:
  solo limpieza Ollama + password reset (ENH-021 + US-063). Los 3
  items originales de v1.2 (#88/#89/#90) pasan a v2.0 por ser un
  major overhaul de Auth/Roles/Aprobaciones. Ver **DEC-018**.
- **2026-04-22 (Sprint 2 intake):** 21 issues clasificados en 4
  bloques v1.1 + 3 items v1.2 (luego reclasificados a v2.0 el
  2026-04-23).

---

## Instrucción para Claude Code

Al iniciar sesión, lee este archivo y los epics relevantes para las US en cola.
Trabaja el backlog en orden sin parar entre US. Por cada US:
1. Implementa la US completa.
2. Haz commit con el mensaje indicado antes de tocar la siguiente.
3. Mueve la US de IN-PROGRESS a DONE con fecha de hoy.
4. Mueve la primera US de QUEUE a IN-PROGRESS.
5. Arranca la siguiente US de inmediato.

Continúa hasta que no queden US en QUEUE o el contexto se agote.
Si el contexto se agota a mitad de una US, haz commit del avance con prefijo `wip:` y anota aquí dónde quedó.
