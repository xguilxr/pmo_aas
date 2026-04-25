# Runbook — Scheduled Reports troubleshooting (BUG-036)

> Cuándo usar: el owner programa un reporte automático en
> `/pmo/projects/[id]/reports` y el correo nunca llega al destinatario.

## Causa raíz típica

El servicio Railway `worker` corría sólo `celery worker`, sin
`celery beat`. Sin beat, el scheduler periódico no dispara la tarea
`scheduled_reports.send_due_reports` y las filas en `scheduled_reports`
se quedan con `next_run_at` en el pasado pero sin envío.

## Fix aplicado en BUG-036

1. **`apps/api/worker.railway.toml`** — `startCommand` ahora incluye
   `--beat` embebido en la misma instance:
   ```
   celery -A app.workers.celery_app worker --beat --loglevel=info --concurrency=2
   ```
   El worker actúa como worker + beat scheduler. Suficiente para 1
   replica (Railway free tier). Para >1 replica, mover beat a un
   servicio Railway dedicado y quitar `--beat` del worker.

2. **Endpoint `POST /api/v1/scheduled-reports/{id}/run-now`** —
   permite disparar el envío inmediato sin esperar la cadencia. Útil
   para validar end-to-end (PDF + email) desde la UI.

3. **UI**: botón "Enviar ahora" agregado a cada row en
   `/pmo/projects/[id]/reports`.

## Checklist de diagnóstico

Cuando el owner reporte "no me llegó el correo", correr en orden:

### 1. ¿El worker está corriendo?

```
railway logs -s worker --tail 100 | grep -E "celery@|beat:"
```

Buscar líneas como:
- `celery@<host> ready.` → worker arrancó.
- `beat: Starting...` → beat arrancó.
- `Scheduler: Sending due task ...` → beat está disparando tasks.

Si no aparece "beat:", el `--beat` no está activo. Verificar que el
deploy del worker aplicó el cambio del `worker.railway.toml`.

### 2. ¿Hay filas pending en `scheduled_reports`?

```sql
SELECT id, project_id, report_type, cadence, enabled,
       last_run_at, next_run_at, last_error
FROM scheduled_reports
WHERE enabled = true
ORDER BY next_run_at NULLS LAST;
```

- `enabled=false` → owner debe activar.
- `next_run_at IS NULL` → bug en `compute_next_run`. Reportar.
- `next_run_at < now()` y `last_run_at IS NULL` después de >5 min →
  beat no está disparando.

### 3. ¿Resend está configurado?

```
echo $RESEND_API_KEY | wc -c        # debe ser 39+ chars (re_xxxxx)
echo $RESEND_FROM                    # ej. "PMO <noreply@pmo-aas.com>"
```

En Railway dashboard → Variables. Si falta `RESEND_API_KEY`,
configurar (ver `docs/runbooks/email/resend-setup.md`).

### 4. ¿El dominio FROM está verificado en Resend?

Resend rechaza envíos a destinatarios externos (gmail, etc.) si el
dominio del FROM no está verificado. Login en
[resend.com/domains](https://resend.com/domains) y confirmar que
`pmo-aas.com` aparece como `verified` (DNS records aplicados).

Si NO está verificado:
- Para test rápido: cambiar `RESEND_FROM` a
  `onboarding@resend.dev` (sandbox de Resend, sólo va al email
  registrado en la cuenta Resend).
- Para producción: verificar DNS según el runbook de Resend setup.

### 5. ¿Hay errores en `last_error` de `scheduled_reports`?

```sql
SELECT id, last_error, last_run_at
FROM scheduled_reports
WHERE last_error IS NOT NULL;
```

Errores comunes:
- `RESEND_API_KEY missing` → ver paso 3.
- `Domain not verified` → ver paso 4.
- `RecipientInvalid` → email malformado en `recipients[]`.
- `PDF generation failed: weasyprint ...` → bug en el renderer (abrir
  issue separado).

### 6. Trigger manual desde la UI

Owner puede usar el botón "Enviar ahora" en cada row (BUG-036).
Internamente llama `POST /api/v1/scheduled-reports/{id}/run-now`
que hace `send_scheduled_report.delay(id)` directo. Si el envío
funciona desde aquí pero NO automáticamente, el problema es el
beat scheduler (paso 1).

### 7. Verificar inbox + spam

- Buscar en inbox: `from:pmo-aas.com OR from:onboarding@resend.dev`.
- Buscar en spam.
- Verificar la regla DMARC del dominio del destinatario (gmail puede
  rechazar si SPF/DKIM no están bien).

## Si todo lo anterior pasa y aún no llega

1. Agregar logging temporal en
   `apps/api/app/workers/tasks/scheduled_reports.py:send_scheduled_report`:
   ```python
   logger.info("send_scheduled_report id=%s recipients=%s", sched_id, recipients)
   ```
2. Re-deploy worker + dashboard logs.
3. Revisar respuesta de Resend (status code + body) para entender
   por qué el envío fue rechazado.

## Costos esperados

Resend free tier: **3000 emails/mes + 100/día**. Sobrado para PMO
con cadencia diaria + 5-10 destinatarios por proyecto. Si excede,
upgrade a Resend Pro ($20/mes para 50k/mes).

## Referencias

- US-056 (#78) — implementación original.
- BUG-036 (#166) — diagnóstico + fix de beat embedded + run-now.
- `apps/api/app/workers/celery_app.py` — beat_schedule config.
- `apps/api/app/workers/tasks/scheduled_reports.py` — task body.
- `apps/api/app/services/email.py` — `send_email_via_resend`.
- `docs/runbooks/email/resend-setup.md` — Resend account setup.
