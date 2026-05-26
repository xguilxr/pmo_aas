"""metric_snapshots — fundación de datos para dashboards N1/N2 (US-151).

Revision ID: 20260526_0079
Revises: 20260525_0078
Create Date: 2026-05-26 12:00:00

Foto semanal de métricas de stock a 4 niveles de scope (tenant/org/programa/
proyecto) para habilitar tendencias en dashboards y reportes Nivel 1/2.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260526_0079"
down_revision: str | None = "20260525_0078"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("scope_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("projects_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("projects_active", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("health_green", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("health_yellow", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("health_red", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_progress", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0"),
        sa.Column("budget_plan", sa.Numeric(precision=16, scale=2), nullable=False, server_default="0"),
        sa.Column("budget_actual", sa.Numeric(precision=16, scale=2), nullable=False, server_default="0"),
        sa.Column("open_risks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("severe_risks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("changes_in_review", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requests_in_review", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasks_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasks_done", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("milestones_due_7", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("milestones_due_14", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("milestones_due_30", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extras", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "scope_type",
            "scope_id",
            "snapshot_date",
            name="uq_metric_snapshot_scope_date",
        ),
    )
    op.create_index(
        "idx_metric_snapshot_scope",
        "metric_snapshots",
        ["scope_type", "scope_id", "snapshot_date"],
    )
    op.create_index(
        "idx_metric_snapshot_tenant_date",
        "metric_snapshots",
        ["tenant_id", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_index("idx_metric_snapshot_tenant_date", table_name="metric_snapshots")
    op.drop_index("idx_metric_snapshot_scope", table_name="metric_snapshots")
    op.drop_table("metric_snapshots")
