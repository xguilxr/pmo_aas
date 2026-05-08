"""project_artifacts — sistema de artefactos por proyecto (US-106 / EP018).

Revision ID: 20260508_0055
Revises: 20260508_0054
Create Date: 2026-05-08 19:00:00

US-106 introduce un catálogo estricto de artefactos vivos por proyecto.
Solo 4 tipos pueden existir: charter, plan, raid, organigrama.
El charter sigue viviendo en `project_charters` (tabla rica con secciones).
`project_artifacts` guarda metadata de archivos vivos para Plan/RAID/Organigrama
y referencia opcional al charter (id) para que el módulo Documentos exponga
los 4 tabs uniformemente.

UNIQUE (project_id, type) — solo 1 artefacto vivo por tipo (sin histórico).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260508_0055"
down_revision: str | None = "20260508_0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_artifacts",
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
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("source_format", sa.String(length=16), nullable=True),
        sa.Column("storage_url", sa.String(length=500), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "type", name="uq_artifact_project_type"),
        sa.CheckConstraint(
            "type IN ('charter','plan','raid','organigrama')",
            name="ck_artifact_type_whitelist",
        ),
    )
    op.create_index(
        "ix_project_artifacts_tenant_project",
        "project_artifacts",
        ["tenant_id", "project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_artifacts_tenant_project", table_name="project_artifacts"
    )
    op.drop_table("project_artifacts")
