---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 180d
---

# Stack tecnológico

**ID:** `DOC-ARCH-STACK`
**Última verificación contra código:** 2026-05-23.

Decisiones de tecnología por capa, con justificación explícita. Cada decisión debería tener un ADR en [`../adr/`](../adr/).

> **Política:** este doc refleja lo que está realmente instalado en `apps/web/package.json` y `apps/api/requirements*.txt`. Si una herramienta aparece aquí, está en el repo. Si se evaluó y no se adoptó, va en "Qué evitamos" o como nota explícita.

---

## Frontend — Next.js 15 + React 19 + TypeScript

Dependencias reales (`apps/web/package.json`):

```jsonc
{
  "dependencies": {
    "next": "15.0.7",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "@dnd-kit/core": "6.1.0",
    "@dnd-kit/sortable": "8.0.0",
    "@dnd-kit/utilities": "3.2.2",
    "lucide-react": "0.453.0",
    "clsx": "2.1.1",
    "tailwind-merge": "2.5.4",
    "exceljs": "^4.4.0"
  },
  "devDependencies": {
    "tailwindcss": "4.1.14",
    "@tailwindcss/postcss": "4.1.14",
    "postcss": "8.4.49",
    "typescript": "5.6.3"
  }
}
```

**Por qué:**
- **App Router + RSC** → TTFB bajo, menos JS al cliente, streaming con Suspense.
- **Tailwind v4** → CSS-first config, tokens del design system vía `@theme`.
- **@dnd-kit** para drag&drop (RAID, plan de tareas).
- **lucide-react** como única familia de íconos.
- **clsx + tailwind-merge** combinados en `lib/cn.ts` para componer clases sin pisar conflictos.
- **exceljs** para generar/leer `.xlsx` en cliente (import wizard y exportaciones).

**Qué NO está en el repo (descartado o no necesario hasta ahora):**
- ❌ TanStack Query / Redux / Zustand — la app usa `fetch` + RSC + `useState/useReducer` locales (`apps/web/lib/api/*` envuelve llamadas REST). No hay store global.
- ❌ shadcn/ui formal — solo se reutilizan ideas (utility `cn`, primitivas Radix-like manuales en `components/ui/`). No hay registro shadcn ni dependencia `@radix-ui/*`.
- ❌ next-intl / i18next — la UI hoy es **solo en español**. Se difirió i18n.
- ❌ react-hook-form / zod en cliente — los formularios usan estado controlado + validación inline.
- ❌ recharts / chart.js — los gráficos están escritos a mano con SVG (ej. `gantt-view.tsx`).
- ❌ frappe-gantt — no instalado. El Gantt es SVG propio en `components/gantt-view.tsx`.
- ❌ framer-motion — animaciones con CSS / `transition` de Tailwind.
- ❌ Storybook — no configurado.

---

## Backend — FastAPI + Python 3.12

Dependencias reales (`apps/api/requirements.txt`):

```txt
fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.5.2
email-validator==2.2.0
sqlalchemy==2.0.35
alembic==1.13.3
asyncpg==0.29.0
psycopg[binary]==3.2.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
python-multipart==0.0.12
httpx==0.27.2
slowapi==0.1.9
redis==5.1.1
celery[redis]==5.4.0
tenacity==9.0.0
structlog==24.4.0
uuid7==0.1.0
python-dotenv==1.0.1
jinja2==3.1.4
weasyprint==68.1            # PDF de reportes (EP014 — US-037)
python-docx==1.2.0          # Minuta .docx (EP014 — US-040)
boto3==1.35.49              # S3-compatible storage (Cloudflare R2 — US-066)
openpyxl==3.1.5             # lectura .xlsx en imports
```

**Por qué:**
- **FastAPI** → OpenAPI auto, typing con Pydantic v2, performance async nativa.
- **SQLAlchemy 2.0** estilo `async` + `select()` moderno, compatible con RLS.
- **Alembic** para migraciones versionadas y reversibles.
- **Pydantic v2** → validación 10x más rápida que v1, schemas compartibles con frontend vía OpenAPI.
- **httpx** es el cliente HTTP único: se usa también para hablar con proveedores de IA (Groq, Anthropic, Gemini, OpenAI) sin SDKs propietarios.
- **structlog** para logs estructurados (JSON en prod, pretty en dev).
- **tenacity** para retries (carga MS Project, llamadas IA).
- **weasyprint + jinja2** → render HTML→PDF de reportes.
- **python-docx** → minutas exportadas a Word.
- **boto3** → cliente S3 para Cloudflare R2 (object storage de uploads).

