# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-29 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Rediseño V1 project detail — 21 issues entregados en branch
claude/practical-ptolemy-s7LyL (status:fix-committed, esperan verificación
del owner). Sin migraciones Alembic. Tests backend 565 passed/1 skipped;
next build + tsc verdes.

Bloque A (layout):     BUG-064 #490, ENH-126 #491
Bloque B (Resumen):    ENH-127 #492, ENH-128 #493, ENH-129 #494,
                       ENH-130 #495, ENH-131 #496, US-149 #497,
                       BUG-065 #498, ENH-132 #499
Bloque C (Plan):       BUG-066 #500, BUG-067 #501, ENH-133 #502,
                       ENH-134 #503, ENH-135 #504
Bloque D (Áreas):      ENH-136 #505, ENH-137 #506
Bloque E (Documentos): US-150 #507 (Organigrama Excel)
Bloque F (Reportes):   ENH-138 #508, ENH-139 #509, ENH-140 #510

Próximo libre: US-151, BUG-068, ENH-141.

Notas para el owner / follow-ups detectados:
- ENH-131 removió el panel de Equipo del Resumen: la gestión de miembros
  queda para Áreas/Recursos (EP017). Confirmar si se quiere un acceso
  directo desde el Resumen.
- ENH-134: el header "Criticidad" ahora importa como booleano (is_critical);
  el enum legacy solo se importa vía header "Prioridad Criticidad".
- Sucesoras en el form de tarea es read-only (se derivan de predecesoras).

