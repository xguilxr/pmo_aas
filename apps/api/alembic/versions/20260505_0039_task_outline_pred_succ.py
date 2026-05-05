"""tasks.outline_level + predecessors + successors — US-090.

Revision ID: 20260505_0039
Revises: 20260505_0038
Create Date: 2026-05-05 21:25:00

Agrega columnas tipo MS Project:
- `outline_level` (smallint nullable, computado por backend desde wbs).
- `predecessors` (JSON array de strings con wbs_code).
- `successors` (JSON array de strings con wbs_code, auto-managed:
  recomputado en backend desde predecessors de otras tareas del mismo
  proyecto).

`duration_days` ya existía (US-067) como Integer; el clamp de max 21
días vive en el endpoint, no en constraint (Postgres no soporta CHECK
con expresión cross-column compleja para este caso).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260505_0039"
down_revision: str | None = "20260505_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("outline_level", sa.SmallInteger(), nullable=True))
        batch_op.add_column(sa.Column("predecessors", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("successors", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("successors")
        batch_op.drop_column("predecessors")
        batch_op.drop_column("outline_level")
