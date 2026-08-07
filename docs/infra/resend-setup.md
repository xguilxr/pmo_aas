---
tipo: guia
responsable: propietario
estado: vigente
revisado: 2026-05-08
revisar_cada: 180d
---

# Runbook: Resend para emails transaccionales (US-028)

> Checklist operativo para habilitar el canal email de notificaciones
> de PMO·aaS. Si este runbook no está completo, el flujo in-app
> (US-027) funciona de todos modos — solo no se mandan correos.

## Resumen

PMO·aaS usa [Resend](https://resend.com/) para los emails transaccionales
de notificaciones (solicitud aprobada, PM asignado, AID vencida, etc.).
El código en `apps/api/app/services/email.py` hace un `POST` directo al
endpoint `https://api.resend.com/emails` usando una API key.

## Vars de entorno (Railway → servicio `worker`)

| Var | Requerida | Ejemplo | Notas |
|---|---|---|---|
| `RESEND_API_KEY` | Sí | `re_xxxxxxxxxxxxxxxx` | API key de Resend. Sin esta, el canal email queda OFF (los logs muestran warning `RESEND_API_KEY no configurado`). |
| `RESEND_FROM` | Sí | `PMO·aaS <no-reply@pmo-aas.com>` | Debe usar un dominio **verificado** en Resend. El nombre humano es opcional. |
| `APP_BASE_URL` | Recomendada | `https://app.pmo-aas.com` | Se inserta en el CTA "Ver en PMO·aaS" y en el link de preferencias. |

Las 3 también pueden vivir en `api` si alguna ruta decide mandar email
síncrono, pero hoy solo el worker dispatcha la task — con ponerlas en
el servicio `worker` basta.

## Paso a paso

1. **Crear cuenta en Resend** (tier Free = 3 000 emails/mes, suficiente
   para MVP). https://resend.com/signup
2. **Agregar el dominio**: `pmo-aas.com`.
   - Resend te da 3 registros DNS (SPF, DKIM, DMARC-friendly).
   - En Cloudflare (DNS productivo — ver `docs/infra/dns-routing.md`):
     - Añadir el `TXT` de SPF (`v=spf1 include:amazonses.com ~all` o el
       que Resend provea).
     - Añadir el `CNAME` de DKIM (`resend._domainkey.pmo-aas.com →
       ...amazonses.com`). **Importante**: proxy **DNS only** (nube
       gris) — Cloudflare proxy rompe SMTP/DKIM.
     - Opcional: un `TXT` DMARC `v=DMARC1; p=quarantine; rua=mailto:…`.
   - En Resend dashboard → verificar.
3. **Crear API key**: Dashboard → API Keys → Create → alcance
   "Sending access". Copia el string `re_xxx`.
4. **Configurar Railway**: project `pmo-aas` → servicio `worker` →
   Variables → agregar `RESEND_API_KEY`, `RESEND_FROM`, `APP_BASE_URL`.
   Deploy (Railway redespliega automático).
5. **Smoke test**:
   - Login en la app con 2 cuentas distintas (solicitante + reviewer).
   - Solicitante crea una solicitud.
   - Reviewer la aprueba.
   - El solicitante debe recibir email "Solicitud aprobada: …" +
     notificación in-app con badge.
   - Si llega solo in-app, revisar logs del worker Railway:
     - `RESEND_API_KEY no configurado` → env var no llegó.
     - `Resend API 401` → key inválida.
     - `Resend API 403` → dominio no verificado o `RESEND_FROM` usa otro dominio.

## Comportamiento sin API key

Si `RESEND_API_KEY` queda vacía, `send_email_via_resend` devuelve
`None` y la task Celery termina con `{"skipped": "resend_not_configured"}`.
La notificación in-app se crea igual. Útil en desarrollo local y para
apagar el canal temporalmente sin tocar código.

## Unsubscribe / preferencias

El footer de cada email linkea a `APP_BASE_URL/account`. Ahí el usuario
tiene:

- Un **kill-switch global** "Enviar correos electrónicos" (apaga todos).
- Un **switch por tipo** (Solicitud aprobada, PM asignado, etc.) que
  cambia entre "Email + in-app" y "Solo in-app".

Las preferencias viven en `users.preferences.notifications` (JSON) y se
consultan antes de dispatchear cada email (ver
`services/notifications._user_wants_email`).

## Supresión por lectura in-app

Si el usuario ya leyó la notificación in-app dentro de las últimas 2 h
(`EMAIL_SUPPRESS_IF_READ_WITHIN`), la task skip-ea el envío para evitar
spam duplicado. Logs: `{"skipped": "recently_read_inapp"}`.

## Límites y costos

- Free: 3 000 emails/mes, 100/día.
- Pro ($20/mes): 50 000 emails/mes, 50 msg/s.
- Ver https://resend.com/pricing.

Con el volumen esperado del MVP + primeros clientes (~200 emails/día
máximo) el tier Free cubre. Upgrade a Pro cuando se habiliten reports
programados (post-MVP).

## Rollback

Para deshabilitar emails sin quitar el código:

1. Railway → `worker` → borrar `RESEND_API_KEY` (o ponerla vacía).
2. Restart del servicio.

Todas las notifs quedan solo in-app.
