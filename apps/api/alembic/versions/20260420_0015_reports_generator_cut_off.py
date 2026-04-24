"""reports.generator + reports.cut_off_date (EP014 — US-038/039)

Revision ID: 20260420_0015
Revises: 20260420_0014
Create Date: 2026-04-20 00:15:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260420_0015"
down_revision: str | None = "20260420_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.add_column(
            sa.Column(
                "generator",
                sa.String(32),
                nullable=False,
                server_default="manual",
            )
        )
        batch.add_column(sa.Column("cut_off_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.drop_column("cut_off_date")
        batch.drop_column("generator")
