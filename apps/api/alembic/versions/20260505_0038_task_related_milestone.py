"""tasks.related_milestone_id — ENH-050.

Revision ID: 20260505_0038
Revises: 20260505_0037
Create Date: 2026-05-05 21:10:00

Agrega FK self a `tasks` para vincular una tarea a un hito relacionado.
Nullable + ondelete=SET NULL: si el hito se borra, las tareas vinculadas
quedan con `related_milestone_id=NULL` (no se borran en cascada).

La validación de que el target sea efectivamente un hito (`is_milestone
=true`) y que pertenezca al mismo proyecto vive en el endpoint, no en
constraint — Postgres no permite triggers de igualdad cross-row con FK.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260505_0038"
down_revision: str | None = "20260505_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column("related_milestone_id", sa.String(length=36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_tasks_related_milestone",
            "tasks",
            ["related_milestone_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_tasks_related_milestone_id",
            ["related_milestone_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_related_milestone_id")
        batch_op.drop_constraint("fk_tasks_related_milestone", type_="foreignkey")
        batch_op.drop_column("related_milestone_id")
