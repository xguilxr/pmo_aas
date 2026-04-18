"""project modules: risks, issues, change_requests, documents, lessons, meeting_minutes

Revision ID: 20260101_0006
Revises: 20260101_0005
Create Date: 2026-01-01 00:05:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260101_0006"
down_revision: Union[str, None] = "20260101_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_BASE_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("tenant_id", sa.String(36), nullable=False),
    sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    sa.Column("folio", sa.String(32), nullable=False),
    sa.Column("title", sa.String(200), nullable=False),
    sa.Column("description", sa.String(5000)),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")),
    sa.Column("deleted_at", sa.DateTime(timezone=True)),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
]


def upgrade() -> None:
    op.create_table(
        "risks",
        *_BASE_COLS,
        sa.Column("category", sa.String(100)),
        sa.Column("probability", sa.SmallInteger),
        sa.Column("impact", sa.SmallInteger),
        sa.Column("severity", sa.Integer),
        sa.Column("mitigation_strategy", sa.String(5000)),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("identified_at", sa.Date),
        sa.Column("due_date", sa.Date),
        sa.Column("closure_note", sa.String(5000)),
        sa.UniqueConstraint("tenant_id", "folio", name="uq_risks_tenant_folio"),
    )
    op.create_index("ix_risks_project_id", "risks", ["project_id"])

    op.create_table(
        "issues",
        *_BASE_COLS,
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("priority", sa.SmallInteger),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_date", sa.Date),
        sa.Column("resolution", sa.String(5000)),
        sa.Column("comments", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.UniqueConstraint("tenant_id", "folio", name="uq_issues_tenant_folio"),
    )
    op.create_index("ix_issues_project_id", "issues", ["project_id"])

    op.create_table(
        "change_requests",
        *_BASE_COLS,
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("impact", sa.String(5000)),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", "folio", name="uq_chg_tenant_folio"),
    )
    op.create_index("ix_chg_project_id", "change_requests", ["project_id"])

    op.create_table(
        "documents",
        *_BASE_COLS,
        sa.Column("category", sa.String(32)),
        sa.Column("file_url", sa.String(500)),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("size_bytes", sa.Integer),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("uploaded_at", sa.DateTime(timezone=True)),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("tenant_id", "folio", name="uq_doc_tenant_folio"),
    )
    op.create_index("ix_doc_project_id", "documents", ["project_id"])

    op.create_table(
        "lessons",
        *_BASE_COLS,
        sa.Column("category", sa.String(32)),
        sa.Column("phase", sa.String(32)),
        sa.Column("recommendation", sa.String(5000)),
        sa.Column("tags", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.UniqueConstraint("tenant_id", "folio", name="uq_lesson_tenant_folio"),
    )
    op.create_index("ix_lesson_project_id", "lessons", ["project_id"])

    op.create_table(
        "meeting_minutes",
        *_BASE_COLS,
        sa.Column("meeting_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("participants", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("topics", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("agreements", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("next_meeting_date", sa.Date),
        sa.Column("attachments", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("transcript_file_id", sa.String(36)),
        sa.Column("generated_by_ai", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("tenant_id", "folio", name="uq_min_tenant_folio"),
    )
    op.create_index("ix_min_project_id", "meeting_minutes", ["project_id"])


def downgrade() -> None:
    for t in ["meeting_minutes", "lessons", "documents", "change_requests", "issues", "risks"]:
        op.drop_table(t)
