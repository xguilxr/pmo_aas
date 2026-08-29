---
name: handoff
description: Reescribe HANDOFF.md con lo que no se puede derivar y deja SPRINT.md solo con lo activo, archivando el resto. Úsala al cerrar la sesión.
---

# /handoff — cierre de sesión

## La regla que manda todo lo demás

**`HANDOFF.md` lleva solo lo que no se puede derivar.** Todo lo que git,
GitHub, `SPRINT.md` o un epic ya saben se **referencia**, no se copia.

Un handoff que repite lo derivable no es más completo: es más frágil. Lo copiado
envejece —el 2026-08-19 este documento declaraba el PR #594 abierto y esperando
verificación, y siguió diciéndolo después de que #594, #595 y #598 se mergearan—
y la sesión siguiente arranca decidiendo sobre una premisa falsa, sin nada que la
contradiga porque el sello dice «vigente».

| Se deriva → se referencia | Con qué |
|---|---|
| Rama, commits, migraciones, frescura | `python scripts/estado.py` |
| PRs y su CI | GitHub |
| Issues y su estado | GitHub |
| Qué se hizo, en detalle | `git log` · `SPRINT-DONE-HISTORY.md` |
| Qué sigue | INBOX de `SPRINT.md` |
| Si una epic está al día | La epic misma — se actualiza en el mismo bloque (§0.2) |

Queda **lo que solo vive en la cabeza de quien cerró la sesión**: qué se estaba
intentando, dónde retomar, y qué va a morder a la siguiente sesión.

---

## Paso 1 — Reúne lo derivado

```bash
python scripts/estado.py
git log --oneline origin/main..HEAD
```

Y el estado de los PR que tocó la sesión (`mcp__github__list_pull_requests`).
Esto **no se copia al documento**: se usa para escribir los cuatro apartados del
paso 3 y para detectar lo que falta.

## Paso 2 — Deja `SPRINT.md` solo con lo activo

`SPRINT.md` se mira cada día, así que solo lleva lo que se mira cada día:

```
🔴 IN-PROGRESS   La US/bloque en curso, o «Sin US activa» + el siguiente paso.
⏳ ESPERANDO     Lo bloqueado por el owner o por un tercero, con quién lo destraba.
📥 INBOX         Lo próximo que se va a ejecutar. Con issue, un enlace basta.
📦 puntero       → SPRINT-BACKLOG.md
```

**Un item sale de `SPRINT.md`** en cuanto deja de ser una de esas tres cosas:

- terminado → `SPRINT-DONE-HISTORY.md` (el detalle narrativo)
- sin fecha ni dueño → `SPRINT-BACKLOG.md`
- con issue y sin trabajo esta semana → solo el issue; el INBOX no lo repite

Si un item lleva tres cierres de sesión sin moverse, **no está activo**: va al
backlog. Un INBOX que acumula es un backlog disfrazado, y se deja de leer.

Techo: **60 líneas**. El CI acota el total (`check_contexto.py`), pero el techo
real es que quepa en una pantalla — si no cabe, nadie distingue lo urgente.

## Paso 3 — Reescribe `HANDOFF.md`

Cuatro apartados, **1 500 caracteres o menos**. Si algo no aplica, se omite el
apartado entero; un apartado vacío enseña a saltárselos todos.

```markdown
---
tipo: gestion
responsable: propietario
estado: vigente
revisado: AAAA-MM-DD
revisar_cada: 30d
---

# HANDOFF.md — puente a la próxima sesión

**AAAA-MM-DD** · rama `claude/...` · lo derivado: `python scripts/estado.py`

## Qué se estaba haciendo, y por qué

<2-4 oraciones. La intención, no la lista de commits. Por qué se eligió este
camino y qué se descartó. Es lo único de este archivo que no está en ningún
otro sitio.>

## Dónde retomar

<Una acción concreta. «Verificar #XXX y mergear», «arrancar US-YYY sobre rama
nueva». Si hay un blocker, aquí va y se dice quién lo destraba.>

## Qué va a morder

<Solo lo que sorprendería a alguien que lee el código y los docs. Un gotcha que
ya esté escrito en una epic, un ADR o LESSONS.md **no va aquí**: va su
referencia. Si no hay ninguno, se omite el apartado.>

## Decisiones del owner de esta sesión

<Solo las que se tomaron hablando y todavía no están en DECISIONS.md, un ADR o
una epic. Si ya se escribieron ahí, esto se omite: el sitio correcto es aquel.>
```

**Lo que ya no lleva**, y a dónde se fue: la tabla de PR (GitHub), la lista de
commits (`git log`), el resumen del backlog (INBOX), la tabla de epics
sincronizadas (§0.2 obliga a actualizarlas en el mismo bloque, así que una tabla
que lo repita solo puede mentir), el cleanup pendiente del owner (issues o
INBOX), y las ideas sueltas (`SPRINT-BACKLOG.md`).

## Paso 4 — Antes de cerrar, comprueba §0.2

Repasa los commits de la sesión: ¿alguno cambió comportamiento, esquema o
endpoints que una epic describe? Si sí, **la epic se actualiza ahora**, no se
anota como pendiente en el handoff. Redáctalo con un sub-agente Haiku (skill
`delegar`). Un cambio interno —refactor, typo— no actualiza nada.

## Paso 5 — Commit + push

```
docs(handoff): AAAA-MM-DD — <una línea>
```

Push a la rama activa. **Nunca** a `main`, y **nunca** abriendo un PR.

## Paso 6 — Resumen al owner

Skill `resumen-ronda`. Añade: cuánto encogió `SPRINT.md` y qué se archivó.

---

## Reglas duras

- **No inventes.** Si no estás seguro de qué se hizo, míralo en `git log` o
  pregunta. Un handoff con un dato inventado es peor que uno corto.
- **No copies lo derivable.** Ante la duda de si un apartado va: si un comando o
  un enlace lo responde, no va.
- **Sesión sin commits.** Igual se escribe: qué se discutió y qué se decidió.
  Es cuando el handoff más vale, porque no hay `git log` que lo cuente.
- **Un handoff que crece es una señal**, no un logro. Si no baja de 1 500
  caracteres, casi siempre es que algo debía ser un issue.
