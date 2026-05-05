"""scheduled_reports add day_of_week + hour_of_day + run_at — ENH-046.

Revision ID: 20260505_0036
Revises: 20260429_0035
Create Date: 2026-05-05 16:00:00

Owner pidió poder elegir día de la semana + hora para reportes
recurrentes y fecha + hora para uno-time. Esta migración agrega 3
columnas opcionales a `scheduled_reports`. La validación condicional
vive en la API (Pydantic): weekly requiere day_of_week + hour_of_day,
daily requiere hour_of_day, once requiere run_at.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260505_0036"
down_revision: str | None = "20260429_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scheduled_reports",
        sa.Column("day_of_week", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "scheduled_reports",
        sa.Column("hour_of_day", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "scheduled_reports",
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scheduled_reports", "run_at")
    op.drop_column("scheduled_reports", "hour_of_day")
    op.drop_column("scheduled_reports", "day_of_week")
