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

**Revamp v2 — ronda de limpieza.** Sin US activa. Fases 0-8 mergeadas a
`main` (PR #610). Siguiente: fase 9 — 3 PRs propios de code review
transversal con `code-review --comment` (`revamp-v2/FASE-9.md`).

- [x] Feedback: 14/15 hechos (`REVAMP-V2-FEEDBACK.md`); punto 11 (Plan e
  IA) es decisión de producto sin cerrar (D5)
- [x] Fases 0-8 (BUG-095..097, US-248..271, DEC-036..039) → [ ] 9
  — runbooks en `revamp-v2/FASE-0..9`, wireframes W1–W8 OK
- [ ] Mobile, sin revisar ninguna pantalla

---

## ⏳ ESPERANDO al owner

- [ ] **Decisión D7** (logo PMO-aaS, plan §7; D1 cerrada DEC-038, D2 cerrada
  DEC-036, D3 cerrada DEC-037, D4 cerrada DEC-039, D6 cerrada en W5). No
  bloquea ninguna fase — mientras, la marca es texto.
- [ ] **Leer el registro del despliegue** de `0110`, `0111` y `0115`: las
  migraciones ya corrieron; falta mirar lo que dejaron escrito.
- [ ] **Cómo se traza un batch.** US-203–222 se mergearon sin issues: o se
  crean al cerrar el lote, o se escribe que el lote se traza por commit.

---

## 📥 INBOX

- [ ] **Glosario de datos** (FASE-9 pasada 2): #613-#619.
- [ ] **W3 — RLS de Postgres**: #599 (US-240), #600 (US-241), #601 (US-242).
- [ ] **EP021**: quedan US-223, US-225 y US-226. US-224 entregada.
- [ ] **US-239** — clave de proyecto estilo Jira en la URL (mig. 0120).
- [ ] **Hueco de compat**: `GET /projects` no normaliza `phase`/`type`.
  Ver `core/compatibilidad.py`.
- [ ] **Pantalla del catálogo de IA** en `/admin/plan?tab=ia` — US-224 solo
  tiene API.

---

## 📦 Lo demás

Backlog, diferidos y DONE: [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md).
Historial narrativo: [`SPRINT-DONE-HISTORY.md`](SPRINT-DONE-HISTORY.md).
