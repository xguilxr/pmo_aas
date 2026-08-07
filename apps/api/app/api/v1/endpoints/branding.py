"""Tenant branding endpoints (US-031).

Upload + serve del logo del tenant para el chrome (topbar/sidebar).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_capability
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.dominio.moneda import POR_DEFECTO as MONEDA_POR_DEFECTO
from app.dominio.moneda import resolver as _resolver_moneda
from app.models.tenant import Tenant
from app.services.audit import write_audit
from app.services.branding_storage import (
    ALLOWED_LOGO_MIMES,
    delete_logo,
    find_logo_file,
    logo_to_data_url,
)
from app.services.tenant_settings import DEFAULT_ORG_LABEL, get_org_label


def moneda_preferida_de(t: Tenant) -> str:
    """La preferida del inquilino, ya resuelta a un código válido."""
    return _resolver_moneda(None, (t.settings or {}).get("currency"))


router = APIRouter(tags=["branding"])


# ---- helpers ----
def _tenant_id(cu: CurrentUser) -> UUID:
    # BUG-056: superadmin con joinAsAdmin opera con effective_tenant_id.
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


def _ext_to_mime(path_suffix: str) -> str:
    """Map extension back to MIME for serving."""
    inv = {v: k for k, v in ALLOWED_LOGO_MIMES.items() if k != "image/jpg"}
    return inv.get(path_suffix.lstrip("."), "application/octet-stream")


# ---- Upload / delete logo (admin-only) ----
@router.post("/admin/tenant/logo")
async def upload_tenant_logo(
    file: UploadFile = File(...),
    cu: CurrentUser = Depends(require_capability("tenant.manage")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    # BUG-068: guardamos el logo como data-URL en DB (no en disco efímero) para
    # que renderice directo desde `<img>` sin pasar por un endpoint autenticado.
    t.logo_url = await logo_to_data_url(file)
    # Limpia cualquier archivo legacy en disco de subidas anteriores.
    delete_logo(str(tenant_id))
    await write_audit(
        db,
        action="tenant.logo.upload",
        module="admin",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="tenant",
        entity_id=str(t.id),
        details={"stored": "data_url"},
    )
    await db.commit()
    return {"logo_url": t.logo_url}


@router.delete("/admin/tenant/logo", status_code=200)
async def remove_tenant_logo(
    cu: CurrentUser = Depends(require_capability("tenant.manage")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    removed_file = delete_logo(str(tenant_id))
    # Limpiamos el logo si es un data-URL subido o apuntaba al endpoint
    # interno. Una URL externa legítima (p.ej. CDN) no se toca.
    cleared = False
    if t.logo_url and (
        t.logo_url.startswith("data:") or t.logo_url.startswith("/api/")
    ):
        t.logo_url = None
        cleared = True
    deleted = removed_file or cleared
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
    if not cu.is_superadmin and str(cu.effective_tenant_id) != str(tenant_id):
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
    if cu.effective_tenant_id is None:
        return {
            "tenant_id": None,
            "tenant_name": None,
            "tenant_slug": None,
            "logo_url": None,
            "primary_color": None,
            # ENH-190: default label when there is no active tenant.
            "org_label": DEFAULT_ORG_LABEL,
            "preferred_currency": MONEDA_POR_DEFECTO,
        }
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(cu.effective_tenant_id)))
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
        # ENH-190: effective per-tenant UI label ("organizations" | "portfolios").
        # UI-only — any user in the tenant can read it via this shared endpoint.
        "org_label": get_org_label(t),
        # BUG-092 — la moneda PREFERIDA del inquilino: el valor inicial de los
        # proyectos que no eligen una propia. Viaja por aquí y no por un punto
        # de acceso nuevo porque es el mismo caso que `org_label`: un dato de
        # presentación que toda pantalla necesita y ninguna debería ir a pedir.
        "preferred_currency": moneda_preferida_de(t),
    }
