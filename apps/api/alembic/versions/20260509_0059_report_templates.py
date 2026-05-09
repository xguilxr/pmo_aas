"""report_templates (ENH-085) + reports.html_content (US-109).

Revision ID: 20260509_0059
Revises: 20260509_0058
Create Date: 2026-05-09 01:00:00

ENH-085: nueva tabla `report_templates` (tenant-shared, distinta de
`ai_report_templates` per-project) para guardar reportes tweakeados
como plantillas reusables.

US-109: nueva columna `reports.html_content` para persistir el HTML
final del reporte (con tweaks aplicados via LLM).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260509_0059"
down_revision: str | None = "20260509_0058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_report_templates_tenant", "report_templates", ["tenant_id"]
    )
    op.alter_column("report_templates", "is_shared", server_default=None)
    # US-109: HTML final del reporte (con tweaks aplicados). Default ""
    # para filas existentes — se rellena al primer render desde el
    # endpoint US-111.
    op.add_column(
        "reports",
        sa.Column(
            "html_content",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("reports", "html_content", server_default=None)


def downgrade() -> None:
    op.drop_column("reports", "html_content")
    op.drop_index("ix_report_templates_tenant", table_name="report_templates")
    op.drop_table("report_templates")
