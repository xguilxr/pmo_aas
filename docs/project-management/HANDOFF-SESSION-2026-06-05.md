---
tipo: gestion
responsable: propietario
estado: historico
revisado: 2026-06-05
revisar_cada: nunca
---

# Handoff — pmo_aas — 2026-06-05

> **Histórico.** Puente de la sesión del 2026-06-05, conservado como registro.
> El puente vivo es siempre [`HANDOFF.md`](HANDOFF.md); este ya no describe
> dónde retomar.

> Foco de este handoff: **los 4 temas restantes** del batch de bugs/ENH que pidió
> el owner (2026-06-05). El bloque ya cerrado (6 temas) está al final como contexto.

## Estado
- Branch: `claude/gantt-areas-fixes` · Base: `main` · PR: **ninguno** (falta crearlo)
- Ahead of `origin/main`: 6 commits (todos pusheados)
- Working tree: **1 untracked → `apps/api/uv.lock`** (lo generó `uv run` durante los tests; NO commitear — `git checkout`/ignorar, o agregar a `.gitignore` si se decide adoptar lockfile uv)
- Sin migraciones nuevas, sin cambios de deps (lockfiles intactos)

## Contexto crítico (leer antes de seguir)
- **Status canónico de tarea = `not_started | in_progress | completed | on_hold`** (NO existe `done`). BUG-074 barrió todas las comparaciones `== "done"` en servicios de reporte. Si ves `done` en código de tarea, es bug.
- **`app/services/status_display.py`** (nuevo) = fuente única ES + color. Helpers `status_es()` / `status_badge_html()` y filtros Jinja `status_es` / `status_badge` (registrados en `pdf_renderer.py`).
- **Áreas son project-scoped** vía `area_assignments`. Pickers usan `listAreasByProject`; el catálogo `AreasAndTeamsPanel` (tab "Áreas y Equipos") ahora tiene toggle **Asignar/Quitar** por área (project context). Decisión del owner: project-scoped es main, catálogo tenant es soporte.
- **Glitch de commits**: ENH-151 y ENH-153 quedaron con `(refs #)` vacío (subshell de `gh issue list` no resolvió a tiempo). Link issue→commit vía SHA en el comment. **Para los próximos: crear el issue primero, capturar el número, recién commitear.**
- **IDs**: creados como GitHub issues → BUG-073/074/076 (#538/539/542), ENH-150/151/153 (#540/541/543). **Reservados sin crear aún**: BUG-075 (RAID estado), ENH-149 (plan end-date), ENH-152 (export RAID), ENH-154 (acciones seguimiento). Próximo ENH libre real = ENH-155; próximo BUG libre = BUG-077.
- Flujo del repo (CLAUDE.md): 1 issue = 1 commit · `tipo(scope): ID — desc (refs #N)` · push inmediato · label `status:fix-committed` + comment DoD. El owner pidió **cerrar** los nuevos sin review en este batch.

## Próximo — los 4 temas (en orden sugerido)

### 1. ENH-149 — Plan: editar fecha fin de tarea (chico, empezar por acá)
- **Objetivo**: poder actualizar `end_date` de una tarea para que no quede "atrasada por siempre".
- **Clave**: BUG-074 ya hizo que `_is_delayed` use `end_date < hoy AND status != completed`. Es decir, **empujar `end_date` al futuro YA des-marca la tarea**. Falta solo confirmar/exponer la edición de `end_date` en el form de tarea.
- **Próxima acción**: en `apps/web/app/(app)/pmo/projects/[id]/plan/page.tsx`, revisar el modal de **editar tarea** (~líneas 2005-2022 área picker; buscar el campo de fecha fin) y confirmar que (a) hay input de `end_date` editable y (b) `updateTask` (`apps/web/lib/api/tasks.ts`) manda `end_date`. Si falta, agregarlo. Backend: endpoint PATCH de tarea acepta `end_date` (verificar schema en `apps/api/app/api/v1/endpoints/tasks.py` o similar).

### 2. BUG-075 — RAID: estado no editable
- **Objetivo**: editar el `status` de cualquier item RAID (Riesgo/Acción/Incidencia/Decisión).
- **Próxima acción**: revisar `apps/web/components/raid-detail-page.tsx` (línea ~976 tiene el type de status) y `apps/web/components/raid-edit-fields.tsx` — agregar/exponer un `<Select>` de estado por tipo y cablearlo al update. Backend: confirmar que el endpoint de update de `risk_action` acepta `status` (enum del modelo `risk_action`; `ALLOWED_STATUSES` en `services/ai/validator.py` = Open/In Progress/Pending/Closed, pero verificar el enum real del modelo `RiskActionItem`).
- **Nota**: el usuario reportó esto en el contexto de Reportes → confirmar si es la página `/pmo/projects/[id]/raid` o la sección RAID del reporte. Probablemente la página RAID.

### 3. ENH-152 — Export RAID rework (el más grande)
- **Objetivo**: el botón "Exportar RAID" en `/pmo/projects/[id]/raid` debe:
  1. Nombre de archivo `RAID-[Nombre Proyecto]` (hoy: `raid_[id_proyecto]`).
  2. Usar como base el **generador del RAID de Documentos** (no el actual single-sheet mal formateado).
  3. 4 hojas en ES: **Riesgos / Acciones / Incidencias / Decisiones** (hoy: Risk/Issues/Lessons/Changes — mal).
  4. Columnas: Folio · Título · Descripción · Severidad/Prioridad · Estado · Responsable área · Responsable · Fecha creación.
  5. **Mismo archivo para ambos botones** (el de /raid y el de Documentos).
- **Próxima acción**: `grep -rn "raid_" apps/api` para hallar el export actual del botón /raid; ubicar el generador RAID de Documentos (probable `services/*raid*` o `services/charter_generator`-style con openpyxl). Consolidar ambos en el generador de Documentos con columnas/hojas/nombre nuevos. `filename_slug.artifact_filename` ya existe para el patrón `RAID-...`.

### 4. ENH-154 — Seguimiento: "Acciones" vigentes antes de "próximas"
- **Objetivo**: en el Reporte de Seguimiento, **antes** de "Actividades próximas", una sección **"Acciones"** = items RAID tipo Acción vigentes durante el período del reporte.
- **Próxima acción**: backend en `apps/api/app/services/operational_reports.py` (función que arma el contexto de seguimiento) — construir un grupo `groups_actions` (RAID acciones con fecha/vigencia dentro del período). Template `apps/api/app/templates/pdf/reports/seguimiento.html` — agregar `{{ render_group("Acciones", groups_actions, false) }}` antes del `render_group("Actividades próximas", ...)` en la línea ~66.

## Bloqueos / pendiente de input
- Ninguno bloqueante. ENH-152 conviene confirmar con el owner cuál es "el archivo de Documentos" exacto que quiere como base si hay >1 generador RAID.

## Acciones del owner (externas)
- [ ] (GitHub web) Crear PR `claude/gantt-areas-fixes` → `main` y mergear cuando esté listo el batch completo: https://github.com/xguilxr/pmo_aas/compare/main...claude/gantt-areas-fixes
- [ ] (App, post-merge) Smoke visual: reportes Avance/Seguimiento (status ES + color), Charter (logos), y Áreas → asignar un área y verla en tarea/RAID/Plan.
- [ ] Decidir destino de `apps/api/uv.lock` (descartar vs `.gitignore`).

## Cómo retomar
1. (Git Bash o WSL) `cd /c/Users/dagui/claude/pmo_aas && git checkout claude/gantt-areas-fixes && git pull`
2. (Git Bash) `git checkout -- apps/api/uv.lock 2>/dev/null; rm -f apps/api/uv.lock` — limpiar el artefacto untracked
3. (PowerShell, en `apps/api`) backend: `uv run uvicorn app.main:app --reload`
4. (PowerShell, en `apps/web`) front: `pnpm dev` (sin `pnpm install`, lockfile intacto)
5. Empezar por **ENH-149** (paso 1 arriba). Crear el issue primero: `gh issue create --title "[ENH-149] — …" --label "enhancement,EP006,status:in-progress"`, capturar el `#N`, luego commitear con `(refs #N)`.
6. (Backend tests por tema) `cd apps/api && uv run python -m pytest tests/ -k "<keyword>" -q` · (Front) `cd apps/web && pnpm exec tsc --noEmit`

---

## Apéndice — hecho esta sesión (6 temas cerrados)
- `593cb48` BUG-073 #538 — minuta: coerciona `summary` dict/list a str en `validate_minute_payload` (fix `TypeError` cross-chunk join).
- `7f7c272` BUG-074 #539 — sweep `done`→`completed` en `snapshots/operational_reports/progress_calculator/reports/engine` (+ fixtures). Causa raíz de "completadas vencidas" y "avance 0%".
- `c53edf2` ENH-150 #540 — status de tarea en ES + color leve en reportes (`status_display.py` + filtros Jinja + `_filter_table raw_cols` + `_task_row` badge).
- `8b7f28f` ENH-151 #541 — Reporte de Avance: fusión "Indicadores+Avance del plan" → "Avance del Plan" (Total/Completadas/En curso/No iniciadas/Avance prom/Avance planeado/+−), avance reportado con fallback, presupuesto condicional en Info General.
- `1461c51` BUG-076 #542 — áreas project-scoped: toggle Asignar/Quitar en catálogo + refresh de áreas en Plan.
- `a71e395` ENH-153 #543 — logos PMO+cliente en header del Project Charter (reusa `load_report_branding`).

**Verificación**: pytest de los servicios tocados (42+33+20+6 verdes) · `tsc --noEmit` 0 errores. Issues #538-543 cerrados (por indicación del owner, sin review).
