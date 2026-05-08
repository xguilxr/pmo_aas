"""Defaults de AI a nivel de plataforma (US-054, BUG-053).

Superadmin puede ajustar AI_MODE y la config Groq sin redeploy. Los
valores se guardan en la tabla singleton `platform_ai_settings`
(id='default').

Endpoints:
- GET  /api/v1/superadmin/ai/defaults — lee config actual + snapshot env.
- PATCH /api/v1/superadmin/ai/defaults — actualiza campos parciales.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_superadmin
from app.core.config import settings
from app.db.session import get_db
from app.models.platform_settings import PLATFORM_SETTINGS_ID, PlatformAISettings
from app.services.audit import write_audit

router = APIRouter(prefix="/superadmin/ai", tags=["superadmin_ai"])


class EnvSnapshot(BaseModel):
    ai_mode: str
    gemini_configured: bool
    claude_configured: bool
    groq_configured: bool


class PlatformAIDefaultsRead(BaseModel):
    ai_mode: str | None = None
    groq_api_key_mask: str | None = None
    groq_configured: bool = False
    groq_model: str | None = None
    env: EnvSnapshot


class PlatformAIDefaultsPatch(BaseModel):
    ai_mode: Literal["disabled", "platform", "byo"] | None = None
    groq_api_key: str | None = Field(default=None, description="Vacío = borrar; None = conservar")
    groq_model: str | None = Field(default=None, max_length=100)


async def _get_or_create(db: AsyncSession) -> PlatformAISettings:
    row = (
        await db.execute(
            select(PlatformAISettings).where(PlatformAISettings.id == PLATFORM_SETTINGS_ID)
        )
    ).scalar_one_or_none()
    if row is None:
        row = PlatformAISettings(id=PLATFORM_SETTINGS_ID)
        db.add(row)
        await db.flush()
    return row


def _to_read(row: PlatformAISettings) -> PlatformAIDefaultsRead:
    from app.services.ai_secrets import decrypt_secret, mask_secret

    groq_plain = decrypt_secret(row.groq_api_key_encrypted or "")
    return PlatformAIDefaultsRead(
        ai_mode=row.ai_mode,
        groq_api_key_mask=mask_secret(groq_plain) if groq_plain else None,
        groq_configured=bool(groq_plain or settings.GROQ_API_KEY),
        groq_model=row.groq_model,
        env=EnvSnapshot(
            ai_mode=settings.AI_MODE,
            gemini_configured=bool(settings.GEMINI_API_KEY),
            claude_configured=bool(settings.ANTHROPIC_API_KEY),
            groq_configured=bool(settings.GROQ_API_KEY),
        ),
    )


@router.get("/defaults", response_model=PlatformAIDefaultsRead)
async def read_defaults(
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_create(db)
    await db.commit()
    return _to_read(row)


@router.patch("/defaults", response_model=PlatformAIDefaultsRead)
async def update_defaults(
    body: PlatformAIDefaultsPatch,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_create(db)
    data = body.model_dump(exclude_unset=True)
    if "ai_mode" in data:
        row.ai_mode = data["ai_mode"]
    if "groq_api_key" in data and data["groq_api_key"] is not None:
        from app.services.ai_secrets import encrypt_secret

        key = str(data["groq_api_key"])
        row.groq_api_key_encrypted = encrypt_secret(key) if key else ""
    if "groq_model" in data:
        row.groq_model = data["groq_model"]

    await write_audit(
        db, action="superadmin.ai.defaults.update", module="superadmin",
        user_id=cu.id, entity_type="platform_ai_settings", entity_id=PLATFORM_SETTINGS_ID,
        details={"fields_set": list(data.keys())},
    )
    await db.commit()
    return _to_read(row)


# ============================================================================
# US-057 — Panel de tenants + dashboard de uso Groq + ping Groq
# ============================================================================

import time  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402

from sqlalchemy import case, func  # noqa: E402

from app.models.ai import AIJob  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402


class TenantAIStatusRow(BaseModel):
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    mode: str  # disabled | platform | byo
    byo_provider: str | None = None
    byo_model: str | None = None
    byo_api_key_mask: str | None = None
    last_test_at: str | None = None
    last_test_status: str | None = None  # ok | fail | null
    last_test_error: str | None = None


@router.get("/tenants-status", response_model=list[TenantAIStatusRow])
async def list_tenants_ai_status(
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los tenants con su config IA: modo + proveedor + modelo
    + último test. Alimenta el panel del superadmin."""
    from app.services.ai_secrets import decrypt_secret, mask_secret

    rows = (
        await db.execute(
            select(Tenant)
            .where(Tenant.is_active.is_(True))
            .order_by(Tenant.name)
        )
    ).scalars().all()
    out: list[TenantAIStatusRow] = []
    for t in rows:
        ai = dict((t.settings or {}).get("ai") or {})
        mode = str(ai.get("mode") or "disabled")
        byo = ai.get("byo") if isinstance(ai.get("byo"), dict) else None
        byo_plain = decrypt_secret((byo or {}).get("api_key_encrypted") or "")
        out.append(
            TenantAIStatusRow(
                tenant_id=str(t.id),
                tenant_name=t.name,
                tenant_slug=t.slug,
                mode=mode,
                byo_provider=(byo or {}).get("provider"),
                byo_model=(byo or {}).get("model"),
                byo_api_key_mask=mask_secret(byo_plain) if byo_plain else None,
                last_test_at=(byo or {}).get("last_test_at"),
                last_test_status=(byo or {}).get("last_test_status"),
                last_test_error=(byo or {}).get("last_test_error"),
            )
        )
    return out


