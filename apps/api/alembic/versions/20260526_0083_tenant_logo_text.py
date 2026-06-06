"""BUG-068 — widen tenants.logo_url to TEXT (data-URL base64).

El logo del tenant ahora se guarda como data-URL base64 en DB (antes a disco
efímero servido por un endpoint autenticado que un <img> no podía consumir →
401). Para que el data-URL quepa, la columna pasa de String(500) a Text.

Revision ID: 20260526_0083
Revises: 20260526_0082

Create Date: 2026-05-26 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260526_0083"
down_revision: str | None = "20260526_0082"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tenants") as batch:
        batch.alter_column(
            "logo_url",
            existing_type=sa.String(length=500),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("tenants") as batch:
        batch.alter_column(
            "logo_url",
            existing_type=sa.Text(),
            type_=sa.String(length=500),
            existing_nullable=True,
        )
