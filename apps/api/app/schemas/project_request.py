from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


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
    sponsor: str = Field(min_length=1, max_length=200)
    benefits: str = Field(min_length=3)
    budget: Decimal = Field(ge=Decimal("0"))
    scope: str = Field(min_length=3)
    attachments: list[Attachment] = []


class ProjectRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    objective: str | None = None
    business_unit: str | None = None
    department: str | None = None
    sponsor: str | None = None
    benefits: str | None = None
    budget: Decimal | None = None
    scope: str | None = None


class ProjectRequestRead(BaseModel):
    id: UUID
    folio: str
    title: str
    description: str
    objective: str
    organization_id: UUID
    business_unit: str
    department: str
    sponsor: str
    benefits: str
    budget: Decimal
    scope: str
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
