"""scheduled_minutes table (ENH-107, EP014).

Revision ID: 20260522_0068
Revises: 20260522_0067
Create Date: 2026-05-22 12:00:00

Tabla símil de `scheduled_reports` (US-056): programaciones
automáticas para envío de minutas. Mismas columnas de cadencia
(daily/weekly/monthly/once + day_of_week/hour_of_day/day_of_month +
run_at), recipients, enabled, last/next_run_at, created_by; agrega
`template_id` opcional para usar plantillas de minuta más adelante.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260522_0068"
down_revision: str | None = "20260522_0067"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_minutes",
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
        sa.Column("cadence", sa.String(length=16), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=True),
        sa.Column("hour_of_day", sa.SmallInteger(), nullable=True),
        sa.Column("day_of_month", sa.SmallInteger(), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("template_id", sa.String(length=36), nullable=True),
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
        "idx_sched_minutes_tenant_project",
        "scheduled_minutes",
        ["tenant_id", "project_id"],
    )
    op.create_index(
        "idx_sched_minutes_due",
        "scheduled_minutes",
        ["enabled", "next_run_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_sched_minutes_due", table_name="scheduled_minutes")
    op.drop_index("idx_sched_minutes_tenant_project", table_name="scheduled_minutes")
    op.drop_table("scheduled_minutes")
