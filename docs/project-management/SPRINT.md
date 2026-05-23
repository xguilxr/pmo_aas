# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-29 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Sprint 30 — Rediseño Minutas + Reports (decisión owner 2026-05-23).
Branch: claude/zen-brown-ivCbz.

Bloque 1 — Pre-requisitos backend (3 items existentes).
Bloque 2 — Sidebar + bug + cosméticos minutas (4 items nuevos).

Próximo libre: US-149, BUG-063, ENH-126.
```

---

## 📥 INBOX / TRIAGE

> Todos los issues abajo están en `status:ready` (owner aprobó). Claude los ataca secuencialmente. 1 issue = 1 commit + push + comment.

### Sprint 30 — Pre-requisitos + Sidebar + Minutas cosmético (7 items)

**Bloque 1 — Pre-requisitos backend (desbloquea B y D)**
- [ ] **US-140 #428** — Persistir reports del builder (`generator='builder'`). CRÍTICO para tab Historial.
- [ ] **US-136 #424** — Tabs Resumen/Reportes en `/pmo/organizations/[id]`. Pre-req B2.
- [ ] **US-137 #425** — Tabs Resumen/Reportes en `/pmo/programs/[id]`. Pre-req B3.

**Bloque 2 — Sidebar + bug + minutas cosmético**
- [ ] **ENH-116 #450** — Sidebar: "Módulos de Proyecto" → "Módulos" + aplanar dropdown Reportes.
- [ ] **BUG-062 #451** — Click en nombre de minuta abre el listing en vez del detail. Fix en `/pmo/minutes/page.tsx:113` (href apunta al listing del proyecto).
- [ ] **ENH-117 #452** — Minutas listing rediseñado: un solo botón "Generar Minuta" + columnas Folio/Minuta/Fecha/Tipo/Exportar/Preview/Borrar.
- [ ] **ENH-118 #453** — Detail de minuta: quitar export MD/TXT, dejar solo PDF/DOCX.

### Sprint 31 — Minutas generador unificado + Reports PMO 4 tabs (7 items)

**Bloque 1 — Minutas generador (Transcript/Minuta/Manual)**
- [ ] **US-143 #455** — Backend: extender `POST /ai/projects/{id}/minutes/generate` con `source_type=transcript|minute|manual`.
- [ ] **US-142 #454** — Frontend nueva ruta `minutes/new` con 3 modos. Reemplaza `ai-minutes/new` (borrar carpeta).
- [ ] **ENH-119 #456** — Detail minuta: RAID sugeridos editables hasta confirmar → link read-only.

**Bloque 2 — `/pmo/reports` 4 tabs (PMO/Org/Prog/Proyectos)**
- [ ] **US-144 #457** — Tab "PMO" (default): descargar Status PMO + historial. Cascarón funcional, estructura del reporte se define en sesión aparte.
- [ ] **US-145 #458** — Tab "Organizaciones": filtro org + historial.
- [ ] **US-146 #459** — Tab "Programas": filtros org+programa + historial.
- [ ] **ENH-120 #460** — Tab "Proyectos": mover contenido actual + fixes folio/tipo/período + filtrar drafts + link al detail + label "Builder".

### Sprint 32 — Reports proyecto + Builder unificado (8 items)

**Bloque 1 — Reports proyecto rediseñado**
- [ ] **US-147 #462** — Endpoint reporte Look-ahead (`POST /projects/{id}/reports/look-ahead/generate`).
- [ ] **ENH-122 #463** — Períodos extendidos en Avance/Seguimiento: "3 semanas" + rango custom from/to.
- [ ] **ENH-121 #461** — Reports proyecto: 3 tabs Generar/Historial/Programar + 3 paneles default + catálogo plantillas builder.
- [ ] **ENH-114 #433** — Schedule type=custom en form de ScheduledReportsSection (encaja en tab Programar).

**Bloque 2 — Builder unificado**
- [ ] **US-148 #464** — Builder header: selector Modo + ventana de tiempo persistida en plantilla.
- [ ] **ENH-123 #465** — Builder catálogo: verificar 22 secciones EP020 + drag-drop.
- [ ] **ENH-124 #466** — Builder: SectionParamsPanel contextual + PreviewPane real-time con cortes de página.
- [ ] **ENH-125 #467** — Builder: guardar/editar plantilla + prompt salir sin guardar + edición desde tab Generar.

### Cross / cuando haya hueco
- [ ] **ENH-115 #434** — Breadcrumbs consistentes en `/pmo/**/reports`.

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

### Admin UI settings (cross — sin sprint asignado al rediseño Minutas/Reports)
- [ ] **ENH-111 #430** — UI admin tenant para `progress_calculation_method`.
- [ ] **ENH-112 #431** — UI admin tenant para `task_load_thresholds`.
- [ ] **ENH-113 #432** — UI admin org para upload `client_logo_url`.

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
| 27-29 | v1.26 | 2026-05-25 | 10 (mega-PR EP020: US-123/124/125/126/127/128/129/130/131/132) |

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

- **2026-05-23 (apertura Sprint 30-32 — rediseño Minutas + Reports):** owner pidió rediseño grande de Minutas y Reports. 16 issues triage cerrados (12 duplicados + 4 superseded), 18 issues nuevos creados (#450-#467), 5 issues existentes reasignados al plan (US-136/137/140, ENH-114/115). Plan: Sprint 30 cleanup + sidebar + cosmético minutas; Sprint 31 generador minutas unificado + 4 tabs `/pmo/reports`; Sprint 32 reports proyecto + builder unificado. Total 22 items secuenciales.
- **2026-05-25 (mega-PR EP020 completo):** 10 US entregadas en 10 commits secuenciales (US-123 a US-132). Decisiones DEC-025..029 registradas en DECISIONS.md. Migraciones 0073 + 0074 en DB-CHANGES.md. Mergeado a main (PR #449).
- **2026-05-22 (cierre Sprint 26 + skill /handoff):** Sprint 26 cerrado completo (16 items). Frente Minutas v1.0 + Backbone EP020. 3 collisions de alembic resueltas. **Decisión clave:** desarrollo secuencial puro.
- **2026-05-22 (Sprint 26 Bloque 0 — Minutas v1.0 + EP020 planning):** catálogo de 22 secciones atómicas de EP020 cerrado. Promoción a epic oficial `EP020-report-builder.md`. Gold standard de minuta (Highlander EAM-BNF) como referencia normativa.

---

## Instrucción para Claude Code

Cuando arranques una sesión nueva:

1. Lee `docs/project-management/HANDOFF.md` PRIMERO (bridge de la sesión anterior).
2. Luego `CLAUDE.md` (reglas) + este archivo + el epic referenciado en IN-PROGRESS.
3. Mueve la siguiente US/ENH/BUG de **INBOX** (marcada `status:ready`) a **IN-PROGRESS** antes de empezar.
4. Cambia label del issue: `status:ready` → `status:in-progress`.
5. Implementa con tests verdes + typecheck.
6. Commit con header `<tipo>(<scope>): <ID> — <desc> (refs #<issue>)` y push.
7. Cambia label → `status:fix-committed` + comment con template CLAUDE.md §3 paso 6.
8. Mueve item a DONE en este archivo o a la tabla histórica si cierra sprint.
9. Resumen de ronda al owner siguiendo CLAUDE.md §11.
10. Al cierre de sesión: invocar `/handoff` para limpiar SPRINT.md y dejar bridge.

**Regla sagrada:** 1 US = 1 commit. No mezclar varios IDs en el mismo commit.

**Regla post-Sprint 26 (decisión owner 2026-05-22):** desarrollo secuencial puro. 1 sesión activa, 1 lane, 1 branch. Migraciones consecutivas sin paralelización para evitar collisions de revision IDs.
