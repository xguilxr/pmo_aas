"""ScheduledMinute model (ENH-107, EP014).

Programaciones automáticas de envío de minutas. Símil
`ScheduledReport` (US-056): el owner define un proyecto, una cadencia
y destinatarios; el worker selecciona la última minuta del periodo y
la envía como PDF vía Resend cuando se vence el `next_run_at`. Si no
hay minuta en el periodo, envía un email fallback ("Sin minuta
registrada en este periodo").
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ScheduledMinute(Base, TimestampMixin):
    __tablename__ = "scheduled_minutes"
    __table_args__ = (
        Index("idx_sched_minutes_tenant_project", "tenant_id", "project_id"),
        Index("idx_sched_minutes_due", "enabled", "next_run_at"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    # Cadencia acepta "daily" | "weekly" | "monthly" | "once" (mismo set
    # que ScheduledReport — reusamos compute_next_run del servicio
    # `scheduled_reports`).
    cadence: Mapped[str] = mapped_column(String(16), nullable=False)
    # Día de la semana (0=lunes … 6=domingo). Sólo aplica weekly.
    day_of_week: Mapped[int | None] = mapped_column(SmallInteger)
    # Hora del día (0-23, UTC). Aplica daily/weekly/monthly.
    hour_of_day: Mapped[int | None] = mapped_column(SmallInteger)
    # Día del mes (1-31). Sólo monthly; se clampa al último día del mes.
    day_of_month: Mapped[int | None] = mapped_column(SmallInteger)
    # Timestamp para cadence=once.
    run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Plantilla opcional (no validada como FK por ahora — el sistema de
    # plantillas de minutas vive en otro flujo).
    template_id: Mapped[UUID | None] = mapped_column(String(36))
    recipients: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
