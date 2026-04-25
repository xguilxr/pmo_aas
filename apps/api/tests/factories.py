"""Helpers para crear entidades en tests."""
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.role import Role, UserRole
from app.models.tenant import Tenant
from app.models.user import User

ADMIN_PERMS = {
    "users": ["read", "create", "update", "delete"],
    "roles": ["read", "create", "update", "delete"],
    "organizations": ["read", "create", "update", "delete"],
    "admin": ["read", "create", "update", "delete"],
    "requests": ["read", "create", "update", "delete", "approve"],
    "projects": ["read", "create", "update", "delete", "approve"],
    "risks": ["read", "create", "update", "delete"],
    "issues": ["read", "create", "update", "delete"],
    "change_requests": ["read", "create", "update", "delete", "approve"],
    "documents": ["read", "create", "update", "delete", "upload"],
    "lessons": ["read", "create", "update", "delete"],
    "minutes": ["read", "create", "update", "minute"],
    "dashboard": ["read"],
    "ai.generate": ["create"],
}


async def create_tenant(db: AsyncSession, slug: str = "acme", name: str = "Acme") -> Tenant:
    t = Tenant(slug=slug, name=name, is_active=True, settings={})
    db.add(t)
    await db.flush()
    return t


async def create_admin_role(db: AsyncSession, tenant: Tenant) -> Role:
    r = Role(
        tenant_id=tenant.id, name="Administrador", description="Admin",
        is_system=True, permissions=ADMIN_PERMS,
    )
    db.add(r)
    await db.flush()
    return r


async def create_user(
    db: AsyncSession,
    *,
    tenant: Tenant | None,
    username: str = "admin",
    email: str = "admin@acme.example.com",
    password: str = "Abcdefgh123!",
    full_name: str = "Admin User",
    is_superadmin: bool = False,
    roles: list[Role] | None = None,
    role_type: str | None = None,
) -> User:
    # US-076 + DEC-024: los tests históricamente NO seteaban role_type.
    # Inferimos del rol legacy asignado (equivalente a migración 0026):
    # un user con rol "Administrador" o "Admin" recibe role_type="admin",
    # el resto "user". Tests que necesiten un role_type específico lo
    # pasan explícito.
    if role_type is None:
        if is_superadmin:
            role_type = "admin"
        elif roles and any(r.name in ("Administrador", "Admin", "PMO Manager") for r in roles):
            role_type = "admin"
        else:
            role_type = "user"
    u = User(
        tenant_id=tenant.id if tenant else None,
        username=username.lower(),
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        is_active=True,
        is_superadmin=is_superadmin,
        role_type=role_type,
    )
    db.add(u)
    await db.flush()
    for r in roles or []:
        db.add(UserRole(user_id=u.id, role_id=r.id))
    await db.commit()
    return u


async def login(client, identifier: str, password: str) -> dict:
    r = await client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    data["_authz"] = {"Authorization": f"Bearer {data['access_token']}"}
    return data


def _password(ch: str = "a") -> str:
    return f"Str0ng-Pass-{ch}{uuid4().hex[:4]}!"


async def enable_tenant_ai(
    db: AsyncSession,
    tenant: Tenant,
    *,
    mode: str = "platform",
    byo: dict | None = None,
) -> None:
    """US-057: helper de tests para marcar el tenant en un modo IA dado.

    Los providers están stubbed en conftest (`_stub_ai_providers`), así
    que cualquier modo != "disabled" corre con la respuesta stub sin
    depender de API keys reales.
    """
    tenant_settings = dict(tenant.settings or {})
    ai = dict(tenant_settings.get("ai") or {})
    ai["mode"] = mode
    if byo is not None:
        ai["byo"] = byo
    tenant_settings["ai"] = ai
    tenant.settings = tenant_settings
    await db.flush()
    await db.commit()
