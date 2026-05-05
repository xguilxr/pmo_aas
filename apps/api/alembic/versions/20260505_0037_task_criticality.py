"""tasks.criticality — ENH-051.

Revision ID: 20260505_0037
Revises: 20260505_0036
Create Date: 2026-05-05 21:00:00

Agrega campo `criticality` a `tasks` con valores `low|medium|high|critical`.
NOT NULL con server default `medium` para que las tareas existentes queden
con criticidad media. Postgres-compatible (string column con check
constraint en lugar de ENUM nativo para mantener portabilidad SQLite +
evitar costo de drop+create del enum si después se agregan valores).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260505_0037"
down_revision: str | None = "20260505_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CRITICALITY_VALUES = ("low", "medium", "high", "critical")


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "criticality",
                sa.String(length=16),
                nullable=False,
                server_default="medium",
            )
        )
        batch_op.create_check_constraint(
            "ck_tasks_criticality",
            f"criticality IN {CRITICALITY_VALUES!r}",
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("ck_tasks_criticality", type_="check")
        batch_op.drop_column("criticality")
