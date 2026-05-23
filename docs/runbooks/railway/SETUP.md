# Railway — Configuración de Servicios y Variables de Entorno

**ID:** `DOC-RAILWAY-SETUP`  
**Scope:** Proyecto `pmo-aas`, 3 servicios (api, worker, web) + 2 plugins (Postgres, Redis)

Este runbook detalla cómo crear y configurar los 6 componentes del proyecto en
Railway, incluyendo todas las variables de entorno necesarias para v1.0.

---

## 1. Crear proyecto y servicios en Railway

1. Ve a https://railway.app → **+ New Project**.
2. Nombre: `pmo-aas`.
3. Crea los 3 servicios desde el repo:
   - **web**: root `apps/web`, detecta Next.js automático.
   - **api**: root `apps/api`, detecta Python/FastAPI.
   - **worker**: root `apps/api`, start command distinto (Celery).
4. Agregar plugins **Postgres 16** y **Redis 7**.

**Resultado esperado:**
```
pmo-aas/
├── web (Next.js 15)
├── api (FastAPI)
├── worker (Celery)
├── postgres (Railway Plugin v16)
└── redis (Railway Plugin v7)
```

---

## 2. Plugins: Postgres + Redis

### Postgres

- Railway crea automáticamente la base `railway` cuando agregás el plugin.
- **Connection string**: Railway auto-inyecta `DATABASE_URL` a todos los servicios.
  ```
  DATABASE_URL=postgresql://user:pass@host:5432/railway
  ```
- **Backup**: Railway hace snapshots diarios + sync semanal a Backblaze (configurar en settings).

### Redis

- **Connection string**: `REDIS_URL=redis://default:pass@host:6379`.
- Auto-inyectado a servicios que lo necesiten (api, worker).

**No necesitas intervención manual** — Railway auto-configura estos URLs.

---

## 3. Variables de entorno por servicio

### 3.1 Variables compartidas (Reference Variables)

Crear en Railway como **Shared Variables** — se copian a todos los servicios automático.

| Variable | Fuente | Valor ejemplo | Notas |
|---|---|---|---|
| `DATABASE_URL` | Plugin Postgres | `postgres://…` | Auto-inyectado, no tocar |
| `REDIS_URL` | Plugin Redis | `redis://…` | Auto-inyectado, no tocar |
| `NODE_ENV` | Tú | `production` | Para Next.js |
| `PYTHON_ENV` | Tú | `production` | Para FastAPI/Celery |

### 3.2 Servicio `api` (FastAPI)

| Variable | Requiere | Valor ejemplo | Descripción |
|---|---|---|---|
| `JWT_SECRET` | **Sí** | `<random 32+ chars>` | Firma de JWT. Rotar c/90 días. |
| `JWT_REFRESH_SECRET` | **Sí** | `<random 32+ chars>` | Firma de refresh token. |
| `ACCESS_TOKEN_TTL_SEC` | No | `3600` | 1 hora (default) |
| `REFRESH_TOKEN_TTL_SEC` | No | `2592000` | 30 días (default) |
| `BCRYPT_ROUNDS` | No | `12` | Difficulty de hash. ⚠️ cambiar rompe logins viejos. |
| `ALLOWED_ORIGINS` | **Sí** | `https://app.pmo-aas.com,https://www.pmo-aas.com` | CORS whitelist. |
| `AI_MODE` | **Sí** | `platform` | `disabled` \| `platform` \| `byo` (BUG-053). |
| `GROQ_API_KEY` | **Sí** | `gsk_…` | Key Groq de plataforma (modo `platform`). |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Modelo default Groq. |
| `AI_SECRETS_FERNET_KEY` | **Sí** | `<fernet 32B>` | Cifra BYO api_keys + Groq platform key. |
| `GEMINI_API_KEY` | No | `AIza…` | Default env-only (BYO no usa este). |
| `ANTHROPIC_API_KEY` | No | `sk-ant-…` | Default env-only (BYO no usa este). |
| `STORAGE_BACKEND` | **Sí** | `s3` (prod) / `local` (dev) | Backend de storage (ver §4). |
| `S3_*` | **Sí prod** | ver §4 | 5 variables R2/B2 (ver runbook `infra/uploads-storage.md`). |
| `LOG_LEVEL` | No | `INFO` | debug, info, warning, error. |

**Cómo generar `JWT_SECRET` y `JWT_REFRESH_SECRET`:**

```bash
# En tu shell local
python -c "import secrets; print(secrets.token_hex(32))"
# Copiar el output y pegar en Railway
```

### 3.3 Servicio `worker` (Celery)

Hereda **todas** las de `api` (DATABASE_URL, REDIS_URL, AI_SECRETS_FERNET_KEY,
GROQ_API_KEY, etc.) más estas específicas:

