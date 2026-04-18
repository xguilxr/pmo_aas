"""projects table

Revision ID: 20260101_0004
Revises: 20260101_0003
Create Date: 2026-01-01 00:03:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260101_0004"
down_revision: Union[str, None] = "20260101_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("program_id", sa.String(36), sa.ForeignKey("programs.id")),
        sa.Column("folio", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(5000)),
        sa.Column("type", sa.String(50)),
        sa.Column("priority", sa.SmallInteger),
        sa.Column("phase", sa.String(32), nullable=False, server_default="planning"),
        sa.Column("pm_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("sponsor", sa.String(200)),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("budget", sa.Numeric(14, 2)),
        sa.Column("actual_budget", sa.Numeric(14, 2)),
        sa.Column("progress", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("health_status", sa.String(16), nullable=False, server_default="green"),
        sa.Column("request_id", sa.String(36)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "folio", name="uq_projects_tenant_folio"),
    )
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_projects_tenant_id", table_name="projects")
    op.drop_table("projects")
