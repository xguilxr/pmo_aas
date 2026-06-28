"""US-171 — tasks.closed_at (fecha de cierre real, editable).

Sprint 35. Agrega `closed_at` (Date, nullable) al modelo `tasks`. Es la
fecha real en que se cerró/completó la actividad, editable por el PM. La
lógica de atraso para tareas completadas pasa a comparar `closed_at` contra
`end_date` (planeada): si `closed_at > end_date` la actividad se marca como
"Retrasada" (cerrada con retraso). Para tareas NO completadas se mantiene la
regla previa (`end_date < hoy`).

Nullable sin backfill: las tareas completadas legacy sin `closed_at` no se
consideran retrasadas (no hay dato para afirmarlo). El endpoint auto-setea
`closed_at = hoy` cuando una tarea pasa a `completed` sin fecha provista.

Revision ID: 20260628_0086
Revises: 20260608_0085
Create Date: 2026-06-28 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_0086"
down_revision: str | None = "20260608_0085"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("closed_at", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("closed_at")
