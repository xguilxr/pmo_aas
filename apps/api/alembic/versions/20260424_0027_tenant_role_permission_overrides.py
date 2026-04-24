"""tenant_role_permission_overrides — US-073 + DEC-021

Revision ID: 20260424_0027
Revises: 20260424_0026
Create Date: 2026-04-24 19:00:00

Owner pidió (post BUG-031) un mecanismo para que el superadmin
pueda ajustar permisos de un tenant específico sin tocar el
mapping estático de DEC-020. La estrategia (DEC-021):

- El mapping de `app/core/permissions.py` sigue siendo la base.
- Esta tabla guarda overrides per (tenant, role_type, module, action)
  con `granted` boolean. `True` agrega; `False` quita.
- Solo superadmin puede crear overrides (audit log obligatorio
  con `reason`).
- `CurrentUser.has()` aplica mapping estático + overrides del
  tenant actual.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260424_0027"
down_revision: str | None = "20260424_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenant_role_permission_overrides",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("role_type", sa.String(length=16), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "updated_by_user_id", sa.String(length=36), nullable=True
        ),
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
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "role_type",
            "module",
            "action",
            name="uq_trpo_tenant_role_module_action",
        ),
    )
    op.create_index(
        "ix_trpo_tenant_role",
        "tenant_role_permission_overrides",
        ["tenant_id", "role_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_trpo_tenant_role", table_name="tenant_role_permission_overrides"
    )
    op.drop_table("tenant_role_permission_overrides")
