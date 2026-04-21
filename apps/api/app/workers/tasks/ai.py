"""Tasks Celery para generación de IA (US-051).

El endpoint `POST /ai/minutes` y `POST /ai/projects/{id}/reports/draft`
crean un `AIJob` en estado `queued` y dispatchan estas tasks al
worker Celery. El worker (que sí tiene sidecar Tailscale — US-048)
ejecuta la cascada IA, persiste el resultado y marca el job como
`succeeded` o `failed`. La UI hace polling a `GET /ai/jobs/{id}`.

Las tasks son sincrónicas para Celery pero internamente corren una
coroutine con `run_async` — así podemos reusar el código async de
providers/repositorios tal cual.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import desc, select

from app.models.ai import AIJob, Report
from app.models.modules import MeetingMinute, Risk
from app.models.project import Project
from app.models.tenant import Tenant
from app.services.ai.prompts import MINUTE_SYSTEM, REPORT_SYSTEM
from app.services.ai.provider import chunk_text, generate_with_cascade
from app.services.audit import write_audit
from app.services.folio import next_folio
from app.workers.celery_app import celery_app
from app.workers.db import db_session, run_async

logger = logging.getLogger("pmoaas.ai.tasks")

_EMPTY_MINUTE = {
    "summary": "",
    "participants": [],
    "topics": [],
    "agreements": [],
    "decisions": [],
    "next_steps": [],
    "risks_blockers": [],
}


def _parse_json_strict(s: str) -> dict | None:
    try:
        return json.loads(s)
    except Exception:
        start = s.find("{")
        end = s.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(s[start : end + 1])
            except Exception:
                return None
        return None


async def _tenant_ollama_cfg(db, tenant_id: str) -> dict | None:
    t = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if t is None:
        return None
    cfg = dict(((t.settings or {}).get("ai") or {}).get("ollama") or {})
    if not cfg.get("base_url"):
        return None
    return cfg


async def _mark_running(db, job_id: str) -> AIJob | None:
    job = (
        await db.execute(select(AIJob).where(AIJob.id == job_id))
    ).scalar_one_or_none()
    if job is None:
        return None
    job.status = "running"
    await db.flush()
    await db.commit()
    return job


async def _mark_failed(db, job_id: str, error: str) -> None:
    job = (
        await db.execute(select(AIJob).where(AIJob.id == job_id))
    ).scalar_one_or_none()
    if job is None:
        return
    job.status = "failed"
    job.error = error[:2000]
    job.completed_at = datetime.now(UTC)
    await db.commit()


async def _run_minute(
    job_id: str,
    tenant_id: str,
    project_id: str,
    transcript: str,
    language: str | None,
    save_as_minute: bool,
    title: str,
    requested_by: str | None,
) -> None:
    async with db_session() as db:
        job = await _mark_running(db, job_id)
        if job is None:
            logger.warning("minute task: job %s not found", job_id)
            return

    started = datetime.now(UTC)
    try:
        async with db_session() as db:
            ollama_cfg = await _tenant_ollama_cfg(db, tenant_id)

        logger.info(
            "minute task start job=%s tenant=%s ollama_cfg=%s",
            job_id, tenant_id,
            {"base_url": ollama_cfg.get("base_url"), "model": ollama_cfg.get("model")}
            if ollama_cfg else None,
        )
        chunks = chunk_text(transcript)
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
                parsed = dict(_EMPTY_MINUTE)
                parsed["summary"] = res.text[:2000]
            collected.append(parsed)

        merged = {
            "summary": "\n\n".join([c.get("summary") or "" for c in collected]).strip(),
            "participants": sum((c.get("participants") or [] for c in collected), []),
            "topics": sum((c.get("topics") or [] for c in collected), []),
            "agreements": sum((c.get("agreements") or [] for c in collected), []),
            "decisions": sum((c.get("decisions") or [] for c in collected), []),
            "next_steps": sum((c.get("next_steps") or [] for c in collected), []),
            "risks_blockers": sum((c.get("risks_blockers") or [] for c in collected), []),
        }

        async with db_session() as db:
            job = (
                await db.execute(select(AIJob).where(AIJob.id == job_id))
            ).scalar_one()
            minute_id: str | None = None
            if save_as_minute:
                folio = await next_folio(db, tenant_id=tenant_id, prefix="MIN")
                mm = MeetingMinute(
                    tenant_id=tenant_id, project_id=project_id, folio=folio,
                    title=title, meeting_date=datetime.now(UTC),
                    participants=merged["participants"], topics=merged["topics"],
                    agreements=merged["agreements"], next_meeting_date=None,
                    attachments=[], generated_by_ai=True, status="final",
                    created_by=requested_by,
                )
                db.add(mm)
                await db.flush()
                minute_id = str(mm.id)
                merged["minute_id"] = minute_id

            job.status = "succeeded"
            job.output = merged
            job.model_used = model_used
            job.tokens_in = total_in
            job.tokens_out = total_out
            job.duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            job.completed_at = datetime.now(UTC)

            await write_audit(
                db, action="ai.minute.generate", module="ai",
                user_id=requested_by, tenant_id=tenant_id,
                entity_type="ai_job", entity_id=str(job.id),
                details={"model": model_used, "duration_ms": job.duration_ms,
                         "minute_id": minute_id, "language": language},
            )
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("minute task failed job=%s", job_id)
        async with db_session() as db:
            await _mark_failed(db, job_id, f"{type(exc).__name__}: {exc}")


async def _run_report(
    job_id: str,
    tenant_id: str,
    project_id: str,
    recipients: list[str],
    requested_by: str | None,
) -> None:
    async with db_session() as db:
        job = await _mark_running(db, job_id)
        if job is None:
            return

    started = datetime.now(UTC)
    try:
        async with db_session() as db:
            p = (
                await db.execute(
                    select(Project).where(
                        Project.id == project_id, Project.tenant_id == tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if p is None:
                raise RuntimeError("project_not_found")

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
            project_folio = p.folio
            ollama_cfg = await _tenant_ollama_cfg(db, tenant_id)

        prompt = json.dumps(context, ensure_ascii=False)
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

        async with db_session() as db:
            rep = Report(
                tenant_id=tenant_id, project_id=project_id,
                title=f"Reporte {project_folio} — {datetime.now(UTC).strftime('%Y-%m-%d')}",
                sections=sections, status="draft", recipients=recipients,
                generated_by_ai=True, created_by=requested_by,
            )
            db.add(rep)
            await db.flush()

            job = (
                await db.execute(select(AIJob).where(AIJob.id == job_id))
            ).scalar_one()
            job.status = "succeeded"
            job.output = {"report_id": str(rep.id), "sections": sections}
            job.model_used = res.model
            job.tokens_in = res.tokens_in
            job.tokens_out = res.tokens_out
            job.duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            job.completed_at = datetime.now(UTC)

            await write_audit(
                db, action="report.draft", module="ai",
                user_id=requested_by, tenant_id=tenant_id,
                entity_type="report", entity_id=str(rep.id),
                details={"model": res.model, "duration_ms": job.duration_ms},
            )
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("report task failed job=%s", job_id)
        async with db_session() as db:
            await _mark_failed(db, job_id, f"{type(exc).__name__}: {exc}")


@celery_app.task(name="ai.generate_minute", acks_late=True)
def generate_minute_task(
    job_id: str,
    tenant_id: str,
    project_id: str,
    transcript: str,
    language: str | None,
    save_as_minute: bool,
    title: str,
    requested_by: str | None,
) -> str:
    run_async(_run_minute(
        job_id, tenant_id, project_id, transcript, language,
        save_as_minute, title, requested_by,
    ))
    return job_id


@celery_app.task(name="ai.draft_report", acks_late=True)
def draft_report_task(
    job_id: str,
    tenant_id: str,
    project_id: str,
    recipients: list[str],
    requested_by: str | None,
) -> str:
    run_async(_run_report(job_id, tenant_id, project_id, recipients, requested_by))
    return job_id
