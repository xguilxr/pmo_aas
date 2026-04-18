# Architecture Decision Records (ADR)

**ID:** `DOC-ADR`

Decisiones arquitectónicas registradas con formato ligero. Una decisión = una sección.

Formato: `ADR-XXX — Título` → **Contexto**, **Decisión**, **Consecuencias**, **Alternativas**, **Estado**, **Fecha**.

---

## ADR-001 — Railway como plataforma de despliegue

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Tras evaluar AWS ECS, Fly.io, Render, Heroku y Railway, necesitamos una plataforma que: (1) minimice fricción de deploy, (2) soporte monorepo multi-servicio, (3) provea Postgres + Redis administrados, (4) sea económica en MVP, (5) permita crecer sin vendor lock duro.

**Decisión:**
Usar **Railway** como PaaS principal. Frontend, API, Worker y plugins (Postgres, Redis) viven en un solo `project` de Railway.

**Consecuencias positivas:**
- Zero-config deploy con Nixpacks.
- Variables y secretos centralizados, con referencias entre servicios.
- CLI y UI excelentes.
- Integración GitHub auto (push → deploy).
- Plugins de Postgres/Redis con backups automáticos.

**Consecuencias negativas:**
- Dependencia de Railway para runtime. Mitigación: todo el código es estándar (Docker/Nixpacks funciona en otros PaaS si migramos).
- Coste escala con réplicas; en volúmenes altos (>1000 tenants) puede convenir migrar a AWS/GCP.
- Sin GPU nativa aún (para Ollama hosteamos externo o esperamos rollout).

**Alternativas evaluadas:**
- AWS ECS: muy potente pero complejidad alta y coste fijo de load balancer/VPC.
- Fly.io: similar a Railway, pero ecosistema de plugins más limitado.
- Render: UI menos pulida, pricing similar.
- Vercel (solo frontend): obligaría a hostear API en otro lado → split infra.

---

## ADR-002 — Next.js 15 (App Router) + RSC para el frontend

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Frontend debe ser rápido (TTFB, hydration), accesible, mantenible y tener buena DX. Opciones: Next.js, Remix, SvelteKit, Nuxt, SPA con Vite.

**Decisión:**
**Next.js 15** con App Router y React Server Components. TypeScript 5 estricto.

**Consecuencias positivas:**
- RSC reduce JS al cliente (KPIs, listados) → carga rápida.
- Streaming con `<Suspense>` mejora percepción.
- Server Actions para mutations simples.
- Ecosistema grande (shadcn/ui, next-intl, next-auth).
- TypeScript nativo + type-safe routes (post v13).

**Consecuencias negativas:**
- Learning curve App Router para devs nuevos.
- RSC + client component split requiere cuidado.
- Bundler (Turbopack) aún maduro.

**Alternativas:**
- Remix: similar filosofía, menor ecosistema shadcn, menos adoption.
- SvelteKit: DX excelente pero menos libs ready (Gantt, Rich editor).
- SPA Vite: pierde SSR/streaming, peor SEO (aunque SEO no aplica a app privada).

---

## ADR-003 — PostgreSQL con RLS para multi-tenancy

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Multi-tenant tiene 3 patrones: DB-per-tenant, schema-per-tenant, shared-schema con RLS. Cada uno con trade-offs distintos.

**Decisión:**
**Shared database + shared schema + Row-Level Security** en Postgres.

**Consecuencias positivas:**
- Una sola BD a administrar (migraciones únicas).
- Cross-tenant analytics posibles si se necesita (desde superadmin).
- Coste fijo bajo independiente del número de tenants.
- RLS a nivel DB es defensa profunda real (no solo WHERE en app).

**Consecuencias negativas:**
- Riesgo de fuga si RLS se desactiva por error → mitigado por TC-MT-*.
- Queries hot-path con muchos tenants requieren índices compuestos (`(tenant_id, …)`).
- Performance en tablas globales gigantes → mitigación por particionado futuro.

**Alternativas:**
- DB-per-tenant: coste lineal con tenants, onboarding lento.
- Schema-per-tenant: migrations N veces más trabajo.

