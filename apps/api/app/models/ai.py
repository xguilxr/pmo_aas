from datetime import date, datetime
from uuid import UUID

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class AIJob(Base, TimestampMixin):
    __tablename__ = "ai_jobs"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[UUID | None] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(64), nullable=False)  # minute_from_transcript|progress_report
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    input: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output: Mapped[dict | None] = mapped_column(JSON)
    model_used: Mapped[str | None] = mapped_column(String(100))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(String(2000))
    requested_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # US-057: qué provider atendió el request, para el dashboard de uso Groq
    # y el panel de status por tenant del superadmin.
    provider: Mapped[str | None] = mapped_column(String(32), index=True)


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sections: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    period: Mapped[str | None] = mapped_column(String(16))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recipients: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    generated_by_ai: Mapped[bool] = mapped_column(default=False)
    generator: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    cut_off_date: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    # US-109/ENH-089: HTML final del reporte (con tweaks aplicados via
    # LLM). Es el formato primario de exportación; PDF/TXT son
    # adecuaciones server-side.
    html_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
