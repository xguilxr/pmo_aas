from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import business_rule, conflict, forbidden, not_found
from app.db.session import get_db
from app.models.area import Area, AreaAssignment
from app.models.modules import (
    ChangeRequest,
    Document,
    Issue,
    Lesson,
    MeetingMinute,
    Risk,
)
from app.models.project import Project
from app.models.user import User
from app.schemas.modules import (
    ChangeRequestCreate,
    ChangeRequestRead,
    ChangeRequestUpdate,
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
    IssueComment,
    IssueCreate,
    IssueRead,
    IssueUpdate,
    LessonCreate,
    LessonRead,
    LessonUpdate,
    MeetingMinuteCreate,
    MeetingMinuteRead,
    MeetingMinuteUpdate,
    RaidApproveBatch,
    RiskComment,
    RiskCreate,
    RiskRead,
    RiskUpdate,
)
from app.services.audit import write_audit
from app.services.document_storage import save_document
from app.services.folio import next_folio

ALLOWED_DOC_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-excel",
    "image/png",
    "image/jpeg",
    "text/csv",
}
MAX_DOC_SIZE = 25 * 1024 * 1024


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


async def _get_project(db: AsyncSession, project_id: UUID, tenant_id: UUID) -> Project:
    p = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id), Project.tenant_id == tenant_id,
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")
    return p


def _ensure_editable(p: Project, *, allow_after_closed: bool = False) -> None:
    if p.phase == "closed" and not allow_after_closed:
        raise business_rule("Proyecto cerrado, no se puede escribir en este módulo")


async def _validate_area(
    db: AsyncSession, area_id: UUID, project_id: UUID, tenant_id: UUID
) -> Area:
    """US-064 / US-103: el area_id debe ser un Área del catálogo tenant
    asignada (vía area_assignments) al proyecto en cuestión. La cascada
    cubre is_global, project_id directo, program_id del proyecto y
    organization_id del proyecto.
    """
    project = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if project is None:
        raise business_rule("Proyecto no encontrado")
    cond = or_(
        AreaAssignment.is_global.is_(True),
        AreaAssignment.project_id == str(project_id),
        AreaAssignment.organization_id == str(project.organization_id),
    )
    if project.program_id:
        cond = or_(cond, AreaAssignment.program_id == str(project.program_id))
    # BUG-078: el JOIN con AreaAssignment multiplica filas cuando un área
    # tiene varias asignaciones que matchean la cascada (p.ej. is_global +
    # project_id). Todas las filas son la MISMA área (Area.id está fijado),
    # pero scalar_one_or_none() reventaba con MultipleResultsFound. Tomamos
    # la primera: solo necesitamos confirmar que el área es válida.
    area = (
        await db.execute(
            select(Area)
            .join(AreaAssignment, AreaAssignment.area_id == Area.id)
            .where(
                Area.id == str(area_id),
                Area.tenant_id == str(tenant_id),
                Area.is_active.is_(True),
                cond,
            )
        )
    ).scalars().first()
    if area is None:
        raise business_rule("Área no válida para este proyecto")
    return area


def _attach_area(item, area: Area | None) -> None:
    """Guarda el area embebida en un atributo transitorio para que
    *Read.model_validate la recoja automáticamente (from_attributes)."""
    item.area = (  # type: ignore[attr-defined]
        {"id": area.id, "name": area.name} if area else None
    )


async def _load_areas(
    db: AsyncSession, area_ids: list[str]
) -> dict[str, Area]:
    ids = [a for a in area_ids if a]
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(Area).where(Area.id.in_(ids))
        )
    ).scalars().all()
    return {str(a.id): a for a in rows}


async def _attach_owners(db: AsyncSession, items: list) -> None:
    """BUG-035: enriquece `item.owner` con `{id, full_name, email}` para
    que el sidebar de RAID detail muestre nombre del responsable en vez
    del UUID.

    Mutates `item.owner` in-place. Items sin `owner_id` quedan con
    owner=None. 1 SELECT batch del set único de owner_ids.
    """
    owner_ids: set[str] = set()
    for it in items:
        oid = getattr(it, "owner_id", None)
        if oid:
            owner_ids.add(str(oid))
    by_id: dict[str, User] = {}
    if owner_ids:
        rows = (
            await db.execute(select(User).where(User.id.in_(owner_ids)))
        ).scalars().all()
        by_id = {str(u.id): u for u in rows}
    for it in items:
        oid = getattr(it, "owner_id", None)
        user = by_id.get(str(oid)) if oid else None
        it.owner = (  # type: ignore[attr-defined]
            {
                "id": str(user.id),
                "full_name": user.full_name,
                "email": user.email,
            }
            if user
            else None
        )


async def _attach_change_users(db: AsyncSession, items: list) -> None:
    """ENH-039: enriquece `item.requester` y `item.approver` con
    `{id, full_name, email}` para que la UI de Cambios muestre los
    nombres en vez de UUIDs. 1 SELECT batch.
    """
    ids: set[str] = set()
    for it in items:
        for attr in ("requested_by", "approved_by"):
            v = getattr(it, attr, None)
            if v:
                ids.add(str(v))
    by_id: dict[str, User] = {}
    if ids:
        rows = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
        by_id = {str(u.id): u for u in rows}

    def _mini(uid):
        u = by_id.get(str(uid)) if uid else None
        return (
            {"id": str(u.id), "full_name": u.full_name, "email": u.email} if u else None
        )

    for it in items:
        it.requester = _mini(getattr(it, "requested_by", None))  # type: ignore[attr-defined]
        it.approver = _mini(getattr(it, "approved_by", None))  # type: ignore[attr-defined]


async def _attach_comment_authors(db: AsyncSession, items: list) -> None:
    """BUG-035: enriquece `item.comments[].author` con `{id, full_name,
    email}` para que el frontend muestre el nombre real en vez del UUID.

    Mutates `item.comments` in-place. Hace 1 SELECT batch del set único
    de `author_id`. Items sin comments se ignoran.
    """
    author_ids: set[str] = set()
    for it in items:
        for c in it.comments or []:
            aid = c.get("author_id") if isinstance(c, dict) else None
            if aid:
                author_ids.add(str(aid))
    if not author_ids:
        return
    rows = (
        await db.execute(select(User).where(User.id.in_(author_ids)))
    ).scalars().all()
    by_id = {str(u.id): u for u in rows}
    for it in items:
        new_comments = []
        for c in it.comments or []:
            if not isinstance(c, dict):
                new_comments.append(c)
                continue
            aid = c.get("author_id")
            user = by_id.get(str(aid)) if aid else None
            new_comments.append({
                **c,
                "author": (
                    {
                        "id": str(user.id),
                        "full_name": user.full_name,
                        "email": user.email,
                    }
                    if user
                    else None
                ),
            })
        it.comments = new_comments


# ========== RISKS ==========
risks_router = APIRouter(tags=["risks"])


