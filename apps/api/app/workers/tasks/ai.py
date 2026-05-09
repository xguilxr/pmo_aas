"""Tasks Celery para generación de IA (US-051, BUG-053).

El endpoint `POST /ai/minutes` y `POST /ai/projects/{id}/reports/draft`
crean un `AIJob` en estado `queued` y dispatchan estas tasks al
worker Celery. El worker enruta al provider del tenant (platform/byo),
persiste el resultado y marca el job como `succeeded` o `failed`. La
UI hace polling a `GET /ai/jobs/{id}`.

Las tasks son sincrónicas para Celery pero internamente corren una
coroutine con `run_async` — así podemos reusar el código async de
providers/repositorios tal cual.
"""
from __future__ import annotations

import functools
import json
import logging
import operator
from datetime import UTC, datetime

from sqlalchemy import desc, select

from app.models.ai import AIJob, Report
from app.models.modules import MeetingMinute, Risk
from app.models.project import Project
from app.services.ai.platform_config import resolve_groq_config
from app.services.ai.prompts import MINUTE_SYSTEM, REPORT_SYSTEM
from app.services.ai.provider import (
    AIResult,
    chunk_text,
    generate_for_tenant,
)
from app.services.ai.tenant_ai import TenantAIConfig, load_tenant_ai
from app.services.audit import write_audit
from app.services.folio import next_folio
from app.workers.celery_app import celery_app
from app.workers.db import db_session, run_async

logger = logging.getLogger("pmoaas.ai.tasks")

# US-057: reintentos internos del worker al llamar al provider. El owner
# pidió 3 intentos para Groq sin fallback a otros proveedores — mismo
# umbral aplica al BYO para uniformidad.
_AI_CALL_MAX_RETRIES = 3
_AI_CALL_BACKOFF_SEC: tuple[float, ...] = (1.0, 3.0, 8.0)

def _empty_raid() -> dict:
    return {"risks": [], "issues": [], "lessons": [], "changes": []}


def _empty_minute() -> dict:
    """Devuelve un dict virgen — fábrica, NO un singleton, para evitar
    que los `extend` en cascada contaminen llamadas posteriores."""
    return {
        "summary": "",
        "participants": [],
        "topics": [],
        "agreements": [],
        "decisions": [],
        "next_steps": [],
        "risks_blockers": [],
        "raid": _empty_raid(),
    }


def _normalize_raid_block(raw: object) -> dict:
    """ENH-084: normaliza el bloque `raid` a las 4 claves canónicas con
    arrays. Tolera modelos que devuelvan claves alternativas (`risk`,
    `lesson`, `change`, alias) o aplanen los items en un array suelto.
    Si no hay items de un tipo, queda en `[]` — no se inventa.
    """
    block: dict = {"risks": [], "issues": [], "lessons": [], "changes": []}
    if not isinstance(raw, dict):
        return block
    aliases = {
        "risks": ("risks", "risk", "riesgos", "riesgo"),
        "issues": ("issues", "issue", "incidents", "incidencias", "incidentes"),
        "lessons": (
            "lessons", "lesson", "lecciones", "lessons_learned",
        ),
        "changes": ("changes", "change", "cambios", "change_requests"),
    }
    for key, names in aliases.items():
        for n in names:
            v = raw.get(n)
            if isinstance(v, list):
                block[key].extend([x for x in v if isinstance(x, dict)])
                break
    return block


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


async def _alert_superadmin_platform_failure(
    tenant_id: str, job_id: str, error: str
) -> None:
    """US-057: notificar al superadmin si Groq (modo plataforma) cae tras
    los 3 reintentos. Usa el sistema de notificaciones + email de EP011.
    Falla silenciosamente si no hay superadmins configurados — no queremos
    que un bug en notifications tumbe al worker."""
    try:
        from app.models.user import User
        from app.services.notifications import PLATFORM_AI_ALERT, enqueue_notification

        async with db_session() as db:
            superadmins = (
                await db.execute(
                    select(User).where(
                        User.is_superadmin.is_(True),
                        User.is_active.is_(True),
                    )
                )
            ).scalars().all()
            for sa in superadmins:
                # El notif carga el tenant que falló como contexto —
                # el superadmin puede navegar a /superadmin/ai para ver
                # el panel con todos los tenants.
                await enqueue_notification(
                    db,
                    tenant_id=tenant_id,
                    user_id=str(sa.id),
                    type=PLATFORM_AI_ALERT,
                    title="Groq (IA plataforma) falló tras 3 reintentos",
                    body=(
                        f"Tenant {tenant_id[:8]}…, job {job_id[:8]}: "
                        f"{error[:400]}. Revisa GROQ_API_KEY y el rate "
                        "limit en /superadmin/ai."
                    ),
                    entity_type="ai_job",
                    entity_id=job_id,
                    link="/superadmin/ai",
                )
            await db.commit()
    except Exception as exc:
        logger.exception(
            "platform_ai_alert_failed tenant=%s job=%s: %s",
            tenant_id, job_id, exc,
        )


