"""ReportHistory model — US-092.

Cada vez que se genera un reporte (manual via endpoint o por scheduler)
se persiste una fila aquí. El binario del PDF puede archivarse en R2
(field `file_key`) en una iteración futura; por ahora el download
re-renderiza desde el `sections` del Report fuente.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid


class ReportHistory(Base):
    __tablename__ = "report_history"
    __table_args__ = (
        Index(
            "ix_report_history_project_generated",
            "project_id",
            "generated_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    generated_by_user_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    file_key: Mapped[str | None] = mapped_column(String(500))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    scheduled_report_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("scheduled_reports.id", ondelete="SET NULL")
    )
    # Pointer al Report fuente — permite re-renderizar el PDF desde el
    # snapshot persistido en `reports.sections`.
    source_report_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="SET NULL")
    )
