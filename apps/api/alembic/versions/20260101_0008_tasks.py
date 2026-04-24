"""tasks + task_dependencies

Revision ID: 20260101_0008
Revises: 20260101_0007
Create Date: 2026-01-01 00:07:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260101_0008"
down_revision: str | None = "20260101_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wbs", sa.String(64)),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("tasks.id")),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.String(5000)),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("duration_days", sa.Integer),
        sa.Column("progress", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("is_milestone", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("priority", sa.SmallInteger),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("external_id", sa.String(100)),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"])

    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("predecessor_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("successor_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(4), nullable=False, server_default="FS"),
        sa.Column("lag_days", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("predecessor_id", "successor_id", name="uq_task_dep"),
    )


def downgrade() -> None:
    op.drop_table("task_dependencies")
    op.drop_index("ix_tasks_tenant_id", table_name="tasks")
    op.drop_index("ix_tasks_project_id", table_name="tasks")
    op.drop_table("tasks")
