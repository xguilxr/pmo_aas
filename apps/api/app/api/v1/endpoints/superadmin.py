import secrets
import string
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_superadmin
from app.core.errors import business_rule, conflict, forbidden, mensaje, not_found, validation_error
from app.core.security import (
    create_access_token,
    hash_password,
    mensaje_de_politica,
    validate_password_policy,
)
from app.db.session import get_db
from app.models.organization import Program
from app.models.role import Role, UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.organization import (
    TenantProvisionRequest,
    TenantProvisionResponse,
    TenantRead,
)
from app.services.audit import write_audit
from app.services.seed import SYSTEM_ROLES

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


def _random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    # Garantizar cumple política
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        ok, _ = validate_password_policy(pwd)
        if ok:
            return pwd


@router.post("/provision", response_model=TenantProvisionResponse, status_code=201)
async def provision_tenant(
    body: TenantProvisionRequest,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    slug = body.slug.lower()
    existing = (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()
    if existing is not None:
        raise conflict(mensaje(
            que="slug de tenant duplicado",
            porque="El identificador va en la URL y tiene que ser único.",
            accion="Elige otro identificador.",
        ), code="SLUG_DUPLICATE")

    tenant = Tenant(slug=slug, name=body.name, is_active=True, settings={})
    db.add(tenant)
    await db.flush()

    admin_role = None
    for r in SYSTEM_ROLES:
        role = Role(
            tenant_id=tenant.id, name=r["name"], description=r["description"],
            permissions=r["permissions"], is_system=True,
        )
        db.add(role)
        await db.flush()
        if r["name"] == "Administrador":
            admin_role = role

    pwd = body.admin_password or _random_password()
    ok, err = validate_password_policy(pwd)
    if not ok:
        raise validation_error(mensaje_de_politica(err), {"code": err})

    username = (body.admin_username or body.admin_email.split("@")[0]).lower()
    user = User(
        tenant_id=tenant.id,
        username=username,
        email=body.admin_email.lower(),
        full_name=body.admin_full_name,
        password_hash=hash_password(pwd),
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=admin_role.id))
    # US-076 (role_type fijo): el admin recién provisionado debe tener
    # `role_type=admin` para que las capabilities admin estén activas.
    user.role_type = "admin"

    # ENH-080: enviar email de bienvenida + setup al admin del tenant
    # nuevo. Pre-commit para que un fail de Resend no enmascare el
    # provisioning, pero guardamos el flag en el audit log.
    welcome_sent = await _send_tenant_welcome_email(
        tenant_name=body.name,
        tenant_slug=slug,
        admin_full_name=body.admin_full_name,
        admin_email=body.admin_email.lower(),
        admin_username=username,
        admin_password=pwd,
    )

    await write_audit(
        db, action="tenant.provisioned", module="superadmin", user_id=cu.id,
        entity_type="tenant", entity_id=str(tenant.id),
        details={
            "slug": slug,
            "admin_user_id": str(user.id),
            "welcome_email_sent": welcome_sent,
        },
    )
    await db.commit()
    return TenantProvisionResponse(
        tenant_id=tenant.id, slug=slug, admin_user_id=user.id, admin_password=pwd,
    )


async def _send_tenant_welcome_email(
    *,
    tenant_name: str,
    tenant_slug: str,
    admin_full_name: str,
    admin_email: str,
    admin_username: str,
    admin_password: str,
) -> bool:
    """ENH-080 — bienvenida al admin de un tenant recién provisionado.

    Incluye credenciales + manual de montaje inicial (organizaciones →
    usuarios → primer proyecto). Devuelve True si Resend ack, False si
    canal deshabilitado o falla (no levanta — el tenant ya existe).
    """
    import logging

    from app.core.config import settings as _settings
    from app.services.email import send_email_via_resend

    log = logging.getLogger(__name__)
    login_url = f"{_settings.APP_BASE_URL}/login"
    admin_url = f"{_settings.APP_BASE_URL}/admin"
    html = f"""<!DOCTYPE html>
<html lang="es">
<body style="font-family:-apple-system,Segoe UI,sans-serif;background:#f8fafc;margin:0;padding:24px;color:#0f172a">
<table role="presentation" align="center" width="600" style="background:#fff;border-radius:12px;padding:28px;border:1px solid #e2e8f0">
<tr><td>
<div style="font-weight:600;color:#182e4e;margin-bottom:16px;font-size:14px">PMO·aaS</div>
<h2 style="margin:0 0 8px">Bienvenido a PMO·aaS — tenant <em>{tenant_name}</em></h2>
<p style="color:#334155;line-height:1.5">
Hola {admin_full_name}, tu tenant fue creado y eres el administrador
inicial. Estas son tus credenciales (cámbialas en el primer login):
</p>
<table role="presentation" cellpadding="6" cellspacing="0" style="background:#f1f5f9;border-radius:8px;width:100%;font-size:14px">
  <tr><td style="font-weight:600;color:#475569;width:140px">Tenant</td><td>{tenant_name} <code style="font-size:12px;color:#64748b">({tenant_slug})</code></td></tr>
  <tr><td style="font-weight:600;color:#475569">Email</td><td>{admin_email}</td></tr>
  <tr><td style="font-weight:600;color:#475569">Usuario</td><td>{admin_username}</td></tr>
  <tr><td style="font-weight:600;color:#475569">Contraseña</td><td><code style="background:#fff;padding:2px 6px;border-radius:4px;border:1px solid #e2e8f0">{admin_password}</code></td></tr>
</table>
<p style="margin-top:20px"><a href="{login_url}" style="display:inline-block;padding:10px 18px;background:#182e4e;color:#fff;border-radius:6px;text-decoration:none">Iniciar sesión</a></p>
<hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0"/>
<h3 style="margin:0 0 8px;color:#0f172a">Manual de montaje inicial</h3>
<ol style="color:#334155;line-height:1.6;padding-left:20px">
  <li>Inicia sesión en <a href="{login_url}">{login_url}</a> y cambia la contraseña.</li>
  <li>Configura branding y datos del tenant en <a href="{admin_url}/tenant">/admin/tenant</a>.</li>
  <li>Crea tus organizaciones y áreas en <a href="{admin_url}/organizations">/admin/organizations</a>.</li>
  <li>Da de alta a los usuarios del equipo desde <a href="{admin_url}/users">/admin/users</a> (cada uno recibirá un correo con sus credenciales).</li>
  <li>Define permisos por rol en <a href="{admin_url}/permissions">/admin/permissions</a>.</li>
  <li>Configura el proveedor de IA (opcional) en <a href="{admin_url}/ai">/admin/ai</a>.</li>
  <li>Levanta tu primer proyecto desde <a href="{_settings.APP_BASE_URL}/pmo/projects/new">/pmo/projects/new</a>.</li>
</ol>
<p style="color:#334155;line-height:1.5;margin-top:16px">
Cualquier duda responde a este correo y el equipo PMO·aaS te acompaña en el setup.
</p>
<hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0"/>
<p style="font-size:12px;color:#64748b">
Si no esperabas este correo, contacta al super administrador que provisionó el tenant.
</p>
</td></tr>
</table>
</body></html>
"""
    subject = f"Bienvenido a PMO·aaS — tenant {tenant_name} listo"
    try:
        result = await send_email_via_resend(
            to=admin_email, subject=subject, html=html
        )
    except Exception as exc:
        log.warning("tenant welcome email send failed: %s", exc)
        return False
    return result is not None


@router.get("/tenants", response_model=list[TenantRead])
async def list_tenants(
    include_inactive: bool = Query(default=False),
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.organization import Organization
    from app.models.project import Project

    stmt = select(Tenant)
    if not include_inactive:
        stmt = stmt.where(Tenant.is_active.is_(True))
    tenants = (await db.execute(stmt.order_by(Tenant.slug))).scalars().all()
    if not tenants:
        return []

    tenant_ids = [t.id for t in tenants]

    # Counts por tenant en batch (US-025).
    def grouped(stmt):
        return {str(tid): int(n) for tid, n in stmt}

    users_rows = (
        await db.execute(
            select(User.tenant_id, func.count(User.id))
            .where(User.tenant_id.in_(tenant_ids))
            .group_by(User.tenant_id)
        )
    ).all()
    user_counts = grouped(users_rows)

    orgs_rows = (
        await db.execute(
            select(Organization.tenant_id, func.count(Organization.id))
            .where(Organization.tenant_id.in_(tenant_ids))
            .group_by(Organization.tenant_id)
        )
    ).all()
    org_counts = grouped(orgs_rows)

    progs_rows = (
        await db.execute(
            select(Program.tenant_id, func.count(Program.id))
            .where(Program.tenant_id.in_(tenant_ids))
            .group_by(Program.tenant_id)
        )
    ).all()
    program_counts = grouped(progs_rows)

    projs_rows = (
        await db.execute(
            select(Project.tenant_id, func.count(Project.id))
            .where(
                Project.tenant_id.in_(tenant_ids), Project.deleted_at.is_(None)
            )
            .group_by(Project.tenant_id)
        )
    ).all()
    project_counts = grouped(projs_rows)

    out: list[TenantRead] = []
    for t in tenants:
        tid = str(t.id)
        out.append(
            TenantRead(
                id=t.id,
                slug=t.slug,
                name=t.name,
                is_active=t.is_active,
                user_count=user_counts.get(tid, 0),
                organization_count=org_counts.get(tid, 0),
                program_count=program_counts.get(tid, 0),
                project_count=project_counts.get(tid, 0),
            )
        )
    return out


@router.get("/tenants/{tenant_id}/detail")
async def tenant_detail(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    # BUG-033: incluye `role_type` y `is_superadmin` para que la sección
    # de Usuarios en /superadmin/tenants/[id] pueda mostrar dropdown
    # editable inline (descubre la funcionalidad sin requerir navegar
    # al panel /users dedicado).
    users = (
        await db.execute(
            select(
                User.id,
                User.username,
                User.email,
                User.is_active,
                User.role_type,
                User.is_superadmin,
            ).where(User.tenant_id == t.id)
        )
    ).all()
    from app.models.organization import Organization

    orgs = (
        await db.execute(
            select(Organization.id, Organization.name, Organization.is_active).where(
                Organization.tenant_id == t.id
            )
        )
    ).all()
    programs = (
        await db.execute(
            select(Program.id, Program.name, Program.organization_id).where(Program.tenant_id == t.id)
        )
    ).all()
    # Jerarquía: counts globales por tenant (US-025).
    from app.models.organization import BusinessUnit, Department
    from app.models.project import Project

    bu_count = (
        await db.execute(
            select(func.count(BusinessUnit.id)).where(
                BusinessUnit.tenant_id == t.id, BusinessUnit.deleted_at.is_(None)
            )
        )
    ).scalar_one() or 0
    dept_count = (
        await db.execute(
            select(func.count(Department.id)).where(
                Department.tenant_id == t.id, Department.deleted_at.is_(None)
            )
        )
    ).scalar_one() or 0
    project_count = (
        await db.execute(
            select(func.count(Project.id)).where(
                Project.tenant_id == t.id, Project.deleted_at.is_(None)
            )
        )
    ).scalar_one() or 0

    return {
        "tenant": {"id": str(t.id), "slug": t.slug, "name": t.name, "is_active": t.is_active},
        "users": [
            {
                "id": str(r.id),
                "username": r.username,
                "email": r.email,
                "is_active": r.is_active,
                "role_type": r.role_type,
                "is_superadmin": r.is_superadmin,
            }
            for r in users
        ],
        "organizations": [{"id": str(r.id), "name": r.name, "is_active": r.is_active} for r in orgs],
        "programs": [{"id": str(r.id), "name": r.name, "organization_id": str(r.organization_id)} for r in programs],
        "hierarchy": {
            "organization_count": len(orgs),
            "business_unit_count": int(bu_count),
            "department_count": int(dept_count),
            "program_count": len(programs),
            "project_count": int(project_count),
        },
    }


@router.delete("/tenants/{tenant_id}", status_code=204)
async def soft_delete_tenant(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    t.is_active = False
    await write_audit(
        db, action="tenant.soft_delete", module="superadmin", user_id=cu.id,
        entity_type="tenant", entity_id=str(t.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.delete("/tenants/{tenant_id}/permanent", status_code=204)
async def hard_delete_tenant(
    tenant_id: UUID,
    confirm_slug: str = Query(...),
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    if confirm_slug != t.slug:
        raise business_rule(mensaje(
            que="confirm_slug no coincide con el slug del tenant",
            porque="La confirmación escrita a mano es lo único que separa esta acción de un clic accidental.",
            accion="Escribe el identificador exacto del tenant tal como aparece en su ficha.",
        ))
    await write_audit(
        db, action="tenant.hard_delete", module="superadmin", user_id=cu.id,
        entity_type="tenant", entity_id=str(t.id), details={"slug": t.slug},
    )
    await db.delete(t)  # cascade elimina todo
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.post("/tenants/{tenant_id}/join-as-admin")
async def join_as_admin(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    admin_role = (
        await db.execute(
            select(Role).where(Role.tenant_id == t.id, Role.name == "Administrador")
        )
    ).scalar_one_or_none()
    if admin_role is None:
        raise business_rule(mensaje(
            que="Tenant no tiene rol Administrador; re-seed",
            porque="La organización se creó sin su rol de administración y nadie podría gestionarla.",
            accion="Vuelve a sembrar los roles del tenant desde el panel de plataforma.",
        ))

    existing_ur = (
        await db.execute(
            select(UserRole).where(UserRole.user_id == cu.id, UserRole.role_id == admin_role.id)
        )
    ).scalar_one_or_none()
    if existing_ur is None:
        db.add(UserRole(user_id=cu.id, role_id=admin_role.id))

    await write_audit(
        db, action="superadmin.join_as_admin", module="superadmin", user_id=cu.id,
        tenant_id=t.id, entity_type="tenant", entity_id=str(t.id),
    )
    await db.commit()

    access = create_access_token(
        subject=cu.id,
        tenant_ids=[str(t.id)],
        active_tenant_id=str(t.id),
        is_superadmin=True,
        roles=[*cu.roles, "Administrador"],
    )
    return {"access_token": access, "active_tenant_id": str(t.id), "tenant_slug": t.slug}


# ============================================================================
# US-072 — SuperAdmin: gestionar role_type de usuarios de cualquier tenant
# ============================================================================
# Lección de BUG-031: el sistema necesita una vía explícita para que el
# superadmin recupere/ajuste el role_type de un usuario sin caer al psql
# directo. Endpoints expuestos solo bajo `is_superadmin=True`.

from pydantic import BaseModel, Field  # noqa: E402


class _SuperadminUserRow(BaseModel):
    id: str
    email: str
    username: str
    full_name: str | None = None
    role_type: str | None = None
    is_active: bool
    is_superadmin: bool


class _RoleTypeUpdate(BaseModel):
    role_type: str = Field(pattern=r"^(admin|user|viewer)$")


@router.get(
    "/tenants/{tenant_id}/users",
    response_model=list[_SuperadminUserRow],
)
async def list_tenant_users(
    tenant_id: UUID,
    q: str | None = Query(default=None),
    role_type: str | None = Query(default=None),
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """US-072: lista usuarios del tenant para gestión de roles."""
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    stmt = select(User).where(User.tenant_id == str(t.id))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            (func.lower(User.email).like(like))
            | (func.lower(User.username).like(like))
        )
    if role_type:
        if role_type not in ("admin", "user", "viewer"):
            raise validation_error(mensaje(
                que="role_type debe ser admin|user|viewer",
                porque="El tipo decide qué puede hacer la persona y solo hay esos tres.",
                accion="Elige `admin`, `user` o `viewer`.",
            ))
        stmt = stmt.where(User.role_type == role_type)

    rows = (await db.execute(stmt.order_by(User.email))).scalars().all()
    return [
        _SuperadminUserRow(
            id=str(u.id),
            email=u.email,
            username=u.username,
            full_name=u.full_name,
            role_type=u.role_type,
            is_active=u.is_active,
            is_superadmin=u.is_superadmin,
        )
        for u in rows
    ]


@router.patch("/users/{user_id}/role-type", status_code=200)
async def update_user_role_type(
    user_id: UUID,
    body: _RoleTypeUpdate,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """US-072: superadmin actualiza role_type de un usuario.

    No permite cambiar `is_superadmin` (eso es US-074 + acción manual
    en BD). Audit log queda con from→to para trazabilidad.
    """
    u = (
        await db.execute(select(User).where(User.id == str(user_id)))
    ).scalar_one_or_none()
    if u is None:
        raise not_found("User")

    previous = u.role_type
    if previous == body.role_type:
        return {
            "id": str(u.id),
            "role_type": u.role_type,
            "changed": False,
        }

    u.role_type = body.role_type
    await write_audit(
        db,
        action="superadmin.user_role_type_change",
        module="superadmin",
        user_id=cu.id,
        tenant_id=u.tenant_id,
        entity_type="user",
        entity_id=str(u.id),
        details={"from": previous, "to": body.role_type},
    )
    await db.commit()
    return {
        "id": str(u.id),
        "role_type": u.role_type,
        "from": previous,
        "to": body.role_type,
        "changed": True,
    }


# ============================================================================
# US-074 — SuperAdmin: gestionar su propio email + password
# ============================================================================

from app.core.security import verify_password  # noqa: E402


class _SuperadminMeRead(BaseModel):
    id: str
    email: str
    username: str
    full_name: str | None = None
    is_superadmin: bool


class _SuperadminMeUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    new_password: str | None = None
    current_password: str = Field(min_length=1)
    # BUG-032: si el email destino ya está en uso por otro user
    # (típicamente el propio owner registrado como admin de algún
    # tenant), permite "tomar" el email renombrando al user en
    # conflicto a `released.<ts>.<old_email>` y mover el ownership
    # del email al superadmin. Audit log queda con la migración.
    force_takeover_email: bool = False


@router.get("/me", response_model=_SuperadminMeRead)
async def superadmin_me(
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """US-074: perfil del superadmin actual."""
    u = (
        await db.execute(select(User).where(User.id == cu.id))
    ).scalar_one()
    return _SuperadminMeRead(
        id=str(u.id),
        email=u.email,
        username=u.username,
        full_name=u.full_name,
        is_superadmin=u.is_superadmin,
    )


@router.patch("/me", response_model=_SuperadminMeRead)
async def superadmin_me_update(
    body: _SuperadminMeUpdate,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """US-074: actualiza email/full_name/password del superadmin.

    Cambios sensibles (email + password) requieren `current_password`.
    Email único globalmente — si choca con otro user devuelve 409.
    """
    u = (
        await db.execute(select(User).where(User.id == cu.id))
    ).scalar_one()
    if not verify_password(body.current_password, u.password_hash):
        raise forbidden(mensaje(
            que="current_password incorrecto",
            porque="Cambiar la contraseña exige demostrar que la sesión es de quien dice ser.",
            accion="Vuelve a escribir tu contraseña actual.",
        ))

    diff: dict = {}

    if body.full_name is not None and body.full_name != u.full_name:
        diff["full_name"] = {"from": u.full_name, "to": body.full_name}
        u.full_name = body.full_name

    if body.email is not None and body.email != u.email:
        new_email = body.email.strip().lower()
        # Unicidad global (cualquier tenant + cualquier user activo).
        clash = (
            await db.execute(
                select(User).where(
                    func.lower(User.email) == new_email, User.id != u.id
                )
            )
        ).scalar_one_or_none()
        if clash is not None:
            if not body.force_takeover_email:
                # BUG-032: mensaje detallado para que la UI ofrezca
                # take-over si el owner reconoce el clash como suyo.
                # `extra` viaja en `error.detail.extra` para el cliente.
                raise conflict(
                    mensaje(
                        que="Email ya en uso por otro usuario",
                        porque="El correo identifica la cuenta y no puede repetirse.",
                        accion="Usa otra dirección, o recupera la cuenta existente.",
                    ),
                    code="EMAIL_TAKEN_OFFER_TAKEOVER",
                    fields={
                        "clashing_user_id": str(clash.id),
                        "clashing_user_email": clash.email,
                        "clashing_user_username": clash.username,
                        "clashing_user_tenant_id": (
                            str(clash.tenant_id) if clash.tenant_id else None
                        ),
                    },
                )
            # Liberar el email del user en conflicto: renombrar a
            # `released.<unix_ts>.<old_email>` y guardar diff.
            from time import time as _now_ts

            ts = int(_now_ts())
            released_email = f"released.{ts}.{clash.email}"
            diff["email_takeover"] = {
                "released_user_id": str(clash.id),
                "old_email": clash.email,
                "new_released_email": released_email,
            }
            clash.email = released_email
        diff["email"] = {"from": u.email, "to": new_email}
        u.email = new_email

    if body.new_password is not None:
        if body.new_password == body.current_password:
            raise business_rule(mensaje(
                que="La nueva contraseña debe ser diferente",
                porque="Repetir la anterior no cambia nada si alguien ya la conocía.",
                accion="Elige una contraseña que no hayas usado antes.",
            ))
        ok, err = validate_password_policy(body.new_password)
        if not ok:
            raise validation_error(mensaje_de_politica(err), {"code": err})
        u.password_hash = hash_password(body.new_password)
        diff["password"] = {"changed": True}

    if not diff:
        return _SuperadminMeRead(
            id=str(u.id),
            email=u.email,
            username=u.username,
            full_name=u.full_name,
            is_superadmin=u.is_superadmin,
        )

    await write_audit(
        db,
        action="superadmin.self_update",
        module="superadmin",
        user_id=u.id,
        tenant_id=u.tenant_id,
        entity_type="user",
        entity_id=str(u.id),
        details=diff,
    )
    await db.commit()
    await db.refresh(u)
    return _SuperadminMeRead(
        id=str(u.id),
        email=u.email,
        username=u.username,
        full_name=u.full_name,
        is_superadmin=u.is_superadmin,
    )

# ============================================================================
# US-073 — SuperAdmin: overrides de permisos por tenant (DEC-021)
# ============================================================================

from pydantic import BaseModel, Field  # noqa: E402

from app.models.tenant_permission import TenantRolePermissionOverride  # noqa: E402


class _PermissionOverrideRow(BaseModel):
    id: str
    role_type: str
    module: str
    action: str
    granted: bool
    reason: str
    updated_by_user_id: str | None = None


class _PermissionOverrideUpsert(BaseModel):
    role_type: str = Field(pattern=r"^(admin|user|viewer)$")
    module: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=32)
    granted: bool
    reason: str = Field(min_length=1, max_length=2000)


@router.get(
    "/tenants/{tenant_id}/permission-overrides",
    response_model=list[_PermissionOverrideRow],
)
async def list_permission_overrides(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """US-073: lista overrides de permisos del tenant."""
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    rows = (
        await db.execute(
            select(TenantRolePermissionOverride)
            .where(TenantRolePermissionOverride.tenant_id == str(t.id))
            .order_by(
                TenantRolePermissionOverride.role_type,
                TenantRolePermissionOverride.module,
                TenantRolePermissionOverride.action,
            )
        )
    ).scalars().all()
    return [
        _PermissionOverrideRow(
            id=str(r.id),
            role_type=r.role_type,
            module=r.module,
            action=r.action,
            granted=r.granted,
            reason=r.reason,
            updated_by_user_id=r.updated_by_user_id,
        )
        for r in rows
    ]


@router.put(
    "/tenants/{tenant_id}/permission-overrides",
    response_model=list[_PermissionOverrideRow],
)
async def upsert_permission_overrides(
    tenant_id: UUID,
    body: list[_PermissionOverrideUpsert],
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """US-073: upsert batch de overrides. Reemplaza por (role_type, module,
    action). Cada item exige `reason` no vacía → audit log."""
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    diff: list[dict] = []
    for item in body:
        existing = (
            await db.execute(
                select(TenantRolePermissionOverride).where(
                    TenantRolePermissionOverride.tenant_id == str(t.id),
                    TenantRolePermissionOverride.role_type == item.role_type,
                    TenantRolePermissionOverride.module == item.module,
                    TenantRolePermissionOverride.action == item.action,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.granted = item.granted
            existing.reason = item.reason
            existing.updated_by_user_id = str(cu.id)
            diff.append(
                {
                    "op": "update",
                    "role_type": item.role_type,
                    "module": item.module,
                    "action": item.action,
                    "granted": item.granted,
                }
            )
        else:
            db.add(
                TenantRolePermissionOverride(
                    tenant_id=str(t.id),
                    role_type=item.role_type,
                    module=item.module,
                    action=item.action,
                    granted=item.granted,
                    reason=item.reason,
                    updated_by_user_id=str(cu.id),
                )
            )
            diff.append(
                {
                    "op": "create",
                    "role_type": item.role_type,
                    "module": item.module,
                    "action": item.action,
                    "granted": item.granted,
                }
            )

    if diff:
        await write_audit(
            db,
            action="superadmin.permission_override_set",
            module="superadmin",
            user_id=cu.id,
            tenant_id=str(t.id),
            entity_type="tenant",
            entity_id=str(t.id),
            details={"changes": diff},
        )
    await db.commit()

    rows = (
        await db.execute(
            select(TenantRolePermissionOverride)
            .where(TenantRolePermissionOverride.tenant_id == str(t.id))
            .order_by(
                TenantRolePermissionOverride.role_type,
                TenantRolePermissionOverride.module,
                TenantRolePermissionOverride.action,
            )
        )
    ).scalars().all()
    return [
        _PermissionOverrideRow(
            id=str(r.id),
            role_type=r.role_type,
            module=r.module,
            action=r.action,
            granted=r.granted,
            reason=r.reason,
            updated_by_user_id=r.updated_by_user_id,
        )
        for r in rows
    ]


@router.delete(
    "/tenants/{tenant_id}/permission-overrides/{override_id}",
    status_code=204,
)
async def delete_permission_override(
    tenant_id: UUID,
    override_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """US-073: borra un override (vuelve al default del mapping)."""
    o = (
        await db.execute(
            select(TenantRolePermissionOverride).where(
                TenantRolePermissionOverride.id == str(override_id),
                TenantRolePermissionOverride.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if o is None:
        raise not_found("Override")
    snapshot = {
        "op": "delete",
        "role_type": o.role_type,
        "module": o.module,
        "action": o.action,
        "granted": o.granted,
    }
    await db.delete(o)
    await write_audit(
        db,
        action="superadmin.permission_override_set",
        module="superadmin",
        user_id=cu.id,
        tenant_id=str(tenant_id),
        entity_type="tenant",
        entity_id=str(tenant_id),
        details={"changes": [snapshot]},
    )
    await db.commit()
    from fastapi import Response

    return Response(status_code=204)
