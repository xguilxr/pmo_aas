# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** todo lo cerrado vive en `SPRINT-DONE-HISTORY.md`.
>
> **Límite:** este archivo no pasa de 250 líneas. Lo hace cumplir el CI
> (`scripts/check_contexto.py`); se carga en toda sesión y se paga en cada turno.

---

## 🔴 IN-PROGRESS

```
Sesión 2026-08-04 · Branch: claude/auditoria-conformidad-mca-mcs · PR #573
Auditoría de conformidad MCA/MCS + Tanda A y B1/B2/B3/B4 de remediación.
Pendiente: revisión y merge del owner. Siguiente y última de la tanda: B5.

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

> Plan completo y estado por requisito en `docs/conformidad/plan.md`. No consume
> IDs US/ENH/BUG. **PR #573**, CI verde.

Hecho: MCA acciones 1-10, MCS auditado, Tanda A (4/5) y B1/B2/B3/B4.

**Pendiente de decisión del owner:**

- [ ] Abrir Claude Code **con el repo como directorio de trabajo** y comprobar
  que el guard de acciones irreversibles intercepta. `/hooks` no basta: es
  config de proyecto. Con esto MCA llega a **N2**.
- [ ] **Proteger `main`** — hoy cualquiera escribe directo en productiva.
  Comando en `plan.md` → Tanda A. Acordado esperar a cerrar los PR abiertos.
- [ ] Fijar el presupuesto de contexto: 40.000 declarado, ~51.000 real, y el
  número lo propuso la auditoría.
- [ ] Revisar `docs/dominio/02-GLOSARIO.md`. Bloquea la remediación de dominio.

**Pendiente de ejecución:** solo **B5** (modelo de amenazas, 2 d).

> B3 dejó el conjunto de evaluación de IA en `apps/api/evaluacion/`.
> **Al proteger `main`, añadir `evaluacion-ia` a los checks requeridos.**

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

| Sprint / batch | Versión | Cerrado | Items |
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
| 26 | v1.25 | 2026-05-22 | 16 (Minutas v1.0 + Dependencias EP020 + Backbone EP020) |
| 27-29 | v1.26 | 2026-05-25 | 10 (mega-PR EP020: US-123 a US-132) |
| 30-32 | v1.27 | 2026-05-23 | 22 (rediseño Minutas + Reports) |
| 33 | v1.28 | 2026-05-26 | 13 (Dashboards N1/N2 + reportes derivados + revamp) |
| Sprint 34 Bloque 1 | — | 2026-06-08 | 5 de 6 (US-168 sigue abierta) |
| Sprint 35 + follow-ups | — | 2026-06-28 | 14 + 9 (PR #560, CI verde) |
| Hotfix minutas/planes | — | 2026-06-28 | 3 (BUG-078/079/080) |
| Batch feedback owner | — | 2026-06-29 | 5 (#562-566) |
| Batch WBS+RAID+Áreas | — | 2026-06-29 | 11 |
| Revamp 1.0 + Fase 2 | — | 2026-07-09 | 14 (PR #570, migs 0091-0094) |
| Plan Import Revamp | — | 2026-07-18 | 9 |
| Feedback 16-jul | — | 2026-07-18 | 8 (migs 0095-0096) |
| Mini-batch Plan UX | — | 2026-07-18 | 4 de 5 (ENH-202 abierta) |

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
- [ ] KPIs custom por admin tenant.
- [ ] **Cleanup post-Sprint 32**: borrar `apps/web/app/(app)/pmo/projects/[id]/ai-minutes/` y `.../reports/tweak/` (hoy son redirects 301). Tras 1 sprint en main sin bookmarks rotos.
- [ ] **Persistencia reports L1/L2** (PMO/Org/Prog): la generación ya existe (v1.28, US-160). Falta persistir el histórico: `generator='pmo'|'organization'|'program'` + nullable `project_id` o tabla aparte.
- [ ] **Dirty-flag fino en builder** (mejora ENH-125): comparar canvas vs plantilla cargada para detectar cambios sin guardar incluso con `loadedTemplateId`.
- [ ] **Export RAID — Lecciones/Cambios** (follow-up ENH-152): si se necesita, abrir un export aparte.

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
5. Implementa con tests verdes + typecheck (comandos en `CLAUDE.md` §0.3).
6. Commit con header `<tipo>(<scope>): <ID> — <desc> (refs #<issue>)` y push.
7. Cambia label → `status:fix-committed` + comment con template CLAUDE.md §3 paso 6.
8. Mueve item a DONE en este archivo o a la tabla histórica si cierra sprint.
9. Resumen de ronda al owner siguiendo CLAUDE.md §11.
10. Al cierre de sesión: invocar `/handoff` para limpiar este archivo y dejar bridge.

**Regla sagrada:** 1 US = 1 commit. No mezclar varios IDs en el mismo commit.

**Regla post-Sprint 26 (decisión owner 2026-05-22):** desarrollo secuencial puro. 1 sesión activa, 1 lane, 1 branch. Migraciones consecutivas sin paralelización.
