from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_superadmin
from app.core.errors import not_found
from app.db.session import get_db
from app.models.ai import AIJob
from app.models.audit import AuditLog
from app.models.organization import Organization
from app.models.project import Project
from app.models.tenant import Tenant
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(prefix="/superadmin", tags=["superadmin_panel"])


@router.get("/dashboard")
async def platform_dashboard(
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    total_tenants = (await db.execute(select(func.count(Tenant.id)))).scalar_one()
    active_tenants = (
        await db.execute(select(func.count(Tenant.id)).where(Tenant.is_active.is_(True)))
    ).scalar_one()
    inactive_tenants = total_tenants - active_tenants
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    total_projects = (
        await db.execute(
            select(func.count(Project.id)).where(Project.deleted_at.is_(None))
        )
    ).scalar_one()

    month_ago = datetime.now(UTC) - timedelta(days=30)
    ai_tokens_rows = (
        await db.execute(
            select(
                func.coalesce(func.sum(AIJob.tokens_in), 0),
                func.coalesce(func.sum(AIJob.tokens_out), 0),
            ).where(AIJob.created_at >= month_ago)
        )
    ).one()
    ai_tokens_in, ai_tokens_out = int(ai_tokens_rows[0] or 0), int(ai_tokens_rows[1] or 0)

    recent = (
        await db.execute(
            select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(20)
        )
    ).scalars().all()

    top_tenant_rows = (
        await db.execute(
            select(Tenant.id, Tenant.slug, Tenant.name, func.count(Project.id).label("cnt"))
            .select_from(Tenant)
            .join(Project, Project.tenant_id == Tenant.id, isouter=True)
            .where(and_(Tenant.is_active.is_(True)))
            .group_by(Tenant.id, Tenant.slug, Tenant.name)
            .order_by(func.count(Project.id).desc())
            .limit(5)
        )
    ).all()

    return {
        "kpis": {
            "tenants_total": total_tenants,
            "tenants_active": active_tenants,
            "tenants_inactive": inactive_tenants,
            "users_total": total_users,
            "projects_total": total_projects,
            "ai_tokens_30d": {"in": ai_tokens_in, "out": ai_tokens_out},
        },
        "top_tenants": [
            {"id": str(r.id), "slug": r.slug, "name": r.name, "project_count": int(r.cnt)}
            for r in top_tenant_rows
        ],
        "activity_recent": [
            {
                "id": r.id, "action": r.action, "module": r.module,
                "tenant_id": r.tenant_id, "user_id": r.user_id,
                "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
            }
            for r in recent
        ],
    }


@router.get("/tenants/search")
async def search_tenants(
    q: str | None = Query(default=None),
    ai_mode: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tenant)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Tenant.slug).like(like),
                func.lower(Tenant.name).like(like),
            )
        )
    if is_active is not None:
        stmt = stmt.where(Tenant.is_active.is_(is_active))
    if created_from:
        stmt = stmt.where(Tenant.created_at >= created_from)
    if created_to:
        stmt = stmt.where(Tenant.created_at <= created_to)
    if cursor:
        stmt = stmt.where(Tenant.id > cursor)
    stmt = stmt.order_by(Tenant.id).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    # Filtrar ai_mode post-query (está en JSON settings)
    if ai_mode:
        rows = [t for t in rows if (t.settings or {}).get("ai_mode") == ai_mode]

    next_cursor = str(rows[-1].id) if len(rows) == limit else None
    return {
        "items": [
            {
                "id": str(t.id), "slug": t.slug, "name": t.name,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat(),
                "ai_mode": (t.settings or {}).get("ai_mode"),
            }
            for t in rows
        ],
        "next_cursor": next_cursor,
    }


