# Railway — Arquitectura, CI/CD y Migraciones

**ID:** `DOC-RAILWAY-DEPLOYMENT`

Referencia técnica de la arquitectura de despliegue en Railway,
CI/CD pipeline, y operaciones post-deploy.

---

## 1. Servicios Railway

El proyecto se despliega como **6 componentes** dentro de un mismo **Project**:

```mermaid
flowchart LR
    WEB["web<br/>Next.js 15 (Nixpacks)"]
    API["api<br/>FastAPI (Dockerfile)"]
    WORKER["worker<br/>Celery + beat (mismo Dockerfile)"]
    DB[("postgres<br/>Railway Plugin")]
    REDIS[("redis<br/>Railway Plugin")]
    GROQ["Groq API<br/>(modo platform)"]
    BYO["BYO provider<br/>(modo byo)"]
    R2[("Cloudflare R2<br/>(STORAGE_BACKEND=s3)")]

    WEB --> API
    API --> DB
    API --> REDIS
    API -.-> R2
    WORKER --> DB
    WORKER --> REDIS
    WORKER -.-> R2
    WORKER -->|platform| GROQ
    WORKER -.->|byo| BYO
```

| Servicio | Root | Runtime | Auto-deploy | Estado |
|---|---|---|---|---|
| `web` | `apps/web` | Nixpacks (Node 20, `npm`) | Sí (rolling) | ✅ |
| `api` | `apps/api` | **Dockerfile** (JRE 21 + MPXJ + WeasyPrint) | Sí (rolling) | ✅ |
| `worker` | `apps/api` (mismo Dockerfile, start command diferente) | Celery + beat | Sí | ✅ |
| `postgres` | Plugin | PostgreSQL 16 | No (persistente) | ✅ |
| `redis` | Plugin | Redis 7 | No | ✅ |

> **No hay** servicio `ollama` (BUG-053 eliminó OllamaProvider). **No hay** servicio `glitchtip` (sin observabilidad APM hoy).

---

## 2. Archivos de configuración (railway.json y railway.toml)

### 2.1 railway.json (raíz)

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "pnpm start",
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 2.2 apps/api/railway.toml

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 60
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

El `CMD` default del Dockerfile aplica para `api`:

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
```

(Migraciones corren al arranque del contenedor `api`.)

### 2.3 apps/api/worker.railway.toml

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "celery -A app.workers.celery_app worker --beat --loglevel=info --concurrency=2"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

El worker corre Celery + **beat embebido** (`--beat`, BUG-036) — procesa
tasks de IA (Groq platform o BYO cloud) y dispara las tareas periódicas
(`scheduled_reports.send_due_reports`, `scheduled_minutes.send_due_minutes`).
Si se escala a >1 replica, separar beat a un servicio dedicado.

Hasta ENH-023 (2026-04-23) tenía un wrapper `start-worker.sh` con
sidecar Tailscale (US-048); DEC-017 lo eliminó.

### 2.4 apps/web/railway.toml

```toml
[build]
builder = "NIXPACKS"
buildCommand = "npm install && npm run build"

[deploy]
startCommand = "pnpm --filter web start -p $PORT"
healthcheckPath = "/api/health"
numReplicas = 2
```

---

## 3. Migraciones de base de datos

### 3.1 Alembic en build step

Alembic corre automático en el `buildCommand` del servicio `api`:

```bash
buildCommand = "pip install -r requirements.txt && alembic upgrade head"
```

**Flujo:**
1. Build job starts → `pip install`.
2. **Alembic runs** → aplica migraciones pending en `apps/api/alembic/versions/`.
3. Si success → servicio arranca.
4. Si error → build falla, deploy se cancela, versión anterior sigue live.

### 3.2 Crear una migración

```bash
cd apps/api
alembic revision --autogenerate -m "Add column X to table Y"
# Generates: alembic/versions/xxx_add_column_x_to_table_y.py
```

Edita el archivo generado para:
- Verificar que la migración es correcta.
- Agregar `down()` para rollback.

**Registra en [`docs/epics/DB-CHANGES.md`](../../epics/DB-CHANGES.md) si es un cambio material.**

### 3.3 Rollback

Si una migración rompe producción:

```bash
# En local (o vía Railway one-off job)
alembic downgrade -1

