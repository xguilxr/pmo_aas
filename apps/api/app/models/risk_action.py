"""RiskAction (US-107) — acciones de mitigación de un Riesgo, multi-responsable."""
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid

RISK_ACTION_STATUS = ("open", "in_progress", "done", "blocked")


class RiskAction(Base):
    __tablename__ = "risk_actions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','in_progress','done','blocked')",
            name="ck_risk_action_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    risk_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("risks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    short_desc: Mapped[str] = mapped_column(String(500), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RiskActionAssignee(Base):
    __tablename__ = "risk_action_assignees"

    risk_action_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("risk_actions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    actor_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("actors.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
