"""Project document file storage (file upload for documents)."""
from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile, status

from app.core.config import settings
from app.core.errors import AppError, validation_error

MAX_DOC_BYTES = 50 * 1024 * 1024  # 50 MB

# MIME -> extensión canónica (whitelist: PDF, XLSX, DOCX, PPTX, PNG, JPG, CSV)
ALLOWED_DOC_MIMES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "text/csv": "csv",
}


def _project_docs_dir(tenant_id: str, project_id: str) -> Path:
    """Return the directory where project documents are stored."""
    base = Path(settings.STORAGE_PATH) / "documents" / tenant_id / project_id
    base.mkdir(parents=True, exist_ok=True)
    return base


async def save_document(
    tenant_id: str, project_id: str, upload: UploadFile, document_id: str
) -> tuple[str, str]:
    """
    Persist the uploaded document to disk.
    Returns (file_url, mime_type).
    """
    content_type = (upload.content_type or "").lower()
    ext = ALLOWED_DOC_MIMES.get(content_type)
    if ext is None:
        raise validation_error(
            "Formato no permitido. Usa PDF, XLSX, DOCX, PPTX, PNG, JPG o CSV.",
            fields={"mime": content_type},
        )

    data = await upload.read()
    if len(data) == 0:
        raise validation_error("Archivo vacío")
    if len(data) > MAX_DOC_BYTES:
        raise AppError(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "PAYLOAD_TOO_LARGE",
            f"El documento excede {MAX_DOC_BYTES // (1024*1024)} MB",
            {"max_bytes": MAX_DOC_BYTES, "size": len(data)},
        )

    base = _project_docs_dir(tenant_id, project_id)
    target = base / f"{document_id}.{ext}"
    target.write_bytes(data)

    file_url = f"/api/v1/documents/{document_id}/download"
    return file_url, content_type


def get_document_path(tenant_id: str, project_id: str, document_id: str) -> Path | None:
    """Return the file path for a document if it exists, checking all allowed extensions."""
    base = _project_docs_dir(tenant_id, project_id)
    for ext in set(ALLOWED_DOC_MIMES.values()):
        candidate = base / f"{document_id}.{ext}"
        if candidate.is_file():
            return candidate
    return None


def delete_document_file(tenant_id: str, project_id: str, document_id: str) -> bool:
    """Remove stored document files. Returns True if something was deleted."""
    removed = False
    base = _project_docs_dir(tenant_id, project_id)
    for ext in set(ALLOWED_DOC_MIMES.values()):
        f = base / f"{document_id}.{ext}"
        if f.exists():
            f.unlink()
            removed = True
    return removed
