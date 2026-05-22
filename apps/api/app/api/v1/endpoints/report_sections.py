"""Report Sections catalog (read-only) — US-120 (EP020 backbone).

Endpoint que expone el catálogo global de secciones atómicas
registradas en `report_sections`. Usado por el Report Builder UI
(US-124) y por el panel de parámetros (US-125).
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.db.session import get_db
from app.models.report_section import ReportSection

router = APIRouter(prefix="/report-sections", tags=["report_sections"])


class ReportSectionRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    category: str
    level: int
    data_shape: dict
    parameters_schema: dict
    composition_mode_default: str
    supports_ia: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[ReportSectionRead])
async def list_report_sections(
    db: AsyncSession = Depends(get_db),
    _cu: CurrentUser = Depends(require_authenticated()),
    category: str | None = Query(default=None),
    level: int | None = Query(default=None, ge=1, le=4),
    enabled: bool | None = Query(default=True),
) -> list[ReportSectionRead]:
    stmt = select(ReportSection).order_by(ReportSection.code)
    if category is not None:
        stmt = stmt.where(ReportSection.category == category)
    if level is not None:
        stmt = stmt.where(ReportSection.level <= level)
    if enabled is not None:
        stmt = stmt.where(ReportSection.enabled == enabled)
    rows = (await db.execute(stmt)).scalars().all()
    return [ReportSectionRead.model_validate(r) for r in rows]
