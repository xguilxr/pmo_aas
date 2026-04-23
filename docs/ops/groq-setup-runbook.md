# Runbook · Habilitar Groq como IA base de la plataforma (US-057)

> Aplica a **Sprint 2 v1.1**. Ejecutar en producción tras mergear
> la branch que trae las migraciones `20260423_0021` y `20260423_0022`.

Tiempo estimado: **15–25 min** incluyendo la sección final de limpieza.

---

## 0. Pre-requisitos

- Acceso a **Railway** con rol `Admin` del proyecto `pmo_aas`.
- Acceso a **`/superadmin/ai`** en la app desplegada.
- Un correo accesible para crear la cuenta de Groq si aún no existe.
- (Si aplica) acceso RDP/SSH a la máquina PC-PMO que corrió los intentos
  previos con Tailscale + NSSM + Cloudflare.

---

## 1. Generar `FERNET_KEY` de plataforma

La Fernet key cifra las API keys (Groq plataforma y BYO del tenant).
Si ya existe `AI_SECRETS_FERNET_KEY` en Railway válida (32 bytes
url-safe base64), **saltar al paso 2**. Si nunca se configuró o el
valor actual es el default de dev (`dev-ai-secrets-fernet-key-...`),
generar una nueva:

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

Copiar el string resultante (ej. `abcDE...=`). En Railway:

1. Proyecto → servicio `api` → **Variables** → agregar/editar
   `AI_SECRETS_FERNET_KEY` = `<valor generado>`.
2. Repetir para el servicio `worker`.
3. Redeploy ambos servicios para que la variable surta efecto.

> ⚠️ **Si pierdes esta key, las API keys cifradas en BD son irrecuperables.**
> Guarda el valor en el gestor de secretos del equipo (1Password /
> Bitwarden / similar). No la commits a git bajo ningún concepto.

---

## 2. Crear API key de Groq

1. Ir a <https://console.groq.com> y crear cuenta (o iniciar sesión).
2. Tab **API Keys** → **Create API Key** → nombre "pmo-aas-prod".
3. Copiar el valor `gsk_...` (sólo se muestra una vez).
4. (Opcional pero recomendado) crear una **segunda key** de backup
   bajo el mismo proyecto, nombre "pmo-aas-backup", guardarla en el
   gestor de secretos.

**Free tier (llama-3.1-70b-versatile, al 2026-04):**
- 30 requests/min (RPM)
- 14 400 requests/día (RPD)
- 6 000 tokens/min (TPM)
- 1 000 000 tokens/día (TPD)

Estos límites están pre-cargados en el dashboard de `/superadmin/ai`.
Si en algún punto el owner paga el tier de Groq, actualizar los
valores en `GroqUsageSummary.limit_requests_per_day` / `…tokens_per_day`
(archivo `apps/api/app/api/v1/endpoints/superadmin_ai.py`).

---

## 3. Configurar Groq en la plataforma

1. Entrar a **`/superadmin/ai`** como superadmin.
2. En la sección "IA base (Groq) — modo platform":
   - Pegar la `gsk_...` en **GROQ_API_KEY**.
   - Confirmar/ajustar **Modelo Groq** = `llama-3.1-70b-versatile`.
3. Click **Guardar defaults**.
4. Click **Probar conexión**:
   - Esperado: `OK · <latencia>ms` (típicamente 300–900 ms).
   - Si da `HTTP 401`: la key está mal copiada, regenerarla.
   - Si da `Timeout`: revisar que Railway tiene egress a
     `api.groq.com` (generalmente sí, es HTTPS público).
5. Verificar que la key queda enmascarada al recargar (ej. `••••w3xY`).

> La API key **nunca** sale del backend en claro después del primer POST.
> `FERNET_KEY` la descifra sólo en memoria para el llamado a Groq.

---

## 4. Smoke test con un tenant real

1. Elegir un tenant de prueba o el tenant del owner.
2. Log in como admin del tenant → `/admin/ai`.
3. Seleccionar radio **"IA de la plataforma (Groq)"** → **Guardar** →
   confirmar el modal de "Cambiar modo".
4. Ir a `/admin/projects/{id}/minutes` → pegar una transcripción
   breve (`"PM: hola. Ana: OK"`) → generar minuta IA.
5. Verificar:
   - El job pasa a `succeeded` en ~3–10 s.
   - La minuta creada tiene el folio y estructura esperada.
   - En `/superadmin/ai` la sección "Uso de Groq" refleja +1 request
     y tokens acumulados.
   - El panel "Tenants · Estado de IA" muestra el tenant en modo
     `Plataforma`.
6. Si todo OK, habilitar Groq para los demás tenants que deban usarlo
   (cada admin decide desde `/admin/ai`).

