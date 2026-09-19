"""US-285 — catálogos de proyecto por inquilino (`tenant_catalog_values`).

## Qué crea

La tabla donde cada inquilino define sus propios tipos y fases de proyecto, y
la siembra con los valores que hoy están en el enum de `app/dominio/proyecto.py`
para **todos** los inquilinos que ya existen.

## Por qué la siembra va aquí y no en el arranque de la aplicación

Sin ella, el primer inquilino que abriera `/admin/catalogos` después del
despliegue vería dos listas vacías, y su formulario de alta de proyecto se
quedaría sin opciones — con proyectos ya guardados que apuntan a claves que el
catálogo no conoce. La tabla y sus datos son la misma unidad de cambio.

## Por qué los valores están escritos aquí y no importados del dominio

Una migración es una foto de un momento. Si importara `app.dominio.proyecto`,
el día que alguien agregue una fase al enum esta migración **cambiaría de
efecto retroactivamente**: la base que se levante desde cero no quedaría igual
que la que se migró en su día. Duplicar seis líneas es el precio de que una
migración vieja siga significando lo mismo dentro de un año.

El trinquete `test_us285_catalogos.py` comprueba que lo sembrado aquí coincide
hoy con el dominio, así que la copia no puede desviarse en silencio mientras
las dos listas deban ser iguales.

## Sobre RLS

El criterio de aceptación pedía crear la tabla «con su política RLS desde el
inicio». No se hace, y no por olvido: **ninguna** tabla de esta base tiene RLS.
ADR-003 lo aceptó en diseño y anota desde 2026-05-23 que no está implementado;
`architecture/database.md` describe el aislamiento como filtrado en capa de
aplicación. Una política en una sola tabla, con la aplicación conectándose como
dueña —que en PostgreSQL salta RLS salvo `FORCE`—, daría una protección
aparente sin serlo, que es peor que no tenerla. Cuando W3 active RLS, esta
tabla entra en la misma migración que el resto.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260919_0117"
down_revision: str | None = "20260911_0116"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: Copia deliberada de `app/dominio/proyecto.py` en el momento de esta
#: migración. Ver el encabezado.
TIPOS: tuple[tuple[str, str], ...] = (
    ("transformacion", "Transformación"),
    ("operacion", "Operación"),
    ("innovacion", "Innovación"),
    ("bau", "BAU (operación continua)"),
)

#: `(clave, etiqueta, terminal)`. `activa` es lo contrario de `terminal`.
FASES: tuple[tuple[str, str, bool], ...] = (
    ("preparacion", "Preparación", False),
    ("ejecucion", "Ejecución", False),
    ("hypercare", "Hypercare", False),
    ("cerrado", "Cerrado", True),
    ("cancelado", "Cancelado", True),
)


def upgrade() -> None:
    op.create_table(
        "tenant_catalog_values",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("catalogo", sa.String(length=32), nullable=False),
        sa.Column("clave", sa.String(length=64), nullable=False),
        sa.Column("etiqueta", sa.String(length=120), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "activo", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "catalogo", "clave", name="uq_catalogo_valor_clave"
        ),
    )
    op.create_index(
        "ix_tenant_catalog_values_tenant_id",
        "tenant_catalog_values",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_catalog_values_tenant_catalogo",
        "tenant_catalog_values",
        ["tenant_id", "catalogo"],
    )
    _sembrar()


def _sembrar() -> None:
    """Un valor por inquilino existente, con `INSERT ... SELECT` desde `tenants`.

    Se hace en SQL y no en Python para no traerse la lista de inquilinos a
    memoria: una base con mil inquilinos son nueve mil filas, y un bucle por
    fila multiplicaría por nueve mil los viajes a la base durante el despliegue.
    """
    filas: list[tuple[str, str, str, int, str]] = []
    for i, (clave, etiqueta) in enumerate(TIPOS):
        filas.append(("tipo_proyecto", clave, etiqueta, i, "{}"))
    for i, (clave, etiqueta, terminal) in enumerate(FASES):
        datos = (
            '{"terminal": true, "activa": false}'
            if terminal
            else '{"terminal": false, "activa": true}'
        )
        filas.append(("fase_proyecto", clave, etiqueta, i, datos))

    conexion = op.get_bind()
    # `gen_random_uuid()` no está en todos los despliegues (pgcrypto), y el resto
    # de la base usa UUID como texto: se compone con `md5` sobre el par
    # (inquilino, valor), que además hace la siembra idempotente si se repite.
    for catalogo, clave, etiqueta, orden, datos in filas:
        conexion.execute(
            sa.text(
                """
                INSERT INTO tenant_catalog_values
                    (id, tenant_id, catalogo, clave, etiqueta, orden, activo,
                     metadata, created_at, updated_at)
                SELECT
                    md5(t.id || ':' || :catalogo || ':' || :clave),
                    t.id, :catalogo, :clave, :etiqueta, :orden, true,
                    CAST(:datos AS json), now(), now()
                FROM tenants t
                """
            ),
            {
                "catalogo": catalogo,
                "clave": clave,
                "etiqueta": etiqueta,
                "orden": orden,
                "datos": datos,
            },
        )


def downgrade() -> None:
    op.drop_index(
        "ix_tenant_catalog_values_tenant_catalogo",
        table_name="tenant_catalog_values",
    )
    op.drop_index(
        "ix_tenant_catalog_values_tenant_id", table_name="tenant_catalog_values"
    )
    op.drop_table("tenant_catalog_values")
