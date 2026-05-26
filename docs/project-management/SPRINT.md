# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-29 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Batch "bugs logos + /pmo + rediseño big canvas" (2026-05-26) en branch
claude/friendly-lamport-LZ45l. 4 commits, status:fix-committed, esperando
MERGE + QA visual del owner:

- BUG-068 #514 (e87c55f + 70f377a) — upload PNG de logos de org (data-URL en
  DB, mig. 0082) + preview circular. Follow-up: logo del **tenant** también a
  data-URL (mig. 0083) — arregla el 401 del serve endpoint con `<img>`.
- ENH-142 #515 (1ad5ed3) — botones crear org/programa/proyecto en /pmo.
- ENH-143 #516 (c7551b4) — org detail: botón Nuevo proyecto, renombra Status,
  quita toggle Resumen/Reportes.
- US-164 #517 (766f9f4) — rediseño "big canvas" global (lienzo cream + sidebar
  azul flotante + topbar full-width + fix tab-strip + iconos + pinch-zoom +
  dark mode). Supersede chrome navy DEC-006.

tsc + next build verdes; tests EP002 (26) + US-031 (data-URL) + BUG-068 verdes.
Migraciones nuevas pendientes de aplicar en Railway: 0082 + 0083 (además de
0079-0081 si aún no se aplicaron).

Follow-up doc diferido (US-164): navigation.md + ADR/DEC del supersede de
chrome navy DEC-006.

Próximo libre: US-165, BUG-069, ENH-144.
```

---

## 📥 INBOX / TRIAGE

### Cross-cutting / sin sprint asignado
- [ ] **ENH-115 #434** — Breadcrumbs consistentes en `/pmo/**/reports`. `status:ready` desde 2026-05-23 pero diferido al cierre del rediseño grande. Owner pasa a ready o reasigna sprint cuando lo prioriza.

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

---

## Notas y cambios recientes

> Histórico de sprints anteriores en `SPRINT-DONE-HISTORY.md`.

- **2026-05-26 (batch bugs logos + /pmo + rediseño big canvas):** branch
  `claude/friendly-lamport-LZ45l`, 4 commits (BUG-068 #514, ENH-142 #515,
  ENH-143 #516, US-164 #517), `status:fix-committed`. Esperando merge + QA
  visual. Rediseño "big canvas" supersede el chrome navy DEC-006 (sidebar azul
  flotante + lienzo cream). Mig. nueva: 0082 (logos org → TEXT). Doc follow-up
  diferido: navigation.md + ADR del cambio de chrome.
- **2026-05-26 (Sprint 33 / v1.28 — Dashboards N1/N2 + reportes derivados + revamp):**
  branch `claude/laughing-carson-stUJu`, 19 commits, **esperando merge + QA**.
  - **Datos:** `MetricSnapshot` (foto semanal 4 niveles, mig. 0079) + endpoints
    analytics (trends/risk-matrix/heatmap/treemap/capture).
  - **Dashboards:** primitivos SVG (Gauge/TrendLines/RiskMatrix/Heatmap/Treemap) +
    rediseño de `/dashboard`, `/pmo`, org y programa con sus visuales.
  - **Reportes derivados:** secciones builder S-05/S-07/S-15 (migs. 0080/0081) +
    reportes de status N1/N2 en PDF (fuera del builder) con heatmap/treemap/curva-S.
  - **Revamp v1:** radio de tarjetas 16→10px + `tabular-nums` global (navy/paleta intactos).
  - **Follow-ups:** vistas/reportes accesibles a PMs (scoped); `ProgressGauge` de
    #511 consolidado en `Gauge` compartido.
  - 583 tests backend + ruff + tsc + next build verdes; render real de PDF validado.
- **2026-05-26 (rediseño V1 project detail — #490-#510, ya en main):** branch
  `claude/practical-ptolemy-s7LyL` (#511 mergeado). Detalle en `SPRINT-DONE-HISTORY.md`.

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
