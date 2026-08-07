"""MetricSnapshot model (US-151, EP020 + dashboards N1/N2).

Foto periódica (cadencia semanal) de las métricas de *stock* del portafolio
a los 4 niveles de scope: tenant, organización, programa y proyecto. Sin
historia persistida no hay líneas de tendencia en los dashboards ni en los
reportes Nivel 1/2; este modelo es esa historia.

Las métricas de *flujo* (cycle-time, throughput) NO viven aquí: se calculan
on-the-fly desde timestamps ya existentes (requested_at/approved_at, etc.).
"""
from datetime import date
from uuid import UUID

from sqlalchemy import (
    JSON,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.magnitudes import Importe, PorcentajeDecimal
from app.db.base import Base, TimestampMixin, new_uuid


class MetricSnapshot(Base, TimestampMixin):
    __tablename__ = "metric_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "scope_type",
            "scope_id",
            "snapshot_date",
            name="uq_metric_snapshot_scope_date",
        ),
        Index("idx_metric_snapshot_scope", "scope_type", "scope_id", "snapshot_date"),
        Index("idx_metric_snapshot_tenant_date", "tenant_id", "snapshot_date"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    # scope_type: "tenant" | "organization" | "program" | "project".
    # scope_id apunta a la entidad del scope (para "tenant" == tenant_id).
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    # --- Proyectos ---
    projects_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    projects_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Salud (health_status) ---
    health_green: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    health_yellow: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    health_red: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Avance ---
    avg_progress: Mapped[PorcentajeDecimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )

    # --- Presupuesto ---
    budget_plan: Mapped[Importe] = mapped_column(
        Numeric(16, 2), nullable=False, default=0
    )
    budget_actual: Mapped[Importe] = mapped_column(
        Numeric(16, 2), nullable=False, default=0
    )

    # --- RAID / solicitudes ---
    open_risks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    severe_risks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changes_in_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests_in_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Tareas / hitos ---
    tasks_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    milestones_due_7: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    milestones_due_14: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    milestones_due_30: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Bolsa flexible para métricas futuras sin migración por cada una.
    extras: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
