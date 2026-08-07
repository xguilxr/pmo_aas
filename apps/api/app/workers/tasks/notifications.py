"""Celery task que entrega notificaciones por email (US-028).

La request que creó la notif in-app encola esta task vía
`send_notification_email.delay(notification_id)`. La task abre su propia
sesión DB, revisa si todavía procede mandar email (suppression window),
renderiza el template con branding del tenant y llama a Resend.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.models.notification import Notification
from app.models.organization import Organization
from app.models.tenant import Tenant
from app.models.user import User
from app.services.email import build_email_html, send_email_via_resend
from app.services.notifications import EMAIL_SUPPRESS_IF_READ_WITHIN
from app.workers.celery_app import celery_app
from app.workers.db import db_session, run_async

log = logging.getLogger(__name__)


@celery_app.task(name="notifications.send_email", bind=True, max_retries=3)
def send_notification_email(self, notification_id: str) -> dict:
    return run_async(_send(notification_id))


async def _send(notification_id: str) -> dict:
    async with db_session() as db:
        notif = (
            await db.execute(
                select(Notification).where(Notification.id == notification_id)
            )
        ).scalar_one_or_none()
        if notif is None:
            return {"skipped": "not_found"}

        # Dedupe: si el user ya leyó in-app dentro de la ventana, no mandes email.
        if notif.is_read and notif.read_at:
            if datetime.now(UTC) - notif.read_at < EMAIL_SUPPRESS_IF_READ_WITHIN:
                return {"skipped": "recently_read_inapp"}

        if notif.email_sent:
            return {"skipped": "already_sent"}

        user = (
            await db.execute(select(User).where(User.id == notif.user_id))
        ).scalar_one_or_none()
        if user is None or not user.email or not user.is_active:
            return {"skipped": "no_deliverable_user"}

        # Branding del tenant: el campo tenant_name / logo vive en la Org
        # principal del tenant o en el propio Tenant. Tomamos la primera Org
        # activa como label (post-MVP: columna `display_name`).
        tenant = (
            await db.execute(
                select(Tenant).where(Tenant.id == notif.tenant_id)
            )
        ).scalar_one_or_none()
        org = (
            await db.execute(
                select(Organization)
                .where(
                    Organization.tenant_id == notif.tenant_id,
                    Organization.is_active.is_(True),
                )
                .order_by(Organization.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        tenant_name = (org.name if org else None) or (tenant.name if tenant else None)
        tenant_logo = org.logo_url if org else None

        html = build_email_html(
            title=notif.title,
            body=notif.body,
            link=notif.link,
            tenant_name=tenant_name,
            tenant_logo_url=tenant_logo,
        )

        try:
            resp = await send_email_via_resend(
                to=user.email, subject=notif.title, html=html
            )
        except Exception as exc:  # retry con backoff estándar Celery
            log.exception("Resend send failed for notif=%s: %s", notification_id, exc)
            raise send_notification_email.retry(exc=exc, countdown=60) from exc

        if resp is None:
            # Canal deshabilitado; no fallamos ni reintentamos.
            return {"skipped": "resend_not_configured"}

        notif.email_sent = True
        notif.email_sent_at = datetime.now(UTC)
        notif.email_provider_id = resp.get("id")
        await db.commit()
        return {"sent": True, "provider_id": notif.email_provider_id}


@celery_app.task(name="notifications.send_security_email", bind=True, max_retries=3)
def send_security_email(self, to: str, subject: str, body: str) -> dict:
    """Aviso de seguridad por correo, **sin** notificación in-app detrás.

    MCS SEG-01 · ASVS 2.2.3 y 2.5.5. Existe porque `send_notification_email`
    no sirve para los dos casos que más importan de este control:

    1. **El destinatario no tiene fila in-app.** `notifications.tenant_id` es
       NOT NULL, así que un superadministrador —que no pertenece a ningún
       inquilino— no puede tener notificación, y hasta ahora tampoco recibía
       aviso al cambiar su contraseña.
    2. **El destinatario es la dirección ANTERIOR.** Al cambiar el correo de
       una cuenta hay que avisar al que se deja de usar; ahí no hay usuario a
       quien colgar la notificación, y es precisamente el aviso que le llega a
       la persona cuya cuenta le acaban de quitar.

    Tampoco pasa por la ventana de supresión ni por las preferencias: un aviso
    de seguridad que se puede desactivar desde los ajustes no es un control.
    """
    return run_async(_envia_aviso(to, subject, body))


async def _envia_aviso(to: str, subject: str, body: str) -> dict:
    html = build_email_html(title=subject, body=body, link=None)
    try:
        resp = await send_email_via_resend(to=to, subject=subject, html=html)
    except Exception as exc:
        log.exception("aviso de seguridad no entregado a %s: %s", to, exc)
        raise send_security_email.retry(exc=exc, countdown=60) from exc
    if resp is None:
        return {"skipped": "resend_not_configured"}
    return {"sent": True, "provider_id": resp.get("id")}