| Variable | Requiere | Valor ejemplo | Descripción |
|---|---|---|---|
| `RESEND_API_KEY` | **Sí** | `re_xxxxxxxx` | Para enviar emails. |
| `RESEND_FROM` | **Sí** | `PMO·aaS <no-reply@pmo-aas.com>` | Sender email (dominio verificado en Resend). |
| `APP_BASE_URL` | **Sí** | `https://app.pmo-aas.com` | Base URL para links en emails. |

> **Histórico:** hasta ENH-023 (2026-04-23) el worker requería
> `TS_AUTHKEY` + `TS_HOSTNAME` para un sidecar Tailscale que hablaba
> con Ollama (US-048). DEC-017 retiró ese flujo y ENH-023 borró el
> `start-worker.sh`. Si esas env vars existen en Railway, pueden
> eliminarse.

### 3.4 Servicio `web` (Next.js)

Hereda `NODE_ENV` + estas específicas:

| Variable | Requiere | Valor ejemplo | Descripción |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Sí** | `https://api.pmo-aas.com` | URL del backend (public, accesible desde browser). |

> **No usamos NextAuth.** El frontend habla directo con `/api/v1/auth/*` del backend. Si ves `NEXTAUTH_URL` / `NEXTAUTH_SECRET` en Railway, son legacy de versiones viejas del doc y pueden eliminarse.
>
> **GlitchTip / Sentry**: `sentry-sdk` no está instalado en `apps/api/requirements.txt`. La variable `NEXT_PUBLIC_GLITCHTIP_DSN` (o equivalente) hoy no se usa. Si se reintegra observabilidad APM, agregar aquí.

---

## 4. Volúmenes y storage

El servicio `api` y `worker` necesitan acceso al mismo storage para
uploads (api sube docs, worker genera PDFs de reportes).

### 4.1 Storage S3-compatible (Cloudflare R2)

> **Nota importante:** Railway Volumes **NO se pueden compartir
> entre servicios** — cada volumen se monta en un único contenedor.
> Para el caso PMO·aaS (api + worker compartiendo archivos)
> usamos **Cloudflare R2** (S3-compatible, 0 egress fees, 10 GB
> free).
>
> **Runbook completo:** [`docs/runbooks/infra/uploads-storage.md`](../infra/uploads-storage.md).

Env vars requeridas en Railway shared variables:

| Variable | Valor | Descripción |
|---|---|---|
| `STORAGE_BACKEND` | `s3` | Enum del backend. `local` en dev, `s3` en prod. |
| `S3_BUCKET` | `pmo-aas-uploads` | Nombre del bucket R2 (o B2). |
| `S3_ENDPOINT_URL` | `https://<accountid>.r2.cloudflarestorage.com` | R2 endpoint (o B2 equivalente). |
| `S3_ACCESS_KEY_ID` | `<key-id>` | API token R2. |
| `S3_SECRET_ACCESS_KEY` | `<secret>` | API token R2. |
| `S3_REGION` | `auto` | `auto` para R2. B2/S3 cambia. |

Para dev local, usa `STORAGE_BACKEND=local` + `STORAGE_PATH=/tmp/pmo_uploads`
(filesystem del container de dev).

### 4.2 Setup step-by-step

Ver runbook completo: `docs/runbooks/infra/uploads-storage.md`
§2-§5 para los pasos detallados con screenshots:

1. Crear bucket en Cloudflare R2.
2. Generar API token con permiso Object Read & Write scoped al bucket.
3. Pegar env vars en Railway → Deploy.
4. Smoke test desde Railway shell con `boto3`.

### 4.3 Ejemplo dev local

```bash
# .env en apps/api para dev local:
STORAGE_BACKEND=local
STORAGE_PATH=/tmp/pmo_uploads
# Los archivos se guardan en disco local (no R2). Se borran al
# reiniciar el container pero es suficiente para dev.
```

---

## 5. Configuración por servicio (railway.toml)

Cada servicio tiene su archivo de configuración. Ya existen en el repo:
- `apps/api/railway.toml` → servicio `api`
- `apps/api/worker.railway.toml` → servicio `worker`
- `apps/web/railway.toml` → servicio `web`

Railway lee estos automáticos al detectar la app. **No necesitas editarlos manualmente**
para v1.0, pero revisa que `startCommand` y `healthcheckPath` sean correctos:

```toml
# apps/api/railway.toml
[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"
healthcheckPath = "/health"

# apps/api/worker.railway.toml
[deploy]
startCommand = "celery -A app.workers.celery_app worker --loglevel=info --concurrency=2"
healthcheckPath = ""  # worker no expone HTTP
numReplicas = 1

# apps/web/railway.toml
[deploy]
startCommand = "pnpm --filter web start -p $PORT"
healthcheckPath = "/api/health"
```

---

## 6. Dominios custom en Railway

Once DNS está listo (ver [`docs/runbooks/infra/dns-routing.md`](../infra/dns-routing.md)):

1. Railway UI → Proyecto → Servicio `web` → **Networking** → **Custom Domain** → `app.pmo-aas.com`.
2. Idem para servicio `api` → `api.pmo-aas.com`.

