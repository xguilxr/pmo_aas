"""US-066: storage S3-compatible (Cloudflare R2 en prod, mocked con
moto en tests).

Cubre el contrato del nuevo selector `STORAGE_BACKEND`:
- save_document(): persiste en S3 con la key esperada.
- get_document_stream(): recupera el iterator + extensión.
- delete_document_file(): borra el objeto.
- Endpoint GET /download: StreamingResponse con el body correcto.

Los tests usan `moto[s3]` para simular el bucket en proceso. No
hablan con R2/B2 reales.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import boto3
import pytest
from moto import mock_aws

from app.services import document_storage as storage_module


@pytest.fixture
def s3_backend(monkeypatch):
    """Activa backend S3 con moto. Yieldea el cliente boto3 conectado
    al bucket virtual para hacer asserts directos."""
    monkeypatch.setattr(storage_module.settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(storage_module.settings, "S3_BUCKET", "pmo-test-bucket")
    monkeypatch.setattr(
        storage_module.settings, "S3_ENDPOINT_URL", "https://s3.example.com"
    )
    monkeypatch.setattr(storage_module.settings, "S3_ACCESS_KEY_ID", "AKIAFAKE")
    monkeypatch.setattr(
        storage_module.settings, "S3_SECRET_ACCESS_KEY", "SECRETFAKE"
    )
    monkeypatch.setattr(storage_module.settings, "S3_REGION", "us-east-1")

    # Reset singleton para que use las nuevas settings.
    storage_module._reset_s3_client()

    with mock_aws():
        # Crear bucket en el moto S3 virtual.
        boto3.client(
            "s3",
            endpoint_url="https://s3.example.com",
            aws_access_key_id="AKIAFAKE",
            aws_secret_access_key="SECRETFAKE",
            region_name="us-east-1",
        )
        # moto ignora endpoint_url; el bucket se crea en el namespace global.
        actual_client = boto3.client("s3", region_name="us-east-1")
        actual_client.create_bucket(Bucket="pmo-test-bucket")

        # Re-construir el client de la app sin endpoint_url (moto-compatible).
        storage_module._reset_s3_client()

        def _patched_get_s3_client():
            return actual_client

        monkeypatch.setattr(storage_module, "_get_s3_client", _patched_get_s3_client)
        yield actual_client

    storage_module._reset_s3_client()


def _make_upload(content: bytes, filename: str, content_type: str) -> MagicMock:
    """Construye un mock de FastAPI UploadFile con read() async."""
    upload = MagicMock()
    upload.filename = filename
    upload.content_type = content_type
    upload.size = len(content)
    upload.read = AsyncMock(return_value=content)
    return upload


@pytest.mark.asyncio
async def test_us066_s3_save_puts_object_with_correct_key(s3_backend):
    """save_document() en backend s3 hace put_object al bucket con
    la key `documents/{tenant}/{project}/{doc}.xlsx`."""
    # ASVS 12.4.2: un `.xlsx` es un ZIP, así que empieza por `PK\x03\x04`. El
    # contenido de relleno anterior no pasaba de ser texto suelto con nombre de
    # hoja de cálculo — justo lo que el análisis de firma rechaza ahora.
    xlsx = b"PK\x03\x04" + b"fake xlsx bytes"
    upload = _make_upload(
        xlsx,
        "reporte.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    file_url, mime = await storage_module.save_document(
        "tenant-a", "project-b", upload, "doc-001"
    )

    assert file_url == "/api/v1/documents/doc-001/download"
    assert mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Verificar en moto que el objeto existe.
    obj = s3_backend.get_object(
        Bucket="pmo-test-bucket",
        Key="documents/tenant-a/project-b/doc-001.xlsx",
    )
    assert obj["Body"].read() == xlsx
    assert obj["ContentType"].startswith("application/vnd.openxmlformats")


@pytest.mark.asyncio
async def test_us066_s3_get_stream_returns_bytes(s3_backend):
    """get_document_stream() lee el objeto desde S3 y devuelve un
    iterator con los bytes + la extensión."""
    upload = _make_upload(b"%PDF-1.4 fake pdf", "report.pdf", "application/pdf")
    await storage_module.save_document(
        "tenant-x", "project-y", upload, "doc-002"
    )

    result = storage_module.get_document_stream("tenant-x", "project-y", "doc-002")
    assert result is not None
    iterator, ext = result
    assert ext == "pdf"
    body = b"".join(iterator)
    assert body == b"%PDF-1.4 fake pdf"


def test_us066_s3_get_stream_returns_none_for_missing(s3_backend):
    """get_document_stream() devuelve None si el objeto no existe en
    S3 (cualquiera de las extensiones whitelisted)."""
    result = storage_module.get_document_stream(
        "tenant-x", "project-y", "doc-nonexistent"
    )
    assert result is None


@pytest.mark.asyncio
async def test_us066_s3_delete_removes_object(s3_backend):
    """delete_document_file() llama delete_object en S3 y devuelve
    True; siguiente get_document_stream devuelve None."""
    upload = _make_upload(b"to be deleted", "del.csv", "text/csv")
    await storage_module.save_document(
        "tenant-d", "project-e", upload, "doc-del"
    )

    removed = storage_module.delete_document_file(
        "tenant-d", "project-e", "doc-del"
    )
    assert removed is True

    result = storage_module.get_document_stream(
        "tenant-d", "project-e", "doc-del"
    )
    assert result is None


def test_us066_s3_delete_no_op_when_missing(s3_backend):
    """Borrar un doc inexistente devuelve False sin levantar excepción."""
    removed = storage_module.delete_document_file(
        "tenant-z", "project-z", "doc-never-existed"
    )
    assert removed is False


@pytest.mark.asyncio
async def test_us066_local_backend_still_works(monkeypatch, tmp_path):
    """Backend local sigue siendo funcional. No regresión vs BUG-029."""
    monkeypatch.setattr(storage_module.settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(storage_module.settings, "STORAGE_PATH", str(tmp_path))

    upload = _make_upload(b"hello local", "note.txt", "text/plain")
    file_url, mime = await storage_module.save_document(
        "tenant-l", "project-m", upload, "doc-local-1"
    )

    assert file_url == "/api/v1/documents/doc-local-1/download"
    assert mime == "text/plain"

    target = tmp_path / "documents" / "tenant-l" / "project-m" / "doc-local-1.txt"
    assert target.is_file()
    assert target.read_bytes() == b"hello local"

    # Stream
    result = storage_module.get_document_stream(
        "tenant-l", "project-m", "doc-local-1"
    )
    assert result is not None
    iterator, ext = result
    assert ext == "txt"
    assert b"".join(iterator) == b"hello local"

    # Delete
    assert storage_module.delete_document_file(
        "tenant-l", "project-m", "doc-local-1"
    )
    assert not target.exists()


def test_us066_s3_client_fails_without_bucket(monkeypatch):
    """Si STORAGE_BACKEND=s3 pero S3_BUCKET vacío, _get_s3_client()
    levanta AppError en vez de un boto error críptico."""
    from app.core.errors import AppError

    monkeypatch.setattr(storage_module.settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(storage_module.settings, "S3_BUCKET", "")
    monkeypatch.setattr(storage_module.settings, "S3_ENDPOINT_URL", "")

    storage_module._reset_s3_client()

    with pytest.raises(AppError) as exc_info:
        storage_module._get_s3_client()

    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "STORAGE_NOT_CONFIGURED"
