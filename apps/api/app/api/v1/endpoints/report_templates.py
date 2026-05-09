"""Report Templates — ENH-085.

Plantillas tenant-shared (cross-project) para reusar HTML de reportes
tweakeados por el PM. Distintas de `ai_report_templates` (per-project,
config wizard de IA).

Endpoints:
- GET    /api/v1/report-templates           — lista del tenant.
- POST   /api/v1/report-templates           — crea con name + html_content.
- GET    /api/v1/report-templates/{id}      — detalle.
- PATCH  /api/v1/report-templates/{id}      — edita (creator/admin).
- DELETE /api/v1/report-templates/{id}      — borra (creator/admin).

Audit logs: `report_template.{create,update,delete}`.
"""
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.report_template import ReportTemplate
from app.services.audit import write_audit

router = APIRouter(tags=["report_templates"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


def _is_admin(cu: CurrentUser) -> bool:
    return bool(getattr(cu, "is_admin", False)) or bool(
        getattr(cu, "is_superadmin", False)
    )


class ReportTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    html_content: str = Field(min_length=10)
    is_shared: bool = True


class ReportTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    html_content: str | None = Field(default=None, min_length=10)
    is_shared: bool | None = None


class ReportTemplateRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    html_content: str
    is_shared: bool
    created_by: UUID | None
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReportTemplateMini(BaseModel):
    """Listado: omite html_content para no inflar la respuesta."""

    id: UUID
    name: str
    description: str | None
    is_shared: bool
    created_by: UUID | None
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


@router.get("/report-templates", response_model=list[ReportTemplateMini])
async def list_templates(
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    rows = (
        await db.execute(
            select(ReportTemplate)
            .where(ReportTemplate.tenant_id == str(tenant_id))
            .order_by(ReportTemplate.created_at.desc())
        )
    ).scalars().all()
    # Filtra plantillas no-compartidas que no son del usuario actual.
    visible = [
        t
        for t in rows
        if t.is_shared
        or (t.created_by and str(t.created_by) == str(cu.id))
        or _is_admin(cu)
    ]
    return [ReportTemplateMini.model_validate(t) for t in visible]


@router.post("/report-templates", response_model=ReportTemplateRead, status_code=201)
async def create_template(
    body: ReportTemplateCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = ReportTemplate(
        tenant_id=str(tenant_id),
        name=body.name.strip(),
        description=body.description,
        html_content=body.html_content,
        is_shared=body.is_shared,
        created_by=cu.id,
    )
    db.add(t)
    await db.flush()
    await write_audit(
        db, action="report_template.create", module="reports",
        user_id=cu.id, tenant_id=tenant_id,
        entity_type="report_template", entity_id=str(t.id),
        details={"name": t.name},
    )
    await db.commit()
    return ReportTemplateRead.model_validate(t)


@router.get("/report-templates/{template_id}", response_model=ReportTemplateRead)
async def get_template(
    template_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (
        await db.execute(
            select(ReportTemplate).where(
                ReportTemplate.id == str(template_id),
                ReportTemplate.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Plantilla")
    if not t.is_shared and (
        not t.created_by or str(t.created_by) != str(cu.id)
    ) and not _is_admin(cu):
        raise forbidden("Plantilla privada de otro usuario")
    # Marca de uso para ordenamiento futuro por "más usadas".
    t.last_used_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(t)
    return ReportTemplateRead.model_validate(t)


@router.patch("/report-templates/{template_id}", response_model=ReportTemplateRead)
async def update_template(
    template_id: UUID,
    body: ReportTemplateUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (
        await db.execute(
            select(ReportTemplate).where(
                ReportTemplate.id == str(template_id),
                ReportTemplate.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Plantilla")
    is_creator = bool(t.created_by) and str(t.created_by) == str(cu.id)
    if not (is_creator or _is_admin(cu)):
        raise forbidden("Solo el creador o un admin puede editar")
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(t, k, v)
    await write_audit(
        db, action="report_template.update", module="reports",
        user_id=cu.id, tenant_id=tenant_id,
        entity_type="report_template", entity_id=str(t.id),
    )
    await db.commit()
    await db.refresh(t)
    return ReportTemplateRead.model_validate(t)


@router.delete("/report-templates/{template_id}", status_code=204)
async def delete_template(
    template_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (
        await db.execute(
            select(ReportTemplate).where(
                ReportTemplate.id == str(template_id),
                ReportTemplate.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Plantilla")
    is_creator = bool(t.created_by) and str(t.created_by) == str(cu.id)
    if not (is_creator or _is_admin(cu)):
        raise forbidden("Solo el creador o un admin puede borrar")
    await write_audit(
        db, action="report_template.delete", module="reports",
        user_id=cu.id, tenant_id=tenant_id,
        entity_type="report_template", entity_id=str(t.id),
        details={"name": t.name},
    )
    await db.delete(t)
    await db.commit()
    return None
