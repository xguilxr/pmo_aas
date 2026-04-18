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

## ADR-007 — Cascada de proveedores IA: Ollama → Gemini → Claude

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
PMO maneja datos sensibles (presupuestos, estrategia, personal). Criterios en
orden: (1) **privacidad**, (2) **coste cercano a cero** en MVP personal,
(3) calidad suficiente para minutas/reportes estructurados, (4) disponibilidad
en horas de uso intenso.

**Decisión:**
Adoptar **cascada de tres proveedores** con orden estricto de prioridad y
política por tenant:

1. **Ollama local** (default global) con `qwen2.5:7b-instruct-q4_K_M`.
   Hospedado en tu hardware (home-host via Cloudflare Tunnel), VPS con GPU,
   o Railway GPU cuando esté disponible.
2. **Google Gemini 1.5 Flash** como **2.º fallback gratuito** — free tier
   1M tokens/día, 15 RPM. Suficiente para un MVP con <10 tenants activos.
3. **Claude Sonnet 4.6** como **3.º fallback premium** — solo si el tenant
   lo activa explícitamente y aporta API key. Mejor calidad para cargas
   complejas.

Política por tenant en `tenants.settings.ai.providers`: array ordenado.
Runtime intenta primero el primero disponible; si falla/timeout, pasa al
siguiente.

**Consecuencias positivas:**
- **Costo $0** en MVP personal (Ollama home + Gemini free tier).
- Privacidad por default (data no sale si Ollama responde).
- Resiliencia: si home-host cae, Gemini cubre automático.
- Tenant puede desactivar Gemini/Claude si su política lo prohíbe.

**Consecuencias negativas:**
- Código del provider tiene complejidad adicional (cascada + métricas).
  Mitigación: abstraer en `AIProviderCascade` con tests del fallback.
- Gemini free tier tiene **rate limit 15 RPM** — si se satura, cola de jobs
  se ralentiza. Mitigación: backoff + alerta a admin.
- Para ir a producción real con un tenant sensible, idealmente home-host
  Ollama con SLA interno (monitoreo + auto-restart).

**Alternativas evaluadas:**
- Solo Claude: coste alto, pierde clientes con compliance estricto.
- Solo Ollama: sin fallback si hardware cae.
- Ollama + Claude (sin Gemini): Claude cuesta real; Gemini cubre el hueco gratis.
- OpenAI gpt-4o-mini: buena calidad pero sin free tier real y menos alineado
  con nuestra política ("0 data egress preferido").

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

## ADR-011 — GlitchTip self-hosted para observabilidad (reemplaza Sentry)

**Estado:** ✅ Aceptada — 2026-04-18 (reemplaza propuesta previa de Sentry pago)
**Contexto:**
Necesitamos errores + performance (p95) + trazas con tags `tenant_id`,
`user_id`, `api_version`. Sentry cloud (plan Team $26/mes) no encaja en el
presupuesto personal del MVP. Alternativas evaluadas:

- **GlitchTip** — OSS compatible con Sentry SDK (mismos DSN, mismo protocolo).
- **Sentry OSS self-hosted** — potente pero ~2GB RAM mín., complejidad alta
  (Kafka, Zookeeper, ClickHouse).
- **BetterStack Telemetry Free** — 1GB logs/mes, 3d retención; sin errores como
  primer ciudadano.
- **Grafana Cloud Free** — 10k series, 50GB logs, 14d; requiere instrumentar
  OpenTelemetry desde cero.
- **Axiom Free** — 500GB ingest/mes; bueno para logs pero no para errores.
- **Solo Railway Logs + UptimeRobot** — gratis total, pero sin stack trace
  agregado ni dashboard de errores.

**Decisión:**
**GlitchTip** como servicio adicional en Railway (~$5/mes de compute, $0 de
licencia). Usamos `sentry-sdk` (Python) y `@sentry/nextjs` (Next) **sin
cambios** — GlitchTip implementa el protocolo wire de Sentry. Complementamos
con:
- **Railway Logs** (incluido) para logs.
- **UptimeRobot Free** (50 monitors) para uptime externo.
- Tabla interna `audit_log` para forense de negocio.

