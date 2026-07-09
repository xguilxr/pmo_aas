"""Project Artifacts (US-106 / EP018).

Catálogo estricto de 4 artefactos por proyecto: charter / plan / raid /
organigrama. Whitelist server-side; uploads/queries fuera de esos tipos
devuelven 400 ARTIFACT_TYPE_NOT_ALLOWED.

Endpoints:
- GET  /projects/{id}/artifacts                — lista los 4 tabs con metadata.
- GET  /projects/{id}/artifacts/{type}         — metadata del tipo.
- GET  /projects/{id}/artifacts/{type}/download — descarga (delega).

Charter usa `project_charters` (tabla rica). Plan/RAID/Organigrama usan
`project_artifacts` o delegan al endpoint nativo (ej. RAID export Excel
vía modules.docs_router). Organigrama queda como placeholder en Sprint 18
(ver EP018: depende de redefinición Áreas/Recursos).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import AppError, forbidden, not_found
from app.db.session import get_db
from app.models.modules import Issue, Risk
from app.models.project import Project
from app.models.project_artifact import ARTIFACT_TYPES, ProjectArtifact
from app.models.project_charter import ProjectCharter
from app.models.task import Task

router = APIRouter(prefix="/projects", tags=["project_artifacts"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


def _validate_type(artifact_type: str) -> str:
    t = (artifact_type or "").strip().lower()
    if t not in ARTIFACT_TYPES:
        raise AppError(
            status.HTTP_400_BAD_REQUEST,
            "ARTIFACT_TYPE_NOT_ALLOWED",
            f"Tipo de artefacto no permitido: {artifact_type!r}. "
            f"Whitelist: {', '.join(ARTIFACT_TYPES)}.",
            {"type": artifact_type},
        )
    return t


async def _ensure_project(
    db: AsyncSession, project_id: UUID, tenant_id: UUID
) -> Project:
    p = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == tenant_id,
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")
    return p


class ArtifactMeta(BaseModel):
    type: str
    available: bool
    source_format: str | None = None
    filename: str | None = None
    size_bytes: int | None = None
    download_url: str | None = None
    edit_url: str | None = None
    placeholder: bool = False
    placeholder_reason: str | None = None


class ArtifactList(BaseModel):
    project_id: UUID
    items: list[ArtifactMeta]


def _charter_meta(
    project_id: UUID,
    charter: ProjectCharter | None,
    project_name: str | None = None,
) -> ArtifactMeta:
    from app.services.filename_slug import artifact_filename

    if charter is None:
        return ArtifactMeta(
            type="charter",
            available=False,
            edit_url=f"/api/v1/projects/{project_id}/charter",
        )
    name = charter.project_name or project_name
    return ArtifactMeta(
        type="charter",
        available=True,
        source_format="docx",
        # ENH-092: filename derivado del nombre del proyecto.
        filename=artifact_filename(name, "charter", "docx"),
        download_url=f"/api/v1/projects/{project_id}/charter/download?format=docx",
        edit_url=f"/api/v1/projects/{project_id}/charter",
    )


def _plan_meta(
    project_id: UUID,
    art: ProjectArtifact | None,
    project_name: str | None = None,
) -> ArtifactMeta:
    from app.services.filename_slug import artifact_filename

    if art is None:
        # BUG-057: sin import previo, la descarga regenera la plantilla
        # XLSX desde DB (vacía o con tareas). Reportamos source_format
        # = xlsx para que la UI no caiga al fallback ".bin".
        return ArtifactMeta(
            type="plan",
            available=False,
            source_format="xlsx",
            filename=artifact_filename(project_name, "plan", "xlsx"),
            download_url=f"/api/v1/projects/{project_id}/plan/download?format=auto",
        )
    # ENH-092 / BUG-057: filename derivado del nombre del proyecto + ext
    # canónico del source_format. MPP cae a XLSX en el regenerator (ENH-080).
    ext = (art.source_format or "xlsx").lower()
    if ext == "mpp":
        ext = "xlsx"
    return ArtifactMeta(
        type="plan",
        available=True,
        source_format=art.source_format,
        filename=artifact_filename(project_name, "plan", ext),
        size_bytes=art.size_bytes,
        download_url=f"/api/v1/projects/{project_id}/plan/download?format=auto",
    )


def _raid_meta(project_id: UUID, project_name: str | None = None) -> ArtifactMeta:
    # ENH-152: export RAID = 4 hojas ES (Riesgos/Acciones/Incidencias/
    # Decisiones), mismo archivo que el botón de /raid. Filename legible.
    from app.services.filename_slug import raid_display_filename

    return ArtifactMeta(
        type="raid",
        available=True,
        source_format="xlsx",
        filename=raid_display_filename(project_name),
        download_url=f"/api/v1/projects/{project_id}/raid/export",
    )


def _organigrama_meta(project_id: UUID, project_name: str | None = None) -> ArtifactMeta:
    # US-150: Excel con 4 hojas (Áreas/Equipos/Roles/Recursos).
    from app.services.filename_slug import artifact_filename

    return ArtifactMeta(
        type="organigrama",
        available=True,
        source_format="xlsx",
        filename=artifact_filename(project_name, "organigrama", "xlsx"),
        download_url=f"/api/v1/projects/{project_id}/organigrama/export",
    )


@router.get("/{project_id}/artifacts", response_model=ArtifactList)
async def list_artifacts(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    project = await _ensure_project(db, project_id, tenant_id)

    charter = (
        await db.execute(
            select(ProjectCharter).where(ProjectCharter.project_id == str(project_id))
        )
    ).scalar_one_or_none()

    plan_art = (
        await db.execute(
            select(ProjectArtifact).where(
                ProjectArtifact.project_id == str(project_id),
                ProjectArtifact.type == "plan",
            )
        )
    ).scalar_one_or_none()

    return ArtifactList(
        project_id=project_id,
        items=[
            _charter_meta(project_id, charter, project.name),
            _plan_meta(project_id, plan_art, project.name),
            _raid_meta(project_id, project.name),
            _organigrama_meta(project_id, project.name),
        ],
    )


@router.get("/{project_id}/artifacts/{artifact_type}", response_model=ArtifactMeta)
async def get_artifact(
    project_id: UUID,
    artifact_type: str,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    t = _validate_type(artifact_type)
    tenant_id = _tenant(cu)
    project = await _ensure_project(db, project_id, tenant_id)

    if t == "charter":
        charter = (
            await db.execute(
                select(ProjectCharter).where(
                    ProjectCharter.project_id == str(project_id)
                )
            )
        ).scalar_one_or_none()
        return _charter_meta(project_id, charter, project.name)

    if t == "plan":
        art = (
            await db.execute(
                select(ProjectArtifact).where(
                    ProjectArtifact.project_id == str(project_id),
                    ProjectArtifact.type == "plan",
                )
            )
        ).scalar_one_or_none()
        return _plan_meta(project_id, art, project.name)

    if t == "raid":
        return _raid_meta(project_id, project.name)

    return _organigrama_meta(project_id, project.name)


@router.get("/{project_id}/plan/download")
async def download_plan(
    project_id: UUID,
    format: str = "auto",
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-080: regenera el archivo del Plan on-demand desde DB.

    `format=auto` (default) usa el `source_format` registrado en
    `project_artifacts.plan` (último import). Si no hay artefacto previo,
    cae a XLSX (plantilla US-096). `format=xlsx|csv|mpp` fuerza el formato.

    MPP no es soportado para escritura (MPXJ Pro requerido); en ese caso
    se regenera en XLSX y se devuelve el header
    `X-Plan-Format-Fallback: xlsx-mpp-not-supported`.
    """
    from io import BytesIO
    from urllib.parse import quote

    from fastapi.responses import StreamingResponse

    from app.services.plan_regenerator import regenerate_for_format

    tenant_id = _tenant(cu)
    project = await _ensure_project(db, project_id, tenant_id)

    art = (
        await db.execute(
            select(ProjectArtifact).where(
                ProjectArtifact.project_id == str(project_id),
                ProjectArtifact.type == "plan",
            )
        )
    ).scalar_one_or_none()

    fmt = (format or "auto").lower()
    if fmt == "auto":
        fmt = (art.source_format if art else None) or "xlsx"
    if fmt not in ("xlsx", "csv", "mpp", "template"):
        raise AppError(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_FORMAT",
            f"format inválido: {format!r}. Usa auto|xlsx|csv|mpp.",
            {"format": format},
        )

    tasks = (
        await db.execute(
            select(Task)
            .where(Task.project_id == str(project_id))
            .order_by(Task.outline_level.nullslast(), Task.wbs)
        )
    ).scalars().all()

    data, mime, ext, fallback = regenerate_for_format(fmt, list(tasks))

    # ENH-092: filename canónico `{project-slug}-plan.{ext}`.
    from app.services.filename_slug import artifact_filename

    filename = artifact_filename(project.name, "plan", ext)
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
    }
    if fallback:
        headers["X-Plan-Format-Fallback"] = "xlsx-mpp-not-supported"

    return StreamingResponse(BytesIO(data), media_type=mime, headers=headers)