**Qué NO está en el repo (decisión consciente):**
- ❌ `google-generativeai`, `anthropic`, `openai` SDKs — se llaman las APIs vía `httpx` directo. Evita dependencia transitiva pesada y permite cubrirlas con un solo mocking layer en tests.
- ❌ `sentry-sdk` — sin observabilidad APM hoy. Logs centralizados vía Railway + structlog. Se evaluará reintroducir cuando haya tráfico que lo justifique.

**Convenciones:**
- Rutas tenant-scoped bajo `/api/v1/…` con dependencia `get_current_tenant`.
- Super admin bajo `/api/v1/superadmin/…` con dependencia `get_superadmin_user`.
- Errores: `{ "detail": str, "code": "ERR_CODE", "fields": {...} }`.

---

## Base de datos — PostgreSQL 16

- **Railway Postgres** plan Pro (conexiones, backups).
- Extensiones: `pg_trgm` (búsqueda fuzzy), `uuid-ossp`, `pgcrypto`.
- **Row-Level Security** activo en todas las tablas tenant-scoped. Ver [`database.md`](./database.md).
- **Conexión**: `asyncpg` con pool de 20 conexiones por instancia API.

Alternativa evaluada: **MongoDB** → descartada. Queries relacionales complejas (Plan vs Real, agregaciones por jerarquía) son más naturales en SQL.

---

## Caché y colas — Redis 7

- **Railway Redis** para:
  - Rate limiting (`slowapi`)
  - Colas de jobs (generación IA, envío de reportes, minutas programadas)
  - Caché de respuestas cacheables (KPIs del dashboard, TTL 5 min)
  - Sesiones invalidadas (token blacklist)
- **Cola**: **Celery** (Python-only). El worker corre Celery directo contra Redis. Tasks vivas en `apps/api/app/workers/tasks/`: `ai.py`, `notifications.py`, `scheduled_minutes.py`, `scheduled_reports.py`.

---

## Storage de archivos

Backend dual (`apps/api/app/services/document_storage.py` + `core/config.py`):

| `STORAGE_BACKEND` | Para qué | Notas |
|---|---|---|
| `local` (default dev) | Carpeta en disco (`/data/uploads/{tenant_slug}`) | Funciona con Railway Volume; OK en dev/staging. |
| `s3` (prod) | S3-compatible: Cloudflare R2 (default), Backblaze B2, AWS S3, MinIO | Vars `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION` (`auto` para R2), `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`. |

US-066 introdujo el backend S3 para evitar perder uploads si Railway recicla el volumen.

---

## Autenticación — JWT + refresh tokens

- Access token: JWT HS256, TTL **1 h** (`ACCESS_TOKEN_TTL_SEC=3600`), claims `sub`, `tenant_ids`, `is_superadmin`.
- Refresh token: JWT HS256, TTL **30 días** (`REFRESH_TOKEN_TTL_SEC=2592000`), cookie `HttpOnly; Secure; SameSite=Strict`.
- Contraseñas: `bcrypt` con `rounds=12` (`BCRYPT_ROUNDS=12`).
- Reset: token único de 1 uso con TTL 30 min (vía email o mostrado al admin una vez).

Detalles en [`security-multitenant.md`](./security-multitenant.md).

---

## IA — modo `platform` (Groq) y modo `byo` (multi-provider)

Definido en `apps/api/app/services/ai/`. Ver también `EP008-ai.md`.

### Modo `platform` (default para tenants nuevos)

- Provider único: **Groq** (`api.groq.com/openai/v1`, API OpenAI-compatible).
- Modelo default: `llama-3.3-70b-versatile` (override por tenant desde `/superadmin/ai`).
- API key: `platform_ai_settings.groq_api_key_encrypted` (cifrada con Fernet) o env `GROQ_API_KEY` como fallback.
- Sin infra propia: latencia ~300–600 ms.

> **Ollama fue eliminado** en BUG-053 (2026-05-08). Ya no hay `OllamaProvider` ni cascada legacy `ollama → gemini → claude`. El runbook `runbooks/ai/groq-setup.md` reemplaza a los antiguos `local-ollama-setup` y `local-model-setup`.

### Modo `byo` (Bring Your Own)

El admin del tenant configura uno o más providers desde `/admin/ai`. Catálogo real en `apps/api/app/services/ai/byo_catalog.py`:

| key | Label | Notas |
|---|---|---|
| `openai` | OpenAI (ChatGPT) | gpt-4o-mini / gpt-4o / gpt-4-turbo |
| `claude` | Anthropic (Claude) | claude-sonnet-* via API directa |
| `gemini` | Google Gemini | gemini-1.5-flash / gemini-1.5-pro |
| `perplexity` | Perplexity | sonar / sonar-pro |
| `azure` | **Microsoft Copilot M365** (Azure OpenAI) | gpt-4o / gpt-4 / gpt-35-turbo; requiere endpoint + deployment |
| `custom` | Otro provider compatible OpenAI | base_url + api_key + modelo |

