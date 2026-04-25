"""organization_user_exclusions — US-078 (membership opt-out).

Revision ID: 20260425_0029
Revises: 20260425_0028
Create Date: 2026-04-25 01:00:00

Tabla de exclusiones user↔organización (modelo opt-out). Default:
todos los users del tenant tienen acceso a todas las orgs. Esta tabla
almacena solo las excepciones que el admin define en
`/admin/users/{id}`. El filtrado efectivo en queries queda como ENH
follow-up (ver issue de US-078).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260425_0029"
down_revision: str | None = "20260425_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_user_exclusions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organization_id",
            sa.String(length=36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "user_id", "organization_id", name="uq_org_user_excl_pair"
        ),
    )


def downgrade() -> None:
    op.drop_table("organization_user_exclusions")
