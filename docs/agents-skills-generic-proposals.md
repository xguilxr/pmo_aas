# Propuestas genéricas para `claudio-enterprises`

**ID:** `DOC-AGENTS-GENERIC`

Estas son propuestas de **agentes y skills reutilizables** para tu plugin
personal (`claudio-enterprises`), **no específicas de PMO-aaS**. Aplican a
cualquier proyecto SaaS moderno (Next.js + FastAPI/Node + Postgres + IA).

Para las específicas de PMO-aaS ver [`agents-skills-proposals.md`](./agents-skills-proposals.md).

---

## 1. Agentes genéricos

### `tenant-isolation-auditor` (generalización)

**Resuelve:** el problema universal de SaaS multi-tenant: olvidar filtro
`tenant_id` en algún endpoint, query o job.

**Trigger:** PR que toca rutas, ORM queries, workers, filesystem, cache keys.

**Descripción:**
```
Configurable por proyecto vía .claude/config/tenant-isolation.yaml:
  scope_field: tenant_id | org_id | workspace_id
  tenant_dep: get_current_tenant | require_workspace
  tables: lista de modelos tenant-scoped
  fs_prefix_pattern: "{tenant_slug}/"
  cache_prefix_pattern: "{tenant_id}:"
  exceptions: rutas explícitamente globales

Escanea diff y reporta file:line por cada violación detectada.
```

**Input:** Read, Grep, Bash.

---

### `schema-consistency-guardian` (generalización)

**Resuelve:** drift entre ORM, schemas, API contracts y clientes TS/Py.

**Config:**
```yaml
layers:
  db: sqlalchemy | prisma | drizzle | typeorm
  api: pydantic | zod | tsoa
  client: openapi-ts | orval | autogen
  migrations: alembic | prisma-migrate | drizzle-kit
```

Automatiza la validación: si uno cambia, los demás siguen. Sugiere parche o
lo aplica con `--fix`.

---

### `security-auditor-pro`

**Resuelve:** review automático de seguridad más profundo que linters.

**Cubre:**
- OWASP top 10 (SQLi, XSS, CSRF, SSRF, IDOR, etc.).
- Secrets en commits (extiende `truffleHog`).
- Configuraciones de headers (CSP, HSTS, X-Frame).
- Auth middleware presente en rutas nuevas.
- Rate limiting en endpoints costosos.
- Validación de uploads (MIME, magic bytes, tamaño).
- Cryptography: algoritmos débiles (MD5, SHA1, DES).
- CORS permisivo (`*`).

**Output:** markdown con hallazgos, severidad y fix sugerido.

---

### `migration-safety-guardian`

**Resuelve:** migraciones SQL que causan downtime o pérdida de datos.

**Reglas:**
```
- NUNCA DROP COLUMN en un solo PR (requiere 2 fases).
- ALTER que añade NOT NULL requiere DEFAULT + backfill previo.
- Agregar índices debe ser CONCURRENTLY si la tabla >100k rows.
- ALTER TYPE requiere ventana de mantenimiento explícita.
- Tests de upgrade() y downgrade() sobre Postgres real.
- DROP TABLE requiere 2 releases + export.
```

Bloquea el PR si detecta operación peligrosa sin escape explícito en comment.

---

### `design-system-enforcer` (generalización)

**Resuelve:** drift entre design tokens y código.

**Config:**
```yaml
token_source: tailwind.config.ts | design-tokens.json | css-variables
allow_arbitrary_values: false
icon_library: lucide | heroicons | phosphor  # solo uno
motion: framer-motion | react-spring  # solo uno
color_source: oklch | hsl | hex   # reglas sobre qué vale
```

Detecta colores hardcoded, spacing arbitrary (`p-[13px]`), mezcla de icon
libs, animaciones sin respeto a `prefers-reduced-motion`.

---

### `api-contract-diff`

**Resuelve:** consumidores externos se rompen cuando cambia el API.

**Trigger:** `/api-diff <base-sha>` o automático en PR.

