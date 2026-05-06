"""backfill outline_level from wbs — BUG-050.

Revision ID: 20260506_0043
Revises: 20260505_0042
Create Date: 2026-05-06 18:00:00

Pobla `tasks.outline_level` para filas con `wbs IS NOT NULL` y
`outline_level IS NULL`. La columna ya existe (migración 0039); este
backfill solo ejecuta el cómputo equivalente a
`compute_outline_level(wbs)`.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260506_0043"
down_revision: str | None = "20260505_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Cuenta segmentos no vacíos de wbs separados por '.'.
    # Postgres: array_length(string_to_array(wbs, '.'), 1) ya cuenta
    # segmentos pero no descarta vacíos por trailing dots; la limpieza
    # se hace en backend al persistir nuevas filas.
    op.execute(
        """
        UPDATE tasks
        SET outline_level = array_length(
            string_to_array(NULLIF(trim(both '.' from wbs), ''), '.'), 1
        )
        WHERE wbs IS NOT NULL
          AND wbs <> ''
          AND outline_level IS NULL
        """
    )


def downgrade() -> None:
    # No-op: el backfill es idempotente y no destructivo.
    pass
