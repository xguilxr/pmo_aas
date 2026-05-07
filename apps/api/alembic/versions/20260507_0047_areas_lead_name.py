"""areas.lead_name (texto libre) — US-097 fix.

Revision ID: 20260507_0047
Revises: 20260507_0046
Create Date: 2026-05-07 03:00:00

Owner clarificó (2026-05-07): el líder de un Área no necesariamente
es un user del tenant — puede ser un actor/recurso. Agregamos campo
texto libre `lead_name` para evitar forzar una FK a users.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260507_0047"
down_revision: str | None = "20260507_0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("areas") as batch_op:
        batch_op.add_column(sa.Column("lead_name", sa.String(length=200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("areas") as batch_op:
        batch_op.drop_column("lead_name")
