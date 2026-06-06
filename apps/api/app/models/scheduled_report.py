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
    SmallInteger,
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
    # ENH-046: cadence acepta "daily" | "weekly" | "monthly" | "once".
    cadence: Mapped[str] = mapped_column(String(16), nullable=False)
    # ENH-046: día de la semana (0=lunes … 6=domingo) — sólo usado por
    # cadence="weekly". NULL para los demás casos.
    day_of_week: Mapped[int | None] = mapped_column(SmallInteger)
    # ENH-046: hora del día (0-23, en UTC). Usado por daily/weekly/monthly.
    hour_of_day: Mapped[int | None] = mapped_column(SmallInteger)
    # ENH-056: día del mes (1-31). Sólo aplica a cadence="monthly". Si el
    # mes destino no tiene ese día, se clampa al último del mes.
    day_of_month: Mapped[int | None] = mapped_column(SmallInteger)
    # ENH-046: timestamp de ejecución one-time (cadence="once").
    run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recipients: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    # US-131 — cuando `report_type='custom'`, apunta a la plantilla del
    # Report Builder (US-122) que el worker renderiza con el engine
    # US-123 antes de enviar por correo.
    report_builder_template_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("report_builder_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
