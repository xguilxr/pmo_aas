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
2. **Sprint 35 — "Plan page + RAID mejoras"** — EN CURSO. Batch de 14 items
   (5 US + 9 ENH) pedido por el owner para ejecutar de principio a fin.
   El detalle y progreso por item vive en `SPRINT.md` → bloque "Sprint 35".

## 📍 Dónde retomar (próximo paso accionable)

Seguir el bloque **Sprint 35** de `SPRINT.md` en orden. Los items marcados `[x]`
ya están commiteados; retomar en el primer `[ ]`. Cada item es 1 commit con
header `feat(web|api): <ID> — …`. Al terminar el batch: análisis UI/UX +
actualizar epics (EP006/EP009) y `DB-CHANGES.md` si US-171/172 tocaron schema.

## ✅ Hecho en esta sesión (2026-06-28)

- Hotfix BUG-078/079/080 (3 commits) + registro en SPRINT.
- Sprint 35 abierto; progreso por item en SPRINT.md.

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
