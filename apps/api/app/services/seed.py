"""Minimal bootstrap seed. Creates demo tenant, system roles and a superadmin."""
import logging
import secrets
import string

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.role import Role
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
            "projects": ["read", "create", "update", "delete"],
        },
    },
    {
        "name": "PMO Manager",
        "description": "Gestor de portafolio.",
        "permissions": {
            "projects": ["read", "create", "update", "approve"],
            "risks": ["read", "create", "update"],
            "issues": ["read", "create", "update"],
        },
    },
    {
        "name": "Project Manager",
        "description": "Responsable de un proyecto.",
        "permissions": {
            "projects": ["read", "update"],
            "risks": ["read", "create", "update"],
            "issues": ["read", "create", "update"],
            "documents": ["read", "upload"],
            "minutes": ["read", "create", "minute"],
        },
    },
    {
        "name": "Viewer",
        "description": "Consulta solamente.",
        "permissions": {
            "projects": ["read"],
            "risks": ["read"],
            "issues": ["read"],
            "documents": ["read"],
        },
    },
]


def _random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def run_initial_seed() -> None:
    async with SessionLocal() as db:
        existing_super = (
            await db.execute(select(User).where(User.is_superadmin.is_(True)))
        ).scalar_one_or_none()
        if existing_super:
            logger.info("[seed] skipped: superadmin already exists (%s)", existing_super.email)
            return

        tenant = (await db.execute(select(Tenant).where(Tenant.slug == "acme"))).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(
                slug="acme",
                name="Acme PMO Demo",
                is_active=True,
                settings={"locale": "es-MX", "currency": "MXN", "ai_mode": "disabled"},
            )
            db.add(tenant)
            await db.flush()
            logger.info("[seed] tenant created: %s", tenant.slug)

        for role_def in SYSTEM_ROLES:
            existing = (
                await db.execute(
                    select(Role).where(Role.tenant_id == tenant.id, Role.name == role_def["name"])
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    Role(
                        tenant_id=tenant.id,
                        name=role_def["name"],
                        description=role_def["description"],
                        permissions=role_def["permissions"],
                        is_system=True,
                    )
                )

        temp_password = _random_password()
        superadmin = User(
            tenant_id=None,
            username="superadmin",
            email="superadmin@pmoaas.local",
            password_hash=hash_password(temp_password),
            full_name="Platform Super Admin",
            is_active=True,
            is_superadmin=True,
            must_change_password=True,
            locale="es-MX",
        )
        db.add(superadmin)
        await db.commit()
        logger.warning(
            "[seed] superadmin created: email=%s temp_password=%s (change immediately, "
            "then set SEED_ON_STARTUP=false)",
            superadmin.email,
            temp_password,
        )
