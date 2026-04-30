"""Stakeholders catalog CRUD — US-086."""
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import not_found
from app.db.session import get_db
from app.models.stakeholder import Stakeholder
from app.schemas.stakeholder import (
    StakeholderCreate,
    StakeholderRead,
    StakeholderUpdate,
)

router = APIRouter(prefix="/stakeholders", tags=["stakeholders"])


def _tenant(cu: CurrentUser) -> UUID:
    return cu.user.tenant_id


@router.get("", response_model=list[StakeholderRead])
async def list_stakeholders(
    organization_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Stakeholder).where(
        Stakeholder.tenant_id == tenant_id,
        Stakeholder.deleted_at.is_(None),
    )
    if organization_id is not None:
        stmt = stmt.where(Stakeholder.organization_id == str(organization_id))
    if is_active is not None:
        stmt = stmt.where(Stakeholder.is_active == is_active)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(Stakeholder.full_name).like(like)
            | func.lower(Stakeholder.email).like(like)
            | func.lower(Stakeholder.company).like(like)
        )
    rows = (
        await db.execute(
            stmt.order_by(Stakeholder.full_name).offset((page - 1) * limit).limit(limit)
        )
    ).scalars().all()
    return [StakeholderRead.model_validate(r) for r in rows]


@router.post("", response_model=StakeholderRead, status_code=201)
async def create_stakeholder(
    body: StakeholderCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    s = Stakeholder(
        tenant_id=str(tenant_id),
        organization_id=str(body.organization_id) if body.organization_id else None,
        full_name=body.full_name,
        email=str(body.email) if body.email else None,
        phone=body.phone,
        company=body.company,
        job_title=body.job_title,
        notes=body.notes,
        is_active=body.is_active,
        created_by=str(cu.id),
    )
    db.add(s)
    await db.commit()
    return StakeholderRead.model_validate(s)


@router.get("/{stakeholder_id}", response_model=StakeholderRead)
async def get_stakeholder(
    stakeholder_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    s = (
        await db.execute(
            select(Stakeholder).where(
                Stakeholder.id == str(stakeholder_id),
                Stakeholder.tenant_id == tenant_id,
                Stakeholder.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if s is None:
        raise not_found("Stakeholder")
    return StakeholderRead.model_validate(s)


@router.patch("/{stakeholder_id}", response_model=StakeholderRead)
async def update_stakeholder(
    stakeholder_id: UUID,
    body: StakeholderUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    s = (
        await db.execute(
            select(Stakeholder).where(
                Stakeholder.id == str(stakeholder_id),
                Stakeholder.tenant_id == tenant_id,
                Stakeholder.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if s is None:
        raise not_found("Stakeholder")
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        if k == "organization_id" and v is not None:
            v = str(v)
        if k == "email" and v is not None:
            v = str(v)
        setattr(s, k, v)
    await db.commit()
    return StakeholderRead.model_validate(s)


@router.delete("/{stakeholder_id}", status_code=204)
async def delete_stakeholder(
    stakeholder_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    s = (
        await db.execute(
            select(Stakeholder).where(
                Stakeholder.id == str(stakeholder_id),
                Stakeholder.tenant_id == tenant_id,
                Stakeholder.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if s is None:
        raise not_found("Stakeholder")
    s.deleted_at = datetime.now(UTC)
    s.is_active = False
    await db.commit()
