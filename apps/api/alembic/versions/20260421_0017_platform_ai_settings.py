"""platform_ai_settings table (US-054, EP008/EP010)

Revision ID: 20260421_0017
Revises: 20260421_0016
Create Date: 2026-04-21 21:45:00

Tabla singleton con defaults de AI a nivel de plataforma. Editable solo
por superadmin. El provider la consulta entre el override del tenant y
las env vars para decidir base_url/model/timeout.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260421_0017"
down_revision: Union[str, None] = "20260421_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_ai_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ai_mode", sa.String(length=16), nullable=True),
        sa.Column("ollama_base_url", sa.String(length=500), nullable=True),
        sa.Column("ollama_model", sa.String(length=100), nullable=True),
        sa.Column("ai_timeout_sec", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Seed singleton. Todos los campos NULL = "no hay override de
    # plataforma; usa el env var". El superadmin los llena desde UI.
    op.execute(
        "INSERT INTO platform_ai_settings (id) VALUES ('default')"
    )


def downgrade() -> None:
    op.drop_table("platform_ai_settings")
