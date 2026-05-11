"""US-117 — lessons.owner_actor_id (consistencia con risks/issues/tasks).

Revision ID: 20260510_0062
Revises: 20260510_0061
Create Date: 2026-05-10 01:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260510_0062"
down_revision: str | None = "20260510_0061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("lessons") as batch:
        batch.add_column(
            sa.Column(
                "owner_actor_id",
                sa.String(length=36),
                sa.ForeignKey("actors.id", ondelete="SET NULL"),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("lessons") as batch:
        batch.drop_column("owner_actor_id")
