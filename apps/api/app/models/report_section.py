"""ReportSection — US-120 (EP020 Report Builder backbone).

Catálogo global de secciones atómicas del Report Builder. Tabla de
referencia (no tenant-scoped); todas las secciones disponibles para
todos los tenants. Las 22 entradas seed cubren los catálogos cerrados
documentados en `docs/epics/drafts/EP020-secciones-atomicas.md`.

Las plantillas (`report_builder_templates`, US-122) componen reportes
referenciando los `code` de esta tabla.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ReportSection(Base, TimestampMixin):
    """Catálogo global de secciones atómicas (S-XX) del Report Builder."""

    __tablename__ = "report_sections"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    # Slug único corto, ej. "S-01" o "S-09". Es la clave que las
    # plantillas referencian en `section_codes`.
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Categoría del catálogo (HDR/EST/AVN/PLN/RAID/EQP/NAR/KPI/PRT).
    category: Mapped[str] = mapped_column(String(8), nullable=False)
    # Nivel mínimo de aplicabilidad: 1=portafolio, 2=org/programa,
    # 3=proyecto, 4=custom. Una sección de nivel 3 se puede usar en
    # nivel 4; las de nivel 1 (PRT) sólo aplican a niveles 1 y 2.
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # Contrato de datos que la sección expone (shape JSON). Lo usa
    # el motor de render (US-123) para validar params + dispatch.
    data_shape: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # JSON schema (informal) de los parámetros configurables además
    # de los transversales.
    parameters_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Modo de composición default cuando la sección entra a un canvas
    # nuevo. 'A' = "by_section" (Avance), 'B' = "by_area" (Seguimiento).
    composition_mode_default: Mapped[str] = mapped_column(
        String(1), nullable=False, default="A", server_default="A"
    )
    supports_ia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
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
