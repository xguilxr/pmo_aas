"""ENH-101 — projects.status_rag declarative field.

Adds a PM-declared RAG override column to projects. NULL means "no
declarative override; fall back to computed status". Values are
constrained to {'green','amber','red'}.

Revision ID: 20260522_0065
Revises: 20260510_0062
Create Date: 2026-05-22 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260522_0065"
down_revision: str | None = "20260510_0062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("status_rag", sa.String(length=8), nullable=True))
        batch.create_check_constraint(
            "ck_projects_status_rag",
            "status_rag IS NULL OR status_rag IN ('green','amber','red')",
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("ck_projects_status_rag", type_="check")
        batch.drop_column("status_rag")
