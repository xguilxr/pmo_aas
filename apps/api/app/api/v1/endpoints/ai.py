import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import forbidden, not_found, validation_error
from app.db.session import get_db
from app.models.ai import AIJob, Report
from app.models.modules import MeetingMinute, Risk
from app.models.project import Project
from app.models.tenant import Tenant
from app.services.ai.prompts import MINUTE_SYSTEM, REPORT_SYSTEM
from app.services.ai.provider import chunk_text, generate_with_cascade
from app.services.audit import write_audit
from app.services.folio import next_folio

router = APIRouter(prefix="/ai", tags=["ai"])

MAX_TRANSCRIPT_BYTES = 5 * 1024 * 1024


class GenerateMinuteRequest(BaseModel):
    project_id: UUID
    transcript: str = Field(min_length=10)
    language: str | None = None
    save_as_minute: bool = True
    title: str = "Minuta (IA)"


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


async def _tenant_ollama_config(db: AsyncSession, tenant_id: UUID) -> dict | None:
    """US-048: devuelve la config Ollama por-tenant si tiene base_url.

    Si no está configurada (o tenant no existe), devuelve None y la
    cascada cae a los env globales del worker.
    """
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        return None
    cfg = dict(((t.settings or {}).get("ai") or {}).get("ollama") or {})
    if not cfg.get("base_url"):
        return None
    return cfg


def _parse_json_strict(s: str) -> dict | None:
    try:
        return json.loads(s)
    except Exception:
        # Intento extraer {...} si el modelo envolvió texto
        start = s.find("{")
        end = s.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(s[start : end + 1])
            except Exception:
                return None
        return None


