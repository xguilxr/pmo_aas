"""ENH-177 — issues.category (alineación de campos RAID).

Sprint 35 (follow-up post-análisis). Agrega `category` (String(100), nullable)
al modelo `issues`, en paralelo a `risks.category` ya existente, para que
acciones / incidencias / decisiones también puedan clasificarse por categoría.

Nullable sin backfill: los issues legacy quedan con category=NULL.

Revision ID: 20260628_0087
Revises: 20260628_0086
Create Date: 2026-06-28 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_0087"
down_revision: str | None = "20260628_0086"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("issues") as batch:
        batch.add_column(sa.Column("category", sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("issues") as batch:
        batch.drop_column("category")