### Prueba del canal de alerta

Opcionalmente validar que, si Groq cae o la key está mal, el superadmin
recibe la notificación:

1. En `/superadmin/ai`, cambiar temporalmente `GROQ_API_KEY` a un valor
   inválido → guardar.
2. Como admin del tenant, mandar una minuta IA.
3. Tras ~15 s (3 reintentos con backoff 1/3/8 s), revisar
   `/notifications` del superadmin: debe aparecer un item
   `Groq (IA plataforma) falló tras 3 reintentos`.
4. Si `RESEND_API_KEY` está configurado, llegará también un email.
5. Restaurar la key válida.

---

## 5. Docs internas y comunicación

- [ ] Anunciar al equipo: "Groq ya está disponible como IA base. Los
  tenants pueden activarla en `/admin/ai`. Las minutas procesan ahí;
  reportes IA sólo disponibles en modo BYO."
- [ ] Registrar **DEC-017 — Groq como IA base de la plataforma**
  en `docs/epics/DECISIONS.md` (si aún no está).
- [ ] Actualizar `docs/epics/EP008-ai.md` mencionando el modo
  `platform` y el scope "sólo minutas".

---

## 6. Limpieza de intentos previos (IA local / tailnet)

Los intentos anteriores de host local (Ollama en PC-PMO) dejaron
residuos. Si **ningún tenant productivo depende ya de Ollama tailnet**
(confirmar en `/superadmin/ai` → columna "Proveedor"), ejecutar:

### 6.1 En la máquina PC-PMO (Windows)

```powershell
# 1. Detener y eliminar el servicio NSSM que hostea Ollama.
nssm stop  PMOOllama
nssm remove PMOOllama confirm

# 2. Detener Tailscale (si ya no se usa fuera del flujo AI).
net stop Tailscale
"C:\Program Files\Tailscale\tailscale.exe" logout

# 3. (Opcional) Desinstalar Tailscale:
#    Panel de Control → Programas → Desinstalar "Tailscale".

# 4. Bajar cualquier Cloudflare Tunnel (intento anterior a Tailscale).
cloudflared service uninstall
#    Y eliminar el config:
Remove-Item -Force "$env:USERPROFILE\.cloudflared\config.yml" -ErrorAction SilentlyContinue
```

### 6.2 En Cloudflare (navegador)

1. **Zero Trust** → **Access** → **Applications** — eliminar la app
   que protegía el túnel Ollama (si existe) + sus Service Tokens.
2. **Zero Trust** → **Networks** → **Tunnels** — borrar el tunnel
   `pmo-ollama-*`.

### 6.3 En la plataforma

- Revisar `tenants.settings.ai.ollama.auth_legacy.*` en los tenants
  migrados por el commit 0022 (data migration). Si ningún item queda
  con `auth_legacy`, opcional en un commit de housekeeping **borrar
  la columna legacy** o dejarla como retro-compat.
- Una vez confirmado que `tenants.settings.ai.ollama.auth_legacy` no
  se lee más, se puede **eliminar el módulo deprecated**
  `apps/api/app/services/ai_secrets.py` (pero Fernet sigue vivo
  porque lo usan US-057, así que sólo eliminar lo legacy, no el archivo).

### 6.4 Verificación final

- [ ] `/superadmin/ai` — panel de tenants: ningún tenant activo con
  proveedor `ollama` salvo los que explícitamente quieren seguir con
  su tailnet propio.
- [ ] Railway `api` y `worker` sin variables viejas tipo
  `OLLAMA_BASE_URL`, `OLLAMA_MODEL` apuntando al PC local. (Las env
  siguen existiendo como defaults, pero deben apuntar a algo que
  exista o estar vacías.)
- [ ] El PC-PMO puede apagarse sin consecuencias para la producción.

---

## 7. Plan de rollback

Si Groq se vuelve inestable y quieres deshabilitarlo sin revertir
migraciones:

1. `/superadmin/ai` → borrar **GROQ_API_KEY** → Guardar.
2. Todos los tenants en modo `platform` dejarán de poder generar
   minutas (error `groq_no_api_key`). Los tenants en modo `byo`
   siguen funcionando.
3. Opción A: los tenants afectados cambian a `byo` con su proveedor.
4. Opción B: el superadmin los fuerza a `disabled` modificando
   `tenants.settings.ai.mode` en la BD directamente.

---

## Apéndice — Rollback total

Si hiciste el deploy y hay que revertir del todo:

```bash
# En la branch de rollback:
alembic downgrade 20260423_0020
```

Esto desarma las migraciones 0021 y 0022 (la segunda es no-op, la primera
borra las columnas de Groq y `ai_jobs.provider`). Los valores cifrados se
pierden pero nunca estuvieron en el env.
