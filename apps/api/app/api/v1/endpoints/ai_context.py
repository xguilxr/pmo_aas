"""US-185 — Memoria de proyecto para IA: CRUD del contexto persistente.

- GET  /projects/{id}/ai-context — lee la memoria (vacía si no existe).
- PUT  /projects/{id}/ai-context — upsert de context_md / instructions_md
  / auto_summary_md (el PM puede podar el resumen automático).
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
from app.models.project import Project
from app.models.project_ai_context import ProjectAIContext
from app.services.audit import write_audit

router = APIRouter(prefix="/projects/{project_id}/ai-context", tags=["ai-context"])

MAX_LEN = 20000


class AIContextUpdate(BaseModel):
    context_md: str | None = Field(default=None, max_length=MAX_LEN)
    instructions_md: str | None = Field(default=None, max_length=MAX_LEN)
    auto_summary_md: str | None = Field(default=None, max_length=MAX_LEN)


class AIContextRead(BaseModel):
    project_id: UUID
    context_md: str | None = None
    instructions_md: str | None = None
    auto_summary_md: str | None = None
    auto_summary_updated_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


async def _get_project(db: AsyncSession, project_id: UUID, tenant_id: UUID) -> Project:
    p = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == str(tenant_id),
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")
    return p


@router.get("", response_model=AIContextRead)
async def get_ai_context(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    ctx = (
        await db.execute(
            select(ProjectAIContext).where(
                ProjectAIContext.tenant_id == str(tenant_id),
                ProjectAIContext.project_id == str(project_id),
            )
        )
    ).scalar_one_or_none()
    if ctx is None:
        return AIContextRead(project_id=project_id)
    return AIContextRead.model_validate(ctx)


@router.put("", response_model=AIContextRead)
async def upsert_ai_context(
    project_id: UUID,
    body: AIContextUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    ctx = (
        await db.execute(
            select(ProjectAIContext).where(
                ProjectAIContext.tenant_id == str(tenant_id),
                ProjectAIContext.project_id == str(project_id),
            )
        )
    ).scalar_one_or_none()
    fields = body.model_dump(exclude_unset=True)
    if ctx is None:
        ctx = ProjectAIContext(
            tenant_id=str(tenant_id), project_id=str(project_id)
        )
        db.add(ctx)
    for k, v in fields.items():
        setattr(ctx, k, (v.strip() or None) if isinstance(v, str) else v)
    if "auto_summary_md" in fields:
        ctx.auto_summary_updated_at = datetime.now(UTC)
    ctx.updated_by = str(cu.id)
    await write_audit(
        db, action="project.ai_context.updated", module="ai",
        user_id=cu.id, tenant_id=tenant_id,
        entity_type="project", entity_id=str(project_id),
        details={"fields": sorted(fields.keys())},
    )
    await db.commit()
    await db.refresh(ctx)
    return AIContextRead.model_validate(ctx)
