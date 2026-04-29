from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Attachment(BaseModel):
    filename: str
    url: str
    size: int
    mime: str


class ProjectRequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3)
    objective: str = Field(min_length=3)
    organization_id: UUID
    business_unit: str = Field(min_length=1, max_length=200)
    department: str = Field(min_length=1, max_length=200)
    # FKs reales (US-011): opcionales hasta migrar datos legacy
    business_unit_id: UUID | None = None
    department_id: UUID | None = None
    sponsor: str = Field(min_length=1, max_length=200)
    sponsor_email: EmailStr
    benefits: str = Field(min_length=3)
    budget: Decimal = Field(ge=Decimal("0"))
    scope: str = Field(min_length=3)
    entregables: str | None = None
    key_people: str | None = None
    if_not_done: str | None = None
    observations: str | None = None
    requester_name: str | None = Field(default=None, max_length=200)
    requester_email: EmailStr | None = None
    delivery_constraint_date: date | None = None
    attachments: list[Attachment] = []


class ProjectRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    objective: str | None = None
    business_unit: str | None = None
    department: str | None = None
    business_unit_id: UUID | None = None
    department_id: UUID | None = None
    sponsor: str | None = None
    sponsor_email: EmailStr | None = None
    benefits: str | None = None
    budget: Decimal | None = None
    scope: str | None = None
    entregables: str | None = None
    key_people: str | None = None
    if_not_done: str | None = None
    observations: str | None = None
    requester_name: str | None = None
    requester_email: EmailStr | None = None
    delivery_constraint_date: date | None = None


class ProjectRequestRead(BaseModel):
    id: UUID
    folio: str
    title: str
    description: str
    objective: str
    organization_id: UUID
    business_unit: str
    department: str
    business_unit_id: UUID | None = None
    department_id: UUID | None = None
    sponsor: str
    sponsor_email: str | None = None
    benefits: str
    budget: Decimal
    scope: str
    entregables: str | None = None
    key_people: str | None = None
    if_not_done: str | None = None
    observations: str | None = None
    requester_name: str | None = None
    requester_email: str | None = None
    delivery_constraint_date: date | None = None
    status: str
    requested_by: UUID
    requested_at: datetime
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    review_comment: str | None
    attachments: list[Attachment] = []
    project_id: UUID | None = None

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject", "needs_info"]
    comment: str | None = None


class CreateProjectFromRequest(BaseModel):
    pm_id: UUID
