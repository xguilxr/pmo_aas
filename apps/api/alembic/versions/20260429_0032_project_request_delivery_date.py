"""project_requests.delivery_constraint_date — ENH-038.

Revision ID: 20260429_0032
Revises: 20260425_0031
Create Date: 2026-04-29 12:00:00

Agrega columna `delivery_constraint_date DATE NULL` a `project_requests`
para permitir capturar la fecha de restricción de entrega (opcional)
solicitada por el feedback DRC.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260429_0032"
down_revision: str | None = "20260425_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_requests",
        sa.Column("delivery_constraint_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_requests", "delivery_constraint_date")
