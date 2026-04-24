"""project_requests + folio_sequences

Revision ID: 20260101_0003
Revises: 20260101_0002
Create Date: 2026-01-01 00:02:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260101_0003"
down_revision: str | None = "20260101_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("folio", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(5000), nullable=False),
        sa.Column("objective", sa.String(5000), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("business_unit", sa.String(200), nullable=False),
        sa.Column("department", sa.String(200), nullable=False),
        sa.Column("sponsor", sa.String(200), nullable=False),
        sa.Column("benefits", sa.String(5000), nullable=False),
        sa.Column("budget", sa.Numeric(14, 2), nullable=False),
        sa.Column("scope", sa.String(5000), nullable=False),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="in_review"),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_comment", sa.String(5000)),
        sa.Column("attachments", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("project_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "folio", name="uq_req_tenant_folio"),
    )
    op.create_index("ix_req_tenant_id", "project_requests", ["tenant_id"])

    op.create_table(
        "folio_sequences",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("last_number", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("tenant_id", "prefix", "year", name="uq_folio_tpy"),
    )


def downgrade() -> None:
    op.drop_table("folio_sequences")
    op.drop_index("ix_req_tenant_id", table_name="project_requests")
    op.drop_table("project_requests")
