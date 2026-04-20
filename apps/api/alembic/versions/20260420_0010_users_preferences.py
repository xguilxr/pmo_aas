"""users.preferences JSON

Revision ID: 20260420_0010
Revises: 20260420_0009
Create Date: 2026-04-20 00:10:00

US-NEW-007 (EP001): preferences por usuario para tema (dark/light/system).
Columna genérica JSON que también albergará otras preferencias a futuro.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260420_0010"
down_revision: Union[str, None] = "20260420_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "preferences",
                sa.JSON,
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("preferences")