---

## ADR-004 — Python/FastAPI para el backend

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Alternativas: FastAPI (Python), NestJS (Node), Rails, Django, Elixir/Phoenix, Go.

**Decisión:**
**FastAPI + Python 3.12** con Pydantic v2 y SQLAlchemy 2.0.

**Consecuencias positivas:**
- Tipado fuerte con Pydantic (compartido con frontend vía OpenAPI).
- Ecosistema IA (Ollama, Whisper, ML libs) nativo.
- MPXJ integra via subprocess, pero alternativa nativa si llegara.
- DX excelente (autocompletion, docs auto).

**Consecuencias negativas:**
- GIL — mitigación: workers `uvicorn` múltiples + async.
- Performance puro inferior a Go/Rust, pero suficiente para MVP (p95 <300ms).

**Alternativas:**
- NestJS: todo TypeScript, pero workaround para IA (subprocess Python).
- Rails: mature pero lejos de Apple-style modern dev.
- Go: rapidísimo, pero menos libs IA y MPXJ más lento de integrar.

---

## ADR-005 — Diseño "estilo Apple" como norte visual

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Queremos que se sienta limpio, premium, con personalidad. Diferenciación clara de Jira/Asana que se ven pesados.

**Decisión:**
Sistema de diseño inspirado en **Human Interface Guidelines** de Apple (macOS Sonoma/Sequoia, iPadOS). Tipografía clara, color solo para significado, materiales (blur), movimiento con propósito.

**Consecuencias:**
- Componentes shadcn/ui como base, retematizados con nuestros tokens.
- Tailwind v4 con variables oklch para color preciso.
- Animaciones Framer Motion sutiles.
- `Cmd+K` command palette obligatorio.

**Alternativas:**
- Material Design: demasiado Google, no encaja con PMO.
- Ant Design: denso, buen admin UI pero feo.
- Custom desde cero: esfuerzo excesivo.

---

## ADR-006 — Celery para colas (Python-only)

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Necesitamos workers para IA (minutas/reportes), import MS Project, envío masivo de emails. Opciones: Celery, RQ, Dramatiq, BullMQ (Node), Temporal.

**Decisión:**
**Celery 5** con broker Redis. Evita introducir Node solo para colas.

**Consecuencias positivas:**
- Stack Python único.
- Celery tiene beat para crons (reportes programados).
- Compatible con testcontainers.

**Consecuencias negativas:**
- Celery config es notorio. Mitigación: config centralizada en `app/worker/config.py`.
- Retries y dead-letter queue requieren setup explícito.

**Alternativas:**
- RQ: más simple pero sin beat.
- BullMQ: requeriría Node worker.
- Temporal: overkill para MVP, re-evaluar si crecemos.

---

## ADR-007 — Ollama local como motor IA default

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
PMO maneja datos sensibles (presupuestos, estrategia, personal). Queremos opción "zero data egress".

**Decisión:**
**Ollama + Qwen 2.5 7B** como default. **Claude Sonnet 4.6** como fallback opcional por tenant.

**Consecuencias positivas:**
- Privacidad: datos nunca salen.
- Costo fijo, no por token.
- Tenants pueden elegir según su política.

**Consecuencias negativas:**
- Requiere hardware GPU o Mac con buen chip.
- Calidad ligeramente inferior a Claude, pero suficiente para minutas/reportes estructurados.
- Latencia variable según carga.

**Alternativas:**
- Solo Claude: pierde clientes con compliance strict.
- Solo Ollama: pierde uso en cargas difíciles.
- llama.cpp server custom: más control, pero Ollama lo usa debajo y es más plug-and-play.

---

## ADR-008 — Monorepo con pnpm + Turborepo

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Proyecto tiene frontend (TS/React), backend (Python), docs, infra. Necesitamos gestionar dependencias compartidas y builds eficientes.

**Decisión:**
**Monorepo**: `apps/web`, `apps/api`, `packages/ui`, `packages/config`, `packages/sdk`, `docs/`.
Gestor: **pnpm workspaces** + **Turborepo** para caching.

