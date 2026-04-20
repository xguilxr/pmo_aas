from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    reason_social: str | None = None
    industry: str | None = None
    country: str | None = None
    contact_email: str | None = None
    is_active: bool = True


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    reason_social: str | None = None
    industry: str | None = None
    country: str | None = None
    contact_email: str | None = None
    is_active: bool | None = None


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    reason_social: str | None
    industry: str | None
    country: str | None
    contact_email: str | None
    logo_url: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class BusinessUnitCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    is_active: bool = True


class BusinessUnitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    is_active: bool | None = None


class BusinessUnitRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ProgramCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    organization_id: UUID
    description: str | None = None
    strategic_alignment: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool = True


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    strategic_alignment: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


class ProgramRead(BaseModel):
    id: UUID
    name: str
    organization_id: UUID
    description: str | None
    strategic_alignment: str | None
    start_date: date | None
    end_date: date | None
    is_active: bool

    model_config = {"from_attributes": True}


class TenantProvisionRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9\-]+$")
    admin_email: str = Field(min_length=3, max_length=200)
    admin_password: str | None = None
    admin_full_name: str = Field(min_length=2, max_length=200)
    admin_username: str | None = Field(default=None, max_length=64)


class TenantProvisionResponse(BaseModel):
    tenant_id: UUID
    slug: str
    admin_user_id: UUID
    admin_password: str


class TenantRead(BaseModel):
    id: UUID
    slug: str
    name: str
    is_active: bool
    user_count: int = 0
    project_count: int = 0

    model_config = {"from_attributes": True}
