from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

#: MCS IA-02 — los dos únicos valores de `audit_log.actor_type`.
#:
#: Constantes y no literales sueltos: con la cadena escrita a mano en cada
#: sitio, un `"IA"` o un `"ai"` se cuela sin que nada chille y parte el filtro
#: de quien después pregunte «qué hizo el modelo».
ACTOR_HUMANO = "humano"
ACTOR_IA = "ia"


async def write_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_type: str = ACTOR_HUMANO,
    module: str | None = None,
    user_id: UUID | None = None,
    tenant_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            actor_type=actor_type,
            module=module,
            user_id=str(user_id) if user_id else None,
            tenant_id=str(tenant_id) if tenant_id else None,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
    await db.flush()
