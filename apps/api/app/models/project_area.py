from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid


class ProjectArea(Base):
    """Áreas/actores/equipos del proyecto (US-018, DEC-009).

    No son usuarios del sistema — se referencian como texto en tareas,
    RAIDs y minutas para registrar stakeholders sin cuenta.
    """

    __tablename__ = "project_areas"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="area")
    description: Mapped[str | None] = mapped_column(String(2000))
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
