"""US-180 — Salud única híbrida: unifica health_status + status_rag.

Agrega ``projects.health_source`` ('auto'|'manual') y
``projects.health_reason``. Absorbe el RAG declarado (ENH-101): donde
``status_rag`` estaba seteado, pasa a ser el semáforo efectivo
(``health_status``, amber→yellow) con ``health_source='manual'``. Dropea
``status_rag`` y su check constraint.

Revision ID: 20260708_0091
Revises: 20260629_0090
Create Date: 2026-07-08 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260708_0091"
down_revision: str | None = "20260629_0090"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(
            sa.Column("health_source", sa.String(length=8), nullable=False, server_default="auto")
        )
        batch.add_column(sa.Column("health_reason", sa.String(length=2000), nullable=True))
        batch.create_check_constraint(
            "ck_projects_health_source", "health_source IN ('auto','manual')"
        )

    op.execute(
        "UPDATE projects SET "
        "health_status = CASE status_rag WHEN 'amber' THEN 'yellow' ELSE status_rag END, "
        "health_source = 'manual' "
        "WHERE status_rag IS NOT NULL"
    )

    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("ck_projects_status_rag", type_="check")
        batch.drop_column("status_rag")


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("status_rag", sa.String(length=8), nullable=True))
        batch.create_check_constraint(
            "ck_projects_status_rag",
            "status_rag IS NULL OR status_rag IN ('green','amber','red')",
        )

    # Lossy: solo los overrides manuales regresan a status_rag.
    op.execute(
        "UPDATE projects SET "
        "status_rag = CASE health_status WHEN 'yellow' THEN 'amber' ELSE health_status END "
        "WHERE health_source = 'manual'"
    )

    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("ck_projects_health_source", type_="check")
        batch.drop_column("health_reason")
        batch.drop_column("health_source")
