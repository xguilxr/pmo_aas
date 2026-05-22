"""ENH-103 — actors.auto_created + actors.verified.

Sprint 26 Bloque 0 lane C. Agrega flags al catálogo `actors` para
distinguir actores creados a mano (verified=True) de los que el matcher
de minutas crea on-the-fly cuando no encuentra match en
`project_participations` (auto_created=True, verified=False).

El owner verifica/promueve estos actores desde `/admin/actors` cuando
los reconoce.

Revision ID: 20260524_0072
Revises: 20260523_0071
Create Date: 2026-05-22 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260524_0072"
down_revision: str | None = "20260523_0071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("actors") as batch:
        batch.add_column(
            sa.Column(
                "auto_created",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch.add_column(
            sa.Column(
                "verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("actors") as batch:
        batch.drop_column("verified")
        batch.drop_column("auto_created")