class GroqUsageDayBucket(BaseModel):
    date: str  # YYYY-MM-DD
    requests: int
    tokens_in: int
    tokens_out: int
    failed: int


class GroqUsageTenantRow(BaseModel):
    tenant_id: str
    tenant_name: str
    requests: int
    tokens_in: int
    tokens_out: int


class GroqUsageSummary(BaseModel):
    days: int
    today_requests: int
    today_tokens: int
    # Free-tier Groq (documentado en el runbook): 14_400 RPD y 1_000_000 TPD
    # para llama-3.1-70b-versatile. Sirven de referencia visual — se
    # actualizan si el owner cambia de tier.
    limit_requests_per_day: int = 14_400
    limit_tokens_per_day: int = 1_000_000
    total_requests: int
    total_tokens: int
    total_failed: int
    by_day: list[GroqUsageDayBucket]
    top_tenants: list[GroqUsageTenantRow]


def _date_bucket(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d")


@router.get("/groq-usage", response_model=GroqUsageSummary)
async def groq_usage(
    days: int = 30,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """US-057: dashboard de uso del modo `platform` (Groq). Sumariza
    requests/tokens/fails agregando sobre `ai_jobs` con
    `provider='groq'` dentro de la ventana solicitada."""
    days = max(1, min(days, 90))
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)

    base_where = [
        AIJob.provider == "groq",
        AIJob.completed_at.is_not(None),
        AIJob.completed_at >= since,
    ]

    totals_row = (
        await db.execute(
            select(
                func.count(AIJob.id),
                func.coalesce(func.sum(AIJob.tokens_in), 0),
                func.coalesce(func.sum(AIJob.tokens_out), 0),
                func.coalesce(
                    func.sum(case((AIJob.status == "failed", 1), else_=0)),
                    0,
                ),
            ).where(*base_where)
        )
    ).first()
    total_requests = int(totals_row[0] or 0)
    total_tokens_in = int(totals_row[1] or 0)
    total_tokens_out = int(totals_row[2] or 0)
    total_failed = int(totals_row[3] or 0)

    today_row = (
        await db.execute(
            select(
                func.count(AIJob.id),
                func.coalesce(func.sum(AIJob.tokens_in), 0),
                func.coalesce(func.sum(AIJob.tokens_out), 0),
            ).where(
                AIJob.provider == "groq",
                AIJob.completed_at.is_not(None),
                AIJob.completed_at >= today_start,
            )
        )
    ).first()
    today_requests = int(today_row[0] or 0)
    today_tokens = int((today_row[1] or 0) + (today_row[2] or 0))

    # Agregación por día — hecha en Python para mantener compat con SQLite
    # (que no tiene date_trunc). El volumen (90 días × ~1k rows) es
    # irrelevante para este dashboard.
    day_rows = (
        await db.execute(
            select(
                AIJob.completed_at,
                AIJob.tokens_in,
                AIJob.tokens_out,
                AIJob.status,
            ).where(*base_where)
        )
    ).all()
    buckets: dict[str, GroqUsageDayBucket] = {}
    for completed_at, t_in, t_out, st in day_rows:
        d = _date_bucket(completed_at)
        if d not in buckets:
            buckets[d] = GroqUsageDayBucket(
                date=d, requests=0, tokens_in=0, tokens_out=0, failed=0,
            )
        buckets[d].requests += 1
        buckets[d].tokens_in += int(t_in or 0)
        buckets[d].tokens_out += int(t_out or 0)
        if st == "failed":
            buckets[d].failed += 1
    by_day = sorted(buckets.values(), key=lambda b: b.date)

    # Top tenants por requests en la ventana.
    top_rows = (
        await db.execute(
            select(
                AIJob.tenant_id,
                Tenant.name,
                func.count(AIJob.id).label("reqs"),
                func.coalesce(func.sum(AIJob.tokens_in), 0),
                func.coalesce(func.sum(AIJob.tokens_out), 0),
            )
            .join(Tenant, Tenant.id == AIJob.tenant_id)
            .where(*base_where)
            .group_by(AIJob.tenant_id, Tenant.name)
            .order_by(func.count(AIJob.id).desc())
            .limit(10)
        )
    ).all()
    top_tenants = [
        GroqUsageTenantRow(
            tenant_id=str(r[0]),
            tenant_name=str(r[1]),
            requests=int(r[2] or 0),
            tokens_in=int(r[3] or 0),
            tokens_out=int(r[4] or 0),
        )
        for r in top_rows
    ]

    return GroqUsageSummary(
        days=days,
        today_requests=today_requests,
        today_tokens=today_tokens,
        total_requests=total_requests,
        total_tokens=total_tokens_in + total_tokens_out,
        total_failed=total_failed,
        by_day=by_day,
        top_tenants=top_tenants,
    )


class GroqPingResult(BaseModel):
    ok: bool
    latency_ms: int | None = None
    error: str | None = None
    model: str | None = None


@router.post("/groq/ping", response_model=GroqPingResult)
async def ping_groq(
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """US-057: valida la GROQ_API_KEY + modelo actuales con un completion
    mínimo. El superadmin llama esto al guardar para asegurar que Groq
    responde antes de habilitar tenants en modo platform."""
    import httpx

    from app.services.ai.platform_config import resolve_groq_config

    cfg = await resolve_groq_config(db)
    if cfg is None:
        return GroqPingResult(
            ok=False, error="GROQ_API_KEY no configurado",
        )
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {cfg['api_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": cfg["model"],
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 4,
                },
            )
        latency = int((time.perf_counter() - started) * 1000)
        if r.status_code >= 300:
            return GroqPingResult(
                ok=False, latency_ms=latency,
                error=f"HTTP {r.status_code}: {r.text[:160]}",
            )
        return GroqPingResult(ok=True, latency_ms=latency, model=cfg["model"])
    except httpx.TimeoutException:
        return GroqPingResult(ok=False, error="Timeout al conectar con Groq")
    except Exception as exc:
        return GroqPingResult(ok=False, error=str(exc)[:200])
