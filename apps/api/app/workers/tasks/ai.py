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
from decimal import Decimal

from sqlalchemy import desc, select

from app.core.config import settings
from app.core.tenant_context import fijar_tenant_actual
from app.core.unidades import razon_a_pct_decimal, segundos_a_ms
from app.models.ai import AIJob, Report
from app.models.modules import MeetingMinute, Risk
from app.models.project import Project
from app.services.ai.platform_config import resolve_groq_config
from app.services.ai.prompt_builder import build_system_prompt
from app.services.ai.prompts import (
    MINUTE_NORMALIZE_SYSTEM,
    MINUTE_SYSTEM,
    REPORT_SYSTEM,
)
from app.services.ai.provider import (
    AIResult,
    chunk_text,
    generate_for_tenant,
)
from app.services.ai.tenant_ai import TenantAIConfig, load_tenant_ai
from app.services.ai.untrusted import envolver_no_confiable
from app.services.ai.validator import (
    dedupe_participants,
    merge_topics,
    validate_minute_payload,
)
from app.services.audit import ACTOR_IA, write_audit
from app.services.folio import next_folio
from app.workers.celery_app import celery_app
from app.workers.db import db_session, run_async

logger = logging.getLogger("pmoaas.ai.tasks")

# US-057: reintentos internos del worker al llamar al provider. El owner
# pidió 3 intentos para Groq sin fallback a otros proveedores — mismo
# umbral aplica al BYO para uniformidad.
_AI_CALL_MAX_RETRIES = 3
_AI_CALL_BACKOFF_SEC: tuple[float, ...] = (1.0, 3.0, 8.0)
# BUG-061: 429 (rate limit) necesita backoff más generoso que el genérico.
# El window típico de Groq es 60s. Si el provider devuelve `Retry-After` lo
# honramos, sino usamos esta tabla.
_AI_CALL_BACKOFF_429_SEC: tuple[float, ...] = (10.0, 25.0, 60.0)

def _empty_raid_suggestions() -> dict:
    """4 buckets canónicos A/R/D/I alineados con el modelo RAID."""
    return {"actions": [], "risks": [], "decisions": [], "issues": []}


def _empty_minute() -> dict:
    """Devuelve un dict virgen — fábrica, NO un singleton, para evitar
    que los `extend` en cascada contaminen llamadas posteriores."""
    return {
        "summary": "",
        "header": {},
        "participants": [],
        "topics": [],
        "free_notes": None,
        "raid": [],
        "raid_suggestions": _empty_raid_suggestions(),
    }


def _merge_raid_suggestions(buckets: list[dict]) -> dict:
    """Concatena buckets canónicos {actions, risks, decisions, issues}
    proveniente de chunks múltiples. Items inválidos (no-dict) se
    descartan silenciosamente."""
    out = _empty_raid_suggestions()
    for b in buckets:
        if not isinstance(b, dict):
            continue
        for k in out:
            for it in b.get(k) or []:
                if isinstance(it, dict):
                    out[k].append(it)
    return out


