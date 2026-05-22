"""Scheduled Minutes — CRUD de programaciones de envío de minutas (ENH-107, EP014).

Símil de `scheduled_reports`: el PM/admin programa el envío recurrente
de la última minuta del proyecto a una lista de emails. El worker
`app.workers.tasks.scheduled_minutes` consume estas filas y dispara el
PDF por Resend cuando ``next_run_at <= now``. Si no hay minuta en el
periodo evaluado, envía un email fallback informativo.
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
from app.models.scheduled_minute import ScheduledMinute
from app.services.audit import write_audit
from app.services.scheduled_minutes import CADENCES, Cadence, compute_next_run

router = APIRouter(tags=["scheduled-minutes"])


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


class ScheduledMinuteCreate(BaseModel):
    cadence: Cadence
    recipients: list[EmailStr] = Field(min_length=1)
    enabled: bool = True
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    hour_of_day: int | None = Field(default=None, ge=0, le=23)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    run_at: datetime | None = None
    template_id: UUID | None = None

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
        return self


class ScheduledMinuteUpdate(BaseModel):
    cadence: Cadence | None = None
    recipients: list[EmailStr] | None = None
    enabled: bool | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    hour_of_day: int | None = Field(default=None, ge=0, le=23)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    run_at: datetime | None = None
    template_id: UUID | None = None


class ScheduledMinuteRead(BaseModel):
    id: UUID
    project_id: UUID
    cadence: str
    recipients: list[str]
    enabled: bool
    day_of_week: int | None = None
    hour_of_day: int | None = None
    day_of_month: int | None = None
    run_at: datetime | None = None
    template_id: UUID | None = None
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
    "/projects/{project_id}/scheduled-minutes",
    response_model=list[ScheduledMinuteRead],
)
async def list_scheduled_minutes(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, tenant_id, project_id)
    rows = (
        await db.execute(
            select(ScheduledMinute)
            .where(
                ScheduledMinute.tenant_id == str(tenant_id),
                ScheduledMinute.project_id == str(project_id),
            )
            .order_by(ScheduledMinute.created_at.desc())
        )
    ).scalars().all()
    return [ScheduledMinuteRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/scheduled-minutes",
    response_model=ScheduledMinuteRead,
    status_code=201,
)
async def create_scheduled_minute(
    project_id: UUID,
    body: ScheduledMinuteCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    _validate_enum("cadence", body.cadence, CADENCES)

    sched = ScheduledMinute(
        tenant_id=str(tenant_id),
        project_id=str(project.id),
        cadence=body.cadence,
        day_of_week=body.day_of_week,
        hour_of_day=body.hour_of_day,
        day_of_month=body.day_of_month,
        run_at=body.run_at,
        template_id=str(body.template_id) if body.template_id else None,
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
        action="scheduled_minute.create",
        module="minutes",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="scheduled_minute",
        entity_id=str(sched.id),
        details={
            "cadence": body.cadence,
            "recipients_count": len(sched.recipients),
        },
    )
    await db.commit()
    return ScheduledMinuteRead.model_validate(sched)


@router.patch(
    "/scheduled-minutes/{scheduled_id}", response_model=ScheduledMinuteRead
)
async def update_scheduled_minute(
    scheduled_id: UUID,
    body: ScheduledMinuteUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    sched = (
        await db.execute(
            select(ScheduledMinute).where(
                ScheduledMinute.id == str(scheduled_id),
                ScheduledMinute.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if sched is None:
        raise not_found("Programación")

    data = body.model_dump(exclude_unset=True)
    if "cadence" in data and data["cadence"] is not None:
        _validate_enum("cadence", data["cadence"], CADENCES)
    if "recipients" in data and data["recipients"] is not None:
        if len(data["recipients"]) == 0:
            raise business_rule("Debe haber al menos un destinatario")
        data["recipients"] = [str(e) for e in data["recipients"]]
    if "template_id" in data and data["template_id"] is not None:
        data["template_id"] = str(data["template_id"])

    prev_enabled = sched.enabled
    prev_cadence = sched.cadence
    prev_dow = sched.day_of_week
    prev_hod = sched.hour_of_day
    prev_dom = sched.day_of_month
    prev_run_at = sched.run_at
    for field, value in data.items():
        setattr(sched, field, value)

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
        action="scheduled_minute.update",
        module="minutes",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="scheduled_minute",
        entity_id=str(sched.id),
        details=data,
    )
    await db.commit()
    await db.refresh(sched)
    return ScheduledMinuteRead.model_validate(sched)


@router.delete("/scheduled-minutes/{scheduled_id}", status_code=204)
async def delete_scheduled_minute(
    scheduled_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    sched = (
        await db.execute(
            select(ScheduledMinute).where(
                ScheduledMinute.id == str(scheduled_id),
                ScheduledMinute.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if sched is None:
        raise not_found("Programación")
    await db.delete(sched)
    await write_audit(
        db,
        action="scheduled_minute.delete",
        module="minutes",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="scheduled_minute",
        entity_id=str(scheduled_id),
    )
    await db.commit()
    return Response(status_code=204)