**Consecuencias positivas:**
- Costo: **~$5/mes** vs $26 de Sentry cloud.
- Datos **nuestros** (compliance, GDPR más sencillo).
- Migrar a Sentry cloud luego = cambiar DSN (sin refactor).
- Suficiente para volumen MVP (hasta ~50k eventos/día).

**Consecuencias negativas:**
- Operamos una pieza más (upgrades, backups de la DB de GlitchTip).
- GlitchTip no tiene tracing distribuido completo (solo performance simple).
  Mitigación: si lo necesitamos, OTel → Grafana Cloud Free.
- Sin release health nativo tipo Sentry SaaS; se puede simular.

**Alternativas descartadas:**
- Sentry cloud: fuera de presupuesto personal.
- Sentry OSS self-hosted: overkill para MVP.
- Grafana Cloud Free: buena opción post-MVP cuando tracing importe.

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

## ADR-013 — Dev local sin Docker obligatorio

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
El owner desarrolla en Windows y ha tenido fricción recurrente con Docker
Desktop (consumo RAM de VMMEM, WSL2 lento, ocasionales licencias empresariales
ausentes). Forzar Docker bloquea el setup inicial.

**Decisión:**
Ofrecer **tres rutas de setup** documentadas en `docs/setup-dev.md`:
- **Ruta A:** Windows nativo — Postgres installer + Memurai (Redis) + Ollama
  instalador + Python + Node. Cero Docker.
- **Ruta B:** Railway dev services — Postgres/Redis en Railway vía plugin;
  dev corre local contra esas URLs. Ideal si se trabaja desde varias máquinas.
- **Ruta C:** macOS/Linux con Docker — para quien prefiere contenedores de
  infra. Ollama siempre nativo (GPU passthrough).

Testcontainers (usado en tests de integración) sigue necesitando Docker, pero
solo al correr `pytest -m integration` — desarrollo día a día no lo exige.

**Consecuencias positivas:**
- Onboarding en Windows sin bloqueadores.
- Ollama nativo siempre gana en rendimiento vs Docker (sin GPU passthrough issues).
- Ruta B acerca dev a producción (mismos managed services).

**Consecuencias negativas:**
- 3 rutas documentadas = 3× superficie de soporte. Mitigación: las rutas
  comparten `.env.example` y comandos de app son idénticos.

**Alternativas:**
- Docker forzoso: fuente conocida de fricción del owner.
- Dev containers (VS Code): buena DX pero aún requiere Docker.

---

## ADR-014 — Home-host Ollama vía Cloudflare Tunnel (opcional)

**Estado:** ✅ Aceptada — 2026-04-18
**Contexto:**
Railway aún no ofrece GPU uniformemente; VPS con GPU cuesta €220+/mes. El
owner puede disponer de hardware en casa/oficina (Mac Studio, PC con GPU NVIDIA).

**Decisión:**
Soportar **home-hosting de Ollama** como primera opción económica en producción:
- Servidor local con Ollama nativo.
- **Cloudflare Tunnel** (`cloudflared`) expone `ollama.pmoaas.com` sin abrir
  puertos en el router; auth por service token de Cloudflare Access.
- Railway `api/worker` apunta a ese FQDN con `OLLAMA_BASE_URL` + headers de
  auth de Cloudflare.
- Health check detecta caída y cascada pasa a Gemini automáticamente (ver ADR-007).

**Consecuencias positivas:**
- **$0/mes** de hosting GPU.
- Cero ingreso de data a terceros (end-to-end bajo nuestro control).
- Hardware ya amortizado se reutiliza.

**Consecuencias negativas:**
- Uptime dependiente de tu conexión/energía. Mitigación: cascada a Gemini.
- Si te mueves o el hardware muere, hay que repensar. Mitigación: VPS con GPU
  es el plan B ya documentado.
- Latencia +30-80ms por el túnel vs Railway same-region.

**Alternativas:**
- Railway GPU tier: depende de disponibilidad; reevaluar en 3 meses.
- VPS GPU Hetzner/OVH: €220-250/mes — evaluar cuando haya ingresos.

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