async def _call_ai_for_tenant(
    prompt: str,
    *,
    system: str | None,
    tenant_cfg: TenantAIConfig,
    platform_groq_config: dict | None,
    tenant_id: str,
    job_id: str,
) -> AIResult:
    """US-057: llama al provider del tenant con 3 reintentos. Sin
    fallback entre modos (disabled → caller debió chequear antes;
    platform falla → alerta superadmin + error; byo falla → error)."""
    last_err: Exception | None = None
    for attempt in range(_AI_CALL_MAX_RETRIES):
        try:
            return await generate_for_tenant(
                prompt,
                system=system,
                tenant_ai_mode=tenant_cfg.mode,
                platform_groq_config=platform_groq_config,
                byo_config=tenant_cfg.byo,
                tenant_id=tenant_id,
                job_id=job_id,
            )
        except Exception as exc:
            last_err = exc
            sleep_sec = _AI_CALL_BACKOFF_SEC[
                min(attempt, len(_AI_CALL_BACKOFF_SEC) - 1)
            ]
            logger.warning(
                "ai_call_retry tenant=%s job=%s mode=%s attempt=%d/%d err=%s",
                tenant_id, job_id, tenant_cfg.mode,
                attempt + 1, _AI_CALL_MAX_RETRIES,
                type(exc).__name__,
            )
            if attempt + 1 < _AI_CALL_MAX_RETRIES:
                import asyncio

                await asyncio.sleep(sleep_sec)
    # Agotados los reintentos. Alerta al superadmin si es modo `platform`.
    if tenant_cfg.mode == "platform":
        await _alert_superadmin_platform_failure(
            tenant_id, job_id, str(last_err)[:500]
        )
    raise RuntimeError(
        f"ai_call_failed mode={tenant_cfg.mode} after {_AI_CALL_MAX_RETRIES}"
        f" retries: {last_err}"
    )


