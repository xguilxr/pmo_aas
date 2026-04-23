from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class ProjectAreaCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    type: Literal["area", "actor", "team"] = "area"
    description: str | None = None
    contact_name: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None
    area_leader_id: UUID | None = None
    is_active: bool = True


class ProjectAreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    type: Literal["area", "actor", "team"] | None = None
    description: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    area_leader_id: UUID | None = None
    is_active: bool | None = None


class ProjectAreaRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    type: str
    description: str | None
    contact_name: str | None
    contact_email: str | None
    area_leader_id: UUID | None = None
    is_active: bool

    model_config = {"from_attributes": True}


# ENH-020 + US-062: recursos múltiples asignados a un Área.


class ProjectAreaResourceCreate(BaseModel):
    """Crea un recurso interno (user_id) o externo (name+email)."""

    user_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    role: str | None = Field(default=None, max_length=100)
    is_active: bool = True

    @model_validator(mode="after")
    def _validate_identity(self) -> "ProjectAreaResourceCreate":
        # Debe haber identidad: user_id interno o (al menos name) externo.
        if self.user_id is None and not (self.name and self.name.strip()):
            raise ValueError(
                "Debe indicar user_id (recurso interno) o name (recurso externo)"
            )
        return self


class ProjectAreaResourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    role: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class ProjectAreaResourceRead(BaseModel):
    id: UUID
    area_id: UUID
    user_id: UUID | None
    name: str | None
    email: str | None
    role: str | None
    is_active: bool

    model_config = {"from_attributes": True}
