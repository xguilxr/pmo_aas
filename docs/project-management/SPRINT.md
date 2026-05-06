# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-10 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Sprint 11 (v1.10) — Bloque 1 (Nav review) marcado status:ready 2026-05-05
Branch sesión: claude/next-sprint-tasks-fITMO

Sin US activa todavía. Orden de implementación del Bloque 1:
  BUG-042 #206 → BUG-043 #207

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

**Sprint 11 (v1.10) — Bloque 1 marcado `status:ready` por owner 2026-05-05.**

### Sprint 11 — Bloque 1: Nav review (2 BUGs)
- [ ] BUG-042 #206 — Breadcrumb desde Programa → link Org va a PMO en lugar de Admin
- [ ] BUG-043 #207 — Panel de Programa en vista PMO Org no es clicable
- [ ] (pasada con `ui-reviewer` agent comenzando por RAID, luego nav)

**Próximo libre:** US-094, BUG-044, ENH-057.

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

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo (Sprints 1-10).**

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

---

## 📋 Backlog v2.0 (post-v1.x)

> **Contexto (DEC-020):** plataforma definida como herramienta de apoyo/visualización
> sin aprobaciones jerárquicas. US-061 cancelada; US-059/US-060 entregadas en Sprint 4.

- [ ] ENH-035 #158 — Análisis profundo optimización CI tests pesados (post-MVP, diferido Sprint 7).
- [ ] (posibles items futuros: 2FA, SSO, magic-link login)

---

## Notas y cambios recientes

- **2026-05-06 (Sprint 11 arranque):** Sprint 10 cerrado y archivado a SPRINT-DONE-HISTORY.md (14 items, PR #215 mergeado a main `7e03332`). SPRINT.md queda con Sprint 11 Bloque 1 IN-PROGRESS — solo BUG-042 + BUG-043 pendientes (nav review).
- **2026-05-05 (Sprint 10 triage):** owner pidió planeación próximos 2 sprints + mejoras a página de reportes. 15 issues creados (#196-#207, #209-#212) en 6 bloques Sprint 10 + 1 bloque Sprint 11. Detalle histórico en SPRINT-DONE-HISTORY.md.
- **Notas históricas de Sprints 2-9:** ver `SPRINT-DONE-HISTORY.md` (incluye decisiones DEC-018/020/021/022, contexto reshuffles, naming conventions, runbooks Cloudflare R2, Tailscale).

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
