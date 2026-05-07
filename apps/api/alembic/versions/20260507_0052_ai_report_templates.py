"""ai_report_templates — plantillas reusables de reporte IA (ENH-080).

Revision ID: 20260507_0052
Revises: 20260507_0051
Create Date: 2026-05-07 22:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260507_0052"
down_revision: str | None = "20260507_0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_report_templates",
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
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "base",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'avance'"),
        ),
        sa.Column(
            "config",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ai_report_templates_tenant_project",
        "ai_report_templates",
        ["tenant_id", "project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_report_templates_tenant_project", table_name="ai_report_templates"
    )
    op.drop_table("ai_report_templates")
