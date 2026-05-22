"""meeting_minutes.origin — ENH-106.

Revision ID: 20260523_0068
Revises: 20260522_0067
Create Date: 2026-05-23 09:00:00

Agrega campo de auditoría `origin` a `meeting_minutes` con valores
`manual|transcript_ai|import_file|import_paste`. NOT NULL con server
default `manual`. Backfill: filas con `generated_by_ai=true` → `transcript_ai`,
resto → `manual`. Postgres-compatible (string + check constraint, igual
patrón que `tasks.criticality`).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260523_0068"
down_revision: str | None = "20260522_0067"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ORIGIN_VALUES = ("manual", "transcript_ai", "import_file", "import_paste")


def upgrade() -> None:
    with op.batch_alter_table("meeting_minutes") as batch_op:
        batch_op.add_column(
            sa.Column(
                "origin",
                sa.String(length=16),
                nullable=False,
                server_default="manual",
            )
        )
        batch_op.create_check_constraint(
            "ck_meeting_minutes_origin",
            f"origin IN {ORIGIN_VALUES!r}",
        )

    # Backfill: minutas generadas por IA → transcript_ai; resto queda en manual.
    op.execute(
        "UPDATE meeting_minutes SET origin = 'transcript_ai' "
        "WHERE generated_by_ai = TRUE"
    )


def downgrade() -> None:
    with op.batch_alter_table("meeting_minutes") as batch_op:
        batch_op.drop_constraint("ck_meeting_minutes_origin", type_="check")
        batch_op.drop_column("origin")
