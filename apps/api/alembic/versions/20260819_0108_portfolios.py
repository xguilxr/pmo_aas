"""US-198 / ADR-037 — `portfolios` entra y los programas se mudan dentro.

La jerarquía pasa de `organización → BU → departamento → programa → proyecto` a
`organización → portafolio ⊃ programa → proyecto`. Lo que cambia no es la forma
del árbol sino **qué modela**: BU y departamento describían el organigrama del
cliente; el portafolio describe la cartera de inversión, que es la pregunta que
un comité de dirección hace ("qué hacemos, con qué, y qué dejamos de hacer").

**No hay migración de datos desde BU/departamento**, y eso es un dato, no un
atajo: el owner confirmó el 2026-08-19 que nunca se usaron en producción. Un
mapeo BU→portafolio inventaría una taxonomía a partir de tablas vacías. Esta
migración lo **cuenta en el momento de correr** y lo deja en el registro: si
alguna instalación tuviera filas, se ve antes de que US-199 suelte las columnas.

## Las tres cosas que hace, y por qué en este orden

1. `portfolios` nace vacía.
2. `programs.portfolio_id` nace **nullable**, se rellena, y solo entonces se
   endurece a `NOT NULL`. Al revés no se puede: `SET NOT NULL` sobre una columna
   con nulos falla, y crearla ya `NOT NULL` sin `server_default` falla igual en
   cuanto la tabla tiene una fila. El endurecimiento va en **esta misma**
   migración a propósito — dejarlo para después es como se acumulan las columnas
   «temporalmente nullable» que nunca se endurecen.
3. `projects.portfolio_id` nace nullable y **se rellena desde el programa** para
   los proyectos que tienen uno. Si no se rellenara, la regla de consistencia
   (`services/jerarquia.py`) nacería violada por todos los proyectos existentes:
   tendrían programa y no tendrían su portafolio.

El relleno crea **un «Portafolio General» por organización que tenga programas**
— no uno global, no uno por organización. Uno global rompería el aislamiento
entre organizaciones; uno por organización sin programas sería basura en la
pantalla de alguien que nunca usó programas.

## Por qué hay una rama por motor

SQLite no sabe endurecer una columna existente ni añadirle una restricción:
`ALTER TABLE` no lo soporta y Alembic solo lo emula recreando la tabla, que en
`projects` significa reflejar y reconstruir a mano su índice único y sus once
claves ajenas — más riesgo que el que la rama evita.

Lo que la rama de SQLite se salta es **exactamente lo que en SQLite ya está
puesto por otro camino**: el esquema de las pruebas nace de
`Base.metadata.create_all`, donde `portfolio_id` ya nace `NOT NULL` con su clave
ajena. Y lo que sí corre en los dos motores es el **relleno**, que es donde una
migración de datos se equivoca (la lección de la 0098: ejercitar SQL de
migración contra un sujeto inventado no prueba nada). El DDL de producción lo
ejerce el job `api-migrations-postgres` con `upgrade head` / `downgrade base` /
`upgrade head`.

## La bajada

Exacta hacia el esquema, no hacia los datos: al bajar desaparecen las columnas y
la tabla, y con ellas la clasificación por portafolio que se hubiera capturado.
No hay dónde guardarla —el esquema anterior no tiene el concepto— así que la
bajada es **destructiva de información nueva**, y eso es lo esperable en un
`downgrade` que retira una entidad. Lo que sí conserva intacto es todo lo
anterior: `programs.department_id`, `projects.business_unit_id` y
`projects.department_id` no se tocan aquí (US-199 los retira, con sus lectores).

Revision ID: 20260819_0108
Revises: 20260807_0107
Create Date: 2026-08-19
"""
from __future__ import annotations

import logging
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260819_0108"
down_revision: str | None = "20260807_0107"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.us198")

#: Mismo literal que `app.services.jerarquia.NOMBRE_PORTAFOLIO_GENERAL`. Está
#: duplicado porque una migración no importa código de la aplicación: el día que
#: `jerarquia.py` se renombre o desaparezca, esta migración tiene que seguir
#: corriendo igual sobre una base de 2026.
NOMBRE_PORTAFOLIO_GENERAL = "Portafolio General"

DESCRIPCION_GENERAL = (
    "Portafolio por defecto de la organización. Reagrupa lo que no se "
    "clasificó en un portafolio propio."
)

#: Las columnas que quedan sin lectores nuevos tras esta oleada. No se tocan: se
#: cuentan, para que US-199 las suelte con la evidencia delante.
RESIDUO_BU_DEPTO: tuple[tuple[str, str], ...] = (
    ("programs", "department_id"),
    ("projects", "business_unit_id"),
    ("projects", "department_id"),
    ("project_requests", "business_unit_id"),
    ("project_requests", "department_id"),
    ("project_charters", "business_unit_id"),
    ("project_charters", "department_id"),
)


def _contar(bind: sa.Connection, tabla: str, columna: str, *, nulos: bool = False) -> int:
    """Cuántas filas tienen (o no tienen) valor en esa columna.

    El nombre de tabla y de columna se interpolan porque no hay forma de
    parametrizar un identificador en SQL; los únicos valores que llegan aquí
    salen de `RESIDUO_BU_DEPTO` y de literales de este módulo, nunca de
    entrada externa.
    """
    prueba = "IS NULL" if nulos else "IS NOT NULL"
    total = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {tabla} WHERE {columna} {prueba}")
    ).scalar()
    return int(total or 0)


