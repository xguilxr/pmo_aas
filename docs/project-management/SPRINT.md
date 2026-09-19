---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-19
revisar_cada: 30d
---

# SPRINT.md — lo activo

> Solo IN-PROGRESS, ESPERANDO e INBOX inmediato. Lo demás vive en
> [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md), en un issue o en
> [`SPRINT-DONE-HISTORY.md`](SPRINT-DONE-HISTORY.md). Techo: 60 líneas (CI).
> Estado derivado: `python scripts/estado.py` · IDs: `proximo_id.py`.

---

## 🔴 IN-PROGRESS

**Batch 2026-09-19.** Rama `claude/inspiring-ramanujan-nltb7k`. Bloques 0, 0b
y A entregados y en `fix-committed`. Sigue el Bloque E (#637-#639) y luego F,
D, B, C. Orden completo en el draft del batch.

- [x] **Bloque 0** — #623, #624, #625 (DEC-044) · **0b** — #642…#651 ·
  **A** — #626, #627 (vaciado, DEC-045)
- [ ] Owner: correr `diagnostico_participaciones_cruzadas.py` (sin `--apply`)
- [ ] Revamp v2 fase 9 y mobile, en pausa: `revamp-v2/FASE-9.md`

---

## ⏳ ESPERANDO al owner

- [ ] **Decisión D7** (logo PMO-aaS; D1–D6 cerradas en DEC-036…039 y W5). No
  bloquea: mientras, la marca es texto.
- [ ] **Leer el registro del despliegue** de `0110`, `0111` y `0115`.
- [ ] **Cómo se traza un batch.** US-203–222 se mergearon sin issues: o se
  crean al cerrar el lote, o se escribe que el lote se traza por commit.

---

## 📥 INBOX

- [ ] **Batch 2026-09-19** — multi-organización y catálogos: #623-#641 en 7
  bloques (`drafts/plataforma-multiorg-y-catalogos.md`). Arranca el Bloque 0
  (#623, #624, #625). Falta la label `EP022` y marcar `status:ready`.
- [ ] **Glosario de datos** (FASE-9 pasada 2): #613-#619.
- [ ] **W3 — RLS de Postgres**: #599 (US-240), #600 (US-241), #601 (US-242).
- [ ] **EP021**: quedan US-223, US-225 y US-226. US-224 entregada.
- [ ] **US-239** — clave de proyecto estilo Jira en la URL (mig. 0120).
- [ ] **Hueco de compat**: `GET /projects` no normaliza `phase` (`core/compatibilidad.py`).
- [ ] **Pantalla del catálogo de IA** en `/admin/plan?tab=ia`: US-224 solo tiene API.

---

## 📦 Lo demás

Backlog, diferidos y DONE: [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md).
Historial narrativo: [`SPRINT-DONE-HISTORY.md`](SPRINT-DONE-HISTORY.md).
