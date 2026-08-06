---
tipo: runbook
responsable: propietario
estado: vigente
revisado: 2026-05-08
revisar_cada: 180d
---

# CI gate: alembic upgrade head contra Postgres efímero

**ID:** `RUN-CI-002`
**Estado:** Vigente — 2026-04-29
**Relacionado:** ENH-044 (#185), BUG-039 (#184), [ENH-035 (#158)](../README.md)

---

## Qué hace

El job `api-migrations-postgres` en `.github/workflows/ci.yml` levanta
un container `postgres:15-alpine` efímero y corre la secuencia:

1. `alembic upgrade head` desde DB vacía → debe completar.
2. `alembic downgrade base` → debe completar (smoke de reversibilidad).
3. `alembic upgrade head` re-aplicado → debe completar.

Si cualquiera de los 3 pasos falla, el job falla y bloquea el merge.

## Por qué existe

BUG-039 (#184) reveló un gap: la migración `20260425_0031` usaba
`server_default=sa.text("1")` sobre columna BOOLEAN. SQLite (motor de
la suite de tests) acepta `1` como booleano, **Postgres lo rechaza**
con `DatatypeMismatch`. El merge a `main` pasó CI verde, el deploy
a Railway crasheó en `alembic upgrade head`, y el API quedó caído ~3
días.

Este patrón (SQLite-pasa-Postgres-falla) puede repetirse con
`sa.text("0/1")`, JSONB vs TEXT, `gen_random_uuid()`, secuencias,
exclusion constraints, etc. Este gate los caza antes del merge.

## Costo

~30-45s por PR que toque `apps/api/**`. PRs solo-frontend lo saltan
gracias al filter `dorny/paths-filter@v3` (`needs.changes.outputs.api == 'true'`).

Cazar 1 BUG-039-like al año ya paga la inversión.

## Cómo debuggear si el job falla

### Caso 1: la migración nueva crashea en upgrade head

Síntoma: `upgrade head` falla con `DatatypeMismatch`, `UndefinedFunction`,
`DuplicateColumn`, etc.

Acciones:
1. Lee el traceback. Identifica la migración (revision id) que está
   ejecutándose cuando falla.
2. Revisa `apps/api/alembic/versions/<revision>.py`:
   - `server_default=sa.text("0|1")` sobre BOOLEAN → cambiar a
     `sa.text("false|true")` o `sa.text("'false'|'true'")`.
   - `op.add_column(..., nullable=False)` sin default sobre tabla con
     datos → agregar `server_default` para el backfill.
   - `op.alter_column(..., type_=...)` que no se traduce limpio en
     Postgres → usar `op.execute("ALTER TABLE ... USING ...::nuevotipo")`.
3. Reproduce localmente:
   ```bash
   docker run -d --name pg15 -p 5432:5432 \
     -e POSTGRES_USER=pmo -e POSTGRES_PASSWORD=pmo -e POSTGRES_DB=pmo_test \
     postgres:15-alpine
   cd apps/api
   DATABASE_URL=postgresql+psycopg://pmo:pmo@localhost:5432/pmo_test \
     alembic upgrade head
   ```

### Caso 2: downgrade base crashea

Síntoma: `upgrade head` pasa pero `downgrade base` rompe.

Causa probable: `op.drop_column` en una columna que tiene FK que no
fue droppeada antes; o `op.drop_table` sobre una tabla con
dependencias circulares.

Acciones:
1. Verifica que la migración tenga `downgrade()` definido y simétrico
   al upgrade.
2. Si es legacy y nunca se usó downgrade en prod, considera marcar
   la migración como `downgrade = lambda: pass` con comentario
   explicando, **pero esto rompe la idempotencia**: hablarlo con el
   owner antes.

### Caso 3: upgrade head re-aplicado crashea

Síntoma: 1ra `upgrade head` y `downgrade base` pasan, pero la 2da
`upgrade head` falla.

Causa probable: el downgrade no fue completo (quedó algo en DB
después del downgrade). Síntoma típico: "extension/index/sequence
already exists".

Acciones:
1. Revisa la migración nueva: ¿el upgrade crea algo (extensión,
   sequence, type) que el downgrade no borra?
2. Agrega los `op.drop_*` correspondientes en el downgrade.

### Caso 4: el container Postgres no levanta

Síntoma: el job falla en setup con timeout esperando `pg_isready`.

Acciones:
1. Reintenta el workflow. Es raro pero ocurre con runners
   sobrecargados.
2. Si persiste: revisar si la versión de Postgres en el workflow
   (`postgres:15-alpine`) cambió de comportamiento. Pinear a tag
   específico (ej. `postgres:15.6-alpine`).

## Convivencia con ENH-035 (#158)

ENH-035 propone un análisis amplio para evaluar si Postgres reemplaza
SQLite en la **suite completa de tests** (post-MVP/v2.0). Este gate
es **complementario**: aunque ENH-035 termine con la decisión "no
migrar la suite", este job sigue siendo útil como sanity check
dedicado solo a migrations.

Si ENH-035 decide migrar la suite a Postgres, este gate puede
absorberse en el job de tests (los tests ya correrían contra
Postgres). Hasta entonces, este gate es independiente.

## Mantenimiento

- Si la versión de Postgres en Railway prod cambia, alinear
  `postgres:15-alpine` en el workflow.
- Si una migración legacy se descubre con bug latente que SQLite
  enmascara, el gate fallará al primer run después de modificar
  cualquier archivo en `apps/api/**`. Decisión:
  - Fixear la migración legacy in-place (preferido).
  - Si el cambio es muy invasivo, marcar como `legacy fix-on-touch`
    con DEC en `docs/decisions/` antes de mergear.

## Referencias

- BUG-039 (#184) — incidente que motivó el gate.
- ENH-044 (#185) — issue de implementación.
- ENH-035 (#158) — análisis amplio post-MVP.
