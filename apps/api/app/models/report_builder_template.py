"""ReportBuilderTemplate — US-122 (EP020 Report Builder backbone).

Plantillas declarativas del Report Builder. Cada plantilla es una
**composición** de secciones del catálogo `report_sections` (US-120).
Distinta de `report_templates` (ENH-085, persiste HTML tweakeado del
PM) y de `ai_report_templates` (per-project, wizard de IA).

Plantillas seed (`is_seed=True`, `tenant_id=NULL`):
- L3-AVANCE          — modo A (by_section)
- L3-SEGUIMIENTO     — modo B (by_area)
- L1-PORTAFOLIO      — modo A
- L2-ORG             — modo A
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ReportBuilderTemplate(Base, TimestampMixin):
    """Plantilla declarativa del Report Builder (compone secciones)."""

    __tablename__ = "report_builder_templates"
    __table_args__ = (
        Index("ix_report_builder_templates_tenant", "tenant_id"),
        Index("ix_report_builder_templates_level", "level"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    # `tenant_id` NULL = plantilla seed compartida por todos los tenants.
    # Plantillas custom de un tenant tienen su tenant_id seteado.
    tenant_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    # Código único (seed) o slug del tenant (custom). Para custom el
    # uniqueness vive en (tenant_id, code).
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Nivel: 1=portafolio, 2=org/programa, 3=proyecto, 4=custom.
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    # Modo de composición: 'A' = by_section, 'B' = by_area.
    composition_mode: Mapped[str] = mapped_column(
        String(1), nullable=False, server_default="A"
    )
    # Array JSON de códigos de `report_sections.code` (ej. ["S-01","S-02",...])
    # en el orden en que se renderizan.
    section_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    # Parámetros por sección (mapa code → dict de overrides).
    default_parameters: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    is_seed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
