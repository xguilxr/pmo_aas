"""notifications table (US-027, EP011)

Revision ID: 20260421_0016
Revises: 20260420_0015
Create Date: 2026-04-21 16:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260421_0016"
down_revision: Union[str, None] = "20260420_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "email_sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_provider_id", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_notifications_user_read",
        "notifications",
        ["user_id", "is_read"],
    )
    op.create_index(
        "idx_notifications_tenant_time",
        "notifications",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_notifications_tenant_time", table_name="notifications")
    op.drop_index("idx_notifications_user_read", table_name="notifications")
    op.drop_table("notifications")
