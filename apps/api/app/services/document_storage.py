"""Project document file storage (file upload for documents).

US-066 (2026-04-24): selector de backend `STORAGE_BACKEND`:
- `local` (default dev): filesystem bajo `STORAGE_PATH`. No persiste
  entre redeploys de Railway → solo dev / branding tenant.
- `s3` (prod): object storage S3-compatible (Cloudflare R2 por
  default; Backblaze B2 / AWS S3 / MinIO también funcionan ajustando
  `S3_ENDPOINT_URL` + `S3_REGION`). Requiere las 6 env vars S3_*
  (ver docs/runbooks/infra/uploads-storage.md).

Razón del refactor: Railway Volumes no se pueden compartir entre
servicios, así que api (uploads) + worker (PDFs generados) necesitan
storage común vía red. Object storage es el patrón estándar.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import IO

from fastapi import UploadFile, status

from app.core.config import settings
from app.core.errors import AppError, validation_error
from app.core.unidades import a_mebibytes, mebibytes

# BUG-040: límite reducido a 1 MB. La plataforma no es un drive
# corporativo; documentos grandes deben vivir en SharePoint/Drive y
# enlazarse desde el comentario.
MAX_DOC_BYTES = mebibytes(1)

#: Cuánto se lee de golpe al copiar un archivo. No es un límite de negocio;
#: se nombra porque estaba escrito dos veces con el mismo `64 * 1024`.
TROZO_BYTES = 64 * 1024

# MIME -> extensión canónica (whitelist: PDF, XLSX, DOCX, PPTX, PNG, JPG, CSV,
# + formatos legacy XLS/DOC/PPT). BUG-029 agrega los legacy porque algunos
# Excel "ligeros" del owner se guardaban como .xls con MIME
# `application/vnd.ms-excel` y caían del whitelist.
ALLOWED_DOC_MIMES: dict[str, str] = {
    "application/pdf": "pdf",
    # Office 2007+ (OOXML)
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    # Office 97-2003 (legacy binary)
    "application/vnd.ms-excel": "xls",
    "application/msword": "doc",
    "application/vnd.ms-powerpoint": "ppt",
    # Imágenes
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    # Datos
    "text/csv": "csv",
    "application/csv": "csv",
    "text/plain": "txt",
}

# Fallback por extensión cuando el browser manda `application/octet-stream`
# o vacío (caso común al arrastrar archivos desde explorer en Windows).
_EXTENSION_FALLBACK: dict[str, str] = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "ppt": "application/vnd.ms-powerpoint",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "csv": "text/csv",
    "txt": "text/plain",
}


# ============================================================================
# Resolución de MIME + validación común
# ============================================================================


def _resolve_mime(upload: UploadFile) -> tuple[str, str]:
    """Return `(content_type, ext)` para un upload, aplicando fallback
    por extensión si el browser no mandó MIME conocido. Levanta
    `validation_error` si el formato no está whitelisted."""
    content_type = (upload.content_type or "").lower()
    ext = ALLOWED_DOC_MIMES.get(content_type)

    # BUG-029: fallback por extensión del filename cuando el browser
    # manda `application/octet-stream` o vacío.
    if ext is None:
        filename = (upload.filename or "").lower()
        fname_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        if fname_ext in _EXTENSION_FALLBACK:
            content_type = _EXTENSION_FALLBACK[fname_ext]
            ext = ALLOWED_DOC_MIMES.get(content_type)

    if ext is None:
        raise validation_error(
            "Formato no permitido. Usa PDF, XLSX, DOCX, PPTX, PNG, JPG, CSV o TXT.",
            fields={
                "mime": upload.content_type or "",
                "filename": upload.filename or "",
            },
        )
    return content_type, ext


def _validate_size(data: bytes) -> None:
    if len(data) == 0:
        raise validation_error("Archivo vacío")
    if len(data) > MAX_DOC_BYTES:
        raise AppError(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "PAYLOAD_TOO_LARGE",
            f"El documento excede {a_mebibytes(MAX_DOC_BYTES):.0f} MB",
            {"max_bytes": MAX_DOC_BYTES, "size": len(data)},
        )


def _doc_key(tenant_id: str, project_id: str, document_id: str, ext: str) -> str:
    """Object key (S3) o sufijo de path (local) — formato consistente."""
    return f"documents/{tenant_id}/{project_id}/{document_id}.{ext}"


# ============================================================================
# Backend: local filesystem (dev / branding)
# ============================================================================


def _local_full_path(key: str) -> Path:
    return Path(settings.STORAGE_PATH) / key


async def _save_local(
    tenant_id: str, project_id: str, upload: UploadFile, document_id: str
) -> tuple[str, str]:
    content_type, ext = _resolve_mime(upload)
    data = await upload.read()
    _validate_size(data)

    key = _doc_key(tenant_id, project_id, document_id, ext)
    target = _local_full_path(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

    return f"/api/v1/documents/{document_id}/download", content_type


def _stream_local(
    tenant_id: str, project_id: str, document_id: str
) -> tuple[Iterator[bytes], str] | None:
    """Devuelve `(iterator, ext)` o `None` si no existe."""
    base = _local_full_path(_doc_key(tenant_id, project_id, document_id, "")).parent
    for ext in set(ALLOWED_DOC_MIMES.values()):
        candidate = base / f"{document_id}.{ext}"
        if candidate.is_file():
            def _gen(path: Path = candidate) -> Iterator[bytes]:
                with path.open("rb") as fh:
                    while chunk := fh.read(TROZO_BYTES):
                        yield chunk

            return _gen(), ext
    return None


def _delete_local(tenant_id: str, project_id: str, document_id: str) -> bool:
    base = _local_full_path(_doc_key(tenant_id, project_id, document_id, "")).parent
    removed = False
    for ext in set(ALLOWED_DOC_MIMES.values()):
        f = base / f"{document_id}.{ext}"
        if f.exists():
            f.unlink()
            removed = True
    return removed


# ============================================================================
# Backend: S3-compatible (Cloudflare R2 / B2 / AWS S3 / MinIO)
# ============================================================================


_s3_client = None  # lazy singleton


def _get_s3_client():
    """Lazy boto3 client. Falla con AppError si las env vars no están."""
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    if not settings.S3_BUCKET or not settings.S3_ENDPOINT_URL:
        raise AppError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "STORAGE_NOT_CONFIGURED",
            "Storage S3 no configurado. Falta S3_BUCKET o S3_ENDPOINT_URL.",
            {},
        )
    import boto3
    from botocore.config import Config

    _s3_client = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        region_name=settings.S3_REGION or "auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
    return _s3_client


def _reset_s3_client() -> None:
    """Test helper — reset el singleton tras cambiar settings/env vars."""
    global _s3_client
    _s3_client = None


async def _save_s3(
    tenant_id: str, project_id: str, upload: UploadFile, document_id: str
) -> tuple[str, str]:
    content_type, ext = _resolve_mime(upload)
    data = await upload.read()
    _validate_size(data)

    key = _doc_key(tenant_id, project_id, document_id, ext)
    client = _get_s3_client()
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    return f"/api/v1/documents/{document_id}/download", content_type


def _stream_s3(
    tenant_id: str, project_id: str, document_id: str
) -> tuple[Iterator[bytes], str] | None:
    """Busca el objeto en cada extensión posible y devuelve el stream."""
    from botocore.exceptions import ClientError

    client = _get_s3_client()
    for ext in set(ALLOWED_DOC_MIMES.values()):
        key = _doc_key(tenant_id, project_id, document_id, ext)
        try:
            obj = client.get_object(Bucket=settings.S3_BUCKET, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                continue
            raise
        body: IO[bytes] = obj["Body"]

        def _gen(stream: IO[bytes] = body) -> Iterator[bytes]:
            try:
                while chunk := stream.read(TROZO_BYTES):
                    yield chunk
            finally:
                stream.close()

        return _gen(), ext
    return None


def _delete_s3(tenant_id: str, project_id: str, document_id: str) -> bool:
    from botocore.exceptions import ClientError

    client = _get_s3_client()
    removed = False
    for ext in set(ALLOWED_DOC_MIMES.values()):
        key = _doc_key(tenant_id, project_id, document_id, ext)
        try:
            client.head_object(Bucket=settings.S3_BUCKET, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                continue
            raise
        client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
        removed = True
    return removed


# ============================================================================
# Public API — selector por settings.STORAGE_BACKEND
# ============================================================================


async def save_document(
    tenant_id: str, project_id: str, upload: UploadFile, document_id: str
) -> tuple[str, str]:
    """Persiste el documento en el backend configurado.

    Returns: `(file_url, mime_type)`. `file_url` es siempre la ruta del
    endpoint de descarga (`/api/v1/documents/{id}/download`); el cliente
    nunca toca el storage directo.
    """
    if settings.STORAGE_BACKEND == "s3":
        return await _save_s3(tenant_id, project_id, upload, document_id)
    return await _save_local(tenant_id, project_id, upload, document_id)


def save_document_bytes(
    tenant_id: str,
    project_id: str,
    document_id: str,
    *,
    data: bytes,
    ext: str,
    content_type: str,
) -> tuple[str, str]:
    """BUG-028: persiste bytes generados server-side (p. ej. charter .docx
    generado con python-docx) sin pasar por UploadFile.

    Returns: `(file_url, content_type)` — mismo contrato que `save_document`.
    """
    _validate_size(data)
    if ext not in set(ALLOWED_DOC_MIMES.values()):
        raise validation_error(
            f"Extensión no whitelisted para storage: {ext}",
            fields={"ext": ext},
        )
    key = _doc_key(tenant_id, project_id, document_id, ext)
    if settings.STORAGE_BACKEND == "s3":
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    else:
        target = _local_full_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return f"/api/v1/documents/{document_id}/download", content_type


def get_document_stream(
    tenant_id: str, project_id: str, document_id: str
) -> tuple[Iterator[bytes], str] | None:
    """Devuelve `(iterator de bytes, extensión)` o `None` si no existe.

    El iterator es lazy y debe consumirse en un `StreamingResponse` de
    FastAPI. Para backends S3 cierra el cuerpo HTTP cuando termina el
    iterator.
    """
    if settings.STORAGE_BACKEND == "s3":
        return _stream_s3(tenant_id, project_id, document_id)
    return _stream_local(tenant_id, project_id, document_id)


def delete_document_file(
    tenant_id: str, project_id: str, document_id: str
) -> bool:
    """Borra el archivo (en cualquier extensión) del backend configurado.
    Returns True si se borró algo."""
    if settings.STORAGE_BACKEND == "s3":
        return _delete_s3(tenant_id, project_id, document_id)
    return _delete_local(tenant_id, project_id, document_id)


def get_document_presigned_url(
    tenant_id: str,
    project_id: str,
    document_id: str,
    *,
    expires_in: int = 300,
    download_filename: str | None = None,
) -> str | None:
    """BUG-034: devuelve presigned URL del objeto S3 (R2) para que el
    frontend pueda hacer descarga directa sin pasar por el backend.

    Resuelve el problema del `<a href>` plain que no enviaba
    `Authorization: Bearer <token>` y daba 401/404.

    Para backend `local` devuelve `None` (la UI debe seguir usando el
    endpoint streaming protegido por auth header). Para backend `s3`
    devuelve URL firmada con `expires_in` segundos (default 5 min).

    El parámetro `download_filename` agrega `response-content-disposition`
    para que el browser descargue con nombre legible.
    """
    if settings.STORAGE_BACKEND != "s3":
        return None
    from botocore.exceptions import ClientError

    client = _get_s3_client()
    for ext in set(ALLOWED_DOC_MIMES.values()):
        key = _doc_key(tenant_id, project_id, document_id, ext)
        try:
            client.head_object(Bucket=settings.S3_BUCKET, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                continue
            raise
        params: dict = {"Bucket": settings.S3_BUCKET, "Key": key}
        if download_filename:
            from urllib.parse import quote

            safe = quote(download_filename)
            params["ResponseContentDisposition"] = (
                f'attachment; filename="{download_filename}"; '
                f"filename*=UTF-8''{safe}"
            )
        return client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )
    return None


# ============================================================================
# Compatibilidad legacy — código viejo importa estos directo.
# ============================================================================


def get_document_path(
    tenant_id: str, project_id: str, document_id: str
) -> Path | None:
    """**DEPRECATED (US-066):** solo funciona con backend `local`. Usar
    `get_document_stream()` en su lugar.

    Mantenido para no romper imports existentes (ej. tests legacy o
    scripts ad-hoc) durante la transición. Backend `s3` retorna `None`
    porque no hay path local."""
    if settings.STORAGE_BACKEND != "local":
        return None
    base = _local_full_path(_doc_key(tenant_id, project_id, document_id, "")).parent
    for ext in set(ALLOWED_DOC_MIMES.values()):
        candidate = base / f"{document_id}.{ext}"
        if candidate.is_file():
            return candidate
    return None
