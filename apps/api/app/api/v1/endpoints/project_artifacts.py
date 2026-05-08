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

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from fastapi import status

from app.core.errors import AppError, forbidden, not_found
from app.db.session import get_db
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


def _charter_meta(project_id: UUID, charter: ProjectCharter | None) -> ArtifactMeta:
    if charter is None:
        return ArtifactMeta(
            type="charter",
            available=False,
            edit_url=f"/api/v1/projects/{project_id}/charter",
        )
    return ArtifactMeta(
        type="charter",
        available=True,
        source_format="docx",
        download_url=f"/api/v1/projects/{project_id}/charter/download?format=docx",
        edit_url=f"/api/v1/projects/{project_id}/charter",
    )


def _plan_meta(project_id: UUID, art: ProjectArtifact | None) -> ArtifactMeta:
    if art is None:
        return ArtifactMeta(
            type="plan",
            available=False,
            download_url=f"/api/v1/projects/{project_id}/plan/download?format=auto",
        )
    return ArtifactMeta(
        type="plan",
        available=True,
        source_format=art.source_format,
        filename=art.filename,
        size_bytes=art.size_bytes,
        download_url=f"/api/v1/projects/{project_id}/plan/download?format=auto",
    )


def _raid_meta(project_id: UUID) -> ArtifactMeta:
    # ENH-082 (Sprint 19) entregará el export 4-sheets dedicado. Mientras,
    # se expone el endpoint de export RAID actual (modules.docs_router).
    return ArtifactMeta(
        type="raid",
        available=True,
        source_format="xlsx",
        download_url=f"/api/v1/projects/{project_id}/raid/export",
    )


def _organigrama_meta() -> ArtifactMeta:
    return ArtifactMeta(
        type="organigrama",
        available=False,
        placeholder=True,
        placeholder_reason=(
            "Pendiente de redefinición Áreas/Recursos. El cableado funcional "
            "se entregará cuando esa redefinición se complete (post-Sprint 18)."
        ),
    )


@router.get("/{project_id}/artifacts", response_model=ArtifactList)
async def list_artifacts(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _ensure_project(db, project_id, tenant_id)

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
            _charter_meta(project_id, charter),
            _plan_meta(project_id, plan_art),
            _raid_meta(project_id),
            _organigrama_meta(),
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
    await _ensure_project(db, project_id, tenant_id)

    if t == "charter":
        charter = (
            await db.execute(
                select(ProjectCharter).where(
                    ProjectCharter.project_id == str(project_id)
                )
            )
        ).scalar_one_or_none()
        return _charter_meta(project_id, charter)

    if t == "plan":
        art = (
            await db.execute(
                select(ProjectArtifact).where(
                    ProjectArtifact.project_id == str(project_id),
                    ProjectArtifact.type == "plan",
                )
            )
        ).scalar_one_or_none()
        return _plan_meta(project_id, art)

    if t == "raid":
        return _raid_meta(project_id)

    return _organigrama_meta()


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

    safe_name = (project.name or "plan").replace("/", "_")
    filename = f"Plan - {safe_name}.{ext}"
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
    }
    if fallback:
        headers["X-Plan-Format-Fallback"] = "xlsx-mpp-not-supported"

    return StreamingResponse(BytesIO(data), media_type=mime, headers=headers)
