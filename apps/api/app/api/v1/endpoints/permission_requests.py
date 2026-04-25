"""US-082 — Permission change requests.

Flujo: el admin del tenant abre un "ticket" pidiendo cambio puntual
de permiso para un usuario. El superadmin recibe notificación in-app
+ email (vía Resend) y aprueba/rechaza desde su panel. Al aprobar,
se crea/actualiza el override correspondiente en
`tenant_role_permission_overrides` (US-073).

Endpoints:
- POST   /api/v1/permission-requests                      (admin tenant)
- GET    /api/v1/permission-requests?status=&mine=        (admin / superadmin)
- DELETE /api/v1/permission-requests/{id}                 (admin cancela)
- POST   /api/v1/superadmin/permission-requests/{id}/approve
- POST   /api/v1/superadmin/permission-requests/{id}/reject
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    get_superadmin,
    require_authenticated,
)
from app.core.errors import business_rule, conflict, forbidden, not_found
from app.db.session import get_db
from app.models.notification import Notification
from app.models.permission_request import PermissionChangeRequest
from app.models.tenant_permission import TenantRolePermissionOverride
from app.models.user import User
from app.services.audit import write_audit
from app.services.email import send_email_via_resend

router = APIRouter(tags=["permission-requests"])


# ---------- Schemas ----------
class _CreateBody(BaseModel):
    target_user_id: UUID
    module: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=32)
    requested_grant: bool = True
    reason: str = Field(min_length=10, max_length=2000)


class _RejectBody(BaseModel):
    decision_note: str = Field(min_length=1, max_length=2000)


class _UserMini(BaseModel):
    id: str
    email: str
    full_name: str | None = None


class _RequestRead(BaseModel):
    id: str
    tenant_id: str
    requested_by: _UserMini | None
    target_user: _UserMini | None
    module: str
    action: str
    requested_grant: bool
    reason: str
    status: str
    decided_by: _UserMini | None
    decided_at: datetime | None
    decision_note: str | None
    created_at: datetime
    updated_at: datetime


def _user_mini(u: User | None) -> _UserMini | None:
    if u is None:
        return None
    return _UserMini(
        id=str(u.id), email=u.email, full_name=u.full_name
    )


async def _resolve_users(
    db: AsyncSession, ids: set[str]
) -> dict[str, User]:
    if not ids:
        return {}
    rows = (
        await db.execute(select(User).where(User.id.in_(ids)))
    ).scalars().all()
    return {str(u.id): u for u in rows}


def _read(r: PermissionChangeRequest, by_user: dict[str, User]) -> _RequestRead:
    return _RequestRead(
        id=str(r.id),
        tenant_id=str(r.tenant_id),
        requested_by=_user_mini(by_user.get(str(r.requested_by_user_id))),
        target_user=_user_mini(by_user.get(str(r.target_user_id))),
        module=r.module,
        action=r.action,
        requested_grant=r.requested_grant,
        reason=r.reason,
        status=r.status,
        decided_by=_user_mini(
            by_user.get(str(r.decided_by_superadmin_id))
            if r.decided_by_superadmin_id
            else None
        ),
        decided_at=r.decided_at,
        decision_note=r.decision_note,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


# ---------- Helpers de permisos ----------
def _is_admin_or_super(cu: CurrentUser) -> bool:
    if cu.user.is_superadmin:
        return True
    return cu.role_type == "admin"


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


# ---------- Endpoint: crear ticket (admin tenant) ----------
@router.post(
    "/permission-requests", response_model=_RequestRead, status_code=201
)
async def create_request(
    body: _CreateBody,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Admin del tenant crea un ticket pidiendo cambio de permiso."""
    if not _is_admin_or_super(cu):
        raise forbidden(
            code="ADMIN_REQUIRED",
            detail="Solo admin del tenant puede solicitar cambios de permiso",
        )
    tenant_id = _tenant(cu)

    # target_user debe existir en este tenant.
    target = (
        await db.execute(
            select(User).where(
                User.id == str(body.target_user_id),
                User.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if target is None:
        raise not_found("Target user")
    if target.is_superadmin:
        raise business_rule(
            "No se pueden cambiar permisos del superadmin",
            code="SUPERADMIN_LOCKED",
        )

    req = PermissionChangeRequest(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        requested_by_user_id=str(cu.id),
        target_user_id=str(target.id),
        module=body.module.strip().lower(),
        action=body.action.strip().lower(),
        requested_grant=body.requested_grant,
        reason=body.reason.strip(),
        status="pending",
    )
    db.add(req)
    await db.flush()

    # Notificar a TODOS los superadmins (in-app + email).
    superadmins = (
        await db.execute(
            select(User).where(User.is_superadmin.is_(True), User.is_active.is_(True))
        )
    ).scalars().all()
    for sa_user in superadmins:
        notif = Notification(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            user_id=str(sa_user.id),
            type="permission_request.created",
            title=f"Nuevo ticket de permiso — {body.module}.{body.action}",
            body=(
                f"{cu.user.full_name or cu.user.email} solicita "
                f"{'otorgar' if body.requested_grant else 'revocar'} "
                f"{body.module}.{body.action} para "
                f"{target.full_name or target.email}."
            ),
            entity_type="permission_request",
            entity_id=str(req.id),
            link="/superadmin/permission-requests",
            meta={"reason": body.reason[:500]},
        )
        db.add(notif)
        # Email best-effort.
        try:
            res = await send_email_via_resend(
                to=sa_user.email,
                subject=f"[PMO·aaS] Nuevo ticket de permiso — {body.module}.{body.action}",
                html=(
                    f"<p>Solicitante: {cu.user.full_name or cu.user.email}</p>"
                    f"<p>Target: {target.full_name or target.email}</p>"
                    f"<p>Permiso: <code>{body.module}.{body.action}</code> "
                    f"({'otorgar' if body.requested_grant else 'revocar'})</p>"
                    f"<p>Motivo:</p><blockquote>{body.reason}</blockquote>"
                    f"<p><a href='https://pmo-aas.com/superadmin/permission-requests'>"
                    f"Revisar en el panel</a></p>"
                ),
            )
            if res and res.get("id"):
                notif.email_sent = True
                notif.email_sent_at = datetime.now(UTC)
                notif.email_provider_id = res["id"]
        except Exception:
            # Email error es non-fatal — el ticket queda creado, la
            # notificación in-app sí está, el superadmin lo ve al
            # entrar al panel.
            pass

    await write_audit(
        db,
        action="permission_request.create",
        module="permissions",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="permission_request",
        entity_id=str(req.id),
        details={
            "target_user_id": str(target.id),
            "module": body.module,
            "action": body.action,
            "requested_grant": body.requested_grant,
        },
    )
    await db.commit()
    await db.refresh(req)

    by_user = await _resolve_users(
        db, {str(req.requested_by_user_id), str(req.target_user_id)}
    )
    return _read(req, by_user)


# ---------- Endpoint: lista (admin propios / superadmin todos) ----------
@router.get(
    "/permission-requests", response_model=list[_RequestRead]
)
async def list_requests(
    status: str | None = Query(default=None),
    mine: bool = Query(default=False),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    if not _is_admin_or_super(cu):
        raise forbidden(code="ADMIN_REQUIRED")

    stmt = select(PermissionChangeRequest)
    if cu.user.is_superadmin and not mine:
        # Superadmin ve todos, opcional filtro por status.
        pass
    else:
        # Admin tenant ve sólo los de su tenant.
        stmt = stmt.where(
            PermissionChangeRequest.tenant_id == str(_tenant(cu))
        )
    if status:
        stmt = stmt.where(PermissionChangeRequest.status == status)
    stmt = stmt.order_by(PermissionChangeRequest.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()

    user_ids: set[str] = set()
    for r in rows:
        user_ids.add(str(r.requested_by_user_id))
        user_ids.add(str(r.target_user_id))
        if r.decided_by_superadmin_id:
            user_ids.add(str(r.decided_by_superadmin_id))
    by_user = await _resolve_users(db, user_ids)
    return [_read(r, by_user) for r in rows]


# ---------- Endpoint: cancelar (admin solicitante) ----------
@router.delete(
    "/permission-requests/{request_id}", status_code=204
)
async def cancel_request(
    request_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    req = (
        await db.execute(
            select(PermissionChangeRequest).where(
                PermissionChangeRequest.id == str(request_id)
            )
        )
    ).scalar_one_or_none()
    if req is None:
        raise not_found("Ticket")
    if not (cu.user.is_superadmin or str(req.requested_by_user_id) == str(cu.id)):
        raise forbidden()
    if req.status != "pending":
        raise conflict(
            "Solo se pueden cancelar tickets pendientes",
            code="NOT_PENDING",
        )
    req.status = "cancelled"
    await write_audit(
        db,
        action="permission_request.cancel",
        module="permissions",
        user_id=cu.id,
        tenant_id=req.tenant_id,
        entity_type="permission_request",
        entity_id=str(req.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


# ---------- Endpoint: aprobar (superadmin) ----------
sa_router = APIRouter(prefix="/superadmin", tags=["superadmin"])


@sa_router.post(
    "/permission-requests/{request_id}/approve",
    response_model=_RequestRead,
)
async def approve_request(
    request_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Superadmin aprueba: crea/actualiza el override en
    tenant_role_permission_overrides (US-073) y notifica al admin
    solicitante."""
    req = (
        await db.execute(
            select(PermissionChangeRequest).where(
                PermissionChangeRequest.id == str(request_id)
            )
        )
    ).scalar_one_or_none()
    if req is None:
        raise not_found("Ticket")
    if req.status != "pending":
        raise conflict("Ticket ya decidido", code="NOT_PENDING")

    # Determinar el role_type del target.
    target = (
        await db.execute(
            select(User).where(User.id == str(req.target_user_id))
        )
    ).scalar_one()
    role_type = target.role_type or "user"

    # Crear / actualizar el override correspondiente.
    override = (
        await db.execute(
            select(TenantRolePermissionOverride).where(
                TenantRolePermissionOverride.tenant_id == str(req.tenant_id),
                TenantRolePermissionOverride.role_type == role_type,
                TenantRolePermissionOverride.module == req.module,
                TenantRolePermissionOverride.action == req.action,
            )
        )
    ).scalar_one_or_none()
    if override is None:
        override = TenantRolePermissionOverride(
            id=str(uuid4()),
            tenant_id=str(req.tenant_id),
            role_type=role_type,
            module=req.module,
            action=req.action,
            granted=req.requested_grant,
            reason=f"Aprobado vía ticket #{req.id}: {req.reason[:500]}",
            updated_by_user_id=str(cu.id),
        )
        db.add(override)
    else:
        override.granted = req.requested_grant
        override.reason = f"Aprobado vía ticket #{req.id}: {req.reason[:500]}"
        override.updated_by_user_id = str(cu.id)

    req.status = "approved"
    req.decided_by_superadmin_id = str(cu.id)
    req.decided_at = datetime.now(UTC)

    # Notificación al solicitante.
    requester = (
        await db.execute(
            select(User).where(User.id == str(req.requested_by_user_id))
        )
    ).scalar_one_or_none()
    if requester:
        notif = Notification(
            id=str(uuid4()),
            tenant_id=str(req.tenant_id),
            user_id=str(requester.id),
            type="permission_request.approved",
            title=f"Ticket aprobado — {req.module}.{req.action}",
            body=f"El superadmin aprobó tu solicitud para {target.email}.",
            entity_type="permission_request",
            entity_id=str(req.id),
            meta={},
        )
        db.add(notif)
        try:
            res = await send_email_via_resend(
                to=requester.email,
                subject=f"[PMO·aaS] Ticket aprobado — {req.module}.{req.action}",
                html=(
                    f"<p>Tu solicitud para "
                    f"{'otorgar' if req.requested_grant else 'revocar'} "
                    f"<code>{req.module}.{req.action}</code> a "
                    f"<strong>{target.email}</strong> fue <strong>aprobada</strong>.</p>"
                ),
            )
            if res and res.get("id"):
                notif.email_sent = True
                notif.email_sent_at = datetime.now(UTC)
                notif.email_provider_id = res["id"]
        except Exception:
            pass

    await write_audit(
        db,
        action="permission_request.approve",
        module="permissions",
        user_id=cu.id,
        tenant_id=req.tenant_id,
        entity_type="permission_request",
        entity_id=str(req.id),
        details={"override_id": str(override.id) if override else None},
    )
    await db.commit()
    await db.refresh(req)

    by_user = await _resolve_users(
        db,
        {
            str(req.requested_by_user_id),
            str(req.target_user_id),
            str(req.decided_by_superadmin_id or ""),
        },
    )
    return _read(req, by_user)


@sa_router.post(
    "/permission-requests/{request_id}/reject",
    response_model=_RequestRead,
)
async def reject_request(
    request_id: UUID,
    body: _RejectBody,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Superadmin rechaza: marca el ticket como rejected con
    decision_note obligatoria + notifica al admin."""
    req = (
        await db.execute(
            select(PermissionChangeRequest).where(
                PermissionChangeRequest.id == str(request_id)
            )
        )
    ).scalar_one_or_none()
    if req is None:
        raise not_found("Ticket")
    if req.status != "pending":
        raise conflict("Ticket ya decidido", code="NOT_PENDING")

    req.status = "rejected"
    req.decided_by_superadmin_id = str(cu.id)
    req.decided_at = datetime.now(UTC)
    req.decision_note = body.decision_note.strip()

    requester = (
        await db.execute(
            select(User).where(User.id == str(req.requested_by_user_id))
        )
    ).scalar_one_or_none()
    target = (
        await db.execute(
            select(User).where(User.id == str(req.target_user_id))
        )
    ).scalar_one_or_none()
    if requester:
        notif = Notification(
            id=str(uuid4()),
            tenant_id=str(req.tenant_id),
            user_id=str(requester.id),
            type="permission_request.rejected",
            title=f"Ticket rechazado — {req.module}.{req.action}",
            body=f"El superadmin rechazó tu solicitud. Motivo: {body.decision_note[:200]}",
            entity_type="permission_request",
            entity_id=str(req.id),
            meta={"decision_note": body.decision_note[:500]},
        )
        db.add(notif)
        try:
            target_label = (target.email if target else "(target eliminado)")
            res = await send_email_via_resend(
                to=requester.email,
                subject=f"[PMO·aaS] Ticket rechazado — {req.module}.{req.action}",
                html=(
                    f"<p>Tu solicitud para "
                    f"<code>{req.module}.{req.action}</code> a "
                    f"<strong>{target_label}</strong> fue <strong>rechazada</strong>.</p>"
                    f"<p>Motivo del superadmin:</p>"
                    f"<blockquote>{body.decision_note}</blockquote>"
                ),
            )
            if res and res.get("id"):
                notif.email_sent = True
                notif.email_sent_at = datetime.now(UTC)
                notif.email_provider_id = res["id"]
        except Exception:
            pass

    await write_audit(
        db,
        action="permission_request.reject",
        module="permissions",
        user_id=cu.id,
        tenant_id=req.tenant_id,
        entity_type="permission_request",
        entity_id=str(req.id),
        details={"decision_note": body.decision_note[:500]},
    )
    await db.commit()
    await db.refresh(req)
    by_user = await _resolve_users(
        db,
        {
            str(req.requested_by_user_id),
            str(req.target_user_id),
            str(req.decided_by_superadmin_id or ""),
        },
    )
    return _read(req, by_user)
