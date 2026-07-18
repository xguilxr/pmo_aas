from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import business_rule, forbidden, not_found, validation_error
from app.db.session import get_db
from app.models.project import Project
from app.models.project_artifact import ProjectArtifact
from app.models.task import Task, TaskDependency
from app.models.user import User
from app.schemas.modules import UserMini
from app.services.ai.tenant_ai import load_tenant_ai
from app.services.audit import write_audit
from app.services.csv_task_parser import parse_csv
from app.services.import_ai import (
    ai_match_resources,
    ai_normalize_statuses,
    ai_propose_structure,
    extract_raw_rows,
)
from app.services.import_job_store import (
    JOB_TTL_SECONDS,
    create_job_id,
    delete_preview,
    load_preview,
    save_preview,
)
from app.services.import_mapping_suggest import (
    SYSTEM_FIELDS as MAPPING_SYSTEM_FIELDS,
)
from app.services.import_mapping_suggest import (
    suggest_column_mapping,
)
from app.services.msproject.mpp_parser import parse_mpp
from app.services.msproject.xml_parser import parse_ms_project_xml
from app.services.plan_metadata import (
    collect_by_wbs,
    compute_duration_days,
    compute_outline_level,
    compute_wbs_rollup,
    ensure_duration_max_21,
    parent_wbs,
    recompute_successors_for_project,
    round_half_up,
    validate_predecessors,
    wbs_sort_key,
)
from app.services.xlsx_task_parser import (
    ParsedTask,
    XlsxParseResult,
    _coerce_date,
    parse_xlsx,
)

# ENH-051: enum literal compartido por TaskCreate / TaskUpdate / TaskRead.
TaskCriticality = Literal["low", "medium", "high", "critical"]

_VALID_CRITICALITY = {"low", "medium", "high", "critical"}


