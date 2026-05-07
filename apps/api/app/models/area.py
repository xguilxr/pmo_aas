"""Tenant-level Áreas → Equipos → Actores — US-097.

Catálogo jerárquico tenant-wide reutilizable en Plan, RAID y otros
módulos. Cada entidad es de scope tenant — un Actor representa una
persona dentro de la organización (puede o no tener cuenta de usuario)
y persiste a través de proyectos.

Diferencia con `project_areas` (US-091): aquellas son scope-proyecto,
sirven para asignaciones puntuales por proyecto. Estas son el catálogo
maestro tenant.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Area(Base, TimestampMixin):
    __tablename__ = "areas"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_areas_tenant_name"),
        Index("ix_areas_tenant_active", "tenant_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    # US-097 fix: el líder de un Área no necesariamente es un user del
    # tenant — puede ser un actor/recurso. Texto libre para no forzar
    # FK; cuando el owner cablee actores como líderes se agrega una
    # FK opcional adicional sin migrar este campo.
    lead_name: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )


class Team(Base, TimestampMixin):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("tenant_id", "area_id", "name", name="uq_teams_area_name"),
        Index("ix_teams_tenant_area", "tenant_id", "area_id"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    area_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("areas.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )


class Actor(Base, TimestampMixin):
    """Persona dentro del catálogo tenant.

    `team_id` es nullable: un actor puede existir sin equipo asignado
    (recién creado o re-asignado vía US-099 bulk-move).
    `user_id` es nullable: un actor puede ser un contacto sin cuenta.
    `email` es opcional pero único por tenant cuando está presente.
    """

    __tablename__ = "actors"
    __table_args__ = (
        Index("ix_actors_tenant_team", "tenant_id", "team_id"),
        Index("ix_actors_tenant_user", "tenant_id", "user_id"),
        UniqueConstraint("tenant_id", "email", name="uq_actors_tenant_email"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="SET NULL"),
    )
    user_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
