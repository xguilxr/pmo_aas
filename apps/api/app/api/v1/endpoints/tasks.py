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
from app.services.csv_task_parser import parse_csv
from app.services.import_job_store import (
    JOB_TTL_SECONDS,
    create_job_id,
    delete_preview,
    load_preview,
    save_preview,
)
from app.services.msproject.mpp_parser import parse_mpp
from app.services.msproject.xml_parser import parse_ms_project_xml
from app.services.xlsx_task_parser import ParsedTask, XlsxParseResult, parse_xlsx

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


# ------------------------------------------------------------------
# US-070 — Wizard de mapeo de columnas (preview + confirm)
#
# El endpoint `import_ms_project` de arriba sigue funcionando como
# "one-shot": útil para MPP/XML que no necesitan mapeo y tests viejos
# que lo consumen directo. El wizard nuevo para XLSX/CSV vive acá.
#
# Flujo:
#   1. POST /import/preview   → parsea, guarda archivo + metadata en
#      Redis con TTL 1h, devuelve {job_id, sheets[], sample_rows[],
#      columns_detected{}, task_count}.
#   2. Usuario revisa preview, eventualmente re-mappea columnas.
#   3. POST /import/{job_id}/confirm → lee preview de Redis, re-parsea
#      con mapping override si se envió, persiste.
#
# Límite de archivo para el wizard: 10 MB (vs 50 MB del endpoint viejo)
# porque guardamos el binario en Redis codificado en base64 para poder
# re-parsear en confirm sin persistir a disco.
# ------------------------------------------------------------------

MAX_WIZARD_FILE_MB = 10
SYSTEM_FIELDS: list[str] = [
    "name", "wbs", "start_date", "end_date", "duration_days",
    "progress", "is_milestone", "predecessors", "resources",
]


def _detect_source(content_type: str, filename: str) -> str:
    """Devuelve 'xlsx' | 'csv' | 'mpp' | 'xml' o lanza 415."""
    ct = (content_type or "").lower()
    fn = (filename or "").lower()
    if (
        ct == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        or fn.endswith(".xlsx")
    ):
        return "xlsx"
    if ct in {"text/csv", "application/csv"} or fn.endswith(".csv"):
        return "csv"
    if (
        ct in {"application/vnd.ms-project", "application/x-project"}
        or fn.endswith((".mpp", ".mpt"))
    ):
        return "mpp"
    if ct in {"application/xml", "text/xml"} or fn.endswith((".xml", ".mpx", ".mspdi")):
        return "xml"
    from fastapi import HTTPException
    raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_MEDIA_TYPE"})


def _serialize_sample(rows: list[list[object]]) -> list[list[str | None]]:
    """Convierte celdas a string (o None) para serializar a JSON sin
    perder info. `datetime` se convierte a ISO; `None` se mantiene."""
    out: list[list[str | None]] = []
    for row in rows:
        serialized: list[str | None] = []
        for cell in row:
            if cell is None or cell == "":
                serialized.append(None)
            elif isinstance(cell, (datetime, date)):
                serialized.append(cell.isoformat())
            else:
                serialized.append(str(cell))
        out.append(serialized)
    return out


