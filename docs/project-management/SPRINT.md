# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-9 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Sprint 10 (v1.9) — Bloque 6 (Reportes) marcado status:ready 2026-05-05
Branch sesión: claude/archive-sprint-tasks-Ee7XC

Sin US activa todavía. Orden de implementación del Bloque 6:
  ENH-055 #209 → US-092 #210 → ENH-056 #212 → US-093 #211
  (US-093 depende de ENH-055 + US-092).

Próximo libre: US-094, BUG-044, ENH-057.
```

---

## 📥 INBOX / TRIAGE

> Issues recién creados que todavía no han sido asignados a un Bloque.

```
(vacío)
```

---

## ⏳ QUEUE

**Sprint 10 (v1.9) — TRIAGE COMPLETO 2026-05-05.**
**Bloque 6 (reportes) marcado `status:ready` por owner 2026-05-05.**

15 issues en total: 10 en 5 bloques plan/RAID/áreas + 4 reportes (Bloque 6, ready) + 2 bugs Sprint 11.

### Sprint 10 — Bloque 1: Plan visualización (3 ENHs)
- [ ] ENH-047 #196 — Toggle agrupación WBS en lista de tareas
- [ ] ENH-048 #197 — Filtros chip multi-select Hitos / Críticos / Retrasados
- [ ] ENH-049 #198 — Columna Responsable visible en lista

### Sprint 10 — Bloque 2: Plan template + columnas (3 items)
- [ ] ENH-050 #199 — Campo "Hito Relacionado" en form de tarea
- [ ] ENH-051 #200 — Campo "Criticidad" en form de tarea
- [ ] US-090  #201 — Columnas Outline Level (auto), Duration (auto, max 21d), Predecessors/Successors (asignables)

### Sprint 10 — Bloque 3: Plan import/export UX (2 ENHs)
- [ ] ENH-052 #202 — Botones Plantilla / Descargar / Importar misma fila + colores distintos
- [ ] ENH-053 #203 — Mapeo de columnas asistido por IA al importar

### Sprint 10 — Bloque 4: RAID editable completo (1 ENH)
- [ ] ENH-054 #204 — Toda la información de ítems RAID editable inline/modal

### Sprint 10 — Bloque 5: Áreas / Equipos / Actores (1 US)
- [ ] US-091  #205 — Jerarquía Área→Equipo→Actor + teléfono + UI rediseñada (vista por área / por actor) + toggle filtro

### Sprint 10 — Bloque 6: Reportes 3 vistas + cadencia mensual ✅ status:ready
- [ ] ENH-055 #209 — Reportes: layout 3 vistas (Catálogo / Historial / Creación) + implementa Catálogo
- [ ] US-092  #210 — Reportes: Historial de reportes generados (persistencia DB + R2)
- [ ] US-093  #211 — Reportes: Creación nueva con IA + preview (tercera vista)
- [ ] ENH-056 #212 — Reportes programados: cadencia mensual con día del mes (1-31) + clamp al último día
- Orden: ENH-055 → US-092 → ENH-056 → US-093 (US-093 depende de ENH-055 + US-092).

### Sprint 11 (v1.10) — Bloque 1: Nav review (2 BUGs)
- [ ] BUG-042 #206 — Breadcrumb desde Programa → link Org va a PMO en lugar de Admin
- [ ] BUG-043 #207 — Panel de Programa en vista PMO Org no es clicable
- [ ] (pasada con `ui-reviewer` agent comenzando por RAID, luego nav)

**Decisiones owner (clarificación 2026-05-05):**
1. US-090: Outline Level + Duration auto-calculadas (Duration max 21 días); Predecessors/Successors asignables como referencias WBS.
2. ENH-053: approach mínimo (heurística + LLM del tenant si AI habilitada; manual override siempre disponible).
3. US-091: mantener tabla `project_areas` con `type ∈ {area,actor,team}` + agregar FK explícitas `team_id` + `area_id` + campo `phone`.
4. BUG-042/043: van a Sprint 11 como parte del nav review (no Bloque 0 hotfix).
5. Reportes Bloque 6: 3 vistas (Catálogo, Historial, Creación IA). ENH-055/US-092/US-093/ENH-056 = `status:ready`.

**Pendiente owner:**
- Revisar y asignar `status:ready` a los issues plan/RAID/áreas (#196-#207, excluyendo reportes que ya están ready).
- Confirmar versión target (default propuesto: v1.9 Sprint 10, v1.10 Sprint 11).

**Próximo libre tras este triage:** US-094, BUG-044, ENH-057.

### Follow-ups identificados (Sprint 9+)
- US-081 — Borrar físicamente tablas `roles` + `user_roles` (migración 0037+) tras validación de Sprint 6 en producción.
- ENH futuro — Filtrado efectivo de queries por `organization_user_exclusions`.
- Cross-empresa nativo (post-ENH-043): si ≥3 grupos lo solicitan, abrir US con `program_organizations` + redesign listados.
- US-086 fase 2 — Cablear stakeholders FK en Charter (sponsor / business lead / technical lead) + migración data charters strings → stakeholders.
- US-084 fase 2 — Banner de divergencias cuando importadores MPP/XLSX detecten diferencia entre manual y calculado; botón "Resetear a calculado" en UI.
- US-087 fase 2 — Campos `Task.hours_estimated/hours_actual` para que `compute_kpis` exponga horas plan/real.
- Hard-delete User cuando hay `project_request.requested_by` (US-088 fase 2) — endpoint reasignación interactiva.

---

## ✅ DONE

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo (Sprints 1-9).**

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

---

## 📋 Backlog v2.0 (post-v1.x)

> **Contexto (DEC-020):** plataforma definida como herramienta de apoyo/visualización
> sin aprobaciones jerárquicas. US-061 cancelada; US-059/US-060 entregadas en Sprint 4.

- [ ] ENH-035 #158 — Análisis profundo optimización CI tests pesados (post-MVP, diferido Sprint 7).
- [ ] (posibles items futuros: 2FA, SSO, magic-link login)

---

## Notas y cambios recientes

- **2026-05-05 (Sprint 10 archivado):** se mueven Sprints 2-9 desde SPRINT.md a SPRINT-DONE-HISTORY.md como parte del cierre de Sprint 9. Se agrega paso 6 a CLAUDE.md §6 ("limpieza al cierre de sprint"). SPRINT.md queda con solo Sprint 10 IN-PROGRESS / QUEUE + tabla resumen DONE.
- **2026-05-05 (Sprint 10 triage):** owner pidió planeación próximos 2 sprints + mejoras a página de reportes. 15 issues creados (#196-#207, #209-#212) en 6 bloques Sprint 10 + 1 bloque Sprint 11. Bloque 6 (reportes) marcado `status:ready` directo. Decisiones documentadas arriba en QUEUE.
- **2026-05-05 (Sprint 9 cerrado):** 6 items entregados (US-088 hard delete + ENH-045/US-089/ENH-046 batch + BUG-041 + UX polish). PR #213 mergeado a main 044dc08. Detalle en SPRINT-DONE-HISTORY.md.
- **Notas históricas de Sprints 2-8:** ver `SPRINT-DONE-HISTORY.md` (incluye decisiones DEC-018/020/021/022, contexto reshuffles, naming conventions, runbooks Cloudflare R2, Tailscale).

---

## Instrucción para Claude Code

Al iniciar sesión, lee este archivo y los epics relevantes para las US en cola.
Trabaja el backlog en orden sin parar entre US. Por cada US:
1. Implementa la US completa.
2. Haz commit con el mensaje indicado antes de tocar la siguiente.
3. Mueve la US de IN-PROGRESS a DONE con fecha de hoy.
4. Mueve la primera US de QUEUE a IN-PROGRESS.
5. Arranca la siguiente US de inmediato.

Continúa hasta que no queden US en QUEUE o el contexto se agote.
Si el contexto se agota a mitad de una US, haz commit del avance con prefijo `wip:` y anota aquí dónde quedó.
