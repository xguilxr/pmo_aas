"""risks.comments JSON column (US-058)

Revision ID: 20260423_0020
Revises: 20260423_0019
Create Date: 2026-04-23 16:00:00

Agrega campo `comments` a `risks` (mismo patrón que `issues.comments`)
para soportar comentarios estilo Jira desde el panel editable de RAID.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260423_0020"
down_revision: Union[str, None] = "20260423_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risks",
        sa.Column(
            "comments", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
    )


def downgrade() -> None:
    op.drop_column("risks", "comments")
