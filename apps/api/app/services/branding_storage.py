"""Tenant branding file storage (logo upload)."""
from __future__ import annotations

import base64
from pathlib import Path

from fastapi import UploadFile, status

from app.core.config import settings
from app.core.errors import AppError, validation_error
from app.core.unidades import mebibytes

MAX_LOGO_BYTES = mebibytes(2)  # criterio US-031

# MIME -> extensión canónica
ALLOWED_LOGO_MIMES: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/svg+xml": "svg",
    "image/webp": "webp",
}

# MIME canónico para el prefijo del data-URL (image/jpg -> image/jpeg).
_CANONICAL_MIME = {"image/jpg": "image/jpeg"}


async def logo_to_data_url(upload: UploadFile) -> str:
    """Valida y devuelve el logo subido como data-URL base64.

    BUG-068: en lugar de escribir a disco (efímero en Railway) y servir el
    archivo por un endpoint autenticado que un `<img>` no puede consumir
    (401), el logo se guarda como data-URL en la columna del tenant y se
    renderiza directo desde `<img src="data:...">`.
    """
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_LOGO_MIMES:
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
    mime = _CANONICAL_MIME.get(content_type, content_type)
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"



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
