"""user_scope_assignments — US-167 (EP001)

Tabla de asignaciones de visibilidad positivas para usuarios PM.
Permite al admin asignar a un PM acceso a orgs, programas o proyectos
específicos. La visibilidad hereda hacia abajo (org → programas → proyectos).
Admin y pm_sr ignoran esta tabla — siempre ven todo el tenant.

Revision ID: 20260608_0085
Revises: 20260528_0084
Create Date: 2026-06-08 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260608_0085"
down_revision: str | None = "20260528_0084"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_scope_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope_type", sa.String(16), nullable=False),
        sa.Column("scope_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_user_scope_assignments_tenant_id",
        "user_scope_assignments",
        ["tenant_id"],
    )
    op.create_index(
        "ix_user_scope_assignments_user_id",
        "user_scope_assignments",
        ["user_id"],
    )
    op.create_index(
        "ix_user_scope_assignments_scope_id",
        "user_scope_assignments",
        ["scope_id"],
    )
    op.create_unique_constraint(
        "uq_user_scope_assignment",
        "user_scope_assignments",
        ["user_id", "scope_type", "scope_id"],
    )


def downgrade() -> None:
    op.drop_table("user_scope_assignments")
