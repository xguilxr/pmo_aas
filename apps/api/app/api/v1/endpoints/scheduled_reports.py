"""Scheduled Reports — CRUD de programaciones automáticas (US-056, EP014+EP011).

Permite al PM/admin programar el envío recurrente de un reporte
(Avance o Seguimiento) a una lista de emails. El worker
`app.workers.tasks.scheduled_reports` consume estas filas y dispara
el PDF por Resend cuando `next_run_at <= now`.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import business_rule, forbidden, not_found
from app.db.session import get_db
from app.models.project import Project
from app.models.scheduled_report import ScheduledReport
from app.services.audit import write_audit
from app.services.scheduled_reports import (
    CADENCES,
    REPORT_TYPES,
    Cadence,
    ReportType,
    compute_next_run,
)

router = APIRouter(tags=["scheduled-reports"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


async def _get_project(db: AsyncSession, tenant_id: UUID, project_id: UUID) -> Project:
    p = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id), Project.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")
    return p


class ScheduledReportCreate(BaseModel):
    report_type: ReportType
    cadence: Cadence
    recipients: list[EmailStr] = Field(min_length=1)
    enabled: bool = True
    # ENH-046: opcionales según cadencia.
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    hour_of_day: int | None = Field(default=None, ge=0, le=23)
    # ENH-056: día del mes (1-31) para cadence=monthly. Clamp server-side.
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    run_at: datetime | None = None
    # US-131: para report_type='custom', plantilla del Report Builder.
    report_builder_template_id: UUID | None = None

    @model_validator(mode="after")
    def _validate_cadence_fields(self):
        if self.cadence == "once" and self.run_at is None:
            raise ValueError("cadence=once requiere run_at")
        if self.cadence == "weekly" and (
            self.day_of_week is None or self.hour_of_day is None
        ):
            raise ValueError(
                "cadence=weekly requiere day_of_week (0-6) y hour_of_day (0-23)"
            )
        if self.cadence == "daily" and self.hour_of_day is None:
            raise ValueError("cadence=daily requiere hour_of_day (0-23)")
        if self.cadence == "monthly" and (
            self.day_of_month is None or self.hour_of_day is None
        ):
            raise ValueError(
                "cadence=monthly requiere day_of_month (1-31) y hour_of_day (0-23)"
            )
        if self.report_type == "custom" and self.report_builder_template_id is None:
            raise ValueError(
                "report_type=custom requiere report_builder_template_id"
            )
        return self


class ScheduledReportUpdate(BaseModel):
    report_type: ReportType | None = None
    cadence: Cadence | None = None
    recipients: list[EmailStr] | None = None
    enabled: bool | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    hour_of_day: int | None = Field(default=None, ge=0, le=23)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    run_at: datetime | None = None


class ScheduledReportRead(BaseModel):
    id: UUID
    project_id: UUID
    report_type: str
    cadence: str
    recipients: list[str]
    enabled: bool
    day_of_week: int | None = None
    hour_of_day: int | None = None
    day_of_month: int | None = None
    run_at: datetime | None = None
    report_builder_template_id: UUID | None = None
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def _validate_enum(field: str, value: str, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        raise business_rule(f"{field} inválido: {value}")


@router.get(
    "/projects/{project_id}/scheduled-reports",
    response_model=list[ScheduledReportRead],
)
async def list_scheduled_reports(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, tenant_id, project_id)
    rows = (
        await db.execute(
            select(ScheduledReport)
            .where(
                ScheduledReport.tenant_id == str(tenant_id),
                ScheduledReport.project_id == str(project_id),
            )
            .order_by(ScheduledReport.created_at.desc())
        )
    ).scalars().all()
    return [ScheduledReportRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/scheduled-reports",
    response_model=ScheduledReportRead,
    status_code=201,
)
async def create_scheduled_report(
    project_id: UUID,
    body: ScheduledReportCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    _validate_enum("report_type", body.report_type, REPORT_TYPES)
    _validate_enum("cadence", body.cadence, CADENCES)

    sched = ScheduledReport(
        tenant_id=str(tenant_id),
        project_id=str(project.id),
        report_type=body.report_type,
        cadence=body.cadence,
        day_of_week=body.day_of_week,
        hour_of_day=body.hour_of_day,
        day_of_month=body.day_of_month,
        run_at=body.run_at,
        report_builder_template_id=(
            str(body.report_builder_template_id)
            if body.report_builder_template_id
            else None
        ),
        recipients=[str(e) for e in body.recipients],
        enabled=body.enabled,
        next_run_at=(
            compute_next_run(
                body.cadence,
                day_of_week=body.day_of_week,
                hour_of_day=body.hour_of_day,
                day_of_month=body.day_of_month,
                run_at=body.run_at,
            )
            if body.enabled
            else None
        ),
        created_by=cu.id,
    )
    db.add(sched)
    await db.flush()
    await write_audit(
        db,
        action="scheduled_report.create",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="scheduled_report",
        entity_id=str(sched.id),
        details={
            "report_type": body.report_type,
            "cadence": body.cadence,
            "recipients_count": len(sched.recipients),
        },
    )
    await db.commit()
    return ScheduledReportRead.model_validate(sched)


@router.patch(
    "/scheduled-reports/{scheduled_id}", response_model=ScheduledReportRead
)
async def update_scheduled_report(
    scheduled_id: UUID,
    body: ScheduledReportUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    sched = (
        await db.execute(
            select(ScheduledReport).where(
                ScheduledReport.id == str(scheduled_id),
                ScheduledReport.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if sched is None:
        raise not_found("Programación")

    data = body.model_dump(exclude_unset=True)
    if "report_type" in data and data["report_type"] is not None:
        _validate_enum("report_type", data["report_type"], REPORT_TYPES)
    if "cadence" in data and data["cadence"] is not None:
        _validate_enum("cadence", data["cadence"], CADENCES)
    if "recipients" in data and data["recipients"] is not None:
        if len(data["recipients"]) == 0:
            raise business_rule("Debe haber al menos un destinatario")
        data["recipients"] = [str(e) for e in data["recipients"]]

    prev_enabled = sched.enabled
    prev_cadence = sched.cadence
    prev_dow = sched.day_of_week
    prev_hod = sched.hour_of_day
    prev_dom = sched.day_of_month
    prev_run_at = sched.run_at
    for field, value in data.items():
        setattr(sched, field, value)

    # ENH-046 / ENH-056: validación condicional pos-merge SOLO si el
    # caller tocó campos de cadencia. Filas legacy reciben updates de
    # `recipients`/`enabled` sin tropezar con validación.
    cadence_fields_touched = any(
        f in data
        for f in ("cadence", "day_of_week", "hour_of_day", "day_of_month", "run_at")
    )
    if cadence_fields_touched:
        if sched.cadence == "once" and sched.run_at is None:
            raise business_rule("cadence=once requiere run_at")
        if sched.cadence == "weekly" and (
            sched.day_of_week is None or sched.hour_of_day is None
        ):
            raise business_rule(
                "cadence=weekly requiere day_of_week (0-6) y hour_of_day (0-23)"
            )
        if sched.cadence == "daily" and sched.hour_of_day is None:
            raise business_rule("cadence=daily requiere hour_of_day (0-23)")
        if sched.cadence == "monthly" and (
            sched.day_of_month is None or sched.hour_of_day is None
        ):
            raise business_rule(
                "cadence=monthly requiere day_of_month (1-31) y hour_of_day (0-23)"
            )

    # Re-computar next_run_at si cambió algún input que lo afecta.
    inputs_changed = (
        sched.cadence != prev_cadence
        or sched.day_of_week != prev_dow
        or sched.hour_of_day != prev_hod
        or sched.day_of_month != prev_dom
        or sched.run_at != prev_run_at
        or (sched.enabled and not prev_enabled)
    )
    if sched.enabled and (inputs_changed or sched.next_run_at is None):
        sched.next_run_at = compute_next_run(
            sched.cadence,
            day_of_week=sched.day_of_week,
            hour_of_day=sched.hour_of_day,
            day_of_month=sched.day_of_month,
            run_at=sched.run_at,
        )
    if not sched.enabled:
        sched.next_run_at = None

    await write_audit(
        db,
        action="scheduled_report.update",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="scheduled_report",
        entity_id=str(sched.id),
        details=data,
    )
    await db.commit()
    await db.refresh(sched)
    return ScheduledReportRead.model_validate(sched)


@router.post(
    "/scheduled-reports/{scheduled_id}/run-now", status_code=202
)
async def run_scheduled_report_now(
    scheduled_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """BUG-036: dispara el envío inmediato del reporte sin esperar la
    cadencia. Útil para que el owner valide end-to-end (PDF + email)
    desde la UI antes de confiar en el beat scheduler.

    Devuelve 202 Accepted con `{ scheduled_id, queued_at }`. El task
    se enqueue vía Celery; si el worker está caído, la fila queda
    esperando y se procesará al próximo arranque.
    """
    from datetime import UTC
    from datetime import datetime as _dt

    tenant_id = _tenant(cu)
    sched = (
        await db.execute(
            select(ScheduledReport).where(
                ScheduledReport.id == str(scheduled_id),
                ScheduledReport.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if sched is None:
        raise not_found("Programación")

    # Importa el task aquí (lazy) para evitar circular imports en boot.
    from app.workers.tasks.scheduled_reports import send_scheduled_report

    try:
        send_scheduled_report.delay(str(sched.id))
    except Exception as exc:
        # Si el broker está caído (Redis sin conectar), reportarlo claro.
        raise business_rule(
            f"No se pudo encolar el envío: {exc}",
            code="QUEUE_UNAVAILABLE",
        ) from exc

    await write_audit(
        db,
        action="scheduled_report.run_now",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="scheduled_report",
        entity_id=str(sched.id),
    )
    await db.commit()
    return {
        "scheduled_id": str(sched.id),
        "queued_at": _dt.now(UTC).isoformat(),
        "note": "El envío se procesa en background. Verifica logs de Railway o tu inbox en 1-2 min.",
    }


@router.delete("/scheduled-reports/{scheduled_id}", status_code=204)
async def delete_scheduled_report(
    scheduled_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    sched = (
        await db.execute(
            select(ScheduledReport).where(
                ScheduledReport.id == str(scheduled_id),
                ScheduledReport.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if sched is None:
        raise not_found("Programación")
    await db.delete(sched)
    await write_audit(
        db,
        action="scheduled_report.delete",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="scheduled_report",
        entity_id=str(scheduled_id),
    )
    await db.commit()
    return Response(status_code=204)
