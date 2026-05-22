"""ENH-097 — tasks.is_critical boolean (additive, criticality preserved).

Sprint 26 Bloque 1. Agrega un boolean explicito `is_critical` al modelo
`tasks` que vive en paralelo con el enum string `criticality`. La columna
nueva se backfilea desde el enum existente:

    is_critical = true  WHEN criticality IN ('high', 'critical')
    is_critical = false otherwise

Decisión owner 2026-05-22: NO drop de `criticality`. Ambas columnas
coexisten para el Report Builder (EP020). La eliminación del enum se
planificará en sprint posterior.

Revision ID: 20260522_0063
Revises: 20260510_0062
Create Date: 2026-05-22 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260522_0063"
down_revision: str | None = "20260510_0062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) add column nullable=True con default false, para no fallar en
    # rows existentes durante el ALTER en Postgres.
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(
            sa.Column(
                "is_critical",
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
            )
        )

    # 2) Backfill desde criticality. Usamos SQL plano para que funcione
    # tanto en Postgres como en SQLite (batch upgrade tests).
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE tasks SET is_critical = CASE "
            "WHEN criticality IN ('high', 'critical') THEN 1 ELSE 0 END"
        )
    )

    # 3) NOT NULL constraint.
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("is_critical", existing_type=sa.Boolean(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("is_critical")
