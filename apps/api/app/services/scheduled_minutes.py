"""Service helpers para ScheduledMinute (ENH-107, EP014).

Símil de `app.services.scheduled_reports` — reusa `compute_next_run`
para el cómputo de cadencia. Agrega helpers específicos para minutas:

- ``should_send_now(sched, now)``: True si la programación está
  habilitada y ``next_run_at`` vence al ``now`` dado.
- ``select_latest_minute(db, project_id, period_start, period_end)``:
  devuelve la última ``MeetingMinute`` del proyecto cuya ``meeting_date``
  cae en el periodo ``[period_start, period_end]`` (None si no hay).
- ``send_minute_email(...)``: renderiza PDF + adjunta + envía. Si no
  hay minuta en el periodo, envía un fallback informativo.
"""
from __future__ import annotations

import base64
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modules import MeetingMinute
from app.models.project import Project
from app.models.scheduled_minute import ScheduledMinute
from app.services.email import build_email_html, send_email_via_resend
from app.services.minutes_formatter import build_view, to_pdf

# Reusamos cadencias y compute_next_run de scheduled_reports para
# garantizar paridad de semántica.
from app.services.scheduled_reports import (  # noqa: F401
    CADENCES,
    Cadence,
    compute_next_run,
)


def should_send_now(sched: ScheduledMinute, now: datetime) -> bool:
    """True si la programación debe ejecutarse en ``now``."""
    if not sched.enabled:
        return False
    if sched.next_run_at is None:
        return False
    return sched.next_run_at <= now


async def select_latest_minute(
    db: AsyncSession,
    project_id: UUID | str,
    period_start: datetime,
    period_end: datetime,
) -> MeetingMinute | None:
    """Devuelve la última minuta del proyecto cuyo ``meeting_date`` cae
    en el rango ``[period_start, period_end]``. None si no hay.
    """
    rows = (
        await db.execute(
            select(MeetingMinute)
            .where(
                MeetingMinute.project_id == str(project_id),
                MeetingMinute.deleted_at.is_(None),
                MeetingMinute.meeting_date >= period_start,
                MeetingMinute.meeting_date <= period_end,
            )
            .order_by(MeetingMinute.meeting_date.desc())
            .limit(1)
        )
    ).scalars().all()
    return rows[0] if rows else None


async def send_minute_email(
    *,
    recipients: list[str],
    minute: MeetingMinute | None,
    project: Project,
    tenant_name: str | None,
    tenant_logo_url: str | None,
    period_start: datetime,
    period_end: datetime,
) -> dict[str, Any] | None:
    """Envía la minuta vía Resend; si ``minute`` es None, envía un email
    fallback ("Sin minuta registrada en este periodo").
    """
    period_str = (
        f"{period_start.date().isoformat()} → {period_end.date().isoformat()}"
    )
    if minute is None:
        subject = f"Minuta — {project.name} — {period_str}"
        body_text = (
            "Sin minuta registrada en este periodo. "
            f"Proyecto: {project.name} ({project.folio}). "
            f"Periodo evaluado: {period_str}."
        )
        html = build_email_html(
            title=subject,
            body=body_text,
            link=None,
            tenant_name=tenant_name,
            tenant_logo_url=tenant_logo_url,
        )
        return await send_email_via_resend(
            to=list(recipients),
            subject=subject,
            html=html,
            attachments=None,
        )

    view = build_view(minute, project)
    pdf_bytes = to_pdf(view, tenant_name=tenant_name)
    filename = (
        f"Minuta_{project.folio}_{minute.meeting_date.date().isoformat()}.pdf"
    )
    subject = (
        f"Minuta — {project.name} — {minute.meeting_date.date().isoformat()}"
    )
    body_text = (
        f"Adjunto la última minuta del proyecto {project.name} "
        f"(periodo {period_str})."
    )
    html = build_email_html(
        title=subject,
        body=body_text,
        link=None,
        tenant_name=tenant_name,
        tenant_logo_url=tenant_logo_url,
    )
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    attachments = [{"filename": filename, "content": pdf_b64}]
    return await send_email_via_resend(
        to=list(recipients),
        subject=subject,
        html=html,
        attachments=attachments,
    )
