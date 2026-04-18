"""ai_jobs + reports

Revision ID: 20260101_0007
Revises: 20260101_0006
Create Date: 2026-01-01 00:06:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260101_0007"
down_revision: Union[str, None] = "20260101_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36)),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("input", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("output", sa.JSON),
        sa.Column("model_used", sa.String(100)),
        sa.Column("tokens_in", sa.Integer),
        sa.Column("tokens_out", sa.Integer),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("error", sa.String(2000)),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_jobs_tenant_id", "ai_jobs", ["tenant_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("sections", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("recipients", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("generated_by_ai", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reports_project_id", "reports", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_project_id", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_ai_jobs_tenant_id", table_name="ai_jobs")
    op.drop_table("ai_jobs")
