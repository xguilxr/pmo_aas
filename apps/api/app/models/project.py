from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("tenant_id", "folio", name="uq_projects_tenant_folio"),)

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    program_id: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("programs.id"))
    business_unit_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("business_units.id")
    )
    department_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("departments.id")
    )
    folio: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(5000))
    type: Mapped[str | None] = mapped_column(String(50))
    priority: Mapped[int | None] = mapped_column(SmallInteger)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, default="planning")
    pm_id: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    sponsor: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    actual_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    health_status: Mapped[str] = mapped_column(String(16), nullable=False, default="green")
    # US-180: salud única híbrida. `health_status` es EL semáforo.
    # `health_source`: 'auto' = lo mantiene el motor de reglas
    # (services/project_health.py); 'manual' = declarado por el PM (con
    # `health_reason`, obligatoria en amarillo/rojo) y el motor no lo
    # sobreescribe hasta volver a 'auto'. Reemplaza a `status_rag`
    # (ENH-101, absorbido en migración 0091).
    health_source: Mapped[str] = mapped_column(
        String(8), nullable=False, default="auto", server_default="auto"
    )
    health_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    request_id: Mapped[UUID | None] = mapped_column(String(36))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # US-084: dict por nombre de field con auditoría de edición manual.
    # Forma: {field_name: {edited_at: ISO, edited_by: user_id}}.
    manually_edited_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
