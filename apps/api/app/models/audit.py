from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, Integer, String, event, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegistroInmutableError(RuntimeError):
    """Alguien intentó modificar o borrar una fila de `audit_log`."""


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_tenant_time", "tenant_id", "occurred_at"),
        Index("idx_audit_user_time", "user_id", "occurred_at"),
        Index("idx_audit_action_time", "action", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID | None] = mapped_column(String(36))
    user_id: Mapped[UUID | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    module: Mapped[str | None] = mapped_column(String(50))
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# AM-08 / MCS SEG-07 — el registro es de solo anexado
# ---------------------------------------------------------------------------
#
# El control de verdad son los disparadores de PostgreSQL que instala la
# migración 0097: actúan pase lo que pase, incluido el SQL crudo, y no dependen
# de que la aplicación se comporte.
#
# Esto de aquí es la otra mitad, y no es redundante por dos motivos:
#
# - **Falla donde se causa el error.** El disparador devuelve un error de base
#   a mitad de una transacción; esto lanza en la línea que hizo el `delete()`,
#   con el objeto delante.
# - **Cubre SQLite**, donde corre toda la suite y buena parte del desarrollo
#   local. Sin esto, AM-08 solo sería comprobable con Postgres levantado, y un
#   control que solo se puede verificar en producción no se verifica.
#
# Lo que NO cubre: las sentencias masivas (`session.execute(delete(AuditLog))`),
# que no pasan por los eventos del mapeador. Para eso está el disparador.


def _prohibir(operacion: str):
    def _guardian(_mapper, _connection, target):
        raise RegistroInmutableError(
            f"`audit_log` es de solo anexado (AM-08): {operacion} denegado sobre "
            f"la fila {getattr(target, 'id', '?')}. Si hace falta corregir un "
            f"registro, se anexa uno nuevo que lo explique."
        )

    return _guardian


event.listen(AuditLog, "before_update", _prohibir("UPDATE"))
event.listen(AuditLog, "before_delete", _prohibir("DELETE"))
