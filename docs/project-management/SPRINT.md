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
MCS: N0 · **29 bloquean N1** (eran 41) · runbook de cierre en docs/conformidad/ · una sola exclusión viva (ARQ-03).
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

- [x] **Olas 0, 1 y 2 — 2026-08-05/06.** De 45 a 32 bloqueantes. Las dos
  primeras sin escribir producto (el registro no se había enterado de cuatro
  cierres) y `main` protegida; la tercera, once commits con prueba y
  verificación por mutación. `DAT-05` **volvió a cerrar**: estaba CONFORME
  sobre una lista escrita a mano y quedaba una quinta paleta, en el acta que se
  firma. `DAT-02`, `DIS-03` y `DAT-11` se reclasificaron ahí —no eran
  mecánicos— y hoy están medidos.
- [x] **Ola 3 — cerrada el 2026-08-07.** De 32 bloqueantes de N1 a **1**; 31
  cierres con prueba y verificación por mutación. Detalle en el registro.
- [x] **Los quince huecos ASVS — doce cerrados el 2026-08-07**, uno por commit,
  con prueba y verificación por mutación. El tope de `check_asvs.py` baja de 15
  a 3. **`SEG-01` sigue PARCIAL**: quedan `4.3.1` (segundo factor de
  administración), `8.3.2` (exportar/suprimir) y `8.3.3` (consentimiento), y los
  tres son producto por construir con una decisión del owner delante. Detalle y
  cuál es cada decisión, en `docs/conformidad/asvs-l1.md`.
- [ ] **Al desplegar, ADR-033 cierra todas las sesiones vivas.** Coste de una
  vez, inevitable.
- [ ] **Ola 4 — de N1 a N2.** Se replanifica al alcanzar N1.

### Producto — abierto

- [x] **BUG-092 — hecho el 2026-08-07.** La moneda va sobre el **proyecto**,
  con una preferida por inquilino como valor inicial (decisión del owner). Los
  agregados de cartera **no suman monedas distintas**: devuelven un importe por
  moneda. Migración 0104; trinquete `check_moneda.py`.

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
