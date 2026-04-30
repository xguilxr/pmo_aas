"""stakeholders catalog — US-086.

Revision ID: 20260429_0035
Revises: 20260429_0034
Create Date: 2026-04-29 13:30:00

Catálogo de personas a nivel tenant/organización, reutilizable en
Charter (Sponsor / Líder Negocio / Líder Técnico) y Áreas. Decisión
owner: scope = tenant; opcionalmente asociado a organización.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260429_0035"
down_revision: str | None = "20260429_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stakeholders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("company", sa.String(length=200), nullable=True),
        sa.Column("job_title", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.String(length=5000), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index(
        "ix_stakeholders_tenant_id",
        "stakeholders",
        ["tenant_id"],
    )
    op.create_index(
        "ix_stakeholders_tenant_name",
        "stakeholders",
        ["tenant_id", "full_name"],
    )
    op.create_index(
        "ix_stakeholders_org_active",
        "stakeholders",
        ["organization_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_stakeholders_org_active", table_name="stakeholders")
    op.drop_index("ix_stakeholders_tenant_name", table_name="stakeholders")
    op.drop_index("ix_stakeholders_tenant_id", table_name="stakeholders")
    op.drop_table("stakeholders")
