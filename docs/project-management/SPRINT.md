# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-25 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Sprint 26 (v1.25) — Bloque 0 Minutas v1.0 — EN CURSO 2026-05-22

  Lanes A/B/C ya en main (BUG-061, ENH-103, ENH-104, ENH-106, ENH-107, ENH-108).
  Migraciones agregadas a main: 0064 (client_logo_url), 0065 (status_rag),
    0067 (tasks.is_critical), 20260522_0068 (scheduled_minutes),
    20260523_0068 (minute_origin), 20260523_0069 (merge heads).

  Lane D — PR #408 abierto:
    ENH-102 — Parser RAID estricto (solo A/R/D/I) + validador post-IA.
    ENH-105 — Estructura de minuta v1.0 (6 secciones fijas).
    Branch sesión: claude/sprint26-b0-lane-d-prompts-parser
    Estado: CI api-migrations-postgres pasa tras rebase sobre main + merge heads.

  Bloque 1 Dependencias EP020 — entregadas en main:
    ENH-097 #373 — tasks.is_critical boolean (migración 0067).
    ENH-098 #374 — progress_calculation_method por tenant.
    ENH-099 #375 — task_load_thresholds por tenant.
    ENH-100 #376 — organizations.client_logo_url + upload (migración 0064).
    ENH-101 #377 — projects.status_rag declarativo (migración 0065).

