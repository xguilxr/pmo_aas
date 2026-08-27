"""US-241 / ADR-003 — RLS en el dominio jerarquía.

Segundo paso de la oleada **W3** (el primero fue `20260827_0116`, los FKs de
`tenant_id`). Activa `ROW LEVEL SECURITY` en las seis tablas del dominio
jerarquía — `organizations`, `portfolios`, `business_units`, `departments`,
`programs`, `projects` — con una policy que confía en
`current_setting('app.tenant_id', true)`, fijado por `app/core/tenant_
context.py::fijar_tenant_actual` en cada sesión de la API y del worker.

## La policy y el centinela

```sql
USING (tenant_id = current_setting('app.tenant_id', true)
       OR current_setting('app.tenant_id', true) = '*')
```

El `'*'` es el centinela de plataforma (ADR-003, revisión 2026-08-27, decisión
del owner). Un único call site del código puede escribirlo
(`api/deps.py::get_superadmin`); `tests/test_us241_rls_trinquete.py` lo
comprueba con un grep literal. `WITH CHECK` repite la misma condición: sin
eso, un `INSERT`/`UPDATE` con `tenant_id` de otro tenant pasaría la policy de
lectura y quedaría escrito igual — `USING` sola solo protege lecturas.

`FOR ALL` en vez de policies separadas por comando: las seis tablas no tienen
hoy un caso de "puede leer pero no escribir cruzando tenant" que amerite
diferenciar, y una policy por tabla es más fácil de auditar que cuatro.

## `FORCE ROW LEVEL SECURITY` — y su límite

Postgres exime por default al **dueño de la tabla** de sus propias policies.
La app conecta con un único rol (`database.md` línea 33: "la app conecta con
un solo rol") — el mismo que corrió esta migración, así que **es** el dueño.
Sin `FORCE`, esta migración no haría nada en producción: cada policy existiría
y cada query de la API la ignoraría en silencio.

Lo que `FORCE` **no** arregla: si ese rol único es además **superusuario** de
Postgres (frecuente en el usuario que un proveedor administrado da por
default — Railway incluido, sin verificar todavía en este entorno), RLS no
aplica **nunca** a un superusuario, con o sin `FORCE`. Por eso el `upgrade()`
consulta `pg_roles` y **avisa fuerte** (log, no excepción: bloquear todas las
migraciones futuras por una condición que no se puede confirmar desde acá
sería peor que avisar) si el rol conectado es superusuario o tiene
`BYPASSRLS`. Si el aviso aparece en el log de un despliegue real, esta
migración corrió pero **no protege nada** — hay que resolver el rol antes de
confiar en la policy.

## Lo que esto implica para migraciones futuras

Esta migración es DDL puro (`ALTER TABLE`, `CREATE POLICY`) y el DDL no pasa
por RLS. Pero cualquier migración **futura** que backfillee datos de estas
seis tablas (un `UPDATE`/`INSERT ... SELECT` sobre `organizations`,
`portfolios`, `business_units`, `departments`, `programs` o `projects`, como
hizo la 0108 con `portfolios`) corre con el mismo rol de siempre, y ese rol
ya no ve todas las filas sin ayuda: tiene que fijar el centinela primero —

```python
bind.execute(sa.text("SELECT set_config('app.tenant_id', '*', true)"))
```

— al principio de su `upgrade()`/`downgrade()`, o verá (y afectará) cero
filas en silencio. `SELECT`s de solo lectura sobre estas tablas dentro de una
migración tienen el mismo problema.

## No toca el worker ni el rollout de dominios

`app/core/tenant_context.py` ya está wireado en `api/deps.py` (toda petición
autenticada) y en los cinco puntos del worker que tocan estas tablas
(`ai.py`, `notifications.py`, `scheduled_minutes.py`, `scheduled_reports.py`,
`services/analytics/snapshots.py::snapshot_tenant`) — ninguno de esos cambios
de código va en esta migración, van en el mismo commit de US-241. El dominio
proyectos (`tasks`, `risks`, `issues`, etc., ya con FK desde `20260827_0116`)
queda para US-242.

Revision ID: 20260827_0117
Revises: 20260827_0116
Create Date: 2026-08-27
"""
from __future__ import annotations

import logging

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0117"
down_revision: str | None = "20260827_0116"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.us241")

#: Dominio jerarquía (ADR-037): organización → portafolio ⊃ programa →
#: proyecto. `business_units`/`departments` siguen vivas hasta el drop de W8
#: y siguen siendo tenant-scoped mientras tanto — se protegen igual.
TABLAS_JERARQUIA: tuple[str, ...] = (
    "organizations",
    "portfolios",
    "business_units",
    "departments",
    "programs",
    "projects",
)

_POLICY_USING = (
    "tenant_id = current_setting('app.tenant_id', true) "
    "OR current_setting('app.tenant_id', true) = '*'"
)


def _advertir_si_el_rol_puede_saltarse_rls(bind: sa.Connection) -> None:
    fila = bind.execute(
        sa.text(
            "SELECT rolsuper, rolbypassrls FROM pg_roles "
            "WHERE rolname = current_user"
        )
    ).one()
    if fila.rolsuper or fila.rolbypassrls:
        log.warning(
            "US-241: el rol de conexión (%s) es superusuario o tiene "
            "BYPASSRLS — las policies de esta migración no van a filtrar "
            "nada para él, con o sin FORCE ROW LEVEL SECURITY. Resolver el "
            "rol de conexión antes de confiar en RLS como control real.",
            bind.engine.url.username,
        )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite no tiene RLS. El esquema de tests sigue protegido solo por
        # el filtro `WHERE tenant_id = ...` de capa de aplicación, como
        # siempre — esta migración no le agrega ni le quita nada ahí.
        return

    _advertir_si_el_rol_puede_saltarse_rls(bind)

    for tabla in TABLAS_JERARQUIA:
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {tabla}_tenant_isolation ON {tabla} "
            f"FOR ALL USING ({_POLICY_USING}) WITH CHECK ({_POLICY_USING})"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for tabla in TABLAS_JERARQUIA:
        op.execute(f"DROP POLICY IF EXISTS {tabla}_tenant_isolation ON {tabla}")
        op.execute(f"ALTER TABLE {tabla} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabla} DISABLE ROW LEVEL SECURITY")
