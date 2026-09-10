"""Crea un tenant desechable para demos/QA, sin código de correo real.

ENH-203: el tenant se configura con `settings.otp_codigo_fijo` — el segundo
factor (MFA, ASVS 4.3.1) sigue exigido a sus administradores, pero el código
que valida es siempre el mismo, así que quien hace la demo no depende de un
buzón. Con `--sin-mfa` el tenant queda con `settings.mfa_enabled=False` y sus
administradores no reciben ningún desafío.

Uso:
  cd apps/api
  python -m app.scripts.seed_demo_qa
  python -m app.scripts.seed_demo_qa --slug mi-demo --codigo 111111
  python -m app.scripts.seed_demo_qa --sin-mfa

Para borrar el ambiente cuando termine la demo:
  DELETE FROM tenants WHERE slug = '<slug>';  -- cascada sobre sus datos
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from app.db.session import SessionLocal
from app.services.seed import _ensure_system_roles, _ensure_tenant, _ensure_tenant_admin

logger = logging.getLogger(__name__)


async def crear_tenant_demo_qa(*, slug: str, nombre: str, codigo: str | None, sin_mfa: bool) -> None:
    settings: dict = {"locale": "es-MX", "currency": "MXN", "ai_mode": "disabled"}
    if sin_mfa:
        settings["mfa_enabled"] = False
    elif codigo:
        settings["otp_codigo_fijo"] = codigo

    async with SessionLocal() as db:
        tenant, creado = await _ensure_tenant(db, slug=slug, name=nombre, settings=settings)
        if not creado:
            logger.info("[seed_demo_qa] tenant ya existía: %s (no se tocan sus settings)", slug)
        roles = await _ensure_system_roles(db, tenant)
        admin_user, admin_pwd = await _ensure_tenant_admin(
            db,
            tenant=tenant,
            username="admin",
            email=f"admin@{slug}.demo.local",
            full_name="Admin Demo QA",
            admin_role=roles["Administrador"],
        )
        await db.commit()

    print(f"Tenant: {tenant.slug} ({'creado' if creado else 'ya existía'})")
    print(f"Admin:  {admin_user.email}")
    if admin_pwd:
        print(f"Password inicial: {admin_pwd} (must_change_password=True)")
    else:
        print("Password: ya existía, no se generó una nueva")
    if sin_mfa:
        print("MFA: deshabilitado para este tenant (settings.mfa_enabled=False)")
    elif codigo:
        print(f"Código MFA fijo: {codigo}")
    print(f"Borrar luego con: DELETE FROM tenants WHERE slug = '{slug}';")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default="demo-qa")
    parser.add_argument("--nombre", default="Demo QA")
    parser.add_argument("--codigo", default="000000", help="Código MFA fijo (ignorado si --sin-mfa)")
    parser.add_argument("--sin-mfa", action="store_true", help="Desactiva el segundo factor del tenant")
    args = parser.parse_args()
    asyncio.run(
        crear_tenant_demo_qa(
            slug=args.slug, nombre=args.nombre, codigo=args.codigo, sin_mfa=args.sin_mfa
        )
    )


if __name__ == "__main__":
    main()
