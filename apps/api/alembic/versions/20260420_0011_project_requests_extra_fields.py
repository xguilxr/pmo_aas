"""project_requests: campos adicionales (US-011, EP003)

Revision ID: 20260420_0011
Revises: 20260420_0010
Create Date: 2026-04-20 00:11:00

Agrega campos de solicitud según PENDING-ADDITIONS.md:
- requester_name / requester_email (defaults: user.full_name / user.email).
- sponsor_email (obligatorio).
- key_people / if_not_done / observations (opcionales).
- entregables (complementa/renombra scope — mantenemos ambos por
  compatibilidad, UI muestra `entregables` como etiqueta y sincroniza
  `scope` para código existente).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260420_0011"
down_revision: Union[str, None] = "20260420_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("project_requests") as batch:
        batch.add_column(sa.Column("requester_name", sa.String(200), nullable=True))
        batch.add_column(sa.Column("requester_email", sa.String(200), nullable=True))
        batch.add_column(sa.Column("sponsor_email", sa.String(200), nullable=True))
        batch.add_column(sa.Column("key_people", sa.String(5000), nullable=True))
        batch.add_column(sa.Column("if_not_done", sa.String(5000), nullable=True))
        batch.add_column(sa.Column("observations", sa.String(5000), nullable=True))
        batch.add_column(sa.Column("entregables", sa.String(5000), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("project_requests") as batch:
        batch.drop_column("entregables")
        batch.drop_column("observations")
        batch.drop_column("if_not_done")
        batch.drop_column("key_people")
        batch.drop_column("sponsor_email")
        batch.drop_column("requester_email")
        batch.drop_column("requester_name")
