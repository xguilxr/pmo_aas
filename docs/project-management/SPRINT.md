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
Sin US activa. **Vuelta al producto.**

CONFORMIDAD — cerrada. El programa de remediación terminó el 2026-08-07
(ADR-036): quince huecos ASVS cerrados, tres residuales aceptados, N1 no se
persigue. No hay nada que retomar aquí; lo que queda vivo son los trinquetes
del CI, que siguen bloqueando solos.

MCA: N2, su objetivo. MCS: N0 con un requisito en contra, a sabiendas.
```

> **¿Próximo ID libre?** `python scripts/proximo_id.py`. Se deriva de GitHub +
> `git log` + docs; ya no se almacena aquí (MCA CTX-03). Corrélo contra
> `origin/main` actualizado.

---

## 📥 INBOX / TRIAGE

### Conformidad — cerrada, no pendiente

Nada que hacer. El detalle vive en `docs/conformidad/asvs-l1.md` y la decisión
en **ADR-036**. `python scripts/registro_conformidad.py` seguirá diciendo
`BLOQUEAN N1: 1 ['SEG-01']` — es correcto: el derivador mide, no opina sobre si
el nivel se persigue.

Vuelve a la mesa solo si aparece un cliente que exija certificación, si entra un
requisito contractual, o ante el primer incidente de credenciales.

### Producto — abierto

- [ ] **Desplegar lo mergeado (#584/#585).** Migraciones `0105`, `0106` y
  `0107`. Al desplegar se cierran **todas las sesiones vivas** (ADR-033) y
  entrar al panel pasa a ser dos pasos (ADR-035) — ten acceso a tu correo. Si
  Resend se cae, ningún administrador entra.
- [ ] **Cerrar las ventanas de compatibilidad** cuando el contador lo permita.
  Se cuentan por `compat.nombre_viejo`; fichas en `core/compatibilidad.py`.
  **Cuatro abiertas:** `phase=support`, `portfolio_function`, `wbs` y
  `amber_max`, más `cookie:refresh_token` — esta última se cierra sola al
  caducar las cookies anteriores a ADR-033.
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