def _normalize_criticality(raw: object) -> str | None:
    """US-096 — normaliza el valor leído desde la plantilla XLSX.

    Acepta variantes case-insensitive ('Low', 'HIGH'). Devuelve None
    si el valor no calza con el enum (la fila usa el default de la
    columna en la BD)."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    return s if s in _VALID_CRITICALITY else None

router = APIRouter(tags=["tasks"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


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
    # US-171: fecha de cierre real (editable).
    closed_at: date | None = None
    duration_days: int | None = None
    progress: int = Field(default=0, ge=0, le=100)
    is_milestone: bool = False
    owner_id: UUID | None = None
    # ENH-079: responsable como Actor (futuro reemplazo de owner_id).
    assignee_actor_id: UUID | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    status: str = "not_started"
    # ENH-051: criticidad opcional al crear; default `medium` server-side.
    criticality: TaskCriticality = "medium"
    # ENH-097: boolean explicito de criticidad (paralelo a `criticality`).
    is_critical: bool = False
    # ENH-050: hito relacionado opcional al crear.
    related_milestone_id: UUID | None = None
    # US-090: predecesoras como lista de wbs_code.
    predecessors: list[str] | None = None
    # US-098: área responsable (catálogo tenant).
    area_id: UUID | None = None


class TaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    # US-171: PATCH de la fecha de cierre. Ausente = no tocar; None = limpiar.
    closed_at: date | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    status: str | None = None
    owner_id: UUID | None = None
    assignee_actor_id: UUID | None = None
    area_id: UUID | None = None
    criticality: TaskCriticality | None = None
    # ENH-097: PATCH del boolean explicito.
    is_critical: bool | None = None
    # ENH-050: PATCH para reasignar / desasociar (None) el hito relacionado.
    # Pydantic distingue ausente vs None vía `model_dump(exclude_unset=True)`.
    related_milestone_id: UUID | None = None
    # US-090: PATCH de predecesoras. None = desasociar todas, ausente = no tocar.
    predecessors: list[str] | None = None
    # US-090: tras editar fechas, el backend recalcula duration_days
    # (auto). Si el cliente manda duration_days explícito, se ignora.
    wbs: str | None = None


class TaskMini(BaseModel):
    """ENH-050: shape mínimo del hito relacionado embebido en TaskRead."""

    id: UUID
    name: str
    wbs: str | None = None

    model_config = {"from_attributes": True}


class TaskRead(BaseModel):
    id: UUID
    project_id: UUID
    wbs: str | None
    parent_id: UUID | None
    name: str
    start_date: date | None
    end_date: date | None
    # US-171: fecha de cierre real.
    closed_at: date | None = None
    duration_days: int | None
    progress: int
    is_milestone: bool
    status: str
    source: str
    external_id: str | None
    # ENH-049: responsable embebido para que la lista de tareas muestre
    # avatar+nombre sin un round-trip extra a /users.
    owner_id: UUID | None = None
    owner: UserMini | None = None
    assignee_actor_id: UUID | None = None
    # ENH-051: criticidad para chip de color en lista + filtro Críticos.
    criticality: str = "medium"
    # ENH-097: boolean explicito de criticidad (paralelo a `criticality`).
    is_critical: bool = False
    # ENH-050: hito relacionado.
    related_milestone_id: UUID | None = None
    related_milestone: TaskMini | None = None
    # US-090: outline level + predecesoras / sucesoras (auto-managed).
    # Coerce None → [] para tasks legacy importadas antes de migración 0039.
    outline_level: int | None = None
    predecessors: list[str] | None = None
    successors: list[str] | None = None
    # US-098: área responsable.
    area_id: UUID | None = None

    model_config = {"from_attributes": True}


async def _validate_related_milestone(
    db: AsyncSession, project_id: UUID, related_id: UUID
) -> Task:
    """ENH-050: target debe (a) existir, (b) pertenecer al mismo proyecto,
    (c) ser un hito (`is_milestone=true`). Devuelve la Task validada o
    levanta 422."""
    target = (
        await db.execute(select(Task).where(Task.id == str(related_id)))
    ).scalar_one_or_none()
    if target is None:
        raise validation_error("related_milestone_id no existe")
    if str(target.project_id) != str(project_id):
        raise validation_error("related_milestone_id no pertenece al proyecto")
    if not target.is_milestone:
        raise validation_error("related_milestone_id debe apuntar a un hito (is_milestone=true)")
    return target


async def _attach_milestones(db: AsyncSession, tasks: list[Task]) -> None:
    """ENH-050: enriquece `task.related_milestone` con `{id, name, wbs}`."""
    ids: set[str] = {str(t.related_milestone_id) for t in tasks if t.related_milestone_id}
    if not ids:
        for t in tasks:
            t.related_milestone = None  # type: ignore[attr-defined]
        return
    rows = (
        await db.execute(select(Task).where(Task.id.in_(ids)))
    ).scalars().all()
    by_id = {str(r.id): r for r in rows}
    for t in tasks:
        m = by_id.get(str(t.related_milestone_id)) if t.related_milestone_id else None
        t.related_milestone = (  # type: ignore[attr-defined]
            {"id": str(m.id), "name": m.name, "wbs": m.wbs} if m else None
        )


async def _attach_owners(db: AsyncSession, tasks: list[Task]) -> None:
    """ENH-049 + ENH-079: enriquece `task.owner` con `{id, full_name, email}`
    para la columna Responsable. Si `assignee_actor_id` está set, mappea
    al Actor (preferido); fallback al owner_id user legacy.
    """
    from app.models.area import Actor

    actor_ids: set[str] = {
        str(t.assignee_actor_id) for t in tasks if t.assignee_actor_id
    }
    actor_by_id: dict[str, Actor] = {}
    if actor_ids:
        rows = (
            await db.execute(select(Actor).where(Actor.id.in_(actor_ids)))
        ).scalars().all()
        actor_by_id = {str(a.id): a for a in rows}

    legacy_owner_ids: set[str] = {
        str(t.owner_id) for t in tasks if t.owner_id and not t.assignee_actor_id
    }
    user_by_id: dict[str, User] = {}
    if legacy_owner_ids:
        rows = (
            await db.execute(select(User).where(User.id.in_(legacy_owner_ids)))
        ).scalars().all()
        user_by_id = {str(u.id): u for u in rows}

    for t in tasks:
        if t.assignee_actor_id:
            a = actor_by_id.get(str(t.assignee_actor_id))
            t.owner = (  # type: ignore[attr-defined]
                {
                    "id": str(a.id),
                    "full_name": a.name,
                    "email": a.email or "",
                }
                if a
                else None
            )
        elif t.owner_id:
            u = user_by_id.get(str(t.owner_id))
            t.owner = (  # type: ignore[attr-defined]
                {"id": str(u.id), "full_name": u.full_name, "email": u.email}
                if u
                else None
            )
        else:
            t.owner = None  # type: ignore[attr-defined]


@router.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    project_id: UUID,
    area_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _ensure_project(db, project_id, tenant_id)
    stmt = select(Task).where(Task.project_id == str(project_id))
    if area_id is not None:
        stmt = stmt.where(Task.area_id == str(area_id))
    rows = (await db.execute(stmt)).scalars().all()
    # US-176: si el proyecto fue reordenado manualmente, `position` manda; el
    # resto cae al orden natural por WBS (BUG-049: 1.2 < 1.10) post-fetch.
    rows_list = sorted(
        rows,
        key=lambda t: (
            t.position is None,
            t.position if t.position is not None else 0,
            wbs_sort_key(t.wbs),
        ),
    )
    await _attach_owners(db, rows_list)
    await _attach_milestones(db, rows_list)
    # ENH-109 — avance jerárquico: una tarea con hijos muestra el promedio
    # del avance de sus hijos (recursivo por nivel WBS). Las hojas mantienen
    # su valor almacenado. Se calcula al serializar (read-side); no muta la
    # columna `tasks.progress`. Si `area_id` filtra la lista, el rollup se
    # computa sobre el plan COMPLETO del proyecto para que un padre fuera
    # del filtro no quede mal promediado.
    rollup_source = rows_list
    if area_id is not None:
        rollup_source = (
            await db.execute(
                select(Task).where(Task.project_id == str(project_id))
            )
        ).scalars().all()
    rollup = compute_wbs_rollup(rollup_source)
    out: list[TaskRead] = []
    for t in rows_list:
        r = TaskRead.model_validate(t)
        eff = rollup.get(str(t.id))
        if eff is not None:
            r.progress = round_half_up(eff)
        out.append(r)
    return out


@router.post("/projects/{project_id}/tasks", response_model=TaskRead, status_code=201)
async def create_task(
    project_id: UUID,
    body: TaskCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _ensure_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado")
    if body.start_date and body.end_date and body.end_date < body.start_date:
        raise validation_error("end_date debe ser >= start_date")
    if body.related_milestone_id is not None:
        await _validate_related_milestone(db, project_id, body.related_milestone_id)
    # US-090: duration auto-calculada desde fechas (override del client si
    # las fechas existen). Clamp a max 21 días.
    auto_duration = compute_duration_days(body.start_date, body.end_date)
    final_duration = auto_duration if auto_duration is not None else body.duration_days
    ensure_duration_max_21(final_duration)
    # US-171: al crear ya completada sin fecha de cierre explícita, default = hoy.
    closed_at_value = body.closed_at
    if closed_at_value is None and body.status == "completed":
        closed_at_value = date.today()
    # US-090: predecessors validados contra el set actual de tasks del
    # proyecto + cycle check.
    cleaned_preds: list[str] = []
    if body.predecessors is not None:
        all_tasks = (
            await db.execute(select(Task).where(Task.project_id == str(project_id)))
        ).scalars().all()
        cleaned_preds = validate_predecessors(
            body.predecessors, collect_by_wbs(all_tasks), body.wbs
        )
    t = Task(
        tenant_id=str(tenant_id), project_id=str(project_id),
        name=body.name, description=body.description, wbs=body.wbs,
        parent_id=str(body.parent_id) if body.parent_id else None,
        start_date=body.start_date, end_date=body.end_date,
        closed_at=closed_at_value,
        duration_days=final_duration, progress=body.progress,
        is_milestone=body.is_milestone,
        owner_id=str(body.owner_id) if body.owner_id else None,
        assignee_actor_id=str(body.assignee_actor_id) if body.assignee_actor_id else None,
        priority=body.priority, status=body.status, source="manual",
        criticality=body.criticality,
        is_critical=body.is_critical,
        related_milestone_id=(
            str(body.related_milestone_id) if body.related_milestone_id else None
        ),
        outline_level=compute_outline_level(body.wbs),
        predecessors=cleaned_preds,
        successors=[],
        area_id=str(body.area_id) if body.area_id else None,
    )
    db.add(t)
    await db.flush()
    # US-090: re-sync successors de todo el proyecto (incluye la task nueva).
    await recompute_successors_for_project(db, str(project_id))
    await write_audit(
        db, action="task.create", module="tasks", user_id=cu.id, tenant_id=tenant_id,
        entity_type="task", entity_id=str(t.id),
    )
    await db.commit()
    await _attach_owners(db, [t])
    await _attach_milestones(db, [t])
    return TaskRead.model_validate(t)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (
        await db.execute(select(Task).where(Task.id == str(task_id), Task.tenant_id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tarea")
    # ENH-050: distinguir "no enviado" vs "enviado=null" (desasociar). El
    # resto de campos sigue usando exclude_none=True para back-compat.
    data_full = body.model_dump(exclude_unset=True)
    data = body.model_dump(exclude_none=True)
    if "owner_id" in data and data["owner_id"] is not None:
        data["owner_id"] = str(data["owner_id"])
    if "assignee_actor_id" in data and data["assignee_actor_id"] is not None:
        data["assignee_actor_id"] = str(data["assignee_actor_id"])
    # ENH-079: PATCH `assignee_actor_id` distingue ausente vs None.
    if "assignee_actor_id" in data_full:
        aid = data_full["assignee_actor_id"]
        t.assignee_actor_id = str(aid) if aid is not None else None
        data.pop("assignee_actor_id", None)
    # US-098: PATCH `area_id` distingue ausente (no tocar) vs None
    # (desasignar) — mismo patrón que related_milestone_id.
    if "area_id" in data_full:
        aid = data_full["area_id"]
        t.area_id = str(aid) if aid is not None else None
        data.pop("area_id", None)
    # US-171: PATCH `closed_at` distingue ausente (no tocar) vs None (limpiar).
    if "closed_at" in data_full:
        t.closed_at = data_full["closed_at"]
        data.pop("closed_at", None)
    if "related_milestone_id" in data_full:
        rid = data_full["related_milestone_id"]
        if rid is None:
            t.related_milestone_id = None
        else:
            await _validate_related_milestone(db, UUID(str(t.project_id)), rid)
            t.related_milestone_id = str(rid)
        data.pop("related_milestone_id", None)
    # US-090: handle predecessors PATCH (None = vaciar, ausente = no tocar).
    if "predecessors" in data_full:
        new_preds = data_full["predecessors"] or []
        all_tasks = (
            await db.execute(select(Task).where(Task.project_id == t.project_id))
        ).scalars().all()
        t.predecessors = validate_predecessors(
            new_preds, collect_by_wbs(all_tasks, exclude_id=str(t.id)), t.wbs
        )
        data.pop("predecessors", None)
    for k, v in data.items():
        setattr(t, k, v)
    # US-090: si tocaron wbs / start / end, recomputar outline + duration.
    if "wbs" in data_full:
        t.outline_level = compute_outline_level(t.wbs)
    if {"start_date", "end_date"} & data_full.keys():
        auto_d = compute_duration_days(t.start_date, t.end_date)
        if auto_d is not None:
            ensure_duration_max_21(auto_d)
            t.duration_days = auto_d
    # US-171: al completar sin fecha de cierre explícita, default = hoy. Así la
    # lógica de atraso (closed_at > end_date) tiene un dato con qué comparar.
    if t.status == "completed" and t.closed_at is None:
        t.closed_at = date.today()
    # Re-sync successors del proyecto entero (predecessors o wbs pueden haber cambiado).
    await recompute_successors_for_project(db, t.project_id)
    await db.commit()
    await _attach_owners(db, [t])
    await _attach_milestones(db, [t])
    return TaskRead.model_validate(t)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
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
    # ENH-050: la FK self con ondelete=SET NULL cubre Postgres en prod;
    # en SQLite (tests) la PRAGMA foreign_keys puede estar OFF, así que
    # también NULLeamos explícitamente para que la semántica sea idéntica.
    await db.execute(
        update(Task).where(Task.related_milestone_id == t.id).values(related_milestone_id=None)
    )
    await db.delete(t)
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


def _natural_wbs_key(wbs: str | None) -> tuple:
    """Orden jerárquico natural de un WBS: '1.10' va DESPUÉS de '1.2'.
    Segmentos numéricos se comparan como int; los no numéricos van al final;
    WBS vacío al final del todo."""
    if not wbs:
        return ((2, 0, ""),)
    parts: list[tuple[int, int, str]] = []
    for seg in str(wbs).split("."):
        seg = seg.strip()
        if seg.isdigit():
            parts.append((0, int(seg), ""))
        elif seg:
            parts.append((1, 0, seg))
    return tuple(parts) or ((2, 0, ""),)


@router.post("/projects/{project_id}/tasks/renumber-wbs")
async def renumber_wbs(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-172 — renumera el WBS de TODAS las tareas del proyecto de forma
    jerárquica y ÚNICA (1, 1.1, 1.2, 2, 2.1, ...), preservando el orden
    visual actual y la profundidad (outline_level / segmentos del WBS).
    Resuelve WBS duplicados o vacíos. Remapea predecesoras al nuevo esquema
    (best-effort, primera ocurrencia gana) y recomputa sucesoras.
    """
    tenant_id = _tenant(cu)
    p = await _ensure_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado")

    tasks = (
        await db.execute(select(Task).where(Task.project_id == str(project_id)))
    ).scalars().all()
    # Orden visual: US-176 `position` manda si existe; luego WBS natural y
    # created_at para desempatar duplicados.
    _floor = datetime.min.replace(tzinfo=UTC)
    ordered = sorted(
        tasks,
        key=lambda t: (
            t.position is None,
            t.position if t.position is not None else 0,
            _natural_wbs_key(t.wbs),
            t.created_at or _floor,
        ),
    )

    old_to_new: dict[str, str] = {}
    counters: list[int] = []
    for t in ordered:
        raw = (
            t.outline_level
            if t.outline_level is not None
            else max(0, len((t.wbs or "").split(".")) - 1)
        )
        depth = min(max(0, raw), len(counters))
        if depth < len(counters):
            del counters[depth + 1:]
            counters[depth] += 1
        else:
            counters.append(1)
        new_wbs = ".".join(str(c) for c in counters)
        if t.wbs and t.wbs not in old_to_new:
            old_to_new[t.wbs] = new_wbs  # primera ocurrencia gana
        t.wbs = new_wbs
        t.outline_level = depth

    # Remapea predecesoras (tokens WBS) al nuevo esquema; descarta dangling.
    for t in ordered:
        if t.predecessors:
            remapped: list[str] = []
            for pre in t.predecessors:
                nv = old_to_new.get(pre)
                if nv and nv != t.wbs and nv not in remapped:
                    remapped.append(nv)
            t.predecessors = remapped

    await recompute_successors_for_project(db, str(project_id))
    await write_audit(
        db, action="tasks.renumber_wbs", module="tasks", user_id=cu.id,
        tenant_id=tenant_id, entity_type="project", entity_id=str(project_id),
        details={"count": len(ordered)},
    )
    await db.commit()
    return {"renumbered": len(ordered)}


