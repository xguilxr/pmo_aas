# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-29 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Batch "Roles + Visibilidad PM + Catálogo por Org + Nav Sin Programa" (2026-06-08)
Branch: claude/friendly-bell-EYlVB

Sprint 34 Bloque 1 COMPLETO — todos los issues en status:fix-committed.
Pendiente PR y verificación del owner.
```

---

## 📥 INBOX / TRIAGE

### Sprint 34 — Bloque 1 — Roles + Visibilidad + Recursos (branch: claude/friendly-bell-EYlVB)

Aprobado por owner 2026-06-08 (plan + decisiones en sesión).

- [x] **ENH-159 #551** — Nav sidebar: proyectos sin programa bajo "Sin Programa". `status:fix-committed`
- [x] **US-166 #552** — Rol `pm_sr`: nuevo role_type con acceso admin completo. `status:fix-committed`
- [x] **US-167 #553** — Modelo `UserScopeAssignment`: asignaciones de visibilidad para PM. `status:fix-committed`
- [ ] **US-168 #554** — Filtrado de API y sidebar por visibilidad de PM. `status:in-progress`
- [x] **US-169 #555** — UI: árbol de asignación Org→Prog→Proyecto en admin de usuarios. `status:fix-committed`
- [x] **US-170 #556** — Catálogo de áreas/equipos/actores a nivel organización. `status:fix-committed`

### Cross-cutting / sin sprint asignado
- [ ] **ENH-115 #434** — Breadcrumbs consistentes en `/pmo/**/reports`. `status:ready` desde 2026-05-23 pero diferido al cierre del rediseño grande. Owner pasa a ready o reasigna sprint cuando lo prioriza.

### Batch previo pendiente de PR
- `claude/gantt-areas-fixes` — `status:fix-committed`. Owner crea PR manualmente:
  ENH-149 #544, BUG-075 #545, ENH-154 #546, ENH-152 #547.

---

## ⏸️ Deferred — re-evaluación post EP020

> Issues abiertos sin asignación de versión. Se retoman cuando owner decida.

### IA conversacional global (ex Sprint 17 Bloque 1)
- [ ] US-102 #255 — Side-panel chat IA en cada página (Ctrl+K + flotante)
- [ ] ENH-074 #256 — Context-awareness por página
- [ ] ENH-075 #257 — Tool-use (crear tarea / RAID / nav)
- [ ] ENH-076 #258 — Historial persistente + summary rolling

**Decisión owner 2026-05-08:** posterga el chat global. Volver a evaluar necesidad post-EP020.

### Pendiente redefinición Áreas/Recursos (cubierto parcial por EP017 Sprint 25)
- [ ] **US-105 #311** — Import Plan: wizard matching responsables → Actor.
- [ ] **Tab Organigrama de US-106** — placeholder UI; cableado funcional depende del paquete EP017 final.
- [ ] **US-119 #414** — EP017 cleanup: drop legacy `actors.team_id`, `actors.is_lead`, `teams.area_id`, `tasks/risks/issues.area_id`. **Bloqueado por ENH-109.**
- [ ] **ENH-109 #417** — PersonPicker cableado en formularios existentes. **Bloquea US-119 y ENH-110.**
- [ ] **ENH-110 #418** — Filtros / agrupadores de Plan por dimensiones derivadas. Depende de ENH-109.
- [ ] **US-133 #415** — US-118 Fase 2: RBAC migra a leer `project_participations`.
- [ ] **US-134 #416** — US-118 Fase 3: drop `project_members` table.

### Admin UI settings (cross — sin sprint asignado al rediseño Minutas/Reports)
- [ ] **ENH-111 #430** — UI admin tenant para `progress_calculation_method`.
- [ ] **ENH-112 #431** — UI admin tenant para `task_load_thresholds`.
- [ ] **ENH-113 #432** — UI admin org para upload `client_logo_url`.

### Reportes / snapshots (estado actualizado 2026-05-26)
- ✅ Snapshots periódicos de KPIs y semáforo → **implementado** (US-151, `metric_snapshots`, cadencia semanal).
- ✅ S-07 Curva-S → **implementado** (US-161, planeado lineal start→end).
- [ ] S-10 Entregables formales (concepto no configurado) — sigue diferido.

---

## ✅ DONE

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo.**

> Batches post-Sprint 33 (deepwork reportes/RAID/IA #524-528, big canvas #514-517, chrome #520-521) mergeados a main 2026-05-26/29 → archivados en `SPRINT-DONE-HISTORY.md` el 2026-06-05.

| Sprint | Versión | Cerrado | Items |
|---|---|---|---|
| 1 | v1.0 MVP | 2026-04-21 | ~94 (22 bloques) |
| 2 | v1.1 | 2026-04-23 | 18 |
| 3 | v1.2 | 2026-04-24 | 5 |
| 4 | v1.3 | 2026-04-24 | 14 |
| 5 | v1.4 | 2026-04-24 | 10 |
| 6 | v1.5 | 2026-04-25 | 5 |
| 7 | v1.6 | 2026-04-28 | 10 |
| 8 | v1.7 | 2026-04-29 | 13 |
| 9 | v1.8 | 2026-05-05 | 6 |
| 10 | v1.9 | 2026-05-06 | 14 |
| 11 | v1.9 | 2026-05-06 | 12 |
| 12 | v1.10/v1.11 | 2026-05-06 | 9 |
| 13 | v1.12 | 2026-05-07 | 7 |
| 14 | v1.13 | 2026-05-07 | 4 |
| 15 | v1.14 | 2026-05-07 | 4 |
| 16 | v1.14 | 2026-05-07 | 4 |
| 17 | v1.16 | 2026-05-08 | 2 |
| 18 | v1.17 | 2026-05-08 | 3 |
| 19 | v1.18 | 2026-05-09 | 6 |
| 20 | v1.19 | 2026-05-09 | 5 |
| 21 | v1.20 | 2026-05-09 | 4 |
| 22 | v1.21 | 2026-05-09 | 2 |
| 23 | v1.22 | 2026-05-09 | 1 |
| 24 | v1.23 | 2026-05-09 | 12 |
| 25 | v1.24 | 2026-05-10 | 5 |
| 26 | v1.25 | 2026-05-22 | 16 (3 bloques — Minutas v1.0 + Dependencias EP020 + Backbone EP020) |
| 27-29 | v1.26 | 2026-05-25 | 10 (mega-PR EP020: US-123 a US-132) |
| 30-32 | v1.27 | 2026-05-23 | 22 (rediseño Minutas + Reports — ver `SPRINT-DONE-HISTORY.md`) |
| 33 | v1.28 | 2026-05-26 | 13 (Dashboards N1/N2 + reportes derivados + revamp + follow-ups — ver `SPRINT-DONE-HISTORY.md`) |

---

## 📋 Backlog v2.0 (post-v1.x)

> **Contexto (DEC-020):** plataforma definida como herramienta de apoyo/visualización sin aprobaciones jerárquicas.

- [ ] ENH-035 #158 — Análisis profundo optimización CI tests pesados.
- [ ] US-081 — Borrar físicamente tablas `roles` + `user_roles`.
- [ ] ENH futuro — Filtrado efectivo de queries por `organization_user_exclusions`.
- [ ] Cross-empresa nativo (post-ENH-043): si ≥3 grupos lo solicitan, abrir US con `program_organizations`.
- [ ] US-086 fase 2 — Cablear stakeholders FK en Charter.
- [ ] US-084 fase 2 — Banner de divergencias cuando importadores MPP/XLSX detecten diferencia entre manual y calculado.
- [ ] US-087 fase 2 — Campos `Task.hours_estimated/hours_actual`.
- [ ] Hard-delete User cuando hay `project_request.requested_by` (US-088 fase 2).
- [x] ~~Snapshots históricos de KPIs y semáforo~~ → hecho en v1.28 (US-151).
- [ ] KPIs custom por admin tenant.
- [ ] **Cleanup post-Sprint 32**: borrar `apps/web/app/(app)/pmo/projects/[id]/ai-minutes/` y `.../reports/tweak/` carpetas enteras (hoy son redirects 301). Tras 1 sprint en main sin reportes de bookmarks rotos.
- [ ] **Persistencia reports L1/L2** (PMO/Org/Prog): la **generación** ya existe (v1.28, US-160: PDF on-demand vía `/dashboard/reports/portfolio`, `/organizations/{id}/reports/status`, `/programs/{id}/reports/status`). Falta **persistir** el histórico: agregar `generator='pmo'|'organization'|'program'` + nullable `project_id` o tabla aparte.
- [ ] **Dirty-flag fino en builder** (mejora ENH-125): comparar canvas vs plantilla cargada para detectar cambios sin guardar incluso cuando hay `loadedTemplateId`.
- [ ] **Export RAID — Lecciones/Cambios** (follow-up ENH-152): si se necesita exportar Lessons / ChangeRequests, abrir un export aparte (ENH-152 los descartó del XLSX RAID por decisión del owner 2026-06-05).

---

## Notas y cambios recientes

> Histórico de sprints anteriores en `SPRINT-DONE-HISTORY.md`.

- **2026-06-08 (batch Roles+Visibilidad+Recursos — branch claude/friendly-bell-EYlVB):**
  6 issues creados: ENH-159 #551, US-166 #552, US-167 #553, US-168 #554, US-169 #555, US-170 #556.
  Próximo libre: US-171, BUG-078, ENH-160.
- **2026-06-06 (batch feedback owner — MERGED #549 a main 2026-06-07):**
  branch `claude/owner-feedback-batch`, 5 commits atómicos, sin migraciones.
  CI verde, tsc/ruff/lint limpios.
  - **ENH-155** — avance derivado del plan (rollup WBS jerárquico): padre =
    promedio de avance de hijos recursivo; general = promedio de nivel más
    alto. Read-side en lista de tareas, resumen de proyectos, detalle,
    dashboard (KPIs/charts/plan-vs-actual) y reporte de avance; manual como
    fallback para proyectos sin plan. Helper `compute_wbs_rollup` +
    `round_half_up` en `plan_metadata.py`.
  - **ENH-156** — salud/semáforo solo-color (sin "Green"/"Verde"): reporte de
    avance (`.dot`), charter `.docx` (● coloreado) y 5 vistas read-only del
    front. No se tocaron los selectores interactivos.
  - **ENH-157** — logos PMO+cliente en el `.docx` del charter
    (`resolve_charter_logos`, disco + httpx, solo PNG/JPEG). Complementa
    ENH-153, que cubrió el header HTML/PDF.
  - **ENH-158** — borrar/cancelar tickets de RAID/Lecciones/Cambios:
    soft-delete + audit; Cambios además cancela (status `cancelled`) e
    invalida los ApprovalToken EP019. Cualquier miembro puede hacerlo.
  - **BUG-077** — guardar minuta devolvía 422 (título < 2 chars): guard ≥2 +
    parser del 422 nativo de FastAPI en `lib/api.ts`. Re-aplicado en
    `minutes/new/page.tsx` tras el merge (el llenado manual se movió ahí).
  ⚠️ **Nota de IDs:** los commits aterrizaron etiquetados `ENH-109/110/111/112`
  y `BUG-062` — se eligieron contra una base desactualizada (`9c904a2`,
  max ENH-108/BUG-061) antes de ver los 196 commits de main, que ya habían
  consumido esos números (ENH-109/110 = #417/#418, ENH-111/112 = #430/#431,
  BUG-062 = "click en minuta abre el detail"). Historia ya mergeada → **no se
  reescribe**; los IDs **canónicos** de este batch son **ENH-155..158 /
  BUG-077** (los labels de commit quedan como referencia histórica).
- **2026-06-05 (batch gantt/áreas/reportes/RAID fixes):** branch
  `claude/gantt-areas-fixes`, 9 commits de trabajo, `status:fix-committed`,
  **sin PR aún**. Sesión previa: BUG-073/074/076 #538/539/542 +
  ENH-150/151/153 #540/541/543. Esta sesión cerró los 4 temas restantes:
  ENH-149 #544 (ya estaba implementado, solo verificación), BUG-075 #545
  (estado RAID editable), ENH-154 #546 (sección Acciones en Seguimiento),
  ENH-152 #547 (export RAID XLSX 4 hojas ES unificado). Sin migraciones.
  Epics EP006/EP014/EP018 actualizadas. Branch detrás de origin/main →
  rebase al armar el PR si CI lo pide.
- **2026-05-26/29 (3 batches mergeados):** deepwork reportes/RAID/IA
  (#524-528, mig. 0084), big canvas (#514-517, migs 0082/0083), chrome
  logo/iconos (#520-521). Archivados en `SPRINT-DONE-HISTORY.md`.

---

## Instrucción para Claude Code

Cuando arranques una sesión nueva:

1. Lee `docs/project-management/HANDOFF.md` PRIMERO.
2. Luego `CLAUDE.md` + este archivo + el epic referenciado en IN-PROGRESS.
3. Mueve la siguiente US/ENH/BUG de **INBOX** (marcada `status:ready`) a **IN-PROGRESS** antes de empezar.
4. Cambia label del issue: `status:ready` → `status:in-progress`.
5. Implementa con tests verdes + typecheck.
6. Commit con header `<tipo>(<scope>): <ID> — <desc> (refs #<issue>)` y push.
7. Cambia label → `status:fix-committed` + comment con template CLAUDE.md §3 paso 6.
8. Mueve item a DONE en este archivo o a la tabla histórica si cierra sprint.
9. Resumen de ronda al owner siguiendo CLAUDE.md §11.
10. Al cierre de sesión: invocar `/handoff` para limpiar SPRINT.md y dejar bridge.

**Regla sagrada:** 1 US = 1 commit. No mezclar varios IDs en el mismo commit.

**Regla post-Sprint 26 (decisión owner 2026-05-22):** desarrollo secuencial puro. 1 sesión activa, 1 lane, 1 branch. Migraciones consecutivas sin paralelización.
