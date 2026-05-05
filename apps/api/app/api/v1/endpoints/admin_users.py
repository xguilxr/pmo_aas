import secrets
import string
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_capability
from app.core.errors import business_rule, conflict, forbidden, not_found, validation_error
from app.core.hard_delete import confirm_slug, ensure_confirm, ensure_inactive
from app.core.security import hash_password, validate_password_policy
from app.db.session import get_db
from app.models.organization import Organization
from app.models.organization_user_exclusion import OrganizationUserExclusion
from app.models.permission_request import PermissionChangeRequest
from app.models.project_member import ProjectMember
from app.models.project_request import ProjectRequest
from app.models.role import Role, UserRole
from app.models.user import User
from app.schemas.hard_delete import HardDeletePreview
from app.schemas.user import (
    ExcludedOrganizationsBody,
    ExcludedOrganizationsRead,
    PaginatedUsers,
    UserCreate,
    UserRead,
    UserResetPasswordResponse,
    UserUpdate,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/admin/users", tags=["admin.users"])


def _random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _ensure_same_tenant(cu: CurrentUser, target_tenant_id: UUID | None) -> None:
    if cu.is_superadmin:
        return
    if cu.user.tenant_id != target_tenant_id:
        raise forbidden()


async def _user_roles(db: AsyncSession, user_id: UUID) -> list[str]:
    rows = (
        await db.execute(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
        )
    ).scalars().all()
    return list(rows)


async def _serialize(db: AsyncSession, u: User) -> UserRead:
    return UserRead(
        id=u.id, username=u.username, email=u.email, full_name=u.full_name,
        is_active=u.is_active, must_change_password=u.must_change_password,
        last_login=u.last_login.isoformat() if u.last_login else None,
        roles=await _user_roles(db, u.id),
        role_type=u.role_type,
    )


@router.get("", response_model=PaginatedUsers)
async def list_users(
    q: str | None = Query(default=None),
    role_id: UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User)
    if not cu.is_superadmin:
        stmt = stmt.where(User.tenant_id == cu.user.tenant_id)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.full_name).like(like),
                func.lower(User.username).like(like),
                func.lower(User.email).like(like),
            )
        )
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if role_id is not None:
        stmt = stmt.join(UserRole, UserRole.user_id == User.id).where(UserRole.role_id == str(role_id))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await db.execute(stmt.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit))
    ).scalars().all()

    items = [await _serialize(db, u) for u in rows]
    return PaginatedUsers(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=UserRead, status_code=201)
