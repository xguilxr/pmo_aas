from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.magnitudes import Escala
from app.db.base import Base, new_uuid


class ProjectCharter(Base):
    """Charter fundacional del proyecto (US-012, DEC-008).

    Sección 4 (Gestión) se deriva al vuelo desde `projects` en el endpoint
    GET; esta tabla guarda únicamente las secciones 1-3 estructuradas.
    """

    __tablename__ = "project_charters"
    __table_args__ = (UniqueConstraint("project_id", name="uq_charter_project"),)

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("project_requests.id")
    )

    # Sección 1: Info General
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(5000))
    organization_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("organizations.id")
    )
    business_unit_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("business_units.id")
    )
    department_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("departments.id")
    )

    # Sección 2: Stakeholders
    sponsor: Mapped[str | None] = mapped_column(String(200))
    sponsor_email: Mapped[str | None] = mapped_column(String(200))
    business_leader: Mapped[str | None] = mapped_column(String(200))
    business_leader_email: Mapped[str | None] = mapped_column(String(200))
    tech_leader: Mapped[str | None] = mapped_column(String(200))
    tech_leader_email: Mapped[str | None] = mapped_column(String(200))
    pm_id: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))

    # Sección 3: Clasificación
    project_type: Mapped[str | None] = mapped_column(String(50))
    priority: Mapped[Escala | None] = mapped_column(SmallInteger)
    objective: Mapped[str | None] = mapped_column(String(5000))
    restrictions: Mapped[str | None] = mapped_column(String(5000))
    risks_summary: Mapped[str | None] = mapped_column(String(5000))
    scope: Mapped[str | None] = mapped_column(String(5000))
    key_people: Mapped[str | None] = mapped_column(String(5000))
    benefits: Mapped[str | None] = mapped_column(String(5000))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
