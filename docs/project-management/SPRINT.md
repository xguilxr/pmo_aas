# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-26 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Mega-PR EP020 abierto (claude/dazzling-fermat-W354x) — 10 US
entregadas en 10 commits secuenciales, sin merges intermedios.
Por mergear todo de un golpe tras CI verde:

  US-123 (engine) 67bb040
  US-130 (export PDF) 0dba512
  US-124 (canvas drag-drop) d53daaa
  US-125 (panel params) ec63303
  US-126 (plantillas privadas + visibility) 88bbcac · migración 0073
  US-127 (chat IA conversacional) 5436224
  US-131 (suscripciones custom) 176448b · migración 0074
  US-128 (UI Nivel 1 PMO) 58e29d1
  US-129 (UI Nivel 2 Org/Programa) 13f7595
  US-132 (Gantt SVG snapshot) d97943f

Próximo libre: US-133, BUG-062, ENH-109.
```

---

## 📥 INBOX / TRIAGE

> Issues creados con `status:triage`. Owner pasa a `status:ready` para arrancar.

### Sprints 27-29 EP020 — entregados en mega-PR (pendiente merge)

Todos los items abajo están en commits separados sobre la branch
`claude/dazzling-fermat-W354x`. Al mergear el PR pasan a la tabla DONE.

**Sprint 27 Bloque 1 (motor + export):**
- [x] **US-123 #381** — Engine de render con modos composición A/B (`67bb040`).
- [x] **US-130 #390** — Export PDF de reportes custom (`0dba512`).

**Sprint 27 Bloque 2 (canvas Nivel 4):**
- [x] **US-124 #382** — Canvas drag-and-drop + preview en vivo (`d53daaa`).
- [x] **US-125 #383** — Panel de parámetros transversales (`ec63303`).
- [x] **US-126 #384** — Plantillas privadas + publicar al proyecto (`88bbcac`, migración 0073).

**Sprint 28:**
- [x] **US-127 #385** — IA conversacional (tool-call JSON-action, reusa cascada EP008) (`5436224`).
- [x] **US-131 #386** — Suscripciones reportes custom (`176448b`, migración 0074).

**Sprint 29:**
- [x] **US-128 #387** — UI Reportes Nivel 1 PMO `/pmo/reports/portfolio` (`58e29d1`).
- [x] **US-129 #388** — UI Reportes Nivel 2 Organización + Programa (`13f7595`).
- [x] **US-132 #389** — Render del Gantt WBS-N para S-19 (SVG Python; Playwright diferido a v1.x — DEC-029) (`d97943f`).

---

## ⏸️ Deferred — re-evaluación post EP020

> Issues abiertos sin asignación de versión. Se retoman cuando owner decida.

### IA conversacional global (ex Sprint 17 Bloque 1)
- [ ] US-102 #255 — Side-panel chat IA en cada página (Ctrl+K + flotante)
- [ ] ENH-074 #256 — Context-awareness por página
- [ ] ENH-075 #257 — Tool-use (crear tarea / RAID / nav)
- [ ] ENH-076 #258 — Historial persistente + summary rolling

**Decisión owner 2026-05-08:** posterga el chat global. Primero ejecutar Sprints 18-23 (Documentos / RAID / Minutas / Reportes / Cambios / BYO universal). Volver a evaluar necesidad después.

### Pendiente redefinición Áreas/Recursos (cubierto parcial por EP017 Sprint 25)
- [ ] **US-105 #311** — Import Plan: wizard matching responsables → Actor.
- [ ] **Tab Organigrama de US-106** — placeholder UI; cableado funcional depende del paquete EP017 final.
- [ ] **US-119 #414** — EP017 cleanup: drop legacy `actors.team_id`, `actors.is_lead`, `teams.area_id`, `tasks/risks/issues.area_id`. **Bloqueado por ENH-109.**
- [ ] **ENH-109 #417** — PersonPicker cableado en formularios existentes (Task/Risk/Issue/Change/Lesson/Participant). **Bloquea US-119 y ENH-110.**
- [ ] **ENH-110 #418** — Filtros / agrupadores de Plan por dimensiones derivadas. Depende de ENH-109.
- [ ] **US-133 #415** — US-118 Fase 2: RBAC migra a leer `project_participations` (en lugar de `project_members`).
- [ ] **US-134 #416** — US-118 Fase 3: drop `project_members` table. Bloqueado por US-133 en producción ≥ 1 sprint.

### Snapshots históricos (postergado v2.0)
- Snapshots periódicos de KPIs y semáforo (habilita S-05 tendencia, sparklines, deltas vs anterior).
- S-07 Curva S (descartada — incompatible con flexibilidad del plan).
- S-10 Entregables formales (concepto no configurado en plataforma).

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

---

## 📋 Backlog v2.0 (post-v1.x)

> **Contexto (DEC-020):** plataforma definida como herramienta de apoyo/visualización sin aprobaciones jerárquicas. US-061 cancelada; US-059/US-060 entregadas en Sprint 4.

- [ ] ENH-035 #158 — Análisis profundo optimización CI tests pesados.
- [ ] US-081 — Borrar físicamente tablas `roles` + `user_roles` (migración 0037+) tras validación de Sprint 6 en producción.
- [ ] ENH futuro — Filtrado efectivo de queries por `organization_user_exclusions`.
- [ ] Cross-empresa nativo (post-ENH-043): si ≥3 grupos lo solicitan, abrir US con `program_organizations`.
- [ ] US-086 fase 2 — Cablear stakeholders FK en Charter.
- [ ] US-084 fase 2 — Banner de divergencias cuando importadores MPP/XLSX detecten diferencia entre manual y calculado.
- [ ] US-087 fase 2 — Campos `Task.hours_estimated/hours_actual` para que `compute_kpis` exponga horas plan/real.
- [ ] Hard-delete User cuando hay `project_request.requested_by` (US-088 fase 2).
- [ ] Snapshots históricos de KPIs y semáforo (habilita S-05 tendencia, sparklines, deltas).
- [ ] KPIs custom por admin tenant (extensión del catálogo cerrado v1.0 de EP020).

---

## Notas y cambios recientes

- **2026-05-25 (mega-PR EP020 completo):** 10 US entregadas en 10 commits secuenciales sobre `claude/dazzling-fermat-W354x` (US-123 a US-132). Decisiones DEC-025..029 registradas en DECISIONS.md. Migraciones 0073 (visibility) + 0074 (scheduled custom) en DB-CHANGES.md. Suite de regresión EP020: 30/30 tests verdes. Pendiente revisión owner + merge.
- **2026-05-22 (cierre Sprint 26 + skill /handoff):** Sprint 26 cerrado completo (16 items en 3 bloques). Frente Minutas v1.0 entregado (BUG-061 + 7 ENH). Backbone EP020 entregado (US-120/121/122). 3 collisions de alembic resueltas con merge migrations + renaming. **Decisión clave:** owner pivotea a desarrollo secuencial puro tras los errores de paralelización. Skill `/handoff` creado (PR #412 mergeado) para forzar cleanup de SPRINT.md y mantener bridge entre sesiones.
- **2026-05-22 (Sprint 26 Bloque 0 — Minutas v1.0 + EP020 planning):** catálogo de 22 secciones atómicas de EP020 cerrado tras 4 rondas con owner. Promoción del draft a epic oficial `docs/epics/EP020-report-builder.md` con 13 US (US-120 a US-132) + 5 ENH dependencias. Gold standard de minuta (Highlander EAM-BNF) como referencia normativa del parser IA. 26 issues creados (#373-#398) + labels aplicados.
- **2026-05-10 (EP017 Directorio de Proyecto — Sprint 25 entregado):** 5 US entregadas. Migraciones 0061 + 0062. Diferidos significativos: PersonPicker cableado en cada form, US-118 Fases 2/3, US-119 cleanup.

---

## Instrucción para Claude Code

Cuando arranques una sesión nueva:

1. Lee `docs/project-management/HANDOFF.md` PRIMERO (bridge de la sesión anterior).
2. Luego `CLAUDE.md` (reglas) + este archivo + el epic referenciado en IN-PROGRESS.
3. Mueve la siguiente US/ENH/BUG de **INBOX** (marcada `status:ready`) a **IN-PROGRESS** antes de empezar.
4. Cambia label del issue: `status:triage` → `status:in-progress`.
5. Implementa con tests verdes + typecheck.
6. Commit con header `<tipo>(<scope>): <ID> — <desc> (refs #<issue>)` y push.
7. Cambia label → `status:fix-committed` + comment con template CLAUDE.md §3 paso 6.
8. Mueve item a DONE en este archivo o a la tabla histórica si cierra sprint.
9. Resumen de ronda al owner siguiendo CLAUDE.md §11.
10. Al cierre de sesión: invocar `/handoff` para limpiar SPRINT.md y dejar bridge.

**Regla sagrada:** 1 US = 1 commit. No mezclar varios IDs en el mismo commit.

**Regla post-Sprint 26 (decisión owner 2026-05-22):** desarrollo secuencial puro. 1 sesión activa, 1 lane, 1 branch. Migraciones consecutivas sin paralelización para evitar collisions de revision IDs.
