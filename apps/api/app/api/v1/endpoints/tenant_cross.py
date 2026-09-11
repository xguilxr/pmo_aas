"""US-052 — vistas cross-tenant de RAID/Cambios/Minutas/Reportes.

Los endpoints existentes en `modules.py` y `reports.py` son project-scoped
(`/projects/{id}/<recurso>`). Estas rutas agregan listado a nivel tenant
con filtros por organization_id, portfolio_id (US-201), program_id y
project_id, para las
páginas `/admin/raid`, `/admin/changes`, `/admin/minutes` y
`/admin/reports`.

ENH-010: cada item del JSON incluye `project_folio` y `project_name`
para que la UI muestre el proyecto legible (no solo el UUID).
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.api.v1.endpoints.reports import ReportRead
from app.core.errors import forbidden
from app.db.session import get_db
from app.models.ai import Report
from app.models.area import Area as ProjectArea  # ENH-078: alias post drop
from app.models.modules import (
    ChangeRequest,
    Issue,
    MeetingMinute,
    Risk,
)
from app.models.project import Project
from app.schemas.modules import (
    ChangeRequestRead,
    IssueRead,
    MeetingMinuteRead,
    RiskRead,
)

router = APIRouter(prefix="/tenant", tags=["tenant_cross"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


def _project_scope(
    stmt,
    project_model_rel,
    tenant_id: UUID,
    organization_id: UUID | None,
    program_id: UUID | None,
    project_id: UUID | None,
    portfolio_id: UUID | None = None,
):
    """Aplica filtros cruzados (tenant, org, portafolio, programa, proyecto) +
    selecciona `Project.folio` y `Project.name` para enriquecer la
    respuesta (ENH-010).

    US-201 — `portfolio_id` va al final y con valor por defecto para no
    reordenar las llamadas posicionales que ya existen: cinco superficies llaman
    aquí y una firma reordenada las rompe todas a la vez, en silencio si los
    tipos coinciden.
    """
    stmt = stmt.add_columns(Project.folio, Project.name).join(
        Project, Project.id == project_model_rel
    ).where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
    if organization_id is not None:
        stmt = stmt.where(Project.organization_id == str(organization_id))
    if portfolio_id is not None:
        stmt = stmt.where(Project.portfolio_id == str(portfolio_id))
    if program_id is not None:
        stmt = stmt.where(Project.program_id == str(program_id))
    if project_id is not None:
        stmt = stmt.where(Project.id == str(project_id))
    return stmt


def _enrich(item_read: Any, folio: str, name: str) -> dict:
    data = item_read.model_dump(mode="json")
    data["project_folio"] = folio
    data["project_name"] = name
    return data


@router.get("/risks")
async def list_tenant_risks(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    # ENH-019: filtros avanzados.
    status: str | None = Query(default=None),
    severity_min: int | None = Query(default=None, ge=1, le=25),
    owner_id: UUID | None = Query(default=None),
    area_id: UUID | None = Query(default=None),  # US-064.
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    tenant_id = _tenant(cu)
    # US-064: outer join con ProjectArea para ordering + embed en el item.
    stmt = select(Risk, ProjectArea).outerjoin(
        ProjectArea, ProjectArea.id == Risk.area_id
    ).where(Risk.deleted_at.is_(None))
    stmt = _project_scope(
        stmt,
        Risk.project_id,
        tenant_id,
        organization_id,
        program_id,
        project_id,
        portfolio_id,
    )
    if status:
        stmt = stmt.where(Risk.status == status)
    if severity_min is not None:
        stmt = stmt.where(Risk.severity >= severity_min)
    if owner_id is not None:
        stmt = stmt.where(Risk.owner_id == str(owner_id))
    if area_id is not None:
        stmt = stmt.where(Risk.area_id == str(area_id))
    stmt = stmt.order_by(
        case((Risk.area_id.is_(None), 1), else_=0),
        ProjectArea.name.asc(),
        Risk.identified_at.desc().nullslast(),
        Risk.severity.desc().nullslast(),
    )
    rows = (await db.execute(stmt)).all()
    out: list[dict] = []
    for r, area, folio, name in rows:
        r.area = {"id": area.id, "name": area.name} if area else None  # type: ignore[attr-defined]
        out.append(_enrich(RiskRead.model_validate(r), folio, name))
    return out


@router.get("/issues")
async def list_tenant_issues(
    type: str | None = Query(default=None, description="action|issue|decision"),
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    # ENH-019: filtros avanzados.
    status: str | None = Query(default=None),
    priority_min: int | None = Query(default=None, ge=1, le=5),
    owner_id: UUID | None = Query(default=None),
    area_id: UUID | None = Query(default=None),  # US-064.
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    tenant_id = _tenant(cu)
    stmt = select(Issue, ProjectArea).outerjoin(
        ProjectArea, ProjectArea.id == Issue.area_id
    ).where(Issue.deleted_at.is_(None))
    stmt = _project_scope(
        stmt,
        Issue.project_id,
        tenant_id,
        organization_id,
        program_id,
        project_id,
        portfolio_id,
    )
    if type:
        stmt = stmt.where(Issue.type == type)
    if status:
        stmt = stmt.where(Issue.status == status)
    if priority_min is not None:
        stmt = stmt.where(Issue.priority >= priority_min)
    if owner_id is not None:
        stmt = stmt.where(Issue.owner_id == str(owner_id))
    if area_id is not None:
        stmt = stmt.where(Issue.area_id == str(area_id))
    stmt = stmt.order_by(
        case((Issue.area_id.is_(None), 1), else_=0),
        ProjectArea.name.asc(),
        Issue.reported_at.desc(),
        Issue.priority.desc().nullslast(),
    )
    rows = (await db.execute(stmt)).all()
    out: list[dict] = []
    for r, area, folio, name in rows:
        r.area = {"id": area.id, "name": area.name} if area else None  # type: ignore[attr-defined]
        out.append(_enrich(IssueRead.model_validate(r), folio, name))
    return out


@router.get("/change-requests")
async def list_tenant_changes(
    status: str | None = Query(default=None),
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    tenant_id = _tenant(cu)
    stmt = select(ChangeRequest).where(ChangeRequest.deleted_at.is_(None))
    stmt = _project_scope(
        stmt,
        ChangeRequest.project_id,
        tenant_id,
        organization_id,
        program_id,
        project_id,
        portfolio_id,
    )
    if status:
        stmt = stmt.where(ChangeRequest.status == status)
    rows = (await db.execute(stmt.order_by(ChangeRequest.created_at.desc()))).all()
    return [
        _enrich(ChangeRequestRead.model_validate(r), folio, name)
        for r, folio, name in rows
    ]


@router.get("/meeting-minutes")
async def list_tenant_minutes(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    tenant_id = _tenant(cu)
    stmt = select(MeetingMinute)
    stmt = _project_scope(
        stmt,
        MeetingMinute.project_id,
        tenant_id,
        organization_id,
        program_id,
        project_id,
        portfolio_id,
    )
    rows = (await db.execute(stmt.order_by(MeetingMinute.meeting_date.desc()))).all()
    return [
        _enrich(MeetingMinuteRead.model_validate(r), folio, name)
        for r, folio, name in rows
    ]


@router.get("/reports")
async def list_tenant_reports(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    include_drafts: bool = Query(default=False),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """ENH-120 — listado tenant-wide de reportes de proyecto.

    Cambios respecto al endpoint legacy:
    - Filtra `status='draft'` por default (owner pidió que sólo aparezcan
      reportes guardados/enviados). Pasar `?include_drafts=true` para ver
      borradores.
    - Enriquece cada item con `folio` (derivado del id corto),
      `report_type` (derivado de `generator`) y `period` (existente).
    """
    tenant_id = _tenant(cu)
    stmt = select(Report)
    stmt = _project_scope(
        stmt,
        Report.project_id,
        tenant_id,
        organization_id,
        program_id,
        project_id,
        portfolio_id,
    )
    if not include_drafts:
        stmt = stmt.where(Report.status != "draft")
    rows = (await db.execute(stmt.order_by(Report.created_at.desc()))).all()
    out: list[dict] = []
    for r, project_folio, project_name in rows:
        data = _enrich(ReportRead.model_validate(r), project_folio, project_name)
        # ENH-120: folio del reporte derivado del id (cascarón).
        # Cuando exista un campo `folio` real en Report, usarlo en vez
        # de derivarlo. Por ahora `RPT-<8 chars id>` es estable.
        data["folio"] = f"RPT-{str(r.id)[:8].upper()}"
        # ENH-120: report_type derivado del generator. "ai" → "Builder"
        # cuando el reporte vino de la integración legacy IA → builder.
        gen = data.get("generator") or "manual"
        type_label = {
            "manual": "Manual",
            "ai": "Builder",
            "builder": "Builder",
            "avance": "Avance",
            "seguimiento": "Seguimiento",
            "look_ahead": "Look-ahead",
        }.get(gen, gen.title())
        data["report_type"] = type_label
        # period viene del modelo directo (ReportRead lo expone).
        out.append(data)
    return out


# ---------------------------------------------------------------------------
# FASE-8 (revamp v2, US-A) — export XLSX transversal, para el botón "Descargar
# Excel" de las pestañas RAID y Cambios de `/pmo/reports`. Reusa
# `raid_export.py`/`change_export.py` (ENH-152/ENH-186): no se escribe un
# segundo generador. Lo único nuevo es anteponer "Proyecto (folio)" y
# "Proyecto" a cada fila — el archivo por-proyecto no las necesita, este sí,
# porque mezcla filas de organizaciones/portafolios/programas distintos.
# ---------------------------------------------------------------------------


async def _org_slug(db: AsyncSession, organization_id: UUID | None) -> str:
    from app.models.organization import Organization
    from app.services.filename_slug import slugify_project_name

    if organization_id is None:
        return "todas"
    org = (
        await db.execute(
            select(Organization.name).where(Organization.id == str(organization_id))
        )
    ).scalar_one_or_none()
    return slugify_project_name(org, fallback="organizacion")


@router.get("/raid/export")
async def export_tenant_raid(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Excel de 4 hojas RAID (Riesgos/Acciones/Incidencias/Decisiones) de
    **todos** los proyectos que pasan los filtros — no uno solo. Mismo
    archivo que ve la tabla agrupada de la pestaña RAID de `/pmo/reports`."""
    from datetime import date
    from io import BytesIO
    from urllib.parse import quote

    from app.models.area import Actor, Area
    from app.models.user import User
    from app.services.raid_export import (
        AID_HEADERS,
        RISK_HEADERS,
        XLSX_MIME,
        build_issue_rows,
        build_risk_rows,
    )

    tenant_id = _tenant(cu)

    risk_stmt = _project_scope(
        select(Risk).where(Risk.deleted_at.is_(None)),
        Risk.project_id, tenant_id, organization_id, program_id, None, portfolio_id,
    )
    issue_stmt = _project_scope(
        select(Issue).where(Issue.deleted_at.is_(None)),
        Issue.project_id, tenant_id, organization_id, program_id, None, portfolio_id,
    )
    risk_rows_raw = (await db.execute(risk_stmt)).all()
    issue_rows_raw = (await db.execute(issue_stmt)).all()
    risks = [r for r, _folio, _name in risk_rows_raw]
    issues = [i for i, _folio, _name in issue_rows_raw]

    area_ids = {str(x.area_id) for x in [*risks, *issues] if x.area_id}
    actor_ids = {str(x.owner_actor_id) for x in [*risks, *issues] if x.owner_actor_id}
    user_ids = {str(x.owner_id) for x in [*risks, *issues] if x.owner_id}
    area_names = {
        str(a.id): a.name
        for a in (await db.execute(select(Area).where(Area.id.in_(area_ids)))).scalars().all()
    } if area_ids else {}
    actor_names = {
        str(a.id): a.name
        for a in (await db.execute(select(Actor).where(Actor.id.in_(actor_ids)))).scalars().all()
    } if actor_ids else {}
    user_names = {
        str(u.id): u.full_name
        for u in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    } if user_ids else {}

    def _prefixed(built: list[list[Any]], raw: list[Any]) -> list[list[Any]]:
        return [
            [folio, name, *row]
            for row, (_obj, folio, name) in zip(built, raw, strict=True)
        ]

    risk_rows = _prefixed(
        build_risk_rows(risks, area_names, actor_names, user_names), risk_rows_raw
    )
    actions = [(i, f, n) for i, f, n in issue_rows_raw if i.type == "action"]
    incidents = [(i, f, n) for i, f, n in issue_rows_raw if i.type == "issue"]
    decisions = [(i, f, n) for i, f, n in issue_rows_raw if i.type == "decision"]
    action_rows = _prefixed(
        build_issue_rows([i for i, _f, _n in actions], area_names, actor_names, user_names),
        actions,
    )
    incident_rows = _prefixed(
        build_issue_rows([i for i, _f, _n in incidents], area_names, actor_names, user_names),
        incidents,
    )
    decision_rows = _prefixed(
        build_issue_rows([i for i, _f, _n in decisions], area_names, actor_names, user_names),
        decisions,
    )

    prefijo_headers = ["Proyecto (folio)", "Proyecto"]
    from openpyxl import Workbook

    from app.core.tipografia import aplicar_a_workbook
    from app.services.raid_export import _write_sheet

    wb = Workbook()
    aplicar_a_workbook(wb)
    default_ws = wb.active
    if default_ws is not None:
        wb.remove(default_ws)
    _write_sheet(wb, "Riesgos", [*prefijo_headers, *RISK_HEADERS], risk_rows)
    _write_sheet(wb, "Acciones", [*prefijo_headers, *AID_HEADERS], action_rows)
    _write_sheet(wb, "Incidencias", [*prefijo_headers, *AID_HEADERS], incident_rows)
    _write_sheet(wb, "Decisiones", [*prefijo_headers, *AID_HEADERS], decision_rows)
    buf = BytesIO()
    wb.save(buf)
    data = buf.getvalue()

    slug = await _org_slug(db, organization_id)
    filename = f"raid-{slug}-{date.today().isoformat()}.xlsx"
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        ),
    }
    return StreamingResponse(BytesIO(data), media_type=XLSX_MIME, headers=headers)


