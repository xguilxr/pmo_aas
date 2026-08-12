"""Notification helpers (US-027 + US-028, EP011).

Pattern:
    await enqueue_notification(db, user_id=..., type="request_approved", ...)
    # inserta en `notifications`, opcionalmente dispara email.

El envío real de email vive en `app.services.email` (US-028) y se
dispatcha async vía Celery para no bloquear la request que generó el
evento.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User

log = logging.getLogger(__name__)

# Tipos canónicos (ver docs/archive/epics/EP011-notifications.md). Mantener sincronizado con
# el frontend `NOTIFICATION_TYPE_LABEL`.
REQUEST_APPROVED = "request_approved"
REQUEST_REJECTED = "request_rejected"
REQUEST_NEEDS_INFO = "request_needs_info"
PM_ASSIGNED = "pm_assigned"
PM_REMOVED = "pm_removed"
PHASE_CHANGED = "phase_changed"
AID_OVERDUE = "aid_overdue"
RISK_HIGH = "risk_high"
CHANGE_PENDING = "change_pending"
MINUTE_GENERATED = "minute_generated"
REPORT_SENT = "report_sent"
# US-057: alerta al superadmin cuando Groq (modo plataforma) falla.
PLATFORM_AI_ALERT = "platform_ai_alert"
# US-063: flujo de recuperación/cambio de contraseña.
PASSWORD_RESET_REQUESTED = "password_reset_requested"
PASSWORD_CHANGED = "password_changed"
# US-085: nueva organización capturada vía solicitud, queda inactiva
# hasta que el admin del tenant la termine de configurar.
ORGANIZATION_PENDING_SETUP = "organization_pending_setup"

# Qué tipos mandan email por default cuando el user no tiene override.
# Post-MVP puede moverse a config-per-tenant.
EMAIL_BY_DEFAULT = {
    REQUEST_APPROVED,
    REQUEST_REJECTED,
    REQUEST_NEEDS_INFO,
    PM_ASSIGNED,
    AID_OVERDUE,
    PLATFORM_AI_ALERT,
    PASSWORD_RESET_REQUESTED,
    PASSWORD_CHANGED,
    ORGANIZATION_PENDING_SETUP,
}

# Ventana de deduplicación in-app antes de mandar email (US-028).
EMAIL_SUPPRESS_IF_READ_WITHIN = timedelta(hours=2)


async def enqueue_notification(
    db: AsyncSession,
    *,
    tenant_id: UUID | str,
    user_id: UUID | str,
    type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    link: str | None = None,
    meta: dict | None = None,
    send_email: bool | None = None,
) -> Notification:
    """Inserta una notificación y, si corresponde, encola el email.

    - `send_email=None` (default) respeta preferencias del user y los
      defaults del tipo.
    - `send_email=True/False` fuerza el canal.

    NO hace commit: el caller decide cuándo commit (permite agrupar
    con la transacción de la mutación principal).
    """
    notif = Notification(
        tenant_id=str(tenant_id),
        user_id=str(user_id),
        type=type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        link=link,
        meta=meta or {},
    )
    db.add(notif)
    await db.flush()

    # Decisión de email
    if send_email is None:
        send_email = await _user_wants_email(db, user_id, type)

    if send_email:
        # Dispatch async a Celery (no falla la request si el worker no
        # está up). Import local para romper el ciclo con `workers/`.
        try:
            from app.workers.tasks.notifications import send_notification_email

            send_notification_email.delay(str(notif.id))
        except Exception:
            # Si Celery no está configurado (p. ej. en tests) no
            # bloqueamos la creación de la notif in-app.
            pass

    return notif


async def _user_wants_email(
    db: AsyncSession, user_id: UUID | str, type: str
) -> bool:
    """Decide si el user recibe email para este tipo.

    Preferencias viven en `users.preferences.notifications`:
        {
          "notifications": {
            "by_type": {"request_approved": "email_and_inapp", "pm_assigned": "inapp_only"},
            "email_enabled": true  # kill-switch global
          }
        }
    """
    user = (
        await db.execute(select(User).where(User.id == str(user_id)))
    ).scalar_one_or_none()
    if user is None:
        return False
    prefs: dict[str, Any] = (user.preferences or {}).get("notifications", {})
    if prefs.get("email_enabled") is False:
        return False
    by_type = prefs.get("by_type", {})
    choice = by_type.get(type)
    if choice == "inapp_only":
        return False
    if choice == "email_and_inapp":
        return True
    # Sin override: default del tipo.
    return type in EMAIL_BY_DEFAULT


# ---------------------------------------------------------------------------
# MCS SEG-01 · ASVS 2.2.3 y 2.5.5 — aviso al cambiar los datos de acceso
# ---------------------------------------------------------------------------

#: 2.2.3 pide avisar «after updates to authentication details, such as
#: credential resets, email or address changes»; 2.5.5, «if an authentication
#: factor is changed or replaced». Son el mismo aviso visto desde dos sitios,
#: así que se implementan juntos.
#:
#: El **tipo** sigue distinguiendo qué cambió, y `PASSWORD_CHANGED` se conserva
#: para los tres eventos de contraseña: es un valor guardado en filas de
#: `notifications` que ya existen y que el frontend rotula. Renombrarlo dejaría
#: sin etiqueta las notificaciones históricas de todos los inquilinos, a cambio
#: de nada — lo que el control pide es que el aviso salga, no cómo se llame.
CREDENTIAL_CHANGED = "credential_changed"

#: Qué tipo lleva cada motivo.
_TIPO_POR_MOTIVO = {
    "password": PASSWORD_CHANGED,
    "password_reset": PASSWORD_CHANGED,
    "password_admin": PASSWORD_CHANGED,
    "email": CREDENTIAL_CHANGED,
}

#: Qué se dice según lo que cambió. El texto importa: el aviso solo sirve si
#: quien lo recibe **sabe qué hacer** cuando no fue él, y «se actualizó tu
#: perfil» no le dice nada a nadie.
_QUE_PASO = {
    "password": "Se cambió la contraseña de tu cuenta.",
    "password_reset": "Se restableció la contraseña de tu cuenta con el enlace de recuperación.",
    "password_admin": "Un administrador cambió la contraseña de tu cuenta.",
    "email": "Se cambió el correo electrónico asociado a tu cuenta.",
    "email_anterior": "El correo de tu cuenta se cambió a otra dirección.",
}

_QUE_HACER = (
    "Si fuiste tú, no hay nada que hacer. Si no, tu cuenta está comprometida: "
    "cambia la contraseña ahora mismo y avisa a quien administre tu organización."
)


async def avisa_cambio_de_credencial(
    db: AsyncSession,
    *,
    usuario: User,
    motivo: str,
    correo_anterior: str | None = None,
) -> None:
    """Avisa a quien es dueño de la cuenta de que sus datos de acceso cambiaron.

    Se llama en **los seis** sitios que tocan una credencial. Fue lo que enseñó
    medir: el aviso existía en uno solo —el cambio de contraseña por el propio
    usuario— y faltaba en el restablecimiento, en los dos cambios de correo y
    en los dos cambios de contraseña hechos por un administrador. Es decir,
    faltaba justo donde el cambio **no** lo hace el dueño de la cuenta, que es
    el único caso en que el aviso sirve para algo.

    `correo_anterior` manda el aviso también a la dirección que se abandona.
    Sin eso, quien se apodera de una cuenta y le cambia el correo consigue que
    el dueño no se entere nunca: todos los avisos posteriores van al atacante.

    Nunca lanza. Un aviso que no se puede entregar no puede tumbar el cambio
    que venía a anunciar —el usuario se quedaría sin saber si su contraseña
    cambió o no—.
    """
    texto = f"{_QUE_PASO.get(motivo, 'Cambiaron los datos de acceso de tu cuenta.')} {_QUE_HACER}"
    titulo = "Cambio en los datos de acceso de tu cuenta"

    try:
        if usuario.tenant_id is not None:
            await enqueue_notification(
                db,
                tenant_id=usuario.tenant_id,
                user_id=usuario.id,
                type=_TIPO_POR_MOTIVO.get(motivo, CREDENTIAL_CHANGED),
                title=titulo,
                body=texto,
                entity_type="user",
                entity_id=str(usuario.id),
                link="/account",
                # Forzado: un aviso de seguridad que se apaga desde los ajustes
                # de notificaciones no es un control.
                send_email=True,
            )
        else:
            # Superadministrador: no pertenece a ningún inquilino y
            # `notifications.tenant_id` es NOT NULL, así que no puede tener
            # notificación in-app. Hasta ahora eso significaba que la cuenta
            # con más permisos de la plataforma era la única sin aviso.
            _envia_aviso_directo(usuario.email, titulo, texto)

        if correo_anterior and correo_anterior.lower() != (usuario.email or "").lower():
            _envia_aviso_directo(correo_anterior, titulo, f"{_QUE_PASO['email_anterior']} {_QUE_HACER}")
    except Exception:
        log.exception("no se pudo avisar del cambio de credencial a %s", usuario.id)


def _envia_aviso_directo(destino: str, titulo: str, cuerpo: str) -> None:
    """Correo sin notificación in-app detrás. No lanza si Celery no está."""
    try:
        from app.workers.tasks.notifications import send_security_email

        send_security_email.delay(destino, titulo, cuerpo)
    except Exception:
        log.exception("no se pudo encolar el aviso de seguridad a %s", destino)
