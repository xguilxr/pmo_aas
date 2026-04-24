"""charter_docs_legacy — BUG-028

Revision ID: 20260424_0025
Revises: 20260424_0024
Create Date: 2026-04-24 12:00:00

Limpieza de `documents` con `category='charter'` cuyo `file_url`
apuntaba a endpoints legacy o placeholders:
- `example.local/...` (seed dummy que causó el DNS_PROBE reportado).
- `/api/v1/projects/*/charter/pdf` (endpoint HTML on-demand que se
  sustituyó por el .docx real subido al bucket).

Estrategia: set `file_url = NULL` + `mime_type = NULL` para los rows
afectados, para que el siguiente GET del charter (o el próximo PATCH
del editor) regenere el .docx vía `generate_charter_docx()` y repueble
esos campos con la URL real `/api/v1/documents/{id}/download`.

No borra los Document rows porque el UUID y la historia de auditoría
deben preservarse.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260424_0025"
down_revision: Union[str, None] = "20260424_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE documents
            SET file_url = NULL,
                mime_type = NULL
            WHERE category = 'charter'
              AND (
                file_url LIKE '%example.local%'
                OR file_url LIKE '%/charter/pdf'
              )
            """
        )
    )


def downgrade() -> None:
    # Irreversible por diseño: el placeholder legacy no debe re-aplicarse.
    pass