**Output:**
```
### Breaking changes 🔴
- DELETE /api/v1/users/{id} removed
- Field `User.email` changed type String → Email (stricter)

### Non-breaking ✨
- Added POST /api/v1/users/bulk
- Field `User.phone` added (optional)

### Renamed 🔄
- /reports → /analytics/reports (deprecated alias active)
```

Genera comentario estructurado en el PR + bump semver sugerido.

---

### `observability-auditor`

**Resuelve:** código nuevo sin logs, traces o métricas.

**Verifica:**
- Handlers HTTP con `trace_id` en logs.
- Errores capturados por Sentry/GlitchTip.
- Métricas (`counter`, `histogram`) en endpoints críticos.
- Tags `tenant_id`, `user_id` propagados.
- No hay `print` / `console.log` en código productivo.

---

### `ai-prompt-evaluator` (generalización de `pmo-prompt-evaluator`)

**Resuelve:** regresiones silenciosas al cambiar prompts de IA.

**Config:**
```yaml
golden_dataset: tests/ai/golden/
providers: [ollama, gemini, claude, openai]
metrics:
  - semantic_similarity
  - schema_valid
  - required_fields_present
  - latency_p95
regression_threshold: 0.05  # 5% drop triggers block
```

Corre dataset contra el prompt nuevo, compara con baseline, reporta
regresión/mejora por provider.

---

### `monorepo-orchestrator`

**Resuelve:** builds, tests y lint paralelos con caching incremental.

**Integra con:** Turborepo, Nx, Moon, Bazel.

**Usos:**
- Detectar qué cambió y solo correr tests afectados (filtro del agente).
- Alertar si un package cambió su API pero downstream no lo consumió.
- Validar que `pnpm install` no introduce dependencias duplicadas.

---

## 2. Skills genéricas

### `seed-demo` (generalización)

**Propósito:** poblar una BD con datos realistas para demos.

**Config:**
```yaml
seeds:
  - name: tenants
    count: 2
    factory: factories/tenant.py
  - name: users
    count: 10
    relation: tenants
    factory: factories/user.py
# etc.
```

Idempotente por default. CLI:
```bash
/seed-demo --config=seeds.yaml --env=dev
```

---

### `module-scaffold`

**Propósito:** scaffolding de un módulo siguiendo convenciones del repo.

**Detecta patrón existente** en 2-3 módulos del repo, genera nuevo aplicando
el mismo estilo:
- Modelo + migration.
- Schemas (Create/Update/Out).
- Router / controller.
- Component / view UI.
- Tests stubs.
- Entry en docs/glossary.

---

### `release-notes-generator`

**Propósito:** changelog desde PRs merged entre tags.

**Features:**
- Clasifica por Conventional Commits (`feat`, `fix`, `chore`, etc.).
- Agrupa por épica/label si se usa.
- Detecta breaking changes por keyword o label.
- Genera Markdown + draft release en GitHub.
- Soporta múltiples idiomas.

---

### `secret-rotator`

**Propósito:** rotar secrets sin downtime.

**Flujo:**
```
1. Genera nuevo secret.
2. Detecta servicios consumidores (Railway, env vars, Vault).
3. Inyecta nuevo como secundario (dual-accept).
4. Redeploy.
5. Valida todo funciona con nuevo.
6. Retira viejo.
7. Audita.
```

Aplica a JWT, DB passwords, API keys de terceros, NEXTAUTH_SECRET, etc.

---

### `env-sync`

**Propósito:** mantener sincronía entre `.env.example` y variables reales.

**Detecta:**
- Variables en código sin documentar en `.env.example`.
- Variables en `.env.example` sin uso real.
- Diferencias entre entornos (dev, staging, prod).

**Output:** diff + `--fix` aplica.

---

### `db-explorer-readonly`

**Propósito:** consultas rápidas a la BD en lenguaje natural, solo lectura.

Requiere un **ReadOnlyDB MCP** (o rol `readonly` en la conexión). Ejemplos:

```
/db-explorer "usuarios que no se loguean hace >30 días"
/db-explorer "top 10 proyectos por presupuesto"
/db-explorer "tenant con más storage"
```

Traduce a SQL, ejecuta, formatea tabla. **Nunca escribe.**

---

### `cost-estimator`

