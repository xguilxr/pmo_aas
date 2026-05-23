from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import conflict, forbidden, not_found, validation_error
from app.db.session import get_db
from app.models.ai import AIJob, Report
from app.models.modules import MeetingMinute
from app.models.project import Project
from app.services.ai.platform_config import resolve_groq_config
from app.services.ai.prompts import HTML_TWEAK_SYSTEM
from app.services.ai.provider import generate_for_tenant
from app.services.ai.tenant_ai import load_tenant_ai
from app.services.audit import write_audit
from app.services.folio import next_folio
from app.workers.tasks.ai import draft_report_task, generate_minute_task

router = APIRouter(prefix="/ai", tags=["ai"])

MAX_TRANSCRIPT_BYTES = 5 * 1024 * 1024


# US-143 — 3 modos de generación de minuta:
# - transcript (default, retrocompatible): transcripción de reunión → IA estructura.
# - minute: minuta YA redactada → IA normaliza al modelo canónico preservando contenido.
# - manual: el form ya manda las 6 secciones llenas → persiste directo sin IA.
MinuteSourceType = Literal["transcript", "minute", "manual"]


class GenerateMinuteRequest(BaseModel):
    project_id: UUID
    source_type: MinuteSourceType = "transcript"
    transcript: str | None = Field(default=None, min_length=10)
    # Modo `manual`: estructura canónica de 6 secciones (header/participants/
    # summary/topics/raid/free_notes). Aquí se persiste tal cual sin IA.
    structured_data: dict[str, Any] | None = None
    language: str | None = None
    save_as_minute: bool = True
    title: str = "Minuta (IA)"

    @model_validator(mode="after")
    def _validate_source(self) -> "GenerateMinuteRequest":
        if self.source_type in ("transcript", "minute"):
            if not self.transcript:
                raise ValueError(
                    f"source_type={self.source_type} requiere `transcript` no vacío"
                )
        elif self.source_type == "manual":
            if not self.structured_data:
                raise ValueError(
                    "source_type=manual requiere `structured_data` con las 6 secciones"
                )
        return self


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


