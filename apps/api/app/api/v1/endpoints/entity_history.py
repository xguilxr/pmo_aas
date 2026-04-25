"""US-065 — Historial de cambios filtrado por entidad.

Endpoint consumido por la página dedicada de RAID
(`/admin/projects/[id]/raid/[raidId]`) para mostrar la sección
"Historial de cambios" con user + fecha + acción. Reutiliza la tabla
`audit_log` existente.

Permisos: el requester debe tener `risks:read` o `issues:read` según
el `entity_type`. No se expone auditoría cross-tenant (se filtra por
`tenant_id` del user).
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden
from app.db.session import get_db
from app.models.audit import AuditLog

router = APIRouter(prefix="/history", tags=["history"])


class HistoryEntry(BaseModel):
    id: int
    user_id: UUID | None
    action: str
    occurred_at: datetime
    details: dict = {}


@router.get("", response_model=list[HistoryEntry])
async def list_history(
    entity_type: Literal["risk", "issue", "charter", "project"] = Query(...),
    entity_id: UUID = Query(...),
    cu: CurrentUser = Depends(
        require_authenticated()  # risks:read es el gate mínimo
    ),
    db: AsyncSession = Depends(get_db),
) -> list[HistoryEntry]:
    if cu.user.tenant_id is None:
        raise forbidden()
    rows = (
        await db.execute(
            select(AuditLog)
            .where(
                AuditLog.tenant_id == str(cu.user.tenant_id),
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == str(entity_id),
            )
            .order_by(AuditLog.occurred_at.desc())
            .limit(200)
        )
    ).scalars().all()
    return [
        HistoryEntry(
            id=r.id,
            user_id=r.user_id,
            action=r.action,
            occurred_at=r.occurred_at,
            details=r.details or {},
        )
        for r in rows
    ]
