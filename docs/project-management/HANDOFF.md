# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-05-22
**Branch activa:** `main` (todo mergeado al cierre)
**Generado por:** `/handoff` (manual, skill recién creado)

---

## 🎯 Dónde estamos parados

Sprint 26 cerrado completo (16 items en 3 bloques). El frente Minutas v1.0 entregado (estructura rígida de 6 secciones + parser RAID estricto + matching de actores + suscripciones programadas + copy-paste). Las 5 dependencias del sistema EP020 (ENH-097 a ENH-101) y el backbone EP020 (US-120 catálogo, US-121 cálculo % avance, US-122 plantillas seed) ya están en main. **Cero PRs abiertos.** Todo el planning de EP020 (Sprints 27-29) está documentado y con issues en GitHub.

## 📍 Dónde retomar (próximo paso accionable)

Arrancar **Sprint 27 Bloque 1** en una sesión nueva:
- **US-123 #381** — Engine de render con modos composición A/B (`app/services/reports/engine.py`).
- **US-130 #390** — Export PDF de reportes custom (reusa motor PDF compartido US-037).

Pre-requisitos en main: catálogo (US-120) + plantillas seed (US-122). El motor consume ambos.

**Ejecutar SECUENCIAL:** owner pivoteó la metodología tras los errores de paralelización del Sprint 26. 1 sesión = 1 lane = 1 US a la vez.

## ✅ Hecho en esta sesión

Sesión larga de planning + implementación (2026-05-22, ~12 horas):

**Planning (mañana):**
- Catálogo cerrado de 22 secciones atómicas de EP020 tras 4 rondas con owner.
- Epic oficial `docs/epics/EP020-report-builder.md` (13 US + 5 ENH dependencias).
- Gold standard de minuta `docs/epics/drafts/minute-gold-standard.md` (Highlander EAM-BNF transcript + minuta esperada + pipeline parser IA).
- 26 issues creados en GitHub (#373-#398) + labels aplicados.
- 18 issues EP020 + 8 issues Minutas v1.0 distribuidos en 4 bloques.

**Implementación (tarde/noche):**
- Sprint 26 Bloque 0 — Minutas v1.0: BUG-061 + ENH-102 a ENH-108 (8 items).
- Sprint 26 Bloque 1 — Dependencias EP020: ENH-097 a ENH-101 (5 items).
- Sprint 26 Bloque 2 — Backbone EP020: US-120, US-121, US-122 (3 items).
- 3 hotfixes de alembic multi-heads resueltos (PRs #409 + 2 fixes inline).

**Tooling:**
- Skill `/handoff` creado en `.claude/skills/handoff/SKILL.md` (PR #412).
- SPRINT.md limpiado dos veces (662 → 178 → 168 líneas actuales).
- Sprints 17-26 archivados a `SPRINT-DONE-HISTORY.md`.

## 🔄 PRs abiertos o en flight

Ninguno. Todos los PRs de esta sesión están mergeados a main.

## ⚠️ Gotchas y decisiones recientes

- **Paralelización agresiva causa collisions de migraciones alembic.** 3 collisions distintas en este sprint:
  1. ENH-100 + ENH-101 con misma `down_revision='20260510_0062'` → merge migration 0066.
  2. ENH-106 + ENH-107 con misma `down_revision='20260522_0067'` → merge migration `20260523_0069`.
  3. US-120 + US-122 reusaron revision IDs `20260522_0068` y `20260522_0069` que main ya tenía → rename a 0070/0071.
- **Decisión owner 2026-05-22:** desarrollo secuencial puro de aquí en adelante. 1 sesión activa, 1 lane, 1 branch, migraciones consecutivas.
- **Snapshots históricos fuera de scope v1.0.** Se posterga a v2.0 (descarta S-05 tendencia, sparklines, deltas, S-07 curva S, S-10 entregables formales del catálogo EP020).
- **`tasks.is_critical` reemplaza columna `critical` legacy** — owner pidió eliminar dual-column para evitar confusión semántica.
- **RAID estricto:** parser IA solo admite A/R/D/I; lecciones y cambios se descartan silenciosamente.
- **Estructura minuta:** 6 secciones fijas (Encabezado, Participantes, Resumen, Temas, RAID unificado, Notas libres). Las "actividades a hacer" caen como Acciones del RAID, no como sección separada.

## 📋 Lo que sigue (resumen ejecutivo del backlog activo)

Ver `SPRINT.md` para detalle completo.

- **Sprint 27 Bloque 1** — Motor de render + Export PDF (US-123, US-130).
- **Sprint 27 Bloque 2** — Canvas Nivel 4 drag-drop (US-124, US-125, US-126).
- **Sprint 28** — IA conversacional (US-127) + Suscripciones custom (US-131).
- **Sprint 29** — UI Niveles 1 PMO + 2 Org (US-128, US-129) + Render headless Gantt (US-132).

## 🧹 Cleanup técnico pendiente

- [ ] Borrar branches mergeadas localmente y en origin (`claude/sprint26-*`, `claude/adoring-lovelace-i5fak`, `claude/cleanup-planning-roadmap-nHh4J`, `claude/fix-alembic-multiple-heads-0068`, `claude/handoff-skill-setup`).
- [ ] Verificar que el deploy de Railway terminó OK con todas las migraciones nuevas (0064-0067, 0068×2, 0069, 0070, 0071).
- [ ] Crear label `EP020` en GitHub UI y aplicarla en bulk a #378-#390.
- [ ] Cerrar manualmente los issues mergeados que owner no haya cerrado todavía (sub-tarea de validación post-deploy).

## 🔮 Para sesiones futuras (sin issue todavía)

Items mencionados durante la sesión que vale la pena no perder:

- **Sesión de revisión completa de diseño y navegación del producto.** Owner planea esta sesión "al finalizar todo esto" (probablemente cuando EP020 esté completo). Foco: UX cross-módulo, consistencia visual, navegación, atajos.
- **Re-evaluar chat IA conversacional global** (US-102/ENH-074/075/076 en Deferred) después de cerrar EP020 — owner postergó decisión en Sprint 17.
- **Cleanup legacy de Áreas/Recursos:** US-119 (drop columnas `actors.team_id`, `actors.is_lead`, `teams.area_id`, `tasks/risks/issues.area_id`) cuando PersonPicker esté cableado en todos los forms del EP017 fase 2.
- **PersonPicker cableado en cada formulario existente** (TaskAssigneeDropdown, RiskOwnerDropdown, IssueOwnerDropdown, ChangeApproverPicker, LessonOwnerDropdown, ParticipantPicker minutas) — diferido del EP017 Sprint 25.
- **Filtros/agrupadores de Plan por dimensiones derivadas** (depende del PersonPicker integrado + ENH-077).
- **US-118 Fases 2 y 3:** RBAC migra a leer `project_participations` (Fase 2) y drop `project_members` (Fase 3) — abrir US separadas con owner OK explícito por blast radius.

---

## Cómo retomar

Para la próxima sesión:

1. Lee este `HANDOFF.md` primero.
2. Luego `CLAUDE.md` + `docs/project-management/SPRINT.md` + `docs/epics/EP020-report-builder.md`.
3. El próximo paso accionable es **arrancar US-123** sobre una branch nueva (sugerencia: `claude/sprint27-b1-render-engine`). Pasar el issue #381 a `status:ready` antes.
4. Recordar: **secuencial puro**. US-130 (export PDF) viene DESPUÉS de US-123 verde, no en paralelo.