**Consecuencias positivas:**
- Tipos compartidos (generados desde OpenAPI) en `packages/sdk`.
- Design system en `packages/ui` reutilizable.
- Builds cacheados por Turbo (solo rebuild lo que cambió).

**Consecuencias negativas:**
- Python y Node mezclados — cada uno con su tooling.
- CI más complejo (matrix jobs).

**Alternativas:**
- Dos repos separados: acoplamiento de versiones más doloroso.
- Nx: más pesado que Turborepo, curva mayor.

---

## ADR-009 — MPXJ + frappe-gantt para MS Project

**Estado:** ✅ Aceptada — 2026-04-18 (con revisión post-MVP)
**Contexto:**
Necesitamos leer `.mpp`, `.xml`, `.xlsx` de MS Project y visualizar Gantt interactivo.

**Decisión:**
- **MVP:** solo `.xml` y `.xlsx` con parser Python custom / openpyxl.
- **Post-MVP:** agregar `.mpp` nativo usando **MPXJ** en sidecar Java.
- Gantt: **frappe-gantt** (liviano, 30 KB).

**Consecuencias:**
- MVP sin Java runtime (más simple en Railway).
- Calidad de parsing `.xml` es alta (schema MSP estándar).
- frappe-gantt limitado en drag&drop → post-MVP evaluar dhtmlx-gantt.

**Alternativas:**
- Aspose.Tasks: propietario, costoso.
- Python `python-pptx`-style lib para .mpp: inexistente buena.

---

## ADR-010 — i18n desde el día 1 con next-intl

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Mercado objetivo ES-MX principalmente, pero clientes pueden requerir EN-US. Agregar i18n tarde es caro.

**Decisión:**
**next-intl** en frontend, **Babel messages** en backend (jinja-based templates para emails).
Todas las strings en archivos de mensajes, no hardcoded. CI rule bloquea strings literales en JSX fuera de componentes tipo `<Trans />`.

**Consecuencias:**
- Onboarding de nuevos mercados (EN) trivial.
- Moneda y formato de fecha tenant-configurable.
- Overhead de mantener 2 archivos de mensajes.

**Alternativas:**
- react-intl: similar, menos integrado con Next 15.
- i18next: funciona bien, pero next-intl tiene mejor DX en App Router.

---

## ADR-011 — Sentry para observabilidad unificada

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Necesitamos errores + performance + traces. Alternativas: Sentry, Datadog, Grafana Stack, New Relic.

**Decisión:**
**Sentry** (plan Team, $26/mes) cubre frontend + backend con un SDK por cada lado. Tags `tenant_id`, `user_id`, `api_version`.

**Consecuencias:**
- Correlación errores frontend ↔ backend con trace_id.
- Dashboard único para equipo.
- Release tracking auto.

**Alternativas:**
- Grafana+Prometheus+Loki+Tempo: más control, mucho setup.
- Datadog: caro para volumen que tenemos.

---

## ADR-012 — Folios legibles por tenant y entidad

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Usuarios quieren referirse a proyectos/riesgos con códigos cortos, no UUIDs.

**Decisión:**
Folios con prefix + año + secuencial por tenant: `PRJ-2026-001`, `SOL-2026-015`, `RIS-2026-042`.
Implementado con secuencia Postgres por `(tenant_id, kind, year)`.

**Consecuencias:**
- Legible, comunicable en correos/reuniones.
- Secuencia atómica (no hay gaps ni duplicados en alta concurrencia).
- Año dentro permite reinicio anual si se desea (off por default).

**Alternativas:**
- UUID short (`base62`): menos legible.
- Hashids: reversible si filtra el salt.

---

## Template para nuevas ADRs

```markdown
## ADR-XXX — Título

**Estado:** Propuesta | Aceptada | Deprecada | Reemplazada por ADR-YYY
**Fecha:** YYYY-MM-DD

**Contexto:**
Situación, restricciones, alternativas consideradas.

**Decisión:**
La elección concreta.

**Consecuencias:**
Positivas y negativas. Mitigaciones de las negativas.

**Alternativas evaluadas:**
- Opción A: razón por la que no.
- Opción B: razón por la que no.
```
