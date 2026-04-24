"""organizations + programs

Revision ID: 20260101_0002
Revises: 20260101_0001
Create Date: 2026-01-01 00:01:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260101_0002"
down_revision: str | None = "20260101_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("reason_social", sa.String(200)),
        sa.Column("industry", sa.String(100)),
        sa.Column("country", sa.String(100)),
        sa.Column("contact_email", sa.String(200)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_org_tenant_name"),
    )
    op.create_index("ix_org_tenant_id", "organizations", ["tenant_id"])

    op.create_table(
        "programs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000)),
        sa.Column("strategic_alignment", sa.String(2000)),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_programs_tenant_id", "programs", ["tenant_id"])
    op.create_index("ix_programs_org_id", "programs", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_programs_org_id", table_name="programs")
    op.drop_index("ix_programs_tenant_id", table_name="programs")
    op.drop_table("programs")
    op.drop_index("ix_org_tenant_id", table_name="organizations")
    op.drop_table("organizations")