Próximo libre: US-133, BUG-062, ENH-109.
(US-119 reservada para EP017 cleanup diferido; US-120 a US-132 reservadas EP020.)
```

---

## 📥 INBOX / TRIAGE

> Issues creados con `status:triage`. Owner pasa a `status:ready` para arrancar.

### Sprint 26 Bloque 2 — Backbone EP020 (siguiente)

- [ ] **US-120 #378** — Modelo y seed del catálogo de 22 secciones atómicas. Reusa `docs/epics/drafts/EP020-secciones-atomicas.md` como referencia normativa. Tabla `report_sections_catalog` + endpoint `GET /reports/sections-catalog` + service `app/services/reports/catalog.py`.
- [ ] **US-121 #379** — Servicio cálculo % avance configurable por tenant. Dispatcher de 3 métodos (`weighted_duration` default, `weighted_effort`, `simple_count`). Consume ENH-098 ya en main.
- [ ] **US-122 #380** — Modelo de plantillas + 4 plantillas seed: L3-AVANCE (modo A), L3-SEGUIMIENTO (modo B), L1-PORTAFOLIO, L2-ORG. Tabla `report_templates` con `composition_mode` y `visibility`.

### Sprint 27 — Motor de render + Canvas Nivel 4

**Bloque 1 (motor + export):**
- [ ] **US-123 #381** — Engine de render con modos composición A/B. Service `app/services/reports/engine.py`.
- [ ] **US-130 #390** — Export PDF de reportes custom (reusa US-037).

**Bloque 2 (canvas Nivel 4):**
- [ ] **US-124 #382** — Canvas drag-and-drop + preview en vivo en `/pmo/projects/{id}/reports/builder`.
- [ ] **US-125 #383** — Panel de parámetros transversales.
- [ ] **US-126 #384** — Plantillas privadas + publicar al proyecto.

### Sprint 28 — IA conversacional + Suscripciones

- [ ] **US-127 #385** — Modo IA conversacional construyendo el reporte (tool calls). Reusa cascada EP008.
- [ ] **US-131 #386** — Suscripciones de reportes custom (reusa motor `scheduled_reports` US-056).

### Sprint 29 — UI Niveles 1/2 + Gantt

- [ ] **US-128 #387** — Módulo UI Reportes Nivel 1 PMO (`/pmo/reports/portfolio`).
- [ ] **US-129 #388** — Módulo UI Reportes Nivel 2 Organización (tab nuevo en org/programa).
- [ ] **US-132 #389** — Render headless del Gantt WBS-1 para S-19 (puppeteer/playwright).

### Diferidos Sprint 26 Bloque 0 (pendientes de verificación owner)

- [ ] **BUG-061 #391** — Preview muestra RAID pero al guardar no persiste.
- [ ] **ENH-103 #393** — Match participantes ↔ actores del proyecto (auto-link + crear faltantes).
- [ ] **ENH-104 #394** — Título auto desde nombre de archivo + prompt al guardar si vacío.
- [ ] **ENH-106 #396** — Campo de auditoría `origin` en minuta.
- [ ] **ENH-107 #397** — Suscripciones programadas de minutas.
- [ ] **ENH-108 #398** — Copy-paste directo de transcript (sin file upload).
- En PR #408: ENH-102 #392 + ENH-105 #395.

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
- [ ] **US-105 #311** — Import Plan: wizard matching responsables → Actor. Depende del shape final del catálogo Actores.
- [ ] **Tab Organigrama de US-106** — placeholder UI; el cableado funcional depende del paquete EP017 final.
- [ ] **US-119 cleanup** — drop legacy `actors.team_id`, `actors.is_lead`, `teams.area_id`, `tasks/risks/issues.area_id`. Esperando cableado completo de PersonPicker.

### Snapshots históricos (postergado v2.0)
- Snapshots periódicos de KPIs y semáforo (S-05 tendencia, sparklines, deltas vs anterior).
- S-07 Curva S (descartada — incompatible con flexibilidad del plan).
- S-10 Entregables formales (concepto no configurado en plataforma).

---

## ✅ DONE

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo.**

| Sprint | Versión | Cerrado | Items |
|---|---|---|---|
| 1 | v1.0 MVP | 2026-04-21 | ~94 (22 bloques) |
| 2 | v1.1 | 2026-04-23 | 18 (4 bloques + hotfix) |
| 3 | v1.2 | 2026-04-24 | 5 (2 bloques) |
| 4 | v1.3 | 2026-04-24 | 14 (4 bloques) |
| 5 | v1.4 | 2026-04-24 | 10 (6 bloques + follow-up) |
| 6 | v1.5 | 2026-04-25 | 5 (5 bloques) |
| 7 | v1.6 | 2026-04-28 | 10 (6 bloques, 1 diferido v2.0) |
| 8 | v1.7 | 2026-04-29 | 13 (7 bloques, 1 not_planned) |
| 9 | v1.8 | 2026-05-05 | 6 (2 bloques + hotfix UX) |
| 10 | v1.9 | 2026-05-06 | 14 (6 bloques) |
| 11 | v1.9 | 2026-05-06 | 12 (3 bloques) |
| 12 | v1.10/v1.11 | 2026-05-06 | 9 (3 bloques) |
| 13 | v1.12 | 2026-05-07 | 7 (1 bloque) |
| 14 | v1.13 | 2026-05-07 | 4 (1 bloque) |
| 15 | v1.14 | 2026-05-07 | 4 (1 bloque) |
| 16 | v1.14 | 2026-05-07 | 4 (1 bloque — Reportes) |
| 17 | v1.16 | 2026-05-08 | 2 (Bloque 0 + 0.5; Bloque 1 → Deferred) |
| 18 | v1.17 | 2026-05-08 | 3 (1 bloque) |
| 19 | v1.18 | 2026-05-09 | 6 (1 bloque) |
| 20 | v1.19 | 2026-05-09 | 5 (1 bloque) |
| 21 | v1.20 | 2026-05-09 | 4 (1 bloque) |
| 22 | v1.21 | 2026-05-09 | 2 (1 bloque) |
| 23 | v1.22 | 2026-05-09 | 1 (1 bloque) |
| 24 | v1.23 | 2026-05-09 | 12 (4 bloques — feedback batch) |
| 25 | v1.24 | 2026-05-10 | 5 (2 bloques — EP017 directorio) |

---

## 📋 Backlog v2.0 (post-v1.x)

> **Contexto (DEC-020):** plataforma definida como herramienta de apoyo/visualización sin aprobaciones jerárquicas. US-061 cancelada; US-059/US-060 entregadas en Sprint 4.

- [ ] ENH-035 #158 — Análisis profundo optimización CI tests pesados (post-MVP, diferido Sprint 7).
- [ ] US-081 — Borrar físicamente tablas `roles` + `user_roles` (migración 0037+) tras validación de Sprint 6 en producción.
- [ ] ENH futuro — Filtrado efectivo de queries por `organization_user_exclusions`.
- [ ] Cross-empresa nativo (post-ENH-043): si ≥3 grupos lo solicitan, abrir US con `program_organizations` + redesign listados.
- [ ] US-086 fase 2 — Cablear stakeholders FK en Charter + migración data charters strings → stakeholders.
- [ ] US-084 fase 2 — Banner de divergencias cuando importadores MPP/XLSX detecten diferencia entre manual y calculado.
- [ ] US-087 fase 2 — Campos `Task.hours_estimated/hours_actual` para que `compute_kpis` exponga horas plan/real.
- [ ] Hard-delete User cuando hay `project_request.requested_by` (US-088 fase 2) — endpoint reasignación interactiva.
- [ ] Snapshots históricos de KPIs y semáforo (habilita S-05 tendencia, sparklines, deltas vs periodo anterior en reportes EP020).
- [ ] KPIs custom por admin tenant (extensión del catálogo cerrado v1.0 de EP020).

---

## Notas y cambios recientes

- **2026-05-23 (hotfix alembic multiple heads):** ENH-106 (`20260523_0068_minute_origin`) y ENH-107 (`20260522_0068_scheduled_minutes`) se mergearon a main en paralelo con el mismo `down_revision='20260522_0067'`, dejando dos heads abiertos. Fix: merge migration `20260523_0069_merge_minute_heads` sin cambios de schema, branch `claude/fix-alembic-multiple-heads-0068`. Tras merge a main, CI api-migrations-postgres se recupera y PR #408 (lane D) se rebasea automáticamente.
- **2026-05-22 (Sprint 26 Bloque 0 — Minutas v1.0 + EP020 planning):** owner cerró el catálogo de 22 secciones atómicas de EP020 (working doc `docs/epics/drafts/EP020-secciones-atomicas.md`) tras 4 rondas de profundización por categoría. Promoción del draft a epic oficial `docs/epics/EP020-report-builder.md` con 13 US (US-120 a US-132) + 5 ENH dependencias (ENH-097 a ENH-101). Frente Minutas planificado en paralelo: 1 BUG + 7 ENH (BUG-061 + ENH-102 a ENH-108) basados en transcript+minuta gold standard del owner — caso Highlander EAM-BNF que define el nivel de detalle del parser IA. 26 issues creados en GitHub (#373-#398). Labels aplicados a los 26 (solo falta `EP020` por crear). Decisión arquitectónica clave: snapshots históricos del semáforo y KPIs salen del scope v1.0 → posterga a v2.0 (descarta S-05, sparklines, deltas).
- **2026-05-10 (EP017 Directorio de Proyecto — diseño + Sprint 25 entregado):** rediseño del módulo Áreas/Recursos basado en feedback de modelo (separar área funcional / equipo operativo / rol proyecto / participación temporal). Decisión clave: `actors` sigue como catálogo tenant; nueva tabla `project_participations` (con `is_primary` por persona-proyecto) reemplaza la jerarquía `Area→Team→Actor`; `teams` queda plano sin FK a area; `project_roles` nuevo catálogo editable. 5 US entregadas (US-114→US-118) sobre branch `claude/design-areas-resources-8DIfi`. Migraciones 0061 + 0062. Epic doc: `docs/epics/EP017-project-directory.md`. Diferidos significativos (sin issue): `/admin/areas` rediseño completo; cableado de PersonPicker en cada form; US-118 Fases 2/3; US-119 cleanup.

---

## Instrucción para Claude Code

Cuando arranques una sesión nueva:

1. Lee `CLAUDE.md` (reglas) + este archivo + el epic referenciado en el bloque IN-PROGRESS.
2. Mueve la siguiente US/ENH/BUG de la sección **INBOX** (ya marcada `status:ready` por owner) a **IN-PROGRESS** en este archivo antes de empezar.
3. Cambia el label del issue: `status:triage` → `status:in-progress`.
4. Implementa con tests verdes + typecheck.
5. Commit con header `<tipo>(<scope>): <ID> — <desc> (refs #<issue>)` y push.
6. Cambia label del issue → `status:fix-committed` y deja comment con el template del CLAUDE.md sección 3 paso 6.
7. Mueve el item de IN-PROGRESS → DONE en este archivo (o a la tabla histórica si cierra sprint).
8. Resumen de ronda al owner siguiendo CLAUDE.md sección 11.

**Regla sagrada:** 1 US = 1 commit. No mezclar varios IDs en el mismo commit.
