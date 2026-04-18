# Stack tecnológico

**ID:** `DOC-ARCH-STACK`

Decisiones de tecnología por capa, con rationale explícito. Cada decisión debería tener un ADR en [`../adr/`](../adr/).

---

## Frontend — Next.js 15 + TypeScript

```ts
// apps/web/package.json (fragmento)
{
  "dependencies": {
    "next": "^15.0",
    "react": "^19.0",
    "typescript": "^5.5",
    "tailwindcss": "^4.0",
    "@radix-ui/react-*": "latest",
    "class-variance-authority": "^0.7",
    "framer-motion": "^11",
    "zod": "^3.23",
    "react-hook-form": "^7.52",
    "@tanstack/react-query": "^5.50",
    "@tanstack/react-table": "^8.20",
    "recharts": "^2.12",
    "frappe-gantt": "^0.8",
    "next-intl": "^3.17"
  }
}
```

**Por qué:**
- **App Router + RSC** → TTFB bajo, menos JS al cliente, streaming con Suspense.
- **shadcn/ui** → componentes copy-paste que usamos como base. Control total, sin dependencia.
- **Tailwind v4** → CSS-first config, `@theme` con tokens de design system.
- **TanStack Query** para mutations y caché client-side; RSC para lecturas iniciales.
- **next-intl** — i18n tipado ES/EN desde día 1.

**Qué evitamos:**
- ❌ Redux / Zustand global — usamos Server Actions + TanStack Query.
- ❌ Emotion / styled-components — Tailwind solo.
- ❌ Material UI — estética inconsistente con Apple look.

---

## Backend — FastAPI + Python 3.12

```txt
# apps/api/requirements.txt (esenciales)
fastapi==0.115.*
uvicorn[standard]==0.32.*
pydantic==2.9.*
pydantic-settings==2.5.*
sqlalchemy==2.0.*
alembic==1.13.*
asyncpg==0.29.*
psycopg[binary]==3.2.*
python-jose[cryptography]==3.3.*
passlib[bcrypt]==1.7.*
python-multipart==0.0.*
httpx==0.27.*
slowapi==0.1.9
sentry-sdk[fastapi]==2.14.*
celery[redis]==5.4.*         # alternativa a BullMQ si 100% Python
```

**Por qué:**
- **FastAPI** → OpenAPI auto, typing con Pydantic v2, performance async nativa.
- **SQLAlchemy 2.0** estilo `async` + `select()` moderno, compatible con RLS.
- **Alembic** para migraciones versionadas y reversibles.
- **Pydantic v2** → validación 10x más rápida que v1, schemas compartibles con frontend vía OpenAPI.

**Convenciones:**
- Todas las rutas de tenant viven bajo `/api/v1/…` con dependencia `get_current_tenant`.
- Super admin bajo `/api/v1/superadmin/…` con dependencia `get_superadmin_user`.
- Errores devuelven `{ "detail": str, "code": "ERR_CODE", "fields": {...} }`.

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
  - Colas de jobs (generación IA, envío de reportes)
  - Caché de respuestas cacheables (KPIs del dashboard, TTL 5 min)
  - Sesiones invalidadas (token blacklist)
- **Cola**: **Celery** (Python-only) o **BullMQ** (si worker en Node). Ver ADR-006.

---

## Autenticación — JWT + refresh tokens

- Access token: JWT HS256, TTL 1 h, claims `sub`, `tenant_ids`, `is_superadmin`.
- Refresh token: JWT HS256, TTL 30 días, almacenado en cookie `HttpOnly; Secure; SameSite=Strict`.
- Contraseñas: `bcrypt` con `rounds=12`.
- Reset: token único de 1 uso con TTL 30 min (vía email o mostrado al admin una vez).

Detalles en [`security-multitenant.md`](./security-multitenant.md).

---

## IA — Ollama (local) + Claude (fallback)

- **Ollama** expuesto en container separado en Railway (si hardware lo permite) o externo auto-hosteado.
- Modelo por defecto: `qwen2.5:7b-instruct-q4_K_M`.
- Fallback: **Claude Sonnet 4.6** vía Anthropic SDK con prompt caching.
- Detalles en [`../ai/`](../ai/).

---

## Microsoft Project — MPXJ + frappe-gantt

- **MPXJ** (Java) → se ejecuta en un sidecar o se invoca vía subprocess.
- **frappe-gantt** → librería JS liviana (< 30 KB), suficiente para MVP.
- Post-MVP evaluamos **dhtmlx-gantt** si necesitamos drag&drop avanzado.

---

## Observabilidad

| Herramienta | Para qué |
|---|---|
| **Sentry** | Errores del frontend + backend, traces (p95, p99) |
| **Railway Metrics** | CPU, memoria, red por servicio |
| **OpenTelemetry** (opcional) | Exportar traces a Tempo/Grafana si crecemos |
| **UptimeRobot** | `/health` cada 60 s, alertas a Slack |
| **Audit log** (tabla) | Forense y compliance |

---

## Testing

| Tipo | Herramienta | Cobertura objetivo |
|---|---|---|
| Unit frontend | Vitest + React Testing Library | 60% |
| Unit backend | pytest + pytest-asyncio | 80% |
| Integración | pytest + testcontainers (Postgres real) | endpoints críticos |
| E2E | Playwright | flujos core + TC-MT-* |
| Contract | Schemathesis contra OpenAPI | diff vs deploy previo |
| Load | k6 | release pre-flight (500 RPS) |

---

## DevEx / Tooling

- **pnpm workspaces** + **Turborepo** → builds incrementales.
- **Biome** o **Ruff + Black** → linting/formatting único.
- **Husky + lint-staged** → pre-commit.
- **Renovate** → actualización automática de dependencias.
- **Storybook** para `packages/ui`.
- **MkDocs Material** (opcional) para publicar `docs/` como sitio.

---

## Coste estimado mensual (Railway, plan Pro, 10 tenants iniciales)

| Servicio | USD/mes |
|---|---:|
| 2× API containers (Python) | 20 |
| 1× Worker container | 10 |
| 1× Web (Next.js) | 10 |
| Postgres Pro | 20 |
| Redis | 5 |
| Volume 20 GB | 5 |
| Sentry Team | 26 |
| Ollama host (GPU externa o self-hosted) | 0-50 |
| Resend (emails) | 20 |
| **Total** | **~$116-166** |

A Claude API se le presupuesta ~$50/mes adicional para fallback (estimado 20M tokens/mes con cache hit 70%).
