"""Tenant branding endpoints (US-031).

Upload + serve del logo del tenant para el chrome (topbar/sidebar).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_permission
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.audit import write_audit
from app.services.branding_storage import (
    ALLOWED_LOGO_MIMES,
    delete_logo,
    find_logo_file,
    logo_public_url,
    save_logo,
)

router = APIRouter(tags=["branding"])


# ---- helpers ----
def _tenant_id(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


def _ext_to_mime(path_suffix: str) -> str:
    """Map extension back to MIME for serving."""
    inv = {v: k for k, v in ALLOWED_LOGO_MIMES.items() if k != "image/jpg"}
    return inv.get(path_suffix.lstrip("."), "application/octet-stream")


# ---- Upload / delete logo (admin-only) ----
@router.post("/admin/tenant/logo")
async def upload_tenant_logo(
    file: UploadFile = File(...),
    cu: CurrentUser = Depends(require_permission("admin.users", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    _, ext = await save_logo(str(tenant_id), file)
    t.logo_url = logo_public_url(str(tenant_id))
    await write_audit(
        db,
        action="tenant.logo.upload",
        module="admin",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="tenant",
        entity_id=str(t.id),
        details={"ext": ext},
    )
    await db.commit()
    return {"logo_url": t.logo_url}


@router.delete("/admin/tenant/logo", status_code=200)
async def remove_tenant_logo(
    cu: CurrentUser = Depends(require_permission("admin.users", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    deleted = delete_logo(str(tenant_id))
    # Si `logo_url` apuntaba al endpoint interno, lo limpiamos. Si era
    # una URL externa legítima (p.ej. CDN), no la tocamos.
    internal_prefix = logo_public_url(str(tenant_id))
    if t.logo_url and t.logo_url.startswith(internal_prefix):
        t.logo_url = None
    await write_audit(
        db,
        action="tenant.logo.remove",
        module="admin",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="tenant",
        entity_id=str(t.id),
        details={"file_removed": deleted},
    )
    await db.commit()
    return {"deleted": deleted, "logo_url": t.logo_url}


# ---- Serve logo file (authenticated within tenant or super admin) ----
@router.get("/branding/tenants/{tenant_id}/logo")
async def serve_tenant_logo(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_current_user),
):
    if not cu.is_superadmin and str(cu.user.tenant_id) != str(tenant_id):
        raise not_found("Logo")
    path = find_logo_file(str(tenant_id))
    if path is None:
        raise not_found("Logo")
    media_type = _ext_to_mime(path.suffix)
    return FileResponse(
        str(path),
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=60"},
    )


# ---- Branding consumido por el topbar ----
@router.get("/me/tenant-branding")
async def my_tenant_branding(
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Info de branding del tenant del usuario activo.

    Endpoint ligero, auth-only (sin permiso específico), para que el
    topbar pueda consumirlo desde cualquier página del app.
    """
    if cu.user.tenant_id is None:
        return {
            "tenant_id": None,
            "tenant_name": None,
            "tenant_slug": None,
            "logo_url": None,
            "primary_color": None,
        }
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(cu.user.tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    primary_color = (t.settings or {}).get("primary_color")
    return {
        "tenant_id": str(t.id),
        "tenant_name": t.name,
        "tenant_slug": t.slug,
        "logo_url": t.logo_url,
        "primary_color": primary_color,
    }
