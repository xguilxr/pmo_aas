"""ScheduledReport model (US-056, EP014 + EP011).

Programaciones automáticas de reportes: el owner define un proyecto,
un tipo de reporte (avance/seguimiento), una cadencia y destinatarios;
el worker dispara el reporte al PDF + lo envía vía Resend cuando se
vence el `next_run_at`.
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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ScheduledReport(Base, TimestampMixin):
    __tablename__ = "scheduled_reports"
    __table_args__ = (
        Index("idx_sched_reports_tenant_project", "tenant_id", "project_id"),
        Index("idx_sched_reports_due", "enabled", "next_run_at"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    cadence: Mapped[str] = mapped_column(String(16), nullable=False)
    recipients: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