async def create_user(
    body: UserCreate,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    ok, err = validate_password_policy(body.password)
    if not ok:
        raise validation_error("Contraseña no cumple política", {"code": err})

    tenant_id = cu.user.tenant_id
    if tenant_id is None and not cu.is_superadmin:
        raise forbidden()

    username = body.username.strip().lower()
    email = body.email.lower()
    existing = (
        await db.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                or_(User.username == username, User.email == email),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise conflict("username o email duplicado")

    if body.role_ids:
        valid_roles = (
            await db.execute(
                select(Role.id).where(Role.tenant_id == tenant_id, Role.id.in_([str(r) for r in body.role_ids]))
            )
        ).scalars().all()
        if len(valid_roles) != len(body.role_ids):
            raise validation_error("Uno o más role_ids inválidos")

    user = User(
        tenant_id=tenant_id,
        username=username,
        email=email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        is_active=body.is_active,
        role_type=body.role_type,  # US-078
        # US-089: usuarios creados por admin deben cambiar password
        # en su primer login (el password viaja por email, riesgo no-cero).
        must_change_password=True,
    )
    db.add(user)
    await db.flush()
    for rid in body.role_ids:
        db.add(UserRole(user_id=user.id, role_id=str(rid)))

    # US-078: aplicar exclusiones de orgs al alta. Default = ninguna.
    if body.excluded_organization_ids:
        valid_orgs = (
            await db.execute(
                select(Organization.id).where(
                    Organization.tenant_id == tenant_id,
                    Organization.id.in_([str(o) for o in body.excluded_organization_ids]),
                )
            )
        ).scalars().all()
        for oid in valid_orgs:
            db.add(
                OrganizationUserExclusion(
                    user_id=user.id, organization_id=oid, created_by_user_id=cu.id
                )
            )

    # US-089: enviar email de bienvenida con credenciales (post-flush, pre-commit
    # para que un fallo de Resend no marque el user como creado en BD).
    welcome_email_sent = await _send_welcome_email(
        db,
        tenant_id=tenant_id,
        full_name=body.full_name,
        email=email,
        username=username,
        password=body.password,
    )

    await write_audit(
        db, action="user.create", module="admin.users", user_id=cu.id, tenant_id=tenant_id,
        entity_type="user", entity_id=str(user.id),
        details={
            "username": username,
            "email": email,
            "role_type": body.role_type,
            "welcome_email_sent": welcome_email_sent,
        },
    )
    await db.commit()
    return await _serialize(db, user)


async def _send_welcome_email(
    db: AsyncSession,
    *,
    tenant_id: UUID | None,
    full_name: str,
    email: str,
    username: str,
    password: str,
) -> bool:
    """US-089: envía email de bienvenida con credenciales. Devuelve True
    si el send completó (Resend ack); False si Resend está deshabilitado
    o si el send falló (no levanta — el user ya está creado en DB).
    """
    import logging

    from app.models.tenant import Tenant
    from app.services.email import (
        build_welcome_email_html,
        send_email_via_resend,
    )

    log = logging.getLogger(__name__)

    tenant_name: str | None = None
    tenant_logo_url: str | None = None
    if tenant_id:
        t = (
            await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
        ).scalar_one_or_none()
        if t is not None:
            tenant_name = t.name
            tenant_logo_url = (t.settings or {}).get("branding", {}).get("logo_url")

    html = build_welcome_email_html(
        full_name=full_name,
        email=email,
        username=username,
        password=password,
        tenant_name=tenant_name,
        tenant_logo_url=tenant_logo_url,
    )
    subject = f"Bienvenido a {tenant_name or 'PMO·aaS'} — credenciales de acceso"
    try:
        result = await send_email_via_resend(to=email, subject=subject, html=html)
    except Exception as exc:
        log.warning("welcome email send failed: %s", exc)
        return False
    return result is not None


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    u = (await db.execute(select(User).where(User.id == str(user_id)))).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)
    return await _serialize(db, u)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    u = (await db.execute(select(User).where(User.id == str(user_id)))).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)

    if body.full_name is not None:
        u.full_name = body.full_name
    if body.email is not None:
        u.email = body.email.lower()
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.role_ids is not None:
        await db.execute(delete(UserRole).where(UserRole.user_id == u.id))
        for rid in body.role_ids:
            db.add(UserRole(user_id=u.id, role_id=str(rid)))
    # US-078: cambio de role_type (admin ↔ user).
    if body.role_type is not None:
        u.role_type = body.role_type
    # US-078: forzar cambio de password en próximo login (sin tocar
    # password actual). Si pasa False, lo desmarca.
    if body.must_change_password is not None:
        u.must_change_password = body.must_change_password

    await write_audit(
        db, action="user.update", module="admin.users", user_id=cu.id, tenant_id=u.tenant_id,
        entity_type="user", entity_id=str(u.id),
    )
    await db.commit()
    return await _serialize(db, u)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    u = (await db.execute(select(User).where(User.id == str(user_id)))).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)
    if u.is_superadmin:
        raise business_rule("No se puede borrar un super admin desde el panel de tenant")
    u.is_active = False  # soft delete
    await write_audit(
        db, action="user.delete", module="admin.users", user_id=cu.id, tenant_id=u.tenant_id,
        entity_type="user", entity_id=str(u.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.post("/{user_id}/reset-password", response_model=UserResetPasswordResponse)
async def reset_password(
    user_id: UUID,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    u = (await db.execute(select(User).where(User.id == str(user_id)))).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)
    temp = _random_password()
    u.password_hash = hash_password(temp)
    u.must_change_password = True
    u.failed_login_attempts = 0
    u.locked_until = None
    await write_audit(
        db, action="password_reset_by_admin", module="admin.users",
        user_id=cu.id, tenant_id=u.tenant_id, entity_type="user", entity_id=str(u.id),
    )
    await db.commit()
    return UserResetPasswordResponse(temp_password=temp)


@router.post("/{user_id}/unlock", status_code=204)
async def unlock_user(
    user_id: UUID,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    u = (await db.execute(select(User).where(User.id == str(user_id)))).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)
    u.failed_login_attempts = 0
    u.locked_until = None
    await write_audit(
        db, action="account_unlocked", module="admin.users",
        user_id=cu.id, tenant_id=u.tenant_id, entity_type="user", entity_id=str(u.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


# ---------------------------------------------------------------------
# US-078 — force-password-change y membership opt-out de organizaciones
# ---------------------------------------------------------------------


@router.post("/{user_id}/force-password-change", status_code=204)
async def force_password_change(
    user_id: UUID,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Marca al user para que cambie password en su próximo login,
    SIN modificar el password actual. Si lo que se quiere es resetear
    el password, usar `/reset-password` (US-074 / pre-existente)."""
    u = (await db.execute(select(User).where(User.id == str(user_id)))).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)
    u.must_change_password = True
    await write_audit(
        db, action="user.force_password_change", module="admin.users",
        user_id=cu.id, tenant_id=u.tenant_id, entity_type="user", entity_id=str(u.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.get(
    "/{user_id}/excluded-organizations", response_model=ExcludedOrganizationsRead
)
async def list_excluded_organizations(
    user_id: UUID,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Lista IDs de orgs **excluidas** para este user. Default: ninguna
    (acceso a todas las orgs del tenant)."""
    u = (
        await db.execute(select(User).where(User.id == str(user_id)))
    ).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)
    rows = (
        await db.execute(
            select(OrganizationUserExclusion.organization_id).where(
                OrganizationUserExclusion.user_id == str(user_id)
            )
        )
    ).scalars().all()
    return ExcludedOrganizationsRead(organization_ids=[UUID(x) for x in rows])


@router.put(
    "/{user_id}/excluded-organizations", response_model=ExcludedOrganizationsRead
)
async def replace_excluded_organizations(
    user_id: UUID,
    body: ExcludedOrganizationsBody,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Reemplaza atómicamente el set de orgs excluidas para este user.
    Idempotente: enviar `[]` limpia las exclusiones (acceso completo)."""
    u = (
        await db.execute(select(User).where(User.id == str(user_id)))
    ).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)

    target_ids = {str(o) for o in body.organization_ids}
    if target_ids:
        valid = (
            await db.execute(
                select(Organization.id).where(
                    Organization.tenant_id == u.tenant_id,
                    Organization.id.in_(list(target_ids)),
                )
            )
        ).scalars().all()
        if len(valid) != len(target_ids):
            raise validation_error(
                "Una o más organization_ids no pertenecen al tenant del usuario"
            )

    await db.execute(
        delete(OrganizationUserExclusion).where(
            OrganizationUserExclusion.user_id == str(user_id)
        )
    )
    for oid in target_ids:
        db.add(
            OrganizationUserExclusion(
                user_id=str(user_id),
                organization_id=oid,
                created_by_user_id=cu.id,
            )
        )
    await write_audit(
        db,
        action="user.excluded_orgs_set",
        module="admin.users",
        user_id=cu.id,
        tenant_id=u.tenant_id,
        entity_type="user",
        entity_id=str(user_id),
        details={"count": len(target_ids)},
    )
    await db.commit()
    return ExcludedOrganizationsRead(
        organization_ids=[UUID(x) for x in target_ids]
    )


# =============================================================================
# US-088 — Hard delete (segundo paso) para usuarios
# =============================================================================
# Cascade strategy: el FK CASCADE cubre auth/sessions, role, project_member,
# notifications, organization_user_exclusion. Pero hay tablas con
# `requested_by NOT NULL` (project_requests, permission_requests) que
# bloquearían el delete. Si existen referencias bloqueantes, devolvemos
# `blockers` en el preview y el endpoint DELETE responde 409 con detalle.
# Las FKs nullable se settean a NULL antes del delete.
# -----------------------------------------------------------------------------


def _slug(u: User) -> str:
    return confirm_slug("user", u.username or u.email or u.id)


async def _user_blockers(db: AsyncSession, u: User) -> dict[str, int]:
    pr_count = (
        await db.execute(
            select(func.count(ProjectRequest.id)).where(ProjectRequest.requested_by == u.id)
        )
    ).scalar_one()
    perm_req_count = (
        await db.execute(
            select(func.count(PermissionChangeRequest.id)).where(
                PermissionChangeRequest.requested_by_user_id == u.id
            )
        )
    ).scalar_one()
    out: dict[str, int] = {}
    if pr_count:
        out["project_requests_as_requester"] = pr_count
    if perm_req_count:
        out["permission_requests_as_requester"] = perm_req_count
    return out


@router.get(
    "/{user_id}/hard-delete-preview", response_model=HardDeletePreview
)
async def preview_hard_delete_user(
    user_id: UUID,
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    u = (await db.execute(select(User).where(User.id == str(user_id)))).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)
    if u.is_superadmin:
        raise business_rule("No se puede borrar un super admin desde el panel de tenant")
    blockers_map = await _user_blockers(db, u)
    return HardDeletePreview(
        entity_type="user",
        entity_id=str(u.id),
        entity_name=u.full_name or u.username,
        is_active=u.is_active,
        confirm_slug=_slug(u),
        cascades={
            "memberships": (await db.execute(
                select(func.count()).select_from(ProjectMember).where(ProjectMember.user_id == u.id)
            )).scalar_one(),
        },
        blockers=[f"{k}={v}" for k, v in blockers_map.items()],
    )


@router.delete("/{user_id}/permanent", status_code=204)
async def hard_delete_user(
    user_id: UUID,
    confirm: str = Query(...),
    cu: CurrentUser = Depends(require_capability("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update

    from app.models.modules import (
        ChangeRequest,
        Document,
        Issue,
        Lesson,
        MeetingMinute,
        Risk,
    )
    from app.models.organization import BusinessUnit, Department
    from app.models.project import Project
    from app.models.project_area import ProjectArea
    from app.models.project_charter import ProjectCharter
    from app.models.stakeholder import Stakeholder
    from app.models.task import Task

    u = (await db.execute(select(User).where(User.id == str(user_id)))).scalar_one_or_none()
    if u is None:
        raise not_found("Usuario")
    _ensure_same_tenant(cu, u.tenant_id)
    if u.is_superadmin:
        raise business_rule("No se puede borrar un super admin desde el panel de tenant")
    ensure_inactive(u.is_active, "Usuario")

    blockers_map = await _user_blockers(db, u)
    if blockers_map:
        raise conflict(
            "No se puede eliminar permanentemente: el usuario tiene referencias "
            "que requieren limpieza manual previa.",
            code="USER_HAS_BLOCKING_REFS",
            fields={"blockers": blockers_map},
        )
    ensure_confirm(confirm, _slug(u))

    # Settear a NULL las FKs nullable que apuntan al user (no hay ondelete=SET NULL).
    nullable_fks = [
        (Project, "pm_id"),
        (ProjectCharter, "pm_id"),
        (ProjectCharter, "created_by"),
        (Stakeholder, "created_by"),
        (BusinessUnit, "created_by"),
        (Department, "created_by"),
        (ProjectArea, "created_by"),
        (Task, "owner_id"),
        (Risk, "created_by"),
        (Risk, "owner_id"),
        (Issue, "created_by"),
        (Issue, "owner_id"),
        (ChangeRequest, "created_by"),
        (ChangeRequest, "requested_by"),
        (ChangeRequest, "approved_by"),
        (Document, "created_by"),
        (Document, "uploaded_by"),
        (Lesson, "created_by"),
        (MeetingMinute, "created_by"),
    ]
    for model, attr in nullable_fks:
        col = getattr(model, attr)
        await db.execute(update(model).where(col == u.id).values({attr: None}))
    await db.flush()
    await db.delete(u)
    await write_audit(
        db, action="user.hard_delete", module="admin.users",
        user_id=cu.id, tenant_id=u.tenant_id, entity_type="user", entity_id=str(u.id),
        details={"username": u.username, "email": u.email},
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)
