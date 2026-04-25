"""US-082 — permission_change_requests.

Tabla nueva (no se reutiliza Solicitudes EP005, decisión owner):
permite al admin del tenant abrir un "ticket" al superadmin pidiendo
un cambio puntual de permiso para un usuario específico (ej. dar
`tasks:delete` al rol `user` para Daniel temporalmente).

El superadmin recibe notificación in-app + email. Al aprobar,
automáticamente se crea/actualiza el `tenant_role_permission_overrides`
correspondiente (US-073). Al rechazar requiere `decision_note`.

Estados: pending → approved | rejected | cancelled.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid


class PermissionChangeRequest(Base):
    __tablename__ = "permission_change_requests"
    __table_args__ = (
        Index("idx_pcr_tenant_status", "tenant_id", "status"),
        Index("idx_pcr_target_status", "target_user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    target_user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    module: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_grant: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    # pending | approved | rejected | cancelled
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )

    decided_by_superadmin_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
