"""Notification helpers (US-027 + US-028, EP011).

Pattern:
    await enqueue_notification(db, user_id=..., type="request_approved", ...)
    # inserta en `notifications`, opcionalmente dispara email.

El envío real de email vive en `app.services.email` (US-028) y se
dispatcha async vía Celery para no bloquear la request que generó el
evento.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User

# Tipos canónicos (ver EP011-notifications.md). Mantener sincronizado con
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
