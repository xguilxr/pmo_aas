"""Report Builder Templates (read-only) — US-122 (EP020 backbone).

Endpoint que devuelve las plantillas seed (tenant_id=NULL) más las
plantillas custom del tenant del usuario. Las CRUD escrituras quedan
para US-126 (publicar/despublicar al proyecto).
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.db.session import get_db
from app.models.report_builder_template import ReportBuilderTemplate

router = APIRouter(prefix="/report-builder-templates", tags=["report_builder_templates"])


class ReportBuilderTemplateRead(BaseModel):
    id: UUID
    tenant_id: UUID | None
    code: str
    name: str
    description: str | None
    level: int
    composition_mode: str
    section_codes: list[str]
    default_parameters: dict
    is_seed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[ReportBuilderTemplateRead])
async def list_report_builder_templates(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
    level: int | None = Query(default=None, ge=1, le=4),
    include_seed: bool = Query(default=True),
) -> list[ReportBuilderTemplateRead]:
    """Devuelve plantillas seed (tenant_id NULL) + plantillas del tenant."""
    stmt = select(ReportBuilderTemplate).order_by(
        ReportBuilderTemplate.level, ReportBuilderTemplate.code
    )
    conds = []
    if include_seed:
        conds.append(ReportBuilderTemplate.tenant_id.is_(None))
    if cu.effective_tenant_id is not None:
        conds.append(
            ReportBuilderTemplate.tenant_id == cu.effective_tenant_id
        )
    if conds:
        stmt = stmt.where(or_(*conds))
    if level is not None:
        stmt = stmt.where(ReportBuilderTemplate.level == level)
    rows = (await db.execute(stmt)).scalars().all()
    return [ReportBuilderTemplateRead.model_validate(r) for r in rows]
