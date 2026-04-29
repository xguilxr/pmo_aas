"""project_requests.budget → NULL — ENH-040.

Revision ID: 20260429_0033
Revises: 20260429_0032
Create Date: 2026-04-29 12:30:00

Hace `budget` opcional. Hasta ahora era NOT NULL Numeric(14,2). El
solicitante puede no tener estimado al pedir. Si no se llena, se
muestra el campo oculto en el detalle (no aparece como $0).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260429_0033"
down_revision: str | None = "20260429_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("project_requests") as batch_op:
        batch_op.alter_column("budget", existing_type=sa.Numeric(14, 2), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("project_requests") as batch_op:
        batch_op.alter_column("budget", existing_type=sa.Numeric(14, 2), nullable=False)
