# Handoff — pmo_aas — 2026-06-07

## Estado
- Branch: `claude/owner-feedback-batch` · Base: `main` · PR: **#549 — MERGED** (https://github.com/xguilxr/pmo_aas/pull/549)
- El batch ya está en `origin/main` (merge `dabc8a9`). CI del PR: todo verde (api-migrations, api-tests-smoke, lint, web-build, web-typecheck, changes; heavy en job aparte).
- Working tree: **limpio**. La rama de trabajo puede borrarse.
- Sin migraciones Alembic propias del batch.

## Hecho esta sesión
Batch de 5 pedidos del owner (investigados con workflow read-only, implementados con commits atómicos, verificados, mergeados):
- `c61cf15` **ENH-109** — avance derivado del plan (rollup WBS): padre = avg hijos recursivo; general = avg nivel más alto. Read-side en lista de tareas, resumen de proyectos, detalle, dashboard (KPIs/charts/plan-vs-actual) y reporte de avance. Manual como fallback sin plan. Helpers `compute_wbs_rollup` / `compute_plan_rollup_progress` / `round_half_up` en `plan_metadata.py`; `plan_rollup_map` / `effective_progress_map` en `progress_calculator.py`. Test verifica el ejemplo del owner (general=26%, 1.2=93%, 1=39%).
- `e20a8c1` **BUG-062 (mío)** — minuta 422: guard de título `< 2` + parser de 422 nativo de FastAPI en `lib/api.ts`. Tras el merge, re-aplicado en `minutes/new/page.tsx` (el flujo manual se movió ahí).
- `fdd73e3` **ENH-112 (mío)** — borrar/cancelar RAID/Lecciones/Cambios: soft-delete + audit en `modules.py`; cancel de Cambios (status `cancelled`) + invalidación de ApprovalToken EP019; botones+modales en los 3 detail pages.
- `1c407b3` **ENH-111 (mío)** — logos (tenant + cliente) en el `.docx` del charter; `resolve_charter_logos` (disco + httpx), solo PNG/JPEG, tolerante a fallos.
- `fbc9e9e` **ENH-110 (mío)** — salud/semáforo solo-color (sin "Green"/"Verde"); reporte de avance (`.dot`), charter (● coloreado) y 5 vistas read-only del front.
- `77600dc` merge de `origin/main` (196 commits, Report Builder EP020) con resolución de 3 conflictos.

## Decisiones (y por qué)
- **Avance en TODAS las superficies, no solo el resumen** — el owner eligió consistencia; manual queda como fallback solo para proyectos sin plan.
- **Rollup read-side (sin persistir, sin migración)** — más simple y siempre fresco; evita enganchar todos los paths de mutación de tareas.
- **Jerarquía por código WBS (no `parent_id`)** — en planes importados `parent_id` viene null; el WBS es la autoridad que el front ya usa para indentar.
- **`round_half_up` propio (no `round()`)** — Python usa banker's rounding y daría 1.2=92 en vez de 93; el owner mostró 93 en su ejemplo.
- **Salud = círculo de color con `title`/`aria-label`** (no chip con texto) — patrón objetivo que ya existía en `pmo/organizations/[id]`. No se tocaron selectores interactivos (HealthCard/StatusRagCard/filtro), donde el texto es la etiqueta clicable.
- **Cambios: borrar (soft) Y cancelar (status)** — cancelar preserva la trazabilidad de aprobaciones EP019; cualquier miembro puede hacerlo (decisión del owner).
- **Charter: tenant + cliente, ambos URL o PNG** — tenant desde disco (`branding_storage`), cliente desde `client_logo_url` (httpx); todo fallo degrada a "sin ese logo".
- **Resolución de conflictos del merge**: `admin/supervision/page.tsx` borrado en main → acepté la eliminación (ese surface de ENH-110 ya no existe); `minutes/page.tsx` → el llenado manual se movió a `minutes/new/page.tsx`, re-apliqué BUG-062 ahí; `dashboard.py` → conservé ambos bloques de imports.

## Próximo
- Verificar el **deploy** de `main` (Railway backend / Vercel front). El batch no agrega migraciones; si el CD dispara en push a `main`, ya debería estar corriendo.
- **Resolver la colisión de IDs en la documentación** (ver bloqueos) — re-numerar en `SPRINT.md`/`CLAUDE.md` con el próximo libre real.

## Bloqueos / pendiente de input
- **Colisión de IDs (no bloquea el merge, pero ensucia el tracking).** Mis IDs se eligieron contra una base desactualizada (`9c904a2`, max ENH-108/BUG-061), pero main tenía 196 commits sin mergear que ya habían consumido esos números. En `main` hoy el max real es **ENH-154** y **BUG-076**. Resultado: `ENH-109/110/111/112` y `BUG-062` quedan **duplicados** en la historia de main (main tiene su propio BUG-062 "click en minuta", ENH-111/112 "validaciones admin tenant"). La historia ya está mergeada → no se reescribe. Decisión del owner: re-documentar este batch bajo IDs frescos (**ENH-155+ / BUG-077+**) en `SPRINT.md`/docs y dejar los labels de commit como referencia histórica, o aceptarlo. La tabla de numeración del `CLAUDE.md` del repo también está desactualizada (dice ENH-080/BUG-055).

## Acciones del owner (externas)
- [ ] Verificar/disparar el deploy de `main` (Railway + Vercel).
- [ ] Decidir el re-numerado de IDs (ENH-155+/BUG-077+) y actualizar `SPRINT.md` + la tabla de `CLAUDE.md` (próximo libre).
- [ ] Borrar la rama mergeada: `git push origin --delete claude/owner-feedback-batch`.
- [ ] (Opcional) Cargar `client_logo_url` en las orgs que quieran logo del cliente y revisar visualmente el `.docx` del charter (tamaño `Inches(1.4)`, ajustable).
- [ ] (Opcional) Crear los issues GitHub del batch con los IDs correctos para el triage.

## Cómo retomar
1. (PowerShell o Git Bash) `git checkout main; git pull origin main`
2. (PowerShell, en `apps/api`) `uv pip install -r requirements-dev.txt` (solo si vas a correr tests)
3. (PowerShell, en `apps/api`) `uv run pytest -q -m "not heavy"` — verde salvo 2 fallos **pre-existentes de entorno** (`test_enh107` worker de minutas y `test_us040_export_pdf`, por celery/weasyprint no instalados).
4. (PowerShell, en `apps/web`) `pnpm install; pnpm exec tsc --noEmit` (exit 0) y `pnpm lint`.
5. Para el avance: abrir un proyecto con plan WBS y confirmar que los padres muestran el promedio de sus hijos y el resumen el ~general.
