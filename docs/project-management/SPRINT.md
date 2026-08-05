# SPRINT.md — Tarea activa

> **Regla:** este archivo es lo que se mira cada día. El epic se abre al tocarlo
> (`CLAUDE.md` §1). 1 US = 1 commit. Al terminar, mover la siguiente a IN-PROGRESS.
>
> **Histórico:** todo lo cerrado vive en `SPRINT-DONE-HISTORY.md`.
>
> **Límite:** este archivo no pasa de 250 líneas. Lo hace cumplir el CI
> (`scripts/check_contexto.py`); se carga en toda sesión y se paga en cada turno.

---

## 🔴 IN-PROGRESS

```
Sin sesión activa. PR #573 MERGEADO a main el 2026-08-04 (a725d10).

Cerró: auditoría MCA/MCS, Tanda A (4/5), Tanda B entera (B1-B5),
presupuesto de contexto (-61%) y la reauditoría de los dos marcos.

Próximo paso — R1: evaluar los 13 requisitos MCS en NO VERIFICABLE.
Es medición, no construcción. Rama nueva desde main.

Los batches del 2026-07-18 (Plan Import Revamp 9/9 y Feedback 16-jul 8/8)
siguen en `claude/plan-import-wbs-fixes-nwotng` SIN PR. Migraciones 0095-0096
pendientes de `alembic upgrade head`. Ver «PRs en flight» en HANDOFF.md.
```

> **¿Próximo ID libre?** `python scripts/proximo_id.py`. Se deriva de GitHub +
> `git log` + docs; ya no se almacena aquí (MCA CTX-03). Corrélo contra
> `origin/main` actualizado.

---

## 📥 INBOX / TRIAGE

> Solo lo **abierto**. Lo cerrado se archivó a `SPRINT-DONE-HISTORY.md`
> el 2026-08-03.

### Siguiente batch

- [ ] **ENH-202** — Helvetica en TODOS los exports/reportes (cambio masivo de
  fuente; el plan ya la usa vía US-193). Plan:
  1. Backend XLSX (openpyxl): helper `export_fonts.py` con `FONT="Helvetica"`
     aplicado en `raid_export.py`, `change_export.py` (y export de Lecciones),
     `organigrama_export.py` (+ utilización US-186) y `plan_regenerator.py`.
  2. PDFs (WeasyPrint): `font-family: Helvetica, Arial, sans-serif` en el CSS
     base de `templates/pdf/**` (reportes, minutas, look-ahead, status PMO) y
     el renderer HTML inline.
  3. DOCX charter (`charter_generator.py`): estilo Normal → Helvetica.
  4. FE ExcelJS: reusar `XLSX_FONT` de plan-template en el reporte de salud del
     portafolio (US-192) y cualquier export client-side.

### Abiertos de batches ya archivados

- [ ] **US-168 #554** — Filtrado de API y sidebar por visibilidad de PM.
  `status:in-progress`. Único item abierto del Sprint 34 Bloque 1.
- [ ] **ENH-115 #434** — Breadcrumbs consistentes en `/pmo/**/reports`.
  `status:ready` desde 2026-05-23, diferido al cierre del rediseño grande.
  Owner pasa a ready o reasigna sprint cuando lo prioriza.

### Pendiente de PR (acción del owner)

- `claude/gantt-areas-fixes` — `status:fix-committed`. Owner crea PR
  manualmente: ENH-149 #544, BUG-075 #545, ENH-154 #546, ENH-152 #547.

### Conformidad (auditoría 2026-08-03)

> Estado por requisito en `docs/conformidad/plan.md`. **Las acciones del owner
> viven en `HANDOFF.md`**, no aquí: estaban en los dos sitios y una de las dos
> copias iba a envejecer (CTX-06). No consume IDs US/ENH/BUG.

**R1 cerrada el 2026-08-04** — los 13 NO VERIFICABLE medidos, ninguno queda sin
estado (`docs/conformidad/2026-08-04-mcs-r1.md`). Cuatro de los trece no eran
trabajo pendiente: IA-01 ya era NO APLICABLE, IA-04 y las decisiones CON-04 y
ARQ-03 (excluido con ADR-018) se cerraron el mismo día. En **PR #575**.

**Siguiente:** lo barato de R1 —SUM-02, DES-03, LEN-02 y DIS-02, que se cruza
con la decisión D-7 del glosario— antes de las Tandas C/D/E.

---

## 📦 Deferred, DONE y Backlog v2.0

Viven en [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md) — se abren al planear, no al
ejecutar. El historial narrativo sigue en `SPRINT-DONE-HISTORY.md`.

---

## Notas y cambios recientes

> Histórico narrativo en `SPRINT-DONE-HISTORY.md`.

- **2026-08-03 (auditoría de conformidad + remediación):** MCA y MCS auditados
  (`docs/conformidad/`: cuatro informes + plan). **PR #573**, CI verde.

  **MCA 10/11** — contexto permanente −43 %, comandos de verificación
  ejecutables, tres controles nuevos en CI. **MCS 9/126**, no alcanza N1.

  La Tanda A cerró tres de las cuatro exposiciones críticas. Los escáneres, en
  su primer día: una vulnerabilidad real de XML en el importador (archivo del
  usuario a un parser sin defensa), 10 de 23 CVE de Python cerradas —6 de
  subida de archivos, 2 de JWT— y la crítica de Next.js. **B1**: suite de
  aislamiento entre inquilinos, verificada por mutación.

  Detalle completo en `docs/conformidad/plan.md` y en el PR.

---

## Instrucción para Claude Code

Cuando arranques una sesión nueva:

1. Lee `docs/project-management/HANDOFF.md` PRIMERO.
2. Luego `CLAUDE.md` + este archivo + el epic referenciado en IN-PROGRESS.
3. Mueve la siguiente US/ENH/BUG de **INBOX** (marcada `status:ready`) a **IN-PROGRESS** antes de empezar.
4. Cambia label del issue: `status:ready` → `status:in-progress`.
5. Implementa con tests verdes + typecheck (comandos en la skill `verificar`).
6. Commit con header `<tipo>(<scope>): <ID> — <desc> (refs #<issue>)` y push.
7. Cambia label → `status:fix-committed` + comment con template CLAUDE.md §3 paso 6.
8. Mueve item a DONE en este archivo o a la tabla histórica si cierra sprint.
9. Resumen de ronda al owner siguiendo CLAUDE.md §11.
10. Al cierre de sesión: invocar `/handoff` para limpiar este archivo y dejar bridge.

**Regla sagrada:** 1 US = 1 commit. No mezclar varios IDs en el mismo commit.

**Regla post-Sprint 26 (decisión owner 2026-05-22):** desarrollo secuencial puro. 1 sesión activa, 1 lane, 1 branch. Migraciones consecutivas sin paralelización.