@router.post("/minutes", status_code=202)
async def generate_minute(
    body: GenerateMinuteRequest,
    response: Response,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-143: 3 modos. `transcript` y `minute` dispatch a Celery; `manual`
    persiste directo sin IA y devuelve 201.

    La UI envía `source_type` para indicar el flujo.
    """
    tenant_id = _tenant(cu)

    p = (
        await db.execute(
            select(Project).where(Project.id == str(body.project_id), Project.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")

    # ----- Modo MANUAL: sin IA, persiste directo (US-143).
    if body.source_type == "manual":
        return await _persist_manual_minute(
            db, tenant_id, body, cu
        )

    # ----- Modos transcript / minute: dispatch a Celery con IA.
    assert body.transcript is not None  # garantizado por validator
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

    # US-143: `minute_from_transcript` o `minute_from_minute` para
    # diferenciar en auditoría / dashboards. El worker enruta al prompt
    # correcto según el `source_type` que se le pasa.
    job_kind = "minute_from_transcript" if body.source_type == "transcript" else "minute_from_minute"
    job = AIJob(
        tenant_id=str(tenant_id), project_id=str(body.project_id),
        kind=job_kind, status="queued",
        input={"len": len(body.transcript), "lang": body.language,
               "save_as_minute": body.save_as_minute, "title": body.title,
               "source_type": body.source_type},
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
        source_type=body.source_type,
    )

    response.headers["Location"] = f"/api/v1/ai/jobs/{job_id}"
    return {"job_id": job_id, "status": "queued"}


async def _persist_manual_minute(
    db: AsyncSession,
    tenant_id: UUID,
    body: GenerateMinuteRequest,
    cu: CurrentUser,
) -> dict[str, Any]:
    """US-143 manual mode: construye `MeetingMinute` desde `structured_data`
    sin invocar IA. Devuelve `{minute_id, status: "saved"}`.

    `structured_data` espera la estructura canónica de 6 secciones; campos
    faltantes se rellenan con defaults vacíos. RAID viene del form (no se
    auto-sugiere porque el flujo manual no procesa texto).
    """
    sd = body.structured_data or {}
    header = sd.get("header") or {}
    participants_block = sd.get("participants") or {}
    if isinstance(participants_block, list):
        # tolerante: si llega una lista plana, asume attendees.
        attendees = participants_block
    else:
        attendees = participants_block.get("attendees") or []
    # Manual no auto-sugiere; el PM crea los items RAID por separado.
    raid_suggestions_empty = {
        "risks": [], "issues": [], "lessons": [], "changes": [],
    }
    meeting_date_raw = header.get("date") or sd.get("meeting_date")
    if meeting_date_raw:
        try:
            md = datetime.fromisoformat(str(meeting_date_raw).replace("Z", "+00:00"))
        except ValueError:
            md = datetime.now(UTC)
    else:
        md = datetime.now(UTC)
    folio = await next_folio(db, tenant_id=tenant_id, prefix="MIN")
    mm = MeetingMinute(
        tenant_id=str(tenant_id),
        project_id=str(body.project_id),
        folio=folio,
        title=body.title or header.get("title") or "Minuta",
        meeting_date=md,
        participants=attendees,
        topics=sd.get("topics") or [],
        agreements=sd.get("agreements") or sd.get("raid") or [],
        next_meeting_date=None,
        attachments=[],
        generated_by_ai=False,
        status="final",
        created_by=cu.id,
        # ENH-106: origin manual (form llenado por el PM).
        origin="manual",
        raid_suggestions=raid_suggestions_empty,
        description=sd.get("summary") or None,
    )
    db.add(mm)
    await db.flush()
    minute_id = str(mm.id)
    await write_audit(
        db,
        action="minute.create",
        module="minutes",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="meeting_minute",
        entity_id=minute_id,
        details={"source_type": "manual", "folio": folio},
    )
    await db.commit()
    return {"minute_id": minute_id, "status": "saved", "folio": folio}


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


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """BUG-055: marca un AIJob como cancelado para que el worker
    detecte el flag y omita la persistencia del minute/report final.
    Solo aplica a jobs en estado `queued` o `running` — los demás
    transicionan no son válidos.

    El worker verifica el estado antes de hacer commit; si es
    `cancelled`, se aborta sin crear el MeetingMinute (CA4 — sin
    minutas huérfanas).
    """
    tenant_id = _tenant(cu)
    j = (
        await db.execute(
            select(AIJob).where(
                AIJob.id == str(job_id), AIJob.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if j is None:
        raise not_found("Job")
    if j.status not in {"queued", "running"}:
        raise conflict(
            f"Job en estado `{j.status}` no se puede cancelar",
            code="STATE_TRANSITION",
        )
    j.status = "cancelled"
    j.completed_at = datetime.now(UTC)
    j.error = "Cancelado por el usuario"
    await write_audit(
        db, action="ai.job.cancel", module="ai",
        user_id=cu.id, tenant_id=tenant_id,
        entity_type="ai_job", entity_id=str(j.id),
    )
    await db.commit()
    return {"id": str(j.id), "status": j.status}


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


# ========== US-109 — tweaker IA del HTML del reporte ==========


class TweakHTMLBody(BaseModel):
    current_html: str = Field(min_length=20)
    instruction: str = Field(min_length=2, max_length=2000)


class TweakHTMLResult(BaseModel):
    html: str
    model: str | None = None


@router.post("/reports/tweak-html", response_model=TweakHTMLResult)
async def tweak_report_html(
    body: TweakHTMLBody,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-109 CA3-CA5: aplica una instrucción al HTML actual del reporte
    via LLM y devuelve el HTML modificado. Sin streaming (out-of-scope) y
    sin persistencia — el frontend mantiene el historial (CA6) y guarda
    explícitamente con ENH-085.

    Rate-limit / longitud: el HTML se trunca a ~400KB para mantener el
    prompt razonable; el caller es responsable de no enviar HTML inflado.
    """
    tenant_id = _tenant(cu)
    cfg = await load_tenant_ai(db, tenant_id)
    if cfg.mode == "disabled":
        raise conflict(
            "IA deshabilitada para este tenant",
            code="AI_DISABLED",
        )
    platform_groq = await resolve_groq_config(db) if cfg.mode == "platform" else None

    # Truncar input a 400KB para no inflar el prompt.
    current_html = body.current_html[:400_000]
    prompt = (
        f"INSTRUCCIÓN DEL USUARIO:\n{body.instruction}\n\n"
        f"HTML ACTUAL:\n{current_html}\n\n"
        "Devuelve SOLO el HTML modificado completo."
    )

    try:
        res = await generate_for_tenant(
            prompt,
            system=HTML_TWEAK_SYSTEM,
            tenant_ai_mode=cfg.mode,
            platform_groq_config=platform_groq,
            byo_config=cfg.byo,
            tenant_id=str(tenant_id),
        )
    except Exception as exc:
        raise validation_error(
            f"Falló el tweak IA: {type(exc).__name__}",
            code="AI_TWEAK_FAILED",
            fields={"detail": str(exc)[:500]},
        ) from exc

    html_out = res.text.strip()
    # Algunos modelos devuelven el HTML envuelto en ```html ... ```; lo limpiamos.
    if html_out.startswith("```"):
        html_out = html_out.split("\n", 1)[1] if "\n" in html_out else html_out
        if html_out.endswith("```"):
            html_out = html_out.rsplit("```", 1)[0]
        html_out = html_out.strip()
    # Si el modelo devolvió texto sin DOCTYPE, asume que ignoró las
    # reglas y devuelve el HTML original como fallback de seguridad.
    if "<html" not in html_out.lower():
        raise validation_error(
            "El modelo no devolvió HTML válido. Reformula la instrucción.",
            code="AI_TWEAK_INVALID_OUTPUT",
        )

    await write_audit(
        db, action="report.tweak_html", module="reports",
        user_id=cu.id, tenant_id=tenant_id,
        entity_type="report", entity_id="tweak",
        details={"instruction_chars": len(body.instruction), "model": res.model},
    )
    await db.commit()
    return TweakHTMLResult(html=html_out, model=res.model)
