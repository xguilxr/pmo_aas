from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_org_tenant_name"),)

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason_social: Mapped[str | None] = mapped_column(String(200))
    industry: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    contact_email: Mapped[str | None] = mapped_column(String(200))
    # BUG-068: Text (no String(500)) para admitir data-URLs base64 de logos
    # subidos directamente (PNG/JPG/SVG/WEBP), además de URLs externas.
    logo_url: Mapped[str | None] = mapped_column(Text)
    # ENH-100: logo del *cliente* de esta organización (separado de `logo_url`,
    # que es la marca del propio tenant/PMO). Lo consume el header de los
    # reportes generados por EP020 Report Builder.
    client_logo_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class BusinessUnit(Base, TimestampMixin):
    __tablename__ = "business_units"
    __table_args__ = (
        UniqueConstraint("tenant_id", "organization_id", "name", name="uq_bu_tenant_org_name"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "business_unit_id", "name", name="uq_dept_tenant_bu_name"
        ),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    business_unit_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("business_units.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))


class Program(Base, TimestampMixin):
    __tablename__ = "programs"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    department_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("departments.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    strategic_alignment: Mapped[str | None] = mapped_column(String(2000))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
