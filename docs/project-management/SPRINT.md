---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 30d
---

# SPRINT.md — Tarea activa

> Este archivo se mira cada día. El epic se abre al tocarlo (`CLAUDE.md` §1).
> 1 US = 1 commit. Al terminar, mover la siguiente a IN-PROGRESS.
> Histórico: `SPRINT-DONE-HISTORY.md`. El techo de líneas lo hace cumplir el CI
> (`scripts/check_contexto.py`).

---

## 🔴 IN-PROGRESS

Sin US activa. Branch de la sesión: `claude/docs-context-debloat-1j4o3b`
(debloat documental, batch aprobado por el owner). Al terminar: producto.

> Próximo ID libre: `python scripts/proximo_id.py`, contra `origin/main`
> actualizado. Se deriva, no se almacena (MCA CTX-03).

---

## 📥 INBOX / TRIAGE

### Reestructura de plataforma — Bloque Reestructura-W1 (propuesto)

Planeación en `docs/epics/drafts/reestructura-{conceptos,plan,inventario,modelo-datos}.md`.
BU/Departamentos se reemplazan por Portafolio ⊃ Programa (owner 2026-08-19,
sin datos productivos que mapear). `status:ready` y **wireframes aprobados**
por el owner (2026-08-19) — la construcción arranca en sesiones nuevas con
la «Guía de sesiones» de `reestructura-plan.md` (mapas:
`docs/architecture/mapa-{backend,frontend}.md`). Orden: US-198 primero.

- [ ] US-198 #588 — Modelo y migración: entidad Portfolio + re-parenting de Programs
- [ ] US-199 #589 — API: CRUD de portafolios + retiro de BU/deptos (dep: US-198)
- [ ] US-200 #590 — UI admin: jerarquía Portafolio ⊃ Programa (dep: US-199)
- [ ] US-201 #591 — Filtros portafolio/programa en dashboard y cross (dep: US-199)
- [ ] US-202 #592 — Enum de tipo + vocabulario de fases nuevo (dep: US-198)

- 2026-08-07 — **Conformidad cerrada** (ADR-036); detalle en
  `docs/conformidad/asvs-l1.md`. Vuelve a la mesa solo con un cliente que exija
  certificación, un requisito contractual o un incidente de credenciales.

### Producto — abierto

- [ ] **Desplegar lo mergeado (#584/#585).** Migraciones `0105`, `0106` y
  `0107`. Al desplegar se cierran **todas las sesiones vivas** (ADR-033) y
  entrar al panel pasa a ser dos pasos (ADR-035) — ten acceso a tu correo. Si
  Resend se cae, ningún administrador entra.
- [ ] **Cerrar las ventanas de compatibilidad** cuando el contador lo permita.
  Se cuentan por `compat.nombre_viejo`; fichas en `core/compatibilidad.py`.
  Abiertas: `phase=support`, `portfolio_function`, `wbs`, `amber_max` y
  `cookie:refresh_token` — esta última se cierra sola al caducar las cookies
  anteriores a ADR-033.
- [ ] **Contrastar los umbrales de D-4 contra cartera real.** Los valores de
  US-196 son razonados, no medidos; se ajustan en `settings`, sin tocar código.
- [ ] **`design-system/tokens.md`** describe una paleta anterior a D-7 y
  ADR-023. Marcado `reemplazado` el 2026-08-06; queda reescribirlo contra la
  paleta vigente (trabajo de diseño).
- [ ] **Línea base** (D-6), sin la cual «desviación» no tiene referente, y
  **DCMA 14-point**. Épica propia, sin abrir.

---

## 📦 Deferred, DONE y Backlog v2.0

Viven en [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md) — se abren al planear, no al
ejecutar. El historial narrativo sigue en `SPRINT-DONE-HISTORY.md`.
