"""scheduled_reports table (US-056, EP014 + EP011)

Revision ID: 20260423_0018
Revises: 20260421_0017
Create Date: 2026-04-23 12:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260423_0018"
down_revision: str | None = "20260421_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("report_type", sa.String(length=32), nullable=False),
        sa.Column("cadence", sa.String(length=16), nullable=False),
        sa.Column(
            "recipients", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_sched_reports_tenant_project",
        "scheduled_reports",
        ["tenant_id", "project_id"],
    )
    op.create_index(
        "idx_sched_reports_due",
        "scheduled_reports",
        ["enabled", "next_run_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_sched_reports_due", table_name="scheduled_reports")
    op.drop_index("idx_sched_reports_tenant_project", table_name="scheduled_reports")
    op.drop_table("scheduled_reports")
