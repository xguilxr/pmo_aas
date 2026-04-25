from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# US-076 + DEC-024: vocabulario de role_type post-eliminación de viewer.
RoleTypeIn = Literal["admin", "user"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.\-]+$")
    email: EmailStr
    password: str = Field(min_length=1)
    role_ids: list[UUID] = []
    is_active: bool = True
    # US-078: role_type explícito al crear. Default "user".
    role_type: RoleTypeIn = "user"
    # US-078: lista opcional de orgs a EXCLUIR (default = ninguna,
    # i.e. acceso a todas las orgs del tenant).
    excluded_organization_ids: list[UUID] = []


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    role_ids: list[UUID] | None = None
    is_active: bool | None = None
    # US-078: cambiar role_type del user (admin ↔ user).
    role_type: RoleTypeIn | None = None
    # US-078: forzar cambio en próximo login sin tocar password actual.
    must_change_password: bool | None = None


class UserRead(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    is_active: bool
    must_change_password: bool = False
    last_login: str | None = None
    roles: list[str] = []
    role_type: str | None = None  # US-076 + DEC-024

    model_config = {"from_attributes": True}


class ExcludedOrganizationsBody(BaseModel):
    """Reemplazo batch del set de orgs excluidas para un user."""

    organization_ids: list[UUID] = []


class ExcludedOrganizationsRead(BaseModel):
    organization_ids: list[UUID]


class UserResetPasswordResponse(BaseModel):
    temp_password: str


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    permissions: dict[str, list[str]]


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    permissions: dict[str, list[str]] | None = None


class RoleRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system: bool
    permissions: dict[str, list[str]]

    model_config = {"from_attributes": True}


class PaginatedUsers(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    limit: int
