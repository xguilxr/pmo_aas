"""Tenant-level Áreas → Equipos → Actores — US-097 / US-103.

Catálogo jerárquico tenant-wide reutilizable en Plan, RAID y otros
módulos. Cada entidad es de scope tenant — un Actor representa una
persona dentro de la organización (puede o no tener cuenta de usuario)
y persiste a través de proyectos.

US-103 (2026-05-07): el catálogo se vuelve fuente única; se introduce
`area_assignments` para controlar qué áreas se ven desde qué
Org/Programa/Proyecto en cascada. La tabla `project_areas` (US-091)
se deprecó en migración 0048.
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
    # ENH-078: líder del área = Actor con `is_lead=true`. FK opcional
    # (área puede crearse sin líder y asignarlo después). El campo
    # `lead_name` (legacy US-097) fue migrado a Actor en 0049.
    lead_actor_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("actors.id", ondelete="SET NULL"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )


class AreaAssignment(Base):
    """US-103 — asignación de un Área del catálogo a Org/Programa/Proyecto.

    Reglas:
    - `is_global=true` con todos los scopes en NULL = área disponible
      en todos los proyectos del tenant (ej.: PMO seed).
    - Si `organization_id` está set: cubre todos los programas y
      proyectos de esa org (cascada implícita en el query, no via
      filas hijas).
    - Si `program_id` está set: cubre todos los proyectos del programa.
    - Si `project_id` está set: sólo ese proyecto.
    """

    __tablename__ = "area_assignments"
    __table_args__ = (
        Index("ix_area_assignments_area", "area_id"),
        Index("ix_area_assignments_project", "tenant_id", "project_id"),
        Index("ix_area_assignments_program", "tenant_id", "program_id"),
        Index("ix_area_assignments_org", "tenant_id", "organization_id"),
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
    organization_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
    )
    program_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("programs.id", ondelete="CASCADE"),
    )
    project_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
    )
    is_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
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
    # ENH-084 rework: área directa cuando no se asigna a un equipo.
    # Permite asignar un Actor a un Área como recurso sin obligar
    # a crear un equipo intermedio. Si `team_id` se setea, debe
    # coincidir con el `area_id` del team (validación en endpoint).
    area_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("areas.id", ondelete="SET NULL"),
    )
    user_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # ENH-078: marca actor como líder de su área. El área enlaza vía
    # `areas.lead_actor_id`. Sin constraint single-leader-per-area
    # (validación en endpoint).
    is_lead: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