# Deployar hotfix branch
git push origin hotfix/revert-migration-xxx
# PR + merge a main
# Railway redeploya automático
```

**⚠️ Nota:** Rollback de datos (si la migración drop-ea columnas) no se revierte automático.
Considerar backup antes de migración destructiva.

### 3.4 Migraciones largas

Para migraciones que toman > 30s, no usar `buildCommand`:

```bash
# En cambio, ejecutar antes de release como one-off job
railway run --service api alembic upgrade head

# Luego: mergea la rama con .py de migración
# Railway detecta el cambio pero no re-runea Alembic (ya ejecutado)
```

---

## 4. Storage de uploads (object storage S3-compatible)

> **Importante:** Railway Volumes no se pueden compartir entre
> servicios, así que api + worker no pueden usar un volume montado.
> Se usa **Cloudflare R2** (S3-compatible, free tier 10 GB,
> zero egress). Runbook completo:
> [`docs/runbooks/infra/uploads-storage.md`](../infra/uploads-storage.md).

Estructura dentro del bucket `pmo-aas-uploads`:

```
s3://pmo-aas-uploads/
└── documents/
    └── {tenant_id}/
        └── {project_id}/
            ├── {doc-uuid}.pdf
            ├── {doc-uuid}.xlsx
            └── {doc-uuid}.docx
```

(Futuro US-066.x: namespace separado `reports/` para PDFs generados
por el worker si se quiere rotación distinta de la de `documents/`.)

**Backup y durabilidad:**
- R2 es multi-AZ nativo — Cloudflare garantiza durabilidad 99.999999999%.
- **Versioning**: habilitar en bucket settings para recuperar objetos
  borrados/sobrescritos por 30 días.
- Backup cross-region a Backblaze B2: opcional, `rclone sync`
  nocturno a B2 bucket secundario (ver runbook §8).

---

## 5. CI/CD Pipeline

### 5.1 GitHub Actions (.github/workflows/ci.yml)

Estructura real (ver `.github/workflows/ci.yml` para el detalle):

```yaml
on:
  push: { branches: [main] }
  pull_request:

jobs:
  changes:                       # dorny/paths-filter detecta api/web/workflows
  lint:                          # ruff (solo si cambió api)
  api-tests-smoke:               # pytest -n auto -m "not heavy"
  api-migrations-postgres:       # alembic upgrade → downgrade → upgrade
  api-tests-heavy:               # solo en push a main
```

**Qué valida:**
- **Lint**: `ruff` con reglas `E,F,I,N,UP,B,A,C4,RUF` (apps/api/pyproject.toml).
- **Tests backend**: `pytest` + `pytest-asyncio` en paralelo (`-n auto`).
  Lane "heavy" para tests pesados que solo corren en `main`.
- **Migraciones**: Postgres efímero, valida reversibilidad upgrade → downgrade → upgrade (ENH-044).

> **Sin Playwright / Schemathesis en CI hoy** — diferidos. `turbo` no se usa (no hay `turbo.json` ni dependencia en el repo).

**Status:** ✅ Si todo pasa → se puede mergear a `main`.

### 5.2 Auto-deploy desde Railway

Rama `main` → `production` (con aprobación manual en Railway UI si aplica).

**Watch paths** (ver `railway.toml` en cada app):
- Cambio en `apps/web/` → redeploya servicio `web`.
- Cambio en `apps/api/app/` → redeploya servicios `api` + `worker`.
- Cambio en `apps/api/alembic/` → corre migración al buildear `api`.

---

## 6. Dominios

| Entorno | Frontend | API |
|---|---|---|
| **Production** | `app.pmo-aas.com` | `api.pmo-aas.com` |
| **Staging** (si aplica) | `staging.pmo-aas.com` | `api-staging.pmo-aas.com` |

DNS en Cloudflare, TLS gestionado por Railway (Let's Encrypt auto).

Ver [`docs/runbooks/infra/dns-routing.md`](../infra/dns-routing.md) para setup.

---

## 7. Healthchecks y monitoreo

### 7.1 Endpoints de salud

- **API**: `GET /health` → `{"status": "ok", "version": "...", "time": "..."}`
- **Web**: `GET /api/health` → proxea al backend + retorna salud combinada.
- **Worker**: Sin healthcheck HTTP (servicio background).

Railway pinga c/60s. Si falla 3× → marca degraded o auto-redeploy (si enabled).

### 7.2 Logs

```bash
railway logs --service api --tail
railway logs --service worker --tail
railway logs --service web --tail
```

También disponibles en Railway UI → **Logs** tab.

### 7.3 Monitoreo externo (opcional)

Usar **UptimeRobot** para ping externo c/60s desde ubicación remota:
- Monitor: `https://app.pmo-aas.com/api/health`
- Alert Slack si status != 200.