def upgrade() -> None:
    # -- 1. La tabla nueva ---------------------------------------------------
    op.create_table(
        "portfolios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(32), nullable=True),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column(
            "owner_actor_id",
            sa.String(36),
            sa.ForeignKey("actors.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "name", name="uq_portfolio_tenant_org_name"
        ),
    )
    op.create_index("ix_portfolios_tenant_id", "portfolios", ["tenant_id"])
    op.create_index("ix_portfolios_org_id", "portfolios", ["organization_id"])
    op.create_index("ix_portfolios_owner_actor_id", "portfolios", ["owner_actor_id"])

    # -- 2. programs.portfolio_id: nullable → relleno → NOT NULL -------------
    op.add_column("programs", sa.Column("portfolio_id", sa.String(36), nullable=True))

    bind = op.get_bind()
    pares = bind.execute(
        sa.text("SELECT DISTINCT tenant_id, organization_id FROM programs")
    ).all()
    for tenant_id, organization_id in pares:
        # `SELECT` antes de `INSERT` y no un upsert: la sintaxis de
        # `ON CONFLICT` no es portable, y esta migración corre en los dos
        # motores. No pretende cubrir un reintento —Alembic envuelve cada
        # revisión en una transacción y en Postgres el DDL también entra en
        # ella, así que un fallo a mitad deja la tabla sin crear— sino hacer
        # explícito que el nombre es único por organización.
        existente = bind.execute(
            sa.text(
                "SELECT id FROM portfolios "
                "WHERE tenant_id = :t AND organization_id = :o AND name = :n"
            ),
            {"t": tenant_id, "o": organization_id, "n": NOMBRE_PORTAFOLIO_GENERAL},
        ).scalar()
        portfolio_id = existente or str(uuid4())
        if not existente:
            bind.execute(
                sa.text(
                    "INSERT INTO portfolios "
                    "(id, tenant_id, organization_id, name, description, is_active) "
                    "VALUES (:id, :t, :o, :n, :d, TRUE)"
                ),
                {
                    "id": portfolio_id,
                    "t": tenant_id,
                    "o": organization_id,
                    "n": NOMBRE_PORTAFOLIO_GENERAL,
                    "d": DESCRIPCION_GENERAL,
                },
            )
        bind.execute(
            sa.text(
                "UPDATE programs SET portfolio_id = :p "
                "WHERE tenant_id = :t AND organization_id = :o AND portfolio_id IS NULL"
            ),
            {"p": portfolio_id, "t": tenant_id, "o": organization_id},
        )

    huerfanos = _contar(bind, "programs", "portfolio_id", nulos=True)
    if huerfanos:
        # Se para **antes** de endurecer: fallar aquí deja un mensaje que se lee
        # en el registro del despliegue; fallar en el `SET NOT NULL` deja un
        # error del motor sin pista de qué fila lo causó.
        raise RuntimeError(
            f"{huerfanos} programa(s) sin portafolio tras el relleno. "
            "Revisa `programs.tenant_id`/`organization_id` antes de reintentar."
        )

    if bind.dialect.name != "sqlite":
        op.alter_column("programs", "portfolio_id", existing_type=sa.String(36), nullable=False)
        op.create_foreign_key(
            "fk_programs_portfolio_id", "programs", "portfolios", ["portfolio_id"], ["id"]
        )
    op.create_index("ix_programs_portfolio_id", "programs", ["portfolio_id"])

    # -- 3. projects.portfolio_id, heredado del programa ---------------------
    op.add_column("projects", sa.Column("portfolio_id", sa.String(36), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE projects SET portfolio_id = ("
            "  SELECT p.portfolio_id FROM programs p WHERE p.id = projects.program_id"
            ") WHERE program_id IS NOT NULL"
        )
    )
    if bind.dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_projects_portfolio_id", "projects", "portfolios", ["portfolio_id"], ["id"]
        )
    op.create_index("ix_projects_portfolio_id", "projects", ["portfolio_id"])

    # -- 4. El resto de BU/departamento, contado y anotado -------------------
    residuo = {
        f"{tabla}.{col}": _contar(bind, tabla, col) for tabla, col in RESIDUO_BU_DEPTO
    }
    con_datos = {k: v for k, v in residuo.items() if v}
    if con_datos:
        log.warning("US-198 — referencias BU/departamento vivas al migrar: %s", con_datos)
    else:
        log.info("US-198 — sin referencias BU/departamento vivas (lo esperado).")


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_projects_portfolio_id", table_name="projects")
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_projects_portfolio_id", "projects", type_="foreignkey")
    op.drop_column("projects", "portfolio_id")

    op.drop_index("ix_programs_portfolio_id", table_name="programs")
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_programs_portfolio_id", "programs", type_="foreignkey")
    op.drop_column("programs", "portfolio_id")

    op.drop_index("ix_portfolios_owner_actor_id", table_name="portfolios")
    op.drop_index("ix_portfolios_org_id", table_name="portfolios")
    op.drop_index("ix_portfolios_tenant_id", table_name="portfolios")
    op.drop_table("portfolios")
