"""Project Reports — CRUD y listado (US-NEW-022, EP006).

Complementa al draft-con-IA existente en `/ai/projects/{id}/reports/draft`
(EP008) con CRUD manual y un listado paginable por proyecto.
"""
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.ai import Report
from app.models.project import Project
from app.services.audit import write_audit
from app.services.operational_reports import build_avance_context
from app.services.pdf_renderer import render_pdf

router = APIRouter(tags=["reports"])


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


ReportPeriod = Literal["daily", "weekly", "monthly"]
ReportStatus = Literal["draft", "sent"]


DEFAULT_SECTIONS = {
    "resumen_ejecutivo": "",
    "avance_plan": "",
    "acciones_pendientes": "",
    "decisiones_requeridas": "",
    "riesgos_top": "",
}


class ReportCreate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    period: ReportPeriod | None = None
    recipients: list[EmailStr] = []
    sections: dict[str, str] | None = None


class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    period: ReportPeriod | None = None
    recipients: list[EmailStr] | None = None
    sections: dict[str, str] | None = None


class ReportRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    period: str | None
    status: str
    recipients: list[str]
    sections: dict
    generated_by_ai: bool
    generator: str = "manual"
    cut_off_date: date | None = None
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/projects/{project_id}/reports", response_model=list[ReportRead])
async def list_reports(
    project_id: UUID,
    status: str | None = Query(default=None),
    period: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cu: CurrentUser = Depends(require_permission("projects", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, tenant_id, project_id)
    stmt = (
        select(Report)
        .where(Report.tenant_id == str(tenant_id), Report.project_id == str(project_id))
        .order_by(Report.created_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(Report.status == status)
    if period:
        stmt = stmt.where(Report.period == period)
    rows = (await db.execute(stmt)).scalars().all()
    return [ReportRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/reports",
    response_model=ReportRead,
    status_code=201,
)
async def create_report(
    project_id: UUID,
    body: ReportCreate,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Crea un reporte manual (borrador). Secciones pre-llenadas con las
    sugeridas en US-NEW-022 si no se envían."""
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)

    default_title = (
        f"Reporte {project.folio} — "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}"
    )
    rep = Report(
        tenant_id=str(tenant_id),
        project_id=str(project.id),
        title=body.title or default_title,
        period=body.period,
        sections=body.sections or dict(DEFAULT_SECTIONS),
        recipients=[str(e) for e in body.recipients],
        status="draft",
        generated_by_ai=False,
        created_by=cu.id,
    )
    db.add(rep)
    await db.flush()
    await write_audit(
        db,
        action="report.create",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report",
        entity_id=str(rep.id),
        details={"period": body.period},
    )
    await db.commit()
    return ReportRead.model_validate(rep)


@router.get("/reports/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id), Report.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    return ReportRead.model_validate(rep)


@router.patch("/reports/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: UUID,
    body: ReportUpdate,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id), Report.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    if rep.status == "sent":
        from app.core.errors import business_rule

        raise business_rule("Un reporte enviado no puede editarse")
    data = body.model_dump(exclude_unset=True)
    if "recipients" in data and data["recipients"] is not None:
        data["recipients"] = [str(e) for e in data["recipients"]]
    for field, value in data.items():
        setattr(rep, field, value)
    await write_audit(
        db,
        action="report.update",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report",
        entity_id=str(rep.id),
    )
    await db.commit()
    return ReportRead.model_validate(rep)


# ---- EP014 US-NEW-038/039: reportes ejecutables sin IA ----

class AvanceGenerate(BaseModel):
    cut_off_date: date | None = None


def _pdf_response(pdf: bytes, filename: str) -> Response:
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _tenant_name(db: AsyncSession, tenant_id: UUID) -> str | None:
    from app.models.tenant import Tenant

    return (
        await db.execute(select(Tenant.name).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()


@router.post("/projects/{project_id}/reports/avance")
async def generate_avance_report(
    project_id: UUID,
    body: AvanceGenerate | None = None,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Genera Reporte de Avance (Python, sin IA). Devuelve el PDF y guarda
    un row en `reports` con generator='avance' + snapshot del contexto."""
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    cut_off = (body.cut_off_date if body else None) or datetime.now(UTC).date()

    context = await build_avance_context(db, tenant_id, project.id, cut_off)
    context["tenant_name"] = await _tenant_name(db, tenant_id)

    pdf = render_pdf("reports/avance.html", context)

    rep = Report(
        tenant_id=str(tenant_id),
        project_id=str(project.id),
        title=f"Reporte de Avance — {project.folio} — {cut_off.isoformat()}",
        period=None,
        generator="avance",
        cut_off_date=cut_off,
        sections=context,
        recipients=[],
        status="draft",
        generated_by_ai=False,
        created_by=cu.id,
    )
    db.add(rep)
    await db.flush()
    await write_audit(
        db,
        action="report.generate.avance",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report",
        entity_id=str(rep.id),
        details={"cut_off_date": cut_off.isoformat()},
    )
    await db.commit()

    filename = f"Reporte_Avance_{project.folio}_{cut_off.isoformat()}.pdf"
    return _pdf_response(pdf, filename)


@router.get("/reports/{report_id}/avance/download")
async def download_avance_report(
    report_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Re-descarga un Reporte de Avance previamente generado (usa
    contexto persistido en `sections`)."""
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id),
                Report.tenant_id == str(tenant_id),
                Report.generator == "avance",
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    ctx = dict(rep.sections or {})
    ctx["tenant_name"] = await _tenant_name(db, tenant_id)
    pdf = render_pdf("reports/avance.html", ctx)
    project = await _get_project(db, tenant_id, UUID(rep.project_id))
    filename = (
        f"Reporte_Avance_{project.folio}_"
        f"{(rep.cut_off_date.isoformat() if rep.cut_off_date else 'snapshot')}.pdf"
    )
    return _pdf_response(pdf, filename)


@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id), Report.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    if rep.status == "sent":
        from app.core.errors import business_rule

        raise business_rule("Un reporte enviado no puede eliminarse")
    await db.delete(rep)
    await write_audit(
        db,
        action="report.delete",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report",
        entity_id=str(report_id),
    )
    await db.commit()
    return Response(status_code=204)
