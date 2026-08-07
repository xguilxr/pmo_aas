"""MCS SEG-01 · ASVS 8.3.2 — exportar y suprimir los datos de una persona.

«Verify that users have a method to remove or export their data on demand.»

Cierra además la carencia que `docs/dominio/05-DATOS-PERSONALES.md` §5 declaraba
como «la más seria de este inventario»: no había procedimiento, así que una
solicitud se habría atendido a mano y sin garantía de completitud.

## Por qué se anonimiza en vez de borrar

Decisión del owner (2026-08-07), ADR-034. El borrado físico de una persona
choca de frente con dos cosas que este producto necesita:

* **`audit_log` es de solo anexado por diseño** (AM-08, con su trinquete). Es lo
  que permite reconstruir qué pasó ante un error o una disputa, y un registro
  que se puede borrar por partes deja de servir para eso.
* **El historial de un proyecto es dato del inquilino, no de la persona.** Quién
  aprobó un cambio de alcance en marzo es información de la organización que
  paga por la herramienta; borrarla dejaría huecos en la trazabilidad de un
  tercero que no ha pedido nada.

Anonimizar resuelve las dos: **las filas se quedan, y dejan de apuntar a
nadie**. Si el dato ya no identifica a una persona, deja de ser dato personal —
que es lo que el RGPD reconoce en su considerando 26 y lo que hace compatible el
derecho de supresión con la trazabilidad.

Lo que **no** hace, y va escrito: no borra el texto libre. Una minuta que dice
«lo comenta Ana en la reunión» sigue diciéndolo. Buscarlo exigiría barrer todo
el contenido de la plataforma con coincidencia difusa y decidir a mano cada
acierto; se declara como límite en vez de fingir que no existe.

## Por qué la exportación va antes

El orden importa y no es casual: **exportar primero, suprimir después**. Quien
pide que se borren sus datos suele querer también su copia, y una vez
anonimizado ya no hay forma de recuperarla. La supresión exige haber podido
exportar, y la pantalla lo pone en ese orden.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.user import User

#: Con qué se sustituye. Un marcador legible —no una cadena vacía— para que una
#: pantalla que muestre «creado por» siga diciendo algo en vez de quedarse muda
#: o mostrar un identificador crudo.
NOMBRE_ANONIMO = "Usuario eliminado"


def _seudonimo(user_id: UUID | str) -> str:
    """Identificador estable y no reversible para el correo y el usuario.

    Estable porque dos filas del mismo usuario anonimizado tienen que seguir
    siendo del mismo, o el historial de un proyecto se vuelve incoherente. No
    reversible porque si se pudiera deshacer no sería anonimización, sería
    ofuscación — y el dato seguiría siendo personal.

    No se usa el `user_id` a secas: es una clave que aparece en otras tablas y
    permitiría volver a cruzar. El resumen corta ese hilo.
    """
    digest = hashlib.sha256(f"anon:{user_id}".encode()).hexdigest()[:12]
    return digest


async def exporta(db: AsyncSession, *, user: User) -> dict[str, Any]:
    """Todo lo que la plataforma guarda sobre esta persona, en JSON.

    Se incluye el registro de auditoría **de sus propias acciones**: es dato
    sobre ella y el control dice «their data». No se incluye lo que otros
    hicieron sobre sus entidades, que es actividad de terceros.
    """
    auditoria = (
        await db.execute(
            select(AuditLog).where(AuditLog.user_id == str(user.id)).order_by(AuditLog.occurred_at)
        )
    ).scalars().all()
    avisos = (
        await db.execute(
            select(Notification).where(Notification.user_id == str(user.id))
        )
    ).scalars().all()

    return {
        "generado": datetime.now(UTC).isoformat(),
        "aviso": (
            "Copia de los datos personales que PMO·aaS guarda sobre ti. No "
            "incluye el contenido que otras personas escribieron y que puede "
            "mencionarte por tu nombre — ver el límite declarado en "
            "docs/dominio/05-DATOS-PERSONALES.md."
        ),
        "cuenta": {
            "id": str(user.id),
            "usuario": user.username,
            "correo": user.email,
            "nombre": user.full_name,
            "rol": user.role_type,
            "activo": user.is_active,
            "alta": user.created_at.isoformat() if user.created_at else None,
            "ultimo_acceso": user.last_login.isoformat() if user.last_login else None,
            "privacidad_aceptada": (
                user.privacy_accepted_at.isoformat() if user.privacy_accepted_at else None
            ),
            "privacidad_version": user.privacy_version,
        },
        "preferencias": user.preferences or {},
        "actividad": [
            {
                "cuando": fila.occurred_at.isoformat() if fila.occurred_at else None,
                "accion": fila.action,
                "modulo": fila.module,
                "entidad": fila.entity_type,
                "entidad_id": fila.entity_id,
                "ip": fila.ip_address,
                "navegador": fila.user_agent,
            }
            for fila in auditoria
        ],
        "notificaciones": [
            {
                "cuando": n.created_at.isoformat() if n.created_at else None,
                "tipo": n.type,
                "titulo": n.title,
                "cuerpo": n.body,
            }
            for n in avisos
        ],
    }


async def anonimiza(db: AsyncSession, *, user: User) -> dict[str, int]:
    """Sustituye los identificadores personales por un marcador. **No borra filas.**

    Devuelve cuántas filas se tocaron por tabla, para que quede en la auditoría
    y para que la respuesta pueda decírselo a quien lo pidió: «se anonimizaron N
    registros» es comprobable, «hecho» no.

    La cuenta queda **inactiva**: anonimizada y activa sería una cuenta sin
    dueño con la que todavía se puede entrar.
    """
    seudo = _seudonimo(user.id)
    tocadas: dict[str, int] = {}

    # `audit_log` no se toca: es de solo anexado (AM-08) y su trinquete lo
    # impide. Lo que se corta es el vínculo, y se corta en `users`: las filas
    # apuntan a un identificador que ya no lleva a ninguna persona.
    avisos = (
        await db.execute(select(Notification).where(Notification.user_id == str(user.id)))
    ).scalars().all()
    for aviso in avisos:
        # El cuerpo de una notificación puede llevar el nombre («Hola Ana…»).
        aviso.body = None
        aviso.title = "Notificación de una cuenta eliminada"
    tocadas["notificaciones"] = len(avisos)

    user.full_name = NOMBRE_ANONIMO
    user.username = f"anon-{seudo}"
    user.email = f"anon-{seudo}@eliminado.invalid"
    user.is_active = False
    user.preferences = {}
    # La contraseña deja de valer para nada, pero se sustituye igual: dejar el
    # hash sería conservar un dato derivado de un secreto de la persona.
    user.password_hash = f"anonimizado-{seudo}"
    tocadas["cuenta"] = 1

    return tocadas
