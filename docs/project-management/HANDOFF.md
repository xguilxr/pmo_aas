# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-06-05
**Branch activa:** `claude/gantt-areas-fixes`
**Generado por:** /handoff

---

## 🎯 Dónde estamos parados

El batch **"gantt/áreas/reportes/RAID fixes"** está **completo y en
`status:fix-committed`**, esperando que el owner cree el PR, mergee y haga QA.
Esta sesión cerró los **4 temas restantes** que dejó el handoff anterior
(ENH-149, BUG-075, ENH-152, ENH-154). 9 commits de trabajo en total (6 de la
sesión previa + 3 de esta), todos pusheados. **No hay PR creado todavía.** La
branch está detrás de `origin/main` (main avanzó con otros merges que **no
tocan** estos archivos).

## 📍 Dónde retomar (próximo paso accionable)

**Crear el PR** `claude/gantt-areas-fixes` → `main` y verificar/cerrar los 4
issues nuevos (#544-547). Si CI falla por estar detrás de main: rebase +
`--force-with-lease`. Luego, próximo trabajo: `ENH-115 #434` (breadcrumbs en
`/pmo/**/reports`, en INBOX) cuando el owner lo priorice.

## ✅ Hecho en esta sesión (2026-06-05)

- **ENH-149 #544** — Plan: editar `end_date`. **Sin código**: ya estaba
  implementado end-to-end (input del modal de editar tarea + PATCH que persiste
  + cierre de BUG-074 que des-marca el atraso). Verificado los 7 eslabones y el
  edge case de 21 días (no aplica: `ensure_duration_max_21` es no-op). Issue
  documentado + `status:fix-committed`.
- **BUG-075 #545** (`aa5708c`) — RAID: estado editable. `<Select>` in-place en el
  badge del header de `raid-detail-page.tsx`, poblado por tipo (Risk vs Issue).
  Backend ya aceptaba `status`. Frontend-only.
- **ENH-154 #546** (`02dd08a`) — Reporte de Seguimiento: sección **"Acciones"**
  (toda acción abierta) antes de "Actividades próximas". Las acciones salen de
  los buckets de Actividades (sin duplicados); rescata acciones sin fecha.
- **ENH-152 #547** (`482566f`) — Export RAID rework: XLSX único con 4 hojas ES
  (Riesgos/Acciones/Incidencias/Decisiones), nombres resueltos a texto, filename
  `RAID-[Nombre Proyecto].xlsx`, mismo archivo para el botón de `/raid` (pasó de
  CSV cliente a descarga del endpoint) y el de Documentos.

Verificación: `tsc --noEmit` verde · ruff limpio · pytest seguimiento 12/12 +
RAID export 4/4 + EP006 20/20. SPRINT.md limpiado (3 batches viejos mergeados
archivados a `SPRINT-DONE-HISTORY.md`).

## 🔄 PRs abiertos o en flight

| # | Branch | Estado CI | Acción pendiente |
|---|---|---|---|
| (ninguno) | `claude/gantt-areas-fixes` | sin PR | **Crear PR** → main, mergear tras QA |

## ⚠️ Gotchas y decisiones recientes

- **El handoff anterior tenía errores de modelo** (los corregí al mapear contra
  el código real, no los seguí a ciegas): BUG-075 NO era `raid-edit-fields.tsx`
  (código muerto) ni `RiskActionItem` — son `Risk`+`Issue` de `models/modules.py`,
  cada uno con su set de estados. ENH-152 NO tenía 2 generadores (el de `/raid`
  era CSV cliente; el único XLSX es `raid_export.py`). ENH-154 NO era
  `RiskActionItem` — son `Issue` con `type=='action'`.
- **Decisiones del owner (2026-06-05):** BUG-075 las Decisiones reusan el set de
  estados de Issue (no set propio → evita migración). ENH-152: descartar
  Lessons/Changes del export; Responsable = Actor con fallback a Usuario; Fecha
  creación = de negocio (`identified_at`/`reported_at`); filename legible; `/raid`
  reemplaza CSV por el XLSX. ENH-154: criterio "vigente" = toda acción abierta;
  acciones aparte (no duplicar en Actividades).
- **Branch detrás de `origin/main`**: main avanzó (BUG-068 a 072: minutas/actores)
  sin tocar estos archivos. Rebase solo si CI lo pide al armar el PR.
- **Permisos GitHub**: el owner eligió autorizar las escrituras (issue/push/comment)
  **tema por tema**; el classifier las frena individualmente.

## 📋 Lo que sigue (resumen del backlog activo)

Detalle en `SPRINT.md`.

- **INBOX:** ENH-115 #434 — breadcrumbs en `/pmo/**/reports` (`status:ready`,
  diferido; owner reasigna cuando prioriza).
- **Deferred:** IA conversacional global (US-102/ENH-074-076), redefinición
  Áreas/Recursos (US-105/119/133/134, ENH-109/110), admin UI settings
  (ENH-111/112/113). Re-evaluar post-EP020.
- **Próximo libre:** US-166, BUG-077, ENH-155.

## 📚 Estado de las epics docs

| Epic | Sincronizada | Notas |
|---|---|---|
| EP006 (project-modules) | sí | AC del export RAID actualizado (ENH-152) |
| EP014 (operational-deliverables) | sí | Reporte de Seguimiento: sección Acciones (ENH-154) |
| EP018 (documents-artifacts) | sí | Artefacto RAIDs: 4 hojas ES + nombres resueltos (ENH-152) |

No quedan epics desactualizadas por los commits de esta sesión.

## 🧹 Cleanup técnico pendiente (owner / externo)

- [ ] (GitHub web) Crear PR `claude/gantt-areas-fixes` → `main`: https://github.com/xguilxr/pmo_aas/compare/main...claude/gantt-areas-fixes
- [ ] (app) Verificar y **cerrar** #544 (ENH-149), #545 (BUG-075), #546 (ENH-154), #547 (ENH-152) — cada comment trae su smoke test.
- [ ] (Git Bash, si CI falla por estar atrás de main) `git fetch origin main && git rebase origin/main && git push --force-with-lease origin claude/gantt-areas-fixes`

## 🔮 Para sesiones futuras (sin issue todavía)

- Export RAID de **Lecciones/Cambios** aparte (ENH-152 los descartó del XLSX RAID).
- Contador de **Acciones** en la tabla "Resumen" del Reporte de Seguimiento
  (ENH-154 dejó el Resumen contando solo Actividades).

---

## Cómo retomar

1. (Git Bash o WSL) `cd /c/Users/dagui/claude/pmo_aas && git checkout claude/gantt-areas-fixes && git pull`
2. (Git Bash) `git checkout -- apps/api/uv.lock 2>/dev/null; rm -f apps/api/uv.lock` — limpiar el artefacto untracked si `uv run` lo regeneró.
3. (PowerShell, en `apps/api`) backend: `uv run uvicorn app.main:app --reload`
4. (PowerShell, en `apps/web`) front: `pnpm dev` (sin `pnpm install`, lockfile intacto)
5. (GitHub web) crear el PR y mergear tras QA, o continuar con ENH-115 sobre branch nueva.
6. (tests por tema) `cd apps/api && uv run python -m pytest tests/ -k "<keyword>" -q` · `cd apps/web && pnpm exec tsc --noEmit`
