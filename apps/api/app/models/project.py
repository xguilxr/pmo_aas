from datetime import UTC, date, datetime
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

from app.core.magnitudes import Escala, Importe, Porcentaje
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
    priority: Mapped[Escala | None] = mapped_column(SmallInteger)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, default="planning")
    pm_id: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    sponsor: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    budget: Mapped[Importe | None] = mapped_column(Numeric(14, 2))
    actual_budget: Mapped[Importe | None] = mapped_column(Numeric(14, 2))
    progress: Mapped[Porcentaje] = mapped_column(SmallInteger, nullable=False, default=0)
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


class ProjectHealthEvaluation(Base):
    """US-191 — evaluación periódica de salud del PM: 5 dimensiones +
    la salud global (la "sexta"), con fecha de evaluación. Cada guardado
    es un registro histórico — la evolución de la salud en el tiempo.

    Convive con el motor automático (US-180): las dimensiones guardadas
    son la lectura del PM en esa fecha; el overall se aplica al semáforo
    del proyecto como declaración manual."""

    __tablename__ = "project_health_evaluations"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluated_at: Mapped[date] = mapped_column(Date, nullable=False)
    # Dimensiones (green|yellow|red); nullable = el PM no evaluó esa.
    schedule: Mapped[str | None] = mapped_column(String(8))
    budget: Mapped[str | None] = mapped_column(String(8))
    risks: Mapped[str | None] = mapped_column(String(8))
    decisions: Mapped[str | None] = mapped_column(String(8))
    resources: Mapped[str | None] = mapped_column(String(8))
    # La sexta: salud del proyecto como un todo (cuadro grande).
    overall: Mapped[str] = mapped_column(String(8), nullable=False)
    note: Mapped[str | None] = mapped_column(String(2000))
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
