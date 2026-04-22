from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import business_rule, conflict, forbidden, not_found
from app.db.session import get_db
from app.models.modules import (
    ChangeRequest,
    Document,
    Issue,
    Lesson,
    MeetingMinute,
    Risk,
)
from app.models.project import Project
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
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


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


# ========== RISKS ==========
risks_router = APIRouter(tags=["risks"])


@risks_router.get("/projects/{project_id}/risks", response_model=list[RiskRead])
async def list_risks(
    project_id: UUID,
    status: list[str] | None = Query(default=None),
    severity_min: int | None = Query(default=None, ge=1, le=25),
    severity_max: int | None = Query(default=None, ge=1, le=25),
    q: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("risks", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    stmt = select(Risk).where(Risk.project_id == str(project_id), Risk.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Risk.status.in_(status))
    if severity_min is not None:
        stmt = stmt.where(Risk.severity >= severity_min)
    if severity_max is not None:
        stmt = stmt.where(Risk.severity <= severity_max)
    if q:
        stmt = stmt.where(func.lower(Risk.title).like(f"%{q.lower()}%"))
    rows = (await db.execute(stmt.order_by(Risk.severity.desc()))).scalars().all()
    return [RiskRead.model_validate(r) for r in rows]


@risks_router.post("/projects/{project_id}/risks", response_model=RiskRead, status_code=201)
async def create_risk(
    project_id: UUID,
    body: RiskCreate,
    cu: CurrentUser = Depends(require_permission("risks", "create")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    _ensure_editable(p)
    folio = await next_folio(db, tenant_id=tenant_id, prefix="RIS")
    severity = (body.probability or 0) * (body.impact or 0)
    r = Risk(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=body.title, description=body.description, category=body.category,
        probability=body.probability, impact=body.impact, severity=severity,
        mitigation_strategy=body.mitigation_strategy,
        owner_id=str(body.owner_id) if body.owner_id else None,
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
    return RiskRead.model_validate(r)


@risks_router.patch("/risks/{risk_id}", response_model=RiskRead)
async def update_risk(
    risk_id: UUID,
    body: RiskUpdate,
    cu: CurrentUser = Depends(require_permission("risks", "update")),
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
    for k, v in data.items():
        setattr(r, k, v)
    if data.get("probability") or data.get("impact"):
        r.severity = (r.probability or 0) * (r.impact or 0)
    await write_audit(
        db, action="risk.update", module="risks", user_id=cu.id, tenant_id=tenant_id,
        entity_type="risk", entity_id=str(r.id),
    )
    await db.commit()
    return RiskRead.model_validate(r)


@risks_router.delete("/risks/{risk_id}", status_code=204)
async def delete_risk(
    risk_id: UUID,
    cu: CurrentUser = Depends(require_permission("risks", "delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    r = (await db.execute(select(Risk).where(Risk.id == str(risk_id), Risk.tenant_id == str(tenant_id)))).scalar_one_or_none()
    if r is None:
        raise not_found("Riesgo")
    r.deleted_at = datetime.now(UTC)
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
    cu: CurrentUser = Depends(require_permission("issues", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    stmt = select(Issue).where(Issue.project_id == str(project_id), Issue.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Issue.status.in_(status))
    if type:
        stmt = stmt.where(Issue.type == type)
    if overdue:
        stmt = stmt.where(
            Issue.committed_date < date.today(),
            Issue.status.notin_(["resolved", "closed"]),
        )
    rows = (await db.execute(stmt.order_by(Issue.reported_at.desc()))).scalars().all()
    return [IssueRead.model_validate(i) for i in rows]


@issues_router.post("/projects/{project_id}/issues", response_model=IssueRead, status_code=201)
async def create_issue(
    project_id: UUID,
    body: IssueCreate,
    cu: CurrentUser = Depends(require_permission("issues", "create")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    _ensure_editable(p)
    folio = await next_folio(db, tenant_id=tenant_id, prefix="INC")
    i = Issue(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=body.title, description=body.description, type=body.type,
        priority=body.priority, committed_date=body.committed_date,
        owner_id=str(body.owner_id) if body.owner_id else None,
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
    return IssueRead.model_validate(i)


@issues_router.post("/issues/{issue_id}/comments", response_model=IssueRead)
async def add_issue_comment(
    issue_id: UUID,
    body: IssueComment,
    cu: CurrentUser = Depends(require_permission("issues", "update")),
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
    return IssueRead.model_validate(i)


@issues_router.patch("/issues/{issue_id}", response_model=IssueRead)
async def update_issue(
    issue_id: UUID,
    body: IssueUpdate,
    cu: CurrentUser = Depends(require_permission("issues", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    i = (await db.execute(select(Issue).where(Issue.id == str(issue_id), Issue.tenant_id == str(tenant_id)))).scalar_one_or_none()
    if i is None:
        raise not_found("Incidencia")
    data = body.model_dump(exclude_none=True)
    if "owner_id" in data and data["owner_id"] is not None:
        data["owner_id"] = str(data["owner_id"])
    for k, v in data.items():
        setattr(i, k, v)
    await db.commit()
    return IssueRead.model_validate(i)


# ========== CHANGE REQUESTS ==========
chg_router = APIRouter(tags=["change_requests"])


@chg_router.get("/projects/{project_id}/change-requests", response_model=list[ChangeRequestRead])
async def list_chgs(
    project_id: UUID,
    status: list[str] | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("change_requests", "read")),
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
    return [ChangeRequestRead.model_validate(c) for c in rows]


@chg_router.post("/projects/{project_id}/change-requests", response_model=ChangeRequestRead, status_code=201)
async def create_chg(
    project_id: UUID,
    body: ChangeRequestCreate,
    cu: CurrentUser = Depends(require_permission("change_requests", "create")),
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
    return ChangeRequestRead.model_validate(c)


@chg_router.post("/change-requests/{chg_id}/approve", response_model=ChangeRequestRead)
async def approve_chg(
    chg_id: UUID,
    cu: CurrentUser = Depends(require_permission("change_requests", "approve")),
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
    return ChangeRequestRead.model_validate(c)


@chg_router.post("/change-requests/{chg_id}/reject", response_model=ChangeRequestRead)
async def reject_chg(
    chg_id: UUID,
    cu: CurrentUser = Depends(require_permission("change_requests", "approve")),
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
    return ChangeRequestRead.model_validate(c)


# ========== DOCUMENTS ==========
docs_router = APIRouter(tags=["documents"])


@docs_router.post("/projects/{project_id}/documents", response_model=DocumentRead, status_code=201)
async def upload_document(
    project_id: UUID,
    body: DocumentCreate,
    cu: CurrentUser = Depends(require_permission("documents", "upload")),
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

    # Versionado: si existe mismo title + category, incrementa
    existing = (
        await db.execute(
            select(Document).where(
                Document.project_id == str(project_id),
                Document.title == body.title,
                Document.category == (body.category or "other"),
                Document.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    version = 1
    if existing is not None:
        version = existing.version + 1
        existing.is_current = False

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
    cu: CurrentUser = Depends(require_permission("documents", "upload")),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file and create a document entry with versioning."""
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    _ensure_editable(p, allow_after_closed=True)

    from app.schemas.modules import DocumentCategory

    try:
        cat = DocumentCategory(category or "other")
    except (ValueError, KeyError):
        cat = DocumentCategory.other

    file_url, mime_type = await save_document(str(tenant_id), str(project_id), file)

    existing = (
        await db.execute(
            select(Document).where(
                Document.project_id == str(project_id),
                Document.title == title,
                Document.category == cat,
                Document.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()
    version = 1
    if existing is not None:
        version = existing.version + 1
        existing.is_current = False

    folio = await next_folio(db, tenant_id=tenant_id, prefix="DOC")
    d = Document(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=title, description=description, category=cat,
        file_url=file_url, mime_type=mime_type, size_bytes=file.size or 0,
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


@docs_router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    project_id: UUID,
    include_versions: bool = Query(default=False),
    category: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("documents", "read")),
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
    cu: CurrentUser = Depends(require_permission("documents", "update")),
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


@docs_router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    cu: CurrentUser = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Download a document file."""
    from app.services.document_storage import get_document_path

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

    file_path = get_document_path(str(tenant_id), str(d.project_id), str(d.id))
    if file_path is None:
        raise not_found("Archivo del documento")

    return FileResponse(file_path, media_type=d.mime_type, filename=f"{d.title}")


# ========== LESSONS ==========
lessons_router = APIRouter(tags=["lessons"])


@lessons_router.get("/lessons", response_model=list[LessonRead])
async def list_lessons_cross(
    project_id: UUID | None = Query(default=None),
    organization_id: UUID | None = Query(default=None),
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("lessons", "read")),
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


@lessons_router.post("/projects/{project_id}/lessons", response_model=LessonRead, status_code=201)
async def create_lesson(
    project_id: UUID,
    body: LessonCreate,
    cu: CurrentUser = Depends(require_permission("lessons", "create")),
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
    cu: CurrentUser = Depends(require_permission("minutes", "create")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    folio = await next_folio(db, tenant_id=tenant_id, prefix="MIN")
    m = MeetingMinute(
        tenant_id=str(tenant_id), project_id=str(project_id), folio=folio,
        title=body.title, meeting_date=body.meeting_date, participants=body.participants,
        topics=body.topics, agreements=body.agreements,
        next_meeting_date=body.next_meeting_date, attachments=body.attachments,
        transcript_file_id=body.transcript_file_id, generated_by_ai=body.generated_by_ai,
        status="final", created_by=cu.id,
    )
    db.add(m)
    await db.flush()
    await write_audit(
        db, action="meeting_minute.create", module="minutes",
        user_id=cu.id, tenant_id=tenant_id, entity_type="meeting_minute", entity_id=str(m.id),
    )
    await db.commit()
    return MeetingMinuteRead.model_validate(m)


@minutes_router.get("/projects/{project_id}/meeting-minutes", response_model=list[MeetingMinuteRead])
async def list_minutes(
    project_id: UUID,
    cu: CurrentUser = Depends(require_permission("minutes", "read")),
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


@minutes_router.get("/meeting-minutes/{minute_id}/export")
async def export_minute(
    minute_id: UUID,
    format: str = Query(default="pdf", pattern="^(pdf|docx|md|txt)$"),
    cu: CurrentUser = Depends(require_permission("minutes", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Exporta la minuta en el formato estandarizado (US-040).

    Formatos soportados: `pdf` (WeasyPrint), `docx` (python-docx),
    `md`, `txt`. Las acciones del RAID vienen agrupadas por área /
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
    cu: CurrentUser = Depends(require_permission("minutes", "update")),
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
