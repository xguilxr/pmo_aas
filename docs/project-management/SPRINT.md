---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-19
revisar_cada: 30d
---

# SPRINT.md — Tarea activa

> Se mira cada día. El epic se abre al tocarlo (`CLAUDE.md` §1). 1 US = 1 commit.
> Histórico: `SPRINT-DONE-HISTORY.md`. El techo lo hace cumplir el CI.

---

## 🔴 IN-PROGRESS

**Sin US activa.** **Revamp v2 terminado** (2026-08-27, batch del owner;
detalle en `SPRINT-DONE-HISTORY.md`). Lo pendiente:
`docs/epics/drafts/plan-post-revamp.md` (US desde 227).

**Fase 2 mergeada** (PR #595, US-203–US-222, mig. `0112`–`0115`). Falta
**desplegar `0105`–`0115`** leyendo el registro (abajo). EP021: las cuatro
preguntas contestadas (DEC-033) — desbloquea **US-223 a US-226**.

> Próximo ID libre: `python scripts/proximo_id.py`, contra `origin/main`
> actualizado. Se deriva, no se almacena (MCA CTX-03).

---

## 📥 INBOX / TRIAGE

### Reestructura de plataforma — lo que queda

Planeación en `docs/epics/drafts/reestructura-*.md`; mapas en
`docs/architecture/mapa-{backend,frontend}.md`. W1 y Fase 2 cerradas. Queda **W3**
RLS de Postgres y **W8** el `drop` de `business_units`/`departments` cuando el
contador de compat lo confirme.

### Producto — abierto

- [ ] **Desplegar `0105`–`0115`** (#584/#585, #594 y Fase 2). `0105`–`0107`
  cierran **todas las sesiones vivas** (ADR-033) y el panel pasa a dos pasos
  (ADR-035): ten acceso a tu correo. Mirar el registro: `0110` lista los
  `projects.type` sin traducir, `0111` los inquilinos con `org_label` y `0115`
  cuántas membresías sembró.
- [ ] **Hueco antes de cerrar ventanas de compat.** `GET /projects` mete `phase`
  y `type` crudos en el `IN (...)` sin normalizar ni registrar: el contador no ve
  a quien filtra con el nombre viejo. Ver `core/compatibilidad.py`.
- [ ] **Decidir los nueve follow-ups del PR #594**, listados ahí con su evidencia.
- [ ] **Contrastar los umbrales de D-4 contra cartera real.** Los de US-196 son
  razonados, no medidos; se ajustan en `settings`.
- [ ] **`design-system/tokens.md`** describe una paleta previa a D-7 y ADR-023.
  Marcado `reemplazado`; reescribirlo es trabajo de diseño.
- [ ] **Las cuatro preguntas de `EP021-catalogo-de-ia.md`.** Son definiciones, no
  aprobaciones; la cuarta decide si hay un segundo sistema de autorización.
- [ ] **DCMA 14-point.** La línea base que lo bloqueaba ya está (US-212).

- 2026-08-07 — **Conformidad cerrada** (ADR-036): `docs/conformidad/asvs-l1.md`.
  Vuelve solo con un requisito contractual o un incidente.

---

## 📦 Deferred, DONE y Backlog v2.0

Viven en [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md) — se abren al planear, no al
ejecutar. El historial narrativo sigue en `SPRINT-DONE-HISTORY.md`.
