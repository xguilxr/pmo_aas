"""Notifications endpoints (US-027 + US-028, EP011).

Todas las rutas son user-scoped: un user solo ve / actúa sobre sus
propias notificaciones del tenant activo.
"""
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationPreferencesIn,
    NotificationPreferencesOut,
    NotificationRead,
    UnreadCount,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _scope(cu: CurrentUser):
    if cu.user.tenant_id is None:
        raise forbidden()
    return Notification.tenant_id == str(cu.user.tenant_id), Notification.user_id == cu.id


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    is_read: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(*_scope(cu))
    if is_read is not None:
        stmt = stmt.where(Notification.is_read.is_(is_read))
    stmt = stmt.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [NotificationRead.model_validate(r) for r in rows]


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(func.count(Notification.id))
        .where(*_scope(cu))
        .where(Notification.is_read.is_(False))
    )
    count = (await db.execute(stmt)).scalar_one()
    return UnreadCount(count=count)


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: UUID,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    n = (
        await db.execute(
            select(Notification).where(Notification.id == str(notification_id), *_scope(cu))
        )
    ).scalar_one_or_none()
    if n is None:
        raise not_found("Notificación")
    if not n.is_read:
        n.is_read = True
        n.read_at = datetime.now(UTC)
        await db.commit()
    return NotificationRead.model_validate(n)


@router.post("/read-all")
async def mark_all_read(
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_cond, user_cond = _scope(cu)
    now = datetime.now(UTC)
    await db.execute(
        update(Notification)
        .where(tenant_cond, user_cond, Notification.is_read.is_(False))
        .values(is_read=True, read_at=now)
    )
    await db.commit()
    return {"ok": True}


@router.get("/preferences", response_model=NotificationPreferencesOut)
async def get_preferences(
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == cu.id))).scalar_one()
    prefs = (user.preferences or {}).get("notifications", {})
    return NotificationPreferencesOut(
        email_enabled=bool(prefs.get("email_enabled", True)),
        by_type=dict(prefs.get("by_type", {})),
    )


@router.patch("/preferences", response_model=NotificationPreferencesOut)
async def update_preferences(
    body: NotificationPreferencesIn,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == cu.id))).scalar_one()
    prefs = dict(user.preferences or {})
    notif_prefs = dict(prefs.get("notifications", {}))
    if body.email_enabled is not None:
        notif_prefs["email_enabled"] = bool(body.email_enabled)
    if body.by_type is not None:
        merged = dict(notif_prefs.get("by_type", {}))
        merged.update(body.by_type)
        notif_prefs["by_type"] = merged
    prefs["notifications"] = notif_prefs
    user.preferences = prefs
    await db.commit()
    return NotificationPreferencesOut(
        email_enabled=bool(notif_prefs.get("email_enabled", True)),
        by_type=dict(notif_prefs.get("by_type", {})),
    )