@router.post("/minutes")
async def generate_minute(
    body: GenerateMinuteRequest,
    cu: CurrentUser = Depends(require_permission("ai.generate", "create")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    if len(body.transcript.encode("utf-8")) > MAX_TRANSCRIPT_BYTES:
        from fastapi import HTTPException

        raise HTTPException(status_code=413, detail={"code": "PAYLOAD_TOO_LARGE"})

    # Valida proyecto
    p = (
        await db.execute(
            select(Project).where(Project.id == str(body.project_id), Project.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")

    job = AIJob(
        tenant_id=str(tenant_id), project_id=str(body.project_id),
        kind="minute_from_transcript", status="running",
        input={"len": len(body.transcript), "lang": body.language},
        requested_by=cu.id,
    )
    db.add(job)
    await db.flush()

    started = datetime.now(UTC)
    ollama_cfg = await _tenant_ollama_config(db, tenant_id)
    chunks = chunk_text(body.transcript)
    collected: list[dict] = []
    model_used = "unknown"
    total_in = 0
    total_out = 0
    for ch in chunks:
        res = await generate_with_cascade(
            ch, system=MINUTE_SYSTEM, tenant_ollama_config=ollama_cfg,
        )
        model_used = res.model
        total_in += res.tokens_in
        total_out += res.tokens_out
        parsed = _parse_json_strict(res.text)
        if parsed is None:
            parsed = {"summary": res.text[:2000], "participants": [], "topics": [],
                      "agreements": [], "decisions": [], "next_steps": [], "risks_blockers": []}
        collected.append(parsed)

    # Merge simple: unir listas, concatenar summaries
    merged = {
        "summary": "\n\n".join([c.get("summary") or "" for c in collected]).strip(),
        "participants": sum((c.get("participants") or [] for c in collected), []),
        "topics": sum((c.get("topics") or [] for c in collected), []),
        "agreements": sum((c.get("agreements") or [] for c in collected), []),
        "decisions": sum((c.get("decisions") or [] for c in collected), []),
        "next_steps": sum((c.get("next_steps") or [] for c in collected), []),
        "risks_blockers": sum((c.get("risks_blockers") or [] for c in collected), []),
    }

    job.status = "succeeded"
    job.output = merged
    job.model_used = model_used
    job.tokens_in = total_in
    job.tokens_out = total_out
    job.duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    job.completed_at = datetime.now(UTC)

    minute_id = None
    if body.save_as_minute:
        folio = await next_folio(db, tenant_id=tenant_id, prefix="MIN")
        mm = MeetingMinute(
            tenant_id=str(tenant_id), project_id=str(body.project_id), folio=folio,
            title=body.title, meeting_date=datetime.now(UTC),
            participants=merged["participants"], topics=merged["topics"],
            agreements=merged["agreements"], next_meeting_date=None,
            attachments=[], generated_by_ai=True, status="final", created_by=cu.id,
        )
        db.add(mm)
        await db.flush()
        minute_id = str(mm.id)

    await write_audit(
        db, action="ai.minute.generate", module="ai", user_id=cu.id, tenant_id=tenant_id,
        entity_type="ai_job", entity_id=str(job.id),
        details={"model": model_used, "duration_ms": job.duration_ms, "minute_id": minute_id},
    )
    await db.commit()
    return {
        "job_id": str(job.id), "status": job.status, "model": model_used,
        "output": merged, "minute_id": minute_id,
    }


class ReportDraftRequest(BaseModel):
    recipients: list[str] = []


@router.post("/projects/{project_id}/reports/draft")
async def draft_report(
    project_id: UUID,
    body: ReportDraftRequest,
    cu: CurrentUser = Depends(require_permission("ai.generate", "create")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = (
        await db.execute(
            select(Project).where(Project.id == str(project_id), Project.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")

    # Recolectar contexto
    top_risks = (
        await db.execute(
            select(Risk.title, Risk.severity, Risk.status)
            .where(Risk.project_id == p.id, Risk.status != "closed")
            .order_by(desc(Risk.severity))
            .limit(5)
        )
    ).all()
    context = {
        "project": {
            "name": p.name, "folio": p.folio, "phase": p.phase,
            "progress": int(p.progress or 0),
            "budget_plan": float(p.budget or 0),
            "budget_actual": float(p.actual_budget or 0),
            "health": p.health_status,
        },
        "top_risks": [
            {"title": r.title, "severity": r.severity, "status": r.status}
            for r in top_risks
        ],
    }

    prompt = json.dumps(context, ensure_ascii=False)
    ollama_cfg = await _tenant_ollama_config(db, tenant_id)
    res = await generate_with_cascade(
        prompt, system=REPORT_SYSTEM, tenant_ollama_config=ollama_cfg,
    )
    sections = _parse_json_strict(res.text) or {
        "executive_summary": res.text[:1500],
        "achievements": [],
        "next_activities": [],
        "top_risks": context["top_risks"],
        "budget_status": context["project"],
    }

    rep = Report(
        tenant_id=str(tenant_id), project_id=str(project_id),
        title=f"Reporte {p.folio} — {datetime.now(UTC).strftime('%Y-%m-%d')}",
        sections=sections, status="draft", recipients=body.recipients,
        generated_by_ai=True, created_by=cu.id,
    )
    db.add(rep)
    await db.flush()
    await write_audit(
        db, action="report.draft", module="ai", user_id=cu.id, tenant_id=tenant_id,
        entity_type="report", entity_id=str(rep.id), details={"model": res.model},
    )
    await db.commit()
    return {"report_id": str(rep.id), "sections": sections, "model": res.model}


class SendReportRequest(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=50)
    include_pdf: bool = False
    subject: str | None = None


@router.post("/reports/{report_id}/send")
async def send_report(
    report_id: UUID,
    body: SendReportRequest,
    cu: CurrentUser = Depends(require_permission("ai.generate", "create")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    r = (
        await db.execute(
            select(Report).where(Report.id == str(report_id), Report.tenant_id == str(tenant_id))
        )
    ).scalar_one_or_none()
    if r is None:
        raise not_found("Reporte")

    # Validar formato de emails
    for e in body.recipients:
        if "@" not in e or "." not in e.split("@", 1)[1]:
            raise validation_error(f"email inválido: {e}")

    # En dev/test no enviamos realmente. Producción: Resend via worker.
    r.status = "sent"
    r.sent_at = datetime.now(UTC)
    r.recipients = body.recipients
    await write_audit(
        db, action="report.send", module="ai", user_id=cu.id, tenant_id=tenant_id,
        entity_type="report", entity_id=str(r.id),
        details={"recipients": body.recipients},
    )
    await db.commit()
    return {"ok": True, "sent_at": r.sent_at.isoformat(), "recipients": body.recipients}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: UUID,
    cu: CurrentUser = Depends(require_permission("ai.generate", "create")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    j = (
        await db.execute(
            select(AIJob).where(AIJob.id == str(job_id), AIJob.tenant_id == str(tenant_id))
        )
    ).scalar_one_or_none()
    if j is None:
        raise not_found("Job")
    return {
        "id": str(j.id), "status": j.status, "model": j.model_used,
        "tokens_in": j.tokens_in, "tokens_out": j.tokens_out,
        "duration_ms": j.duration_ms, "output": j.output, "error": j.error,
    }
