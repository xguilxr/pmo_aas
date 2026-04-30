"""Stakeholders catalog — US-086.

Catálogo de personas a nivel tenant/organización, reutilizable en
Charter (Sponsor / Líder Negocio / Líder Técnico) y Áreas.

Decisión owner (Opción B, 2026-04-28): scope = tenant; opcionalmente
asociado a una organización específica del tenant.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Stakeholder(Base, TimestampMixin):
    __tablename__ = "stakeholders"
    __table_args__ = (
        Index("ix_stakeholders_tenant_name", "tenant_id", "full_name"),
        Index("ix_stakeholders_org_active", "organization_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))
    company: Mapped[str | None] = mapped_column(String(200))
    job_title: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(5000))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
