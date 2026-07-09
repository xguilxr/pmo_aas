"""US-182 — Actors como pool de recursos con capacidad (Revamp 1.0).

Extiende `actors` con clasificación de recurso (tipo, función de
portafolio, seniority, escasez, skills, ubicación, organización) y
capacidad consumible (nominal vs disponible para proyectos) + flags
clave/compartido + costo opcional. Sin backfill: los actores existentes
quedan "sin clasificar" (NULLs) con capacidad default 100/100.

Revision ID: 20260708_0092
Revises: 20260708_0091
Create Date: 2026-07-08 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260708_0092"
down_revision: str | None = "20260708_0091"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "fte_cost_rate",
    "is_shared_resource",
    "is_key_resource",
    "project_capacity_pct",
    "nominal_capacity_pct",
    "skills_tags",
    "location",
    "scarcity_level",
    "seniority",
    "portfolio_function",
    "resource_type",
    "organization_id",
)


def upgrade() -> None:
    with op.batch_alter_table("actors") as batch:
        batch.add_column(sa.Column("organization_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("resource_type", sa.String(length=24), nullable=True))
        batch.add_column(sa.Column("portfolio_function", sa.String(length=24), nullable=True))
        batch.add_column(sa.Column("seniority", sa.String(length=8), nullable=True))
        batch.add_column(sa.Column("scarcity_level", sa.String(length=8), nullable=True))
        batch.add_column(sa.Column("location", sa.String(length=100), nullable=True))
        batch.add_column(
            sa.Column("skills_tags", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(
            sa.Column(
                "nominal_capacity_pct",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="100",
            )
        )
        batch.add_column(
            sa.Column(
                "project_capacity_pct",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="100",
            )
        )
        batch.add_column(
            sa.Column("is_key_resource", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("is_shared_resource", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.add_column(sa.Column("fte_cost_rate", sa.Numeric(10, 2), nullable=True))
        batch.create_foreign_key(
            "fk_actors_organization",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_check_constraint(
            "ck_actors_resource_type",
            "resource_type IS NULL OR resource_type IN "
            "('cliente_negocio','cliente_it','e4_pmo','e4_tecnologia','vendor_externo')",
        )
        batch.create_check_constraint(
            "ck_actors_portfolio_function",
            "portfolio_function IS NULL OR portfolio_function IN "
            "('pm','pmo','arquitectura','infraestructura','aplicaciones','datos',"
            "'seguridad','integraciones','negocio','change','testing','vendor')",
        )
        batch.create_check_constraint(
            "ck_actors_seniority",
            "seniority IS NULL OR seniority IN ('junior','mid','senior','lead')",
        )
        batch.create_check_constraint(
            "ck_actors_scarcity",
            "scarcity_level IS NULL OR scarcity_level IN ('alta','media','baja')",
        )
    op.create_index(
        "ix_actors_tenant_resource_type", "actors", ["tenant_id", "resource_type"]
    )
    op.create_index(
        "ix_actors_tenant_org", "actors", ["tenant_id", "organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_actors_tenant_org", table_name="actors")
    op.drop_index("ix_actors_tenant_resource_type", table_name="actors")
    with op.batch_alter_table("actors") as batch:
        batch.drop_constraint("ck_actors_scarcity", type_="check")
        batch.drop_constraint("ck_actors_seniority", type_="check")
        batch.drop_constraint("ck_actors_portfolio_function", type_="check")
        batch.drop_constraint("ck_actors_resource_type", type_="check")
        batch.drop_constraint("fk_actors_organization", type_="foreignkey")
        for col in _COLUMNS:
            batch.drop_column(col)
