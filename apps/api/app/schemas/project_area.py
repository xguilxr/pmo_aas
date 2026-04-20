from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ProjectAreaCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    type: Literal["area", "actor", "team"] = "area"
    description: str | None = None
    contact_name: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None
    is_active: bool = True


class ProjectAreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    type: Literal["area", "actor", "team"] | None = None
    description: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    is_active: bool | None = None


class ProjectAreaRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    type: str
    description: str | None
    contact_name: str | None
    contact_email: str | None
    is_active: bool

    model_config = {"from_attributes": True}
