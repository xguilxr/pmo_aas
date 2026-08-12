---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 180d
---

# Arquitectura PMO-aaS

**ID:** `DOC-ARCH`
**Última verificación contra código:** 2026-05-23.

Índice de la documentación arquitectónica. Cada archivo puede leerse independientemente.

| # | Archivo | Contenido |
|---|---|---|
| 1 | [`stack.md`](./stack.md) | Decisiones de stack reales por capa |
| 2 | [`database.md`](./database.md) | 49 tablas, índices, migraciones; **sin RLS hoy** |
| 3 | [`security-multitenant.md`](./security-multitenant.md) | JWT, tenancy app-level, capability-based RBAC |
| 4 | [`deployment-railway.md`](./deployment-railway.md) | 4 servicios Railway, variables, CI/CD |
| 5 | [`api-conventions.md`](./api-conventions.md) | REST, paginación real, catálogo de errores |
| 6 | [`navigation.md`](./navigation.md) | Árbol de páginas, flujos y huérfanas |
| 7 | [`modelo-amenazas.md`](./modelo-amenazas.md) | Fronteras de confianza y catorce amenazas (MCS SEG-06) |
| 8 | Este archivo | Vista C4 (contexto + contenedores + componentes) |

---

## C4 Nivel 1 — Contexto

```mermaid
flowchart TB
    PM["Project Manager<br/>(navegador)"]
    ADMIN["Administrador del tenant<br/>(navegador)"]
    SUPER["Super Admin<br/>(navegador)"]
    STAKE["Stakeholder externo<br/>(email + /approve/[token])"]

    PMO["PMO-aaS<br/>Plataforma SaaS multi-tenant"]

    GROQ["Groq API<br/>(IA modo platform — default)"]
    BYO["Provider BYO opcional<br/>(OpenAI / Anthropic / Gemini /<br/>Perplexity / Azure Copilot M365)"]
    RESEND["Resend<br/>(emails transaccionales)"]
    R2["Cloudflare R2<br/>(opcional: uploads)"]
    MSP["Archivos MS Project<br/>(.mpp / .xml / .xlsx / .csv)"]

    PM --> PMO
    ADMIN --> PMO
    SUPER --> PMO
    PMO --> STAKE
    PMO -->|tenant en modo platform| GROQ
    PMO -.->|tenant en modo byo| BYO
    PMO --> RESEND
    PMO -.->|STORAGE_BACKEND=s3| R2
    MSP --> PMO
```

> **Ollama fue eliminado** (BUG-053). Ignóralo en docs viejos.

---

## C4 Nivel 2 — Contenedores

```mermaid
flowchart TB
    subgraph Browser
        WEB["Next.js 15 App<br/>(App Router + RSC)"]
    end

    subgraph Railway
        API["FastAPI API<br/>(Python 3.12, Dockerfile)"]
        WORKER["Celery Worker + Beat<br/>(Python 3.12, mismo Dockerfile)"]
        DB[("PostgreSQL 16<br/>aislamiento por tenant_id<br/>en capa app, no RLS")]
        REDIS[("Redis 7<br/>colas Celery + rate limit auth")]
        VOL["Railway Volume<br/>(STORAGE_BACKEND=local)"]
    end

    subgraph "Externos"
        GROQ["Groq API<br/>(platform)"]
        BYO["Provider BYO<br/>(byo)"]
        RESEND["Resend"]
        R2[("Cloudflare R2<br/>(STORAGE_BACKEND=s3)")]
    end

    WEB -->|HTTPS JWT| API
    API --> DB
    API --> REDIS
    API --> VOL
    API -.-> R2
    API -->|enqueue| REDIS
    WORKER -->|dequeue| REDIS
    WORKER --> DB
    WORKER --> VOL
    WORKER -.-> R2
    WORKER -->|platform| GROQ
    WORKER -.->|byo| BYO
    WORKER --> RESEND
```

---

## C4 Nivel 3 — Componentes del API

37 routers en `apps/api/app/api/v1/endpoints/`. Vista por dominio:

```mermaid
flowchart LR
    ROUTER["/api/v1 router<br/>(app/api/v1/router.py)"]

    subgraph Auth_Tenancy
        AUTH["auth.py"]
        ME["users / me / permissions"]
    end

    subgraph Catalog
        ORG["organizations.py"]
        AREAS["areas.py"]
        DIR["project_directory.py"]
        DASH["dashboard.py"]
    end

    subgraph Projects
        REQ["project_requests.py"]
        PROJ["projects.py"]
        CHART["project_charters.py"]
        ARTS["project_artifacts.py"]
        MODS["modules.py<br/>(risks/issues/changes/docs/lessons/minutes)"]
        RISKACT["risk_actions.py"]
        CHGAPP["change_approvals.py"]
        TASKS["tasks.py + gantt_snapshot.py"]
    end

    subgraph AI_Reports
        AI["ai.py<br/>(jobs minutes/reports)"]
        SCHED_R["scheduled_reports.py"]
        SCHED_M["scheduled_minutes.py"]
        RPT["reports.py"]
        RPTSEC["report_sections.py"]
        RPTTPL["report_templates.py"]
        RPTBLD["report_builder_*.py"]
    end

    subgraph Admin_Tenant
        ADM_AI["admin_ai.py"]
        ADM_PNL["admin_panel.py"]
        ADM_USR["admin_users.py"]
        BRAND["branding.py"]
        NOTIF["notifications.py"]
        PERM["permission_requests.py"]
        ENTHIST["entity_history.py"]
    end

    subgraph SuperAdmin
        SA["superadmin.py"]
        SA_AI["superadmin_ai.py"]
        SA_PNL["superadmin_panel.py"]
    end

    ROUTER --> Auth_Tenancy
    ROUTER --> Catalog
    ROUTER --> Projects
    ROUTER --> AI_Reports
    ROUTER --> Admin_Tenant
    ROUTER --> SuperAdmin
```

