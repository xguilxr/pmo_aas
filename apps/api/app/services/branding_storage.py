"""Tenant branding file storage (logo upload)."""
from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile, status

from app.core.config import settings
from app.core.errors import AppError, validation_error

MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB — criterio US-NEW-031

# MIME -> extensión canónica
ALLOWED_LOGO_MIMES: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/svg+xml": "svg",
    "image/webp": "webp",
}


def _tenant_dir(tenant_id: str) -> Path:
    base = Path(settings.STORAGE_PATH) / "tenants" / tenant_id
    base.mkdir(parents=True, exist_ok=True)
    return base


def find_logo_file(tenant_id: str) -> Path | None:
    """Return the current logo file on disk, if any (any allowed extension)."""
    base = _tenant_dir(tenant_id)
    for ext in set(ALLOWED_LOGO_MIMES.values()):
        candidate = base / f"logo.{ext}"
        if candidate.is_file():
            return candidate
    return None


async def save_logo(tenant_id: str, upload: UploadFile) -> tuple[Path, str]:
    """Persist the uploaded logo to disk; returns (path, extension)."""
    content_type = (upload.content_type or "").lower()
    ext = ALLOWED_LOGO_MIMES.get(content_type)
    if ext is None:
        raise validation_error(
            "Formato no permitido. Usa PNG, JPG, SVG o WEBP.",
            fields={"mime": content_type},
        )

    data = await upload.read()
    if len(data) == 0:
        raise validation_error("Archivo vacío")
    if len(data) > MAX_LOGO_BYTES:
        raise AppError(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "PAYLOAD_TOO_LARGE",
            "El logo excede 2 MB",
            {"max_bytes": MAX_LOGO_BYTES, "size": len(data)},
        )

    # Limpia variantes previas (otras extensiones)
    base = _tenant_dir(tenant_id)
    for existing_ext in set(ALLOWED_LOGO_MIMES.values()):
        existing = base / f"logo.{existing_ext}"
        if existing != base / f"logo.{ext}" and existing.exists():
            existing.unlink(missing_ok=True)

    target = base / f"logo.{ext}"
    target.write_bytes(data)
    return target, ext


def delete_logo(tenant_id: str) -> bool:
    """Remove stored logo files for the tenant. Returns True if something was deleted."""
    removed = False
    base = _tenant_dir(tenant_id)
    for ext in set(ALLOWED_LOGO_MIMES.values()):
        f = base / f"logo.{ext}"
        if f.exists():
            f.unlink()
            removed = True
    return removed


def logo_public_url(tenant_id: str) -> str:
    """Relative URL used to serve the logo via API (stored in tenant.logo_url)."""
    return f"/api/v1/branding/tenants/{tenant_id}/logo"
