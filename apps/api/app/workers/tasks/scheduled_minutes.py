"""Celery tasks para ScheduledMinute (ENH-107, EP014).

Símil de `scheduled_reports`:

- ``dispatch_due_scheduled_minutes``: beat-triggered. Busca filas con
  ``enabled=true`` y ``next_run_at <= now``; encola una task por cada.
- ``send_scheduled_minute``: selecciona la última minuta del proyecto
  dentro del periodo de la cadencia, renderiza PDF, envía vía Resend y
  actualiza ``last_run_at`` + ``next_run_at``. Si no hay minuta en el
  periodo, envía un fallback "Sin minuta registrada en este periodo".

Retry policy: mismo patrón que `scheduled_reports` — ``max_retries=3``
con countdown de 60s.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.organization import Organization
from app.models.project import Project
from app.models.scheduled_minute import ScheduledMinute
from app.models.tenant import Tenant
from app.services.scheduled_minutes import (
    select_latest_minute,
    send_minute_email,
)
from app.services.scheduled_reports import compute_next_run
from app.workers.celery_app import celery_app
from app.workers.db import db_session, run_async

log = logging.getLogger(__name__)


# Ventana hacia atrás según cadencia: cuánto buscamos hacia atrás para
# encontrar "la última minuta del periodo". Para ``once`` usamos 30
# días como heurística (one-shot suele querer "la más reciente reciente").
_CADENCE_WINDOW_DAYS: dict[str, int] = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "once": 30,
}


def _period_for(cadence: str, now: datetime) -> tuple[datetime, datetime]:
    days = _CADENCE_WINDOW_DAYS.get(cadence, 7)
    return (now - timedelta(days=days), now)


@celery_app.task(name="scheduled_minutes.dispatch_due", bind=True, max_retries=1)
def dispatch_due_scheduled_minutes(self) -> dict:
    """Beat trigger: encola envíos pendientes."""
    return run_async(_dispatch_due())


async def _dispatch_due() -> dict:
    now = datetime.now(UTC)
    async with db_session() as db:
        rows = (
            await db.execute(
                select(ScheduledMinute).where(
                    ScheduledMinute.enabled.is_(True),
                    ScheduledMinute.next_run_at.is_not(None),
                    ScheduledMinute.next_run_at <= now,
                )
            )
        ).scalars().all()
    dispatched = 0
    for r in rows:
        send_scheduled_minute.delay(str(r.id))
        dispatched += 1
    return {"dispatched": dispatched}


@celery_app.task(name="scheduled_minutes.send", bind=True, max_retries=3)
def send_scheduled_minute(self, scheduled_id: str) -> dict:
    try:
        return run_async(_send(scheduled_id))
    except Exception as exc:
        log.exception(
            "Scheduled minute send failed for id=%s: %s", scheduled_id, exc
        )
        raise self.retry(exc=exc, countdown=60) from exc


async def _send(scheduled_id: str) -> dict:
    async with db_session() as db:
        sched = (
            await db.execute(
                select(ScheduledMinute).where(ScheduledMinute.id == scheduled_id)
            )
        ).scalar_one_or_none()
        if sched is None:
            return {"skipped": "not_found"}
        if not sched.enabled:
            return {"skipped": "disabled"}
        if not sched.recipients:
            sched.last_error = "Sin destinatarios"
            await db.commit()
            return {"skipped": "no_recipients"}

        tenant_id = UUID(str(sched.tenant_id))
        project_id = UUID(str(sched.project_id))
        project = (
            await db.execute(
                select(Project).where(
                    Project.id == str(project_id),
                    Project.tenant_id == str(tenant_id),
                )
            )
        ).scalar_one_or_none()
        if project is None:
            sched.enabled = False
            sched.last_error = "Proyecto no existe o fue eliminado"
            sched.next_run_at = None
            await db.commit()
            return {"skipped": "project_missing"}

        now = datetime.now(UTC)
        period_start, period_end = _period_for(sched.cadence, now)
        minute = await select_latest_minute(
            db, project_id, period_start, period_end
        )

        tenant = (
            await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
        ).scalar_one_or_none()
        org = (
            await db.execute(
                select(Organization)
                .where(
                    Organization.tenant_id == str(tenant_id),
                    Organization.is_active.is_(True),
                )
                .order_by(Organization.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        tenant_name = (org.name if org else None) or (
            tenant.name if tenant else None
        )

        resp = await send_minute_email(
            recipients=list(sched.recipients),
            minute=minute,
            project=project,
            tenant_name=tenant_name,
            tenant_logo_url=org.logo_url if org else None,
            period_start=period_start,
            period_end=period_end,
        )

        sched.last_run_at = now
        # cadence=once → no hay próxima ejecución, queda deshabilitada.
        if sched.cadence == "once":
            sched.next_run_at = None
            sched.enabled = False
        else:
            sched.next_run_at = compute_next_run(
                sched.cadence,
                from_dt=now,
                day_of_week=sched.day_of_week,
                hour_of_day=sched.hour_of_day,
                day_of_month=sched.day_of_month,
                run_at=sched.run_at,
            )
        sched.last_error = None if resp is not None else "Resend no configurado"

        db.add(
            AuditLog(
                action="scheduled_minute.sent",
                module="minutes",
                user_id=None,
                tenant_id=str(tenant_id),
                entity_type="scheduled_minute",
                entity_id=str(sched.id),
                details={
                    "minute_id": str(minute.id) if minute else None,
                    "fallback": minute is None,
                    "recipients_count": len(sched.recipients),
                    "provider_id": (resp or {}).get("id") if resp else None,
                },
            )
        )

        await db.commit()
        return {
            "sent": resp is not None,
            "minute_id": str(minute.id) if minute else None,
            "fallback": minute is None,
            "provider_id": (resp or {}).get("id") if resp else None,
        }
