from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid


class ProjectArea(Base):
    """Áreas/actores/equipos del proyecto (US-018, DEC-009, ENH-020).

    El campo `contact_*` se conserva como contacto primario (compat);
    `ProjectAreaResource` permite múltiples recursos (internos o
    externos). US-062 agrega `area_leader_id` opcional (FK a users).
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
    # US-062: líder del área (opcional, puede o no tener cuenta activa).
    area_leader_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    # US-091: jerarquía explícita Área → Equipo → Actor.
    # `team_id` apunta a otra row con type='team' (sólo para actores).
    # `area_id` apunta a otra row con type='area' (para actores y equipos).
    # `phone` aplica a actores; se permite a otros tipos para flexibilidad.
    team_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("project_areas.id", ondelete="SET NULL")
    )
    area_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("project_areas.id", ondelete="SET NULL")
    )
    phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))


class ProjectAreaResource(Base):
    """Recurso asignado a un área (ENH-020 + US-062).

    Puede ser un usuario interno (`user_id` poblado) o un contacto externo
    sin cuenta (`name` + `email` libres). El `role` es texto libre (p. ej.
    "Analista", "Owner de producto") para reflejar cómo el recurso
    participa en el área.
    """

    __tablename__ = "project_area_resources"
    __table_args__ = (
        Index("idx_par_area", "area_id"),
        Index("idx_par_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    area_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("project_areas.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