class MoveTaskBody(BaseModel):
    # US-176: reordena la tarea para que quede JUSTO DESPUÉS de `after_id`.
    # `after_id=None` la manda al inicio del plan.
    after_id: UUID | None = None


@router.post("/projects/{project_id}/tasks/{task_id}/move")
async def move_task(
    project_id: UUID,
    task_id: UUID,
    body: MoveTaskBody,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-176 — reorden manual del plan. Reasigna `position` secuencial a TODAS
    las tareas del proyecto colocando `task_id` justo después de `after_id`
    (o al inicio si es None). Robusto ante vistas filtradas: normaliza el orden
    completo. El indent (outline_level) no cambia."""
    tenant_id = _tenant(cu)
    p = await _ensure_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado, no se puede reordenar")

    tasks = (
        await db.execute(select(Task).where(Task.project_id == str(project_id)))
    ).scalars().all()
    # Orden actual (position manda; fallback WBS natural).
    ordered = sorted(
        tasks,
        key=lambda t: (
            t.position is None,
            t.position if t.position is not None else 0,
            wbs_sort_key(t.wbs),
        ),
    )
    moved = next((t for t in ordered if str(t.id) == str(task_id)), None)
    if moved is None:
        raise not_found("Tarea")
    ordered.remove(moved)
    if body.after_id is None:
        ordered.insert(0, moved)
    else:
        idx = next(
            (i for i, t in enumerate(ordered) if str(t.id) == str(body.after_id)),
            None,
        )
        # after_id inexistente (p.ej. fuera del proyecto) → al final.
        ordered.insert(idx + 1 if idx is not None else len(ordered), moved)
    for i, t in enumerate(ordered):
        t.position = i
    await write_audit(
        db, action="tasks.move", module="tasks", user_id=cu.id,
        tenant_id=tenant_id, entity_type="task", entity_id=str(task_id),
        details={"after_id": str(body.after_id) if body.after_id else None},
    )
    await db.commit()
    return {"reordered": len(ordered)}


@router.post("/projects/{project_id}/tasks/import")
async def import_ms_project(
    project_id: UUID,
    file: UploadFile,
    strategy: str = Query(default="replace", pattern="^(replace|merge)$"),
    cu: CurrentUser = Depends(require_authenticated()),
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
            # BUG-078: (project_id, external_id) no es único. Un plan con
            # WBS repetidos —o un import previo— deja varias filas con el
            # mismo external_id; scalar_one_or_none() reventaba con
            # MultipleResultsFound (500 "no se pudo conectar" al subir).
            # Tomamos la primera de forma determinista en vez de fallar.
            existing = (
                await db.execute(
                    select(Task)
                    .where(
                        Task.project_id == p.id, Task.external_id == pt.external_id
                    )
                    .order_by(Task.id)
                )
            ).scalars().first()
        if existing is not None:
            existing.name = pt.name
            existing.wbs = pt.wbs
            existing.start_date = pt.start_date
            existing.end_date = pt.end_date
            existing.duration_days = pt.duration_days
            existing.progress = pt.progress
            existing.is_milestone = pt.is_milestone
            existing.outline_level = compute_outline_level(pt.wbs)
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
                outline_level=compute_outline_level(pt.wbs),
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
# ENH-192: una sola fuente de verdad para los campos mapeables del
# wizard — la lista completa del suggester/parser (antes el wizard solo
# ofrecía 9 y area/criticidad/hito relacionado no se podían re-mapear).
SYSTEM_FIELDS: list[str] = list(MAPPING_SYSTEM_FIELDS)

# ENH-192: cuántas tareas interpretadas devuelve el preview del wizard.
PARSED_PREVIEW_LIMIT = 10


def _serialize_parsed_tasks(tasks: list[ParsedTask]) -> list[dict]:
    """ENH-192: primeras N tareas YA interpretadas (WBS fiel, % escalado,
    estado normalizado) para que el wizard muestre cómo quedará el plan
    en vez de celdas crudas."""
    out: list[dict] = []
    for t in tasks[:PARSED_PREVIEW_LIMIT]:
        out.append(
            {
                "row_number": t.row_number,
                "wbs": t.wbs,
                "name": t.name,
                "start_date": t.start_date.isoformat() if t.start_date else None,
                "end_date": t.end_date.isoformat() if t.end_date else None,
                "duration_days": t.duration_days,
                "progress": t.progress,
                "status": t.status,
                "is_milestone": t.is_milestone,
                "is_critical": t.is_critical,
                "area": t.area_raw,
                "resources": t.resources_raw,
                "related_milestone": t.related_milestone_wbs,
                "predecessors": t.predecessors_raw,
            }
        )
    return out


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


def _collect_import_warnings(parse_result: XlsxParseResult) -> list[dict]:
    """BUG-088: warnings del parser + detección de huérfanos WBS.

    Una tarea es huérfana cuando su WBS tiene padre implícito (`1.30.1`
    → `1.30`) pero ese padre no existe en el archivo — la jerarquía
    (rollup de avance, agrupado, Gantt) la dejaría suelta al importar.
    Solo se flaggean WBS de ≥ 3 segmentos: los de 2 sin fila padre
    ("1.1" sin "1") son un estilo de plan válido y serían puro ruido.
    """
    warnings = list(parse_result.warnings)
    wbs_set = {t.wbs for t in parse_result.tasks if t.wbs}
    orphans: list[str] = []
    for t in parse_result.tasks:
        pw = parent_wbs(t.wbs)
        if pw and "." in pw and pw not in wbs_set:
            orphans.append(t.wbs or "")
    if orphans:
        warnings.append(
            {
                "code": "WBS_ORPHANS",
                "count": len(orphans),
                "rows": orphans[:20],
                "message": (
                    f"{len(orphans)} tarea(s) quedarían huérfanas: su WBS "
                    "padre no existe en el archivo (ej. "
                    f"{', '.join(orphans[:3])}). Revisá la numeración WBS "
                    "antes de confirmar."
                ),
            }
        )
    return warnings


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
    cu: CurrentUser = Depends(require_authenticated()),
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
        # BUG-088: avisos no bloqueantes (WBS numérico, huérfanos).
        "warnings": _collect_import_warnings(parse_result),
        # ENH-192: tareas interpretadas para el preview del wizard.
        "parsed_preview": _serialize_parsed_tasks(parse_result.tasks),
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
    # US-188 nivel 3: persistir la propuesta de estructura generada por
    # /ai-structure en lugar de re-parsear el archivo con mapping.
    use_ai_structure: bool = False


class RepreviewBody(BaseModel):
    # ENH-192: mismo shape de mapping que el confirm.
    mapping: dict[str, int] | None = None


@router.post("/projects/{project_id}/tasks/import/{job_id}/repreview")
async def import_repreview(
    project_id: UUID,
    job_id: str,
    body: RepreviewBody,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-192 — re-interpreta el archivo del job con un mapping manual
    SIN persistir nada. El wizard lo llama cuando el usuario re-mapea
    columnas para refrescar la vista interpretada + warnings en vivo.
    """
    import base64

    from fastapi import HTTPException

    tenant_id = _tenant(cu)
    await _ensure_project(db, project_id, tenant_id)

    preview = load_preview(job_id)
    if preview is None:
        raise HTTPException(
            status_code=410,
            detail={"code": "PREVIEW_EXPIRED"},
        )
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
    columns_override = (
        body.mapping if body.mapping and source in ("xlsx", "csv") else None
    )
    try:
        parse_result = _parse_for_preview(
            source,
            data,
            sheet=preview.get("sheet"),
            columns_override=columns_override,
            strict=False,
        )
    except ValueError as exc:
        raise business_rule(f"archivo {source.upper()} inválido: {exc}")

    return {
        "task_count": len(parse_result.tasks),
        "columns_detected": parse_result.columns_detected,
        "errors": parse_result.errors,
        "warnings": _collect_import_warnings(parse_result),
        "parsed_preview": _serialize_parsed_tasks(parse_result.tasks),
    }


@router.post("/projects/{project_id}/tasks/import/{job_id}/ai-structure")
async def import_ai_structure(
    project_id: UUID,
    job_id: str,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-188 nivel 3 — la IA interpreta el archivo completo (headers
    crípticos, secciones como filas, indentación sin WBS) y propone un
    plan estructurado. La propuesta se guarda en el job de Redis; el
    usuario la revisa en el preview y el confirm la persiste con
    `use_ai_structure=true`. No toca la DB.
    """
    import base64
    from dataclasses import asdict

    from fastapi import HTTPException

    tenant_id = _tenant(cu)
    await _ensure_project(db, project_id, tenant_id)

    tenant_cfg = await load_tenant_ai(db, tenant_id)
    if tenant_cfg.mode == "disabled":
        raise business_rule(
            "La interpretación con IA requiere IA habilitada para el tenant",
            code="AI_DISABLED",
        )

    preview = load_preview(job_id)
    if preview is None:
        raise HTTPException(status_code=410, detail={"code": "PREVIEW_EXPIRED"})
    if (
        preview.get("tenant_id") != str(tenant_id)
        or preview.get("project_id") != str(project_id)
    ):
        raise not_found("Preview job")
    if preview.get("user_id") != str(cu.id):
        raise forbidden()

    source = preview["source"]
    if source not in ("xlsx", "csv"):
        raise business_rule(
            "La interpretación IA aplica a XLSX/CSV (MPP/XML ya vienen "
            "estructurados)",
            code="AI_STRUCTURE_UNSUPPORTED_SOURCE",
        )
    try:
        data = base64.b64decode(preview["file_b64"])
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "PREVIEW_DECODE_FAILED", "hint": str(exc)[:200]},
        )

    rows = extract_raw_rows(source, data, sheet=preview.get("sheet"))
    tasks = await ai_propose_structure(
        rows, tenant_cfg=tenant_cfg, tenant_id=str(tenant_id)
    )
    if not tasks:
        raise business_rule(
            "La IA no pudo interpretar el archivo. Probá el mapeo manual "
            "de columnas.",
            code="AI_NO_PROPOSAL",
        )

    # Persistir la propuesta en el job (el confirm la usa tal cual —
    # lo que el usuario ve en el preview es lo que se importa).
    preview["ai_tasks"] = [asdict(t) for t in tasks]
    save_preview(job_id, preview)

    await write_audit(
        db,
        action="tasks.import_ai_structure",
        module="tasks",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project",
        entity_id=str(project_id),
        details={"job_id": job_id, "source": source, "proposed": len(tasks)},
    )
    await db.commit()

    fake_result = XlsxParseResult(tasks=tasks)
    return {
        "task_count": len(tasks),
        "warnings": _collect_import_warnings(fake_result),
        "parsed_preview": _serialize_parsed_tasks(tasks),
    }


@router.post("/projects/{project_id}/tasks/import/{job_id}/confirm")
async def import_confirm(
    project_id: UUID,
    job_id: str,
    body: ImportConfirmBody,
    cu: CurrentUser = Depends(require_authenticated()),
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

    if body.use_ai_structure:
        # US-188 nivel 3: la fuente de verdad es la propuesta IA que el
        # usuario ya revisó en el preview, no el archivo re-parseado.
        stored = preview.get("ai_tasks") or []
        if not stored:
            raise business_rule(
                "El job no tiene propuesta de IA — generála primero con "
                "/import/{job_id}/ai-structure",
                code="AI_STRUCTURE_MISSING",
            )
        parse_result = XlsxParseResult(
            tasks=[
                ParsedTask(
                    row_number=int(d.get("row_number") or 0),
                    name=str(d.get("name") or "").strip(),
                    wbs=(str(d["wbs"]).strip() or None)
                    if d.get("wbs") is not None
                    else None,
                    start_date=_coerce_date(d.get("start_date")),
                    end_date=_coerce_date(d.get("end_date")),
                    duration_days=d.get("duration_days"),
                    progress=int(d.get("progress") or 0),
                    status=d.get("status"),
                    is_milestone=bool(d.get("is_milestone")),
                )
                for d in stored
                if str(d.get("name") or "").strip()
            ]
        )
    else:
        # Mapping override solo aplica a XLSX/CSV (MPP/XML ya vienen
        # normalizados por sus parsers propios).
        if body.mapping and source in ("xlsx", "csv"):
            if "name" not in body.mapping:
                # 422 (no 400) — el body es válido sintácticamente, lo que
                # falla es la regla de negocio "name es obligatorio".
                raise business_rule(
                    "El mapping debe incluir el campo obligatorio 'name'",
                    code="MAPPING_MISSING_NAME",
                )
            columns_override = body.mapping
        else:
            columns_override = None

        try:
            parse_result = _parse_for_preview(
                source, data, sheet=sheet, columns_override=columns_override
            )
        except ValueError as exc:
            raise business_rule(
                f"archivo {source.upper()} inválido al confirmar: {exc}"
            )

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
            # ENH-134: propaga criticidad/booleano y área para que el
            # confirm los aplique (antes se perdían al no copiarse al shim).
            self.criticality = getattr(pt, "criticality", None)
            self.is_critical = getattr(pt, "is_critical", None)
            self.area_raw = getattr(pt, "area_raw", None)
            # BUG-090: responsable, hito relacionado y predecesoras — la
            # plantilla los promete y el confirm los descartaba.
            self.resources_raw = getattr(pt, "resources_raw", None)
            self.related_milestone_wbs = getattr(pt, "related_milestone_wbs", None)
            self.predecessors_raw = getattr(pt, "predecessors_raw", None)
            # ENH-191: estado normalizado (None → default not_started).
            self.status = getattr(pt, "status", None)
            # US-188: crudo para normalización IA de no reconocidos.
            self.status_raw = getattr(pt, "status_raw", None)
            self.predecessors: list = []

    parsed = [_TaskShim(t) for t in parse_result.tasks]

    # ENH-134: resolución de "Área Responsable" (texto) → area_id contra
    # las áreas del tenant (match case-insensitive por nombre).
    from app.models.area import Area as _Area

    _area_rows = (
        await db.execute(
            select(_Area.id, _Area.name).where(_Area.tenant_id == str(tenant_id))
        )
    ).all()
    _area_by_name = {(r.name or "").strip().lower(): str(r.id) for r in _area_rows}

    def _resolve_area(raw: object) -> str | None:
        if not raw:
            return None
        return _area_by_name.get(str(raw).strip().lower())

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
            # BUG-078: (project_id, external_id) no es único. Un plan con
            # WBS repetidos —o un import previo— deja varias filas con el
            # mismo external_id; scalar_one_or_none() reventaba con
            # MultipleResultsFound (500 "no se pudo conectar" al subir).
            # Tomamos la primera de forma determinista en vez de fallar.
            existing = (
                await db.execute(
                    select(Task)
                    .where(
                        Task.project_id == p.id, Task.external_id == pt.external_id
                    )
                    .order_by(Task.id)
                )
            ).scalars().first()
        if existing is not None:
            existing.name = pt.name
            existing.wbs = pt.wbs
            existing.start_date = pt.start_date
            existing.end_date = pt.end_date
            existing.duration_days = pt.duration_days
            existing.progress = pt.progress
            existing.is_milestone = pt.is_milestone
            existing.source = source_label
            existing.outline_level = compute_outline_level(pt.wbs)
            # ENH-191: estado del archivo manda solo si vino reconocido.
            if getattr(pt, "status", None):
                existing.status = pt.status
            # US-096: criticidad opcional desde la plantilla.
            crit = _normalize_criticality(getattr(pt, "criticality", None))
            if crit:
                existing.criticality = crit
            # ENH-097: is_critical viene explicito de la plantilla, o se
            # deriva del enum criticality (high/critical → true).
            parsed_ic = getattr(pt, "is_critical", None)
            if parsed_ic is not None:
                existing.is_critical = bool(parsed_ic)
            elif crit:
                existing.is_critical = crit in ("high", "critical")
            # ENH-134: área responsable resuelta por nombre.
            resolved_area = _resolve_area(getattr(pt, "area_raw", None))
            if resolved_area is not None:
                existing.area_id = resolved_area
            created[pt.external_id] = existing
        else:
            crit = _normalize_criticality(getattr(pt, "criticality", None))
            parsed_ic = getattr(pt, "is_critical", None)
            if parsed_ic is not None:
                ic_value = bool(parsed_ic)
            else:
                ic_value = (crit or "medium") in ("high", "critical")
            t = Task(
                tenant_id=str(tenant_id), project_id=str(p.id),
                name=pt.name, wbs=pt.wbs,
                start_date=pt.start_date, end_date=pt.end_date,
                duration_days=pt.duration_days, progress=pt.progress,
                is_milestone=pt.is_milestone,
                # ENH-191: estado importado (default not_started).
                status=getattr(pt, "status", None) or "not_started",
                source=source_label, external_id=pt.external_id,
                imported_at=datetime.now(UTC),
                outline_level=compute_outline_level(pt.wbs),
                criticality=crit or "medium",
                is_critical=ic_value,
                area_id=_resolve_area(getattr(pt, "area_raw", None)),
            )
            db.add(t)
            await db.flush()
            created[pt.external_id] = t

    # ------------------------------------------------------------------
    # BUG-090 — aplicar los campos que la hoja Instrucciones de la
    # plantilla promete y el confirm descartaba silenciosamente.
    # ------------------------------------------------------------------
    from difflib import SequenceMatcher

    from app.models.area import Actor as _Actor

    _actor_rows = (
        await db.execute(
            select(_Actor).where(_Actor.tenant_id == str(tenant_id))
        )
    ).scalars().all()

    def _match_actor(raw: object) -> str | None:
        """Responsable → actor del pool por nombre/email: exacto
        case-insensitive o fuzzy ≥ 0.85 (promesa de la plantilla)."""
        if not raw:
            return None
        s = str(raw).strip().lower()
        if not s:
            return None
        best: str | None = None
        best_ratio = 0.0
        for a in _actor_rows:
            for cand in (a.name, a.email):
                if not cand:
                    continue
                c = str(cand).strip().lower()
                if c == s:
                    return str(a.id)
                ratio = SequenceMatcher(None, s, c).ratio()
                if ratio > best_ratio:
                    best, best_ratio = str(a.id), ratio
        return best if best_ratio >= 0.85 else None

    # Primera ocurrencia gana ante WBS duplicados (consistente con merge).
    _by_wbs: dict[str, Task] = {}
    for _t in created.values():
        if _t.wbs and _t.wbs not in _by_wbs:
            _by_wbs[_t.wbs] = _t

    preds_skipped: list[str] = []
    dep_count = 0
    # US-188 nivel 2: valores que la heurística no resolvió — candidatos
    # a normalización IA post-loop.
    pending_status: list[tuple[str, Task]] = []
    pending_resource: list[tuple[str, Task]] = []
    for pt in parsed:
        t = created.get(pt.external_id)
        if t is None:
            continue
        # Fin vacío + Inicio + Duración → Fin calculado (días inclusivos).
        if (
            t.end_date is None
            and t.start_date is not None
            and (t.duration_days or 0) > 0
        ):
            t.end_date = t.start_date + timedelta(days=(t.duration_days or 1) - 1)
        # Responsable → actor del pool (assignee_actor_id, flujo ENH-079).
        raw_resource = getattr(pt, "resources_raw", None)
        resolved_actor = _match_actor(raw_resource)
        if resolved_actor is not None:
            t.assignee_actor_id = resolved_actor
        elif raw_resource:
            pending_resource.append((str(raw_resource).strip(), t))
        # Estado presente pero no reconocido por la heurística.
        if getattr(pt, "status", None) is None and getattr(pt, "status_raw", None):
            pending_status.append((str(pt.status_raw), t))
        # Hito Relacionado → resolución por WBS (solo hitos reales).
        rel = getattr(pt, "related_milestone_wbs", None)
        if rel:
            target = _by_wbs.get(str(rel).strip())
            if target is not None and target.is_milestone and target.id != t.id:
                t.related_milestone_id = str(target.id)
        # Predecesoras: CSV de WBS → filtra existentes/self/dupes y valida
        # ciclos con las ya asignadas. Best-effort: un ciclo no aborta el
        # import, solo omite las predecesoras de esa tarea.
        raw_preds = getattr(pt, "predecessors_raw", None)
        if raw_preds and t.wbs:
            tokens = [
                tok.strip()
                for tok in str(raw_preds).replace(";", ",").split(",")
                if tok.strip()
            ]
            cleaned = []
            for tok in tokens:
                if tok != t.wbs and tok in _by_wbs and tok not in cleaned:
                    cleaned.append(tok)
            if cleaned:
                try:
                    t.predecessors = validate_predecessors(
                        cleaned, _by_wbs, t.wbs
                    )
                except Exception:
                    preds_skipped.append(t.wbs)
                    continue
                for tok in t.predecessors or []:
                    pre = _by_wbs.get(tok)
                    if pre is None:
                        continue
                    if body.strategy == "merge":
                        # uq_task_dep: en merge la dependencia puede ya
                        # existir de un import previo.
                        dup = (
                            await db.execute(
                                select(TaskDependency).where(
                                    TaskDependency.predecessor_id == pre.id,
                                    TaskDependency.successor_id == t.id,
                                )
                            )
                        ).scalar_one_or_none()
                        if dup is not None:
                            continue
                    db.add(
                        TaskDependency(
                            predecessor_id=str(pre.id),
                            successor_id=str(t.id),
                            type="FS",
                            lag_days=0,
                        )
                    )
                    dep_count += 1

    if any(t.predecessors for t in created.values()):
        await recompute_successors_for_project(db, str(project_id))
    if preds_skipped:
        errors.append(
            {
                "error": (
                    "Predecesoras omitidas por ciclo de dependencias en: "
                    + ", ".join(preds_skipped[:10])
                ),
            }
        )

    # ------------------------------------------------------------------
    # US-188 nivel 2 — normalización IA de lo que la heurística no
    # resolvió. Best-effort: si la IA está deshabilitada o falla, los
    # estados quedan en not_started y los responsables sin asignar.
    # ------------------------------------------------------------------
    ai_normalized = {"statuses": 0, "resources": 0}
    if pending_status or pending_resource:
        tenant_cfg = await load_tenant_ai(db, tenant_id)
        if tenant_cfg.mode != "disabled":
            if pending_status:
                status_map = await ai_normalize_statuses(
                    [raw for raw, _ in pending_status],
                    tenant_cfg=tenant_cfg,
                    tenant_id=str(tenant_id),
                )
                for raw, task in pending_status:
                    mapped = status_map.get(raw)
                    if mapped:
                        task.status = mapped
                        ai_normalized["statuses"] += 1
            if pending_resource:
                name_to_id = {
                    a.name: str(a.id) for a in _actor_rows if a.name
                }
                resource_map = await ai_match_resources(
                    [raw for raw, _ in pending_resource],
                    list(name_to_id.keys()),
                    tenant_cfg=tenant_cfg,
                    tenant_id=str(tenant_id),
                )
                for raw, task in pending_resource:
                    actor_id = name_to_id.get(resource_map.get(raw, ""))
                    if actor_id:
                        task.assignee_actor_id = actor_id
                        ai_normalized["resources"] += 1

    # ENH-109: registrar el Plan vivo en `project_artifacts` con el
    # source_format detectado, para que `GET /plan/download` regenere
    # en el formato origen. UNIQUE(project_id, type='plan') → upsert.
    plan_format = "mpp" if source == "mpp" else ("csv" if source == "csv" else "xlsx")
    existing_art = (
        await db.execute(
            select(ProjectArtifact).where(
                ProjectArtifact.project_id == str(project_id),
                ProjectArtifact.type == "plan",
            )
        )
    ).scalar_one_or_none()
    if existing_art is None:
        db.add(
            ProjectArtifact(
                tenant_id=str(tenant_id),
                project_id=str(project_id),
                type="plan",
                source_format=plan_format,
                filename=preview.get("filename") or None,
                size_bytes=len(data),
                created_by=cu.id,
            )
        )
    else:
        existing_art.source_format = plan_format
        existing_art.filename = preview.get("filename") or existing_art.filename
        existing_art.size_bytes = len(data)
        existing_art.created_by = cu.id

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
        # BUG-090: ahora las predecesoras de la plantilla SÍ crean
        # dependencias (JSON predecessors + TaskDependency FS).
        "dependencies_created": dep_count,
        "errors": errors,
        # BUG-088: mismos avisos que el preview, re-computados sobre el
        # mapping definitivo (el override puede cambiar la columna WBS).
        "warnings": _collect_import_warnings(parse_result),
        # US-188: cuántos valores normalizó la IA (0 si deshabilitada).
        "ai_normalized": ai_normalized,
        "strategy": body.strategy,
        "source": source_label,
    }


@router.get("/projects/{project_id}/gantt")
async def gantt_view(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _ensure_project(db, project_id, tenant_id)
    tasks = (
        await db.execute(select(Task).where(Task.project_id == str(project_id)))
    ).scalars().all()
    # BUG-066: el Gantt debe respetar el orden WBS igual que list_tasks.
    tasks = sorted(tasks, key=lambda t: wbs_sort_key(t.wbs))
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


# ENH-053 — Sugerencia de mapeo de columnas asistido por IA.
class SuggestMappingBody(BaseModel):
    headers: list[str] = Field(min_length=1, max_length=50)
    # US-188 nivel 1: filas de muestra para mapear por CONTENIDO.
    sample_rows: list[list[str | None]] | None = Field(
        default=None, max_length=5
    )


class SuggestMappingItem(BaseModel):
    field: str | None
    confidence: float
    source: str  # "ai" | "heuristic" | "none"


class SuggestMappingResponse(BaseModel):
    suggestions: dict[str, SuggestMappingItem]
    system_fields: list[str]
    ai_used: bool


@router.post(
    "/projects/{project_id}/tasks/import/suggest-mapping",
    response_model=SuggestMappingResponse,
)
async def suggest_import_mapping(
    project_id: UUID,
    body: SuggestMappingBody,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-053: dado un set de headers detectados por el wizard, devuelve
    una sugerencia de mapeo `{header: {field, confidence, source}}`.

    - Heurística siempre corre (sinónimos hardcoded en español + inglés).
    - Si `tenant.ai_mode != disabled`, llama al LLM del tenant para
      refinar; si la IA falla la heurística queda como fallback.
    """
    tenant_id = _tenant(cu)
    await _ensure_project(db, project_id, tenant_id)
    tenant_cfg = await load_tenant_ai(db, tenant_id)
    suggestions = await suggest_column_mapping(
        body.headers,
        tenant_cfg=tenant_cfg,
        platform_groq_config=None,
        tenant_id=str(tenant_id),
        sample_rows=body.sample_rows,
    )
    ai_used = any(s.get("source") == "ai" for s in suggestions.values())
    return SuggestMappingResponse(
        suggestions={
            h: SuggestMappingItem(
                field=s.get("field"),
                confidence=float(s.get("confidence", 0.0)),
                source=str(s.get("source", "none")),
            )
            for h, s in suggestions.items()
        },
        system_fields=list(MAPPING_SYSTEM_FIELDS),
        ai_used=ai_used,
    )
