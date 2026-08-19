"""Helpers para crear entidades en tests."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organization import Portfolio, Program
from app.models.role import Role, UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.services.jerarquia import portafolio_general

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


async def create_portfolio(
    db: AsyncSession,
    *,
    tenant_id: str,
    organization_id: str,
    name: str = "Portafolio A",
    **campos: object,
) -> Portfolio:
    """US-198 — un portafolio de esa organización, para los tests que necesitan
    más de uno (la regla de consistencia solo se puede probar con dos)."""
    pf = Portfolio(
        tenant_id=str(tenant_id),
        organization_id=str(organization_id),
        name=name,
        **campos,
    )
    db.add(pf)
    await db.flush()
    return pf


async def create_program(
    db: AsyncSession,
    *,
    tenant_id: str,
    organization_id: str,
    name: str = "Programa",
    portfolio_id: str | None = None,
    **campos: object,
) -> Program:
    """US-198 — un programa vive **dentro** de un portafolio (`NOT NULL`).

    Sin `portfolio_id` cae en el «Portafolio General» de su organización, que se
    crea al vuelo: es la misma resolución que hace el endpoint de alta, así que
    un test que no le importe el portafolio no tiene que inventarse uno, y uno
    que sí lo pasa explícito.
    """
    if portfolio_id is None:
        pf = await portafolio_general(
            db, tenant_id=str(tenant_id), organization_id=str(organization_id)
        )
        portfolio_id = str(pf.id)
    prog = Program(
        tenant_id=str(tenant_id),
        organization_id=str(organization_id),
        portfolio_id=portfolio_id,
        name=name,
        **campos,
    )
    db.add(prog)
    await db.flush()
    return prog
