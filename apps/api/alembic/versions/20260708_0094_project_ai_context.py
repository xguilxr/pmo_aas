"""US-185 — Memoria de proyecto para IA (project_ai_contexts).

Tabla 1:1 con projects: contexto curado por el PM (context_md), reglas
permanentes de generación (instructions_md) y resumen acumulativo
mantenido por IA (auto_summary_md). Se inyecta como bloque
<CONTEXTO_DEL_PROYECTO> en minutas y reportes generados con IA.

Revision ID: 20260708_0094
Revises: 20260708_0093
Create Date: 2026-07-08 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260708_0094"
down_revision: str | None = "20260708_0093"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_ai_contexts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("context_md", sa.Text(), nullable=True),
        sa.Column("instructions_md", sa.Text(), nullable=True),
        sa.Column("auto_summary_md", sa.Text(), nullable=True),
        sa.Column("auto_summary_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", name="uq_project_ai_context_project"),
    )
    op.create_index(
        "ix_project_ai_contexts_tenant", "project_ai_contexts", ["tenant_id"]
    )
    op.create_index(
        "ix_project_ai_contexts_project", "project_ai_contexts", ["project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_project_ai_contexts_project", table_name="project_ai_contexts")
    op.drop_index("ix_project_ai_contexts_tenant", table_name="project_ai_contexts")
    op.drop_table("project_ai_contexts")
