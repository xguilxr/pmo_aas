# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-10 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Sprint 12 (v1.10/v1.11) — Bloques 1+2+3 ENTREGADOS 2026-05-06
Branch sesión: claude/sprint-12-bloques

Sprint 12 entregado en orden Bloque 1 → 2 → 3 (ENH-065 #236
cerrado por owner pre-arranque):
  Bloque 1 — Plan: BUG-049/050/051 + US-095/096
  Bloque 2 — Admin: US-094 + ENH-062
  Bloque 3 — Reportes: ENH-063 + ENH-064

Pendiente verificación owner: cerrar #227-235.

Post-Sprint 12 (próximo bloque): redesign RAID + Area requirements
  (no cubierto por issues actuales). Owner abrirá scope en sesión
  siguiente sobre branch claude/redesign-raid-area-requirements-EhZ3d.

Próximo libre: US-097, BUG-052, ENH-066.
```

---

## 📥 INBOX / TRIAGE

> Issues recién creados que todavía no han sido asignados a un Bloque.

```
(vacío)
```

---

## ⏳ QUEUE

**Sprint 11 (v1.10) — Bloque 1 ENTREGADO 2026-05-06. Bloques 2+3 `status:ready` por owner 2026-05-06.**

### Sprint 11 — Bloque 1: Nav review (2 BUGs) ✅ ENTREGADO
- [x] BUG-042 #206 — Breadcrumb desde Programa → link Org va a PMO en lugar de Admin — `4591aee`
- [x] BUG-043 #207 — Panel de Programa en vista PMO Org no es clicable — `98822f7`
- [x] (pasada UI 2026-05-06 → 23 findings → 13 issues triagados → Bloques 2 + 3)

### Sprint 11 — Bloque 2: Nav cleanup (5 issues — cierra patrón BUG-042) ✅ ENTREGADO
- [x] BUG-044 #216 — Admin Org → tabla proyectos `?ctx=admin` + project detail ctx-aware — `0e1bd0e`
- [x] BUG-045 #217 — Admin Supervisión → links proyectos `?ctx=admin` — `63c5352`
- [x] ENH-057 #218 — Admin pages con Breadcrumb (4 pages) — `0aee75d`
- [x] ENH-058 #219 — `pmo/projects/new` + `pmo/requests/new` con Breadcrumb + BackLink — `de9dc0b`
- [x] ENH-059 #220 — `admin/users/[id]` migra a `<BackLink>` reutilizable — `9cc4fc6`

### Sprint 11 — Bloque 3: RAID polish (5 issues — correctness primero) ✅ ENTREGADO
- [x] BUG-046 #221 — Priority como badge color (P1=red, P2=warning, P3=info, P4+=neutral) — `e27d560`
- [x] BUG-047 #222 — closure_note vía Modal + Textarea (sin `window.prompt`) — `68e8d5b`
- [x] BUG-048 #223 — Title trim + min_length backend (TitleStr Annotated) + frontend submit guard — `213ad11`
- [x] ENH-060 #224 — Status dropdown spinner + check verde 1.5s — `55b615b`
- [x] ENH-061 #225 — Matriz P×I celdas clicables → filtran tabla con chip [×] — `a16699c`

### Backlog v2.0 — RAID polish diferidos (P3 de pasada UI 2026-05-06)
- Bulk actions multi-select RAID
- Empty states per-severity en lista RAID
- Preview modal "Abrir/Editar" link
- Keyboard shortcut (Ctrl+K) crear RAID item
- Type-change post-creación: confirmation modal
- Audit log UI por item RAID
- Date format inconsistency Issue table
- Closure prompt cancelar: estado inconsistente

---

## ⏳ Sprint 12 (v1.10/v1.11) — Bloques 1+2+3 ENTREGADOS 2026-05-06

### Sprint 12 — Bloque 1: Plan fixes + plantilla (5 issues) ✅ ENTREGADO
- [x] BUG-049 #230 — WBS natural sort (1.1 → 1.2 → 1.10) — `fb35a2e`
- [x] BUG-050 #231 — Outline level auto-calc en imports + backfill 0043 — `374e4cc`
- [x] BUG-051 #232 — Tareas delayed con marca visual roja — `99a481c`
- [x] US-095 #229 — Editar tarea (botón Pencil + modal pre-poblado) — `eab7849`
- [x] US-096 #227 — Plantilla XLSX con fórmulas + nuevos campos — `8889751`

### Sprint 12 — Bloque 2: Admin restructure (2 issues) ✅ ENTREGADO
- [x] US-094 #228 — Página `/admin` landing con 6 paneles — `41d617e`
- [x] ENH-062 #233 — Quitar "Gestión de" en labels admin — `8929a43`

### Sprint 12 — Bloque 3: Reportes refinamiento (2 issues) ✅ ENTREGADO
- [x] ENH-063 #234 — Filtro periodo (1d/1sem/2sem/1mes/3meses) — `7321e0f`
- [x] ENH-064 #235 — Default focus hitos/críticas/delayed — `f7db92c`

### Post-Sprint 12 — RAID + Area requirements redesign
- [ ] Owner redefinirá scope en próxima sesión: los issues anteriores
      cubren parte del RAID (ENH-054, BUG-046/047/048, ENH-060/061) y
      Area (US-091, ENH-020) pero **no satisfacen los requerimientos
      reales**. Branch reservada: `claude/redesign-raid-area-requirements-EhZ3d`.

### Reworks Sprint 11 ya entregados (esperando verificación)
- [x] #204 ENH-054 fase 2 — `25ec5a0`
- [x] #205 US-091 fase 2 — `aa1a1ad`
- [x] #209 ENH-055 fase 2 — `682b06c`

**Próximo libre:** US-097, BUG-052, ENH-066.

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

- **2026-05-06 (Sprint 12 Bloques 1-3 entregados):** 9 commits sobre branch `claude/sprint-12-bloques`, fast-forward desde `main` post-Sprint 11. Migración Alembic 0043 agregada (backfill de `tasks.outline_level`). Owner adelantó que el siguiente bloque será **redesign RAID + Area requirements** (no cubierto por #204/#205/#209/#221-225 ni US-091): scope se definirá al inicio de la próxima sesión sobre branch `claude/redesign-raid-area-requirements-EhZ3d`. ENH-065 #236 cerrado por owner pre-arranque.
- **2026-05-06 (Sprint 11 Bloque 1 entregado):** BUG-042 (breadcrumb context-aware via `?ctx=admin` query param) `4591aee` + BUG-043 (ProgramCard como `<Link>` con hover/focus) `98822f7`. Pendiente owner: verificar + cerrar issues #206 #207.
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
