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
from app.models.modules import ChangeRequest, Issue, Lesson, Risk
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
    # ENH-082 (Sprint 19) entregará el export 4-sheets dedicado. Mientras,
    # se expone el endpoint de export RAID actual (modules.docs_router).
    from app.services.filename_slug import artifact_filename

    return ArtifactMeta(
        type="raid",
        available=True,
        source_format="xlsx",
        # ENH-093: filename con nombre de proyecto, no con su UUID.
        filename=artifact_filename(project_name, "raid", "xlsx"),
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
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-082: Excel RAID con 4 sheets dedicados (Risks/Issues/Lessons/Changes).

    Cada sheet con header bold + fondo, freeze pane y autosize. Sheets vacíos
    se incluyen igual con header (CA5). Refleja el estado actual de DB —
    el módulo Documentos (US-106) consume este endpoint en su tab RAIDs.
    """
    from io import BytesIO
    from urllib.parse import quote

    from fastapi.responses import StreamingResponse

    from app.services.raid_export import XLSX_MIME, export_raid_xlsx

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

    data = export_raid_xlsx(
        risks=list(risks),
        issues=list(issues),
        lessons=list(lessons),
        changes=list(changes),
    )

    # ENH-093: filename canónico `{project-slug}-raid.xlsx`.
    from app.services.filename_slug import artifact_filename

    filename = artifact_filename(project.name, "raid", "xlsx")
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

    data = export_organigrama_xlsx(
        areas_rows=areas_rows,
        teams_rows=teams_rows,
        roles_rows=roles_rows,
        recursos_rows=recursos_rows,
    )

    filename = artifact_filename(project.name, "organigrama", "xlsx")
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
    }
    return StreamingResponse(BytesIO(data), media_type=XLSX_MIME, headers=headers)
