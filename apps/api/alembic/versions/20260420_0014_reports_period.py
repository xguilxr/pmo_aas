"""reports.period — periodicidad (US-022, EP006)

Revision ID: 20260420_0014
Revises: 20260420_0013
Create Date: 2026-04-20 00:14:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260420_0014"
down_revision: str | None = "20260420_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.add_column(sa.Column("period", sa.String(16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.drop_column("period")
