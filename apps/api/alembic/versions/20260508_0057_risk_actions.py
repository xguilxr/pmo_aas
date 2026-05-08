"""risk_actions + risk_action_assignees (US-107).

Revision ID: 20260508_0057
Revises: 20260508_0056
Create Date: 2026-05-08 21:00:00

US-107: acciones de mitigación trackeables, derivadas de la estrategia
texto-libre del Riesgo. N:N con Actores (multi-responsable). Status
independiente del Riesgo. Cascade desde Risk.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260508_0057"
down_revision: str | None = "20260508_0056"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_actions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), nullable=False, index=True
        ),
        sa.Column(
            "risk_id",
            sa.String(length=36),
            sa.ForeignKey("risks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("short_desc", sa.String(length=500), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('open','in_progress','done','blocked')",
            name="ck_risk_action_status",
        ),
    )

    op.create_table(
        "risk_action_assignees",
        sa.Column(
            "risk_action_id",
            sa.String(length=36),
            sa.ForeignKey("risk_actions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "actor_id",
            sa.String(length=36),
            sa.ForeignKey("actors.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("risk_action_assignees")
    op.drop_table("risk_actions")
