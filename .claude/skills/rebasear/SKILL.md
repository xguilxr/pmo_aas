---
name: rebasear
description: Poner al día una branch que quedó atrás respecto a main — fetch, rebase, resolución de conflictos y push con --force-with-lease—, incluidas las colisiones de revisiones de Alembic al mergear lanes en paralelo. Úsala cuando el CI de un PR falle por cambios que main tiene y la branch no, o cuando el merge aparezca bloqueado por conflicto. NO la uses para crear la branch ni para el cierre de un item (eso es cerrar-item).
---

# Rebasear una branch que quedó atrás

Sale de `CLAUDE.md` §8, donde ocupaba contexto permanente para usarse una vez al
mes (MCA CAP-01). El procedimiento no cambió.

## Cuándo

El CI del PR falla y el motivo no es tu cambio: `main` avanzó y trajo algo que tu
branch no tiene. Lo típico son migraciones nuevas.

## Los cuatro pasos

```bash
git fetch origin main
git rebase origin/main          # sobre la branch local
# resolver conflictos si los hay
git push --force-with-lease origin <branch>
```

**Siempre `--force-with-lease`, nunca `--force` a secas.** El flag comprueba que
el remoto sigue donde vos creías: si el owner tocó la branch mientras tanto, el
push falla en vez de pisarle el trabajo. `git push --force` a secas está
**bloqueado** por `scripts/guard_irreversible.py`, así que ni siquiera es una
opción disponible.

## Colisiones de revisiones de Alembic

Es el caso que más se repite: dos lanes en paralelo crean migraciones y las dos
declaran el mismo `down_revision`, así que al mergear la segunda el árbol de
revisiones queda con dos cabezas.

Después del rebase, revisá el `down_revision` de **tu** migración: tiene que
apuntar a la última revisión de `main`, no a la que era la última cuando
empezaste. Se corrige a mano en el archivo de la migración y se vuelve a
commitear.

Comprobación, con Postgres levantado:

```bash
cd apps/api && alembic upgrade head && alembic downgrade base && alembic upgrade head
```

Ese ida y vuelta lo corre el owner: las migraciones están denegadas para Claude
(`CLAUDE.md` §0.3). En el CI lo cubre el job `api-migrations-postgres`.

## Lo que no se hace

- **No** `git push --force` sin lease.
- **No** rebasear una branch que otra persona esté usando sin avisarle.
- **No** rebasear `main`.

La forma de no llegar acá es la de `CLAUDE.md` §8: una sesión, un lane, una
branch, y migraciones consecutivas.
