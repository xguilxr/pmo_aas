"""permission_change_requests — US-082.

Revision ID: 20260425_0031
Revises: 20260425_0030
Create Date: 2026-04-25 13:00:00

Tabla nueva (decisión owner: NO se reutiliza Solicitudes EP005):
permite al admin del tenant abrir un "ticket" al superadmin pidiendo
un cambio puntual de permiso para un usuario específico.

Cuando el superadmin aprueba, se crea automáticamente el override
correspondiente en `tenant_role_permission_overrides` (US-073).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260425_0031"
down_revision: str | None = "20260425_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "permission_change_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column(
            "requested_by_user_id", sa.String(length=36), nullable=False
        ),
        sa.Column("target_user_id", sa.String(length=36), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column(
            "requested_grant",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "decided_by_superadmin_id", sa.String(length=36), nullable=True
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.id"]
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["users.id"]
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_superadmin_id"], ["users.id"]
        ),
    )
    op.create_index(
        "idx_pcr_tenant_status",
        "permission_change_requests",
        ["tenant_id", "status"],
    )
    op.create_index(
        "idx_pcr_target_status",
        "permission_change_requests",
        ["target_user_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_pcr_target_status", table_name="permission_change_requests"
    )
    op.drop_index(
        "idx_pcr_tenant_status", table_name="permission_change_requests"
    )
    op.drop_table("permission_change_requests")