def _provider_from_model(model_str: str, tenant_cfg: TenantAIConfig) -> str:
    """Extrae el nombre de provider desde AIResult.model (formato `provider:model`).

    Si no viene con prefijo (disabled stub), usa el modo del tenant para
    rellenar. Útil para popular `ai_jobs.provider` en el dashboard."""
    if model_str and ":" in model_str:
        return model_str.split(":", 1)[0]
    if tenant_cfg.mode == "platform":
        return "groq"
    if tenant_cfg.mode == "byo" and tenant_cfg.byo:
        return str(tenant_cfg.byo.get("provider") or "byo")
    return "disabled"


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
            tenant_cfg = await load_tenant_ai(db, tenant_id)
            platform_groq = await resolve_groq_config(db)

        if tenant_cfg.mode == "disabled":
            raise RuntimeError("ai_disabled_for_tenant")

        logger.info(
            "minute task start job=%s tenant=%s mode=%s byo_provider=%s",
            job_id, tenant_id, tenant_cfg.mode,
            (tenant_cfg.byo or {}).get("provider") if tenant_cfg.byo else None,
        )
        chunks = chunk_text(transcript)
        collected: list[dict] = []
        model_used = "unknown"
        total_in = 0
        total_out = 0
        for ch in chunks:
            res = await _call_ai_for_tenant(
                ch,
                system=MINUTE_SYSTEM,
                tenant_cfg=tenant_cfg,
                platform_groq_config=platform_groq,
                tenant_id=tenant_id,
                job_id=job_id,
            )
            model_used = res.model
            total_in += res.tokens_in
            total_out += res.tokens_out
            parsed = _parse_json_strict(res.text)
            if parsed is None:
                parsed = _empty_minute()
                parsed["summary"] = res.text[:2000]
            collected.append(parsed)

        # ENH-084: bloque `raid` normalizado y mergeado en cascada (4
        # tipos canónicos: risks/issues/lessons/changes). Si el modelo
        # no devuelve la sección, queda en arrays vacíos — sin inventar.
        merged_raid: dict = {"risks": [], "issues": [], "lessons": [], "changes": []}
        for c in collected:
            block = _normalize_raid_block(c.get("raid"))
            for k in merged_raid:
                merged_raid[k].extend(block[k])

        merged = {
            "summary": "\n\n".join([c.get("summary") or "" for c in collected]).strip(),
            "participants": functools.reduce(operator.iadd, (c.get("participants") or [] for c in collected), []),
            "topics": functools.reduce(operator.iadd, (c.get("topics") or [] for c in collected), []),
            "agreements": functools.reduce(operator.iadd, (c.get("agreements") or [] for c in collected), []),
            "decisions": functools.reduce(operator.iadd, (c.get("decisions") or [] for c in collected), []),
            "next_steps": functools.reduce(operator.iadd, (c.get("next_steps") or [] for c in collected), []),
            "risks_blockers": functools.reduce(operator.iadd, (c.get("risks_blockers") or [] for c in collected), []),
            "raid": merged_raid,
        }

        async with db_session() as db:
            job = (
                await db.execute(select(AIJob).where(AIJob.id == job_id))
            ).scalar_one()
            # BUG-055 CA4: si el usuario canceló mid-stream, no
            # persistimos la minuta — evita orphans en DB. La fila del
            # job queda con status=cancelled (set por el endpoint).
            if job.status == "cancelled":
                logger.info("minute task cancelled before persist job=%s", job_id)
                return
            minute_id: str | None = None
            if save_as_minute:
                folio = await next_folio(db, tenant_id=tenant_id, prefix="MIN")
                # US-108: cada sugerencia entra como `pending` con
                # ticket_id null hasta que el PM la apruebe.
                raid_persisted: dict = {"risks": [], "issues": [], "lessons": [], "changes": []}
                for kind in raid_persisted:
                    for it in merged["raid"].get(kind, []):
                        if not isinstance(it, dict):
                            continue
                        raid_persisted[kind].append({
                            "short_desc": str(it.get("short_desc") or "").strip(),
                            "suggested_owner_name": it.get("suggested_owner_name") or None,
                            "suggested_priority": it.get("suggested_priority"),
                            "raw_quote": it.get("raw_quote") or None,
                            "status": "pending",
                            "ticket_id": None,
                            "ticket_type": None,
                        })
                mm = MeetingMinute(
                    tenant_id=tenant_id, project_id=project_id, folio=folio,
                    title=title, meeting_date=datetime.now(UTC),
                    participants=merged["participants"], topics=merged["topics"],
                    agreements=merged["agreements"], next_meeting_date=None,
                    attachments=[], generated_by_ai=True, status="final",
                    created_by=requested_by,
                    raid_suggestions=raid_persisted,
                )
                db.add(mm)
                await db.flush()
                minute_id = str(mm.id)
                merged["minute_id"] = minute_id

            job.status = "succeeded"
            job.output = merged
            job.model_used = model_used
            job.provider = _provider_from_model(model_used, tenant_cfg)
            job.tokens_in = total_in
            job.tokens_out = total_out
            job.duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            job.completed_at = datetime.now(UTC)

            await write_audit(
                db, action="ai.minute.generate", module="ai",
                user_id=requested_by, tenant_id=tenant_id,
                entity_type="ai_job", entity_id=str(job.id),
                details={"model": model_used, "duration_ms": job.duration_ms,
                         "minute_id": minute_id, "language": language,
                         "provider": job.provider, "mode": tenant_cfg.mode},
            )
            await db.commit()
    except Exception as exc:
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
            tenant_cfg = await load_tenant_ai(db, tenant_id)
            platform_groq = await resolve_groq_config(db)

        # US-057: reports sólo habilitados en modo `byo`. El endpoint ya
        # gateó disabled y platform; defensivo aquí por si re-encola.
        if tenant_cfg.mode == "disabled":
            raise RuntimeError("ai_disabled_for_tenant")
        if tenant_cfg.mode == "platform":
            raise RuntimeError("platform_mode_reports_out_of_scope")

        prompt = json.dumps(context, ensure_ascii=False)
        res = await _call_ai_for_tenant(
            prompt,
            system=REPORT_SYSTEM,
            tenant_cfg=tenant_cfg,
            platform_groq_config=platform_groq,
            tenant_id=tenant_id,
            job_id=job_id,
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
            job.provider = _provider_from_model(res.model, tenant_cfg)
            job.tokens_in = res.tokens_in
            job.tokens_out = res.tokens_out
            job.duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            job.completed_at = datetime.now(UTC)

            await write_audit(
                db, action="report.draft", module="ai",
                user_id=requested_by, tenant_id=tenant_id,
                entity_type="report", entity_id=str(rep.id),
                details={"model": res.model, "duration_ms": job.duration_ms,
                         "provider": job.provider, "mode": tenant_cfg.mode},
            )
            await db.commit()
    except Exception as exc:
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
