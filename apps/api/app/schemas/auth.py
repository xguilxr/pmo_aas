from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=200)


# US-063 — Recuperación de password por email.

class ForgotPasswordRequest(BaseModel):
    """El endpoint responde siempre 204 (no revela existencia del email)."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Finaliza el flujo de reset. `token` llegó al user por email."""

    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    is_active: bool
    is_superadmin: bool
    must_change_password: bool = False
    roles: list[str] = []

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    tenants: list[UUID] = []
    active_tenant_id: UUID | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


class SwitchTenantRequest(BaseModel):
    tenant_id: UUID
