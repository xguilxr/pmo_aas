# PMO-aaS — Project Management Office as a Service

> Plataforma SaaS multi-tenant para gestionar portafolios, programas y proyectos. Reconstruida sobre **Railway** con un stack limpio, fluido y rápido, con estética inspirada en macOS/iPadOS.

[![Stack](https://img.shields.io/badge/stack-Next.js%2015%20%2B%20FastAPI-black)]()
[![DB](https://img.shields.io/badge/db-PostgreSQL%2016-blue)]()
[![Deploy](https://img.shields.io/badge/deploy-Railway-purple)]()
[![AI](https://img.shields.io/badge/ai-Ollama%20%7C%20Claude-orange)]()

---

## ¿Qué es?

PMO-aaS es una herramienta para Project Management Offices que necesitan:

- **Gestionar el ciclo de vida completo** de un proyecto: solicitud → aprobación → ejecución → cierre.
- **Jerarquía organizacional clara**: PMO → Organización → Programa → Proyecto.
- **6 módulos transversales** por proyecto: Riesgos, Incidencias, Cambios, Documentos, Lecciones, Minutas.
- **Dashboard accionable** con KPIs, salud del portafolio y Plan vs Real.
- **IA local** (Ollama) para generar minutas desde transcripciones y reportes de avance.
- **Integración con Microsoft Project** para importar .mpp/.xml y visualizar Gantt.
- **Multi-tenant estricto** con aislamiento a nivel de fila + Super Admin platform-wide.

---

## Documentación

Toda la documentación técnica y de producto vive en [`docs/`](./docs). Arranca por aquí:

| Área | Ruta | Descripción |
|---|---|---|
| Visión general | [`docs/00-overview.md`](./docs/00-overview.md) | Misión, alcance, personas, KPIs del proyecto |
| Arquitectura | [`docs/architecture/`](./docs/architecture/) | C4, stack, BD, deploy en Railway, API |
| Épicas | [`docs/epics/`](./docs/epics/) | EP001-EP009 con User Stories + Test Cases |
| Testing | [`docs/testing/`](./docs/testing/) | Matriz de trazabilidad, multi-tenant isolation |
| Design System | [`docs/design-system/`](./docs/design-system/) | Tokens, componentes, motion (estilo Apple) |
| IA | [`docs/ai/`](./docs/ai/) | Setup de modelo local, prompts, fallback |
| ADRs | [`docs/adr/`](./docs/adr/) | Decisiones arquitectónicas registradas |
| Glosario | [`docs/glossary.md`](./docs/glossary.md) | Términos de negocio ES/EN |
| Plan de construcción | [`docs/construction-plan.md`](./docs/construction-plan.md) | Carriles de trabajo (Claude / usuario) y cronograma |
| Agentes / Skills | [`docs/agents-skills-proposals.md`](./docs/agents-skills-proposals.md) | Uso de claudio-enterprises + complementos PMO |
| Propuestas genéricas | [`docs/agents-skills-generic-proposals.md`](./docs/agents-skills-generic-proposals.md) | Agentes/skills reutilizables para tu plugin |
| Setup local | [`docs/setup-dev.md`](./docs/setup-dev.md) | Instalación detallada (Windows sin Docker) |

---

## Stack resumido

| Capa | Tecnología | Por qué |
|---|---|---|
| Frontend | **Next.js 15** (App Router) + TypeScript 5 + Tailwind v4 + shadcn/ui | SSR, RSC, DX, estética Apple con Radix |
| Backend | **FastAPI 0.115** + Python 3.12 + Pydantic v2 | Tipado, performance, OpenAPI auto |
| BD | **PostgreSQL 16** (Railway) + Prisma/SQLAlchemy 2.0 | JSONB, RLS para multi-tenant |
| Auth | JWT + refresh tokens + bcrypt | Standard, sin vendor lock |
| IA local | **Ollama** + Qwen 2.5 (7B/14B) | Privacidad, sin coste por token — **default** |
| IA gratis (2.º) | **Google Gemini 1.5 Flash** (free tier) | 15 RPM / 1M tokens/día sin costo |
| IA premium (3.º) | **Anthropic Claude Sonnet 4.6** | Opcional por tenant para cargas complejas |
| MS Project | **MPXJ** (Java 21) + **frappe-gantt** | Abre .mpp/.xml/.xlsx nativo |
| Jobs | **Celery** (Python) + Redis | Reportes programados, generación IA async |
| Observabilidad | **GlitchTip** self-hosted + Railway Logs + **UptimeRobot** free | Errores + traces + uptime sin costo extra |

Detalles completos en [`docs/architecture/stack.md`](./docs/architecture/stack.md).

---

## Quickstart local

**Sin Docker obligatorio.** Elige tu ruta según tu SO. Detalles en [`docs/setup-dev.md`](./docs/setup-dev.md).

### Ruta A — Windows nativo (recomendado si ya tuviste problemas con Docker)

```powershell
# Prerequisitos (una vez):
#   - Node 20 LTS      https://nodejs.org
#   - Python 3.12      https://www.python.org
#   - PostgreSQL 16    https://www.postgresql.org/download/windows  (o Railway dev DB)
#   - Redis            Memurai (https://www.memurai.com) o WSL/Ubuntu
#   - Ollama           https://ollama.com/download/windows
#   - pnpm             corepack enable; corepack prepare pnpm@latest --activate

git clone git@github.com:xguilxr/pmo_aas.git; cd pmo_aas
pnpm install
cp .env.example .env   # rellena DATABASE_URL, REDIS_URL, JWT_SECRET, etc.

# Backend
cd apps\api
py -3.12 -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8080

# Frontend (otra consola)
cd apps\web
pnpm dev                          # http://localhost:3000

# Modelo IA (una vez, en otra consola)
ollama pull qwen2.5:7b-instruct-q4_K_M
```

### Ruta B — Dev services en Railway (cero instalación local pesada)

Crea un entorno `dev` en Railway con los plugins Postgres y Redis, copia las
`DATABASE_URL` / `REDIS_URL` a tu `.env`, y corre frontend y backend en local.
Ollama lo pones local (free) o en otro VPS. Guía paso a paso en
[`docs/construction-plan.md`](./docs/construction-plan.md).

### Ruta C — macOS / Linux con Docker (si quieres todo contenido)

```bash
git clone git@github.com:xguilxr/pmo_aas.git && cd pmo_aas
docker compose up -d postgres redis    # solo Postgres + Redis
pnpm install
cd apps/api && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && alembic upgrade head
uvicorn app.main:app --reload --port 8080 &
cd ../web && pnpm dev
```

Ollama se instala **nativo** en el host (más rápido que en container y sin
fricción de GPU passthrough). Guía de despliegue productivo en
[`docs/architecture/deployment-railway.md`](./docs/architecture/deployment-railway.md).

---

## Estructura del repo

```
pmo_aas/
├── apps/
│   ├── web/                      # Next.js 15 (frontend)
│   └── api/                      # FastAPI (backend)
├── packages/
│   ├── ui/                       # Design system (shadcn + tokens)
│   ├── config/                   # ESLint, tsconfig, tailwind preset
│   └── sdk/                      # Cliente tipado del API para el web
├── docs/                         # Toda la documentación
├── docker-compose.yml            # Dev local
├── railway.json                  # Infra como código para Railway
└── .github/workflows/            # CI (lint, test, build)
```

---

## Convenciones

- **Ramas**: `feat/*`, `fix/*`, `chore/*`, `docs/*`. PRs pequeños (<400 líneas).
- **Commits**: Conventional Commits (`feat(auth): …`).
- **IDs de trazabilidad**: `EP-XXX` (épica), `US-XXX` (user story), `TC-XXX` (test case), `ADR-XXX`.
- **Idiomas**: Español (default UI/BD) + Inglés. Claves i18n en `packages/i18n/`.
- **Moneda**: MXN con formato `$1,234.56`.
- **Folios**: `SOL-YYYY-NNN`, `PRJ-YYYY-NNN`, `RIS-…`, `INC-…`, `CHG-…`, `DOC-…`, `LEC-…`, `MIN-…`.

---

## Licencia

Propietaria. Uso interno xguilxr / PMO-aaS.
