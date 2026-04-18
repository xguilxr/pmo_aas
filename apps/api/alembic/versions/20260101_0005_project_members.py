"""project_members

Revision ID: 20260101_0005
Revises: 20260101_0004
Create Date: 2026-01-01 00:04:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260101_0005"
down_revision: Union[str, None] = "20260101_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_members",
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_in_project", sa.String(32), nullable=False, server_default="team"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )


def downgrade() -> None:
    op.drop_table("project_members")
