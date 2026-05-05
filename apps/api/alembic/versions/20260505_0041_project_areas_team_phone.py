"""project_areas.team_id + area_id + phone — US-091.

Revision ID: 20260505_0041
Revises: 20260505_0040
Create Date: 2026-05-05 22:10:00

Hace explícita la jerarquía Área → Equipo → Actor agregando FK self
nulleables y un campo `phone` para los actores.

- `team_id`  → FK a `project_areas.id` con type='team' (validación
  semántica vive en endpoint, no en DB; ondelete=SET NULL).
- `area_id`  → FK a `project_areas.id` con type='area' (idem).
- `phone`    → varchar(32), aplica sólo a actores pero no se restringe
  por tipo en DB para mantener flexibilidad.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260505_0041"
down_revision: str | None = "20260505_0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("project_areas") as batch_op:
        batch_op.add_column(sa.Column("team_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("area_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("phone", sa.String(length=32), nullable=True))
        batch_op.create_foreign_key(
            "fk_project_areas_team",
            "project_areas",
            ["team_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_project_areas_area",
            "project_areas",
            ["area_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_project_areas_team_id", ["team_id"])
        batch_op.create_index("ix_project_areas_area_id", ["area_id"])


def downgrade() -> None:
    with op.batch_alter_table("project_areas") as batch_op:
        batch_op.drop_index("ix_project_areas_area_id")
        batch_op.drop_index("ix_project_areas_team_id")
        batch_op.drop_constraint("fk_project_areas_area", type_="foreignkey")
        batch_op.drop_constraint("fk_project_areas_team", type_="foreignkey")
        batch_op.drop_column("phone")
        batch_op.drop_column("area_id")
        batch_op.drop_column("team_id")
