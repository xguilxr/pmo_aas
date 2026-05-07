"""AIReportTemplate (ENH-080).

Plantillas reusables para reportes generados con IA. El usuario
configura un wizard (base, secciones, free_notes, filtros) y lo guarda
con nombre; luego puede regenerar el reporte con esa misma config.

Scope MVP: una plantilla pertenece a un proyecto y a un tenant. No se
comparten entre proyectos. Solo create/list/delete (no edit en MVP).
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class AIReportTemplate(Base, TimestampMixin):
    __tablename__ = "ai_report_templates"
    __table_args__ = (
        Index("ix_ai_report_templates_tenant_project", "tenant_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # base: "avance" | "seguimiento" | "custom"
    base: Mapped[str] = mapped_column(String(16), nullable=False, default="avance")
    # config = {include_kpis, include_tasks, include_raid, include_milestones,
    # free_notes, filters: {area_ids, assignee_actor_ids, criticalities,
    # statuses, severities, date_from, date_to}}
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