---

## 8. Operaciones comunes

### Restart rolling

Railway UI → servicio → **Restart** (rolling si `numReplicas > 1`).

### Ejecutar script one-off

```bash
railway run --service api python scripts/seed_superadmin.py
```

### Conectarse a Postgres

```bash
railway run --service api psql $DATABASE_URL
```

### Backup Postgres

```bash
railway run --service api pg_dump $DATABASE_URL > backup.sql
```

---

## 9. Costes estimados

| Componente | Entorno | USD/mes |
|---|---|---|
| `web` (2 replicas) | Production | ~$20 |
| `api` (2 replicas) | Production | ~$20 |
| `worker` (1 replica) | Production | ~$7 |
| Postgres plugin | Shared | ~$15 |
| Redis plugin | Shared | ~$10 |
| **Total mínimo** | — | **~$72/mes** |

Agregale:
- Cloudflare DNS: $0 (free tier).
- Resend emails: $0–20 (free/pro).
- Groq API (modo platform, free tier / pay-as-you-go): $0–30.
- Cloudflare R2 (10 GB free tier): $0.
- Providers BYO (OpenAI/Claude/Gemini/Azure/Perplexity): los paga cada tenant con su key — $0 plataforma.

**Total estimado:** ~$110–160/mes.

---

## 10. Troubleshooting

| Síntoma | Causa | Solución |
|---|---|---|
| Servicio marked unhealthy | Healthcheck timeout | `railway logs --tail`, revisar logs. |
| Build falla (Alembic error) | Migración inválida | Revisar `alembic/versions/` última, fix y re-push. |
| CORS error en frontend | `ALLOWED_ORIGINS` no configurado | Update Railway `api` → redeploy. |
| Memory leak en worker | Celery task holding refs | Ajustar `--concurrency` en `worker.railway.toml`. |
| OOM en Postgres | Volumen full | `railway run --service api pg_reindex` o expand volumen. |

---

## 11. Escalado futuro (post-MVP)

- **Múltiples regiones**: Railway multi-region deployments.
- **Database read replicas**: Postgres read replica para queries pesadas.
- **S3 storage ya en uso**: Cloudflare R2 es el backend desde US-066 (Sprint 4 v1.3). Si se quiere migrar a AWS S3 puro, cambiar `S3_ENDPOINT_URL` y `S3_REGION` — el código usa boto3 y es portable.
- **Message queue**: Escalado de worker con separate Celery broker.

---

## Referencias

- Railway docs — https://docs.railway.app/
- Alembic docs — https://alembic.sqlalchemy.org/
- Next.js deployment — https://nextjs.org/docs/deployment
- FastAPI deployment — https://fastapi.tiangolo.com/deployment/
- Setup variables — [`docs/runbooks/railway/SETUP.md`](./SETUP.md)
- DNS — [`docs/runbooks/infra/dns-routing.md`](../infra/dns-routing.md)
