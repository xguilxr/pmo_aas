"""BUG-068 — widen organizations.logo_url / client_logo_url to TEXT.

Permite almacenar data-URLs base64 de logos subidos directamente (PNG/JPG/
SVG/WEBP), además de URLs externas. Antes eran String(500), lo que truncaba
los data-URLs y rompía el guardado ("subir PNG no se guarda bien").

Revision ID: 20260526_0082
Revises: 20260526_0081

Create Date: 2026-05-26 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260526_0082"
down_revision: str | None = "20260526_0081"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("organizations") as batch:
        batch.alter_column(
            "logo_url",
            existing_type=sa.String(length=500),
            type_=sa.Text(),
            existing_nullable=True,
        )
        batch.alter_column(
            "client_logo_url",
            existing_type=sa.String(length=500),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("organizations") as batch:
        batch.alter_column(
            "logo_url",
            existing_type=sa.Text(),
            type_=sa.String(length=500),
            existing_nullable=True,
        )
        batch.alter_column(
            "client_logo_url",
            existing_type=sa.Text(),
            type_=sa.String(length=500),
            existing_nullable=True,
        )
