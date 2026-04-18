from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.\-]+$")
    email: EmailStr
    password: str = Field(min_length=1)
    role_ids: list[UUID] = []
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    role_ids: list[UUID] | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    is_active: bool
    must_change_password: bool = False
    last_login: str | None = None
    roles: list[str] = []

    model_config = {"from_attributes": True}


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
