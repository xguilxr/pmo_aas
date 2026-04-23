"""password_reset_tokens — US-063

Revision ID: 20260424_0023
Revises: 20260423_0022
Create Date: 2026-04-24 09:00:00

Tabla nueva para el flujo de recuperación de contraseña por email. Sólo
guarda SHA-256 del token (`token_hash`); el plaintext vive únicamente
en el email enviado. Tokens de un solo uso (`used_at`), con TTL corto
(default 30 min — el backend fija `expires_at`).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260424_0023"
down_revision: Union[str, None] = "20260423_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "token_hash", sa.String(length=64), nullable=False, unique=True
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_prt_user_unused", "password_reset_tokens", ["user_id", "used_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_prt_user_unused", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
