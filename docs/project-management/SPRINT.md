---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-19
revisar_cada: 30d
---

# SPRINT.md — Tarea activa

> Este archivo se mira cada día. El epic se abre al tocarlo (`CLAUDE.md` §1).
> 1 US = 1 commit. Al terminar, mover la siguiente a IN-PROGRESS.
> Histórico: `SPRINT-DONE-HISTORY.md`. El techo de líneas lo hace cumplir el CI
> (`scripts/check_contexto.py`).

---

## 🔴 IN-PROGRESS

**Sin US activa.** Reestructura-W1 implementada y pusheada; el PR **#594**
espera tu verificación. Detalle en `SPRINT-DONE-HISTORY.md` (ronda 2026-08-19).

Próximo paso: verificar #594, cerrar #588–#592, desplegar `0105`–`0111`. Después,
**W2** según la «Guía de sesiones» de `drafts/reestructura-plan.md`.

> Próximo ID libre: `python scripts/proximo_id.py`, contra `origin/main`
> actualizado. Se deriva, no se almacena (MCA CTX-03).

---

## 📥 INBOX / TRIAGE

### Reestructura de plataforma — oleadas siguientes

Planeación en `docs/epics/drafts/reestructura-{conceptos,plan,inventario,modelo-datos}.md`
(mapas: `docs/architecture/mapa-{backend,frontend}.md`). W1 cerrada. Lo que
queda comprometido de las oleadas: **W3** RLS de Postgres, **W8** el `drop` de
`business_units` y `departments` cuando el contador de compat lo confirme.

### Producto — abierto

- [ ] **Desplegar `0105`–`0111`** (#584/#585 y #594). `0105`–`0107` cierran
  **todas las sesiones vivas** (ADR-033) y el panel pasa a dos pasos (ADR-035):
  ten acceso a tu correo, y si Resend se cae ningún administrador entra. De W1,
  mirar el registro del despliegue: `0110` lista los `projects.type` sin traducir
  y `0111` cuántos inquilinos tenían `org_label`.
- [ ] **Tapar un hueco antes de cerrar ventanas de compat.** `GET /projects`
  mete `phase` y `type` crudos en el `IN (...)` sin normalizar ni registrar: el
  contador no ve a quien filtra con el nombre viejo. Fichas y ventanas abiertas
  en `core/compatibilidad.py`.
- [ ] **Decidir los nueve follow-ups del PR #594**, listados ahí con su
  evidencia (superficie de API sin pantalla, permisos muertos, rutas sin enlace).
- [ ] **Contrastar los umbrales de D-4 contra cartera real.** Los valores de
  US-196 son razonados, no medidos; se ajustan en `settings`, sin tocar código.
- [ ] **`design-system/tokens.md`** describe una paleta anterior a D-7 y
  ADR-023. Marcado `reemplazado` el 2026-08-06; queda reescribirlo contra la
  paleta vigente (trabajo de diseño).
- [ ] **Línea base** (D-6), sin la cual «desviación» no tiene referente, y
  **DCMA 14-point**. Épica propia, sin abrir.

- 2026-08-07 — **Conformidad cerrada** (ADR-036); detalle en
  `docs/conformidad/asvs-l1.md`. Vuelve a la mesa solo con un cliente que exija
  certificación, un requisito contractual o un incidente de credenciales.

---

## 📦 Deferred, DONE y Backlog v2.0

Viven en [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md) — se abren al planear, no al
ejecutar. El historial narrativo sigue en `SPRINT-DONE-HISTORY.md`.
