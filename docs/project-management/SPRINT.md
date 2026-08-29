---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-28
revisar_cada: 30d
---

# SPRINT.md — lo activo

> Solo IN-PROGRESS, ESPERANDO e INBOX inmediato. Lo demás vive en
> [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md), en un issue o en
> [`SPRINT-DONE-HISTORY.md`](SPRINT-DONE-HISTORY.md). Techo: 60 líneas (CI).
> Estado derivado: `python scripts/estado.py` · IDs: `proximo_id.py`.

---

## 🔴 IN-PROGRESS

**Revamp v2 — el styling está, el diseño no** (owner, 2026-08-28):

- [ ] QA de vista web — el owner levanta la lista → BUG-093+
- [ ] Mobile, sin revisar ninguna pantalla
- [ ] Diseño de dashboards · [ ] Diseño de reportes

Los dos diseños bloquean el bloque G del plan post-revamp: un renderer
determinista necesita el diseño antes que el código.

---

## ⏳ ESPERANDO al owner

- [ ] **Cerrar #588–#592** (US-198–202): mergeadas desde el 2026-08-19 con
  `status:ready` intacta. Claude nunca cierra un issue (§3).
- [ ] **Leer el registro del despliegue** de `0110` (tipos sin traducir), `0111`
  (inquilinos con `org_label`) y `0115` (membresías sembradas). Las migraciones
  ya corrieron —el `CMD` del contenedor `api` las aplica al arrancar—; lo que
  falta es mirar lo que dejaron escrito.
- [ ] **Cómo se traza un batch.** US-203–222 se mergearon sin issues: o se crean
  al cerrar el lote, o se escribe que el lote se traza por commit y
  `SPRINT-DONE-HISTORY.md` es su registro de aceptación.

---

## 📥 INBOX

- [ ] **W3 — RLS de Postgres**: #599 (US-240), #600 (US-241), #601 (US-242).
- [ ] **EP021**: quedan US-223, US-225 y US-226. US-224 entregada.
- [ ] **US-239** — clave de proyecto estilo Jira en la URL (mig. 0120).
- [ ] **Hueco de compat**: `GET /projects` no normaliza `phase`/`type`, así que
  el contador no ve a quien filtra con el nombre viejo. Taparlo antes de cerrar
  las ventanas. Ver `core/compatibilidad.py`.
- [ ] **Pantalla del catálogo de IA** en `/admin/ai` — US-224 solo tiene API.

---

## 📦 Lo demás

Backlog, diferidos y DONE: [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md).
Historial narrativo: [`SPRINT-DONE-HISTORY.md`](SPRINT-DONE-HISTORY.md).
