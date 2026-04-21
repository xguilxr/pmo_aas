"""Config y smoke de proveedores IA por-tenant.

Historia:
- US-NEW-045 (2026-04-20): versión inicial con Cloudflare Tunnel +
  Service Token (CF-Access-Client-Id / CF-Access-Client-Secret).
- US-NEW-047 (2026-04-21): pivote a Tailscale — se eliminan los campos
  CF-Access. La config por-tenant pasa a `{base_url, model, timeout_sec}`.
  El canal PC→worker se asegura por tailnet WireGuard (ver EP016 +
  DEC-011). Los secrets Fernet legacy en BD se ignoran al leer y no se
  escriben más; `AI_SECRETS_FERNET_KEY` queda deprecado.

Endpoints:
- GET  /api/v1/admin/ai/ollama      — devuelve config.
- PATCH /api/v1/admin/ai/ollama     — actualiza config.
- POST /api/v1/admin/ai/test-connection — ping al endpoint tailnet.
"""
from __future__ import annotations

import time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import AnyHttpUrl, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.tenant import Tenant
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
    configured: bool = False


class OllamaConfigPatch(BaseModel):
    # US-NEW-047: AnyHttpUrl acepta http://host.ts.net:11434 (MagicDNS
    # tailnet) además de https. HttpUrl v2 validaba esquema y host;
    # AnyHttpUrl es el correcto para endpoints LAN/tailnet privados.
    base_url: AnyHttpUrl | None = None
    model: str | None = Field(default=None, max_length=100)
    timeout_sec: int | None = Field(default=None, ge=5, le=600)


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
    return OllamaConfigRead(
        base_url=cfg.get("base_url"),
        model=cfg.get("model"),
        timeout_sec=int(cfg.get("timeout_sec") or 60),
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

    # US-NEW-047: si el tenant tenía claves CF-Access legacy, las archivamos
    # bajo `auth_legacy` una sola vez (no se borran para auditoría) y dejamos
    # la rama activa limpia.
    legacy_keys = [
        "cf_access_client_id",
        "cf_access_client_secret_encrypted",
    ]
    if any(k in ollama_cfg for k in legacy_keys):
        auth_legacy = dict(ollama_cfg.get("auth_legacy") or {})
        for k in legacy_keys:
            if k in ollama_cfg:
                auth_legacy[k] = ollama_cfg.pop(k)
        ollama_cfg["auth_legacy"] = auth_legacy

    data = body.model_dump(exclude_unset=True)
    if "base_url" in data and data["base_url"] is not None:
        ollama_cfg["base_url"] = str(data["base_url"]).rstrip("/")
    if "model" in data and data["model"] is not None:
        ollama_cfg["model"] = data["model"]
    if "timeout_sec" in data and data["timeout_sec"] is not None:
        ollama_cfg["timeout_sec"] = int(data["timeout_sec"])

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
        details={"fields_set": list(data.keys())},
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

    # US-NEW-047: canal Tailscale no requiere headers de auth. El request es
    # un GET plano al endpoint privado del tailnet.
    headers: dict[str, str] = {"Accept": "application/json"}

    timeout = float(cfg.get("timeout_sec") or 10)
    # Para un ping, 15 s es un techo razonable aunque timeout_sec sea más alto.
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
