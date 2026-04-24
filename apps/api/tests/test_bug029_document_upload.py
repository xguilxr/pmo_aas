"""BUG-029: verificar que el upload de documentos acepta Excel legacy (.xls)
y que el fallback por extensión funciona cuando el browser no manda MIME.

Rework de BUG-024 / fix owner report:
> Botón de Choose File solo se ve como texto. Intenté subir un excel
> ligero y me dio: No se pudo subir el documento.

Root cause identificado:
1. Frontend fetch nativo sin Authorization header → 401 Unauthorized
   disfrazado como error genérico (fix en frontend).
2. Whitelist MIME del backend no aceptaba .xls legacy
   (`application/vnd.ms-excel`) — fix aquí.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.document_storage import (
    _EXTENSION_FALLBACK,
    ALLOWED_DOC_MIMES,
)


def test_bug029_xls_legacy_is_whitelisted():
    """Excel 97-2003 (.xls) con MIME `application/vnd.ms-excel` es
    aceptado. Antes del fix solo XLSX OOXML pasaba."""
    assert ALLOWED_DOC_MIMES.get("application/vnd.ms-excel") == "xls"


def test_bug029_doc_legacy_is_whitelisted():
    """Word 97-2003 (.doc) también aceptado."""
    assert ALLOWED_DOC_MIMES.get("application/msword") == "doc"


def test_bug029_ppt_legacy_is_whitelisted():
    """PowerPoint 97-2003 (.ppt) también aceptado."""
    assert ALLOWED_DOC_MIMES.get("application/vnd.ms-powerpoint") == "ppt"


def test_bug029_extension_fallback_covers_common_formats():
    """Si el browser manda `application/octet-stream` (común en Windows
    drag-drop o Safari), el fallback resuelve por extensión del filename."""
    for ext in ("pdf", "xlsx", "xls", "docx", "doc", "pptx", "ppt", "csv"):
        resolved_mime = _EXTENSION_FALLBACK[ext]
        assert resolved_mime in ALLOWED_DOC_MIMES, (
            f"Extension `{ext}` maps to `{resolved_mime}` but that MIME "
            f"is not in ALLOWED_DOC_MIMES — whitelist/fallback mismatch."
        )


@pytest.mark.asyncio
async def test_bug029_save_document_accepts_xls_with_fallback(tmp_path):
    """Integration test: una UploadFile con content_type vacío +
    filename=`test.xls` es aceptada vía fallback por extensión."""
    from app.services import document_storage as storage_module

    # Override STORAGE_PATH al tmp_path del test.
    original_storage_path = storage_module.settings.STORAGE_PATH
    storage_module.settings.STORAGE_PATH = str(tmp_path)

    try:
        fake_upload = MagicMock()
        fake_upload.content_type = ""  # browser no mandó MIME
        fake_upload.filename = "reporte_ligero.xls"
        fake_upload.read = AsyncMock(return_value=b"BM\x00" * 100)  # 300 bytes fake
        fake_upload.size = 300

        file_url, mime = await storage_module.save_document(
            "tenant-a", "project-b", fake_upload, "doc-123"
        )

        assert file_url == "/api/v1/documents/doc-123/download"
        # Fallback resolvió `.xls` → `application/vnd.ms-excel`.
        assert mime == "application/vnd.ms-excel"

        # Archivo físico creado.
        expected = tmp_path / "documents" / "tenant-a" / "project-b" / "doc-123.xls"
        assert expected.is_file()
        assert expected.stat().st_size == 300
    finally:
        storage_module.settings.STORAGE_PATH = original_storage_path


@pytest.mark.asyncio
async def test_bug029_save_document_rejects_unknown_format(tmp_path):
    """Extensiones no whitelisted (ej. `.exe`) siguen bloqueadas con
    mensaje claro y field `filename` en el error para debugging."""
    from app.core.errors import AppError
    from app.services import document_storage as storage_module

    original_storage_path = storage_module.settings.STORAGE_PATH
    storage_module.settings.STORAGE_PATH = str(tmp_path)

    try:
        fake_upload = MagicMock()
        fake_upload.content_type = "application/octet-stream"
        fake_upload.filename = "malware.exe"
        fake_upload.read = AsyncMock(return_value=b"MZ\x00")
        fake_upload.size = 3

        with pytest.raises(AppError) as exc_info:
            await storage_module.save_document(
                "tenant-a", "project-b", fake_upload, "doc-xxx"
            )

        err_detail = getattr(exc_info.value, "detail", None) or {}
        err_fields = err_detail.get("fields") if isinstance(err_detail, dict) else {}
        assert isinstance(err_fields, dict)
        assert err_fields.get("filename") == "malware.exe"
    finally:
        storage_module.settings.STORAGE_PATH = original_storage_path