Railway auto-provisiona cert Let's Encrypt en ≤10 min.

---

## 7. Auto-deploy

Railway UI → Proyecto → **Settings** → **Deploy**:

- **Trigger**: `main` branch (o la que uses).
- **Auto-deploy**: ON.
- **Watch paths**: (ver `apps/*/railway.toml` en el repo para paths específicos).

**Resultado**: cada `git push` a `main` triggerera redeploy automático de los
servicios afectados. Para bloquear un servicio temporalmente, cambiar su
`production_branch` a `disabled` en la UI.

---

## 8. Logs y debugging

### Ver logs en tiempo real

```bash
railway logs --service api --tail
railway logs --service worker --tail
railway logs --service web --tail
```

### Conectarse a Postgres

```bash
railway run --service api psql $DATABASE_URL
```

### Ejecutar script one-off

```bash
railway run --service api python scripts/seed_superadmin.py
```

---

## 9. Healthchecks

Railway hace ping a los healthcheck endpoints c/60s. Si fallan 3× seguidas,
marca el servicio como degradado.

- **api**: `GET /health` → 200 OK con `{"status": "ok", "version": "...", "time": "..."}`
- **worker**: Sin healthcheck HTTP (servicio background, no expone puerto).
- **web**: `GET /api/health` → proxea a backend + retorna salud combinada.

Si uno falla, Railway auto-redeploy (si está habilitado) o alertas manuales
(revisar settings).

---

## 10. Checklist de configuración

- [ ] Proyecto `pmo-aas` creado con 3 servicios (api, worker, web).
- [ ] Plugins Postgres 16 + Redis 7 agregados.
- [ ] `DATABASE_URL` + `REDIS_URL` auto-inyectados (verificar en servicio settings).
- [ ] `JWT_SECRET` + `JWT_REFRESH_SECRET` generados y guardados en Railway `api`.
- [ ] `ALLOWED_ORIGINS` configurado a `https://app.pmo-aas.com,https://www.pmo-aas.com`.
- [ ] `AI_SECRETS_FERNET_KEY` configurado (cifra la Groq key + BYO).
- [ ] `GROQ_API_KEY` cargada vía `/superadmin/ai` (no se setea en env directamente).
- [ ] `RESEND_API_KEY` + `RESEND_FROM` + `APP_BASE_URL` en `worker`.
- [ ] `NEXTAUTH_URL` + `NEXTAUTH_SECRET` + `NEXT_PUBLIC_API_URL` en `web`.
- [ ] Bucket Cloudflare R2 `pmo-aas-uploads` creado + API token + env vars (ver `infra/uploads-storage.md`).
- [ ] Auto-deploy ON en rama `main`.
- [ ] Health checks respondiendo: `api /health`, `web /api/health`.
- [ ] Custom Domains `app.pmo-aas.com` y `api.pmo-aas.com` agregados (tras DNS listo).

---

## 11. Troubleshooting

| Síntoma | Causa | Solución |
|---|---|---|
| `JWT_SECRET not found` al boot de api | Variable no configurada | Generar y agregar a Railway `api`. |
| Minutas IA fallan con `groq_no_api_key` | `GROQ_API_KEY` vacía en `platform_ai_settings` | Pegar en `/superadmin/ai` (no se setea en env directa). |
| Email no se envía | `RESEND_API_KEY` vacía o dominio no verificado | Ver [`docs/runbooks/email/resend-setup.md`](../email/resend-setup.md). |
| Frontend no alcanza backend (CORS error) | `ALLOWED_ORIGINS` no incluye dominio | Agregar a Railway `api` + redeploy. |
| Healthcheck falla (servicio marked unhealthy) | Database / Redis sin conexión | Verificar `DATABASE_URL` + `REDIS_URL` | plugins conectados. |
| Logs mostrando `ModuleNotFoundError` | `requirements.txt` desactualizado | Revisar build step en `railway.toml`. |

---

## 12. Referencias

- Architecture deployment: [`docs/runbooks/railway/DEPLOYMENT.md`](./DEPLOYMENT.md)
- DNS & custom domains: [`docs/runbooks/infra/dns-routing.md`](../infra/dns-routing.md)
- Tailscale sidecar (archivado post-ENH-023): [`docs/archive/runbooks-ai-legacy/tailscale-sidecar-setup.md`](../../archive/runbooks-ai-legacy/tailscale-sidecar-setup.md)
- Email (Resend): [`docs/runbooks/email/resend-setup.md`](../email/resend-setup.md)
- IA setup: [`docs/runbooks/ai/`](../ai/) — `groq-setup.md` + `byo-setup.md`
- Epic IA actual: [`docs/epics/EP008-ai.md`](../../epics/EP008-ai.md)
- Epic tunnel Ollama (archivada, superseded por DEC-017): [`docs/archive/cancelled-epics/EP016-local-ai-tunnel.md`](../../archive/cancelled-epics/EP016-local-ai-tunnel.md)
