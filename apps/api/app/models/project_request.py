from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ProjectRequest(Base, TimestampMixin):
    __tablename__ = "project_requests"
    __table_args__ = (UniqueConstraint("tenant_id", "folio", name="uq_req_tenant_folio"),)

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    folio: Mapped[str] = mapped_column(String(32), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(5000), nullable=False)
    objective: Mapped[str] = mapped_column(String(5000), nullable=False)

    organization_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    business_unit: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str] = mapped_column(String(200), nullable=False)
    business_unit_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("business_units.id")
    )
    department_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("departments.id")
    )
    sponsor: Mapped[str] = mapped_column(String(200), nullable=False)
    sponsor_email: Mapped[str | None] = mapped_column(String(200))
    benefits: Mapped[str] = mapped_column(String(5000), nullable=False)
    budget: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    scope: Mapped[str] = mapped_column(String(5000), nullable=False)
    entregables: Mapped[str | None] = mapped_column(String(5000))
    key_people: Mapped[str | None] = mapped_column(String(5000))
    if_not_done: Mapped[str | None] = mapped_column(String(5000))
    observations: Mapped[str | None] = mapped_column(String(5000))
    requester_name: Mapped[str | None] = mapped_column(String(200))
    requester_email: Mapped[str | None] = mapped_column(String(200))

    requested_by: Mapped[UUID] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # ENH-038: fecha de restricción de entrega (opcional, sólo fecha)
    delivery_constraint_date: Mapped[date | None] = mapped_column(Date(), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_review")
    reviewed_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_comment: Mapped[str | None] = mapped_column(String(5000))
    attachments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    project_id: Mapped[UUID | None] = mapped_column(String(36))  # back-reference


class FolioSequence(Base):
    __tablename__ = "folio_sequences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("tenant_id", "prefix", "year", name="uq_folio_tpy"),)
