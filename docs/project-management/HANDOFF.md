# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-06-28
**Branch activa:** `claude/minutes-plans-upload-error-driwcd`
**Generado por:** sesión de ejecución directa (owner pidió end-to-end)

---

## 🎯 Dónde estamos parados

Dos frentes en la MISMA branch `claude/minutes-plans-upload-error-driwcd`:

1. **Hotfix subir minutas/planes** — COMPLETO (`status:fix-committed`): BUG-078
   (MultipleResultsFound), BUG-079 (500 sin CORS → "no se pudo conectar"),
   BUG-080 (CSV auditoría con `details`). Pendiente PR + verificación.
2. **Sprint 35 — "Plan page + RAID mejoras"** — **COMPLETO (14/14)**. Todos
   los items `status:fix-committed`. Detalle por item en `SPRINT.md` → "Sprint 35".
   Falta: PR + verificación del owner. Migración **0086** (`tasks.closed_at`)
   debe correrse en Railway (`alembic upgrade head`).

## 📍 Dónde retomar (próximo paso accionable)

1. **Crear PR** de `claude/minutes-plans-upload-error-driwcd` → `main` (cubre el
   hotfix BUG-078/079/080 + todo el Sprint 35).
2. Correr `alembic upgrade head` (migración 0086) tras el merge.
3. Revisar `docs/project-management/UIUX-ANALYSIS-Sprint35.md`: tiene los
   follow-ups y las decisiones de campos RAID marcadas **[requiere OK]**
   (columna Responsable, category en issues, severidad inline). Confirmar
   scope antes de abrir issues nuevos.

## ✅ Hecho en esta sesión (2026-06-28)

- Hotfix BUG-078/079/080 (subir minutas/planes + CORS + audit CSV).
- **Sprint 35 (14/14):** ENH-161..168, US-171..175, ENH-169.
  - Plan: quitar CSV, mover acciones al header, columna Hito, configurador de
    columnas (reemplaza MSP), WBS nivel 0, fecha de cierre + atraso (mig 0086),
    auto-WBS (endpoint renumber-wbs), edición inline.
  - RAID: ocultar finalizados + orden por fase, filtro de área, export por tipo,
    Kanban con drag, estado inline, análisis de alineación de campos.
- Tests nuevos: BUG-078/079/080, US-171, US-172, ENH-152 (single-sheet).
- Verificación: `tsc` + `next build` verdes; pytest de las suites tocadas verdes.

## 🔄 PRs abiertos o en flight

| # | Branch | Estado | Acción |
|---|---|---|---|
| (ninguno) | `claude/minutes-plans-upload-error-driwcd` | sin PR | crear PR al cerrar el batch |

## ⚠️ Gotchas

- **Web:** CI gatea con `tsc --noEmit` + `next build` (no hay eslint configurado).
  Correr `cd apps/web && pnpm install --frozen-lockfile` en container fresco.
- **API tests:** `cd apps/api && pip install -r requirements-dev.txt` (NO hay
  `[project.dependencies]` en pyproject; usar los requirements*.txt). Correr
  `python -m pytest`.
- **Plan page** es un solo archivo gigante (`app/(app)/pmo/projects/[id]/plan/page.tsx`,
  ~2100 líneas). Editar por regiones; no leer completo.
- **US-171/172 tocan schema** → migración Alembic + `DB-CHANGES.md` + epic.
- `_is_delayed` (lateness) vive en `apps/api/app/services/operational_reports.py`;
  el frontend tiene su propio `isTaskDelayed` en la plan page.

## 📚 Estado de epics

- EP009 (ms-project / plan) y EP006 (project-modules / RAID) se actualizan al
  cierre de los items que cambian comportamiento (US-171, US-172, US-174, ENH-169).

## 🧹 Cleanup / acciones del owner

- [ ] Crear PR de la branch → main y verificar hotfix + batch Sprint 35.
- [ ] Si US-171/172 agregan migración: `alembic upgrade head` en Railway.
