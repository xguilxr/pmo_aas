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
| `AI_MODE` | **Sí** | `ollama` | Prioridad: ollama → gemini → claude → disabled |
| `OLLAMA_BASE_URL` | **Sí** | `http://ollama-host.<tailnet>.ts.net:11434` | MagicDNS Tailscale (o IP). |
| `OLLAMA_MODEL` | No | `qwen2.5:7b-instruct-q4_K_M` | Modelo default. |
| `GEMINI_API_KEY` | **Sí** | `AIza…` | Google AI Studio (2.º fallback). |
| `GEMINI_MODEL` | No | `gemini-1.5-flash` | (default) |
| `ANTHROPIC_API_KEY` | **Sí** | `sk-ant-…` | Anthropic (3.º fallback). |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | (default) |
| `STORAGE_PATH` | No | `/data/uploads` | Railway Volume (ver §4). |
| `LOG_LEVEL` | No | `INFO` | debug, info, warning, error. |

**Cómo generar `JWT_SECRET` y `JWT_REFRESH_SECRET`:**

```bash
# En tu shell local
python -c "import secrets; print(secrets.token_hex(32))"
# Copiar el output y pegar en Railway
```

### 3.3 Servicio `worker` (Celery)

Hereda **todas** las de `api` (DATABASE_URL, REDIS_URL, AI_MODE, GEMINI_API_KEY, etc.)
más estas específicas:

| Variable | Requiere | Valor ejemplo | Descripción |
|---|---|---|---|
| `TS_AUTHKEY` | **Sí** | `tskey-auth-…` | Auth key reutilizable Tailscale con tag `tag:railway-worker`. |
| `TS_HOSTNAME` | **Sí** | `pmo-worker-railway` | Nombre del host en la red Tailscale. |
| `RESEND_API_KEY` | **Sí** | `re_xxxxxxxx` | Para enviar emails. |
| `RESEND_FROM` | **Sí** | `PMO·aaS <no-reply@pmo-aas.com>` | Sender email (dominio verificado en Resend). |
| `APP_BASE_URL` | **Sí** | `https://app.pmo-aas.com` | Base URL para links en emails. |

**Nota sobre `TS_AUTHKEY` y `TS_HOSTNAME`:**

- `TS_AUTHKEY` es generada en Tailscale Admin (ver [`docs/runbooks/networking/tailscale-setup.md`](../networking/tailscale-setup.md)).
- Debe ser **reutilizable** y **preauthorized** con tag `tag:railway-worker`.
- `TS_HOSTNAME=pmo-worker-railway` es el nombre que el worker tendrá en MagicDNS.
- El worker se conecta a la red Tailscale vía sidecar `start-worker.sh` (ver `apps/api/start-worker.sh`).

### 3.4 Servicio `web` (Next.js)

Hereda `NODE_ENV` + estas específicas:

| Variable | Requiere | Valor ejemplo | Descripción |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Sí** | `https://api.pmo-aas.com` | URL del backend (public, accesible desde browser). |
| `NEXTAUTH_URL` | **Sí** | `https://app.pmo-aas.com` | Canonical URL de la app (para NextAuth callbacks). |
| `NEXTAUTH_SECRET` | **Sí** | `<random 32+ chars>` | Llave para encriptar NextAuth session. Generar como en §3.2. |
| `NEXT_PUBLIC_GLITCHTIP_DSN` | No | `https://…@glitchtip.pmo-aas.com/2` | Sentry DSN si usas GlitchTip (error reporting). |

---

## 4. Volúmenes y storage

El servicio `api` y `worker` necesitan acceso al mismo directorio de uploads.

### 4.1 Crear un volumen compartido

Railway UI → Proyecto → **Storage** → **+ New Volume**:
- Nombre: `pmo-uploads`
- Mount path en `api`: `/data/uploads`
- Mount path en `worker`: `/data/uploads`

El volumen persiste entre deployments (ver `docs/runbooks/railway/DEPLOYMENT.md`
§3 para migraciones).

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
startCommand = "bash start-worker.sh"  # Levanta tailscaled + celery
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
- [ ] `AI_MODE=ollama`, variables Ollama configuradas.
- [ ] `GEMINI_API_KEY` + `ANTHROPIC_API_KEY` agregadas.
- [ ] `TS_AUTHKEY` + `TS_HOSTNAME` configurados en `worker`.
- [ ] `RESEND_API_KEY` + `RESEND_FROM` + `APP_BASE_URL` en `worker`.
- [ ] `NEXTAUTH_URL` + `NEXTAUTH_SECRET` + `NEXT_PUBLIC_API_URL` en `web`.
- [ ] Volumen `pmo-uploads` montado en `/data/uploads` en `api` y `worker`.
- [ ] Auto-deploy ON en rama `main`.
- [ ] Health checks respondiendo: `api /health`, `web /api/health`.
- [ ] Custom Domains `app.pmo-aas.com` y `api.pmo-aas.com` agregados (tras DNS listo).

---

## 11. Troubleshooting

| Síntoma | Causa | Solución |
|---|---|---|
| `JWT_SECRET not found` al boot de api | Variable no configurada | Generar y agregar a Railway `api`. |
| Worker no se conecta a Ollama (timeout) | `TS_AUTHKEY` falta o inválida | Ver [`docs/runbooks/networking/tailscale-setup.md`](../networking/tailscale-setup.md) §7. |
| Email no se envía | `RESEND_API_KEY` vacía o dominio no verificado | Ver [`docs/runbooks/email/resend-setup.md`](../email/resend-setup.md). |
| Frontend no alcanza backend (CORS error) | `ALLOWED_ORIGINS` no incluye dominio | Agregar a Railway `api` + redeploy. |
| Healthcheck falla (servicio marked unhealthy) | Database / Redis sin conexión | Verificar `DATABASE_URL` + `REDIS_URL` | plugins conectados. |
| Logs mostrando `ModuleNotFoundError` | `requirements.txt` desactualizado | Revisar build step en `railway.toml`. |

---

## 12. Referencias

- Architecture deployment: [`docs/runbooks/railway/DEPLOYMENT.md`](./DEPLOYMENT.md)
- DNS & custom domains: [`docs/runbooks/infra/dns-routing.md`](../infra/dns-routing.md)
- Tailscale + worker: [`docs/runbooks/networking/tailscale-setup.md`](../networking/tailscale-setup.md)
- Email (Resend): [`docs/runbooks/email/resend-setup.md`](../email/resend-setup.md)
- IA setup: [`docs/runbooks/ai/`](../ai/) — `groq-setup.md` + `byo-setup.md`
- Epic IA actual: [`docs/epics/EP008-ai.md`](../../epics/EP008-ai.md)
- Epic tunnel Ollama (archivada, superseded por DEC-017): [`docs/archive/cancelled-epics/EP016-local-ai-tunnel.md`](../../archive/cancelled-epics/EP016-local-ai-tunnel.md)
