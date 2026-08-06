---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 30d
---

# SPRINT.md — Tarea activa

> **Regla:** este archivo es lo que se mira cada día. El epic se abre al tocarlo
> (`CLAUDE.md` §1). 1 US = 1 commit. Al terminar, mover la siguiente a IN-PROGRESS.
>
> **Histórico:** todo lo cerrado vive en `SPRINT-DONE-HISTORY.md`.
>
> **Límite:** este archivo no pasa de 250 líneas. Lo hace cumplir el CI
> (`scripts/check_contexto.py`); se carga en toda sesión y se paga en cada turno.

---

## 🔴 IN-PROGRESS

```
Sin US activa. Branch `claude/remediacion-ola-2-2kg36x` — el owner abre el PR.

REMEDIACIÓN POR OLAS — plan en `docs/conformidad/plan-remediacion.md`.
Olas 0, 1 y **2 cerradas**, más `SEG-04` y `DAT-06` de la Ola 3.
Lo que queda de Ola 3 necesita postura del owner — otra sesión.

MCA: N2, su objetivo, 11/11. Nada pendiente.
MCS: N0 · **30 bloquean N1** (eran 41) · una sola exclusión viva (ARQ-03).
```

> **¿Próximo ID libre?** `python scripts/proximo_id.py`. Se deriva de GitHub +
> `git log` + docs; ya no se almacena aquí (MCA CTX-03). Corrélo contra
> `origin/main` actualizado.

---

## 📥 INBOX / TRIAGE

### 🌊 Las olas — orden de ejecución

El plan completo, con el registro de los 97 abiertos y la evidencia por
requisito, está en **`docs/conformidad/plan-remediacion.md`**. El estado se
recalcula con `python scripts/registro_conformidad.py` (no se almacena: CTX-03).

- [x] **Olas 0 y 1 — hechas el 2026-08-05.** De 45 a 41 sin escribir producto
  (el registro no se había enterado de cuatro cierres), y `main` protegida.
  Detalle en `plan-remediacion.md` y en los informes fechados.
- [x] **Ola 2 — hecha el 2026-08-06.** De **41 a 32** bloqueantes, once commits
  con prueba y verificación por mutación. Cierran `SEG-05`, `OPS-01`, `DEV-04`,
  `CFG-04`, `DIS-01`+`CFG-14`, `DOC-01`, `DOC-03`, `DAT-04`+`DAT-08`, `DAT-12`,
  y `DAT-05` **vuelve a cerrar** — estaba CONFORME sobre una lista escrita a
  mano y quedaba una quinta paleta, en el acta que se firma. `DAT-06` cerró
  entero el mismo día (ver Ola 3); sigue PARCIAL `LEN-02` (177→**166**, con el
  mecanismo ya puesto). **`DAT-02`, `DIS-03` y `DAT-11` se reclasifican**: no
  son mecánicos, y ahora están medidos. Detalle en `plan-remediacion.md`.
- [ ] **Ola 3 — necesita postura del owner.** Alcance de competencia
  (`CON-01/03/05`), escenarios de calidad con medida (`REQ-02`), inventario de
  datos personales (`REQ-03`), fichas de indicador (`DAT-01/10`), almacén de
  secretos (`SEG-02`), estrategia de pruebas (`DEV-02/03` — hoy **cero** en
  frontend), artefacto de canalización (`SUM-01`), entornos y copias
  (`INF-02/03`, `DES-02`). Se le suman de la Ola 2: `DAT-02` (renombres con
  migración), `DIS-03` y `DAT-11` (épica de producto).
  **Hechos ya:** `SEG-04` —la única CRÍTICA, autorización sobre el objeto— y
  `DAT-06` (`amber_max` → `yellow_max`, ADR-030 y migración 0101).
- [ ] **Ola 4 — de N1 a N2.** Se replanifica al alcanzar N1.

### Producto — abierto

- [ ] **Cerrar las ventanas de compatibilidad** cuando el contador lo permita.
  Se cuentan por `compat.nombre_viejo`; fichas en `core/compatibilidad.py`.
  **Cuatro abiertas:** `phase=support`, `portfolio_function`, `wbs` y
  `amber_max` (esta desde el 2026-08-06; se mira el contador a los dos meses).
- [ ] **Contrastar los umbrales de D-4 contra cartera real.** Los valores de
  US-196 son razonados, no medidos; se ajustan en `settings`, sin tocar código.
- [ ] **`design-system/tokens.md`** describe una paleta anterior a D-7 y
  ADR-023. Marcado `reemplazado` con aviso en el cuerpo el 2026-08-06; queda
  reescribirlo contra la paleta vigente, que es trabajo de diseño.
- [ ] **Línea base** (D-6), sin la cual «desviación» no tiene referente, y
  **DCMA 14-point**. Épica propia, sin abrir.

> **El glosario no tiene ninguna decisión abierta.** Las nueve ejecutadas
> (`docs/dominio/03-REVISION-GLOSARIO.md`). El modelo de amenazas tampoco tiene
> ninguna sin control.

---

## 📦 Deferred, DONE y Backlog v2.0

Viven en [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md) — se abren al planear, no al
ejecutar. El historial narrativo sigue en `SPRINT-DONE-HISTORY.md`.

---

## Notas y cambios recientes

> Histórico narrativo en `SPRINT-DONE-HISTORY.md`, incluida la ronda del
> 2026-08-06 (Ola 2 + `SEG-04` + la verificación local por la caída de Actions).

---

## Instrucción para Claude Code

El procedimiento **no vive aquí**: se duplicaba palabra por palabra con
`CLAUDE.md`, y dos copias de una regla son una regla que se contradice sola.

- Qué se carga y en qué orden → `CLAUDE.md` §1
- Ciclo de trabajo, labels y comment de cierre → §3 y skills `triage` /
  `cerrar-item`
- Cómo se comprueba que algo funciona → skill `verificar`
- **1 US = 1 commit** → §7 · Branch y sesiones secuenciales → §8
- Resumen de ronda → §11 · Cierre de sesión → `/handoff` (§12)
