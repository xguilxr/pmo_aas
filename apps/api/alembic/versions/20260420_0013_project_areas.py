"""project_areas — actores/áreas del proyecto (US-018, EP005)

Revision ID: 20260420_0013
Revises: 20260420_0012
Create Date: 2026-04-20 00:13:00

DEC-009: las áreas son referenciables como texto, no son usuarios del
sistema.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260420_0013"
down_revision: Union[str, None] = "20260420_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_areas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "type", sa.String(16), nullable=False, server_default="area"
        ),  # 'area'|'actor'|'team'
        sa.Column("description", sa.String(2000)),
        sa.Column("contact_name", sa.String(200)),
        sa.Column("contact_email", sa.String(200)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_project_areas_project", "project_areas", ["project_id"])
    op.create_index("ix_project_areas_tenant", "project_areas", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_project_areas_tenant", table_name="project_areas")
    op.drop_index("ix_project_areas_project", table_name="project_areas")
    op.drop_table("project_areas")
