"""Render endpoint del Report Builder — US-123 (EP020).

Toma un template (id o code seed), scope (project_id v1.0) y window
opcionales, e invoca :func:`app.services.reports.engine.render_template`.

El response es `{html, json, sections_meta}`. El export PDF vive en
US-130 y se invoca aparte (`?format=pdf` en el mismo endpoint).
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, validation_error
from app.db.session import get_db
from app.services.pdf_renderer import html_to_pdf
from app.services.reports.engine import (
    ReportScope,
    ReportWindow,
    render_template,
)

router = APIRouter(prefix="/report-builder", tags=["report_builder"])


class RenderRequest(BaseModel):
    template: str = Field(
        ...,
        description="Template id (UUID) o code seed (`L3-AVANCE`, ...).",
    )
    project_id: UUID | None = None
    organization_id: UUID | None = None
    program_id: UUID | None = None
    level: int = Field(default=3, ge=1, le=4)
    cut_off_date: date | None = None
    window_days: int = Field(default=14, ge=1, le=365)
    params: dict[str, dict[str, Any]] | None = None


class RenderResponse(BaseModel):
    html: str
    json_data: dict[str, Any] = Field(alias="json")
    sections_meta: list[dict[str, Any]]

    class Config:
        populate_by_name = True


@router.post("/render", response_model=RenderResponse, response_model_by_alias=True)
async def render_report(
    payload: RenderRequest,
    format: str = Query(default="json", pattern="^(json|pdf)$"),
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
):
    """Renderiza una plantilla del Report Builder."""
    tenant_id = cu.effective_tenant_id
    if tenant_id is None:
        raise forbidden("Sin tenant activo")

    if payload.level == 3 and not payload.project_id:
        raise validation_error(
            "project_id es obligatorio para reportes Nivel 3",
            {"project_id": "required"},
        )

    scope = ReportScope(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        organization_id=payload.organization_id,
        program_id=payload.program_id,
        level=payload.level,
    )
    window = ReportWindow(
        cut_off_date=payload.cut_off_date or date.today(),
        window_days=payload.window_days,
    )

    result = await render_template(
        db,
        payload.template,
        scope,
        window,
        params_overrides=payload.params,
    )

    if format == "pdf":
        # US-130 — export PDF reusando el motor compartido.
        pdf_bytes = html_to_pdf(result.html)
        return Response(content=pdf_bytes, media_type="application/pdf")

    return RenderResponse(
        html=result.html,
        json=result.json,
        sections_meta=result.sections_meta,
    )
