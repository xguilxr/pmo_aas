"""meeting_minutes.origin — agrega 'minute_ai' al CHECK constraint (US-143).

Revision ID: 20260523_0075
Revises: 20260525_0074
Create Date: 2026-05-23 18:00:00

US-143 introduce un nuevo flujo de generación de minuta: el usuario sube
una minuta YA redactada y la IA la normaliza al modelo canónico. Las
minutas creadas por este path llevan `origin='minute_ai'` para
diferenciarlas de `transcript_ai` en auditoría. Extendemos el CHECK
constraint para admitir el nuevo valor.

Misma estructura que ENH-106 (migración 0068).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260523_0075"
down_revision: str | None = "20260525_0074"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_VALUES = ("manual", "transcript_ai", "import_file", "import_paste")
NEW_VALUES = (
    "manual",
    "transcript_ai",
    "minute_ai",
    "import_file",
    "import_paste",
)


def upgrade() -> None:
    with op.batch_alter_table("meeting_minutes") as batch_op:
        batch_op.drop_constraint("ck_meeting_minutes_origin", type_="check")
        batch_op.create_check_constraint(
            "ck_meeting_minutes_origin",
            f"origin IN {NEW_VALUES!r}",
        )


def downgrade() -> None:
    with op.batch_alter_table("meeting_minutes") as batch_op:
        batch_op.drop_constraint("ck_meeting_minutes_origin", type_="check")
        batch_op.create_check_constraint(
            "ck_meeting_minutes_origin",
            f"origin IN {OLD_VALUES!r}",
        )
