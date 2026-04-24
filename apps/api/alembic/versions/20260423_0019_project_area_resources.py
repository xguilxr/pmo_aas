"""project_area_resources + area_leader_id (ENH-020 + US-062)

Revision ID: 20260423_0019
Revises: 20260423_0018
Create Date: 2026-04-23 14:00:00

Habilita múltiples recursos por área (con o sin cuenta en la plataforma)
y un area_leader_id opcional (FK a users). Los recursos internos llevan
`user_id`; los externos llevan `name` + `email` libres.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260423_0019"
down_revision: str | None = "20260423_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_areas",
        sa.Column(
            "area_leader_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_table(
        "project_area_resources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "area_id",
            sa.String(length=36),
            sa.ForeignKey("project_areas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_par_area", "project_area_resources", ["area_id"]
    )
    op.create_index(
        "idx_par_tenant_user", "project_area_resources", ["tenant_id", "user_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_par_tenant_user", table_name="project_area_resources")
    op.drop_index("idx_par_area", table_name="project_area_resources")
    op.drop_table("project_area_resources")
    op.drop_column("project_areas", "area_leader_id")
