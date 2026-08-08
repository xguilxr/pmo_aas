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
Sin US activa. Branch `claude/asvs-l1-quince-huecos-kgk2qz` — **PR #584 abierto,
CI verde**. Mergear es el próximo paso.

MCA: N2, su objetivo, 11/11. Nada pendiente.
MCS: N0 · **1 bloquea N1: `SEG-01`**, y sigue bloqueando pese a que sus quince
huecos ASVS están cerrados — queda PARCIAL por TRES residuales ACEPTADO, y
MCS-CORE §6.2 no da crédito parcial. Ver INBOX.
```

> **¿Próximo ID libre?** `python scripts/proximo_id.py`. Se deriva de GitHub +
> `git log` + docs; ya no se almacena aquí (MCA CTX-03). Corrélo contra
> `origin/main` actualizado.

---

## 📥 INBOX / TRIAGE

### 🌊 Conformidad — qué falta para N1

Plan activo en **`docs/conformidad/plan-remediacion.md`**. El estado se recalcula
con `python scripts/registro_conformidad.py` (no se almacena: CTX-03). Las olas
0-3 y el cierre de los quince huecos ASVS están archivados en
`SPRINT-DONE-HISTORY.md`.

- [ ] **`SEG-01` es el único bloqueante de N1, y cerrar los quince huecos NO lo
  desbloqueó.** Sigue PARCIAL por tres residuales ACEPTADO, y MCS-CORE §6.2 no
  da crédito parcial. Para llevarlo a CONFORME hay que **revertir una decisión
  tuya, no escribir código**:
  - `2.1.1` + `2.1.9` → contraseñas de 12 sin reglas de composición (revisa
    ADR-032).
  - `2.7.1` → TOTP ofrecido antes que el código por correo (revisa ADR-035).
  Con esos tres, `SEG-01` cierra y **MCS pasa a N1**. Sin ellos se queda en N0
  con un solo requisito en contra, que es una postura defendible pero hay que
  elegirla a sabiendas.
- [ ] **Ola 4 — de N1 a N2.** Se replanifica al alcanzar N1.

### Despliegue de #584 — lo que se nota

- [ ] **Se cierran todas las sesiones vivas** (ADR-033) y **entrar al panel pasa
  a ser dos pasos** (ADR-035). Ten acceso a tu correo antes de desplegar.
- [ ] **Migraciones 0105, 0106 y 0107.**
- [ ] **Si Resend se cae, ningún administrador entra.** Consecuencia de que el
  segundo factor viaje por correo; escrita en ADR-035.

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
> 2026-08-07 (los quince huecos ASVS, con lo que enseñó cerrarlos).

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