@router.get("/{project_id}/raid/export")
async def export_raid(
    project_id: UUID,
    only: str | None = None,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-152: Excel RAID con 4 hojas en español — Riesgos / Acciones /
    Incidencias / Decisiones — con columnas legibles (nombres de área y
    responsable resueltos a texto) y filename `RAID-[Nombre Proyecto].xlsx`.

    ENH-168: con `?only=risks|actions|incidents|decisions` devuelve un XLSX de
    una sola hoja para ese tipo (filename `{proyecto}-{tipo}.xlsx`). Sin `only`
    devuelve el archivo combinado de 4 hojas (mismo que el módulo Documentos).
    Los 4 tipos RAID son `Risk` + `Issue.type` (action / issue / decision).
    """
    from io import BytesIO
    from urllib.parse import quote

    from fastapi.responses import StreamingResponse

    from app.models.area import Actor, Area
    from app.models.user import User
    from app.services.filename_slug import artifact_filename, raid_display_filename
    from app.services.raid_export import (
        AID_HEADERS,
        RISK_HEADERS,
        XLSX_MIME,
        build_issue_rows,
        build_risk_rows,
        export_raid_xlsx,
        export_single_sheet_xlsx,
    )

    tenant_id = _tenant(cu)
    project = await _ensure_project(db, project_id, tenant_id)

    risks = (
        await db.execute(
            select(Risk)
            .where(
                Risk.project_id == str(project_id),
                Risk.deleted_at.is_(None),
            )
            .order_by(Risk.severity.desc().nullslast(), Risk.identified_at.desc().nullslast())
        )
    ).scalars().all()

    issues = (
        await db.execute(
            select(Issue)
            .where(
                Issue.project_id == str(project_id),
                Issue.deleted_at.is_(None),
            )
            .order_by(Issue.priority.desc().nullslast(), Issue.reported_at.desc())
        )
    ).scalars().all()

    actions = [i for i in issues if i.type == "action"]
    incidents = [i for i in issues if i.type == "issue"]
    decisions = [i for i in issues if i.type == "decision"]

    # Resolver nombres a texto: Responsable área (Area), Responsable
    # (Actor del catálogo, fallback al Usuario).
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

    risk_rows = build_risk_rows(list(risks), area_names, actor_names, user_names)
    action_rows = build_issue_rows(actions, area_names, actor_names, user_names)
    incident_rows = build_issue_rows(incidents, area_names, actor_names, user_names)
    decision_rows = build_issue_rows(decisions, area_names, actor_names, user_names)

    # ENH-168: export individual por tipo.
    single = {
        "risks": ("Riesgos", "riesgos", RISK_HEADERS, risk_rows),
        "actions": ("Acciones", "acciones", AID_HEADERS, action_rows),
        "incidents": ("Incidencias", "incidencias", AID_HEADERS, incident_rows),
        "decisions": ("Decisiones", "decisiones", AID_HEADERS, decision_rows),
    }
    only_key = (only or "").strip().lower()
    if only_key in single:
        title, slug, hdrs, rows = single[only_key]
        data = export_single_sheet_xlsx(title=title, headers=hdrs, rows=rows)
        filename = artifact_filename(project.name, slug, "xlsx")
    else:
        # ENH-152: archivo combinado de 4 hojas. Filename `RAID-[Nombre].xlsx`.
        data = export_raid_xlsx(
            risks_rows=risk_rows,
            actions_rows=action_rows,
            incidents_rows=incident_rows,
            decisions_rows=decision_rows,
        )
        filename = raid_display_filename(project.name)
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
    }
    return StreamingResponse(BytesIO(data), media_type=XLSX_MIME, headers=headers)


@router.get("/{project_id}/changes/export")
async def export_changes(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-186: Excel de 1 hoja "Cambios" en español (folio, título, tipo,
    estado, solicitado por, fecha solicitud, aprobado por, fecha aprobación,
    impacto). Mismo patrón que `/raid/export` (ENH-152): servicio openpyxl +
    descarga autenticada."""
    from io import BytesIO
    from urllib.parse import quote

    from fastapi.responses import StreamingResponse

    from app.models.modules import ChangeRequest
    from app.models.user import User
    from app.services.change_export import XLSX_MIME, build_change_rows, export_changes_xlsx
    from app.services.filename_slug import artifact_filename

    tenant_id = _tenant(cu)
    project = await _ensure_project(db, project_id, tenant_id)

    changes = (
        await db.execute(
            select(ChangeRequest)
            .where(
                ChangeRequest.project_id == str(project_id),
                ChangeRequest.deleted_at.is_(None),
            )
            .order_by(ChangeRequest.requested_at.desc())
        )
    ).scalars().all()

    user_ids = {str(c.requested_by) for c in changes if c.requested_by}
    user_ids |= {str(c.approved_by) for c in changes if c.approved_by}
    user_names = (
        {
            str(u.id): (u.full_name or u.email)
            for u in (
                await db.execute(select(User).where(User.id.in_(user_ids)))
            ).scalars().all()
        }
        if user_ids
        else {}
    )

    rows = build_change_rows(list(changes), user_names)
    data = export_changes_xlsx(rows)
    filename = artifact_filename(project.name, "cambios", "xlsx")
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
    }
    return StreamingResponse(BytesIO(data), media_type=XLSX_MIME, headers=headers)


