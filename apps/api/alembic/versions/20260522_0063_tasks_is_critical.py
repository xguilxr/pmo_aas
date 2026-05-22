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
    # Add column NOT NULL con server_default=false. Para filas existentes
    # el default cubre el INSERT implícito durante el ALTER (mismo patrón
    # que migración 0037 ``tasks.criticality``). Backfill posterior pisa
    # las filas que deberían quedar en true según el enum existente.
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(
            sa.Column(
                "is_critical",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )

    # Backfill desde el enum existente. Usamos boolean literals que
    # Postgres acepta (``true``/``false``) y que SQLite trata como
    # alias de 1/0 desde 3.23.
    op.execute(
        "UPDATE tasks SET is_critical = true "
        "WHERE criticality IN ('high', 'critical')"
    )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("is_critical")
