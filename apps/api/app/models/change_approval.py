"""ChangeApprover + ApprovalToken — EP019 (US-112 + US-113).

`ChangeApprover`: registro multi-actor de aprobadores en un Change
Request. Cada fila tiene rol (primary/secondary) y status individual.

`ApprovalToken`: tokens JWT firmados que habilitan la landing pública
de aprobar/rechazar. Almacenamos el hash, no el JWT en claro.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ChangeApprover(Base, TimestampMixin):
    __tablename__ = "change_approvers"
    __table_args__ = (
        UniqueConstraint(
            "change_id", "actor_id", name="uq_change_approvers_change_actor"
        ),
        Index("ix_change_approvers_change", "change_id"),
        Index("ix_change_approvers_tenant", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    change_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("change_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("actors.id", ondelete="CASCADE"),
        nullable=False,
    )
    # primary | secondary
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="primary")
    # pending | approved | rejected
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(String(2000))


class ApprovalToken(Base):
    __tablename__ = "approval_tokens"
    __table_args__ = (
        Index("ix_approval_tokens_change", "change_id"),
        Index("ix_approval_tokens_tenant", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    change_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("change_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("actors.id", ondelete="CASCADE"),
        nullable=False,
    )
    # SHA256 hex del JWT — el JWT en claro solo viaja por email.
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # approve | reject (cuando se consume)
    action_taken: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
