"""report_builder_templates: owner_id + project_id + visibility (US-126).

Revision ID: 20260525_0073
Revises: 20260524_0072
Create Date: 2026-05-25 09:00:00

US-126 — habilita plantillas custom del Report Builder con visibility
controlada:

- `private`  → sólo el `owner_id`.
- `project`  → todos los miembros del `project_id`.
- `tenant`   → reservado: todos los users del tenant (no usado en v1.0,
               se contempla para "Publicar al tenant" futuro).

Seeds (`is_seed=True`, `tenant_id=NULL`) continúan visibles para todos.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260525_0073"
down_revision: str | None = "20260524_0072"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("report_builder_templates") as batch:
        batch.add_column(
            sa.Column(
                "owner_id",
                sa.String(length=36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "project_id",
                sa.String(length=36),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "visibility",
                sa.String(length=16),
                nullable=False,
                server_default="private",
            )
        )
    op.create_index(
        "ix_report_builder_templates_owner",
        "report_builder_templates",
        ["owner_id"],
    )
    op.create_index(
        "ix_report_builder_templates_project",
        "report_builder_templates",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_builder_templates_project",
        table_name="report_builder_templates",
    )
    op.drop_index(
        "ix_report_builder_templates_owner",
        table_name="report_builder_templates",
    )
    with op.batch_alter_table("report_builder_templates") as batch:
        batch.drop_column("visibility")
        batch.drop_column("project_id")
        batch.drop_column("owner_id")
