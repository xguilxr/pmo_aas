"""Bootstrap seed. Crea 2 tenants demo (acme, globex) con sus roles sistema
y un admin por tenant, más un superadmin global. Idempotente."""
import logging
import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.role import Role, UserRole
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger("pmoaas.seed")

SYSTEM_ROLES = [
    {
        "name": "Administrador",
        "description": "Administrador del tenant.",
        "permissions": {
            "admin.users": ["read", "create", "update", "delete"],
            "admin.roles": ["read", "create", "update", "delete"],
            "admin.organizations": ["read", "create", "update", "delete"],
            "admin.projects": ["read", "create", "update", "delete"],
            "admin.requests": ["read", "create", "update", "delete", "approve"],
            "projects": ["read", "create", "update", "delete", "approve"],
            "risks": ["read", "create", "update", "delete"],
            "issues": ["read", "create", "update", "delete"],
            "change_requests": ["read", "create", "update", "delete", "approve"],
            "documents": ["read", "create", "update", "delete", "upload"],
            "lessons": ["read", "create", "update", "delete"],
            "minutes": ["read", "create", "update", "minute"],
            "dashboard": ["read"],
            "ai.generate": ["create"],
        },
    },
    {
        "name": "PMO Manager",
        "description": "Gestor de portafolio.",
        "permissions": {
            "projects": ["read", "create", "update", "approve"],
            "risks": ["read", "create", "update"],
            "issues": ["read", "create", "update"],
            "change_requests": ["read", "create", "update", "approve"],
            "documents": ["read", "upload"],
            "lessons": ["read", "create"],
            "minutes": ["read", "create"],
            "dashboard": ["read"],
            "admin.requests": ["read", "approve"],
        },
    },
    {
        "name": "Project Manager",
        "description": "Responsable de un proyecto.",
        "permissions": {
            "projects": ["read", "update"],
            "risks": ["read", "create", "update"],
            "issues": ["read", "create", "update"],
            "change_requests": ["read", "create"],
            "documents": ["read", "upload"],
            "lessons": ["read", "create"],
            "minutes": ["read", "create", "minute"],
            "dashboard": ["read"],
            "ai.generate": ["create"],
        },
    },
    {
        "name": "Viewer",
        "description": "Consulta solamente.",
        "permissions": {
            "projects": ["read"],
            "risks": ["read"],
            "issues": ["read"],
            "change_requests": ["read"],
            "documents": ["read"],
            "lessons": ["read"],
            "minutes": ["read"],
            "dashboard": ["read"],
        },
    },
]

DEMO_TENANTS = [
    {
        "slug": "acme",
        "name": "Acme PMO Demo",
        "settings": {"locale": "es-MX", "currency": "MXN", "ai_mode": "disabled"},
        "admin": {
            "username": "admin",
            "email": "admin@acme.pmoaas.local",
            "full_name": "Admin Acme",
        },
    },
    {
        "slug": "globex",
        "name": "Globex Industries",
        "settings": {"locale": "es-MX", "currency": "USD", "ai_mode": "disabled"},
        "admin": {
            "username": "admin",
            "email": "admin@globex.pmoaas.local",
            "full_name": "Admin Globex",
        },
    },
]


def _random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _ensure_tenant(db: AsyncSession, *, slug: str, name: str, settings: dict) -> tuple[Tenant, bool]:
    existing = (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()
    if existing is not None:
        return existing, False
    tenant = Tenant(slug=slug, name=name, is_active=True, settings=settings)
    db.add(tenant)
    await db.flush()
    return tenant, True


async def _ensure_system_roles(db: AsyncSession, tenant: Tenant) -> dict[str, Role]:
    out: dict[str, Role] = {}
    for role_def in SYSTEM_ROLES:
        existing = (
            await db.execute(
                select(Role).where(Role.tenant_id == tenant.id, Role.name == role_def["name"])
            )
        ).scalar_one_or_none()
        if existing is None:
            r = Role(
                tenant_id=tenant.id,
                name=role_def["name"],
                description=role_def["description"],
                permissions=role_def["permissions"],
                is_system=True,
            )
            db.add(r)
            await db.flush()
            out[role_def["name"]] = r
        else:
            out[role_def["name"]] = existing
    return out


async def _ensure_tenant_admin(
    db: AsyncSession,
    *,
    tenant: Tenant,
    username: str,
    email: str,
    full_name: str,
    admin_role: Role,
) -> tuple[User, str | None]:
    """Returns (user, temp_password_if_created_else_None)."""
    existing = (
        await db.execute(
            select(User).where(User.tenant_id == tenant.id, User.username == username)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, None
    pwd = _random_password()
    user = User(
        tenant_id=tenant.id,
        username=username,
        email=email.lower(),
        full_name=full_name,
        password_hash=hash_password(pwd),
        is_active=True,
        is_superadmin=False,
        must_change_password=True,
        locale="es-MX",
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=admin_role.id))
    return user, pwd


async def _ensure_superadmin(db: AsyncSession) -> tuple[User, str | None]:
    existing = (
        await db.execute(select(User).where(User.is_superadmin.is_(True)))
    ).scalar_one_or_none()
    if existing is not None:
        return existing, None
    pwd = _random_password(24)
    user = User(
        tenant_id=None,
        username="superadmin",
        email="superadmin@pmoaas.local",
        password_hash=hash_password(pwd),
        full_name="Platform Super Admin",
        is_active=True,
        is_superadmin=True,
        must_change_password=True,
        locale="es-MX",
    )
    db.add(user)
    await db.flush()
    return user, pwd


async def run_initial_seed() -> None:
    async with SessionLocal() as db:
        created_credentials: list[tuple[str, str, str]] = []  # (label, email, pwd)

        for t_def in DEMO_TENANTS:
            tenant, tenant_created = await _ensure_tenant(
                db, slug=t_def["slug"], name=t_def["name"], settings=t_def["settings"]
            )
            if tenant_created:
                logger.info("[seed] tenant created: %s", tenant.slug)

            roles = await _ensure_system_roles(db, tenant)

            admin_def = t_def["admin"]
            admin_user, admin_pwd = await _ensure_tenant_admin(
                db,
                tenant=tenant,
                username=admin_def["username"],
                email=admin_def["email"],
                full_name=admin_def["full_name"],
                admin_role=roles["Administrador"],
            )
            if admin_pwd is not None:
                created_credentials.append(
                    (f"admin tenant={tenant.slug}", admin_user.email, admin_pwd)
                )

        super_user, super_pwd = await _ensure_superadmin(db)
        if super_pwd is not None:
            created_credentials.append(("superadmin global", super_user.email, super_pwd))

        await db.commit()

        if not created_credentials:
            logger.info("[seed] skipped: ya existen usuarios fundacionales")
            return

        banner = "\n" + "=" * 72 + "\n"
        banner += "[seed] CREDENCIALES INICIALES — cópialas AHORA, no se vuelven a mostrar\n"
        banner += "=" * 72 + "\n"
        for label, email, pwd in created_credentials:
            banner += f"  {label:<24} email={email}  temp_password={pwd}\n"
        banner += "=" * 72 + "\n"
        banner += "Despues de copiar, pon SEED_ON_STARTUP=false y redeploy.\n"
        banner += "En el primer login, te forzará a cambiar la contraseña.\n"
        banner += "=" * 72
        logger.warning(banner)
