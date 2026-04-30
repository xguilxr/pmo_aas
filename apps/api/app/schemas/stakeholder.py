"""Schemas para stakeholders — US-086."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class StakeholderCreate(BaseModel):
    organization_id: UUID | None = None
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool = True


class StakeholderUpdate(BaseModel):
    organization_id: UUID | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    job_title: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class StakeholderRead(BaseModel):
    id: UUID
    tenant_id: UUID
    organization_id: UUID | None
    full_name: str
    email: str | None
    phone: str | None
    company: str | None
    job_title: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