@router.get("/{project_id}/lessons/export")
async def export_lessons(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-187: Excel de 1 hoja "Lecciones" en español (folio, lección,
    descripción, categoría, fase, responsable, recomendación, tags, estado).
    Mismo patrón que `/changes/export` (ENH-186): servicio openpyxl +
    descarga autenticada."""
    from io import BytesIO
    from urllib.parse import quote

    from fastapi.responses import StreamingResponse

    from app.models.area import Actor
    from app.models.modules import Lesson
    from app.services.filename_slug import artifact_filename
    from app.services.lessons_export import (
        XLSX_MIME,
        build_lesson_rows,
        export_lessons_xlsx,
    )

    tenant_id = _tenant(cu)
    project = await _ensure_project(db, project_id, tenant_id)

    lessons = (
        await db.execute(
            select(Lesson)
            .where(
                Lesson.project_id == str(project_id),
                Lesson.deleted_at.is_(None),
            )
            .order_by(Lesson.created_at.desc())
        )
    ).scalars().all()

    actor_ids = {str(l.owner_actor_id) for l in lessons if l.owner_actor_id}
    actor_names = (
        {
            str(a.id): a.name
            for a in (
                await db.execute(select(Actor).where(Actor.id.in_(actor_ids)))
            ).scalars().all()
        }
        if actor_ids
        else {}
    )

    rows = build_lesson_rows(list(lessons), actor_names)
    data = export_lessons_xlsx(rows)
    filename = artifact_filename(project.name, "lecciones", "xlsx")
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
    }
    return StreamingResponse(BytesIO(data), media_type=XLSX_MIME, headers=headers)


@router.get("/{project_id}/organigrama/export")
async def export_organigrama(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-150: Excel con 4 hojas — Áreas, Equipos, Roles, Recursos.

    El scope de áreas/recursos es el visible para el proyecto vía
    `area_assignments` (global + organización + programa + proyecto).
    Roles es el catálogo tenant completo.
    """
    from io import BytesIO
    from urllib.parse import quote

    from fastapi.responses import StreamingResponse
    from sqlalchemy import or_

    from app.models.area import Actor, Area, AreaAssignment, Team
    from app.models.project_role import ProjectRole
    from app.services.filename_slug import artifact_filename
    from app.services.organigrama_export import XLSX_MIME, export_organigrama_xlsx

    tenant_id = _tenant(cu)
    project = await _ensure_project(db, project_id, tenant_id)

    # Áreas visibles para el proyecto (cascada US-103).
    scope_filters = [AreaAssignment.is_global.is_(True), AreaAssignment.project_id == str(project_id)]
    if project.organization_id:
        scope_filters.append(AreaAssignment.organization_id == str(project.organization_id))
    if project.program_id:
        scope_filters.append(AreaAssignment.program_id == str(project.program_id))
    area_ids = set(
        (
            await db.execute(
                select(AreaAssignment.area_id).where(
                    AreaAssignment.tenant_id == tenant_id, or_(*scope_filters)
                )
            )
        ).scalars().all()
    )

    areas = (
        await db.execute(
            select(Area).where(Area.id.in_(area_ids)).order_by(Area.name)
        )
    ).scalars().all() if area_ids else []
    area_name = {str(a.id): a.name for a in areas}

    teams = (
        await db.execute(
            select(Team).where(Team.area_id.in_(area_ids)).order_by(Team.name)
        )
    ).scalars().all() if area_ids else []
    team_name = {str(t.id): t.name for t in teams}

    roles = (
        await db.execute(
            select(ProjectRole)
            .where(ProjectRole.tenant_id == tenant_id)
            .order_by(ProjectRole.name)
        )
    ).scalars().all()

    # Recursos: actores ligados a un equipo de esas áreas o directamente al área.
    team_ids = {str(t.id) for t in teams}
    actor_conds = []
    if team_ids:
        actor_conds.append(Actor.team_id.in_(team_ids))
    if area_ids:
        actor_conds.append(Actor.area_id.in_(area_ids))
    actors = (
        await db.execute(
            select(Actor)
            .where(
                Actor.tenant_id == tenant_id,
                Actor.deleted_at.is_(None),
                or_(*actor_conds),
            )
            .order_by(Actor.name)
        )
    ).scalars().all() if actor_conds else []
    actor_name = {str(a.id): a.name for a in actors}

    def _team_area(team_id: str | None) -> str:
        if not team_id:
            return ""
        t = next((x for x in teams if str(x.id) == team_id), None)
        return area_name.get(str(t.area_id), "") if t else ""

    areas_rows = [
        [str(a.id), a.name, a.description or "",
         actor_name.get(str(a.lead_actor_id), "") if a.lead_actor_id else "",
         "Sí" if a.is_active else "No"]
        for a in areas
    ]
    teams_rows = [
        [str(t.id), area_name.get(str(t.area_id), ""), t.name, t.description or "",
         "Sí" if t.is_active else "No"]
        for t in teams
    ]
    roles_rows = [
        [str(r.id), r.name, r.description or "", "Sí" if r.is_active else "No"]
        for r in roles
    ]
    recursos_rows = [
        [
            str(a.id), a.name,
            team_name.get(str(a.team_id), "") if a.team_id else "",
            area_name.get(str(a.area_id), "") if a.area_id else _team_area(str(a.team_id) if a.team_id else None),
            a.job_title or "", a.company or "", a.email or "", a.phone or "",
            actor_name.get(str(a.manager_actor_id), "") if a.manager_actor_id else "",
            "Sí" if a.is_active else "No",
        ]
        for a in actors
    ]

    # US-186: hojas "Recursos (FTE)" + "Uso mensual" con las participaciones
    # activas del proyecto (alertas ≥80% amarillo / >100% rojo por mes).
    from app.models.tenant import Tenant
    from app.services.capacity import monthly_utilization

    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    util = await monthly_utilization(
        db, tenant, scope_type="project", scope_id=str(project_id)
    )

    data = export_organigrama_xlsx(
        areas_rows=areas_rows,
        teams_rows=teams_rows,
        roles_rows=roles_rows,
        recursos_rows=recursos_rows,
        utilization_months=util["months"],
        utilization_rows=util["rows"],
    )

    filename = artifact_filename(project.name, "organigrama", "xlsx")
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
    }
    return StreamingResponse(BytesIO(data), media_type=XLSX_MIME, headers=headers)
