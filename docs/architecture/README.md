# Arquitectura PMO-aaS

**ID:** `DOC-ARCH`

Índice de la documentación arquitectónica. Cada archivo puede leerse independientemente.

| # | Archivo | Contenido |
|---|---|---|
| 1 | [`stack.md`](./stack.md) | Decisiones de stack por capa, con justificación |
| 2 | [`database.md`](./database.md) | Modelo ER, tablas, índices, migraciones, RLS |
| 3 | [`security-multitenant.md`](./security-multitenant.md) | JWT, tenancy, RBAC, superadmin |
| 4 | [`deployment-railway.md`](./deployment-railway.md) | Infra Railway, variables, CI/CD, dominios |
| 5 | [`api-conventions.md`](./api-conventions.md) | REST, errores, paginación, versionado |
| 6 | [`navigation.md`](./navigation.md) | Árbol de navegación web, páginas, flujos, huérfanas |
| 7 | Este archivo | C4 diagrams (contexto + contenedores) |

---

## C4 Nivel 1 — Contexto

```mermaid
flowchart TB
    PM["Project Manager<br/>(navegador)"]
    ADMIN["Administrador<br/>(navegador)"]
    SUPER["Super Admin<br/>(navegador)"]
    STAKE["Stakeholder<br/>(correo)"]

    PMO["PMO-aaS<br/>Plataforma SaaS multi-tenant"]

    OLLAMA["Ollama Server<br/>(IA local)"]
    CLAUDE["Anthropic Claude<br/>(IA fallback)"]
    SMTP["SMTP / Resend<br/>(correos)"]
    MSP["Archivos MS Project<br/>(.mpp/.xml/.xlsx)"]

    PM --> PMO
    ADMIN --> PMO
    SUPER --> PMO
    PMO --> STAKE
    GROQ["Groq API<br/>(IA modo platform)"]

    PMO -->|modo platform| GROQ
    PMO -.->|modo byo| OLLAMA
    PMO -.->|modo byo (premium)| CLAUDE
    PMO --> SMTP
    MSP --> PMO
```

## C4 Nivel 2 — Contenedores

```mermaid
flowchart TB
    subgraph Browser
        WEB["Next.js 15 App<br/>(RSC + Client)"]
    end

    subgraph Railway
        API["FastAPI API<br/>(Python 3.12)"]
        WORKER["Celery Worker<br/>(Python 3.12)"]
        DB[("PostgreSQL 16<br/>+ RLS")]
        REDIS[("Redis 7<br/>sesiones + colas")]
        STORAGE["Railway Volume<br/>(uploads/tenants)"]
    end

    subgraph AI
        GROQ["Groq API<br/>(platform default)"]
        OLLAMA["Ollama<br/>(byo, Qwen 2.5)"]
        CLAUDE["Claude / Gemini<br/>(byo)"]
    end

    WEB -->|HTTPS JWT| API
    API --> DB
    API --> REDIS
    API --> STORAGE
    API -->|enqueue| REDIS
    WORKER -->|dequeue| REDIS
    WORKER --> DB
    WORKER -->|platform| GROQ
    WORKER -.->|byo| OLLAMA
    WORKER -.->|byo| CLAUDE
    WORKER -->|SMTP| SMTP["Resend / SES"]
```

## C4 Nivel 3 — Componentes del API (vista rápida)

```mermaid
flowchart LR
    ROUTER["/api/v1 router"]
    AUTH["auth/<br/>(JWT, refresh)"]
    TENANT["middleware<br/>tenant_ctx"]
    PROJ["projects/"]
    MOD["modules/<br/>(risks,issues,changes,docs,lessons,minutes)"]
    AI["ai/<br/>(minutes,reports,config)"]
    MSP["msproject/<br/>(import,gantt)"]
    SUPER["superadmin/"]

    ROUTER --> AUTH
    ROUTER --> TENANT
    TENANT --> PROJ
    TENANT --> MOD
    TENANT --> AI
    TENANT --> MSP
    ROUTER --> SUPER
```

## Flujo de una petición típica

```mermaid
sequenceDiagram
    participant U as Browser
    participant W as Next.js (RSC)
    participant A as FastAPI
    participant D as Postgres

    U->>W: GET /projects
    W->>A: GET /api/v1/projects (JWT + X-Tenant-ID)
    A->>A: verify_jwt() → user, tenant_id
    A->>A: set_tenant_ctx() → RLS habilitado
    A->>D: SELECT ... WHERE tenant_id = current_setting('app.tenant_id')
    D-->>A: rows
    A-->>W: JSON paginado
    W-->>U: HTML streameado (Suspense + Skeleton)
```

## Flujo de generación de minuta con IA

```mermaid
sequenceDiagram
    participant PM as Project Manager
    participant W as Next.js
    participant A as FastAPI
    participant Q as Redis Queue
    participant WK as Worker
    participant P as IA Provider<br/>(Groq / Ollama / …)

    PM->>W: sube transcripción .txt
    W->>A: POST /ai/minutes (file + project_id)
    A->>A: persiste transcripción + crea job
    A->>Q: enqueue("generate_minute", job_id)
    A-->>W: 202 Accepted + job_id
    W-->>PM: "Generando… (~60s)"
    WK->>Q: dequeue
    WK->>WK: chunk(text, 3000 tokens)
    WK->>P: completions (prompt)
    P-->>WK: JSON estructurado
    WK->>A: PUT /ai/minutes/{id}/result
    A-->>W: webhook / polling
    W-->>PM: render minuta editable
```

## Estructura del frontend (Next.js App Router)

```mermaid
flowchart TB
    ROOT["app/<br/>(root layout)"]
    PUB["Públicas<br/>/login, /forgot-password, /reset,<br/>/change-password, /approve/[token]"]
    APP["(app)/<br/>layout autenticado<br/>+ AppShell (sidebar + topbar)"]

    DASH["/dashboard<br/>/account<br/>/notifications"]
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

> El detalle de cada subárbol, sus páginas, flujos y huérfanas vive en
> [`navigation.md`](./navigation.md).

---

## Decisiones transversales

- **Monorepo** con `pnpm workspaces` + Turborepo para caching de build.
- **Idempotencia** en endpoints de escritura sensibles (`Idempotency-Key` header).
- **Rate limiting** por tenant con `slowapi` (100 req/min por IP, 1000/min por tenant).
- **Migraciones** con Alembic; nunca se destruye data en migraciones (soft drops).
- **Backups** diarios automáticos por Railway + snapshot semanal a S3 compatible.
- **Feature flags** vía tabla `feature_flags` (por tenant). No usamos servicio externo.
