"""tasks.area_id repointed to project_areas — fix bug US-098 rework.

Revision ID: 20260507_0046
Revises: 20260507_0045
Create Date: 2026-05-07 02:30:00

Owner reportó (2026-05-07): las áreas que se asignan a tareas deben
ser las registradas en el proyecto (`project_areas`, US-091), no el
catálogo tenant (`areas`, US-097).

La migración 0045 creó `tasks.area_id` apuntando al catálogo tenant.
Esta migración:
1. Limpia los valores existentes (la columna recién se introdujo y
   la UI estaba mostrando un select vacío — no hay data productiva
   que migrar).
2. Cambia el FK target de `areas` → `project_areas`.

El catálogo tenant (`areas/teams/actors`) sigue vivo para
`/admin/areas` (admin panel + reasignación masiva US-099).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260507_0046"
down_revision: str | None = "20260507_0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop old FK + index, clear stale values, recreate FK to project_areas.
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_area_id")
        batch_op.drop_constraint("fk_tasks_area", type_="foreignkey")
    op.execute("UPDATE tasks SET area_id = NULL")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.create_foreign_key(
            "fk_tasks_project_area",
            "project_areas",
            ["area_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_tasks_area_id", ["area_id"])


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_area_id")
        batch_op.drop_constraint("fk_tasks_project_area", type_="foreignkey")
    op.execute("UPDATE tasks SET area_id = NULL")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.create_foreign_key(
            "fk_tasks_area",
            "areas",
            ["area_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_tasks_area_id", ["area_id"])
