---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-28
revisar_cada: 30d
---

# SPRINT.md — Tarea activa

> Se mira cada día. El epic se abre al tocarlo (`CLAUDE.md` §1). 1 US = 1 commit.
> Histórico: `SPRINT-DONE-HISTORY.md`. El techo lo hace cumplir el CI.

---

## 🔴 IN-PROGRESS

**Revamp v2 — el styling está, el diseño no** (owner, 2026-08-28). Sigue
abierto: QA de vista web (el owner levanta la lista → BUG-093+), **mobile sin
revisar**, y los **diseños de dashboards y de reportes**, que faltan. Los dos
últimos bloquean el bloque G del plan post-revamp: un renderer determinista
necesita el diseño antes que el código.

**Fase 2 mergeada** (PR #595, US-203–US-222). Falta **desplegar `0105`–`0115`**
leyendo el registro (abajo). EP021: **US-224 entregada**; quedan US-223, US-225
y US-226. **US-243 entregada**: el conocimiento se busca por sección y el
estado se deriva (`CLAUDE.md` §1).

> Próximo ID libre: `python scripts/proximo_id.py`, contra `origin/main`
> actualizado. Se deriva, no se almacena (MCA CTX-03).

---

## 📥 INBOX / TRIAGE

### Reestructura de plataforma — lo que queda

W1 y Fase 2 cerradas. Queda **W3** RLS de Postgres (#599–#601) y **W8** el
`drop` de `business_units`/`departments` cuando el contador de compat lo
confirme. Planeación en `docs/epics/drafts/reestructura-*.md`.

### Producto — abierto

- [ ] **US-239** — clave de proyecto estilo Jira en la URL (mig. 0120).
- [ ] **Cerrar #588–#592** (US-198–202): mergeadas desde el 2026-08-19 con
  `status:ready` intacta. Las cierra el owner al verificar (§3).
- [ ] **Decidir cómo se traza un batch.** US-203–222 se mergearon sin issues:
  o se crean al cerrar el lote, o se escribe que el lote se traza por commit y
  `SPRINT-DONE-HISTORY.md` es su registro. Hoy no está escrito ninguna.

- [ ] **Desplegar `0105`–`0115`.** `0105`–`0107` cierran **todas las sesiones
  vivas** (ADR-033) y el panel pasa a dos pasos (ADR-035): ten acceso a tu
  correo. Registro a mirar: `0110` los `projects.type` sin traducir, `0111` los
  inquilinos con `org_label`, `0115` cuántas membresías sembró.
- [ ] **Hueco antes de cerrar ventanas de compat.** `GET /projects` mete `phase`
  y `type` crudos en el `IN (...)` sin normalizar ni registrar: el contador no ve
  a quien filtra con el nombre viejo. Ver `core/compatibilidad.py`.
- [ ] **Los nueve follow-ups del PR #594**, listados ahí con su evidencia.
- [ ] **Umbrales de D-4 contra cartera real** (US-196: razonados, no medidos).
- [ ] **`design-system/tokens.md`**: paleta previa a D-7/ADR-023, marcado
  `reemplazado`. Reescribirlo es trabajo de diseño.
- [ ] **DCMA 14-point.** La línea base que lo bloqueaba ya está (US-212).

---

## 📦 Deferred, DONE y Backlog v2.0

Viven en [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md) — se abren al planear, no al
ejecutar. El historial narrativo sigue en `SPRINT-DONE-HISTORY.md`.
