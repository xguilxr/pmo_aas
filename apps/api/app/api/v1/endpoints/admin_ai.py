"""Config y smoke de proveedores IA por-tenant (EP016 US-NEW-045).

Endpoints:
- GET  /api/v1/admin/ai/ollama      — devuelve config (secret enmascarado).
- PATCH /api/v1/admin/ai/ollama     — actualiza y cifra el secret.
- POST /api/v1/admin/ai/test-connection — ping al túnel / API Ollama.
"""
from __future__ import annotations

import time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.ai_secrets import decrypt_secret, encrypt_secret, mask_secret
from app.services.audit import write_audit

router = APIRouter(prefix="/admin/ai", tags=["admin_ai"])


def _tenant_id(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


def _read_ollama_config(t: Tenant) -> dict:
    return dict(((t.settings or {}).get("ai") or {}).get("ollama") or {})


class OllamaConfigRead(BaseModel):
    base_url: str | None = None
    model: str | None = None
    timeout_sec: int = 60
    cf_access_client_id: str | None = None
    cf_access_client_secret_masked: str | None = None
    configured: bool = False


class OllamaConfigPatch(BaseModel):
    base_url: HttpUrl | None = None
    model: str | None = Field(default=None, max_length=100)
    timeout_sec: int | None = Field(default=None, ge=5, le=600)
    cf_access_client_id: str | None = Field(default=None, max_length=200)
    cf_access_client_secret: str | None = Field(default=None, max_length=2000)
    clear_secret: bool = False


@router.get("/ollama", response_model=OllamaConfigRead)
async def get_ollama_config(
    cu: CurrentUser = Depends(require_permission("admin.users", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    cfg = _read_ollama_config(t)
    secret_plain = decrypt_secret(cfg.get("cf_access_client_secret_encrypted"))
    return OllamaConfigRead(
        base_url=cfg.get("base_url"),
        model=cfg.get("model"),
        timeout_sec=int(cfg.get("timeout_sec") or 60),
        cf_access_client_id=cfg.get("cf_access_client_id"),
        cf_access_client_secret_masked=mask_secret(secret_plain) if secret_plain else None,
        configured=bool(cfg.get("base_url")),
    )


@router.patch("/ollama", response_model=OllamaConfigRead)
async def update_ollama_config(
    body: OllamaConfigPatch,
    cu: CurrentUser = Depends(require_permission("admin.users", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    merged_settings = dict(t.settings or {})
    ai_settings = dict(merged_settings.get("ai") or {})
    ollama_cfg = dict(ai_settings.get("ollama") or {})

    data = body.model_dump(exclude_unset=True)
    # pydantic HttpUrl → str cuando se persiste
    if "base_url" in data and data["base_url"] is not None:
        ollama_cfg["base_url"] = str(data["base_url"]).rstrip("/")
    if "model" in data and data["model"] is not None:
        ollama_cfg["model"] = data["model"]
    if "timeout_sec" in data and data["timeout_sec"] is not None:
        ollama_cfg["timeout_sec"] = int(data["timeout_sec"])
    if "cf_access_client_id" in data and data["cf_access_client_id"] is not None:
        ollama_cfg["cf_access_client_id"] = data["cf_access_client_id"]
    if body.clear_secret:
        ollama_cfg.pop("cf_access_client_secret_encrypted", None)
    elif data.get("cf_access_client_secret") is not None:
        ollama_cfg["cf_access_client_secret_encrypted"] = encrypt_secret(
            data["cf_access_client_secret"]
        )

    ai_settings["ollama"] = ollama_cfg
    merged_settings["ai"] = ai_settings
    t.settings = merged_settings

    await write_audit(
        db,
        action="tenant.ai.ollama.update",
        module="admin.ai",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="tenant",
        entity_id=str(t.id),
        details={
            "fields_set": [k for k in data.keys() if k != "cf_access_client_secret"],
            "secret_updated": "cf_access_client_secret" in data or body.clear_secret,
        },
    )
    await db.commit()
    return await get_ollama_config(cu=cu, db=db)  # type: ignore[arg-type]


class TestConnectionBody(BaseModel):
    provider: Literal["ollama"] = "ollama"


class TestConnectionResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    ok: bool
    latency_ms: int | None = None
    model_present: bool | None = None
    tags_count: int | None = None
    error: str | None = None
    code: str | None = None


@router.post("/test-connection", response_model=TestConnectionResult)
async def test_ai_connection(
    body: TestConnectionBody,
    cu: CurrentUser = Depends(require_permission("admin.users", "update")),
    db: AsyncSession = Depends(get_db),
):
    import httpx

    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    cfg = _read_ollama_config(t)
    base_url = cfg.get("base_url")
    if not base_url:
        return TestConnectionResult(ok=False, error="base_url no configurado", code="NOT_CONFIGURED")

    headers: dict[str, str] = {"Accept": "application/json"}
    if cfg.get("cf_access_client_id"):
        headers["CF-Access-Client-Id"] = cfg["cf_access_client_id"]
    secret_plain = decrypt_secret(cfg.get("cf_access_client_secret_encrypted"))
    if secret_plain:
        headers["CF-Access-Client-Secret"] = secret_plain

    timeout = float(cfg.get("timeout_sec") or 10)
    # Para un ping, 10s es un techo razonable aunque timeout_sec sea más alto.
    timeout = min(timeout, 15.0)

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as c:
            r = await c.get(f"{base_url.rstrip('/')}/api/tags")
            latency_ms = int((time.perf_counter() - started) * 1000)
            if r.status_code != 200:
                return TestConnectionResult(
                    ok=False,
                    latency_ms=latency_ms,
                    error=f"HTTP {r.status_code}",
                    code="HTTP_ERROR",
                )
            data = r.json()
            models = data.get("models") or []
            tags_count = len(models)
            expected = cfg.get("model")
            model_present = bool(
                expected and any(m.get("name") == expected for m in models)
            )
            await write_audit(
                db,
                action="tenant.ai.ollama.test",
                module="admin.ai",
                user_id=cu.id,
                tenant_id=tenant_id,
                entity_type="tenant",
                entity_id=str(t.id),
                details={
                    "ok": True,
                    "latency_ms": latency_ms,
                    "model_present": model_present,
                    "tags_count": tags_count,
                },
            )
            await db.commit()
            return TestConnectionResult(
                ok=True,
                latency_ms=latency_ms,
                model_present=model_present,
                tags_count=tags_count,
            )
    except httpx.TimeoutException:
        return TestConnectionResult(
            ok=False,
            error=f"Timeout tras {int(timeout)}s",
            code="TIMEOUT",
        )
    except httpx.HTTPError as exc:
        return TestConnectionResult(
            ok=False, error=str(exc)[:200], code="HTTP_EXCEPTION"
        )
    except Exception as exc:  # noqa: BLE001
        return TestConnectionResult(
            ok=False, error=str(exc)[:200], code="UNKNOWN"
        )
