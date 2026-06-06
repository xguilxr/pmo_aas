"""scheduled_reports: report_builder_template_id (US-131).

Revision ID: 20260525_0074
Revises: 20260525_0073
Create Date: 2026-05-25 10:00:00

US-131 — extiende `scheduled_reports` para soportar emisión de
reportes custom del Report Builder. Cuando `report_type='custom'`,
`report_builder_template_id` apunta a una `report_builder_templates`
y el worker invoca el motor de US-123 para renderizar y enviar el PDF.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260525_0074"
down_revision: str | None = "20260525_0073"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scheduled_reports") as batch:
        batch.add_column(
            sa.Column(
                "report_builder_template_id",
                sa.String(length=36),
                sa.ForeignKey(
                    "report_builder_templates.id", ondelete="SET NULL"
                ),
                nullable=True,
            )
        )
    op.create_index(
        "ix_scheduled_reports_builder_template",
        "scheduled_reports",
        ["report_builder_template_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduled_reports_builder_template",
        table_name="scheduled_reports",
    )
    with op.batch_alter_table("scheduled_reports") as batch:
        batch.drop_column("report_builder_template_id")
