"""projects.manually_edited_fields — US-084.

Revision ID: 20260429_0034
Revises: 20260429_0033
Create Date: 2026-04-29 13:00:00

Permite que el PM marque agregados (start_date, end_date, budget,
progress) como "editados manualmente". Los importadores MPP/XLSX
respetan este flag y no sobrescriben los valores manuales.

Estructura de la columna:
- JSON dict: { field: { "edited_at": ISO, "edited_by": user_id } }
- Si un campo no aparece en el dict, sigue libre para auto-cálculo
  o sobrescritura por importador.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260429_0034"
down_revision: str | None = "20260429_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "manually_edited_fields",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "manually_edited_fields")