@risks_router.get("/projects/{project_id}/risks", response_model=list[RiskRead])
async def list_risks(
    project_id: UUID,
    status: list[str] | None = Query(default=None),
    severity_min: int | None = Query(default=None, ge=1, le=25),
    severity_max: int | None = Query(default=None, ge=1, le=25),
    area_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    # US-064: outer join con project_areas para ordering por nombre de
    # área (legacy NULL va al final con COALESCE a 'ZZZ').
    stmt = (
        select(Risk, Area)
        .outerjoin(Area, Area.id == Risk.area_id)
        .where(Risk.project_id == str(project_id), Risk.deleted_at.is_(None))
    )
    if status:
        stmt = stmt.where(Risk.status.in_(status))
    if severity_min is not None:
        stmt = stmt.where(Risk.severity >= severity_min)
    if severity_max is not None:
        stmt = stmt.where(Risk.severity <= severity_max)
    if area_id is not None:
        stmt = stmt.where(Risk.area_id == str(area_id))
    if q:
        stmt = stmt.where(func.lower(Risk.title).like(f"%{q.lower()}%"))
    # US-064: legacy sin área va al final (CASE WHEN), luego por nombre
    # de área ascendente, fecha descendente, severidad descendente.
    stmt = stmt.order_by(
        case((Risk.area_id.is_(None), 1), else_=0),
        Area.name.asc(),
        Risk.identified_at.desc().nullslast(),
        Risk.severity.desc().nullslast(),
    )
    rows = (await db.execute(stmt)).all()
    risks = [r for r, _ in rows]
    await _attach_comment_authors(db, risks)
    await _attach_owners(db, risks)
    out: list[RiskRead] = []
    for r, area in rows:
        _attach_area(r, area)
        out.append(RiskRead.model_validate(r))
    return out


@risks_router.post("/projects/{project_id}/risks", response_model=RiskRead, status_code=201)
async def create_risk(
    project_id: UUID,
    body: RiskCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    _ensure_editable(p)
    # US-064: valida area antes de crear.
    area = await _validate_area(db, body.area_id, project_id, tenant_id)
    folio = await next_folio(db, tenant_id=tenant_id, prefix="RIS")
    severity = (body.probability or 0) * (body.impact or 0)
    r = Risk(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=body.title, description=body.description, category=body.category,
        probability=body.probability, impact=body.impact, severity=severity,
        mitigation_strategy=body.mitigation_strategy,
        owner_id=str(body.owner_id) if body.owner_id else None,
        owner_actor_id=str(body.owner_actor_id) if body.owner_actor_id else None,
        area_id=str(body.area_id),
        identified_at=body.identified_at, due_date=body.due_date,
        status=body.status, created_by=cu.id,
    )
    db.add(r)
    await db.flush()
    await write_audit(
        db, action="risk.create", module="risks", user_id=cu.id, tenant_id=tenant_id,
        entity_type="risk", entity_id=str(r.id), details={"folio": folio, "severity": severity},
    )
    await db.commit()
    _attach_area(r, area)
    await _attach_owners(db, [r])
    return RiskRead.model_validate(r)


@risks_router.get("/risks/{risk_id}", response_model=RiskRead)
async def get_risk(
    risk_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-065: detalle de un riesgo para la página dedicada."""
    tenant_id = _tenant(cu)
    row = (
        await db.execute(
            select(Risk, Area)
            .outerjoin(Area, Area.id == Risk.area_id)
            .where(
                Risk.id == str(risk_id),
                Risk.tenant_id == str(tenant_id),
                Risk.deleted_at.is_(None),
            )
        )
    ).one_or_none()
    if row is None:
        raise not_found("Riesgo")
    r, area = row
    _attach_area(r, area)
    await _attach_comment_authors(db, [r])
    await _attach_owners(db, [r])
    return RiskRead.model_validate(r)


@risks_router.patch("/risks/{risk_id}", response_model=RiskRead)
async def update_risk(
    risk_id: UUID,
    body: RiskUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    r = (await db.execute(select(Risk).where(Risk.id == str(risk_id), Risk.tenant_id == str(tenant_id)))).scalar_one_or_none()
    if r is None:
        raise not_found("Riesgo")
    data = body.model_dump(exclude_none=True)
    new_status = data.get("status")
    if new_status in {"closed", "materialized"}:
        note = data.get("closure_note") or r.closure_note
        if not note:
            raise business_rule("closure_note obligatorio al cerrar/materializar")
    if "owner_id" in data and data["owner_id"] is not None:
        data["owner_id"] = str(data["owner_id"])
    if "owner_actor_id" in data and data["owner_actor_id"] is not None:
        data["owner_actor_id"] = str(data["owner_actor_id"])
    # US-064: si el PATCH cambia area_id, validar pertenencia al proyecto.
    if "area_id" in data and data["area_id"] is not None:
        await _validate_area(db, data["area_id"], UUID(r.project_id), tenant_id)
        data["area_id"] = str(data["area_id"])
    for k, v in data.items():
        setattr(r, k, v)
    if data.get("probability") or data.get("impact"):
        r.severity = (r.probability or 0) * (r.impact or 0)
    await write_audit(
        db, action="risk.update", module="risks", user_id=cu.id, tenant_id=tenant_id,
        entity_type="risk", entity_id=str(r.id),
    )
    await db.commit()
    area = None
    if r.area_id:
        area = (
            await db.execute(
                select(Area).where(Area.id == r.area_id)
            )
        ).scalar_one_or_none()
    _attach_area(r, area)
    await _attach_comment_authors(db, [r])
    await _attach_owners(db, [r])
    return RiskRead.model_validate(r)


@risks_router.post("/risks/{risk_id}/comments", response_model=RiskRead)
async def add_risk_comment(
    risk_id: UUID,
    body: RiskComment,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-058: comentarios tipo Jira sobre un riesgo (mismo shape que
    `issues.comments`)."""
    tenant_id = _tenant(cu)
    r = (
        await db.execute(
            select(Risk).where(
                Risk.id == str(risk_id), Risk.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if r is None:
        raise not_found("Riesgo")
    comments = list(r.comments or [])
    comments.append(
        {
            "text": body.text,
            "author_id": str(cu.id),
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    r.comments = comments
    await write_audit(
        db,
        action="risk.comment.add",
        module="risks",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="risk",
        entity_id=str(r.id),
    )
    await db.commit()
    area = None
    if r.area_id:
        area = (
            await db.execute(select(Area).where(Area.id == r.area_id))
        ).scalar_one_or_none()
    _attach_area(r, area)
    await _attach_comment_authors(db, [r])
    await _attach_owners(db, [r])
    return RiskRead.model_validate(r)


@risks_router.delete("/risks/{risk_id}", status_code=204)
async def delete_risk(
    risk_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    r = (await db.execute(select(Risk).where(Risk.id == str(risk_id), Risk.tenant_id == str(tenant_id)))).scalar_one_or_none()
    if r is None:
        raise not_found("Riesgo")
    r.deleted_at = datetime.now(UTC)
    # ENH-112: audit del soft-delete (antes no se registraba; lo alineamos
    # con issue/lesson/change para trazabilidad).
    await write_audit(
        db, action="risk.delete", module="risks", user_id=cu.id,
        tenant_id=tenant_id, entity_type="risk", entity_id=str(r.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


# ========== ISSUES ==========
issues_router = APIRouter(tags=["issues"])


@issues_router.get("/projects/{project_id}/issues", response_model=list[IssueRead])
async def list_issues(
    project_id: UUID,
    status: list[str] | None = Query(default=None),
    overdue: bool = Query(default=False),
    type: str | None = Query(default=None),
    area_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    stmt = (
        select(Issue, Area)
        .outerjoin(Area, Area.id == Issue.area_id)
        .where(Issue.project_id == str(project_id), Issue.deleted_at.is_(None))
    )
    if status:
        stmt = stmt.where(Issue.status.in_(status))
    if type:
        stmt = stmt.where(Issue.type == type)
    if area_id is not None:
        stmt = stmt.where(Issue.area_id == str(area_id))
    if overdue:
        stmt = stmt.where(
            Issue.committed_date < date.today(),
            Issue.status.notin_(["resolved", "closed"]),
        )
    stmt = stmt.order_by(
        case((Issue.area_id.is_(None), 1), else_=0),
        Area.name.asc(),
        Issue.reported_at.desc(),
        Issue.priority.desc().nullslast(),
    )
    rows = (await db.execute(stmt)).all()
    issues = [i for i, _ in rows]
    await _attach_comment_authors(db, issues)
    await _attach_owners(db, issues)
    out: list[IssueRead] = []
    for i, area in rows:
        _attach_area(i, area)
        out.append(IssueRead.model_validate(i))
    return out


@issues_router.post("/projects/{project_id}/issues", response_model=IssueRead, status_code=201)
async def create_issue(
    project_id: UUID,
    body: IssueCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    _ensure_editable(p)
    # US-064: valida area antes de crear.
    area = await _validate_area(db, body.area_id, project_id, tenant_id)
    folio = await next_folio(db, tenant_id=tenant_id, prefix="INC")
    i = Issue(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=body.title, description=body.description, type=body.type,
        priority=body.priority, committed_date=body.committed_date,
        owner_id=str(body.owner_id) if body.owner_id else None,
        owner_actor_id=str(body.owner_actor_id) if body.owner_actor_id else None,
        area_id=str(body.area_id),
        status=body.status, reported_at=datetime.now(UTC),
        comments=[], created_by=cu.id,
    )
    db.add(i)
    await db.flush()
    await write_audit(
        db, action="issue.create", module="issues", user_id=cu.id, tenant_id=tenant_id,
        entity_type="issue", entity_id=str(i.id), details={"folio": folio},
    )
    await db.commit()
    _attach_area(i, area)
    await _attach_owners(db, [i])
    return IssueRead.model_validate(i)


@issues_router.get("/issues/{issue_id}", response_model=IssueRead)
async def get_issue(
    issue_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-065: detalle de un issue (acción/incidente/decisión)."""
    tenant_id = _tenant(cu)
    row = (
        await db.execute(
            select(Issue, Area)
            .outerjoin(Area, Area.id == Issue.area_id)
            .where(
                Issue.id == str(issue_id),
                Issue.tenant_id == str(tenant_id),
                Issue.deleted_at.is_(None),
            )
        )
    ).one_or_none()
    if row is None:
        raise not_found("Issue")
    i, area = row
    _attach_area(i, area)
    await _attach_comment_authors(db, [i])
    await _attach_owners(db, [i])
    return IssueRead.model_validate(i)


@issues_router.post("/issues/{issue_id}/comments", response_model=IssueRead)
async def add_issue_comment(
    issue_id: UUID,
    body: IssueComment,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    i = (await db.execute(select(Issue).where(Issue.id == str(issue_id), Issue.tenant_id == str(tenant_id)))).scalar_one_or_none()
    if i is None:
        raise not_found("Incidencia")
    comments = list(i.comments or [])
    comments.append({
        "text": body.text, "author_id": str(cu.id),
        "created_at": datetime.now(UTC).isoformat(),
    })
    i.comments = comments
    await db.commit()
    area = None
    if i.area_id:
        area = (
            await db.execute(select(Area).where(Area.id == i.area_id))
        ).scalar_one_or_none()
    _attach_area(i, area)
    await _attach_comment_authors(db, [i])
    await _attach_owners(db, [i])
    return IssueRead.model_validate(i)


@issues_router.patch("/issues/{issue_id}", response_model=IssueRead)
async def update_issue(
    issue_id: UUID,
    body: IssueUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    i = (await db.execute(select(Issue).where(Issue.id == str(issue_id), Issue.tenant_id == str(tenant_id)))).scalar_one_or_none()
    if i is None:
        raise not_found("Incidencia")
    data = body.model_dump(exclude_none=True)
    if "owner_id" in data and data["owner_id"] is not None:
        data["owner_id"] = str(data["owner_id"])
    if "owner_actor_id" in data and data["owner_actor_id"] is not None:
        data["owner_actor_id"] = str(data["owner_actor_id"])
    # US-064: si cambia area_id en PATCH, validar pertenencia.
    if "area_id" in data and data["area_id"] is not None:
        await _validate_area(db, data["area_id"], UUID(i.project_id), tenant_id)
        data["area_id"] = str(data["area_id"])
    for k, v in data.items():
        setattr(i, k, v)
    await db.commit()
    area = None
    if i.area_id:
        area = (
            await db.execute(select(Area).where(Area.id == i.area_id))
        ).scalar_one_or_none()
    _attach_area(i, area)
    await _attach_comment_authors(db, [i])
    await _attach_owners(db, [i])
    return IssueRead.model_validate(i)


@issues_router.delete("/issues/{issue_id}", status_code=204)
async def delete_issue(
    issue_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-112: soft-delete de un incidente/acción/decisión (RAID). Cualquier
    miembro del proyecto puede borrarlo. Las listas ya filtran deleted_at."""
    from fastapi.responses import Response

    tenant_id = _tenant(cu)
    i = (await db.execute(select(Issue).where(Issue.id == str(issue_id), Issue.tenant_id == str(tenant_id), Issue.deleted_at.is_(None)))).scalar_one_or_none()
    if i is None:
        raise not_found("Incidencia")
    i.deleted_at = datetime.now(UTC)
    await write_audit(
        db, action="issue.delete", module="issues", user_id=cu.id,
        tenant_id=tenant_id, entity_type="issue", entity_id=str(i.id),
    )
    await db.commit()
    return Response(status_code=204)


# ========== CHANGE REQUESTS ==========
chg_router = APIRouter(tags=["change_requests"])


@chg_router.get("/projects/{project_id}/change-requests", response_model=list[ChangeRequestRead])
async def list_chgs(
    project_id: UUID,
    status: list[str] | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    stmt = select(ChangeRequest).where(
        ChangeRequest.project_id == str(project_id), ChangeRequest.deleted_at.is_(None)
    )
    if status:
        stmt = stmt.where(ChangeRequest.status.in_(status))
    rows = (await db.execute(stmt.order_by(ChangeRequest.requested_at.desc()))).scalars().all()
    await _attach_change_users(db, rows)
    return [ChangeRequestRead.model_validate(c) for c in rows]


@chg_router.post("/projects/{project_id}/change-requests", response_model=ChangeRequestRead, status_code=201)
async def create_chg(
    project_id: UUID,
    body: ChangeRequestCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    _ensure_editable(p)
    folio = await next_folio(db, tenant_id=tenant_id, prefix="CHG")
    c = ChangeRequest(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=body.title, description=body.description, type=body.type,
        impact=body.impact, status="in_review", requested_by=cu.id,
        requested_at=datetime.now(UTC), created_by=cu.id,
    )
    db.add(c)
    await db.flush()
    await write_audit(
        db, action="change_request.create", module="change_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="change_request",
        entity_id=str(c.id), details={"folio": folio},
    )
    await db.commit()
    await _attach_change_users(db, [c])
    return ChangeRequestRead.model_validate(c)


@chg_router.get("/change-requests/{chg_id}", response_model=ChangeRequestRead)
async def get_chg(
    chg_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-087: detalle de change request para la página dedicada."""
    tenant_id = _tenant(cu)
    c = (
        await db.execute(
            select(ChangeRequest).where(
                ChangeRequest.id == str(chg_id),
                ChangeRequest.tenant_id == str(tenant_id),
                ChangeRequest.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if c is None:
        raise not_found("Change request")
    await _attach_change_users(db, [c])
    return ChangeRequestRead.model_validate(c)


@chg_router.patch("/change-requests/{chg_id}", response_model=ChangeRequestRead)
async def update_chg(
    chg_id: UUID,
    body: ChangeRequestUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-087: edición transaccional desde la página dedicada.

    Permite editar title/description/impact mientras el status sigue
    `in_review`. La transición de status se sigue haciendo vía los
    endpoints `/approve` y `/reject` (single source of truth para
    auditoría de aprobaciones).
    """
    tenant_id = _tenant(cu)
    c = (
        await db.execute(
            select(ChangeRequest).where(
                ChangeRequest.id == str(chg_id),
                ChangeRequest.tenant_id == str(tenant_id),
                ChangeRequest.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if c is None:
        raise not_found("Change request")
    data = body.model_dump(exclude_none=True)
    # Status sigue gobernado por approve/reject — ignorar si llega.
    data.pop("status", None)
    for k, v in data.items():
        setattr(c, k, v)
    await write_audit(
        db, action="change_request.update", module="change_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="change_request",
        entity_id=str(c.id),
    )
    await db.commit()
    await _attach_change_users(db, [c])
    return ChangeRequestRead.model_validate(c)


@chg_router.post("/change-requests/{chg_id}/approve", response_model=ChangeRequestRead)
async def approve_chg(
    chg_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    c = (await db.execute(select(ChangeRequest).where(ChangeRequest.id == str(chg_id), ChangeRequest.tenant_id == str(tenant_id)))).scalar_one_or_none()
    if c is None:
        raise not_found("Change request")
    if c.status != "in_review":
        raise conflict("Transición inválida", code="STATE_TRANSITION")
    c.status = "approved"
    c.approved_by = cu.id
    c.approved_at = datetime.now(UTC)
    await db.commit()
    await _attach_change_users(db, [c])
    return ChangeRequestRead.model_validate(c)


@chg_router.post("/change-requests/{chg_id}/reject", response_model=ChangeRequestRead)
async def reject_chg(
    chg_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    c = (await db.execute(select(ChangeRequest).where(ChangeRequest.id == str(chg_id), ChangeRequest.tenant_id == str(tenant_id)))).scalar_one_or_none()
    if c is None:
        raise not_found("Change request")
    if c.status != "in_review":
        raise conflict("Transición inválida", code="STATE_TRANSITION")
    c.status = "rejected"
    c.approved_by = cu.id
    c.approved_at = datetime.now(UTC)
    await db.commit()
    await _attach_change_users(db, [c])
    return ChangeRequestRead.model_validate(c)


async def _invalidate_change_tokens(db: AsyncSession, change_id: str) -> None:
    """ENH-112: invalida los tokens de aprobación vivos (EP019) de un cambio
    al cancelarlo/borrarlo, para que no queden links de aprobación activos
    apuntando a un cambio terminado. Mismo patrón que post_approval_decision."""
    from app.models.change_approval import ApprovalToken

    live = (
        await db.execute(
            select(ApprovalToken).where(
                ApprovalToken.change_id == change_id,
                ApprovalToken.consumed_at.is_(None),
            )
        )
    ).scalars().all()
    now = datetime.now(UTC)
    for tk in live:
        tk.consumed_at = now
        tk.action_taken = "invalidated"


@chg_router.post("/change-requests/{chg_id}/cancel", response_model=ChangeRequestRead)
async def cancel_chg(
    chg_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-112: cancela un cambio (status='cancelled'). A diferencia de
    borrar, queda visible para trazabilidad de aprobaciones (EP019). Cualquier
    miembro puede cancelar mientras el cambio no esté implementado/cancelado."""
    tenant_id = _tenant(cu)
    c = (await db.execute(select(ChangeRequest).where(ChangeRequest.id == str(chg_id), ChangeRequest.tenant_id == str(tenant_id), ChangeRequest.deleted_at.is_(None)))).scalar_one_or_none()
    if c is None:
        raise not_found("Change request")
    if c.status in ("implemented", "cancelled"):
        raise conflict("Transición inválida", code="STATE_TRANSITION")
    c.status = "cancelled"
    await _invalidate_change_tokens(db, str(c.id))
    await write_audit(
        db, action="change_request.cancel", module="change_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="change_request",
        entity_id=str(c.id),
    )
    await db.commit()
    await _attach_change_users(db, [c])
    return ChangeRequestRead.model_validate(c)


@chg_router.delete("/change-requests/{chg_id}", status_code=204)
async def delete_chg(
    chg_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-112: soft-delete de un cambio. Para preservar la auditoría de
    aprobaciones suele preferirse cancelar; borrar lo retira de la lista."""
    from fastapi.responses import Response

    tenant_id = _tenant(cu)
    c = (await db.execute(select(ChangeRequest).where(ChangeRequest.id == str(chg_id), ChangeRequest.tenant_id == str(tenant_id), ChangeRequest.deleted_at.is_(None)))).scalar_one_or_none()
    if c is None:
        raise not_found("Change request")
    c.deleted_at = datetime.now(UTC)
    await _invalidate_change_tokens(db, str(c.id))
    await write_audit(
        db, action="change_request.delete", module="change_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="change_request",
        entity_id=str(c.id),
    )
    await db.commit()
    return Response(status_code=204)


# ========== DOCUMENTS ==========
docs_router = APIRouter(tags=["documents"])


@docs_router.post("/projects/{project_id}/documents", response_model=DocumentRead, status_code=201)
async def upload_document(
    project_id: UUID,
    body: DocumentCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    _ensure_editable(p, allow_after_closed=True)
    if body.mime_type not in ALLOWED_DOC_MIME:
        from fastapi import HTTPException

        raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_MEDIA_TYPE"})
    if body.size_bytes > MAX_DOC_SIZE:
        from fastapi import HTTPException

        raise HTTPException(status_code=413, detail={"code": "PAYLOAD_TOO_LARGE"})

    # Versionado: si existe mismo title + category, incrementa.
    # BUG-078: (project_id, title, category, is_current) no es único — puede
    # quedar >1 fila marcada is_current (carreras de subida / datos legacy) y
    # scalar_one_or_none() reventaba con MultipleResultsFound (500 al subir).
    # Traemos todas las vigentes, las desmarcamos y versionamos desde el
    # máximo para dejar una sola is_current.
    current_docs = (
        await db.execute(
            select(Document).where(
                Document.project_id == str(project_id),
                Document.title == body.title,
                Document.category == (body.category or "other"),
                Document.is_current.is_(True),
            )
        )
    ).scalars().all()
    version = 1
    if current_docs:
        version = max(d_old.version for d_old in current_docs) + 1
        for d_old in current_docs:
            d_old.is_current = False

    folio = await next_folio(db, tenant_id=tenant_id, prefix="DOC")
    d = Document(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=body.title, description=body.description, category=body.category or "other",
        file_url=body.file_url, mime_type=body.mime_type, size_bytes=body.size_bytes,
        version=version, is_current=True, uploaded_by=cu.id, uploaded_at=datetime.now(UTC),
        status="active", created_by=cu.id,
    )
    db.add(d)
    await db.flush()
    await write_audit(
        db, action="document.upload", module="documents",
        user_id=cu.id, tenant_id=tenant_id, entity_type="document",
        entity_id=str(d.id), details={"folio": folio, "version": version},
    )
    await db.commit()
    return DocumentRead.model_validate(d)


@docs_router.post("/projects/{project_id}/documents/upload", response_model=DocumentRead, status_code=201)
async def upload_document_file(
    project_id: UUID,
    title: str = Query(..., min_length=2, max_length=200),
    description: str | None = Query(default=None),
    category: str | None = Query(default="other"),
    file: UploadFile = File(...),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file and create a document entry with versioning."""
    from app.schemas.modules import DOCUMENT_CATEGORIES

    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    _ensure_editable(p, allow_after_closed=True)

    cat = category if category in DOCUMENT_CATEGORIES else "other"

    # BUG-078: ver upload_document — (project_id, title, category, is_current)
    # no es único; tolerar duplicados en lugar de reventar con
    # MultipleResultsFound.
    current_docs = (
        await db.execute(
            select(Document).where(
                Document.project_id == str(project_id),
                Document.title == title,
                Document.category == cat,
                Document.is_current.is_(True),
            )
        )
    ).scalars().all()
    version = 1
    if current_docs:
        version = max(d_old.version for d_old in current_docs) + 1
        for d_old in current_docs:
            d_old.is_current = False

    folio = await next_folio(db, tenant_id=tenant_id, prefix="DOC")
    d = Document(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=title, description=description, category=cat,
        file_url="", mime_type="", size_bytes=0,
        version=version, is_current=True, uploaded_by=cu.id, uploaded_at=datetime.now(UTC),
        status="active", created_by=cu.id,
    )
    db.add(d)
    await db.flush()

    file_url, mime_type = await save_document(
        str(tenant_id), str(project_id), file, str(d.id)
    )
    d.file_url = file_url
    d.mime_type = mime_type
    d.size_bytes = file.size or 0

    await write_audit(
        db, action="document.upload", module="documents",
        user_id=cu.id, tenant_id=tenant_id, entity_type="document",
        entity_id=str(d.id), details={"folio": folio, "version": version},
    )
    await db.commit()
    return DocumentRead.model_validate(d)


@docs_router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    project_id: UUID,
    include_versions: bool = Query(default=False),
    category: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    stmt = select(Document).where(
        Document.project_id == str(project_id), Document.deleted_at.is_(None)
    )
    if not include_versions:
        stmt = stmt.where(Document.is_current.is_(True))
    if category:
        stmt = stmt.where(Document.category == category)
    rows = (await db.execute(stmt.order_by(Document.created_at.desc()))).scalars().all()
    return [DocumentRead.model_validate(d) for d in rows]


@docs_router.patch("/documents/{doc_id}", response_model=DocumentRead)
async def update_document(
    doc_id: UUID,
    body: DocumentUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza metadata (title/description/category) sin tocar el archivo."""
    tenant_id = _tenant(cu)
    d = (
        await db.execute(
            select(Document).where(
                Document.id == str(doc_id),
                Document.tenant_id == str(tenant_id),
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if d is None:
        raise not_found("Documento")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(d, field, value)
    await write_audit(
        db,
        action="document.update",
        module="documents",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="document",
        entity_id=str(d.id),
    )
    await db.commit()
    return DocumentRead.model_validate(d)


@docs_router.get("/documents/{doc_id}/download-url")
async def get_document_download_url(
    doc_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """BUG-034: devuelve `{ url, expires_at, mode }` para que el frontend
    descargue el documento sin problemas de auth header en `<a href>`.

    - `mode="presigned"`: URL firmada de R2/S3 (5 min expiry). El
      frontend puede hacer `window.open(url)` directo.
    - `mode="stream"`: backend local — el frontend debe usar el
      endpoint `/download` con el token Bearer manual (fetch + blob).
    """
    from datetime import timedelta

    from app.core.config import settings
    from app.services.document_storage import get_document_presigned_url

    tenant_id = _tenant(cu)
    d = (
        await db.execute(
            select(Document).where(
                Document.id == str(doc_id),
                Document.tenant_id == str(tenant_id),
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if d is None:
        raise not_found("Documento")

    expires_in = 300
    # BUG-040: el filename de descarga debe preservar la extensión del
    # archivo subido. La extensión vive en el path R2 (`.{ext}` al final
    # del key) y se mapea desde el `mime_type` guardado.
    from app.services.document_storage import ALLOWED_DOC_MIMES
    raw_title = (d.title or str(d.id)).replace("/", "_")
    ext = ALLOWED_DOC_MIMES.get((d.mime_type or "").lower())
    if not ext and d.file_url:
        # Fallback: extraer ext del key si el mime_type quedó vacío.
        tail = d.file_url.rsplit(".", 1)
        ext = tail[1] if len(tail) == 2 else None
    filename_hint = f"{raw_title}.{ext}" if ext else raw_title
    if settings.STORAGE_BACKEND == "s3":
        url = get_document_presigned_url(
            str(tenant_id),
            str(d.project_id),
            str(d.id),
            expires_in=expires_in,
            download_filename=filename_hint,
        )
        if url is None:
            raise not_found("Archivo del documento")
        return {
            "mode": "presigned",
            "url": url,
            "expires_at": (
                datetime.now(UTC) + timedelta(seconds=expires_in)
            ).isoformat(),
        }
    # Backend local: stream protegido sigue funcionando con auth header.
    return {
        "mode": "stream",
        "url": f"/api/v1/documents/{d.id}/download",
        "expires_at": None,
    }


@docs_router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Download a document file.

    US-066: usa `StreamingResponse` con el iterator devuelto por
    `get_document_stream()`. Funciona igual con backend local
    (filesystem) y con backend S3 (boto3 stream). El cliente nunca
    sabe dónde está realmente almacenado el archivo.
    """
    from urllib.parse import quote

    from fastapi.responses import StreamingResponse

    from app.services.document_storage import get_document_stream

    tenant_id = _tenant(cu)
    d = (
        await db.execute(
            select(Document).where(
                Document.id == str(doc_id),
                Document.tenant_id == str(tenant_id),
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if d is None:
        raise not_found("Documento")

    result = get_document_stream(str(tenant_id), str(d.project_id), str(d.id))
    if result is None:
        raise not_found("Archivo del documento")
    iterator, ext = result

    # Filename con extensión correcta + escape RFC 5987 para acentos.
    safe_title = quote(d.title or f"document-{d.id}")
    filename = f"{d.title or d.id}.{ext}"
    return StreamingResponse(
        iterator,
        media_type=d.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"; '
                f"filename*=UTF-8''{safe_title}.{ext}"
            ),
        },
    )


# ========== LESSONS ==========
lessons_router = APIRouter(tags=["lessons"])


@lessons_router.get("/lessons", response_model=list[LessonRead])
async def list_lessons_cross(
    project_id: UUID | None = Query(default=None),
    organization_id: UUID | None = Query(default=None),
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Lesson).where(
        Lesson.tenant_id == str(tenant_id), Lesson.deleted_at.is_(None)
    )
    if project_id:
        stmt = stmt.where(Lesson.project_id == str(project_id))
    if category:
        stmt = stmt.where(Lesson.category == category)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Lesson.title).like(like),
                func.lower(Lesson.description).like(like),
                func.lower(Lesson.recommendation).like(like),
            )
        )
    rows = (await db.execute(stmt.order_by(Lesson.created_at.desc()))).scalars().all()
    if tag:
        rows = [r for r in rows if tag in (r.tags or [])]
    if organization_id:
        from app.models.project import Project

        project_ids = {
            str(p.id) for p in (
                await db.execute(
                    select(Project).where(
                        Project.organization_id == str(organization_id),
                        Project.tenant_id == tenant_id,
                    )
                )
            ).scalars().all()
        }
        rows = [r for r in rows if str(r.project_id) in project_ids]
    return [LessonRead.model_validate(r) for r in rows]


@lessons_router.get("/lessons/{lesson_id}", response_model=LessonRead)
async def get_lesson(
    lesson_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-086: detalle de lección para la página dedicada."""
    tenant_id = _tenant(cu)
    l = (
        await db.execute(
            select(Lesson).where(
                Lesson.id == str(lesson_id),
                Lesson.tenant_id == str(tenant_id),
                Lesson.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if l is None:
        raise not_found("Lección")
    return LessonRead.model_validate(l)


@lessons_router.patch("/lessons/{lesson_id}", response_model=LessonRead)
async def update_lesson(
    lesson_id: UUID,
    body: LessonUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-086: edición transaccional desde la página dedicada."""
    tenant_id = _tenant(cu)
    l = (
        await db.execute(
            select(Lesson).where(
                Lesson.id == str(lesson_id),
                Lesson.tenant_id == str(tenant_id),
                Lesson.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if l is None:
        raise not_found("Lección")
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(l, k, v)
    await write_audit(
        db, action="lesson.update", module="lessons",
        user_id=cu.id, tenant_id=tenant_id, entity_type="lesson", entity_id=str(l.id),
    )
    await db.commit()
    return LessonRead.model_validate(l)


@lessons_router.delete("/lessons/{lesson_id}", status_code=204)
async def delete_lesson(
    lesson_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-112: soft-delete de una lección aprendida. Cualquier miembro del
    proyecto puede borrarla; la lista ya filtra deleted_at."""
    from fastapi.responses import Response

    tenant_id = _tenant(cu)
    l = (
        await db.execute(
            select(Lesson).where(
                Lesson.id == str(lesson_id),
                Lesson.tenant_id == str(tenant_id),
                Lesson.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if l is None:
        raise not_found("Lección")
    l.deleted_at = datetime.now(UTC)
    await write_audit(
        db, action="lesson.delete", module="lessons",
        user_id=cu.id, tenant_id=tenant_id, entity_type="lesson", entity_id=str(l.id),
    )
    await db.commit()
    return Response(status_code=204)


@lessons_router.post("/projects/{project_id}/lessons", response_model=LessonRead, status_code=201)
async def create_lesson(
    project_id: UUID,
    body: LessonCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    # Lecciones se pueden crear incluso en proyecto cerrado
    await _get_project(db, project_id, tenant_id)
    folio = await next_folio(db, tenant_id=tenant_id, prefix="LEC")
    l = Lesson(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=body.title, description=body.description, category=body.category,
        phase=body.phase, recommendation=body.recommendation, tags=body.tags,
        status="published", created_by=cu.id,
    )
    db.add(l)
    await db.flush()
    await write_audit(
        db, action="lesson.create", module="lessons",
        user_id=cu.id, tenant_id=tenant_id, entity_type="lesson", entity_id=str(l.id),
    )
    await db.commit()
    return LessonRead.model_validate(l)


# ========== MEETING MINUTES ==========
minutes_router = APIRouter(tags=["minutes"])


@minutes_router.post("/projects/{project_id}/meeting-minutes", response_model=MeetingMinuteRead, status_code=201)
async def create_minute(
    project_id: UUID,
    body: MeetingMinuteCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    folio = await next_folio(db, tenant_id=tenant_id, prefix="MIN")
    # BUG-058 + BUG-063: sanitiza `raid_suggestions` al shape canónico
    # A/R/D/I (actions/risks/decisions/issues). Tolera el shape legacy
    # `{risks, issues, lessons, changes}` mapeando lessons/changes →
    # descartado silenciosamente (owner 2026-05-22: solo A/R/D/I).
    raid_in = body.raid_suggestions if isinstance(body.raid_suggestions, dict) else {}
    raid_persisted = {
        "actions": list(raid_in.get("actions") or []),
        "risks": list(raid_in.get("risks") or []),
        "decisions": list(raid_in.get("decisions") or []),
        "issues": list(raid_in.get("issues") or []),
    }
    # BUG-063: clientes legacy aún envían `lessons`/`changes`. Los
    # persistimos para que el auto-approve los materialice como Lesson/
    # ChangeRequest (el IA nuevo ya no los emite — validator los filtra).
    for legacy_kind in ("lessons", "changes"):
        if raid_in.get(legacy_kind):
            raid_persisted[legacy_kind] = list(raid_in[legacy_kind])
    # BUG-063: meta opcional con free_notes para evitar migración.
    meta = {}
    if body.free_notes:
        meta["free_notes"] = body.free_notes
    if meta:
        raid_persisted["_meta"] = meta
    # BUG-063: NO matching de participants. Owner pidió mantener la
    # generación de minuta enfocada en la minuta; cuando se creen RAIDs
    # asignamos a actores en otro flow. Aquí los persistimos tal y como
    # vienen del transcript (lista plana de dicts con name/role/area/
    # attendance opcional).
    m = MeetingMinute(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=body.title, meeting_date=body.meeting_date,
        participants=list(body.participants or []),
        topics=body.topics, agreements=body.agreements,
        next_meeting_date=body.next_meeting_date, attachments=body.attachments,
        transcript_file_id=body.transcript_file_id, generated_by_ai=body.generated_by_ai,
        status="final", created_by=cu.id,
        # ENH-106: campo audit-only. Si el body declara `generated_by_ai=True`
        # y origin sigue siendo el default `manual`, lo corregimos a
        # `transcript_ai` para mantener consistencia con el backfill.
        origin=(
            "transcript_ai" if body.generated_by_ai and body.origin == "manual" else body.origin
        ),
        raid_suggestions=raid_persisted,
        description=body.summary,
    )
    db.add(m)
    await db.flush()

    # BUG-061: si el cliente pidió auto-aprobar (default), creamos los
    # tickets RAID en la misma transacción para items con
    # `status="pending"`. Items con `status="discarded"` (desmarcados en
    # el preview por el PM) NO se crean. El JSON de raid_suggestions
    # queda con `status="approved"` + `ticket_id` para los aprobados,
    # `status="discarded"` para los descartados.
    approved_count = 0
    if body.auto_approve_raid:
        suggestions = dict(m.raid_suggestions or {})
        # BUG-063: 4 nuevos canónicos + 2 legacy (lessons/changes) para
        # retro-compat con clientes pre-refactor. El IA ya no genera
        # lessons/changes (validator los descarta), pero un POST manual
        # con esos buckets sigue funcionando.
        for kind in ("actions", "risks", "decisions", "issues", "lessons", "changes"):
            bucket = list(suggestions.get(kind) or [])
            for idx, raw in enumerate(bucket):
                sugg = dict(raw) if isinstance(raw, dict) else {}
                status = sugg.get("status") or "pending"
                if status != "pending":
                    bucket[idx] = sugg
                    continue
                short_desc = (sugg.get("short_desc") or "").strip()
                if not short_desc:
                    # Sin texto utilizable: lo dejamos descartado en lugar
                    # de fallar la creación entera de la minuta.
                    sugg["status"] = "discarded"
                    bucket[idx] = sugg
                    continue
                ticket_id, ticket_type = await _create_raid_ticket_from_suggestion(
                    db,
                    minute=m,
                    kind=kind,
                    sugg=sugg,
                    override_short_desc=None,
                    override_description=None,
                    override_priority=None,
                    cu=cu,
                    tenant_id=tenant_id,
                )
                sugg["status"] = "approved"
                sugg["ticket_id"] = ticket_id
                sugg["ticket_type"] = ticket_type
                bucket[idx] = sugg
                approved_count += 1
            suggestions[kind] = bucket
        m.raid_suggestions = suggestions

    await write_audit(
        db, action="meeting_minute.create", module="minutes",
        user_id=cu.id, tenant_id=tenant_id, entity_type="meeting_minute", entity_id=str(m.id),
        details={"auto_approved_raid": approved_count} if approved_count else None,
    )
    await db.commit()
    await db.refresh(m)
    return MeetingMinuteRead.model_validate(m)


@minutes_router.get("/projects/{project_id}/meeting-minutes", response_model=list[MeetingMinuteRead])
async def list_minutes(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    rows = (
        await db.execute(
            select(MeetingMinute)
            .where(MeetingMinute.project_id == str(project_id), MeetingMinute.deleted_at.is_(None))
            .order_by(MeetingMinute.meeting_date.desc())
        )
    ).scalars().all()
    return [MeetingMinuteRead.model_validate(m) for m in rows]


@minutes_router.get("/meeting-minutes/{minute_id}/render-html")
async def render_minute_html_endpoint(
    minute_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-090 + US-111 CA6: HTML standalone de la minuta para preview
    in-platform (iframe) o export. Reusa el renderer de US-111."""
    from fastapi.responses import Response as _Resp

    from app.services.html_report_renderer import render_minute_html
    from app.services.reports.branding import load_report_branding

    tenant_id = _tenant(cu)
    m = (
        await db.execute(
            select(MeetingMinute).where(
                MeetingMinute.id == str(minute_id),
                MeetingMinute.tenant_id == str(tenant_id),
                MeetingMinute.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise not_found("Minuta")
    project = (
        await db.execute(select(Project).where(Project.id == str(m.project_id)))
    ).scalar_one_or_none()
    brand = await load_report_branding(
        db, tenant_id, project.organization_id if project else None
    )
    html = render_minute_html(
        title=m.title,
        project_name=project.name if project else "",
        project_folio=project.folio if project else "",
        meeting_date=m.meeting_date,
        summary="",
        participants=list(m.participants or []),
        topics=list(m.topics or []),
        agreements=list(m.agreements or []),
        raid_suggestions=dict(m.raid_suggestions or {}),
        **brand,
    )
    return _Resp(content=html, media_type="text/html; charset=utf-8")


@minutes_router.get("/meeting-minutes/{minute_id}/export")
async def export_minute(
    minute_id: UUID,
    format: str = Query(default="pdf", pattern="^(pdf|docx|md|txt|html)$"),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Exporta la minuta en el formato estandarizado (US-040).

    Formatos soportados: `pdf` (WeasyPrint), `docx` (python-docx),
    `md`, `txt`, `html` (ENH-089 — primario; standalone con filtros
    embebidos). Las acciones del RAID vienen agrupadas por área /
    responsable.
    """
    from fastapi.responses import Response

    from app.models.tenant import Tenant
    from app.services.minutes_formatter import (
        build_view,
        to_docx,
        to_markdown,
        to_pdf,
        to_plain_text,
    )

    tenant_id = _tenant(cu)
    m = (
        await db.execute(
            select(MeetingMinute).where(
                MeetingMinute.id == str(minute_id),
                MeetingMinute.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise not_found("Minuta")
    project = (
        await db.execute(select(Project).where(Project.id == str(m.project_id)))
    ).scalar_one_or_none()
    view = build_view(m, project)

    base_name = (
        f"Minuta_{project.folio if project else 'MIN'}_"
        f"{(project and project.folio) or 'proyecto'}_{(m.meeting_date.date().isoformat() if m.meeting_date else 'fecha')}"
    )

    if format == "html":
        # ENH-089 CA1: HTML primario standalone (estilos inline, JS embebido).
        from app.services.html_report_renderer import render_minute_html
        from app.services.reports.branding import load_report_branding

        brand = await load_report_branding(
            db, tenant_id, project.organization_id if project else None
        )
        html_content = render_minute_html(
            title=m.title,
            project_name=project.name if project else "",
            project_folio=project.folio if project else "",
            meeting_date=m.meeting_date,
            summary="",
            participants=list(m.participants or []),
            topics=list(m.topics or []),
            agreements=list(m.agreements or []),
            raid_suggestions=dict(m.raid_suggestions or {}),
            **brand,
        )
        return Response(
            content=html_content.encode("utf-8"),
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{base_name}.html"',
            },
        )
    if format == "md":
        data = to_markdown(view).encode("utf-8")
        return Response(
            content=data,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.md"'},
        )
    if format == "txt":
        data = to_plain_text(view).encode("utf-8")
        return Response(
            content=data,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.txt"'},
        )
    if format == "docx":
        data = to_docx(view)
        return Response(
            content=data,
            media_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            headers={"Content-Disposition": f'attachment; filename="{base_name}.docx"'},
        )
    # pdf
    tenant_name = (
        await db.execute(select(Tenant.name).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    data = to_pdf(view, tenant_name=tenant_name)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{base_name}.pdf"'},
    )


@minutes_router.post("/meeting-minutes/{minute_id}/convert-agreement")
async def convert_agreement_to_issue(
    minute_id: UUID,
    agreement_index: int,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    m = (
        await db.execute(select(MeetingMinute).where(MeetingMinute.id == str(minute_id), MeetingMinute.tenant_id == str(tenant_id)))
    ).scalar_one_or_none()
    if m is None:
        raise not_found("Minuta")
    agreements = list(m.agreements or [])
    if agreement_index >= len(agreements):
        raise business_rule("Indice de acuerdo inválido")
    ag = agreements[agreement_index]
    folio = await next_folio(db, tenant_id=tenant_id, prefix="INC")
    issue = Issue(
        tenant_id=str(tenant_id), project_id=str(m.project_id), folio=folio,
        title=(ag.get("description") or "Acuerdo")[:200],
        description=ag.get("description"),
        type="action",
        priority=3,
        committed_date=date.fromisoformat(ag["due_date"]) if ag.get("due_date") else None,
        owner_id=ag.get("owner_id"),
        status="open",
        reported_at=datetime.now(UTC),
        comments=[],
        created_by=cu.id,
    )
    db.add(issue)
    await db.commit()
    return {"issue_id": str(issue.id), "folio": folio}


# ========== US-108 + ENH-090/091: minuta GET/PATCH/DELETE + approve RAID =========

# BUG-063: shape canónico A/R/D/I. Acciones y Decisiones se materializan
# como rows en `issues` con `type="action"|"decision"` (modelo Issue ya
# soporta los 3 sub-tipos via la columna `type`). Lecciones/Cambios
# legacy se mantienen para retro-compat con payloads previos al refactor.
_RAID_TYPE_TO_PREFIX = {
    "actions": "ACT",
    "risks": "RIS",
    "decisions": "DEC",
    "issues": "INC",
    "lessons": "LEC",
    "changes": "CHG",
}

_RAID_KIND_TO_ISSUE_TYPE = {
    "actions": "action",
    "decisions": "decision",
    "issues": "issue",
}


async def _create_raid_ticket_from_suggestion(
    db: AsyncSession,
    *,
    minute: "MeetingMinute",
    kind: str,
    sugg: dict,
    override_short_desc: str | None,
    override_description: str | None,
    override_priority: int | None,
    cu: CurrentUser,
    tenant_id: UUID,
) -> tuple[str, str]:
    """BUG-061 + BUG-063: helper compartido entre `create_minute` (auto-
    approve al guardar el preview) y `approve_raid_suggestions` (US-108
    editor). Crea el ticket en el módulo correspondiente y retorna
    ``(ticket_id, ticket_type)``. No actualiza ``sugg`` ni hace commit —
    eso queda al caller.

    Mapping:
    - ``actions`` → Issue(type=action), ticket_type=``action``.
    - ``risks`` → Risk, ticket_type=``risk``.
    - ``decisions`` → Issue(type=decision), ticket_type=``decision``.
    - ``issues`` → Issue(type=issue), ticket_type=``issue``.
    - ``lessons`` / ``changes`` → legacy, mantienen Lesson/ChangeRequest.
    """
    short_desc = (override_short_desc or sugg.get("short_desc") or "").strip()
    if not short_desc:
        raise business_rule(f"short_desc vacío en {kind}")
    title_value = short_desc[:200]
    description_value = (
        override_description or sugg.get("raw_quote") or sugg.get("short_desc") or None
    )
    priority_value = override_priority or sugg.get("suggested_priority") or 3
    prefix = _RAID_TYPE_TO_PREFIX.get(kind, "INC")
    folio = await next_folio(db, tenant_id=tenant_id, prefix=prefix)

    if kind == "risks":
        r = Risk(
            tenant_id=str(tenant_id), project_id=str(minute.project_id), folio=folio,
            title=title_value, description=description_value,
            category=None, owner_id=None, area_id=None,
            probability=int(priority_value) if priority_value else 3,
            impact=int(priority_value) if priority_value else 3,
            severity=(int(priority_value) ** 2) if priority_value else 9,
            mitigation_strategy=None, status="identified",
            identified_at=datetime.now(UTC).date(),
            due_date=None, closure_note=None, comments=[], created_by=cu.id,
        )
        db.add(r)
        await db.flush()
        return str(r.id), "risk"
    if kind in _RAID_KIND_TO_ISSUE_TYPE:
        issue_type = _RAID_KIND_TO_ISSUE_TYPE[kind]
        issue = Issue(
            tenant_id=str(tenant_id), project_id=str(minute.project_id), folio=folio,
            title=title_value, description=description_value,
            type=issue_type, priority=int(priority_value) if priority_value else 3,
            committed_date=None, owner_id=None, area_id=None,
            status="open", reported_at=datetime.now(UTC),
            comments=[], created_by=cu.id,
        )
        db.add(issue)
        await db.flush()
        return str(issue.id), issue_type
    if kind == "lessons":
        lesson = Lesson(
            tenant_id=str(tenant_id), project_id=str(minute.project_id), folio=folio,
            title=title_value, description=description_value,
            category="improvement", phase=None,
            recommendation=None, tags=[], status="published", created_by=cu.id,
        )
        db.add(lesson)
        await db.flush()
        return str(lesson.id), "lesson"
    chg = ChangeRequest(
        tenant_id=str(tenant_id), project_id=str(minute.project_id), folio=folio,
        title=title_value, description=description_value,
        type="scope", impact=None, status="in_review",
        requested_by=cu.id, requested_at=datetime.now(UTC), created_by=cu.id,
    )
    db.add(chg)
    await db.flush()
    return str(chg.id), "change_request"


@minutes_router.get("/meeting-minutes/{minute_id}", response_model=MeetingMinuteRead)
async def get_minute(
    minute_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-090: detalle de una minuta para el preview in-platform."""
    tenant_id = _tenant(cu)
    m = (
        await db.execute(
            select(MeetingMinute).where(
                MeetingMinute.id == str(minute_id),
                MeetingMinute.tenant_id == str(tenant_id),
                MeetingMinute.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise not_found("Minuta")
    return MeetingMinuteRead.model_validate(m)


@minutes_router.patch("/meeting-minutes/{minute_id}", response_model=MeetingMinuteRead)
async def update_minute(
    minute_id: UUID,
    body: MeetingMinuteUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-108: persiste cambios en `raid_suggestions` (descarte / edit
    inline) y/o título. El array completo viene del cliente y reemplaza
    al actual — el cliente es responsable de preservar el shape.
    """
    tenant_id = _tenant(cu)
    m = (
        await db.execute(
            select(MeetingMinute).where(
                MeetingMinute.id == str(minute_id),
                MeetingMinute.tenant_id == str(tenant_id),
                MeetingMinute.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise not_found("Minuta")
    data = body.model_dump(exclude_none=True)
    if "raid_suggestions" in data and isinstance(data["raid_suggestions"], dict):
        m.raid_suggestions = data["raid_suggestions"]
    if "title" in data:
        m.title = data["title"]
    # BUG-063: summary, meeting_date y free_notes editables.
    if "summary" in data:
        m.description = data["summary"]
    if "meeting_date" in data:
        m.meeting_date = data["meeting_date"]
    # ENH-095: secciones estructuradas editables desde el preview.
    if "participants" in data and isinstance(data["participants"], list):
        m.participants = data["participants"]
    if "topics" in data and isinstance(data["topics"], list):
        m.topics = data["topics"]
    if "agreements" in data and isinstance(data["agreements"], list):
        m.agreements = data["agreements"]
    if "free_notes" in data:
        # BUG-063: persistido en `raid_suggestions._meta.free_notes` para
        # evitar migración. El formatter ignora keys con `_` prefix y
        # consume `_meta` solo donde corresponde.
        rs = dict(m.raid_suggestions or {})
        meta = dict(rs.get("_meta") or {})
        if data["free_notes"]:
            meta["free_notes"] = data["free_notes"]
        else:
            meta.pop("free_notes", None)
        rs["_meta"] = meta
        m.raid_suggestions = rs
    await write_audit(
        db, action="meeting_minute.update", module="minutes",
        user_id=cu.id, tenant_id=tenant_id, entity_type="meeting_minute",
        entity_id=str(m.id),
    )
    await db.commit()
    await db.refresh(m)
    return MeetingMinuteRead.model_validate(m)


@minutes_router.delete("/meeting-minutes/{minute_id}", status_code=204)
async def delete_minute(
    minute_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-091: borra físicamente una minuta. Solo el creador o un admin
    del proyecto puede borrarla (CA3). Tickets RAID generados por la
    minuta NO se eliminan — solo se rompe el link de origen (CA5).
    """
    tenant_id = _tenant(cu)
    m = (
        await db.execute(
            select(MeetingMinute).where(
                MeetingMinute.id == str(minute_id),
                MeetingMinute.tenant_id == str(tenant_id),
                MeetingMinute.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise not_found("Minuta")
    is_creator = str(m.created_by) == str(cu.id) if m.created_by else False
    is_admin = bool(getattr(cu, "is_admin", False)) or bool(
        getattr(cu, "is_superadmin", False)
    )
    if not (is_creator or is_admin):
        raise forbidden("Solo el creador o un admin puede borrar la minuta")
    await write_audit(
        db, action="meeting_minute.delete", module="minutes",
        user_id=cu.id, tenant_id=tenant_id, entity_type="meeting_minute",
        entity_id=str(m.id),
        details={"folio": m.folio, "title": m.title},
    )
    await db.delete(m)
    await db.commit()
    return None


@minutes_router.post(
    "/meeting-minutes/{minute_id}/approve-raid-suggestions",
    response_model=MeetingMinuteRead,
)
async def approve_raid_suggestions(
    minute_id: UUID,
    body: RaidApproveBatch,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-108: bulk-aprueba sugerencias RAID y crea los tickets reales
    en el módulo correspondiente. Los items aprobados quedan marcados
    con `status: approved` + `ticket_id` para auditoría.

    Idempotencia: items ya aprobados (`status == "approved"`) se ignoran
    silenciosamente — no se duplican tickets si el cliente reintenta.
    """
    tenant_id = _tenant(cu)
    m = (
        await db.execute(
            select(MeetingMinute).where(
                MeetingMinute.id == str(minute_id),
                MeetingMinute.tenant_id == str(tenant_id),
                MeetingMinute.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise not_found("Minuta")

    suggestions = dict(m.raid_suggestions or {})
    for kind in ("actions", "risks", "decisions", "issues", "lessons", "changes"):
        suggestions.setdefault(kind, [])

    for it in body.items:
        bucket = suggestions.get(it.type) or []
        if not (0 <= it.index < len(bucket)):
            raise business_rule(
                f"Indice {it.index} inválido para {it.type}",
            )
        sugg = dict(bucket[it.index])
        if sugg.get("status") == "approved" and sugg.get("ticket_id"):
            # Idempotencia: ya creado, no se duplica.
            continue
        ticket_id, ticket_type = await _create_raid_ticket_from_suggestion(
            db,
            minute=m,
            kind=it.type,
            sugg=sugg,
            override_short_desc=it.short_desc,
            override_description=it.description,
            override_priority=it.priority,
            cu=cu,
            tenant_id=tenant_id,
        )
        sugg["status"] = "approved"
        sugg["ticket_id"] = ticket_id
        sugg["ticket_type"] = ticket_type
        if it.short_desc:
            sugg["short_desc"] = it.short_desc.strip()
        bucket[it.index] = sugg
        suggestions[it.type] = bucket

    m.raid_suggestions = suggestions
    await write_audit(
        db, action="meeting_minute.approve_raid_suggestions", module="minutes",
        user_id=cu.id, tenant_id=tenant_id, entity_type="meeting_minute",
        entity_id=str(m.id),
        details={"approved_count": len(body.items)},
    )
    await db.commit()
    await db.refresh(m)
    return MeetingMinuteRead.model_validate(m)
