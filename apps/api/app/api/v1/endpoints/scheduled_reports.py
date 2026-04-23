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
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
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
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


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


class ScheduledReportUpdate(BaseModel):
    report_type: ReportType | None = None
    cadence: Cadence | None = None
    recipients: list[EmailStr] | None = None
    enabled: bool | None = None


class ScheduledReportRead(BaseModel):
    id: UUID
    project_id: UUID
    report_type: str
    cadence: str
    recipients: list[str]
    enabled: bool
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
    cu: CurrentUser = Depends(require_permission("projects", "read")),
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
    cu: CurrentUser = Depends(require_permission("projects", "update")),
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
        recipients=[str(e) for e in body.recipients],
        enabled=body.enabled,
        next_run_at=compute_next_run(body.cadence) if body.enabled else None,
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
    cu: CurrentUser = Depends(require_permission("projects", "update")),
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
    for field, value in data.items():
        setattr(sched, field, value)

    # Si se habilitó o cambió la cadencia, re-computar next_run_at.
    if sched.enabled and (
        not prev_enabled or sched.cadence != prev_cadence or sched.next_run_at is None
    ):
        sched.next_run_at = compute_next_run(sched.cadence)
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


@router.delete("/scheduled-reports/{scheduled_id}", status_code=204)
async def delete_scheduled_report(
    scheduled_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
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
