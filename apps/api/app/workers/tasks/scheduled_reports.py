"""Celery tasks para ScheduledReport (US-056, EP014 + EP011).

- `dispatch_due_scheduled_reports`: beat-triggered. Busca filas con
  `enabled=true` y `next_run_at <= now`, y encola una task por cada una.
- `send_scheduled_report`: genera el PDF (Avance o Seguimiento), lo
  adjunta en un email vía Resend, persiste un `reports` row (snapshot)
  y actualiza `last_run_at` + `next_run_at`.

Resend retry policy: mismo patrón que `notifications.send_email` —
`max_retries=3` con countdown de 60s.
"""
from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.models.ai import Report
from app.models.audit import AuditLog
from app.models.organization import Organization
from app.models.project import Project
from app.models.scheduled_report import ScheduledReport
from app.models.tenant import Tenant
from app.services.email import build_email_html, send_email_via_resend
from app.services.operational_reports import (
    build_avance_context,
    build_seguimiento_context,
)
from app.services.pdf_renderer import render_pdf
from app.services.scheduled_reports import compute_next_run
from app.workers.celery_app import celery_app
from app.workers.db import db_session, run_async

log = logging.getLogger(__name__)


@celery_app.task(name="scheduled_reports.dispatch_due", bind=True, max_retries=1)
def dispatch_due_scheduled_reports(self) -> dict:
    """Beat trigger: encola envíos pendientes."""
    return run_async(_dispatch_due())


async def _dispatch_due() -> dict:
    now = datetime.now(UTC)
    async with db_session() as db:
        rows = (
            await db.execute(
                select(ScheduledReport).where(
                    ScheduledReport.enabled.is_(True),
                    ScheduledReport.next_run_at.is_not(None),
                    ScheduledReport.next_run_at <= now,
                )
            )
        ).scalars().all()
    dispatched = 0
    for r in rows:
        send_scheduled_report.delay(str(r.id))
        dispatched += 1
    return {"dispatched": dispatched}


@celery_app.task(name="scheduled_reports.send", bind=True, max_retries=3)
def send_scheduled_report(self, scheduled_id: str) -> dict:
    try:
        return run_async(_send(scheduled_id))
    except Exception as exc:  # reintento con backoff estándar
        log.exception(
            "Scheduled report send failed for id=%s: %s", scheduled_id, exc
        )
        raise self.retry(exc=exc, countdown=60) from exc


async def _send(scheduled_id: str) -> dict:
    async with db_session() as db:
        sched = (
            await db.execute(
                select(ScheduledReport).where(ScheduledReport.id == scheduled_id)
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

        cut_off = datetime.now(UTC).date()
        if sched.report_type == "avance":
            context = await build_avance_context(
                db, tenant_id, project_id, cut_off
            )
            template = "reports/avance.html"
            titulo = "Reporte de Avance"
            generator = "avance"
        elif sched.report_type == "seguimiento":
            context = await build_seguimiento_context(
                db, tenant_id, project_id, cut_off, window_days=14
            )
            template = "reports/seguimiento.html"
            titulo = "Reporte de Seguimiento"
            generator = "seguimiento"
        else:
            sched.enabled = False
            sched.last_error = f"Tipo no soportado: {sched.report_type}"
            sched.next_run_at = None
            await db.commit()
            return {"skipped": "bad_type"}

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
        context["tenant_name"] = tenant_name

        pdf_bytes = render_pdf(template, context)
        filename = (
            f"{titulo.replace(' ', '_')}_{project.folio}_"
            f"{cut_off.isoformat()}.pdf"
        )

        rep = Report(
            tenant_id=str(tenant_id),
            project_id=str(project.id),
            title=f"{titulo} — {project.folio} — {cut_off.isoformat()}",
            period=None,
            generator=generator,
            cut_off_date=cut_off,
            sections=context,
            recipients=list(sched.recipients),
            status="sent",
            sent_at=datetime.now(UTC),
            generated_by_ai=False,
            created_by=None,
        )
        db.add(rep)
        await db.flush()

        subject = f"{titulo} — {project.name} — {cut_off.isoformat()}"
        body_text = (
            f"Adjunto el {titulo} automático del proyecto "
            f"{project.name} con fecha de corte {cut_off.isoformat()}."
        )
        html = build_email_html(
            title=subject,
            body=body_text,
            link=None,
            tenant_name=tenant_name,
            tenant_logo_url=org.logo_url if org else None,
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
        attachments = [{"filename": filename, "content": pdf_b64}]

        resp = await send_email_via_resend(
            to=list(sched.recipients),
            subject=subject,
            html=html,
            attachments=attachments,
        )

        now = datetime.now(UTC)
        sched.last_run_at = now
        # ENH-046: para cadence="once" no hay próxima ejecución; el
        # schedule queda deshabilitado tras correr.
        if sched.cadence == "once":
            sched.next_run_at = None
            sched.enabled = False
        else:
            sched.next_run_at = compute_next_run(
                sched.cadence,
                from_dt=now,
                day_of_week=sched.day_of_week,
                hour_of_day=sched.hour_of_day,
                run_at=sched.run_at,
            )
        sched.last_error = None if resp is not None else "Resend no configurado"

        db.add(
            AuditLog(
                action="scheduled_report.sent",
                module="reports",
                user_id=None,
                tenant_id=str(tenant_id),
                entity_type="scheduled_report",
                entity_id=str(sched.id),
                details={
                    "report_id": str(rep.id),
                    "report_type": sched.report_type,
                    "recipients_count": len(sched.recipients),
                    "provider_id": (resp or {}).get("id") if resp else None,
                },
            )
        )

        await db.commit()
        return {
            "sent": resp is not None,
            "report_id": str(rep.id),
            "provider_id": (resp or {}).get("id") if resp else None,
        }
