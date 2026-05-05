"""Email delivery via Resend (US-028, EP011).

Sólo encapsula el HTTP call al API de Resend + build del template. El
dispatch (Celery task) y la lógica de "qué se manda" viven en
`services/notifications.py` y `workers/tasks/notifications.py`.

Si `RESEND_API_KEY` no está seteado, el helper registra un warning y
devuelve `None` (no-op), de modo que las notificaciones in-app siguen
funcionando aunque el canal email esté deshabilitado.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def build_email_html(
    *,
    title: str,
    body: str | None,
    link: str | None,
    tenant_name: str | None = None,
    tenant_logo_url: str | None = None,
) -> str:
    """Template HTML responsive minimal. No usamos MJML/Jinja aquí —
    el volumen esperado justifica string templating directo para no
    agregar deps."""
    logo_html = (
        f'<img src="{tenant_logo_url}" alt="{tenant_name or "PMO·aaS"}" '
        f'style="max-height:36px;margin-bottom:16px" />'
        if tenant_logo_url
        else f'<div style="font-weight:600;color:#182e4e;margin-bottom:16px">'
        f'{tenant_name or "PMO·aaS"}</div>'
    )
    cta = (
        f'<p><a href="{link}" style="display:inline-block;padding:10px 16px;'
        f'background:#182e4e;color:#fff;border-radius:6px;text-decoration:none">'
        f"Ver en PMO·aaS</a></p>"
        if link
        else ""
    )
    body_html = (
        f'<p style="color:#334155;line-height:1.5">{body}</p>' if body else ""
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<body style="font-family:-apple-system,Segoe UI,sans-serif;background:#f8fafc;margin:0;padding:24px">
<table role="presentation" align="center" width="560" style="background:#fff;border-radius:12px;padding:24px;border:1px solid #e2e8f0">
<tr><td>
{logo_html}
<h2 style="margin:0 0 8px;color:#0f172a">{title}</h2>
{body_html}
{cta}
<hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0"/>
<p style="font-size:12px;color:#64748b">
Estás recibiendo este correo porque tienes notificaciones activas en PMO·aaS.
Ajusta tus preferencias desde <a href="{settings.APP_BASE_URL}/account">tu cuenta</a>.
</p>
</td></tr>
</table>
</body></html>
"""


def build_welcome_email_html(
    *,
    full_name: str,
    email: str,
    username: str,
    password: str,
    tenant_name: str | None = None,
    tenant_logo_url: str | None = None,
) -> str:
    """US-089: template HTML con credenciales de ingreso para usuarios
    creados por un admin.

    El email contiene email, username, password (en claro) y un link a
    `${APP_BASE_URL}/login`. El recipiente debe cambiar el password en su
    primer login (`must_change_password=True` se setea server-side).
    """
    login_url = f"{settings.APP_BASE_URL}/login"
    logo_html = (
        f'<img src="{tenant_logo_url}" alt="{tenant_name or "PMO·aaS"}" '
        f'style="max-height:36px;margin-bottom:16px" />'
        if tenant_logo_url
        else f'<div style="font-weight:600;color:#182e4e;margin-bottom:16px">'
        f'{tenant_name or "PMO·aaS"}</div>'
    )
    creds_table = f"""
<table role="presentation" cellpadding="6" cellspacing="0" style="background:#f1f5f9;border-radius:8px;width:100%;font-size:14px;color:#0f172a">
  <tr><td style="font-weight:600;color:#475569;width:120px">Email</td><td>{email}</td></tr>
  <tr><td style="font-weight:600;color:#475569">Usuario</td><td>{username}</td></tr>
  <tr><td style="font-weight:600;color:#475569">Contraseña</td><td><code style="background:#fff;padding:2px 6px;border-radius:4px;border:1px solid #e2e8f0">{password}</code></td></tr>
</table>
"""
    return f"""<!DOCTYPE html>
<html lang="es">
<body style="font-family:-apple-system,Segoe UI,sans-serif;background:#f8fafc;margin:0;padding:24px">
<table role="presentation" align="center" width="560" style="background:#fff;border-radius:12px;padding:24px;border:1px solid #e2e8f0">
<tr><td>
{logo_html}
<h2 style="margin:0 0 8px;color:#0f172a">Bienvenido a {tenant_name or "PMO·aaS"}</h2>
<p style="color:#334155;line-height:1.5">
Hola {full_name}, se creó tu cuenta. Estas son tus credenciales de acceso:
</p>
{creds_table}
<p style="color:#334155;line-height:1.5;margin-top:16px">
Por seguridad, te pediremos que cambies la contraseña la primera vez que ingreses.
</p>
<p><a href="{login_url}" style="display:inline-block;padding:10px 16px;background:#182e4e;color:#fff;border-radius:6px;text-decoration:none">
Iniciar sesión
</a></p>
<hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0"/>
<p style="font-size:12px;color:#64748b">
Si no esperabas este correo, ignóralo. La cuenta sólo es accesible con la contraseña enviada.
</p>
</td></tr>
</table>
</body></html>
"""


async def send_email_via_resend(
    *,
    to: str | list[str],
    subject: str,
    html: str,
    reply_to: str | None = None,
    attachments: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    """POST a Resend. Devuelve el body JSON (incluye `id` del mensaje)
    o `None` si el canal está deshabilitado.

    `attachments`: lista de objetos Resend `{filename, content}` donde
    `content` es base64 string del archivo.
    """
    api_key = settings.RESEND_API_KEY
    if not api_key:
        log.warning("RESEND_API_KEY no configurado — email omitido: %s", subject)
        return None
    from_addr = settings.RESEND_FROM or "PMO·aaS <no-reply@pmo-aas.com>"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    recipients = [to] if isinstance(to, str) else list(to)
    payload: dict[str, Any] = {
        "from": from_addr,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    if attachments:
        payload["attachments"] = attachments
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(RESEND_API_URL, json=payload, headers=headers)
        if r.status_code >= 300:
            log.error(
                "Resend API %s: %s", r.status_code, r.text[:300]
            )
            r.raise_for_status()
        return r.json()
