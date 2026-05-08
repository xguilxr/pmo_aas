"""areas.organization_id — scope opcional por organización (BUG-061).

Revision ID: 20260508_0054
Revises: 20260508_0053
Create Date: 2026-05-08 17:30:00

Owner decisión 2026-05-08 (híbrido): un Área puede ser tenant-global
(`organization_id IS NULL`, ej.: PMO seed) o atada a una organización
(`organization_id` set). Permite tener "IT" en Org A e "IT" en Org B
con recursos distintos, manteniendo la posibilidad de áreas
tenant-wide.

Cambios:
1. `areas.organization_id` nullable + FK a `organizations`.
2. Drop del unique `uq_areas_tenant_name`.
3. Nuevo unique `uq_areas_tenant_org_name (tenant_id, organization_id, name)`
   — para áreas org-scoped (NULL no choca con NULL en Postgres, así que
   las globales se cuidan con el partial unique de abajo).
4. Partial unique `uq_areas_tenant_global_name (tenant_id, name)`
   `WHERE organization_id IS NULL` — evita duplicar nombres entre
   áreas globales.
5. Backfill: nada — todas las áreas existentes quedan con
   `organization_id=NULL` (tenant-global), comportamiento previo
   preservado.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260508_0054"
down_revision: str | None = "20260508_0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Add organization_id (nullable). FK separada para permitir
    # batch_alter en SQLite.
    with op.batch_alter_table("areas") as batch_op:
        batch_op.add_column(
            sa.Column(
                "organization_id",
                sa.String(length=36),
                nullable=True,
            )
        )

    # FK + drop del unique viejo + uniques nuevos. Solo en Postgres
    # creamos el partial unique (SQLite no soporta CREATE UNIQUE INDEX
    # ... WHERE de la misma forma pero sí lo tolera; mantenemos la
    # sintaxis cross-DB con `postgresql_where`).
    if bind.dialect.name == "postgresql":
        op.create_foreign_key(
            "fk_areas_organization",
            "areas",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.drop_constraint(
            "uq_areas_tenant_name", "areas", type_="unique"
        )
        # Org-scoped: (tenant, org, name) único cuando org no es NULL.
        # En Postgres NULL ≠ NULL, así que esto no afecta a las globales.
        op.create_index(
            "uq_areas_tenant_org_name",
            "areas",
            ["tenant_id", "organization_id", "name"],
            unique=True,
            postgresql_where=sa.text("organization_id IS NOT NULL"),
        )
        # Globales: (tenant, name) único cuando org IS NULL.
        op.create_index(
            "uq_areas_tenant_global_name",
            "areas",
            ["tenant_id", "name"],
            unique=True,
            postgresql_where=sa.text("organization_id IS NULL"),
        )
        op.create_index(
            "ix_areas_tenant_organization",
            "areas",
            ["tenant_id", "organization_id"],
        )
    else:
        # SQLite (test env): batch alter para FK + drop unique.
        with op.batch_alter_table("areas") as batch_op:
            batch_op.create_foreign_key(
                "fk_areas_organization",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )
            try:
                batch_op.drop_constraint(
                    "uq_areas_tenant_name", type_="unique"
                )
            except Exception:
                pass
        op.create_index(
            "uq_areas_tenant_org_name",
            "areas",
            ["tenant_id", "organization_id", "name"],
            unique=True,
        )
        op.create_index(
            "ix_areas_tenant_organization",
            "areas",
            ["tenant_id", "organization_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("ix_areas_tenant_organization", table_name="areas")
        op.drop_index("uq_areas_tenant_global_name", table_name="areas")
        op.drop_index("uq_areas_tenant_org_name", table_name="areas")
        op.create_unique_constraint(
            "uq_areas_tenant_name", "areas", ["tenant_id", "name"]
        )
        op.drop_constraint(
            "fk_areas_organization", "areas", type_="foreignkey"
        )
        with op.batch_alter_table("areas") as batch_op:
            batch_op.drop_column("organization_id")
    else:
        op.drop_index("ix_areas_tenant_organization", table_name="areas")
        op.drop_index("uq_areas_tenant_org_name", table_name="areas")
        with op.batch_alter_table("areas") as batch_op:
            batch_op.drop_constraint(
                "fk_areas_organization", type_="foreignkey"
            )
            batch_op.create_unique_constraint(
                "uq_areas_tenant_name", ["tenant_id", "name"]
            )
            batch_op.drop_column("organization_id")
