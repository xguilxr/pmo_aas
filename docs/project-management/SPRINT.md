---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# SPRINT.md — lo activo

> Solo IN-PROGRESS, ESPERANDO e INBOX inmediato. Lo demás vive en
> [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md), en un issue o en
> [`SPRINT-DONE-HISTORY.md`](SPRINT-DONE-HISTORY.md). Techo: 60 líneas (CI).
> Estado derivado: `python scripts/estado.py` · IDs: `proximo_id.py`.

---

## 🔴 IN-PROGRESS

**Revamp v2 — ronda de limpieza.** Sin US activa. Siguiente paso: fase 3
(dashboard) — necesita wireframe **W1** aprobado (`docs/project-management/revamp-v2/FASE-3.md`).

- [x] Feedback: 15 puntos en `REVAMP-V2-FEEDBACK.md` (2026-09-10/11)
- [x] Plan + diagramas: `REVAMP-V2-PLAN.md` · runbooks `revamp-v2/FASE-0..9`
- [x] Fase 0 (BUG-095/096/097) → [x] 1 (US-248/249) → [x] 2 (US-250/251) →
  [ ] 3…8 (con wireframe) → 9
- [ ] Mobile, sin revisar ninguna pantalla

---

## ⏳ ESPERANDO al owner

- [ ] **Wireframes W1–W8** (plan §5): gate de las fases 3–8. Se hacen con la
  skill `design` y se aprueban en el canvas.
- [ ] **Decisiones D1/D3/D4/D6/D7** (plan §7; D2 cerrada, DEC-036). D3
  bloquea la 4, D1 la 6, D4 la 7.
- [ ] **Leer el registro del despliegue** de `0110`, `0111` y `0115`: las
  migraciones ya corrieron; falta mirar lo que dejaron escrito.
- [ ] **Cómo se traza un batch.** US-203–222 se mergearon sin issues: o se
  crean al cerrar el lote, o se escribe que el lote se traza por commit.

---

## 📥 INBOX

- [ ] **W3 — RLS de Postgres**: #599 (US-240), #600 (US-241), #601 (US-242).
- [ ] **EP021**: quedan US-223, US-225 y US-226. US-224 entregada.
- [ ] **US-239** — clave de proyecto estilo Jira en la URL (mig. 0120).
- [ ] **Hueco de compat**: `GET /projects` no normaliza `phase`/`type`.
  Ver `core/compatibilidad.py`.
- [ ] **Pantalla del catálogo de IA** en `/admin/ai` — US-224 solo tiene
  API. Coordinar con FASE-7 (Plan e IA en una página).

---

## 📦 Lo demás

Backlog, diferidos y DONE: [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md).
Historial narrativo: [`SPRINT-DONE-HISTORY.md`](SPRINT-DONE-HISTORY.md).
