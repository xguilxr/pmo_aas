"""meeting_minutes.raid_suggestions (US-108).

Revision ID: 20260509_0058
Revises: 20260508_0057
Create Date: 2026-05-09 00:00:00

US-108: persistir sugerencias RAID detectadas por el LLM en la minuta
para que el PM pueda revisarlas y aprobarlas (✓), descartarlas (×) o
editarlas — sin perder estado entre sesiones (CA6).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260509_0058"
down_revision: str | None = "20260508_0057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "meeting_minutes",
        sa.Column(
            "raid_suggestions",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    # Drop el server_default tras backfill (no necesitamos defaults
    # implícitos en el modelo — el ORM ya lo maneja).
    op.alter_column("meeting_minutes", "raid_suggestions", server_default=None)


def downgrade() -> None:
    op.drop_column("meeting_minutes", "raid_suggestions")
