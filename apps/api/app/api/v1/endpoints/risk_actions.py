"""Risk actions (US-107) — acciones de mitigación de un Riesgo, multi-Actor.

Endpoints:
- GET    /risks/{risk_id}/actions          — lista acciones del riesgo.
- POST   /risks/{risk_id}/actions          — crea acción + asigna actores.
- PATCH  /risk-actions/{action_id}         — edita campos + lista de actores.
- DELETE /risk-actions/{action_id}         — soft delete (set deleted_at).
"""
from datetime import UTC, date
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, mensaje, not_found
from app.db.session import get_db
from app.models.area import Actor
from app.models.modules import Risk
from app.models.risk_action import (
    RISK_ACTION_STATUS,
    RiskAction,
    RiskActionAssignee,
)
from app.services.audit import write_audit

router = APIRouter(tags=["risk_actions"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


async def _get_risk(db: AsyncSession, risk_id: UUID, tenant_id: UUID) -> Risk:
    r = (
        await db.execute(
            select(Risk).where(
                Risk.id == str(risk_id),
                Risk.tenant_id == str(tenant_id),
                Risk.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if r is None:
        raise not_found("Riesgo")
    return r


async def _get_action(
    db: AsyncSession, action_id: UUID, tenant_id: UUID
) -> RiskAction:
    a = (
        await db.execute(
            select(RiskAction).where(
                RiskAction.id == str(action_id),
                RiskAction.tenant_id == str(tenant_id),
                RiskAction.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise not_found("Acción")
    return a


async def _validate_actors(
    db: AsyncSession, actor_ids: list[UUID], tenant_id: UUID
) -> list[str]:
    """Devuelve la lista de actor_ids válidos del tenant. Filtra silently
    los que no existan/no sean del tenant — el caller decide si es error
    o si solo persiste los válidos."""
    if not actor_ids:
        return []
    rows = (
        await db.execute(
            select(Actor.id).where(
                Actor.id.in_([str(a) for a in actor_ids]),
                Actor.tenant_id == str(tenant_id),
                Actor.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    return [str(r) for r in rows]


async def _assignees_for(
    db: AsyncSession, action_id: str
) -> list[str]:
    rows = (
        await db.execute(
            select(RiskActionAssignee.actor_id).where(
                RiskActionAssignee.risk_action_id == action_id
            )
        )
    ).scalars().all()
    return [str(r) for r in rows]


class RiskActionCreate(BaseModel):
    short_desc: str = Field(min_length=1, max_length=500)
    due_date: date | None = None
    status: str = Field(default="open")
    assignee_actor_ids: list[UUID] = Field(default_factory=list)


class RiskActionUpdate(BaseModel):
    short_desc: str | None = Field(default=None, min_length=1, max_length=500)
    due_date: date | None = None
    status: str | None = None
    # None = no tocar; lista (incluso vacía) = reemplazar.
    assignee_actor_ids: list[UUID] | None = None


class RiskActionRead(BaseModel):
    id: UUID
    risk_id: UUID
    short_desc: str
    due_date: date | None
    status: str
    assignee_actor_ids: list[UUID]
    created_by: UUID | None
    created_at: str
    updated_at: str


def _read(action: RiskAction, assignees: list[str]) -> RiskActionRead:
    return RiskActionRead(
        id=action.id,
        risk_id=action.risk_id,
        short_desc=action.short_desc,
        due_date=action.due_date,
        status=action.status,
        assignee_actor_ids=[UUID(a) for a in assignees],
        created_by=action.created_by,
        created_at=action.created_at.isoformat(),
        updated_at=action.updated_at.isoformat(),
    )


def _validate_status(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in RISK_ACTION_STATUS:
        from app.core.errors import business_rule

        raise business_rule(
            mensaje(
                que=f"Status inválido. Usa uno de: {', '.join(RISK_ACTION_STATUS)}.",
                porque="El seguimiento de una acción solo admite los estados declarados.",
                accion="Elige uno de los estados de la lista.",
            ),
            code="INVALID_STATUS",
        )
    return value


@router.get("/risks/{risk_id}/actions", response_model=list[RiskActionRead])
async def list_risk_actions(
    risk_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_risk(db, risk_id, tenant_id)
    actions = (
        await db.execute(
            select(RiskAction)
            .where(
                RiskAction.risk_id == str(risk_id),
                RiskAction.deleted_at.is_(None),
            )
            .order_by(RiskAction.created_at.asc())
        )
    ).scalars().all()
    out: list[RiskActionRead] = []
    for a in actions:
        out.append(_read(a, await _assignees_for(db, str(a.id))))
    return out


@router.post(
    "/risks/{risk_id}/actions",
    response_model=RiskActionRead,
    status_code=201,
)
async def create_risk_action(
    risk_id: UUID,
    body: RiskActionCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    risk = await _get_risk(db, risk_id, tenant_id)
    _validate_status(body.status)
    valid_actors = await _validate_actors(db, body.assignee_actor_ids, tenant_id)
    action = RiskAction(
        tenant_id=str(tenant_id),
        risk_id=str(risk.id),
        short_desc=body.short_desc.strip(),
        due_date=body.due_date,
        status=body.status,
        created_by=cu.id,
    )
    db.add(action)
    await db.flush()
    for actor_id in valid_actors:
        db.add(
            RiskActionAssignee(
                risk_action_id=str(action.id), actor_id=actor_id
            )
        )
    await write_audit(
        db,
        action="risk_action.create",
        module="risks",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="risk_action",
        entity_id=str(action.id),
        details={"risk_id": str(risk.id), "assignees": valid_actors},
    )
    await db.commit()
    await db.refresh(action)
    return _read(action, valid_actors)


@router.patch(
    "/risk-actions/{action_id}", response_model=RiskActionRead
)
async def update_risk_action(
    action_id: UUID,
    body: RiskActionUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    action = await _get_action(db, action_id, tenant_id)
    data = body.model_dump(exclude_unset=True)

    if "status" in data:
        _validate_status(data["status"])
        action.status = data["status"]
    if "short_desc" in data and data["short_desc"] is not None:
        action.short_desc = data["short_desc"].strip()
    if "due_date" in data:
        action.due_date = data["due_date"]

    if "assignee_actor_ids" in data:
        valid_actors = await _validate_actors(
            db, body.assignee_actor_ids or [], tenant_id
        )
        await db.execute(
            delete(RiskActionAssignee).where(
                RiskActionAssignee.risk_action_id == str(action.id)
            )
        )
        for actor_id in valid_actors:
            db.add(
                RiskActionAssignee(
                    risk_action_id=str(action.id), actor_id=actor_id
                )
            )
        assignees = valid_actors
    else:
        assignees = await _assignees_for(db, str(action.id))

    await write_audit(
        db,
        action="risk_action.update",
        module="risks",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="risk_action",
        entity_id=str(action.id),
        details={"changed": list(data.keys())},
    )
    await db.commit()
    await db.refresh(action)
    return _read(action, assignees)


@router.delete("/risk-actions/{action_id}", status_code=204)
async def delete_risk_action(
    action_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime

    tenant_id = _tenant(cu)
    action = await _get_action(db, action_id, tenant_id)
    action.deleted_at = datetime.now(UTC)
    await write_audit(
        db,
        action="risk_action.delete",
        module="risks",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="risk_action",
        entity_id=str(action.id),
    )
    await db.commit()