El provider `groq` también está disponible en modo BYO si el tenant trae su propia key.

El runtime (`provider.py:resolve_provider`) selecciona implementación por `cfg["provider"]`. Cada implementación es una clase `*Provider` con interfaz común (`AIProvider` Protocol).

---

## Microsoft Project — MPXJ (subprocess Java)

- **MPXJ** (`net.sf.mpxj`) lee `.mpp` binario, `.xml` (MSPDI) y `.mpx`.
- Se invoca como **subprocess Java**, no JPype, para evitar JVM compartida:
  ```
  java -cp "/opt/mpxj/lib/*:/opt/mpxj/cli" MpxjCli <input.mpp>
  ```
- Wrapper Java en `apps/api/app/services/msproject/mpxj_cli/MpxjCli.java`. Classpath configurado en el `Dockerfile` del servicio `api`/`worker`.
- Formatos aceptados por el import wizard (`apps/web/components/import-wizard.tsx`): `.xlsx`, `.csv`, `.mpp`, `.xml`, `.mpx`, `.mspdi`.
- **Escritura `.mpp`** → no soportada (requiere MPXJ Pro comercial). Export sale como XLSX/CSV.
- Visualización Gantt → SVG propio en `apps/web/components/gantt-view.tsx` (no `frappe-gantt`).

---

## Observabilidad

Estado real hoy:

| Herramienta | Estado | Notas |
|---|---|---|
| **Railway Logs** | Activo | `structlog` formatea JSON en prod, texto en dev. |
| **Railway Metrics** | Activo (built-in) | CPU, memoria, red por servicio. |
| **Audit log** (tabla `audit_log`) | Activo | Forense y compliance; ver `database.md`. |
| **Sentry / GlitchTip** | **No integrado.** | El `sentry-sdk` se removió de `requirements.txt`. Pendiente decidir si reintroducir cuando crezca el tráfico. |
| **UptimeRobot** | No configurado en repo | Si se contrata, apuntar a `/api/health`. |
| **OpenTelemetry / tracing** | Descartado por ahora | Sin necesidad en MVP. |

---

## Testing

| Tipo | Herramienta | Estado |
|---|---|---|
| Unit / integración backend | `pytest` + `pytest-asyncio` + `pytest-xdist` | Activo. CI corre con marca `not heavy` en PR path y `heavy` en lane separada. |
| Coverage backend | `pytest-cov` | Disponible; sin gate de % en CI. |
| Lint backend | `ruff` 0.6.9 | Gate completo en CI (ENH-032). |
| Lint frontend | `next lint` | Activo. |
| E2E | Playwright | **No instalado.** Diferido. |
| Contract | Schemathesis | **No instalado.** Diferido. |
| Load | k6 | **No instalado.** Pre-release. |

CI: `.github/workflows/ci.yml` corre ruff + pytest (smoke + heavy lane).

---

## DevEx / Tooling

Estado real:

- **pnpm workspaces** (`pnpm@9.12.0`) + Node `>=20`. Workspaces: `apps/*`, `packages/*`.
- **Ruff** para Python (lint + format). Configurado en `apps/api/pyproject.toml`.
- **`next lint`** para frontend.
- **Sin Turborepo** — los scripts corren `pnpm -r` directo.
- **Sin Husky** — no hay pre-commit hooks instalados.
- **Sin Storybook**.
- **Sin Renovate / Dependabot configurado en el repo**.
- **Sin MkDocs** — la doc vive como markdown en `docs/`.

Si alguna se introduce, actualiza esta sección y deja nota en `DECISIONS.md`.

---

## Coste estimado mensual (Railway, plan Pro, 10 tenants iniciales)

| Servicio | USD/mes |
|---|---:|
| 2× API containers (Python) | 20 |
| 1× Worker container | 10 |
| 1× Web (Next.js) | 10 |
| Postgres Pro | 20 |
| Redis | 5 |
| Volume 20 GB (si STORAGE_BACKEND=local) | 5 |
| Cloudflare R2 (10 GB, free tier) | 0 |
| Groq API (modo platform, tier free / pay-as-you-go) | 0–30 |
| Resend (emails, 3k free) | 0–20 |
| **Total** | **~$70–120** |

Los providers BYO (OpenAI, Anthropic, Gemini, Azure/Copilot) los paga cada tenant con su propia API key. No entran al coste de plataforma.