def _parse_json_strict(s: str) -> dict | None:
    # ENH-147 — usa el parser tolerante compartido (fence-strip, comas
    # colgantes, recorte entre llaves) en vez del json.loads frágil.
    from app.services.ai.json_parse import parse_json_lenient

    return parse_json_lenient(s)


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
            await fijar_tenant_actual(db, tenant_id)
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
    json_mode: bool = False,
) -> AIResult:
    """US-057: llama al provider del tenant con 3 reintentos. Sin
    fallback entre modos (disabled → caller debió chequear antes;
    platform falla → alerta superadmin + error; byo falla → error).

    Auditoría MCS 2026-08-03 (IA-03): el límite de ITERACIONES ya existía
    (`_AI_CALL_MAX_RETRIES`). Lo que faltaba era el límite de COSTE por
    ejecución. Un proyecto con cientos de minutas produce un contexto que
    crece sin techo, y con reintentos se multiplica por tres.

    El tope se aplica ANTES de llamar, porque después el gasto ya ocurrió.
    """
    presupuesto = settings.AI_MAX_PROMPT_CHARS
    if presupuesto and len(prompt) > presupuesto:
        logger.error(
            "ai_call_rechazada_por_coste tenant=%s job=%s chars=%d limite=%d",
            tenant_id, job_id, len(prompt), presupuesto,
        )
        raise RuntimeError(
            f"ai_prompt_demasiado_grande: {len(prompt)} caracteres supera el "
            f"límite de {presupuesto} por ejecución (AI_MAX_PROMPT_CHARS)"
        )

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
                json_mode=json_mode,
            )
        except Exception as exc:
            last_err = exc
            # BUG-061: rate limit (429) lo manejamos con backoff dedicado
            # honrando el header `Retry-After` cuando viene.
            is_429 = _is_rate_limit(exc)
            # BUG-083: un 4xx (≠429) es un error de la *request* (prompt
            # inválido, contexto excedido, modelo dado de baja), no algo
            # transitorio — reintentar 3 veces no ayuda y oculta la causa.
            # Cortamos de inmediato y propagamos la razón real.
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and 400 <= status < 500 and status != 429:
                logger.error(
                    "ai_call_client_error tenant=%s job=%s mode=%s status=%s body=%s",
                    tenant_id, job_id, tenant_cfg.mode, status,
                    _response_body(exc),
                )
                break
            retry_after = _retry_after_seconds(exc) if is_429 else None
            if retry_after is not None:
                sleep_sec = retry_after
            elif is_429:
                sleep_sec = _AI_CALL_BACKOFF_429_SEC[
                    min(attempt, len(_AI_CALL_BACKOFF_429_SEC) - 1)
                ]
            else:
                sleep_sec = _AI_CALL_BACKOFF_SEC[
                    min(attempt, len(_AI_CALL_BACKOFF_SEC) - 1)
                ]
            logger.warning(
                "ai_call_retry tenant=%s job=%s mode=%s attempt=%d/%d err=%s sleep=%.1fs%s",
                tenant_id, job_id, tenant_cfg.mode,
                attempt + 1, _AI_CALL_MAX_RETRIES,
                type(exc).__name__, sleep_sec,
                " (429)" if is_429 else "",
            )
            if attempt + 1 < _AI_CALL_MAX_RETRIES:
                import asyncio

                await asyncio.sleep(sleep_sec)
    # Agotados los reintentos. Alerta al superadmin si es modo `platform`.
    if tenant_cfg.mode == "platform":
        await _alert_superadmin_platform_failure(
            tenant_id, job_id, str(last_err)[:500]
        )
    if _is_rate_limit(last_err):
        # Mensaje user-facing que el frontend puede mostrar tal cual.
        raise RuntimeError(
            "AI_RATE_LIMITED: el proveedor (Groq) está saturado y no aceptó "
            "la petición tras 3 reintentos. Espera 1-2 minutos y vuelve a "
            "intentar, o cambia a un proveedor BYO."
        )
    body = _response_body(last_err)
    raise RuntimeError(
        f"ai_call_failed mode={tenant_cfg.mode} after {_AI_CALL_MAX_RETRIES}"
        f" retries: {last_err}" + (f" | body={body}" if body else "")
    )


def _response_body(exc: Exception | None) -> str:
    """Cuerpo (truncado) de la respuesta HTTP del provider, si lo hay.

    BUG-083: los 4xx de Groq traen la razón real en el body; sin esto el
    error de cara al usuario/superadmin sólo decía 'HTTPStatusError'."""
    resp = getattr(exc, "response", None)
    if resp is None:
        return ""
    try:
        return (resp.text or "")[:500]
    except Exception:
        return ""


def _is_rate_limit(exc: Exception | None) -> bool:
    if exc is None:
        return False
    # httpx.HTTPStatusError tiene .response.status_code; otros providers
    # podrían usar mensajes con "429" o "rate limit".
    resp = getattr(exc, "response", None)
    if resp is not None and getattr(resp, "status_code", None) == 429:
        return True
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg


def _retry_after_seconds(exc: Exception) -> float | None:
    resp = getattr(exc, "response", None)
    if resp is None:
        return None
    headers = getattr(resp, "headers", None)
    if headers is None:
        return None
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if not raw:
        return None
    try:
        # Cap a 90s para no bloquear el worker indefinidamente.
        return min(float(raw), 90.0)
    except (TypeError, ValueError):
        return None


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
    source_type: str = "transcript",
) -> None:
    # US-143: source_type=`minute` usa `MINUTE_NORMALIZE_SYSTEM` que
    # preserva contenido literal en lugar de re-sintetizarlo. Default
    # `transcript` para retrocompatibilidad.
    prompt_system_base = (
        MINUTE_NORMALIZE_SYSTEM if source_type == "minute" else MINUTE_SYSTEM
    )
    async with db_session() as db:
        await fijar_tenant_actual(db, tenant_id)
        job = await _mark_running(db, job_id)
        if job is None:
            logger.warning("minute task: job %s not found", job_id)
            return

    started = datetime.now(UTC)
    try:
        async with db_session() as db:
            await fijar_tenant_actual(db, tenant_id)
            tenant_cfg = await load_tenant_ai(db, tenant_id)
            platform_groq = await resolve_groq_config(db)
            # US-185: memoria de proyecto — bloque <CONTEXTO_DEL_PROYECTO>
            # (contexto curado + instrucciones + resumen acumulado) que se
            # antepone a cada chunk del transcript.
            from app.services.ai.project_context import load_context_block

            context_block = await load_context_block(db, tenant_id, project_id)

        if tenant_cfg.mode == "disabled":
            raise RuntimeError("ai_disabled_for_tenant")

        # ENH-189: system efectivo = base + instrucciones del tenant.
        # B2: `build_system_prompt` anexa además la regla de contenido no
        # confiable, que es la contraparte del bloque que se arma abajo.
        prompt_system = build_system_prompt(
            prompt_system_base, tenant_cfg.instructions_md
        )

        logger.info(
            "minute task start job=%s tenant=%s mode=%s byo_provider=%s",
            job_id, tenant_id, tenant_cfg.mode,
            (tenant_cfg.byo or {}).get("provider") if tenant_cfg.byo else None,
        )
        chunks = chunk_text(transcript)
        # Cada chunk pasa por el validator que produce el shape canónico
        # (gold standard EP019). Luego mergeamos chunks en el cascade
        # del worker. Los participantes y RAID se aplanan/normalizan
        # dentro del validator — el worker solo concatena.
        collected: list[dict] = []
        model_used = "unknown"
        total_in = 0
        total_out = 0
        validator_metrics: dict[str, int] = {
            "kept": 0, "dropped_lesson": 0, "dropped_change": 0,
            "dropped_unknown": 0, "dropped_malformed": 0,
        }
        parse_failed_chunks = 0
        for ch in chunks:
            # B2 (MCS IA-11, T-5): el chunk ES el archivo que subió el
            # usuario. Va envuelto y neutralizado ANTES de tocar el prompt.
            # La instrucción de reparación de abajo se concatena DESPUÉS del
            # cierre del bloque, y ese orden importa: es instrucción de la
            # plataforma y tiene que quedar fuera del dato.
            ch_envuelto = envolver_no_confiable(
                ch,
                origen=(
                    "minuta redactada subida por el usuario"
                    if source_type == "minute"
                    else "transcripción de reunión subida por el usuario"
                ),
            )
            # US-185: el contexto del proyecto acompaña a cada chunk (los
            # chunks se procesan de forma independiente).
            prompt_input = (
                f"{context_block}\n\n{ch_envuelto}" if context_block else ch_envuelto
            )
            # ENH-147 — json_mode fuerza salida estructurada por proveedor.
            res = await _call_ai_for_tenant(
                prompt_input,
                system=prompt_system,
                tenant_cfg=tenant_cfg,
                platform_groq_config=platform_groq,
                tenant_id=tenant_id,
                job_id=job_id,
                json_mode=True,
            )
            model_used = res.model
            total_in += res.tokens_in
            total_out += res.tokens_out
            parsed = _parse_json_strict(res.text)
            if parsed is None:
                # ENH-147 — reintento de reparación: re-pide SOLO JSON antes
                # de degradar a minuta vacía (antes se perdía todo el RAID
                # silenciosamente en cada fallo de parseo).
                repair = await _call_ai_for_tenant(
                    prompt_input + "\n\nTu respuesta anterior no fue JSON válido. "
                    "Devuelve EXCLUSIVAMENTE el objeto JSON pedido, sin texto "
                    "ni fences ni comentarios.",
                    system=prompt_system,
                    tenant_cfg=tenant_cfg,
                    platform_groq_config=platform_groq,
                    tenant_id=tenant_id,
                    job_id=job_id,
                    json_mode=True,
                )
                total_in += repair.tokens_in
                total_out += repair.tokens_out
                parsed = _parse_json_strict(repair.text)
            if parsed is None:
                parse_failed_chunks += 1
                normalized = _empty_minute()
                normalized["summary"] = res.text[:2000]
            else:
                normalized, m = validate_minute_payload(parsed)
                for k, v in m.items():
                    validator_metrics[k] = validator_metrics.get(k, 0) + v
            collected.append(normalized)
        if parse_failed_chunks:
            validator_metrics["parse_failed_chunks"] = parse_failed_chunks
            logger.warning(
                "minute parse failed for %d/%d chunks job=%s tenant=%s",
                parse_failed_chunks, len(chunks), job_id, tenant_id,
            )

        merged = {
            "header": collected[0].get("header") if collected else {},
            "summary": "\n\n".join([c.get("summary") or "" for c in collected]).strip(),
            # BUG-069: cada chunk dedupea internamente (flatten_participants),
            # pero el concat cross-chunk volvía a duplicar cuando un mismo
            # speaker aparecía en chunks distintos (overlap o transcripts
            # largos). Re-dedupeamos por nombre normalizado tras el merge.
            "participants": dedupe_participants(
                functools.reduce(
                    operator.iadd,
                    (c.get("participants_flat") or [] for c in collected),
                    [],
                )
            ),
            # BUG-070: el mismo tema puede ser extraído por varios chunks
            # cuando el transcript se divide (ej. "Alcance del Proyecto"
            # aparecía 3 veces). merge_topics fusiona por título
            # normalizado y combina bullets sin duplicar.
            "topics": merge_topics(
                functools.reduce(
                    operator.iadd,
                    (c.get("topics") or [] for c in collected),
                    [],
                )
            ),
            # ENH-095/US-040: `agreements` queda como sinónimo legacy de
            # `raid_suggestions.actions` para no romper exports/templates
            # que lo referencian. La verdad canónica vive en
            # `raid_suggestions`.
            "agreements": [],
            "free_notes": next(
                (c.get("free_notes") for c in collected if c.get("free_notes")),
                None,
            ),
            "raid_suggestions": _merge_raid_suggestions(
                [c.get("raid_suggestions") for c in collected]
            ),
        }
        # Para retrocompat con UI vieja que aún lee `participants` como
        # lista de speakers/attendees sin distinguir absentes.
        # `participants_flat` ya cumple — el merge anterior reusa ese campo.

        async with db_session() as db:
            await fijar_tenant_actual(db, tenant_id)
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
                # ENH-106 + US-143: origen depende del source_type.
                # `transcript_ai` (default) o `minute_ai` cuando la fuente
                # fue una minuta ya redactada normalizada por IA.
                minute_origin = (
                    "minute_ai" if source_type == "minute" else "transcript_ai"
                )
                # BUG-063: free_notes meta-persistido dentro de
                # raid_suggestions._meta para evitar migración.
                raid_with_meta = dict(merged["raid_suggestions"])
                if merged.get("free_notes"):
                    raid_with_meta["_meta"] = {"free_notes": merged["free_notes"]}
                mm = MeetingMinute(
                    tenant_id=tenant_id, project_id=project_id, folio=folio,
                    title=title, meeting_date=datetime.now(UTC),
                    participants=merged["participants"], topics=merged["topics"],
                    agreements=merged["agreements"], next_meeting_date=None,
                    attachments=[], generated_by_ai=True, status="final",
                    created_by=requested_by,
                    origin=minute_origin,
                    raid_suggestions=raid_with_meta,
                    description=merged.get("summary") or None,
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
            job.duration_ms = segundos_a_ms((datetime.now(UTC) - started).total_seconds())
            job.completed_at = datetime.now(UTC)

            # US-185: la minuta nueva alimenta la memoria del proyecto
            # (resumen acumulativo). Best-effort: nunca falla el job.
            if minute_id:
                try:
                    update_project_context_task.delay(tenant_id, project_id)
                except Exception:  # pragma: no cover
                    pass

            await write_audit(
                db, action="ai.minute.generate", module="ai",
                # IA-02: lo redacta el modelo. `user_id` es quien lo pidió, que
                # es justo a quien NO hay que atribuirle el texto.
                actor_type=ACTOR_IA,
                user_id=requested_by, tenant_id=tenant_id,
                entity_type="ai_job", entity_id=str(job.id),
                details={"model": model_used, "duration_ms": job.duration_ms,
                         "minute_id": minute_id, "language": language,
                         "provider": job.provider, "mode": tenant_cfg.mode,
                         "source_type": source_type},
            )
            await db.commit()
    except Exception as exc:
        logger.exception("minute task failed job=%s", job_id)
        async with db_session() as db:
            await fijar_tenant_actual(db, tenant_id)
            await _mark_failed(db, job_id, f"{type(exc).__name__}: {exc}")


async def _run_report(
    job_id: str,
    tenant_id: str,
    project_id: str,
    recipients: list[str],
    requested_by: str | None,
) -> None:
    async with db_session() as db:
        await fijar_tenant_actual(db, tenant_id)
        job = await _mark_running(db, job_id)
        if job is None:
            return

    started = datetime.now(UTC)
    try:
        async with db_session() as db:
            await fijar_tenant_actual(db, tenant_id)
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
            # Auditoría MCS 2026-08-03 — IA-05 y DAT-03.
            #
            # Antes esto pasaba `float(p.budget)` y le pedía al modelo un
            # `budget_status`. Dos problemas:
            #   1. Dinero en coma flotante (DAT-03), justo en el camino a un
            #      informe que alguien usa para decidir.
            #   2. El modelo tenía que derivar la desviación él mismo, y un
            #      modelo de lenguaje NO DEBE calcular cifras (IA-05).
            #
            # Ahora las cifras se calculan aquí, con Decimal, y viajan ya
            # hechas y como cadena. El modelo redacta; no computa.
            _plan = p.budget or Decimal(0)
            _real = p.actual_budget or Decimal(0)
            _desviacion = _real - _plan
            _consumido = (
                razon_a_pct_decimal(_real, _plan)
                if _plan
                else None
            )
            context = {
                "project": {
                    "name": p.name, "folio": p.folio, "phase": p.phase,
                    "progress": int(p.progress or 0),
                    "budget_plan": str(_plan),
                    "budget_actual": str(_real),
                    "budget_variance": str(_desviacion),
                    "budget_consumed_pct": (
                        str(_consumido) if _consumido is not None else None
                    ),
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

        # B2 (MCS IA-11): el JSON lleva `project.name`, y los títulos y
        # descripciones de los riesgos. Todo eso lo teclean usuarios. Que las
        # CIFRAS ya vengan calculadas (IA-05) no hace confiable al texto que
        # las acompaña.
        prompt = envolver_no_confiable(
            json.dumps(context, ensure_ascii=False),
            origen="datos del proyecto redactados por usuarios",
        )
        res = await _call_ai_for_tenant(
            prompt,
            system=build_system_prompt(REPORT_SYSTEM, None),
            tenant_cfg=tenant_cfg,
            platform_groq_config=platform_groq,
            tenant_id=tenant_id,
            job_id=job_id,
            json_mode=True,
        )
        sections = _parse_json_strict(res.text) or {
            "executive_summary": res.text[:1500],
            "achievements": [],
            "next_activities": [],
            "top_risks": context["top_risks"],
            "budget_status": context["project"],
        }

        async with db_session() as db:
            await fijar_tenant_actual(db, tenant_id)
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
            job.duration_ms = segundos_a_ms((datetime.now(UTC) - started).total_seconds())
            job.completed_at = datetime.now(UTC)

            await write_audit(
                db, action="report.draft", module="ai",
                # IA-02: el borrador lo escribe el modelo. Esta acción NO lleva
                # el prefijo `ai.`, y era la prueba de que el nombre no puede
                # ser el criterio.
                actor_type=ACTOR_IA,
                user_id=requested_by, tenant_id=tenant_id,
                entity_type="report", entity_id=str(rep.id),
                details={"model": res.model, "duration_ms": job.duration_ms,
                         "provider": job.provider, "mode": tenant_cfg.mode},
            )
            await db.commit()
    except Exception as exc:
        logger.exception("report task failed job=%s", job_id)
        async with db_session() as db:
            await fijar_tenant_actual(db, tenant_id)
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
    source_type: str = "transcript",
) -> str:
    run_async(_run_minute(
        job_id, tenant_id, project_id, transcript, language,
        save_as_minute, title, requested_by, source_type,
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


async def _run_context_summary(tenant_id: str, project_id: str) -> None:
    """US-185 — actualiza el resumen acumulativo de la memoria del proyecto
    con las minutas más recientes. Se dispara al guardar una minuta (IA o
    manual). Si la IA del tenant está deshabilitada, no hace nada."""
    from app.models.project_ai_context import ProjectAIContext
    from app.services.ai.prompts import PROJECT_MEMORY_SYSTEM

    async with db_session() as db:
        await fijar_tenant_actual(db, tenant_id)
        tenant_cfg = await load_tenant_ai(db, tenant_id)
        platform_groq = await resolve_groq_config(db)
        if tenant_cfg.mode == "disabled":
            return

        minutes = (
            await db.execute(
                select(MeetingMinute)
                .where(
                    MeetingMinute.tenant_id == tenant_id,
                    MeetingMinute.project_id == project_id,
                    MeetingMinute.deleted_at.is_(None),
                )
                .order_by(desc(MeetingMinute.meeting_date))
                .limit(5)
            )
        ).scalars().all()
        if not minutes:
            return
        ctx = (
            await db.execute(
                select(ProjectAIContext).where(
                    ProjectAIContext.tenant_id == tenant_id,
                    ProjectAIContext.project_id == project_id,
                )
            )
        ).scalar_one_or_none()
        payload = {
            "resumen_actual": (ctx.auto_summary_md if ctx else None) or "(vacío)",
            "minutas_recientes": [
                {
                    "titulo": m.title,
                    "fecha": m.meeting_date.date().isoformat() if m.meeting_date else None,
                    "resumen": (m.description or "")[:1500],
                    "temas": m.topics[:15] if isinstance(m.topics, list) else [],
                    "acuerdos": m.agreements[:15] if isinstance(m.agreements, list) else [],
                }
                for m in minutes
            ],
        }

    try:
        # B2 (MCS IA-11): la entrada son minutas enteras — títulos, temas y
        # acuerdos que subió el usuario. Y la salida se guarda en
        # `auto_summary_md`, que se antepone a cada generación futura del
        # proyecto: si algo se cuela aquí, se vuelve permanente.
        res = await _call_ai_for_tenant(
            envolver_no_confiable(
                json.dumps(payload, ensure_ascii=False),
                origen="minutas del proyecto subidas por usuarios",
            ),
            system=build_system_prompt(PROJECT_MEMORY_SYSTEM, None),
            tenant_cfg=tenant_cfg,
            platform_groq_config=platform_groq,
            tenant_id=tenant_id,
            job_id=f"ctx-summary:{project_id}",
            json_mode=False,
        )
    except Exception:
        logger.exception("context summary failed project=%s", project_id)
        return
    summary_md = (res.text or "").strip()
    if not summary_md:
        return

    async with db_session() as db:
        await fijar_tenant_actual(db, tenant_id)
        ctx = (
            await db.execute(
                select(ProjectAIContext).where(
                    ProjectAIContext.tenant_id == tenant_id,
                    ProjectAIContext.project_id == project_id,
                )
            )
        ).scalar_one_or_none()
        if ctx is None:
            ctx = ProjectAIContext(tenant_id=tenant_id, project_id=project_id)
            db.add(ctx)
        ctx.auto_summary_md = summary_md[:20000]
        ctx.auto_summary_updated_at = datetime.now(UTC)
        await db.commit()
        logger.info(
            "context summary updated project=%s chars=%s model=%s",
            project_id, len(summary_md), res.model,
        )


@celery_app.task(name="ai.update_project_context", acks_late=True)
def update_project_context_task(tenant_id: str, project_id: str) -> str:
    run_async(_run_context_summary(tenant_id, project_id))
    return project_id
