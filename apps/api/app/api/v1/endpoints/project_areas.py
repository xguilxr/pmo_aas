"""CRUD de áreas/actores del proyecto (US-NEW-018, EP005)."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.project import Project
from app.models.project_area import ProjectArea
from app.schemas.project_area import (
    ProjectAreaCreate,
    ProjectAreaRead,
    ProjectAreaUpdate,
)
from app.services.audit import write_audit

router = APIRouter(tags=["project_areas"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


async def _get_project(db: AsyncSession, tenant_id: UUID, project_id: UUID) -> Project:
    p = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")
    return p


@router.get(
    "/projects/{project_id}/areas", response_model=list[ProjectAreaRead]
)
async def list_areas(
    project_id: UUID,
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    type: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("projects", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, tenant_id, project_id)
    stmt = select(ProjectArea).where(
        ProjectArea.tenant_id == tenant_id,
        ProjectArea.project_id == str(project_id),
    )
    if q:
        stmt = stmt.where(func.lower(ProjectArea.name).like(f"%{q.lower()}%"))
    if is_active is not None:
        stmt = stmt.where(ProjectArea.is_active == is_active)
    if type:
        stmt = stmt.where(ProjectArea.type == type)
    rows = (await db.execute(stmt.order_by(ProjectArea.name))).scalars().all()
    return [ProjectAreaRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/areas",
    response_model=ProjectAreaRead,
    status_code=201,
)
async def create_area(
    project_id: UUID,
    body: ProjectAreaCreate,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    data = body.model_dump()
    if data.get("contact_email") is not None:
        data["contact_email"] = str(data["contact_email"])
    area = ProjectArea(
        tenant_id=tenant_id,
        project_id=project.id,
        created_by=str(cu.id),
        **data,
    )
    db.add(area)
    await db.flush()
    await write_audit(
        db,
        action="project_area.create",
        module="projects",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project_area",
        entity_id=str(area.id),
        details={"name": body.name, "type": body.type},
    )
    await db.commit()
    return ProjectAreaRead.model_validate(area)


@router.get("/project-areas/{area_id}", response_model=ProjectAreaRead)
async def get_area(
    area_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    area = (
        await db.execute(
            select(ProjectArea).where(
                ProjectArea.id == str(area_id),
                ProjectArea.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if area is None:
        raise not_found("Área")
    return ProjectAreaRead.model_validate(area)


@router.patch("/project-areas/{area_id}", response_model=ProjectAreaRead)
async def update_area(
    area_id: UUID,
    body: ProjectAreaUpdate,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    area = (
        await db.execute(
            select(ProjectArea).where(
                ProjectArea.id == str(area_id),
                ProjectArea.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if area is None:
        raise not_found("Área")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "contact_email" and value is not None:
            value = str(value)
        setattr(area, field, value)
    await write_audit(
        db,
        action="project_area.update",
        module="projects",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project_area",
        entity_id=str(area.id),
    )
    await db.commit()
    return ProjectAreaRead.model_validate(area)


@router.delete("/project-areas/{area_id}", status_code=204)
async def delete_area(
    area_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    area = (
        await db.execute(
            select(ProjectArea).where(
                ProjectArea.id == str(area_id),
                ProjectArea.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if area is None:
        raise not_found("Área")
    await db.delete(area)
    await write_audit(
        db,
        action="project_area.delete",
        module="projects",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project_area",
        entity_id=str(area_id),
    )
    await db.commit()
    return Response(status_code=204)
