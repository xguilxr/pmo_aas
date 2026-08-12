"""Notification model (US-027, EP011).

Notificaciones in-app. Cada registro apunta a un user_id + tenant_id.
El `type` referencia un evento (ver docs/archive/epics/EP011-notifications.md tabla de
tipos). `entity_type` + `entity_id` permiten construir el link de
navegación al objeto origen.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_user_read", "user_id", "is_read"),
        Index("idx_notifications_tenant_time", "tenant_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(String(1000))

    # Objeto relacionado para construir el link al click.
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    link: Mapped[str | None] = mapped_column(String(500))

    # Metadata libre (para futuros tipos / email template vars).
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # US-028: trazabilidad del email (si aplica).
    email_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_provider_id: Mapped[str | None] = mapped_column(String(120))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
