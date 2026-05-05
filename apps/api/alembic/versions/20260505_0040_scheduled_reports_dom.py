"""scheduled_reports.day_of_month — ENH-056.

Revision ID: 20260505_0040
Revises: 20260505_0039
Create Date: 2026-05-05 21:45:00

Agrega `day_of_month` (smallint 1-31, nullable) a `scheduled_reports`.
Solo se requiere cuando `cadence='monthly'`. Backward-compat: rows
monthly legacy sin `day_of_month` mantienen el cálculo `+30 días`.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260505_0040"
down_revision: str | None = "20260505_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scheduled_reports") as batch_op:
        batch_op.add_column(sa.Column("day_of_month", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("scheduled_reports") as batch_op:
        batch_op.drop_column("day_of_month")
