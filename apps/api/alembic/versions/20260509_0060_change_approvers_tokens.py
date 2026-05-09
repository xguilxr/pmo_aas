"""change_approvers + approval_tokens (US-112 + US-113).

Revision ID: 20260509_0060
Revises: 20260509_0059
Create Date: 2026-05-09 02:00:00

US-112: registro multi-actor de aprobadores en `change_requests`. Cada
fila tiene rol (primary/secondary) y status individual.

US-113: tokens JWT firmados (almacenamos solo el hash) que habilitan
landing pública aprobar/rechazar sin auth.

También extiende `change_requests.status` ENUM-de-facto con dos valores
nuevos (`draft`, `pending_approval`) — al ser un String, no requiere
ALTER TYPE.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260509_0060"
down_revision: str | None = "20260509_0059"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # US-112: change_approvers
    op.create_table(
        "change_approvers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), nullable=False, index=True
        ),
        sa.Column(
            "change_id",
            sa.String(length=36),
            sa.ForeignKey("change_requests.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "actor_id",
            sa.String(length=36),
            sa.ForeignKey("actors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=16),
            nullable=False,
            server_default="primary",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "change_id", "actor_id", name="uq_change_approvers_change_actor"
        ),
    )
    op.alter_column("change_approvers", "role", server_default=None)
    op.alter_column("change_approvers", "status", server_default=None)

    # US-113: approval_tokens (almacenamos el hash, no el JWT en claro)
    op.create_table(
        "approval_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), nullable=False, index=True
        ),
        sa.Column(
            "change_id",
            sa.String(length=36),
            sa.ForeignKey("change_requests.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "actor_id",
            sa.String(length=36),
            sa.ForeignKey("actors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "token_hash", sa.String(length=128), nullable=False, unique=True
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "action_taken", sa.String(length=16), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("approval_tokens")
    op.drop_table("change_approvers")
