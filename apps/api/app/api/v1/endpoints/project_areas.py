"""CRUD de áreas/actores del proyecto (US-018, EP005, ENH-020, US-062)."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import business_rule, forbidden, not_found
from app.db.session import get_db
from app.models.project import Project
from app.models.project_area import ProjectArea, ProjectAreaResource
from app.models.user import User
from app.schemas.project_area import (
    ProjectAreaCreate,
    ProjectAreaRead,
    ProjectAreaResourceCreate,
    ProjectAreaResourceRead,
    ProjectAreaResourceUpdate,
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
    if data.get("area_leader_id") is not None:
        await _require_tenant_user(db, tenant_id, data["area_leader_id"])
        data["area_leader_id"] = str(data["area_leader_id"])
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


async def _require_tenant_user(
    db: AsyncSession, tenant_id: UUID, user_id: UUID
) -> None:
    """Valida que el user_id pertenezca al tenant actual (evita cross-tenant)."""
    row = (
        await db.execute(
            select(User.id).where(
                User.id == str(user_id), User.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise not_found("Usuario")


async def _get_area(
    db: AsyncSession, tenant_id: UUID, area_id: UUID
) -> ProjectArea:
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
    return area


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
    area = await _get_area(db, tenant_id, area_id)
    data = body.model_dump(exclude_unset=True)
    if "area_leader_id" in data and data["area_leader_id"] is not None:
        await _require_tenant_user(db, tenant_id, data["area_leader_id"])
        data["area_leader_id"] = str(data["area_leader_id"])
    for field, value in data.items():
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
    area = await _get_area(db, tenant_id, area_id)
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


# ============================================================================
# ENH-020 + US-062 — Recursos asignados al área (múltiples)
# ============================================================================


@router.get(
    "/project-areas/{area_id}/resources",
    response_model=list[ProjectAreaResourceRead],
)
async def list_area_resources(
    area_id: UUID,
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("projects", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_area(db, tenant_id, area_id)
    stmt = select(ProjectAreaResource).where(
        ProjectAreaResource.area_id == str(area_id),
        ProjectAreaResource.tenant_id == tenant_id,
    )
    if is_active is not None:
        stmt = stmt.where(ProjectAreaResource.is_active == is_active)
    rows = (
        await db.execute(stmt.order_by(ProjectAreaResource.created_at))
    ).scalars().all()
    return [ProjectAreaResourceRead.model_validate(r) for r in rows]


@router.post(
    "/project-areas/{area_id}/resources",
    response_model=ProjectAreaResourceRead,
    status_code=201,
)
async def create_area_resource(
    area_id: UUID,
    body: ProjectAreaResourceCreate,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    area = await _get_area(db, tenant_id, area_id)
    data = body.model_dump()
    if data.get("user_id") is not None:
        await _require_tenant_user(db, tenant_id, data["user_id"])
        # Si el recurso es interno, evitar duplicados dentro del área.
        dup = (
            await db.execute(
                select(ProjectAreaResource.id).where(
                    ProjectAreaResource.area_id == str(area.id),
                    ProjectAreaResource.user_id == str(data["user_id"]),
                    ProjectAreaResource.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if dup is not None:
            raise business_rule("El usuario ya está asignado como recurso activo")
        data["user_id"] = str(data["user_id"])
    if data.get("email") is not None:
        data["email"] = str(data["email"])
    resource = ProjectAreaResource(
        tenant_id=tenant_id,
        area_id=area.id,
        created_by=str(cu.id),
        **data,
    )
    db.add(resource)
    await db.flush()
    await write_audit(
        db,
        action="project_area_resource.create",
        module="projects",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project_area_resource",
        entity_id=str(resource.id),
        details={
            "area_id": str(area.id),
            "user_id": data.get("user_id"),
            "name": data.get("name"),
        },
    )
    await db.commit()
    return ProjectAreaResourceRead.model_validate(resource)


async def _get_resource(
    db: AsyncSession, tenant_id: UUID, resource_id: UUID
) -> ProjectAreaResource:
    row = (
        await db.execute(
            select(ProjectAreaResource).where(
                ProjectAreaResource.id == str(resource_id),
                ProjectAreaResource.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise not_found("Recurso")
    return row


@router.patch(
    "/project-area-resources/{resource_id}",
    response_model=ProjectAreaResourceRead,
)
async def update_area_resource(
    resource_id: UUID,
    body: ProjectAreaResourceUpdate,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    resource = await _get_resource(db, tenant_id, resource_id)
    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"])
    for field, value in data.items():
        setattr(resource, field, value)
    await write_audit(
        db,
        action="project_area_resource.update",
        module="projects",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project_area_resource",
        entity_id=str(resource.id),
    )
    await db.commit()
    return ProjectAreaResourceRead.model_validate(resource)


@router.delete("/project-area-resources/{resource_id}", status_code=204)
async def delete_area_resource(
    resource_id: UUID,
    cu: CurrentUser = Depends(require_permission("projects", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    resource = await _get_resource(db, tenant_id, resource_id)
    await db.delete(resource)
    await write_audit(
        db,
        action="project_area_resource.delete",
        module="projects",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project_area_resource",
        entity_id=str(resource_id),
    )
    await db.commit()
    return Response(status_code=204)
