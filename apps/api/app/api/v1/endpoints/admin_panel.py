import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import business_rule, forbidden, not_found
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.organization import Organization
from app.models.project import Project
from app.models.role import Role, UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.user import RoleRead
from app.services.audit import write_audit

router = APIRouter(prefix="/admin", tags=["admin_panel"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


# ---- Bulk user actions ----
class BulkAssignRoleBody(BaseModel):
    user_ids: list[UUID] = Field(min_length=1, max_length=100)
    role_id: UUID


@router.post("/users/bulk/assign-role", status_code=200)
async def bulk_assign_role(
    body: BulkAssignRoleBody,
    cu: CurrentUser = Depends(require_permission("users", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    role = (
        await db.execute(
            select(Role).where(Role.id == str(body.role_id), Role.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if role is None:
        raise not_found("Rol")
    affected = 0
    for uid in body.user_ids:
        user = (
            await db.execute(
                select(User).where(User.id == str(uid), User.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()
        if user is None:
            continue
        exists = (
            await db.execute(
                select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(UserRole(user_id=user.id, role_id=role.id))
            affected += 1
            await write_audit(
                db, action="user.bulk_role_assigned", module="admin.users",
                user_id=cu.id, tenant_id=tenant_id, entity_type="user",
                entity_id=str(user.id), details={"role_id": str(role.id)},
            )
    await db.commit()
    return {"affected": affected, "total": len(body.user_ids)}


class BulkDeactivateBody(BaseModel):
    user_ids: list[UUID] = Field(min_length=1, max_length=100)


@router.post("/users/bulk/deactivate", status_code=200)
async def bulk_deactivate(
    body: BulkDeactivateBody,
    cu: CurrentUser = Depends(require_permission("users", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    affected = 0
    for uid in body.user_ids:
        if str(uid) == str(cu.id):
            raise business_rule("No puedes desactivar tu propia cuenta")
        user = (
            await db.execute(
                select(User).where(User.id == str(uid), User.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()
        if user and user.is_active:
            user.is_active = False
            affected += 1
    await write_audit(
        db, action="users.bulk_deactivate", module="admin.users",
        user_id=cu.id, tenant_id=tenant_id, details={"affected": affected},
    )
    await db.commit()
    return {"affected": affected}


# ---- Role duplicate & impact ----
@router.post("/roles/{role_id}/duplicate", response_model=RoleRead, status_code=201)
async def duplicate_role(
    role_id: UUID,
    cu: CurrentUser = Depends(require_permission("roles", "create")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    r = (await db.execute(select(Role).where(Role.id == str(role_id), Role.tenant_id == tenant_id))).scalar_one_or_none()
    if r is None:
        raise not_found("Rol")
    new_role = Role(
        tenant_id=tenant_id, name=f"{r.name} (copy)",
        description=r.description, permissions=dict(r.permissions or {}),
        is_system=False,
    )
    db.add(new_role)
    await db.flush()
    await write_audit(
        db, action="role.duplicate", module="admin.roles",
        user_id=cu.id, tenant_id=tenant_id, entity_type="role",
        entity_id=str(new_role.id), details={"source": str(r.id)},
    )
    await db.commit()
    return RoleRead.model_validate(new_role)


@router.get("/roles/{role_id}/impact")
async def role_impact(
    role_id: UUID,
    cu: CurrentUser = Depends(require_permission("roles", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    r = (await db.execute(select(Role).where(Role.id == str(role_id), Role.tenant_id == tenant_id))).scalar_one_or_none()
    if r is None:
        raise not_found("Rol")
    rows = (
        await db.execute(
            select(User.id, User.username, User.email, User.full_name)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == r.id)
        )
    ).all()
    return {
        "affected_count": len(rows),
        "users": [
            {"id": str(u.id), "username": u.username, "email": u.email, "full_name": u.full_name}
            for u in rows
        ],
    }


# ---- Organizations with metrics ----
@router.get("/organizations/metrics")
async def org_metrics(
    cu: CurrentUser = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    orgs = (
        await db.execute(select(Organization).where(Organization.tenant_id == tenant_id))
    ).scalars().all()
    out = []
    for o in orgs:
        pcount = (
            await db.execute(
                select(func.count(Project.id)).where(
                    Project.organization_id == o.id, Project.deleted_at.is_(None),
                    Project.phase.in_(["planning", "execution", "support"]),
                )
            )
        ).scalar_one()
        bsum = (
            await db.execute(
                select(func.coalesce(func.sum(Project.budget), 0)).where(
                    Project.organization_id == o.id, Project.deleted_at.is_(None)
                )
            )
        ).scalar_one()
        out.append(
            {
                "id": str(o.id), "name": o.name, "is_active": o.is_active,
                "project_count_active": pcount, "budget_total": float(bsum or 0),
            }
        )
    return out


# ---- Admin view of all projects (bypass member filter) ----
@router.get("/projects")
async def admin_list_projects(
    include_inactive_orgs: bool = Query(default=True),
    cu: CurrentUser = Depends(require_permission("admin", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Project).where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
    rows = (await db.execute(stmt)).scalars().all()
    if not include_inactive_orgs:
        active_org_ids = {
            str(o.id) for o in (
                await db.execute(
                    select(Organization).where(
                        Organization.tenant_id == tenant_id, Organization.is_active.is_(True)
                    )
                )
            ).scalars().all()
        }
        rows = [p for p in rows if str(p.organization_id) in active_org_ids]
    return [
        {"id": str(p.id), "folio": p.folio, "name": p.name, "phase": p.phase,
         "health_status": p.health_status, "budget": float(p.budget or 0),
         "organization_id": str(p.organization_id)}
        for p in rows
    ]


class ForceCloseBody(BaseModel):
    comment: str = Field(min_length=5, max_length=1000)


@router.post("/projects/{project_id}/force-close")
async def admin_force_close(
    project_id: UUID,
    body: ForceCloseBody,
    cu: CurrentUser = Depends(require_permission("admin", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = (
        await db.execute(
            select(Project).where(Project.id == str(project_id), Project.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")
    p.phase = "closed"
    await write_audit(
        db, action="project.force_close", module="admin.projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(p.id),
        details={"comment": body.comment},
    )
    await db.commit()
    return {"ok": True, "phase": p.phase}


# ---- Tenant info + stats (US-023) ----
class TenantInfoUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    logo_url: str | None = Field(default=None, max_length=500)


@router.get("/tenant")
async def get_tenant_info(
    cu: CurrentUser = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Info + stats del tenant actual (US-023).

    Devuelve identidad del tenant, settings (reexportados), plan y
    estadísticas agregadas (usuarios activos, proyectos, storage).
    """
    tenant_id = _tenant(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    active_users = (
        await db.execute(
            select(func.count(User.id)).where(
                User.tenant_id == str(tenant_id), User.is_active.is_(True)
            )
        )
    ).scalar_one() or 0
    total_users = (
        await db.execute(
            select(func.count(User.id)).where(User.tenant_id == str(tenant_id))
        )
    ).scalar_one() or 0
    total_projects = (
        await db.execute(
            select(func.count(Project.id)).where(
                Project.tenant_id == str(tenant_id), Project.deleted_at.is_(None)
            )
        )
    ).scalar_one() or 0
    total_orgs = (
        await db.execute(
            select(func.count(Organization.id)).where(
                Organization.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one() or 0

    # Storage: suma de `documents.size_bytes` actuales (deleted_at IS NULL).
    # Import diferido para no forzar el módulo si no existe.
    try:
        from app.models.modules import Document  # type: ignore

        storage_bytes = (
            await db.execute(
                select(func.coalesce(func.sum(Document.size_bytes), 0)).where(
                    Document.tenant_id == str(tenant_id),
                    Document.deleted_at.is_(None),
                    Document.is_current.is_(True),
                )
            )
        ).scalar_one() or 0
    except Exception:
        storage_bytes = 0

    # Plan: por ahora se guarda en settings.plan (string libre); si no
    # está, devolvemos "mvp" como default.
    plan = (t.settings or {}).get("plan") or "mvp"

    return {
        "id": str(t.id),
        "slug": t.slug,
        "name": t.name,
        "logo_url": t.logo_url,
        "is_active": t.is_active,
        "plan": plan,
        "settings": t.settings or {},
        "stats": {
            "active_users": int(active_users),
            "total_users": int(total_users),
            "total_organizations": int(total_orgs),
            "total_projects": int(total_projects),
            "storage_bytes": int(storage_bytes),
        },
    }


@router.patch("/tenant")
async def update_tenant_info(
    body: TenantInfoUpdate,
    cu: CurrentUser = Depends(require_permission("users", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza nombre y/o logo del tenant (US-023).

    Slug, plan y eliminación son exclusivos de super admin y se hacen
    desde el panel superadmin.
    """
    tenant_id = _tenant(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return {
            "id": str(t.id),
            "slug": t.slug,
            "name": t.name,
            "logo_url": t.logo_url,
        }
    for field, value in updates.items():
        setattr(t, field, value)
    await write_audit(
        db,
        action="tenant.info.update",
        module="admin",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="tenant",
        entity_id=str(t.id),
        details={"fields": list(updates.keys())},
    )
    await db.commit()
    return {
        "id": str(t.id),
        "slug": t.slug,
        "name": t.name,
        "logo_url": t.logo_url,
    }


# ---- Tenant settings ----
class TenantSettingsUpdate(BaseModel):
    locale: str | None = None
    currency: str | None = None
    date_format: str | None = None
    timezone: str | None = None
    primary_color: str | None = None
    ai_mode: str | None = None
    logo_url: str | None = None


@router.get("/settings")
async def get_settings(
    cu: CurrentUser = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    return {"settings": t.settings or {}}


@router.patch("/settings")
async def patch_settings(
    body: TenantSettingsUpdate,
    cu: CurrentUser = Depends(require_permission("users", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    updates = body.model_dump(exclude_none=True)
    merged = dict(t.settings or {})
    merged.update(updates)
    t.settings = merged
    await write_audit(
        db, action="tenant.settings.update", module="admin",
        user_id=cu.id, tenant_id=tenant_id, details={"fields": list(updates.keys())},
    )
    await db.commit()
    return {"settings": t.settings}


# ---- Audit logs view ----
@router.get("/audit-logs")
async def list_audit_logs(
    action: str | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    cu: CurrentUser = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(AuditLog).where(AuditLog.tenant_id == str(tenant_id))
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == str(user_id))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if date_from:
        stmt = stmt.where(AuditLog.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.occurred_at <= date_to)
    rows = (
        await db.execute(stmt.order_by(AuditLog.occurred_at.desc()).offset((page - 1) * limit).limit(limit))
    ).scalars().all()
    return [
        {
            "id": r.id, "action": r.action, "module": r.module,
            "user_id": r.user_id, "entity_type": r.entity_type, "entity_id": r.entity_id,
            "details": r.details, "ip_address": r.ip_address,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
        }
        for r in rows
    ]


@router.get("/audit-logs/export.csv")
async def export_audit_logs(
    cu: CurrentUser = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    rows = (
        await db.execute(
            select(AuditLog).where(AuditLog.tenant_id == str(tenant_id)).order_by(AuditLog.occurred_at.desc())
        )
    ).scalars().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["occurred_at", "action", "module", "user_id", "entity_type", "entity_id", "ip"])
    for r in rows:
        w.writerow([
            r.occurred_at.isoformat() if r.occurred_at else "",
            r.action, r.module or "", r.user_id or "",
            r.entity_type or "", r.entity_id or "", r.ip_address or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