def _parse_for_preview(
    source: str,
    data: bytes,
    sheet: str | None,
    columns_override: dict[str, int] | None = None,
    strict: bool = True,
) -> XlsxParseResult:
    """Dispatch interno del parser según source. Adapta XML al shape
    de `XlsxParseResult` para que el wizard tenga una superficie
    uniforme. Lanza `ValueError` en errores de parseo.

    `strict=False` se usa desde `/preview` para tolerar archivos con
    headers custom (el usuario los mapea en el wizard); el `/confirm`
    siempre usa `strict=True`.
    """
    if source == "xlsx":
        return parse_xlsx(
            data, sheet=sheet, columns_override=columns_override, strict=strict
        )
    if source == "csv":
        return parse_csv(data, columns_override=columns_override, strict=strict)
    if source == "mpp":
        # MPP no usa mapping manual (el CLI MPXJ emite shape ya normalizado).
        # Se respeta `columns_override` solo si el caller lo envió explícito;
        # caso contrario el shape natural es suficiente.
        return parse_mpp(data)
    if source == "xml":
        tasks_xml, errs = parse_ms_project_xml(data)
        # Adapter: XML devuelve (ParsedTask del msproject.xml_parser, errs[]).
        # Para homogeneizar con el shape del wizard devolvemos un
        # `XlsxParseResult` con las tareas convertidas.
        result = XlsxParseResult()
        for t in tasks_xml:
            result.tasks.append(
                ParsedTask(
                    row_number=int(t.external_id) if t.external_id.isdigit() else 0,
                    name=t.name,
                    wbs=t.wbs,
                    start_date=t.start_date,
                    end_date=t.end_date,
                    duration_days=t.duration_days,
                    progress=t.progress,
                    is_milestone=t.is_milestone,
                    predecessors_raw=(
                        ",".join(d.predecessor_external_id for d in t.predecessors)
                        or None
                    ),
                    resources_raw=None,
                )
            )
        result.errors = [{"row": 0, "error": e} for e in errs]
        return result
    raise ValueError(f"source desconocido: {source}")


@router.post("/projects/{project_id}/tasks/import/preview")
async def import_preview(
    project_id: UUID,
    file: UploadFile,
    sheet: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    """US-070 step 1 — parsea el archivo, guarda en Redis y devuelve
    metadata para renderizar el wizard.
    """
    import base64

    from fastapi import HTTPException

    tenant_id = _tenant(cu)
    p = await _ensure_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado, no se puede importar")

    filename = file.filename or ""
    source = _detect_source(file.content_type or "", filename)

    data = await file.read()
    if not data:
        raise business_rule("archivo vacío")
    if len(data) > MAX_WIZARD_FILE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "PAYLOAD_TOO_LARGE",
                "max_mb": MAX_WIZARD_FILE_MB,
                "hint": "El wizard acepta hasta 10MB. Para archivos más "
                "grandes usá el endpoint /import directo (sin mapeo manual).",
            },
        )

    try:
        parse_result = _parse_for_preview(source, data, sheet=sheet, strict=False)
    except ValueError as exc:
        raise business_rule(f"archivo {source.upper()} inválido: {exc}")

    job_id = create_job_id()
    try:
        save_preview(
            job_id,
            {
                "file_b64": base64.b64encode(data).decode("ascii"),
                "filename": filename,
                "source": source,
                "tenant_id": str(tenant_id),
                "project_id": str(project_id),
                "user_id": str(cu.id),
                "sheet": sheet,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "PREVIEW_STORE_UNAVAILABLE", "hint": str(exc)[:200]},
        )

    await write_audit(
        db,
        action="tasks.import_preview",
        module="tasks",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project",
        entity_id=str(p.id),
        details={
            "job_id": job_id,
            "source": source,
            "filename": filename,
            "sheet": sheet,
            "task_count": len(parse_result.tasks),
            "sheets": parse_result.sheets,
        },
    )
    await db.commit()

    return {
        "job_id": job_id,
        "source": source,
        "sheets": parse_result.sheets,
        "sheet_used": parse_result.sheet_used,
        "columns_detected": parse_result.columns_detected,
        "sample_rows": _serialize_sample(parse_result.sample_rows),
        "task_count": len(parse_result.tasks),
        "errors": parse_result.errors,
        "ttl_seconds": JOB_TTL_SECONDS,
        "system_fields": SYSTEM_FIELDS,
    }


class ImportConfirmBody(BaseModel):
    mapping: dict[str, int] | None = Field(
        default=None,
        description=(
            "Mapeo manual de `{field_sistema: col_index}`. Si ausente, se "
            "usa el auto-detect del preview. Solo aplica a XLSX/CSV — en "
            "MPP/XML el shape ya está normalizado."
        ),
    )
    strategy: str = Field(default="replace", pattern="^(replace|merge)$")


