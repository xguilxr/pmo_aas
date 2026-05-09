"""ReportTemplate — ENH-085.

Plantillas de reportes guardadas a nivel **tenant** (cross-project),
distintas de `ai_report_templates` (por-proyecto, configuración wizard).
Esta tabla persiste el `html_content` final tweakeado por el PM (US-109)
para reusarlo como punto de partida en otros proyectos del mismo tenant.

Scope MVP:
- 1 plantilla = 1 nombre + 1 html_content + creator + flag is_shared.
- CRUD básico; el creador o admin del tenant pueden editar/borrar.
- `is_shared` controla si otros usuarios del tenant pueden usarla
  (true) o solo el creador (false).
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ReportTemplate(Base, TimestampMixin):
    __tablename__ = "report_templates"
    __table_args__ = (
        Index("ix_report_templates_tenant", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
