"""US-177 — renombra la sección de reporte S-17 "Retrasadas" → "Atrasadas".

Mantiene el catálogo del Report Builder consistente con el renombre de la
terminología (Retrasada → Atrasada) en toda la plataforma.

Revision ID: 20260629_0090
Revises: 20260629_0089
Create Date: 2026-06-29 00:00:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260629_0090"
down_revision: str | None = "20260629_0089"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # report_sections usa `code` (slug "S-17"), no `folio`.
    op.execute(
        "UPDATE report_sections SET name = 'Atrasadas' "
        "WHERE code = 'S-17' AND name = 'Retrasadas'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE report_sections SET name = 'Retrasadas' "
        "WHERE code = 'S-17' AND name = 'Atrasadas'"
    )