**Propósito:** estimar costo mensual de cloud + IA.

**Config:**
```yaml
providers:
  - railway
  - aws
  - gcp
  - cloudflare
ai:
  - openai
  - anthropic
  - gemini
  - ollama  # solo infra
```

Outputs un markdown con breakdown y recomendaciones de optimización
(downgrade tier, usar free tier, prompt caching, etc.).

---

### `sentry-glitchtip-migrate`

**Propósito:** migrar entre servicios compatibles con el protocolo Sentry.

**Pasos automáticos:**
1. Identifica SDK en uso (Python, TS, React, Next).
2. Cambia solo la DSN (código intacto).
3. Migra sourcemaps si aplica.
4. Verifica que errores llegan al nuevo backend.

---

### `railway-deploy-helper`

**Propósito:** operaciones comunes de Railway CLI con validación.

```
/railway deploy <service>
/railway rollback <service>
/railway logs <service> --tail
/railway migrate  (alembic + verificaciones)
/railway preview-env create <pr_number>
```

---

### `openapi-client-sync`

**Propósito:** regenerar clientes TS/Py desde OpenAPI spec y mantenerlos
en sync con el backend.

**Detecta:** spec cambió → clientes des-actualizados → regenera → commit.

---

## 3. Estructura sugerida del plugin

```
claudio-enterprises/
├── agents/
│   ├── tenant-isolation-auditor.md
│   ├── schema-consistency-guardian.md
│   ├── security-auditor-pro.md
│   ├── migration-safety-guardian.md
│   ├── design-system-enforcer.md
│   ├── api-contract-diff.md
│   ├── observability-auditor.md
│   ├── ai-prompt-evaluator.md
│   └── monorepo-orchestrator.md
├── skills/
│   ├── seed-demo.md
│   ├── module-scaffold.md
│   ├── release-notes-generator.md
│   ├── secret-rotator.md
│   ├── env-sync.md
│   ├── db-explorer-readonly.md
│   ├── cost-estimator.md
│   ├── sentry-glitchtip-migrate.md
│   ├── railway-deploy-helper.md
│   └── openapi-client-sync.md
├── shared/
│   ├── prompts/          # reutilizables cross-agente
│   ├── configs/          # templates de config
│   └── fixtures/         # ejemplos
├── README.md             # cómo instalar el plugin
└── plugin.json           # manifest (agentes, skills, versión)
```

Config por proyecto en cada repo consumidor:
```
.claude/
├── config/
│   ├── tenant-isolation.yaml
│   ├── schema-consistency.yaml
│   └── design-tokens.yaml
└── agents/   # solo overrides específicos del repo
```

---

## 4. Priorización para `claudio-enterprises`

| P | Propuesta | Valor transversal |
|---|---|---|
| P0 | `tenant-isolation-auditor` | Aplica a cualquier SaaS multi-tenant |
| P0 | `security-auditor-pro` | Pre-release obligatorio |
| P0 | `seed-demo` | Todos los proyectos necesitan datos demo |
| P1 | `schema-consistency-guardian` | Dolor frecuente en stacks typed |
| P1 | `migration-safety-guardian` | Evita accidentes en prod |
| P1 | `env-sync` | Dolor recurrente |
| P2 | `api-contract-diff` | Cuando hay consumidores externos |
| P2 | `ai-prompt-evaluator` | Cuando usas IA en productivo |
| P2 | `design-system-enforcer` | Con design system maduro |
| P3 | `cost-estimator` | Conciencia de costos |
| P3 | `secret-rotator` | Best practice |
| P3 | `monorepo-orchestrator` | Con monorepo maduro |

---

## 5. Ciclo de promoción

Flujo para promover un agente específico a genérico:

1. Un agente nace **en un repo** (e.g. `pmo-tenant-isolation-auditor`).
2. Cuando lo uses en un 2.º repo, identifica qué es config vs lógica.
3. Generaliza con YAML de config y commit a `claudio-enterprises`.
4. Deprecar el específico (shim que llama al genérico con su config).
5. Actualizar `CHANGELOG.md` del plugin.

Este ciclo evita código duplicado y crea tu asset personal de productividad.
