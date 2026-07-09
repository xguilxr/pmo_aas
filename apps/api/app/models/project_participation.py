"""US-114 — Participación de un Actor en un Proyecto.

N filas por (project_id, actor_id) — una persona puede estar en varios
equipos operativos / roles dentro del mismo proyecto. La fila marcada
`is_primary=True` es la que usan los agrupadores y reportes por defecto.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ProjectParticipation(Base, TimestampMixin):
    __tablename__ = "project_participations"
    __table_args__ = (
        Index(
            "ix_participations_project_actor", "project_id", "actor_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("actors.id", ondelete="CASCADE"),
        nullable=False,
    )
    operational_team_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="SET NULL"),
    )
    project_role_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("project_roles.id", ondelete="SET NULL"),
    )
    functional_area_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("areas.id", ondelete="SET NULL"),
    )
    is_area_lead: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # --- US-183: asignación con FTE% (capacidad consumible, Revamp 1.0) ---
    # % FTE asignado a este proyecto. NULL = sin cuantificar (no suma a la
    # saturación; las vistas lo reportan como cobertura pendiente). La regla
    # de modelado del diseño: si cambia FTE/fase/ventana se crea OTRA
    # participation, no se re-edita la histórica.
    allocation_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    # directa | advisory | backup | shared_service | steerco_only.
    assignment_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="directa", server_default="directa"
    )
    # Ciclo de vida de capacidad: tentativa | activa | cerrada | cancelada.
    # Solo 'activa' suma a la saturación; 'tentativa' se reporta aparte.
    # Coexiste con is_active (switch de visibilidad EP017 para dropdowns).
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default="activa", server_default="activa"
    )
    # El proyecto depende fuertemente de este recurso (pesa en alertas).
    is_critical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Fase del proyecto en la que consume capacidad (texto libre corto).
    phase: Mapped[str | None] = mapped_column(String(32))
    created_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
