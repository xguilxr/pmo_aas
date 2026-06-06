"""Report Builder Templates CRUD — US-122 + US-126 (EP020).

`GET /report-builder-templates` devuelve:
- Plantillas seed (`tenant_id=NULL`, `is_seed=True`) — visibles para todos.
- Plantillas privadas del current user (`owner_id == current_user`).
- Plantillas publicadas al proyecto (`project_id == ?project_id`,
  `visibility == 'project'`).

`POST` crea una plantilla con `visibility ∈ {private, project}`.
`PATCH` permite cambiar `visibility` (publicar/despublicar) sólo al
owner. `DELETE` también sólo al owner.
"""
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, not_found, validation_error
from app.db.session import get_db
from app.models.report_builder_template import ReportBuilderTemplate

router = APIRouter(prefix="/report-builder-templates", tags=["report_builder_templates"])


VISIBILITY_VALUES = ("private", "project", "tenant")


def _coerce_json(value: Any) -> Any:
    """BUG-063: defensa contra columnas JSON double-encoded (guardadas
    como string por las migraciones de seed). Parsea strings; deja el
    resto intacto."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


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
    owner_id: UUID | None = None
    project_id: UUID | None = None
    visibility: str = "private"
    created_at: datetime
    updated_at: datetime

    @field_validator("section_codes", mode="before")
    @classmethod
    def _parse_codes(cls, v: Any) -> Any:
        coerced = _coerce_json(v)
        return coerced if isinstance(coerced, list) else []

    @field_validator("default_parameters", mode="before")
    @classmethod
    def _parse_params(cls, v: Any) -> Any:
        coerced = _coerce_json(v)
        return coerced if isinstance(coerced, dict) else {}

    class Config:
        from_attributes = True


class ReportBuilderTemplateCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    level: int = Field(..., ge=1, le=4)
    composition_mode: str = Field(..., pattern="^(A|B)$")
    section_codes: list[str] = Field(default_factory=list)
    default_parameters: dict = Field(default_factory=dict)
    visibility: str = Field(default="private", pattern="^(private|project|tenant)$")
    project_id: UUID | None = None


class ReportBuilderTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    composition_mode: str | None = Field(default=None, pattern="^(A|B)$")
    section_codes: list[str] | None = None
    default_parameters: dict | None = None
    visibility: str | None = Field(
        default=None, pattern="^(private|project|tenant)$"
    )
    project_id: UUID | None = None


@router.get("", response_model=list[ReportBuilderTemplateRead])
async def list_report_builder_templates(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
    level: int | None = Query(default=None, ge=1, le=4),
    include_seed: bool = Query(default=True),
    project_id: UUID | None = Query(default=None),
) -> list[ReportBuilderTemplateRead]:
    """US-122 + US-126 — lista plantillas visibles para el current user."""
    stmt = select(ReportBuilderTemplate).order_by(
        ReportBuilderTemplate.level, ReportBuilderTemplate.code
    )
    conds = []
    if include_seed:
        conds.append(ReportBuilderTemplate.tenant_id.is_(None))
    if cu.effective_tenant_id is not None:
        # Plantillas privadas del user actual.
        conds.append(
            and_(
                ReportBuilderTemplate.tenant_id == cu.effective_tenant_id,
                ReportBuilderTemplate.owner_id == cu.id,
            )
        )
        # Plantillas publicadas al proyecto solicitado.
        if project_id is not None:
            conds.append(
                and_(
                    ReportBuilderTemplate.tenant_id == cu.effective_tenant_id,
                    ReportBuilderTemplate.project_id == str(project_id),
                    ReportBuilderTemplate.visibility == "project",
                )
            )
        # Plantillas tenant-wide (visibility=tenant).
        conds.append(
            and_(
                ReportBuilderTemplate.tenant_id == cu.effective_tenant_id,
                ReportBuilderTemplate.visibility == "tenant",
            )
        )
    if conds:
        stmt = stmt.where(or_(*conds))
    if level is not None:
        stmt = stmt.where(ReportBuilderTemplate.level == level)
    rows = (await db.execute(stmt)).scalars().all()
    return [ReportBuilderTemplateRead.model_validate(r) for r in rows]


@router.post("", response_model=ReportBuilderTemplateRead, status_code=201)
async def create_report_builder_template(
    payload: ReportBuilderTemplateCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
) -> ReportBuilderTemplateRead:
    """US-126 — crea plantilla custom (private o project visibility)."""
    if cu.effective_tenant_id is None:
        raise forbidden("Sin tenant activo")

    if payload.visibility == "project" and payload.project_id is None:
        raise validation_error(
            "project_id es obligatorio cuando visibility='project'",
            {"project_id": "required"},
        )

    row = ReportBuilderTemplate(
        tenant_id=str(cu.effective_tenant_id),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        level=payload.level,
        composition_mode=payload.composition_mode,
        section_codes=payload.section_codes,
        default_parameters=payload.default_parameters,
        is_seed=False,
        owner_id=cu.id,
        project_id=str(payload.project_id) if payload.project_id else None,
        visibility=payload.visibility,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ReportBuilderTemplateRead.model_validate(row)


async def _load_owned(db, cu, template_id) -> ReportBuilderTemplate:
    row = (
        await db.execute(
            select(ReportBuilderTemplate).where(
                ReportBuilderTemplate.id == str(template_id)
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise not_found("Plantilla")
    if row.is_seed:
        raise forbidden("Las plantillas seed son read-only")
    if str(row.owner_id) != str(cu.id):
        raise forbidden("Sólo el owner puede modificar la plantilla")
    return row


@router.patch("/{template_id}", response_model=ReportBuilderTemplateRead)
async def update_report_builder_template(
    template_id: UUID,
    payload: ReportBuilderTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
) -> ReportBuilderTemplateRead:
    """US-126 — sólo el owner puede modificar (incluye publicar/despublicar)."""
    row = await _load_owned(db, cu, template_id)
    data = payload.model_dump(exclude_unset=True)
    if "visibility" in data and data["visibility"] == "project":
        # Si publica al proyecto, debe haber project_id (de payload o existente).
        new_pid = data.get("project_id") or row.project_id
        if new_pid is None:
            raise validation_error(
                "project_id es obligatorio para visibility='project'",
                {"project_id": "required"},
            )
    if "project_id" in data:
        data["project_id"] = str(data["project_id"]) if data["project_id"] else None
    for k, v in data.items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return ReportBuilderTemplateRead.model_validate(row)


@router.delete("/{template_id}", status_code=204)
async def delete_report_builder_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
):
    """US-126 — sólo el owner puede borrar su plantilla."""
    row = await _load_owned(db, cu, template_id)
    await db.delete(row)
    await db.commit()
    return None
