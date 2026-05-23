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
sentry-sdk[fastapi]==2.14.*  # apunta a GlitchTip self-hosted (compatible)
google-generativeai==0.8.*   # Gemini free tier (2.º fallback)
anthropic==0.39.*            # Claude (3.º fallback, opcional por tenant)
celery[redis]==5.4.*
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
- **Cola**: **Celery** (Python-only). El worker corre Celery directo contra Redis. La opción BullMQ (Node) quedó descartada en ADR-006 al consolidar el worker como Python.

---

## Autenticación — JWT + refresh tokens

- Access token: JWT HS256, TTL 1 h, claims `sub`, `tenant_ids`, `is_superadmin`.
- Refresh token: JWT HS256, TTL 30 días, almacenado en cookie `HttpOnly; Secure; SameSite=Strict`.
- Contraseñas: `bcrypt` con `rounds=12`.
- Reset: token único de 1 uso con TTL 30 min (vía email o mostrado al admin una vez).

Detalles en [`security-multitenant.md`](./security-multitenant.md).

---

## IA — modo platform (Groq) y modo BYO (Ollama / Gemini / Claude / OpenAI)

Desde **DEC-017** (2026-05) la plataforma separa dos modos por tenant:

### Modo `platform` (default)

Los tenants nuevos arrancan en este modo. La generación corre contra
**Groq** (Llama 3.1 / Mixtral hosteado), pagado por la plataforma:

- Latencia ~300–600 ms a nivel API.
- Sin infra a mantener (no hay servidor de IA propio).
- Cuota por tenant configurable desde `/superadmin/ai`.

### Modo `byo` (Bring Your Own)

El admin del tenant elige uno o varios providers desde `/admin/ai`. El
runtime resuelve en cascada según lo configurado:

1. **Ollama local** — privacidad total, cero costo por token, modelo
   `qwen2.5:7b-instruct-q4_K_M` default. Hosting: home-host con Cloudflare
   Tunnel, VPS con GPU, o Railway GPU cuando esté disponible.
2. **Google Gemini 1.5 Flash** — free tier **1M tokens/día**, 15 RPM. Útil
   cuando Ollama está caído o como provider económico secundario.
3. **Claude Sonnet 4.6** — máxima calidad; coste real por token.
4. **OpenAI / Perplexity** — soportados como alternativa.

> El antiguo orden "Ollama → Gemini → Claude" del MVP solo aplica a
> tenants en modo `byo` que repliquen esa configuración. El default de
> la plataforma es ahora Groq.

El `AIProvider` es polimórfico y el runtime escoge en cascada: intenta
primario, si falla o está deshabilitado pasa al siguiente. Ver
[`../ai/`](../ai/).

---

## Microsoft Project — MPXJ + frappe-gantt

- **MPXJ** (Java) → se ejecuta en un sidecar o se invoca vía subprocess.
- **frappe-gantt** → librería JS liviana (< 30 KB), suficiente para MVP.
- Post-MVP evaluamos **dhtmlx-gantt** si necesitamos drag&drop avanzado.

---

## Observabilidad (stack $0)

Ver ADR-011 actualizado. Todo lo siguiente es **free** o self-hosted:

| Herramienta | Para qué | Costo |
|---|---|---|
| **GlitchTip** (self-hosted en Railway) | Errores FE + BE, compatible con Sentry-SDK | ~$5/mes container |
| **Railway Logs** | Logs centralizados por servicio (ya incluido) | $0 |
| **Railway Metrics** | CPU, memoria, red | $0 |
| **UptimeRobot Free** | `/health` cada 5 min, 50 monitors, alertas email/Slack | $0 |
| **BetterStack Logs Free** (alternativa) | 1GB/mes, 3 días retención | $0 |
| **Audit log** (tabla propia) | Forense y compliance (negocio) | $0 |

Si crecemos y necesitamos tracing distribuido, **OpenTelemetry → Grafana
Cloud Free** (10k series, 50GB logs, 14d retención) cubre sin costo.

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
| GlitchTip container (observabilidad) | 5 |
| UptimeRobot Free | 0 |
| Ollama host — ver ADR-007 (home / VPS / $0) | 0-50 |
| Gemini free tier | 0 |
| Resend (emails, 3k free) | 0-20 |
| **Total** | **~$75-145** |

Claude API se presupuesta solo si un tenant lo activa explícitamente — el
coste se puede repercutir a ese tenant en su plan.