@router.get("/change-requests/export")
async def export_tenant_changes(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Excel de 1 hoja "Cambios" de todos los proyectos que pasan los
    filtros. Mismo archivo que ve la tabla de la pestaña Cambios."""
    from datetime import date
    from io import BytesIO
    from urllib.parse import quote

    from openpyxl import Workbook

    from app.core.tipografia import aplicar_a_workbook
    from app.models.user import User
    from app.services.change_export import (
        CHANGE_HEADERS,
        XLSX_MIME,
        _write_sheet,
        build_change_rows,
    )

    tenant_id = _tenant(cu)
    stmt = _project_scope(
        select(ChangeRequest).where(ChangeRequest.deleted_at.is_(None)),
        ChangeRequest.project_id, tenant_id, organization_id, program_id, None, portfolio_id,
    )
    if status:
        stmt = stmt.where(ChangeRequest.status == status)
    rows_raw = (await db.execute(stmt.order_by(ChangeRequest.created_at.desc()))).all()
    changes = [c for c, _folio, _name in rows_raw]

    user_ids = {
        str(uid)
        for c in changes
        for uid in (c.requested_by, c.approved_by)
        if uid
    }
    user_names = {
        str(u.id): u.full_name
        for u in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    } if user_ids else {}

    built = build_change_rows(changes, user_names)
    change_rows = [
        [folio, name, *row]
        for row, (_c, folio, name) in zip(built, rows_raw, strict=True)
    ]

    wb = Workbook()
    aplicar_a_workbook(wb)
    default_ws = wb.active
    if default_ws is not None:
        wb.remove(default_ws)
    _write_sheet(wb, "Cambios", ["Proyecto (folio)", "Proyecto", *CHANGE_HEADERS], change_rows)
    buf = BytesIO()
    wb.save(buf)
    data = buf.getvalue()

    slug = await _org_slug(db, organization_id)
    filename = f"cambios-{slug}-{date.today().isoformat()}.xlsx"
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        ),
    }
    return StreamingResponse(BytesIO(data), media_type=XLSX_MIME, headers=headers)
