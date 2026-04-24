from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import business_rule, forbidden, not_found, validation_error
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task, TaskDependency
from app.services.audit import write_audit
from app.services.msproject.mpp_parser import parse_mpp
from app.services.msproject.xml_parser import parse_ms_project_xml
from app.services.xlsx_task_parser import parse_xlsx

router = APIRouter(tags=["tasks"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


async def _ensure_project(db: AsyncSession, project_id: UUID, tenant_id: UUID) -> Project:
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


class TaskCreate(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    description: str | None = None
    wbs: str | None = None
    parent_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    progress: int = Field(default=0, ge=0, le=100)
    is_milestone: bool = False
    owner_id: UUID | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    status: str = "not_started"


class TaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    status: str | None = None
    owner_id: UUID | None = None


class TaskRead(BaseModel):
    id: UUID
    project_id: UUID
    wbs: str | None
    parent_id: UUID | None
    name: str
    start_date: date | None
    end_date: date | None
    duration_days: int | None
    progress: int
    is_milestone: bool
    status: str
    source: str
    external_id: str | None

    model_config = {"from_attributes": True}


@router.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    project_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _ensure_project(db, project_id, tenant_id)
    rows = (
        await db.execute(
            select(Task).where(Task.project_id == str(project_id))
            .order_by(Task.wbs.nullsfirst() if hasattr(Task.wbs, "nullsfirst") else Task.wbs)
        )
    ).scalars().all()
    return [TaskRead.model_validate(t) for t in rows]


@router.post("/projects/{project_id}/tasks", response_model=TaskRead, status_code=201)
async def create_task(
    project_id: UUID,
    body: TaskCreate,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _ensure_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado")
    if body.start_date and body.end_date and body.end_date < body.start_date:
        raise validation_error("end_date debe ser >= start_date")
    t = Task(
        tenant_id=str(tenant_id), project_id=str(project_id),
        name=body.name, description=body.description, wbs=body.wbs,
        parent_id=str(body.parent_id) if body.parent_id else None,
        start_date=body.start_date, end_date=body.end_date,
        duration_days=body.duration_days, progress=body.progress,
        is_milestone=body.is_milestone,
        owner_id=str(body.owner_id) if body.owner_id else None,
        priority=body.priority, status=body.status, source="manual",
    )
    db.add(t)
    await db.flush()
    await write_audit(
        db, action="task.create", module="tasks", user_id=cu.id, tenant_id=tenant_id,
        entity_type="task", entity_id=str(t.id),
    )
    await db.commit()
    return TaskRead.model_validate(t)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (
        await db.execute(select(Task).where(Task.id == str(task_id), Task.tenant_id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tarea")
    data = body.model_dump(exclude_none=True)
    if "owner_id" in data and data["owner_id"] is not None:
        data["owner_id"] = str(data["owner_id"])
    for k, v in data.items():
        setattr(t, k, v)
    await db.commit()
    return TaskRead.model_validate(t)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (
        await db.execute(select(Task).where(Task.id == str(task_id), Task.tenant_id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tarea")
    await db.execute(delete(TaskDependency).where(
        (TaskDependency.predecessor_id == t.id) | (TaskDependency.successor_id == t.id)
    ))
    await db.delete(t)
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.post("/projects/{project_id}/tasks/import")
async def import_ms_project(
    project_id: UUID,
    file: UploadFile,
    strategy: str = Query(default="replace", pattern="^(replace|merge)$"),
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _ensure_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado, no se puede importar")

    content_type = (file.content_type or "").lower()
    filename_lower = (file.filename or "").lower()
    is_xlsx = (
        content_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        or filename_lower.endswith(".xlsx")
    )
    is_mpp = (
        content_type in {"application/vnd.ms-project", "application/x-project"}
        or filename_lower.endswith((".mpp", ".mpt"))
    )
    is_xml = content_type in {"application/xml", "text/xml"} or filename_lower.endswith(
        (".xml", ".mpx", ".mspdi")
    )
    if not (is_xlsx or is_mpp or is_xml):
        from fastapi import HTTPException

        raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_MEDIA_TYPE"})

    data = await file.read()
    if len(data) > 50 * 1024 * 1024:
        from fastapi import HTTPException

        raise HTTPException(status_code=413, detail={"code": "PAYLOAD_TOO_LARGE"})

    errors: list[dict] = []
    parsed: list
    if is_xlsx or is_mpp:
        # US-067 (XLSX) + US-069 (MPP): ambos parsers devuelven el mismo
        # shape `XlsxParseResult`. El MPP viene de MPXJ subprocess; XLSX
        # de openpyxl. Se convierten al shape que el loop de persistencia
        # espera (los campos del XML como `predecessors` resueltos quedan
        # vacíos — el wizard de US-070 los re-mappea).
        try:
            xlsx_result = parse_mpp(data) if is_mpp else parse_xlsx(data)
        except ValueError as exc:
            label = "MPP" if is_mpp else "XLSX"
            raise business_rule(f"archivo {label} inválido: {exc}")
        errors = list(xlsx_result.errors)

        class _TaskShim:
            def __init__(self, pt):
                # external_id para merge: preferimos WBS si está, fallback a
                # "row-{N}" para tener unicidad dentro del import.
                self.external_id = pt.wbs or f"row-{pt.row_number}"
                self.name = pt.name
                self.wbs = pt.wbs
                self.start_date = pt.start_date
                self.end_date = pt.end_date
                self.duration_days = pt.duration_days
                self.progress = pt.progress
                self.is_milestone = pt.is_milestone
                self.predecessors: list = []

        parsed = [_TaskShim(pt) for pt in xlsx_result.tasks]
    else:
        try:
            parsed, errors = parse_ms_project_xml(data)
        except ValueError as exc:
            raise business_rule(f"archivo MSP inválido: {exc}")

    if strategy == "replace":
        await db.execute(delete(TaskDependency).where(
            TaskDependency.predecessor_id.in_(
                select(Task.id).where(Task.project_id == p.id)
            )
        ))
        await db.execute(delete(Task).where(Task.project_id == p.id))

    # Primera pasada: crear tasks por external_id
    created: dict[str, Task] = {}
    for pt in parsed:
        existing = None
        if strategy == "merge":
            existing = (
                await db.execute(
                    select(Task).where(
                        Task.project_id == p.id, Task.external_id == pt.external_id
                    )
                )
            ).scalar_one_or_none()
        if existing is not None:
            existing.name = pt.name
            existing.wbs = pt.wbs
            existing.start_date = pt.start_date
            existing.end_date = pt.end_date
            existing.duration_days = pt.duration_days
            existing.progress = pt.progress
            existing.is_milestone = pt.is_milestone
            created[pt.external_id] = existing
        else:
            t = Task(
                tenant_id=str(tenant_id), project_id=str(p.id),
                name=pt.name, wbs=pt.wbs,
                start_date=pt.start_date, end_date=pt.end_date,
                duration_days=pt.duration_days, progress=pt.progress,
                is_milestone=pt.is_milestone, status="not_started",
                source="msproject", external_id=pt.external_id,
                imported_at=datetime.now(UTC),
            )
            db.add(t)
            await db.flush()
            created[pt.external_id] = t

    # Segunda pasada: dependencias
    dep_count = 0
    for pt in parsed:
        succ = created.get(pt.external_id)
        if succ is None:
            continue
        for dep in pt.predecessors:
            pre = created.get(dep.predecessor_external_id)
            if pre is None:
                continue
            exists = (
                await db.execute(
                    select(TaskDependency).where(
                        TaskDependency.predecessor_id == pre.id,
                        TaskDependency.successor_id == succ.id,
                    )
                )
            ).scalar_one_or_none()
            if exists is None:
                db.add(TaskDependency(
                    predecessor_id=str(pre.id), successor_id=str(succ.id),
                    type=dep.type, lag_days=dep.lag_days,
                ))
                dep_count += 1

    # US-067 agregó "xlsx"; US-069 agrega "mpp" para auditoría.
    if is_mpp:
        source_label = "mpp"
    elif is_xlsx:
        source_label = "xlsx"
    else:
        source_label = "msproject"
    if is_xlsx or is_mpp:
        for t in created.values():
            t.source = source_label
    await write_audit(
        db,
        action=f"tasks.{source_label}_import",
        module="tasks",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project",
        entity_id=str(p.id),
        details={
            "count": len(parsed),
            "deps": dep_count,
            "strategy": strategy,
            "errors": errors,
            "source": source_label,
        },
    )
    await db.commit()
    return {
        "imported": len(parsed),
        "dependencies_created": dep_count,
        "errors": errors,
        "strategy": strategy,
        "source": source_label,
    }


@router.get("/projects/{project_id}/gantt")
async def gantt_view(
    project_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _ensure_project(db, project_id, tenant_id)
    tasks = (
        await db.execute(select(Task).where(Task.project_id == str(project_id)))
    ).scalars().all()
    deps = (
        await db.execute(
            select(TaskDependency).where(
                TaskDependency.successor_id.in_([t.id for t in tasks])
            )
        )
    ).scalars().all()
    return {
        "tasks": [
            {
                "id": str(t.id), "name": t.name, "wbs": t.wbs,
                "start": t.start_date.isoformat() if t.start_date else None,
                "end": t.end_date.isoformat() if t.end_date else None,
                "progress": t.progress, "is_milestone": t.is_milestone,
                "status": t.status, "external_id": t.external_id,
            }
            for t in tasks
        ],
        "dependencies": [
            {
                "predecessor_id": str(d.predecessor_id),
                "successor_id": str(d.successor_id),
                "type": d.type, "lag_days": d.lag_days,
            }
            for d in deps
        ],
    }