> El gating es **por dependencia FastAPI**, no por middleware. Cada endpoint declara `Depends(require_authenticated())`, `Depends(require_capability("…"))` o `Depends(get_superadmin_user)`.

---

## Flujo de una petición típica

```mermaid
sequenceDiagram
    participant U as Browser
    participant W as Next.js (RSC / client)
    participant A as FastAPI
    participant D as Postgres

    U->>W: navega /pmo/projects
    W->>A: GET /api/v1/projects (Authorization: Bearer)
    A->>A: decode JWT → user + effective_tenant_id
    A->>A: require_authenticated() / require_capability(...)
    A->>D: SELECT ... WHERE tenant_id = :tid AND deleted_at IS NULL
    D-->>A: rows
    A-->>W: JSON (array bare, sin envelope)
    W-->>U: HTML / hidratación
```

> No usamos `SET LOCAL app.tenant_id` ni RLS. El filtro `tenant_id` lo aplica explícitamente cada query.

---

## Flujo de generación de minuta con IA

```mermaid
sequenceDiagram
    participant PM as Project Manager
    participant W as Next.js
    participant A as FastAPI /ai/minutes
    participant Q as Redis (Celery broker)
    participant WK as Celery Worker
    participant P as Provider IA<br/>(Groq | OpenAI | Claude | Gemini | …)
    participant D as Postgres

    PM->>W: sube transcripción
    W->>A: POST /api/v1/ai/minutes (multipart)
    A->>D: INSERT ai_jobs (status=queued, kind=minute_from_transcript)
    A->>Q: enqueue ai.generate_minute(job_id)
    A-->>W: 202 Accepted + Location /ai/jobs/{id}
    W-->>PM: spinner

    WK->>Q: dequeue
    WK->>D: SELECT ai_job + tenant ai_mode (platform / byo)
    WK->>P: completions (cascada según mode)
    P-->>WK: JSON
    WK->>D: UPDATE ai_jobs (status=succeeded, output, tokens_in/out, duration_ms)
    opt save_as_minute=true
        WK->>D: INSERT meeting_minutes
    end

    loop polling cada N seg
        W->>A: GET /api/v1/ai/jobs/{id}
        A-->>W: { status, output? }
    end
    W-->>PM: render minuta editable
```

---

## Estructura del frontend (Next.js App Router)

```mermaid
flowchart TB
    ROOT["app/<br/>(root layout)"]
    PUB["Públicas<br/>/login, /forgot-password, /reset,<br/>/change-password, /approve/[token]"]
    APP["(app)/<br/>layout autenticado<br/>+ AppShell (sidebar + topbar)"]

    DASH["/dashboard · /account · /notifications"]
    PMO["/pmo/**<br/>portal de proyectos"]
    ADMIN["/admin/**<br/>admin del tenant"]
    SUPER["/superadmin/**<br/>admin de plataforma"]

    ROOT --> PUB
    ROOT --> APP
    APP --> DASH
    APP --> PMO
    APP --> ADMIN
    APP --> SUPER
```

> El detalle de cada subárbol, sus páginas, flujos y huérfanas vive en [`navigation.md`](./navigation.md).

---

## Decisiones transversales (estado real)

- **Monorepo** con `pnpm workspaces`. **Sin Turborepo** — los scripts corren `pnpm -r` directo.
- **Migraciones Alembic**. Patrón en 2 pasos para `DROP COLUMN` (deprecar uso → drop en migración siguiente). Validadas en CI por `api-migrations-postgres` (upgrade → downgrade → upgrade).
- **Multitenancy app-level** (no RLS). Cada endpoint filtra `tenant_id` explícito. Tests `TC-MT-*` validan aislamiento. Migrar a RLS está como deuda.
- **Backups**: Railway daily de Postgres. Snapshot externo (R2/B2) pendiente formalizar.
- **Rate limit**: solo `/auth/forgot-password` y `/auth/reset` (counter en Redis). El rate limit global por tenant/IP no está implementado.
- **Idempotency-Key**: no implementado (los POST repetidos pueden duplicar). Diferido.
- **Feature flags**: no hay tabla `feature_flags`. Si se introduce, agregar a `database.md` y aquí.

---

## Cosas que NO existen (a pesar de versiones viejas del doc)

| Decía la doc vieja | Realidad |
|---|---|
| RLS en Postgres con `app.tenant_id` | No. Filtrado en app. |
| Roles Postgres `app_user` / `app_admin` con `BYPASSRLS` | No. Un solo rol. |
| Ollama como provider de IA | Eliminado en BUG-053. |
| Servicio Railway `glitchtip` + `sentry-sdk` | No instalado. |
| Header `X-Tenant-ID` | No. Tenant viene del JWT. |
| Header `Idempotency-Key` enforced | No implementado. |
| `slowapi` global por IP/tenant | Solo en endpoints de reset/forgot. |
| NextAuth | No. Auth propia con JWT + cookie. |
| Turborepo | No instalado. |
| Husky / Storybook / Renovate / MkDocs | No instalados. |
| Feature flags table | No existe. |
