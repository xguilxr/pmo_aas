---
tipo: guia
responsable: propietario
estado: vigente
revisado: 2026-05-29
revisar_cada: 180d
---

# PMO-aaS — Project Management Office as a Service

> Plataforma SaaS multi-tenant para gestionar portafolios, programas y proyectos. Construida sobre **Railway** con un stack limpio, fluido y rápido, con estética inspirada en macOS/iPadOS.

[![Stack](https://img.shields.io/badge/stack-Next.js%2015%20%2B%20FastAPI-black)]()
[![DB](https://img.shields.io/badge/db-PostgreSQL%2016-blue)]()
[![Deploy](https://img.shields.io/badge/deploy-Railway-purple)]()
[![Storage](https://img.shields.io/badge/storage-Cloudflare%20R2-orange)]()
[![AI](https://img.shields.io/badge/ai-Groq%20%7C%20Gemini%20%7C%20Claude%20%7C%20OpenAI-red)]()
[![Sprint](https://img.shields.io/badge/sprint-33%20v1.28-green)]()
[![License](https://img.shields.io/badge/license-Proprietary-red)](./LICENSE)

---

## License

Copyright (c) 2026 David Eduardo Aguilar Guillen. **All rights reserved.**

This repository is published for transparency and reference only. Use,
copying, modification, redistribution, hosting, deployment, and AI/ML
training are **not permitted** without prior written permission. See
[`LICENSE`](./LICENSE) for full terms.

For commercial or evaluation licensing inquiries, contact the owner via
[github.com/xguilxr](https://github.com/xguilxr).

---

## ¿Qué es?

PMO-aaS es una herramienta para Project Management Offices que necesitan:

- **Gestionar el ciclo de vida completo** de un proyecto: solicitud → aprobación → ejecución → cierre.
- **Jerarquía organizacional clara**: PMO → Organización → Portafolio ⊃ Programa → Proyecto. El portafolio agrupa por decisión de inversión, no por organigrama (ADR-037).
- **6 módulos transversales** por proyecto: Riesgos, Incidencias, Cambios, Documentos, Lecciones, Minutas.
- **Dashboard accionable** con KPIs, salud del portafolio y Plan vs Real.
- **Charter editable** + sección RAID + áreas de proyecto + stakeholders catálogo.
- **IA multi-proveedor** (Groq como plataforma + BYO: OpenAI, Gemini, Claude, Perplexity, Azure, custom) para minutas, reportes de avance, análisis y asistente conversacional.
- **Integración con Microsoft Project** para importar `.mpp/.xml` y visualizar Gantt.
- **Permisos por capability** + Super Admin platform-wide + tenant-cross dashboards.
- **Notificaciones** por evento + email vía Resend + reportes programados.
- **Multi-tenant estricto** con aislamiento a nivel de fila + Storage S3 namespacing por tenant.
- **Hard delete de dos pasos** (US-088): desactivar primero, luego eliminar permanentemente con typed-confirm + cascade.

---

## Documentación

Toda la documentación técnica y de producto vive en [`docs/`](./docs). Arranca por aquí:

| Área | Ruta | Descripción |
|---|---|---|
| Arquitectura | [`docs/architecture/`](./docs/architecture/) | Stack, BD, deploy en Railway, API, multi-tenant |
| Épicas | [`docs/epics/`](./docs/epics/) | EP001–EP015 con User Stories + Test Cases |
| Sprint actual | [`docs/project-management/SPRINT.md`](./docs/project-management/SPRINT.md) | IN-PROGRESS, INBOX, QUEUE, bloques y DONE del sprint |
| Histórico de sprints | [`docs/project-management/SPRINT-DONE-HISTORY.md`](./docs/project-management/SPRINT-DONE-HISTORY.md) | Sprints cerrados |
| Runbooks | [`docs/runbooks/`](./docs/runbooks/) | Storage R2, Resend email, MS Project import, deploy Railway, etc. |
| ADRs | [`docs/adr/`](./docs/adr/) | Decisiones arquitectónicas (ADR-001 a ADR-017) |
| Testing | [`docs/testing/`](./docs/testing/) | Matriz de trazabilidad, multi-tenant isolation |
| Reglas de Claude Code | [`CLAUDE.md`](./CLAUDE.md) | Numeración (US/BUG/ENH), gates, ciclo issue→fix→comment |

---

## Stack resumido

| Capa | Tecnología | Por qué |
|---|---|---|
| Frontend | **Next.js 15** (App Router, RSC) + TypeScript 5 + Tailwind v4 | SSR, DX, estética Apple |
| Backend | **FastAPI 0.115** + Python 3.12 + Pydantic v2 + SQLAlchemy 2.0 async | Tipado, performance, OpenAPI auto |
| BD | **PostgreSQL 16** (Railway) + Alembic migrations | Multi-tenant por columna `tenant_id`, FK CASCADE selectivo |
| Storage | **Cloudflare R2** (S3-compatible) vía boto3 | Object storage para documentos + branding logos. Ver [`docs/runbooks/infra/uploads-storage.md`](./docs/runbooks/infra/uploads-storage.md) |
| Auth | JWT + refresh tokens + bcrypt + role_type (admin/user/viewer) | Capabilities por módulo en `app/core/permissions.py` |
| IA | **Groq** (plataforma) + BYO: **OpenAI**, **Google Gemini**, **Anthropic Claude**, **Perplexity**, **Azure**, custom | Multi-provider por tenant (modo platform/byo/disabled) |
| MS Project | **MPXJ** (Java 21) + **frappe-gantt** | Importa `.mpp/.xml/.xlsx` |
| Jobs | **Celery** (Python) + Redis | Reportes programados, generación IA async, notificaciones email |
| Email | **Resend** (transactional) | Notificaciones, reset de password, alertas |
| CI/CD | GitHub Actions + Railway autodeploy + alembic gate contra Postgres efímero | Migrations validadas en CI antes de deploy |

Detalles completos en [`docs/architecture/stack.md`](./docs/architecture/stack.md).

---

## Quickstart local

**Sin Docker obligatorio.** Detalles completos en [`docs/runbooks/railway/SETUP.md`](./docs/runbooks/railway/SETUP.md).

### Ruta A — Dev local nativo

```bash
# Prerequisitos:
#   - Node 20 LTS + pnpm (corepack enable)
#   - Python 3.12
#   - PostgreSQL 16 (local o Railway dev DB)
#   - Redis (local, Memurai en Windows o WSL)

git clone git@github.com:xguilxr/pmo_aas.git && cd pmo_aas
cp .env.example .env   # rellena DATABASE_URL, REDIS_URL, JWT_SECRET, S3_*, etc.

# Backend
cd apps/api
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8080

# Frontend (otra consola)
cd apps/web
pnpm install
pnpm dev                          # http://localhost:3000

# Worker (otra consola, opcional para AI/notifs/reports)
cd apps/api
celery -A app.workers.celery_app worker -l info
```

### Ruta B — Railway end-to-end

Crea un proyecto en Railway con plugins **Postgres** + **Redis**, conecta el repo y deja que autodeploy despliegue `apps/api` y `apps/web` por separado. Configura las env vars S3_* apuntando al bucket R2. Guía paso a paso en [`docs/runbooks/railway/DEPLOYMENT.md`](./docs/runbooks/railway/DEPLOYMENT.md).

---

## Estructura del repo

```
pmo_aas/
├── apps/
│   ├── web/                      # Next.js 15 (frontend)
│   │   ├── app/(app)/            # Rutas autenticadas (admin/, pmo/, superadmin/)
│   │   ├── components/           # Componentes (incl. hard-delete-button US-088)
│   │   └── lib/api/              # Cliente tipado del API
│   └── api/                      # FastAPI (backend)
│       ├── app/api/v1/           # Endpoints REST + deps + middleware
│       ├── app/core/             # config, errors, permissions, hard_delete, security
│       ├── app/models/           # SQLAlchemy 2.0 (organization, project, user, modules…)
│       ├── app/services/         # audit, document_storage (R2), folio, notifications, email
│       ├── app/workers/          # Celery tasks (notifications, reports, AI)
│       ├── alembic/versions/     # Migrations (0001 → 0035 stakeholders catalog)
│       └── tests/                # Pytest async (EP001-EP010 + US-### + BUG-### + ENH-###)
├── docs/                         # Documentación (epics, ADRs, runbooks, sprint, testing)
├── CLAUDE.md                     # Reglas de trabajo de Claude Code en este repo
└── .github/workflows/            # CI: lint, typecheck, tests, alembic-gate
```

---

## Convenciones

- **Branches:** `claude/<tema>-<sufijo>` para sesiones de Claude Code; `main` es productivo.
- **Commits:** `<tipo>(<scope>): <ID> — <desc> (refs #N)` — ver [`CLAUDE.md` §4](./CLAUDE.md).
- **Una US/BUG/ENH = un commit.** Mover de IN-PROGRESS → DONE en `SPRINT.md` al pushear.
- **IDs de trazabilidad:** `US-XXX` (story), `BUG-XXX` (bug), `ENH-XXX` (enhancement), `EP0XX` (epic), `ADR-XXX`, `DEC-XXX`, `TC-XXX`. Próximos libres en [`CLAUDE.md` §2](./CLAUDE.md).
- **Idiomas:** Español (default UI) + Inglés en código y docs técnicas.
- **Moneda:** MXN con formato `$1,234.56`. Presupuestos opcionales (ENH-040).
- **Folios:** `SOL-YYYY-NNN` (solicitudes), `PRJ-YYYY-NNN` (proyectos), `RIS-…`, `INC-…`, `CHG-…`, `DOC-…`, `LEC-…`, `MIN-…`.

---

## Estado actual (Sprint 33 v1.28)

- **Producción:** desplegada en Railway. API + Web + Worker + Postgres + Redis. Storage en Cloudflare R2.
- **Última migración:** `0084_assistant_conversations` (US-165) — head único de Alembic.
- **Última feature entregada:** Dashboards N1/N2 + reportes derivados + revamp "big canvas" (Sprint 33). En curso: deepwork de reportes con logos/charts on-brand, confiabilidad minutas→RAID y asistente IA conversacional.
- **Cobertura de tests:** EP001-EP010 + US-### dedicados + BUG-### regresión. CI gate corre pytest + alembic upgrade head contra Postgres efímero.

---

## Licencia

Propietaria. Uso interno xguilxr / PMO-aaS.