@router.get("/tenants/{tenant_id}/full-detail")
async def tenant_full_detail(
    tenant_id: UUID,
    include: str = Query(default="all"),
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    keys = set(include.split(",")) if include != "all" else {
        "overview", "users", "projects", "logs", "ai", "orgs",
    }

    out: dict = {
        "tenant": {
            "id": str(t.id), "slug": t.slug, "name": t.name,
            "is_active": t.is_active, "settings": t.settings or {},
            "created_at": t.created_at.isoformat(),
        }
    }

    if "users" in keys:
        users = (
            await db.execute(select(User).where(User.tenant_id == t.id))
        ).scalars().all()
        out["users"] = [
            {"id": str(u.id), "username": u.username, "email": u.email,
             "is_active": u.is_active, "last_login": u.last_login.isoformat() if u.last_login else None}
            for u in users
        ]
    if "projects" in keys:
        projs = (
            await db.execute(
                select(Project).where(Project.tenant_id == t.id, Project.deleted_at.is_(None))
            )
        ).scalars().all()
        out["projects"] = [
            {"id": str(p.id), "folio": p.folio, "name": p.name, "phase": p.phase,
             "health_status": p.health_status, "pm_id": str(p.pm_id) if p.pm_id else None}
            for p in projs
        ]
    if "orgs" in keys:
        orgs = (
            await db.execute(
                select(Organization).where(Organization.tenant_id == t.id)
            )
        ).scalars().all()
        out["organizations"] = [
            {"id": str(o.id), "name": o.name, "is_active": o.is_active}
            for o in orgs
        ]
    if "logs" in keys:
        logs = (
            await db.execute(
                select(AuditLog).where(AuditLog.tenant_id == str(t.id))
                .order_by(AuditLog.occurred_at.desc()).limit(500)
            )
        ).scalars().all()
        out["logs"] = [
            {"id": l.id, "action": l.action, "module": l.module,
             "user_id": l.user_id, "entity_type": l.entity_type, "entity_id": l.entity_id,
             "occurred_at": l.occurred_at.isoformat() if l.occurred_at else None}
            for l in logs
        ]
    if "ai" in keys:
        jobs = (
            await db.execute(
                select(AIJob).where(AIJob.tenant_id == str(t.id))
                .order_by(AIJob.created_at.desc()).limit(100)
            )
        ).scalars().all()
        out["ai_jobs"] = [
            {"id": str(j.id), "kind": j.kind, "status": j.status,
             "model_used": j.model_used, "tokens_in": j.tokens_in,
             "tokens_out": j.tokens_out, "error": j.error,
             "created_at": j.created_at.isoformat() if j.created_at else None}
            for j in jobs
        ]
    return out


@router.get("/logs/platform")
async def platform_logs(
    q: str | None = Query(default=None),
    action: str | None = Query(default=None),
    tenant_id: UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=1000),
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if tenant_id:
        stmt = stmt.where(AuditLog.tenant_id == str(tenant_id))
    if date_from:
        stmt = stmt.where(AuditLog.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.occurred_at <= date_to)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(AuditLog.action).like(like))
    rows = (
        await db.execute(
            stmt.order_by(AuditLog.occurred_at.desc()).offset((page - 1) * limit).limit(limit)
        )
    ).scalars().all()
    return [
        {"id": r.id, "action": r.action, "module": r.module,
         "tenant_id": r.tenant_id, "user_id": r.user_id,
         "entity_type": r.entity_type, "entity_id": r.entity_id,
         "details": r.details,
         "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None}
        for r in rows
    ]


@router.get("/health")
async def platform_health(
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    # Check db
    from sqlalchemy import text

    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    # Redis skip in tests (sin conexión real)
    return {"db": db_ok, "api": True, "time": datetime.now(UTC).isoformat()}


@router.post("/tenants/{tenant_id}/freeze")
async def freeze_tenant(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    merged = dict(t.settings or {})
    merged["frozen"] = True
    t.settings = merged
    await write_audit(
        db, action="tenant.frozen", module="superadmin",
        user_id=cu.id, entity_type="tenant", entity_id=str(t.id),
    )
    await db.commit()
    return {"ok": True, "frozen": True}


@router.post("/tenants/{tenant_id}/unfreeze")
async def unfreeze_tenant(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    merged = dict(t.settings or {})
    merged["frozen"] = False
    t.settings = merged
    await write_audit(
        db, action="tenant.unfrozen", module="superadmin",
        user_id=cu.id, entity_type="tenant", entity_id=str(t.id),
    )
    await db.commit()
    return {"ok": True, "frozen": False}
