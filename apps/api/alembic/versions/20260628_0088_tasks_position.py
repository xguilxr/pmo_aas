"""US-176 — tasks.position (orden manual del plan).

Sprint 35 (follow-up). Agrega `position` (Integer, nullable) a `tasks` para
permitir reordenar manualmente las filas del plan (drag por fila). Null = sin
reordenar → cae al orden natural por WBS (comportamiento actual). Cuando hay
posiciones, mandan sobre el WBS. Index en (project_id, position) para el orden.

Nullable, sin backfill: proyectos no reordenados quedan con position=NULL.

Revision ID: 20260628_0088
Revises: 20260628_0087
Create Date: 2026-06-28 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_0088"
down_revision: str | None = "20260628_0087"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("position", sa.Integer(), nullable=True))
    op.create_index(
        "ix_tasks_project_position", "tasks", ["project_id", "position"]
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_project_position", table_name="tasks")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("position")
