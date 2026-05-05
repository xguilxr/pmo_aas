"""report_history — US-092.

Revision ID: 20260505_0042
Revises: 20260505_0041
Create Date: 2026-05-05 22:30:00

Tabla de historial de reportes generados (manual o por scheduler).

MVP: persiste sólo metadata + referencia al Report fuente (los datos
para re-render viven en `reports.sections`). `file_key` (R2) queda en
el schema para una iteración futura que sí archive el PDF binario.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260505_0042"
down_revision: str | None = "20260505_0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_history",
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
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "generated_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("file_key", sa.String(length=500), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "scheduled_report_id",
            sa.String(length=36),
            sa.ForeignKey("scheduled_reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_report_id",
            sa.String(length=36),
            sa.ForeignKey("reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_report_history_project_generated",
        "report_history",
        ["project_id", "generated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_report_history_project_generated", table_name="report_history")
    op.drop_table("report_history")