Pendiente fuera de scope: ENH-115 #434 (breadcrumbs cross /pmo/**/reports).
```

---

## 📥 INBOX / TRIAGE

### Cross-cutting / sin sprint asignado
- [ ] **ENH-115 #434** — Breadcrumbs consistentes en `/pmo/**/reports`. `status:ready` desde 2026-05-23 pero diferido al cierre del rediseño grande. Owner pasa a ready o reasigna sprint cuando lo prioriza.

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

### Snapshots históricos (postergado v2.0)
- Snapshots periódicos de KPIs y semáforo.
- S-07 Curva S (descartada).
- S-10 Entregables formales (concepto no configurado).

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
| 27-29 | v1.26 | 2026-05-25 | 10 (mega-PR EP020: US-123 a US-132) |
| 30-32 | v1.27 | 2026-05-23 | 22 (rediseño Minutas + Reports — ver `SPRINT-DONE-HISTORY.md`) |

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
- [ ] Snapshots históricos de KPIs y semáforo.
- [ ] KPIs custom por admin tenant.
- [ ] **Cleanup post-Sprint 32**: borrar `apps/web/app/(app)/pmo/projects/[id]/ai-minutes/` y `.../reports/tweak/` carpetas enteras (hoy son redirects 301). Tras 1 sprint en main sin reportes de bookmarks rotos.
- [ ] **Persistencia reports L1/L2** (PMO/Org/Prog): hoy cascarón. Cuando owner defina estructura del Reporte Status PMO en sesión separada, agregar `generator='pmo'|'organization'|'program'` + nullable `project_id` o tabla aparte.
- [ ] **Dirty-flag fino en builder** (mejora ENH-125): comparar canvas vs plantilla cargada para detectar cambios sin guardar incluso cuando hay `loadedTemplateId`.

---

## Notas y cambios recientes

- **2026-05-26 (rediseño V1 project detail — 21 issues #490-#510):** branch
  `claude/practical-ptolemy-s7LyL`. Layout de tabs (fondo sólido + Lecciones
  al final), Resumen rediseñado (sin RAG; datos clave en la hoja; gauge de
  Avance con Hitos/Críticos/Atrasados; Salud/Fase/Presupuesto Restante;
  tarjetas RAID + mini-Gantt; feed de actividad real desde audit_log; sin
  sub-tabs ni grilla de módulos), Editar (cancelar al resumen + Salud/Real
  editables), Plan (Gantt ordena por WBS; Completada en verde; Criticidad
  booleana; plantilla V1 con Área Responsable + font negro + matching;
  forms reordenados con Área/Responsable en Nueva), Áreas→Áreas/Recursos +
  Directorio→Recursos, Organigrama Excel de 4 hojas, builder de Reportes
  (preview en vivo del canvas, Visualizar PDF, Guardar Reporte al historial).
  Sin migraciones. Backend 565 passed/1 skipped.

- **2026-05-24 (BUG-063 — fix integral generación minutas):** branch `claude/dreamy-heisenberg-jJkUS`, 4 commits.
  - Backend: participants ya no se aplanan mal como keys del dict; RAID `_normalize_raid_block` reemplazado por el validator que produce el shape canónico `{actions, risks, decisions, issues}`. Eliminada la invocación de `match_participants` en `create_minute` (owner: enfocar minuta en minuta). 422 al guardar arreglado en cascada.
  - Mapping de tickets: A → Issue(type=action), R → Risk, D → Issue(type=decision), I → Issue(type=issue). Lessons/changes legacy retenidos para retro-compat.
  - Prompt MINUTE_SYSTEM con few-shot real Highlander; reglas estrictas de detalle (5-15 bullets/tema, prefijo speaker cuando importe, ≥ 1 RAID si hay menciones concretas).
  - Frontend: preview read-only reemplazado por form editable pre-cargado con output IA. Permite editar resumen, fecha, participantes (nombre/rol/area), temas con bullets, items RAID (A/R/D/I con responsable y due_date), notas libres. Botón "Guardar Minuta" persiste el estado actual del form.
  - Detail page renderiza `summary` + `free_notes` y bullets[] para temas (fallback a notes legacy).
  - Migración 0076: re-seed idempotente de `report_sections` si la tabla está vacía (cierra el bug "catálogo vacío" del builder).
  - Tests: 549 passed, 1 skipped. TS + next build verdes.
- **2026-05-23 (cierre Sprints 30-32 — rediseño Minutas + Reports):** 22 items entregados secuencialmente en `claude/zen-brown-ivCbz`. Reorganización completa:
  - **Sidebar**: "Módulos de Proyecto" → "Módulos"; dropdown Reportes aplanado.
  - **Minutas**: listing simplificado (1 botón + columnas reordenadas), generador unificado `/minutes/new` con 3 modos (Transcript/Minuta/Manual), backend con `source_type` y migración 0075 (`minute_ai` origin). Detail sin MD/TXT. RAID labels claros.
  - **Reports `/pmo/reports`**: 4 tabs (PMO/Organizaciones/Programas/Proyectos) reemplazan Operacionales/Builder. Detail standalone para reportes. Cascarón intencional para historial L1/L2.
  - **Reports proyecto**: 3 tabs (Generar/Historial/Programar). 3 paneles default (Avance/Seguimiento/Look-ahead). Períodos extendidos (3 semanas + custom from/to). Catálogo plantillas builder. Scheduled custom soportado.
  - **Builder**: Modo + Ventana (value+unit) persistido en plantilla. Edit via `?template_id=X`. Preview live con marcas A4. Navigation guard.
  - **Cleanup**: `/ai-minutes/new` y `/reports/tweak` ahora redirects 301.
- **2026-05-25 (mega-PR EP020 completo):** 10 US entregadas (US-123 a US-132). Mergeado a main.
- **2026-05-22 (cierre Sprint 26 + skill /handoff):** Sprint 26 cerrado (16 items). Minutas v1.0 + Backbone EP020.

---

## Instrucción para Claude Code

Cuando arranques una sesión nueva:

1. Lee `docs/project-management/HANDOFF.md` PRIMERO.
2. Luego `CLAUDE.md` + este archivo + el epic referenciado en IN-PROGRESS.
3. Mueve la siguiente US/ENH/BUG de **INBOX** (marcada `status:ready`) a **IN-PROGRESS** antes de empezar.
4. Cambia label del issue: `status:ready` → `status:in-progress`.
5. Implementa con tests verdes + typecheck.
6. Commit con header `<tipo>(<scope>): <ID> — <desc> (refs #<issue>)` y push.
7. Cambia label → `status:fix-committed` + comment con template CLAUDE.md §3 paso 6.
8. Mueve item a DONE en este archivo o a la tabla histórica si cierra sprint.
9. Resumen de ronda al owner siguiendo CLAUDE.md §11.
10. Al cierre de sesión: invocar `/handoff` para limpiar SPRINT.md y dejar bridge.

**Regla sagrada:** 1 US = 1 commit. No mezclar varios IDs en el mismo commit.

**Regla post-Sprint 26 (decisión owner 2026-05-22):** desarrollo secuencial puro. 1 sesión activa, 1 lane, 1 branch. Migraciones consecutivas sin paralelización.
