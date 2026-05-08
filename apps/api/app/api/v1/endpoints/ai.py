from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import conflict, forbidden, not_found, validation_error
from app.db.session import get_db
from app.models.ai import AIJob, Report
from app.models.project import Project
from app.services.ai.tenant_ai import load_tenant_ai
from app.services.audit import write_audit
from app.workers.tasks.ai import draft_report_task, generate_minute_task

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


@router.post("/minutes", status_code=202)
async def generate_minute(
    body: GenerateMinuteRequest,
    response: Response,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Dispatch a Celery. Devuelve 202 + job_id; la UI hace polling a
    `GET /ai/jobs/{id}` hasta que termine. El worker enruta al
    provider del tenant (platform Groq / BYO cloud).
    """
    tenant_id = _tenant(cu)
    if len(body.transcript.encode("utf-8")) > MAX_TRANSCRIPT_BYTES:
        from fastapi import HTTPException

        raise HTTPException(status_code=413, detail={"code": "PAYLOAD_TOO_LARGE"})

    # US-057: gate modo IA del tenant. `disabled` → 409 antes de crear job.
    cfg = await load_tenant_ai(db, tenant_id)
    if cfg.mode == "disabled":
        raise conflict(
            "La IA está deshabilitada para este tenant. "
            "Habilítala en /admin/ai (modo plataforma o BYO).",
            code="AI_DISABLED",
        )

    p = (
        await db.execute(
            select(Project).where(Project.id == str(body.project_id), Project.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")

    job = AIJob(
        tenant_id=str(tenant_id), project_id=str(body.project_id),
        kind="minute_from_transcript", status="queued",
        input={"len": len(body.transcript), "lang": body.language,
               "save_as_minute": body.save_as_minute, "title": body.title},
        requested_by=cu.id,
    )
    db.add(job)
    await db.flush()
    job_id = str(job.id)
    await db.commit()

    generate_minute_task.delay(
        job_id=job_id,
        tenant_id=str(tenant_id),
        project_id=str(body.project_id),
        transcript=body.transcript,
        language=body.language,
        save_as_minute=body.save_as_minute,
        title=body.title,
        requested_by=str(cu.id) if cu.id else None,
    )

    response.headers["Location"] = f"/api/v1/ai/jobs/{job_id}"
    return {"job_id": job_id, "status": "queued"}


class ReportDraftRequest(BaseModel):
    recipients: list[str] = []


@router.post("/projects/{project_id}/reports/draft", status_code=202)
async def draft_report(
    project_id: UUID,
    body: ReportDraftRequest,
    response: Response,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-051: dispatch a Celery (idéntico pattern que `generate_minute`)."""
    tenant_id = _tenant(cu)

    # US-057: draft report IA sólo disponible en modo `byo`. En modo
    # `platform` Groq está limitado a minutas (scope del owner). En
    # modo `disabled` → 409.
    cfg = await load_tenant_ai(db, tenant_id)
    if cfg.mode == "disabled":
        raise conflict(
            "La IA está deshabilitada para este tenant.",
            code="AI_DISABLED",
        )
    if cfg.mode == "platform":
        raise conflict(
            "El modo 'plataforma' (Groq) está limitado a minutas. "
            "Para generar reportes con IA, conecta tu propio proveedor en /admin/ai.",
            code="AI_PLATFORM_SCOPE_LIMITED",
        )

    p = (
        await db.execute(
            select(Project).where(Project.id == str(project_id), Project.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")

    job = AIJob(
        tenant_id=str(tenant_id), project_id=str(project_id),
        kind="progress_report", status="queued",
        input={"recipients": body.recipients},
        requested_by=cu.id,
    )
    db.add(job)
    await db.flush()
    job_id = str(job.id)
    await db.commit()

    draft_report_task.delay(
        job_id=job_id,
        tenant_id=str(tenant_id),
        project_id=str(project_id),
        recipients=body.recipients,
        requested_by=str(cu.id) if cu.id else None,
    )

    response.headers["Location"] = f"/api/v1/ai/jobs/{job_id}"
    return {"job_id": job_id, "status": "queued"}


class SendReportRequest(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=50)
    include_pdf: bool = False
    subject: str | None = None


@router.post("/reports/{report_id}/send")
async def send_report(
    report_id: UUID,
    body: SendReportRequest,
    cu: CurrentUser = Depends(require_authenticated()),
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
    cu: CurrentUser = Depends(require_authenticated()),
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