@router.post("/projects/{project_id}/tasks/import/{job_id}/confirm")
async def import_confirm(
    project_id: UUID,
    job_id: str,
    body: ImportConfirmBody,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    """US-070 step 2 — lee preview de Redis, aplica mapping y persiste."""
    import base64

    from fastapi import HTTPException

    tenant_id = _tenant(cu)
    p = await _ensure_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado, no se puede importar")

    preview = load_preview(job_id)
    if preview is None:
        raise HTTPException(
            status_code=410,
            detail={
                "code": "PREVIEW_EXPIRED",
                "hint": f"El preview expiró (TTL {JOB_TTL_SECONDS}s). "
                "Volvé a subir el archivo.",
            },
        )

    # Ownership check: el preview solo puede confirmarlo el mismo
    # usuario del mismo tenant/proyecto que lo creó.
    if (
        preview.get("tenant_id") != str(tenant_id)
        or preview.get("project_id") != str(project_id)
    ):
        raise not_found("Preview job")
    if preview.get("user_id") != str(cu.id):
        raise forbidden()

    try:
        data = base64.b64decode(preview["file_b64"])
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "PREVIEW_DECODE_FAILED", "hint": str(exc)[:200]},
        )
    source = preview["source"]
    sheet = preview.get("sheet")

    # Mapping override solo aplica a XLSX/CSV (MPP/XML ya vienen
    # normalizados por sus parsers propios).
    if body.mapping and source in ("xlsx", "csv"):
        if "name" not in body.mapping:
            raise validation_error(
                "El mapping debe incluir el campo obligatorio 'name'"
            )
        columns_override = body.mapping
    else:
        columns_override = None

    try:
        parse_result = _parse_for_preview(
            source, data, sheet=sheet, columns_override=columns_override
        )
    except ValueError as exc:
        raise business_rule(f"archivo {source.upper()} inválido al confirmar: {exc}")

    errors = list(parse_result.errors)

    class _TaskShim:
        def __init__(self, pt: ParsedTask):
            self.external_id = pt.wbs or f"row-{pt.row_number}"
            self.name = pt.name
            self.wbs = pt.wbs
            self.start_date = pt.start_date
            self.end_date = pt.end_date
            self.duration_days = pt.duration_days
            self.progress = pt.progress
            self.is_milestone = pt.is_milestone
            self.predecessors: list = []

    parsed = [_TaskShim(t) for t in parse_result.tasks]

    if body.strategy == "replace":
        await db.execute(
            delete(TaskDependency).where(
                TaskDependency.predecessor_id.in_(
                    select(Task.id).where(Task.project_id == p.id)
                )
            )
        )
        await db.execute(delete(Task).where(Task.project_id == p.id))

    source_label = source if source != "xml" else "msproject"
    created: dict[str, Task] = {}
    for pt in parsed:
        existing = None
        if body.strategy == "merge":
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
            existing.source = source_label
            created[pt.external_id] = existing
        else:
            t = Task(
                tenant_id=str(tenant_id), project_id=str(p.id),
                name=pt.name, wbs=pt.wbs,
                start_date=pt.start_date, end_date=pt.end_date,
                duration_days=pt.duration_days, progress=pt.progress,
                is_milestone=pt.is_milestone, status="not_started",
                source=source_label, external_id=pt.external_id,
                imported_at=datetime.now(UTC),
            )
            db.add(t)
            await db.flush()
            created[pt.external_id] = t

    # Cleanup Redis post-commit exitoso.
    delete_preview(job_id)

    await write_audit(
        db,
        action="tasks.import_confirm",
        module="tasks",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project",
        entity_id=str(p.id),
        details={
            "job_id": job_id,
            "source": source,
            "strategy": body.strategy,
            "count": len(parsed),
            "mapping_override": bool(body.mapping),
            "errors": errors,
        },
    )
    await db.commit()

    return {
        "imported": len(parsed),
        "dependencies_created": 0,
        "errors": errors,
        "strategy": body.strategy,
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
