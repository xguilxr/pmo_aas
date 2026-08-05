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
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Area(Base, TimestampMixin):
    __tablename__ = "areas"
    __table_args__ = (
        # BUG-061: scope opcional por organización. Las áreas globales
        # (organization_id IS NULL) viven en `uq_areas_tenant_global_name`
        # (partial unique en migración 0054); las org-scoped en
        # `uq_areas_tenant_org_name`. Aquí dejamos solo el índice de
        # lookup — los uniques se manejan a nivel de migración para
        # diferenciar global vs scoped.
        Index("ix_areas_tenant_active", "tenant_id", "is_active"),
        Index("ix_areas_tenant_organization", "tenant_id", "organization_id"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    # BUG-061: nullable = área tenant-global (visible en todas las orgs);
    # set = área scoped a esa organización. Permite "IT" en Org A e
    # "IT" en Org B con recursos distintos.
    organization_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
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
    # ENH-078 / US-114: liderazgo legacy global. Coexiste con
    # `project_participations.is_area_lead` (líder por proyecto) hasta
    # que US-119 dropee este campo.
    is_lead: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # ENH-103: flags para distinguir actores creados a mano vs los que el
    # matcher de minutas crea on-the-fly. `verified=False + auto_created=
    # True` marca actores pendientes de validación por el owner.
    auto_created: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # US-114: enriquecimiento de persona. `company`/`job_title` para el
    # directorio (cliente, vendor, interno, cargo organizacional);
    # `manager_actor_id` autoreferencia para reportes jerárquicos.
    company: Mapped[str | None] = mapped_column(String(200))
    job_title: Mapped[str | None] = mapped_column(String(200))
    manager_actor_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("actors.id", ondelete="SET NULL"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    # --- US-182: pool de recursos con capacidad (Revamp 1.0) ---
    # El Actor ES el resource_pool del tenant. NULL en organization_id =
    # recurso tenant-global (mismo patrón que areas.organization_id).
    organization_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    # cliente_negocio | cliente_it | e4_pmo | e4_tecnologia | vendor_externo.
    # NULL = sin clasificar (legacy). Check en migración 0092.
    resource_type: Mapped[str | None] = mapped_column(String(24))
    # D-8 / ADR-021: se llamaba `portfolio_function`. El glosario veta
    # «portafolio» para un área —la entidad no existe en el producto— y lo que
    # esto guarda es la disciplina: pm | pmo | arquitectura | infraestructura |
    # aplicaciones | datos | seguridad | integraciones | negocio | change |
    # testing | vendor. Migración 0099.
    discipline: Mapped[str | None] = mapped_column(String(24))
    seniority: Mapped[str | None] = mapped_column(String(8))  # junior|mid|senior|lead
    scarcity_level: Mapped[str | None] = mapped_column(String(8))  # alta|media|baja
    location: Mapped[str | None] = mapped_column(String(100))
    skills_tags: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    # Capacidad consumible: nominal = jornada teórica; project = % real
    # disponible para proyectos (BAU descontado). La saturación (US-183)
    # compara asignaciones vs project_capacity_pct, NUNCA vs 100 fijo.
    nominal_capacity_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=100, server_default="100"
    )
    project_capacity_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=100, server_default="100"
    )
    is_key_resource: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_shared_resource: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    fte_cost_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
