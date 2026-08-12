---
tipo: adr
responsable: propietario
estado: vigente
revisado: 2026-08-05
revisar_cada: nunca
---

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
- *(Originalmente: sin GPU nativa para Ollama. Ya no aplica — DEC-017 + BUG-053 eliminaron Ollama; los providers IA son APIs remotas.)*

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

**Estado:** ⚠️ Aceptada en diseño 2026-04-18 — **NO implementada en producción.**

> **Update 2026-05-23:** Ninguna migración Alembic activa el RLS
> (`ENABLE ROW LEVEL SECURITY`) ni crea policies. El aislamiento
> multi-tenant se hace en **capa de aplicación**: cada endpoint declara
> `Depends(get_current_tenant_id)` y filtra `WHERE tenant_id = :tid` en
> cada query. La defensa en profundidad vía RLS queda como deuda
> técnica (ver `architecture/database.md` §"Lo que NO usamos" y
> `architecture/security-multitenant.md`).
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
- Ecosistema IA / ML libs (httpx contra Groq/OpenAI/Anthropic/Gemini/Perplexity/Azure) sin overhead de bindings exóticos.
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

**Estado:** ❌ **Reemplazada** por DEC-017 (modos `disabled`/`platform`/`byo` por tenant) y eliminada del código en BUG-053 (2026-05-08).

> No queda `OllamaProvider` ni cascada automática. Modo `platform` corre
> contra Groq; modo `byo` deja al tenant elegir UN provider (OpenAI /
> Claude / Gemini / Perplexity / Azure Copilot M365 / custom / Groq).
> Si un provider falla, el job se marca `failed` (sin fallback). Ver
> `EP008-ai.md` y `architecture/stack.md`.
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

## ADR-008 — Monorepo con pnpm (+ Turborepo planeado)

**Estado:** ⚠️ Aceptada parcialmente. pnpm workspaces sí, **Turborepo NO**.

> **Update 2026-05-23:** No hay `turbo.json` ni dependencia Turborepo
> en el repo. Los scripts corren `pnpm -r` directo. Caching de builds
> es responsabilidad de cada herramienta (Next, ruff, pytest). Si en
> algún punto los builds se vuelven el cuello, reintroducir Turbo es
> trivial.
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

**Estado:** ⚠️ MPXJ sí (US-069 DONE, embebido en Dockerfile). frappe-gantt **NO** (se usa SVG propio).

> **Update 2026-05-23:** `.mpp` nativo ya es soporte estándar (no
> post-MVP) — MPXJ + JRE 21 viven en el Dockerfile compartido. El
> Gantt visual en frontend es `components/gantt-view.tsx` (SVG manual);
> no se instaló frappe-gantt ni dhtmlx-gantt. Ver `EP009-ms-project.md`
> y `architecture/stack.md`.
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

**Estado:** ❌ **No implementada.** La app es **solo ES** hoy.

> **Update 2026-05-23:** `next-intl` no está instalado en
> `apps/web/package.json`. No hay archivos `messages/*.json` ni gate
> CI. Si se necesita EN, hay que retomar como nueva US (incluiría
> instalar next-intl, montar provider, extraer ~todas las strings de
> JSX, y montar el catálogo de mensajes).
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

**Estado:** ❌ **No implementada.** Ni GlitchTip ni Sentry están en el stack hoy.

> **Update 2026-05-23:** `sentry-sdk` se eliminó de
> `apps/api/requirements.txt`. No hay servicio `glitchtip` en Railway.
> Hoy la observabilidad se limita a Railway Logs + `structlog` (JSON
> en prod) + tabla `audit_log` para forense de negocio. Si se decide
> reintegrar APM, esta ADR aplica como referencia.
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
- **Ruta A:** Windows nativo — Postgres installer + Memurai (Redis) + Python + Node. Cero Docker. *(El paso "Ollama installer" ya no aplica — BUG-053 eliminó Ollama; el dev local apunta a Groq con tu propia key o BYO.)*
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

**Estado:** 🔄 Reemplazada por ADR-015 — 2026-04-21
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

## ADR-015 — Tailscale reemplaza Cloudflare Tunnel + Access para Ollama local

**Estado:** ⚠️ Aceptada 2026-04-21 — **Superseded por DEC-017 (ENH-023,
2026-04-23):** Groq hosteado reemplazó Ollama local en el flujo
productivo; el sidecar Tailscale del worker se retiró. Este ADR queda
como historia del pivote CF Tunnel → Tailscale; la infra descrita abajo
NO está activa en prod.

**Estado original:** ✅ Aceptada — 2026-04-21 (reemplaza ADR-014)
**Contexto:**
ADR-014 definió **Cloudflare Tunnel + Cloudflare Access (Service Token)**
como canal para exponer Ollama local al backend PMO. El intento real de
despliegue destapó tres fricciones operacionales serias:

1. **Complejidad de Cloudflare One UI**: la migración a "Cloudflare One"
   fragmenta Access Controls, Policies y Login Methods. El flujo
   "Application + Service Auth policy + Service Token" tiene bugs de
   estado (dropdown `Select...` vacío al guardar) y la UI cambia entre
   sesiones. Documentar un runbook reproducible es frágil.
2. **403 silenciosos por managed rulesets**: aun con Access correcto,
   el **AI bot blocking ruleset** de Cloudflare (managed, default-on) y
   Bot Fight Mode interceptan requests con UA no-browser (curl, httpx)
   devolviendo 403 sin evento visible en Security → Events. Requiere
   custom Skip rules por hostname — y aun así persisten 403 residuales.
3. **Exposición pública innecesaria**: el endpoint `ollama.pmo-aas.com`
   es un API privado que solo debe ver el worker de Railway. Publicarlo
   en internet (aunque con token) aumenta la superficie: fuga de secret
   → acceso directo a inferencia no facturable, scrapers dedicados,
   correlación con el dominio productivo.

**Decisión:**
Reemplazar CF Tunnel + Access con **Tailscale** (tailnet privado,
WireGuard-based). Topología:

```
PC Windows (tailscaled service)          Railway worker (sidecar tailscaled)
 └─ Ollama 0.0.0.0:11434                   └─ http://ollama-host.<tailnet>.ts.net:11434
 └─ tailnet IP 100.x.y.z                             │
                 └──── tailnet WireGuard ───────────┘
```

- PC local: instala Tailscale (MSI), `tailscale up --hostname=ollama-host`.
- Ollama: `OLLAMA_HOST=0.0.0.0:11434` para aceptar conexiones tailnet.
- Windows Firewall opcional: permite inbound 11434 solo desde
  `100.64.0.0/10`.
- Railway `worker`: Dockerfile custom con `tailscaled` en user-space
  networking; `start.sh` arranca `tailscaled` con `TS_AUTHKEY` (ephemeral
  reusable key) antes de `exec celery`.
- Config por-tenant (`tenants.settings.ai.ollama.base_url`) pasa a
  `http://ollama-host.<tenant>.ts.net:11434` o IP tailnet directa. Sin
  headers de auth.

**Consecuencias positivas:**
- **Cero exposición pública**: Ollama deja de tener hostname en internet.
  Subdominio `ollama.pmo-aas.com` se retira.
- **Setup reproducible**: 2 comandos en Windows + 1 sidecar en Dockerfile.
  Sin policies, sin WAF bypass, sin managed rulesets peleándose.
- **Auth nativa de red**: Tailscale admin console centraliza device
  approval, key rotation, ACLs. Revocación de laptop = 1 click.
- **Free tier suficiente**: 100 dispositivos, 3 usuarios gratis. Hobby
  tier cubre MVP.
- **Latencia competitiva**: WireGuard direct path cuando NAT lo permite
  (30-60ms); DERP relay comparable al tunnel CF cuando no (60-90ms).
- **Observabilidad**: admin.tailscale.com da ping, last-seen,
  connection type (DERP vs direct). Mejor que logs de cloudflared.

**Consecuencias negativas:**
- **Dependencia de Tailscale Inc**: nuevo SaaS en el stack crítico.
  Mitigación: `tailscaled` es OSS; self-host con **Headscale** es plan B
  si escala lo justifica o si TS sube precios.
- **Container worker más pesado**: +15 MB por `tailscaled` en la imagen,
  y un wrapper shell (`start.sh`) en vez de CMD limpio. Mitigación:
  documentado en US-048; template reutilizable.
- **Pérdida de hostname bonito**: sin `ollama.pmo-aas.com`. Mitigación:
  endpoint es privado, nunca lo ven humanos; no aporta valor estético.
- **Troubleshooting multi-host**: fallas requieren revisar 3 lados
  (Tailscale admin, worker log, Ollama log). Mitigación: smoke test CLI
  (US-047) corre end-to-end y reporta dónde rompe.

**Impacto en el stack:**
- **ADR-014**: marcada Reemplazada.
- **ADR-007** (cascada IA): sin cambio. Ollama sigue tier-1.
- **EP016**: US-044 (runbook CF) y US-045 (config CF-Access)
  quedan SUPERSEDED; nuevas US-046/047/048 cubren el reemplazo.
- **Dominio `pmo-aas.com`**: conserva apex + `app.*` + `api.*` +
  `www.*` en Cloudflare. Solo se retira `ollama.*`.

**Alternativas evaluadas:**
- **CF Tunnel + Access (status quo, ADR-014)**: bloqueado en prod por
  403 del AI bot ruleset; setup frágil; exposición innecesaria.
- **CF Tunnel sin Access + Basic Auth via Caddy local**: recicla el
  tunnel pero mantiene exposición pública. Cambia un problema por otro.
- **ngrok (paid tier con custom domain)**: similar a CF Tunnel, peor
  precio ($8-10/mes) y mismo modelo de exposición pública.
- **Reverse SSH a VPS bastión**: requiere VPS ($5/mes) + bastión mantenido.
  Más fricción sin ganancia.
- **Tailscale Funnel**: expone tailnet a internet — mismo antipattern.
- **WireGuard manual**: viable pero sin admin console, sin device
  approval, sin MagicDNS. Fricción ops significativa.

**Referencias:**
- <https://tailscale.com/kb/1017/install>
- <https://tailscale.com/kb/1282/docker> (sidecar en containers)
- Runbook (archivado post-DEC-017): `docs/archive/runbooks-ai-legacy/local-ollama-setup.md` (reescrito en US-046; movido al archivo por ENH-022).

---

## ADR-016 — Programas cross-empresa: diferir hasta criterio de demanda

**Estado:** ✅ Aceptada — 2026-04-29
**Fecha:** 2026-04-29

**Contexto:**
Feedback DRC (Sprint 8 v1.7, item 16) pidió poder agrupar proyectos
de varias empresas dentro de un mismo programa "Corporativo". Hoy el
modelo `programs` tiene FK 1:1 a `organizations`, lo que limita un
programa a vivir en una sola org. Ampliar a N:M requiere:
- Tabla nueva `program_organizations` (m2m).
- Redesign de listados que filtran por `organization_id`.
- Reportes y dashboards que asuman 1:1 hoy.
- Permisos: ¿quién puede leer un programa que cruza orgs?

ETA estimado: 3-4 días + tests.

**Decisión:**
**Diferir** la migración estructural. Entregar un workaround
documentado (`docs/runbooks/programs/cross-org-programs-workaround.md`)
para los pocos casos actuales, y revisitar cuando se cumpla cualquiera
de los siguientes triggers:
1. **≥3 grupos de clientes** lo solicitan formalmente.
2. El cliente más grande (>50 proyectos) lo necesita estructuralmente.
3. La tasa de "programas con un solo proyecto cuyo PM es de otra
   empresa" supera el 20% del total (proxy de uso forzado del
   workaround).

**Consecuencias:**
- ✅ Sprint 8 entrega el feature visible (workaround) sin
  arriesgar la estabilidad de listados/reportes.
- ✅ Decisión auditada; futuros tickets de "programas cross-empresa"
  apuntan a este ADR para evaluar trigger.
- ❌ Clientes con la necesidad genuina cargan con etiquetas/tags como
  workaround; reportes cross-org requieren filtros manuales.

**Alternativas evaluadas:**
- **Implementar ahora** (m2m + redesign): rechazada por costo vs.
  demanda actual (1 cliente, 1 caso real).
- **Eliminar la FK org en programs** (programa "free")**: rechazada
  porque rompe la jerarquía conceptual del modelo PMO.

**Triggers de revisión:** ver "Decisión" arriba (3 criterios).

---

## ADR-017 — Hard delete tenant-admin con patrón two-step

**Estado:** ✅ Aceptada — 2026-05-05
**Fecha:** 2026-05-05

**Contexto:**
Hasta US-088 todas las acciones "Borrar" del panel de tenant-admin
hacían soft-delete (`is_active=false`, en algunos casos `deleted_at`).
El owner reportó (2026-05-05) que necesita borrar permanentemente un
programa duplicado: el soft-delete deja basura visible en filtros
"inactivos" y, sobre todo, no libera unique constraints (`name` por
tenant), por lo que recrear con el mismo nombre falla.

Las 6 entidades afectadas son: `Organization`, `Program`,
`BusinessUnit`, `Department`, `User`, `Stakeholder`. La única
contraparte con hard-delete previo era `superadmin.delete_tenant`
(slug confirm, blast radius enorme, fuera del alcance del tenant).

**Decisión:**
Adoptar el patrón **two-step delete** uniforme para las 6 entidades:

1. **Paso 1 (existente):** `DELETE /<entity>/{id}` → soft-delete
   (`is_active=false`, `deleted_at` cuando aplique).
2. **Paso 2 (nuevo, US-088):** `DELETE /<entity>/{id}/permanent?confirm=<slug>`
   → físico, tras chequeo `is_active=false` y match exacto de `confirm_slug`.
3. **Preview:** `GET /<entity>/{id}/hard-delete-preview` devuelve
   `{ confirm_slug, cascades, blockers }` para que la UI muestre
   conteos antes de exigir el typed confirm.
4. **Cascada:** decisión owner (AskUserQuestion 2026-05-05) =
   "cascade-delete dependents (with explicit count in confirm)".
   Implementación per-entidad:
   - `Organization` → hard-delete proyectos/requests dependientes,
     CASCADE FK toma BUs/programs/exclusions; stakeholders quedan
     SET NULL.
   - `Program` → hard-delete proyectos hijos (project FK CASCADE
     barre modules/charter/tasks/areas/members/scheduled_reports).
   - `BusinessUnit` → SET NULL en project/charter/request, CASCADE FK
     barre departments.
   - `Department` → SET NULL en program/project/charter/request.
   - `User` → SET NULL en ~15 FKs nullables; CASCADE FK barre
     auth/role/member/notification/exclusion. **Bloqueante** si el
     user tiene `project_request.requested_by` o
     `permission_change_request.requested_by_user_id` (NOT NULL): se
     devuelve 409 con `blockers` en `fields`. Resolver manualmente.
   - `Stakeholder` → delete trivial (sin dependientes hoy).
5. **Audit:** acción `<entity>.hard_delete` con `details.cascades`.

**Consecuencias:**
- ✅ Owner desbloqueado para limpiar duplicados con UI segura.
- ✅ Patrón único reutilizable (`confirm_slug` determinístico,
  componente `<HardDeleteButton>` único en frontend).
- ✅ Inactivar primero protege contra hard-delete accidental.
- ❌ Cascade de `User` no es total: hay tablas con FK NOT NULL
  no-cascade (`project_request.requested_by`,
  `permission_change_request.requested_by_user_id`). Se documentan
  como blockers; futura US puede agregar reasignación interactiva.
- ❌ FK landscape diverso → la lógica de cascade vive en cada
  endpoint, no en un helper genérico. Ver `apps/api/app/core/hard_delete.py`
  para el helper mínimo (slug + checks).

**Alternativas evaluadas:**
- **Hard-delete sin two-step (botón directo):** rechazada — sin
  freno previo es demasiado fácil borrar producción.
- **Bloquear hard-delete si hay dependientes (sin cascade):**
  rechazada por owner — preferían cascade explícito sobre fricción
  de limpiar dependientes manualmente uno por uno.
- **`ondelete=CASCADE` global vía migración:** rechazada por
  blast radius (ya hay datos en producción) y porque algunas
  relaciones deben sobrevivir al borrado del padre (auditoría).
- **Slug confirm autogenerado vs typed:** se eligió typed confirm
  para forzar contacto consciente con el nombre exacto.

---

## ADR-018 — Exclusión de MCS ARQ-03: el dominio seguirá hablando SQLAlchemy

**Estado:** ✅ Aceptada — 2026-08-04
**Fecha de revisión:** 2027-02-04, o antes si se dispara alguno de los gatillos de abajo

**Contexto:**
`MCS-CORE` ARQ-03 (N1) exige que «la lógica de dominio NO DEBE depender del
framework web ni del mecanismo de persistencia». La medición de R1 (2026-08-04,
`docs/archive/conformidad/2026-08-04-mcs-r1.md`) dio el número: **54 de los 68 módulos de
`apps/api/app/services/` importan SQLAlchemy**, y solo 2 importan FastAPI.

O sea que el acoplamiento al framework web es leve —los servicios no saben de
peticiones HTTP— y el que existe de verdad es a la persistencia: los servicios
reciben `AsyncSession` y consultan el ORM directamente, sin puertos ni
repositorios en medio.

Cerrarlo es una reescritura arquitectónica: introducir una capa de repositorios
sobre 68 módulos, con sus pruebas, son semanas durante las cuales el producto no
avanza.

**Decisión:**
**Excluir ARQ-03** del alcance de conformidad MCS, con la justificación y el
riesgo que siguen. `MCS-CORE` §1.3 y GOB-02 lo permiten siempre que quede
registrado así.

La exclusión es de **este requisito y este momento**, no una postura permanente
sobre arquitectura hexagonal.

**Justificación:**
Los dos beneficios que ARQ-03 persigue no están en el horizonte de este producto:

- **Cambiar de mecanismo de persistencia.** Postgres es una decisión asumida
  desde ADR-001 (Railway, con su plugin de Postgres). No hay escenario planteado
  en el que se migre de motor.
- **Ejercitar el dominio sin base de datos.** Es el argumento más fuerte de
  ARQ-03, y aquí ya está cubierto por otro camino: la suite corre contra una base
  real y cubre la lógica de negocio de punta a punta (991 casos). La
  independencia daría pruebas más rápidas, no más pruebas.

**Riesgo aceptado:**

1. **Migrar de SQLAlchemy o de motor tocaría 54 módulos.** Si algún día pasa, el
   coste de esta exclusión se paga entero y de golpe.
2. **Las pruebas del dominio necesitan base.** Hoy la suite de API tarda ~26
   minutos en local. Ese número solo puede empeorar, y no hay atajo mientras el
   dominio no sea aislable.
3. **El dominio no es extraíble.** Si mañana hiciera falta un segundo consumidor
   —un servicio aparte, un CLI, un trabajo por lotes— habría que arrastrar el
   ORM entero o duplicar la lógica.

**Gatillos que obligan a revisar antes de la fecha:**

- Se decide soportar otro motor de base de datos.
- La suite de API supera los 45 minutos.
- Aparece un segundo consumidor de la lógica de dominio.

**Alternativas evaluadas:**

- **Refactor completo a puertos y adaptadores.** Cierra el requisito de verdad.
  Descartada por coste: semanas con el roadmap congelado, para un beneficio que
  hoy es teórico.
- **Refactor parcial**, solo el núcleo de plan y salud. Tentadora, pero deja el
  requisito igual de incumplido —ARQ-03 no admite grados— y además crea dos
  estilos de acceso a datos conviviendo, que es peor que uno malo.
- **Dejarlo NO CONFORME sin ADR.** Es lo que había. Bloquea N1 indefinidamente y
  reaparece en cada auditoría sin que nadie decida nada, que es exactamente cómo
  llegó a estar sin medir.

---

## ADR-019 — `support` se renombra a `hypercare`

**Estado:** ✅ Aceptada e **implementada** — 2026-08-05 (migración 0098)

**Contexto:**
La revisión del glosario (D-2) preguntó si `support` era una fase legítima. La
respuesta del owner fue que **sí lo es** —«un estado de hypercare antes del
cierre formal, pero es una forma de closing»— y que el problema era el nombre:
`support` se lee como «mesa de ayuda», que es una función permanente, no una
fase de proyecto con principio y fin.

El vocabulario real de hoy son cuatro fases: `planning`, `execution`, `support`,
`closed`. `phase` es `String(32)` sin enum de base (`models/project.py:43`), así
que el cambio no exige migrar un tipo, pero sí migrar los datos existentes y los
tipos del frontend.

**Decisión:**
Renombrar `support` → `hypercare` en el modelo, la API y la UI.

**Consecuencias:**

- El nombre pasa a decir lo que la fase es: acompañamiento acotado tras la puesta
  en marcha, no soporte perpetuo.
- **Es cambio de contrato.** `apps/web/lib/api/projects.ts:3` declara el tipo,
  la UI lo ofrece como filtro (`projects/page.tsx:38,581`) y
  `ACTIVE_PHASES` lo lista (`analytics/snapshots.py:28`). Un cliente con un
  filtro guardado deja de encontrarlo.
- Necesita **migración de datos** sobre proyectos productivos, y la corre el
  owner. Conviene aceptar los dos valores durante una ventana, como se hizo con
  `amber` → `yellow` en la migración 0091.
- Sin efecto en el semáforo ni en los informes: `support` no aparece en la
  lógica de salud.

**Alternativas evaluadas:**

- **Dejar `support` y documentarlo como hypercare.** Gratis, y era la
  recomendación. Se descarta porque el glosario existe justamente para que el
  nombre en código y el concepto coincidan; documentar la discrepancia la
  conserva.
- **Renombrar y además añadir `initiation` y `cancelled`.** Cubre dos huecos
  reales —hoy un proyecto nace en `planning` aunque el acta sea previa, y uno
  cortado queda `closed`, indistinguible de uno que cumplió— pero es un cambio
  de modelo mayor. Se separa: primero el renombrado, esos dos como decisión
  propia.

**Lo que esta ADR NO decide:** si hacen falta `initiation` y `cancelled`. Sigue
abierto y merece su propia ADR.

---

## ADR-020 — `tasks.wbs` se renombra a `wbs_code`

**Estado:** ✅ Aceptada e **implementada** — 2026-08-05 (US-194, migración 0100)

**Contexto:**
La columna guarda el **código** de la EDT (`1.2.3`), no la estructura — esa vive
en `parent_id` y `outline_level`. El propio código ya lo sabe:
`apps/api/app/models/task.py:90` documenta «predecessors / successors como JSON
array de **wbs_code**» mientras la columna se llama `wbs`. La decisión D-3 del
glosario aprobó el renombrado.

**Decisión:**
Renombrar la columna, el campo de la API y el del frontend a `wbs_code`.

**Lo que cuesta, medido el 2026-08-05 y no estimado:**

| | |
|---|---|
| Ocurrencias de `wbs` como identificador | **259** |
| Archivos de backend | **16** |
| Archivos de frontend | **6** |

No es un `sed`. Los sitios que hay que mirar uno a uno:

- **Los tres importadores** (CSV, XLSX, MS Project) y el sugeridor de mapeo de
  columnas. Ahí `WBS` es además una **etiqueta que el usuario ve** en su propio
  archivo, y esa **no** se renombra: el cliente sigue escribiendo «WBS» en su
  Excel. Confundir el nombre del campo con el de la columna importada rompería
  todas las importaciones existentes.
- **`predecessors` y `successors` son JSON de códigos**, no claves foráneas. El
  contenido no cambia, pero cualquier código que los cruce con `task.wbs` sí.
- **La plantilla descargable del plan** (`lib/plan-template.ts`) escribe la
  cabecera que luego el parser busca. Cambiar una sin la otra rompe el viaje de
  ida y vuelta.

**Consecuencias:**

- Es **cambio de contrato**: el campo viaja en las respuestas de tareas y en el
  cuerpo de creación. Va con la misma ventana de compatibilidad que D-2 —aceptar
  `wbs` a la entrada y devolver siempre `wbs_code`— para no romper a un cliente
  que no se haya actualizado.
- La migración es un `ALTER TABLE … RENAME COLUMN`, barata y reversible.
- El riesgo real no es la migración: es que un sitio se quede con el nombre
  viejo y deje de cruzar datos **sin fallar**, que es lo que pasó con
  `ACTIVE_PHASES` en D-2 y por lo que aquella llevó prueba propia.

**Alternativas evaluadas:**

- **Dejar `wbs` y documentar que significa el código.** Gratis. Se descarta por
  lo mismo que D-2: el glosario existe para que el nombre en código y el
  concepto coincidan, y aquí el propio comentario del modelo ya delata la
  discrepancia.
- **Renombrar solo en la API y no en la columna.** Deja una traducción
  permanente en medio, que es deuda con apariencia de solución.

**Por qué no se implementó junto a la ADR:** 259 ocurrencias en 22 archivos está
muy por encima del límite de 10 de `CLAUDE.md` §3, y el proceso del propio
glosario pide «ADR y US propia, una por una». La ADR fija la decisión y el
método; la ejecución es su propia ronda.

**Ejecutada el 2026-08-05 (US-194).** Lo que la ronda corrigió de esta ADR:

- **La medida asustaba de más y avisaba de menos.** Las 259 ocurrencias las
  resuelve un `sed` sobre `\bwbs\b` —que no toca `wbs_sort_key` ni `parent_wbs`,
  porque el guion bajo es carácter de palabra—. El trabajo real fueron los
  **siete sitios donde `wbs` no era nuestro campo**, y esta ADR nombraba tres.
  Los cuatro que faltaban: los cinco códigos de diagnóstico `WBS_*`, el elemento
  `<WBS>` de MS Project, la clave `wbs` del JSON de MPXJ y —la peligrosa— la
  clave `plan-wbs-level:<id>` de `localStorage`.
- **`localStorage` era el único que rompía en silencio.** Guarda el nivel de
  agrupación del plan. Renombrar la clave no habría dado ningún error: la
  preferencia guardada de cada usuario simplemente habría dejado de encontrarse.
  Es la forma de fallo que esta ADR señalaba como el riesgo real, en el sitio que
  no miraba.
- **La ruta `renumber-wbs` no se renombra.** El campo es lo que se decidió
  renombrar; la ruta habla de la EDT, que sigue llamándose WBS.
- **La ventana tiene dos puertas, no una.** `TaskCreate` y `TaskUpdate`. La del
  PATCH importa más: sin alias, mandar `wbs` no falla, no cambia nada.

---

## ADR-021 — `portfolio_function` se renombra a `discipline`

**Estado:** ✅ Aceptada e **implementada** — 2026-08-05 (migración 0099)

**Contexto:**
El glosario veta «portafolio» para un área (**brecha B-6**): un portafolio es un
conjunto de proyectos y programas agrupados para gestión estratégica, y esa
entidad **no existe en el producto**. Mientras no exista, usar la palabra para
otra cosa la gasta.

Lo que el campo guarda es el rol normalizado para saturación por capacidad:
`pm | pmo | arquitectura | infraestructura | aplicaciones | datos | seguridad |
integraciones | negocio | change | testing | vendor` (`models/area.py:233`).

La decisión D-8 aprobó renombrar, pero **el glosario dejaba la columna
«Preferente» en «—»**: no había nombre destino, y por eso estuvo bloqueada.

**Decisión (owner, 2026-08-05): `discipline`.**

Se eligió sobre las dos alternativas por una razón de vocabulario: en este
producto **«función» y «rol» ya significan otras cosas** —`by_function` es una
agregación de capacidad, y «rol» es el de permisos (`roles`, `user_roles`)—.
`discipline` es lo que la lista realmente enumera y no se pisa con nada.

**Lo que cuesta, medido:** 18 ocurrencias en 5 archivos de backend y 4 de
frontend. Es la más pequeña de las tres del glosario que tocan contrato.

**Consecuencias:**

- **Es cambio de contrato público:** `portfolio_function` es un parámetro de
  consulta de `GET /areas/actors` (`areas.py:675`). Va con la misma ventana de
  compatibilidad que D-2 y D-3 — aceptar el nombre viejo a la entrada y devolver
  siempre el canónico.
- Migración de columna (`ALTER TABLE … RENAME COLUMN`), barata y reversible.
- **`by_function` → `by_discipline`.** Era la decisión pequeña que quedaba
  dentro de la US, y se resolvió renombrando: dejar la clave de agregación con
  el nombre viejo mientras el campo lleva el nuevo reintroduce exactamente el
  desajuste que esta ADR existe para cerrar.
- La ventana cubre **dos puertas**, no una: el cuerpo de creación
  (`AliasChoices` en el esquema) y el parámetro de consulta, que va marcado
  `deprecated=True` para que salga así en el OpenAPI.

**Alternativas evaluadas:**

- **`capacity_function`.** Conserva «función», que es como lo llama la
  agregación. Se descarta porque arrastra la palabra que ya está sobrecargada.
- **`role_type` / `resource_role`.** Alinea con `resource_type` y `seniority`,
  sus vecinos de modelo. Se descarta porque «rol» es el de permisos y confundir
  los dos en un modelo multiinquilino es caro.

---

## ADR-022 — `cancelled` como quinta fase del proyecto

**Estado:** ✅ Aceptada e **implementada** — 2026-08-05 (US-195, sin migración)

**Contexto:**
La revisión del glosario (D-2) dejó el hueco por escrito y el owner lo resolvió
el 2026-08-05: **`cancelled` sí; `initiation` no.** Hoy un proyecto cortado a
mitad —sin presupuesto, prioridad cambiada, patrocinador que se fue— termina en
`closed`, **indistinguible de uno que llegó al final y entregó**.

No es un problema cosmético. Con un solo final:

- toda métrica de éxito cuenta el cancelado como entregado;
- sus lecciones aprendidas se mezclan con las de los que cumplieron, que es
  precisamente donde más importa separarlas;
- «¿cuántos proyectos cancelamos este año?» no tiene respuesta, y es una
  pregunta que una PMO se hace.

**Decisión:**
Añadir `cancelled` al vocabulario de `phase`. Se alcanza **desde cualquier fase
viva** y es **terminal**, como `closed`.

**No lleva migración, y conviene decir por qué.** `projects.phase` es
`String(32)` **sin `CHECK` ni enum de base** (`models/project.py:43`), de modo
que el valor nuevo no exige tocar el esquema — a diferencia de D-2 y D-8, que
eran renombrados sobre datos existentes. Lo único que cambia es el vocabulario
declarado en el código.

**Consecuencias:**

- **`ACTIVE_PHASES` pasa a derivarse del vocabulario** en vez de repetirlo:
  `[f for f in get_args(ProjectPhase) if f not in FASES_TERMINALES]`. Es el
  arreglo de una clase de error, no de un caso: cuando D-2 renombró `support`,
  esta lista fue el sitio que se quedó con el nombre viejo **sin fallar**, y los
  proyectos en hypercare habrían salido de los snapshots en silencio. Derivarla
  hace que cualquier fase terminal futura quede excluida sola.
- **Cancelado se pinta distinto de cerrado** (`danger` frente a `neutral`).
  Distinguirlos de un vistazo es el punto entero de la decisión; dos insignias
  grises habrían dejado el problema donde estaba.
- **`closed` no lleva a `cancelled`.** Un proyecto que llegó al final ya tuvo su
  final; permitir el paso sería reescribir la historia.
- **No es cambio de contrato que rompa a nadie**: se añade un valor, no se
  retira ninguno. No hace falta ventana de compatibilidad — al revés que D-2,
  D-3 y D-8. Un cliente viejo que no conozca `cancelled` lo verá como fase
  desconocida, que es lo que ya le pasaría con cualquier dato futuro.

**Lo que esta ADR NO decide:**

- **Si un proyecto cancelado queda de solo lectura.** Es la misma pregunta que
  el glosario dejó abierta para `closed` («no verificado»), y merece resolverse
  para los dos finales a la vez, no para uno.
- **Si `cancelled` necesita motivo obligatorio.** Sería lo natural —cancelar sin
  decir por qué desperdicia el dato más útil del final— pero es campo nuevo y
  formulario nuevo. US propia.
- **`initiation`: descartada por el owner.** El proyecto nace en `planning`
  aunque el acta sea previa, y eso no ha causado ningún problema reportado.

**Alternativas evaluadas:**

- **Un booleano `was_cancelled` junto a `closed`.** Evita tocar el vocabulario.
  Se descarta porque parte el estado en dos campos que hay que leer juntos: toda
  consulta de fase tendría que acordarse del booleano, y la que se olvide vuelve
  a contar cancelados como entregados — el mismo error, más escondido.
- **Un `status` separado del `phase`.** Es el modelo más general y el que usan
  las herramientas grandes. Se descarta por ahora: el producto ya tiene
  `phase` haciendo de ciclo de vida, y añadir una segunda dimensión sin
  necesidad demostrada es complejidad a cuenta del futuro.

---

## ADR-023 — El semáforo se queda el arco cálido; los gráficos, el frío

**Estado:** ✅ Aceptada e **implementada** — 2026-08-05 (US-197)

**Contexto:**
El owner pidió una paleta de gráficos **propia**: ni la de marca ni la de
Tailwind, categórica y distinta del semáforo a propósito. Al medir qué había,
resultaron dos sistemas y ninguno decidido:

- Los gráficos de la web ofrecían `success`, `warning` y `danger` como colores
  de **serie**, así que una serie cualquiera podía salir verde, amarilla o roja
  sin querer decir nada.
- Los informes del servidor llevaban hexes de Tailwind escritos a mano
  (`#2563eb`, `#dc2626`, `#7c3aed`, `#16a34a`, `#6b7280`, `#9ca3af`).

El choque concreto: **`#dc2626` marcaba «ruta crítica» en el Gantt y `#16a34a`
marcaba «lo real» en la curva-S**, mientras el semáforo de salud usaba esos
mismos rojo y verde para «proyecto en problemas» y «proyecto sano». El mismo
color decía dos cosas en la misma página.

**Decisión:**
Partir el espectro. **El semáforo se queda con el arco cálido y el verde; los
gráficos se quedan con el arco frío.** Cuatro ranuras categóricas de orden fijo
y una rampa ordinal de un solo tono, con origen único en `app/core/paleta.py` y
espejo en los tokens `--chart-*`.

| Trabajo | Qué codifica | Forma |
|---|---|---|
| Categórica | identidad (equipo, área, proyecto) | 4 ranuras, orden fijo, sin reciclar |
| Ordinal | secuencia (fase, tramo, tamaño) | un tono, claro → oscuro |
| Estado | salud | el semáforo, reservado |

No es solo estética: hace **imposible por construcción** que una serie parezca
un estado.

**Consecuencias:**

- **El orden de las ranuras es el mecanismo de seguridad, no una preferencia.**
  Con los mismos cuatro tonos en otro orden, el teal y el rosa colapsan a
  **ΔE 0,2** bajo deuteranopía —indistinguibles—; en el orden elegido el peor
  par adyacente queda en 13,3. Por eso se asignan en secuencia y `serie()`
  **lanza** en vez de reciclar: una quinta serie con el color de la primera es
  un gráfico que miente sobre cuántas cosas distintas muestra.
- **Cuatro ranuras y no ocho.** Es lo que deja el arco frío: un quinto tono frío
  rompía el piso de visión normal, y uno cálido invadía el semáforo. Más de
  cuatro series se pliegan en «Otros» o se parten en múltiplos pequeños.
- **El tema oscuro tiene pasos propios**, no un volteo de los claros: la banda
  de luminosidad válida es más estrecha sobre fondo oscuro. Un aviso conocido y
  aceptado: el morado oscuro queda en 2,59:1, lo que obliga a etiqueta visible o
  vista de tabla — que es lo que los gráficos llevan igual.
- **La fase pasa a la rampa ordinal.** Planificación → ejecución → hypercare →
  cerrado es una secuencia, y cambiarle el orden cambia el significado, así que
  le toca un solo tono de claro a oscuro. Eso resolvió de paso el problema que
  abrió ADR-022: la quinta fase no necesita un quinto color, porque `cancelled`
  se sale de la secuencia y va al neutro.
- **La ruta crítica del Gantt deja el rojo** y pasa a borde y peso. Un grupo con
  tareas críticas no está en problemas, está en el camino largo: es énfasis
  estructural, no un estado.
- **La curva-S deja el verde.** Plan y real son dos versiones de la misma
  medida, no dos categorías; el verde insinuaba «va bien» cuando podía ir
  pésimo.
- **Dos copias inevitables, y un trinquete.** Los informes se dibujan en Python
  y la web en CSS. `test_adr023_paleta_graficos.py` comprueba que los tokens
  espejen el módulo, que ninguna ranura se acerque a un color del semáforo y que
  los hexes de Tailwind no vuelvan.

**Alternativas evaluadas:**

- **Extender la paleta de marca.** Gratis y coherente, pero el azul de marca es
  uno solo: no da cuatro identidades distinguibles sin inventar tonos, que es
  exactamente lo que el owner descartó.
- **Una paleta categórica estándar** (Tableau 10, Okabe-Ito). Están validadas y
  son buenas, pero las dos incluyen verde, ámbar y rojo — reintroducirían el
  choque que esta ADR existe para eliminar.
- **Dejar que el semáforo y las series compartan colores y desambiguar con
  etiqueta.** Es lo que había. La etiqueta funciona cuando se lee; el color se
  ve antes de leer, y ahí ya mintió.

---

> **ADR-024 a ADR-028 — registro retroactivo, 2026-08-05.** MCS `ARQ-02` exige
> que **toda** decisión irreversible esté en un ADR. Cinco de las 25 entradas de
> `docs/epics/DECISIONS.md` lo son —deshacerlas exige migrar datos productivos o
> rompe un contrato público— y vivían solo allí.
>
> Se promueven con su contenido original, añadiendo lo que el formato pide y el
> registro `DEC-` no tenía: consecuencias y requisitos MCS afectados. Las
> entradas `DEC-` **no se borran**: quedan con enlace al ADR, porque la relación
> de reemplazo es bidireccional (`CFG-18`, `DOC-08`).
>
> Las otras veinte se quedan como `DEC-`: son de proceso (1 US = 1 commit), de
> presentación (color del chrome) o de alcance de sprint. Revertirlas cuesta
> una decisión, no una migración.

## ADR-024 — La jerarquía organizativa vive en tablas, no en JSONB

**Estado:** ✅ Aceptada — 2026-04-20 · **Promueve:** DEC-003

**Contexto:**
La jerarquía del inquilino —unidades de negocio y departamentos— podía modelarse
embebida en `organizations.settings` como JSONB, o como tablas propias.

**Opciones consideradas:**

1. **JSONB embebido en `organizations`** — una tabla menos y esquema flexible.
   No admite clave foránea desde `programs` ni `projects`, obliga a filtrar por
   contenido del documento y deja el aislamiento por nivel sin punto de anclaje.
2. **Tablas `business_units` y `departments` con FK reales** — más tablas, y
   cada nivel nuevo es una migración.

**Decisión:**
Tablas con claves foráneas reales.

**Consecuencias:**

- `programs` y `projects` pueden apuntar al nivel exacto, y los filtros por
  jerarquía son índices en vez de recorridos de documento.
- **Irreversible en la práctica:** volver a JSONB exige migrar datos de todos
  los inquilinos y reescribir cada consulta que hoy usa la clave foránea.

**Requisitos MCS afectados:** ARQ-02, CFG-11.

---

## ADR-025 — RAID es una vista sobre `risks` e `issues`, no una tabla

**Estado:** ✅ Aceptada — 2026-04-20 · **Promueve:** DEC-007

**Contexto:**
RAID agrupa cuatro conceptos —riesgo, acción, incidencia y decisión— que el
esquema ya cubría con `risks` y con `issues` tipado.

**Opciones consideradas:**

1. **Tabla `raid` propia** — un solo sitio donde mirar. Duplica datos que ya
   existen y obliga a mantener dos verdades sincronizadas.
2. **Agrupar en la interfaz sobre las tablas existentes** — sin duplicación,
   pero la agrupación vive en el código de presentación.

**Decisión:**
RAID = `risks` más `issues` con tipos `action`, `incident` y `decision`. No se
crea tabla nueva; la agrupación es de interfaz.

**Consecuencias:**

- No hay dos verdades que puedan divergir, que es el modo de fallo que este tipo
  de tabla-resumen produce siempre.
- **Irreversible en la práctica:** crear la tabla después exigiría migrar y
  decidir cuál de las dos manda durante la transición.

**Requisitos MCS afectados:** ARQ-02, DAT-05.

---

## ADR-026 — El acta de constitución es una tabla, no un PDF guardado

**Estado:** ✅ Aceptada — 2026-04-20 · **Promueve:** DEC-008

**Contexto:**
El acta puede guardarse como documento generado —un PDF en almacenamiento— o
como datos estructurados de los que el PDF se deriva al pedirlo.

**Opciones consideradas:**

1. **PDF guardado** — fiel al momento de la firma y barato de servir. Queda
   congelado: cualquier cambio en los datos de gestión obliga a regenerarlo, y
   mientras tanto el documento miente.
2. **Tabla estructurada con generación bajo demanda** — el PDF siempre refleja
   el estado actual, a cambio de generarlo cada vez.

**Decisión:**
`project_charters` es una tabla; sus campos de gestión se sincronizan desde
`projects` y el PDF se genera bajo demanda.

**Consecuencias:**

- Los campos se editan sin regenerar nada, y el acta no puede quedar
  desactualizada respecto al proyecto.
- **Pendiente que esta decisión no resuelve:** si alguna vez hace falta el acta
  *tal como se firmó*, hará falta una línea base — que es justamente lo que D-6
  tiene abierto.
- **Irreversible en la práctica:** los datos estructurados no se reconstruyen
  desde PDF.

**Requisitos MCS afectados:** ARQ-02, DAT-05.

---

## ADR-027 — Dos espacios de rutas: `/pmo` para negocio, `/admin` para sistema

**Estado:** ✅ Aceptada — 2026-04-25 · **Promueve:** DEC-022

**Contexto:**
El panel de administración mezclaba recursos de negocio —proyectos, solicitudes,
RAID, minutas, informes— con gestión del sistema —usuarios, roles, configuración
del inquilino, IA, auditoría— todo bajo `/admin/*`. Eso confundía la navegación,
duplicaba entradas en la barra lateral y exponía rutas de edición a quien solo
necesitaba consultar.

**Opciones consideradas:**

1. **Mantener `/admin/*` y resolver por permisos** — cero migración de rutas.
   Deja la ruta diciendo «administración» a un usuario que solo mira su
   proyecto, y el problema de navegación intacto.
2. **Separar los espacios de nombres** — la ruta comunica a quién pertenece el
   recurso, a cambio de cambiar URL que la gente ya tiene guardadas.

**Decisión:**
`/pmo/*` para recursos de negocio, `/admin/*` para gestión del sistema.

**Consecuencias:**

- La ruta se vuelve información: se sabe de qué tipo es un recurso antes de
  cargarlo.
- **Es cambio de contrato público.** Un enlace guardado a la ruta vieja deja de
  funcionar, y a diferencia de un campo de API, un marcador no tiene ventana de
  compatibilidad que lo salve.

**Requisitos MCS afectados:** ARQ-02, CFG-10.

---

## ADR-028 — Los permisos del administrador son capacidades, no una matriz CRUD

**Estado:** ✅ Aceptada — 2026-04-25 · **Promueve:** DEC-024

**Contexto:**
DEC-020 dejó tres tipos de rol estáticos, pero el mapeo se expresó como matriz
`(rol × módulo × acción CRUD)` que nunca casó con los puntos de acceso reales.
Producción quedó con tres capas desalineadas y el resultado era que nadie podía
responder «¿qué puede hacer exactamente un administrador?» sin leer código.

**Opciones consideradas:**

1. **Arreglar la matriz** — familiar y sin cambio de modelo. El desajuste no era
   de datos sino de forma: las acciones CRUD no corresponden a lo que los
   puntos de acceso hacen, así que la matriz se volvía a desalinear.
2. **Capacidades nombradas** — se pierde la regularidad tabular, y hay que
   enumerar cada capacidad a mano.

**Decisión:**
Modelo basado en capacidades. `Admin` tiene exactamente cinco:
`tenant.manage`, `ai.configure`, `users.manage`, `organizations.delete` y las
que declare el inquilino.

**Consecuencias:**

- La pregunta «¿qué puede hacer un administrador?» se responde leyendo cinco
  nombres, y cada uno dice qué autoriza.
- **Irreversible en la práctica:** `tenant_permissions` guarda capacidades por
  inquilino; volver a la matriz exige traducir datos existentes con una
  correspondencia que no es uno a uno.

**Requisitos MCS afectados:** ARQ-02, SEG-04.

---

## ADR-029 — Exclusión parcial de MCS CFG-03 e INT-03: el administrador conserva la escritura directa

**Estado:** ❌ **RETIRADA el 2026-08-05, el mismo día que se aceptó.** El owner
activó `enforce_admins`, así que los dos requisitos se cumplen y no hay nada que
excluir. Se conserva el texto porque la relación de reemplazo es bidireccional
(`DOC-08`, `CFG-18`) y porque el razonamiento descartado sigue siendo útil: si
algún día vuelve la necesidad de una vía de integración urgente, aquí están las
opciones ya pesadas.

**Por qué se retiró tan rápido, que es lo interesante.** Esta ADR se apoyaba en
dos premisas y las dos cayeron en horas:

1. **Que el repositorio pasaría a privado**, lo que «retira del análisis a
   cualquier actor externo». El owner lo reconsideró al ver que los forks
   existentes **siguen públicos y se desvinculan**: hacer privado el repositorio
   no retira el código ya forkeado, así que el beneficio era menor que el
   anunciado.
2. **Que activar `enforce_admins` era costoso.** El intento inicial devolvió un
   404 —el comando llevaba `PUT` y ese subrecurso solo admite `POST`— y el error
   se leyó como una barrera que no existía. Con el método correcto fue un
   comando.

La lección no es sobre GitHub: **una exclusión que se acepta apoyada en un
obstáculo no verificado es una exclusión que no hacía falta.** El coste de
comprobar el obstáculo era un comando; el de excluir, dos requisitos N1 y un
flanco frente a cualquier auditor externo.

**Estado original (2026-08-05, vigente durante unas horas):** ✅ Aceptada ·
**Aprobada por:** el owner · **Requisitos excluidos:** `CFG-03` e `INT-03`,
solo en la parte que aplica al administrador · **Revisión:** 2027-02-05

**Contexto:**
`main` está protegida desde el 2026-08-05: exige solicitud de cambio, nueve
verificaciones automáticas en modo estricto, y prohíbe el `force-push` y el
borrado de rama. Lo que **no** está activado es `enforce_admins`, de modo que un
administrador —hoy, la única persona que trabaja en el repositorio— puede
escribir directo e integrar con verificaciones en rojo.

`CFG-03` exige la rama protegida «**sin escritura directa**» e `INT-03` que la
integración **no se permita** con verificaciones en fallo. Los dos son N1, y
§6.2 dice que un estado Parcial impide alcanzar su nivel.

El repositorio pasa además a **privado**, lo que retira del análisis a cualquier
actor externo.

**Opciones consideradas:**

1. **`enforce_admins: true`** — cierra los dos requisitos con un comando y sin
   coste de desarrollo. Se descarta porque elimina la única vía de integración
   urgente que tiene un equipo de una persona: si el CI se rompe por causa
   ajena —una acción de GitHub caída, un registro de paquetes inaccesible— no
   hay segunda persona que apruebe una excepción.
2. **Activarlo y desactivarlo puntualmente en la emergencia**
   (`gh api -X DELETE …/enforce_admins`, actuar, reactivar). Mantiene el control
   por defecto y deja rastro del momento en que se levantó, que es una postura
   de riesgo distinta de «nunca activado». Se descarta por el owner: en la
   práctica la emergencia llega cuando hay menos tiempo para ceremonias, y un
   control que se desactiva a mano acaba desactivado.
3. **Exclusión registrada** — la que se adopta.

**Decisión:**
`enforce_admins` se queda en `false`. Se excluye la parte de `CFG-03` e `INT-03`
que exige impedir la escritura directa **al administrador**; el resto de ambos
requisitos —solicitud de cambio obligatoria, verificaciones exigidas, sin
`force-push` ni borrado de rama— se cumple y se mantiene.

**Riesgo aceptado:**

- **Un error del owner puede llegar a `main` sin pasar por el CI.** Es el riesgo
  principal, y el repositorio privado **no lo reduce**: el actor es interno.
- Una escritura directa a la rama principal por descuido no encuentra freno. Lo
  mitiga en parte `guard_irreversible.py`, que la bloquea desde una sesión de
  Claude —pero no desde una terminal del owner—.
- **Lo que sí retira el repositorio privado** es el actor externo: nadie ajeno
  puede intentar escribir. Eso reduce la superficie, no el riesgo aceptado.

**Consecuencias:**

- Los dos requisitos pasan a **EXCLUIDO**, el mismo tratamiento que `ARQ-03`
  recibió en ADR-018.
- **Salvedad que conviene no perder de vista.** El marco permite excluir un
  requisito aplicable (§1.3) pero §6.2 solo concede el nivel a los requisitos
  en estado *Conforme* o *No aplicable*, y un requisito excluido **no es lo
  mismo que uno que no aplica**: `CFG-03` aplica a este producto, que tiene rama
  principal y tiene CI. Se sigue el precedente de ADR-018 y se cuenta como no
  bloqueante, pero **un auditor externo podría negarse a conceder N1 con dos
  controles de integridad excluidos**, y estaría dentro de su derecho. Si N1 va
  a presentarse a un tercero, esta exclusión es lo primero que va a mirar.
- El disparador de revisión no es una fecha arbitraria: **el día que entre una
  segunda persona al repositorio**, «administrador» deja de significar «el
  owner» y la justificación de esta ADR desaparece entera.

**Requisitos MCS afectados:** CFG-03, INT-03, GOB-02 (que exige este registro).

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

---

## ADR-030 — `task_load_thresholds.amber_max` pasa a `yellow_max`

**Estado:** ✅ Aceptada — 2026-08-06 (owner)
**Requisitos MCS afectados:** DAT-06

**Contexto:**
El último resto de `amber` en el producto. El glosario veta el término desde
D-1 y la migración 0091 convirtió los **valores** de salud (`amber` → `yellow`);
lo que sobrevivió fue esta **llave**, dentro de `settings.report_builder` de la
tabla `tenants`, describiendo el mismo concepto con la palabra retirada.

No era cosmético. El umbral colorea la carga de recursos con el vocabulario del
semáforo, así que el valor vivía en `yellow` y su corte en `amber_max`: quien
leyera el código de colorización tenía que traducir mentalmente en cada paso, y
ahí es donde se cuelan los errores de asignación de color. Es además el motivo
por el que `DAT-06` no cerró con la Ola 2 — el plan lo dejó anotado como
«cambio de contrato», no como olvido.

La dificultad es que **vive en datos de inquilinos reales**, no en una columna:
renombrarlo es un cambio de contrato, no un `sed`.

**Decisión:**
Renombrar a `yellow_max` con el mismo molde que `wbs` → `wbs_code` (ADR-020),
que es el precedente aprobado para esta clase de cambio:

1. **Migración 0101** reescribe la llave en los datos existentes. Opera sobre el
   JSON en Python y con SQL portable, no con los operadores de Postgres: la
   suite corre sobre SQLite, y una migración que solo sabe correr en un motor se
   descubre en producción.
2. **Ventana de compatibilidad** en `core/compatibilidad.py`. El API sigue
   aceptando `amber_max` a la entrada **y a la lectura** —un inquilino
   restaurado de una copia anterior al despliegue lo traería—, y cada uso deja
   rastro en `compat.nombre_viejo`.
3. **Lo que se guarda es siempre `yellow_max`.** Si al guardar volviera a
   escribir el nombre viejo, la migración se desharía sola con el primer cambio
   de ajustes.
4. La **etiqueta de la interfaz** deja de decir «Ámbar». El sinónimo no estaba
   solo en una variable: estaba en el formulario de ajustes y en un `aria-label`
   del panel de organizaciones.

**Consecuencias positivas:**
- `DAT-06` cierra: cero `amber` en código, con trinquete que mira el árbol.
- Un vocabulario y no dos para el mismo corte del semáforo.

**Consecuencias negativas:**
- Una ventana más que cerrar. Son cuatro (`phase=support`,
  `portfolio_function`, `wbs`, `amber_max`), y se cierran con dato: a los dos
  meses se mira el contador.
- La migración toca filas de `tenants`. Solo las que tienen el bloque — una
  migración de datos que reescribe filas que no le incumben ensucia el
  `updated_at` de medio producto.

**Alternativas consideradas:**
- **Dejarlo.** Es lo que el plan proponía hasta que el owner decidió lo
  contrario. Coste: `DAT-06` sigue PARCIAL y bloquea N1 por una sola llave.
- **Aceptar los dos nombres para siempre**, sin migrar. Convierte la ventana en
  permanente, que es deuda con apariencia de solución.

---

## ADR-031 — Postura de infraestructura: secretos, construcción y alcance de pruebas

**Estado:** ✅ Aceptada — 2026-08-06
**Contexto:**
Tres requisitos de MCS —`SEG-02` (almacén de secretos), `SUM-01` (dónde se
construye el artefacto) y `DEV-02`/`DEV-03` (estrategia de pruebas)— estaban
abiertos no por falta de trabajo sino por falta de postura declarada. El marco
no exige una solución concreta; exige que la elegida esté escrita. Sin eso, la
misma configuración se lee como conforme o como carencia según quién audite.

**Decisión:**

**Secretos: variables de entorno de Railway.** No se adopta un almacén dedicado
adicional (Vault, Secrets Manager). El almacén de variables de Railway es un
almacén dedicado: vive fuera del repositorio, tiene control de acceso propio y
no se versiona. Lo que `SEG-02` prohíbe es el secreto **en el repositorio**, y
eso lo verifica `gitleaks` sobre el historial completo en cada PR —478 commits
al declarar esto, sin fugas—.

**Construcción: Railway desde la rama.** No se produce un artefacto en la
canalización de CI para desplegarlo después. `SUM-01` exige que lo desplegado se
construya en la canalización automática y **nunca en equipos locales**; Railway
construyendo desde la rama es canalización automática. Nadie despliega desde su
máquina, y esa es la propiedad que el requisito protege.

**Pruebas: alcance reducido, declarado.** Se sostiene la suite de API —unitaria
y de integración, sobre SQLite en memoria— y **no** se abre frente de pruebas de
frontend ni de extremo a extremo. Hoy hay **cero** pruebas de web y se acepta a
sabiendas.

**Consecuencias:**

- Un compromiso de la cuenta de Railway expone todos los secretos a la vez. No
  hay rotación automática ni registro de acceso por secreto. Se acepta con un
  solo operador; se reevalúa al entrar la segunda persona.
- Sin artefacto inmutable, un despliegue no es reproducible bit a bit: dos
  construcciones del mismo commit pueden diferir si cambian las dependencias
  base. Mitigado por los ficheros de bloqueo, no eliminado.
- **Un fallo de frontend llega a producción sin que nada lo detenga.** Es la
  consecuencia más cara de las tres y la más fácil de olvidar: la suite verde
  no dice nada sobre la web. Los gates que sí cubren frontend son `web-build`,
  `web-typecheck`, `contraste-wcag` y el de tokens — ninguno ejecuta la interfaz.
- `DEV-03` pide pruebas separadas por nivel. Con alcance reducido, los niveles
  declarados son **unitaria** y **de integración**; el de extremo a extremo se
  declara ausente en vez de fingirse.

**Alternativas:**

- *Almacén dedicado externo:* correcto a mayor escala; hoy añade una dependencia
  y un modo de fallo para un equipo de una persona.
- *Artefacto en CI + despliegue de imagen:* la forma canónica, y la que habrá
  que adoptar si el despliegue deja de ser de un solo servicio. Cuesta
  reescribir la canalización y añade registro de imágenes.
- *Abrir pruebas de frontend ahora:* es el frente correcto a medio plazo, pero
  compite con 24 requisitos abiertos y no es el más barato.

**Revisión:** al entrar una segunda persona al repositorio, o al primer
incidente de producción originado en el frontend.

---

## ADR-032 — Contraseñas: 8 caracteres con reglas de composición

**Fecha:** 2026-08-07 · **Estado:** aceptada · **Decide:** owner

**Contexto.** El mapeo completo contra OWASP ASVS 4.0.3 L1 (SEG-01, 2026-08-07)
sacó a la luz que la política de contraseñas del producto **contradice a ASVS en
dos controles a la vez, y en direcciones opuestas**:

- `2.1.1` pide un mínimo de **12** caracteres; el producto pide 8.
- `2.1.9` pide que **NO haya reglas de composición**; el producto exige mayúscula,
  dígito y símbolo.

No es un descuido acumulado: las dos cosas van juntas en la postura de ASVS,
que viene de NIST 800-63b. El argumento de NIST es que las reglas de
composición producen contraseñas **predecibles** —«Password1!» las cumple
todas— y que la longitud es lo que de verdad encarece adivinarlas. Por eso
piden más longitud y ninguna regla.

**Decisión.** Se mantiene **8 caracteres con las tres reglas**. Decisión
explícita del owner el 2026-08-07, con el contraste de ASVS delante.

**Consecuencia, escrita.** El producto **no cumple** `2.1.1` ni `2.1.9`, y así
figura en `docs/conformidad/asvs-l1.yaml`: estado **ACEPTADO**, no CUMPLE. Un
residual aceptado y un control cumplido no se pintan igual — es la misma
distinción que se hizo con `enforce_admins` en su momento, y el motivo es que
un auditor externo tiene derecho a ver la diferencia sin preguntar.

Lo que se acepta en concreto: una contraseña de 8 caracteres es adivinable por
fuerza bruta con recursos modestos si el atacante consigue los hashes. Lo que
lo contiene hoy no es la política sino **bcrypt con coste configurable** y el
**retardo creciente del inicio de sesión** (escenario E-4: desde el intento 5,
base 2 s, tope 300 s, y 30 fallos por hora y por IP).

**Lo que sí cambió a raíz del mismo análisis**, porque era defecto y no
postura: `2.1.2` y `2.1.3`. bcrypt **trunca a 72 bytes en silencio**, así que
dos contraseñas distintas de 103 y 108 caracteres que compartieran los primeros
72 abrían la misma cuenta — comprobado, no supuesto. El esquema pasa a
`bcrypt_sha256`, que resume antes de hashear y no tiene longitud que truncar;
`bcrypt` se queda **deprecado y no retirado**, así que los hashes existentes
siguen verificando y se reescriben al esquema nuevo la próxima vez que su dueño
inicia sesión. Y se declara un máximo real de 128 caracteres: «sin máximo»
sonaba generoso mientras por detrás había uno de 72 sin avisar.

**Alternativas:**

- *Adoptar la postura de ASVS (12 sin reglas):* es la recomendación vigente y
  la mejor por evidencia. Cambia lo que se le pide a cada persona al
  registrarse y a las que ya tienen cuenta; el owner decide no hacerlo ahora.
- *Subir solo el mínimo a 12 y conservar las reglas:* la peor de las tres.
  Suma la fricción de las reglas al coste de la longitud sin obtener la ventaja
  que NIST atribuye a quitarlas.

**Revisión:** ante el primer incidente de credenciales, o si entra
autenticación de segundo factor (`4.3.1`), que cambia el peso de la contraseña
en el conjunto.

---

## ADR-033 — Los tokens de sesión viven en cookies `__Host-`, no en `localStorage`

**Fecha:** 2026-08-07 · **Estado:** aceptada · **Decide:** owner

**Contexto.** El mapeo ASVS L1 (SEG-01) dejó tres huecos sobre el mismo asunto
—dónde guarda el navegador la sesión— y conviene decidirlos juntos porque una
respuesta parcial no cierra ninguno:

- `3.2.3` — los tokens de sesión se guardan «using secure methods». El de
  acceso vivía en `localStorage`.
- `8.2.2` — nada sensible en `localStorage`/`sessionStorage`. Ahí vivían el
  token de acceso **y** el perfil del usuario.
- `3.4.4` — las cookies de sesión usan el prefijo `__Host-`. La de refresco no
  lo usaba.

Lo que hacen `3.2.3` y `8.2.2` es cerrar la puerta al robo de sesión por
script: cualquier XSS —propio o de una dependencia— lee `localStorage` con una
línea. `HttpOnly` no hace mejor al token, hace que el script no pueda leerlo.

`3.4.4` cierra otra puerta distinta y con frecuencia olvidada: sin el prefijo,
**un subdominio puede sobrescribir la cookie del dominio padre**. Un panel de un
proveedor colgado de `*.pmo-aas.com`, o un blog, bastan para plantar una cookie
de sesión ajena. El prefijo lo impide porque lo impone el navegador, no
nosotros.

**Decisión.**

1. El token de acceso deja `localStorage` y pasa a cookie `HttpOnly`,
   `SameSite=Strict`, `Secure`, `Path=/`, sin `Domain`.
2. Las dos cookies de sesión —acceso y refresco— llevan prefijo `__Host-` allí
   donde puede emitirse `Secure`, es decir en producción. En desarrollo se
   sirve por HTTP y una cookie `__Host-` **no se guardaría**: el nombre sigue la
   misma condición que ya gobernaba `secure=`.
3. El perfil del usuario deja de persistirse en `localStorage`. Se pide a
   `/auth/me` al cargar y vive en memoria.
4. Queda en `localStorage` lo que no es sensible ni autoriza nada: el tema
   claro/oscuro, el idioma y el inquilino activo de un superadministrador —que
   el servidor vuelve a comprobar en cada petición y por tanto no es una
   credencial—.

**Consecuencias.**

- **Todas las sesiones vivas se cierran al desplegar.** El token de acceso que
  el navegador tiene en `localStorage` deja de enviarse, y no hay cookie hasta
  el siguiente inicio de sesión. Es coste de una vez y no hay forma de evitarlo:
  migrarlo «en caliente» exigiría que el servidor leyera el token del sitio
  inseguro para reemitirlo, que es justo lo que se está quitando.
- Con `SameSite=Strict` el API deja de ser consumible desde otro origen por el
  navegador. Es lo que se quiere; la web y el API se sirven bajo el mismo sitio.
- La cabecera `Authorization` **se sigue aceptando** para el SDK y las
  integraciones servidor a servidor, que no son un navegador y no tienen el
  problema que esto resuelve.
- Al no poder leer el token, el cliente web no puede inspeccionar su expiración:
  la sesión caducada se descubre con un 401, que es como debía descubrirse.

**Alternativas:**

- *Dejar el token en `localStorage` y confiar en no tener XSS.* Es la postura
  de hoy. El coste de equivocarse es la sesión completa de cada usuario, y la
  superficie incluye toda dependencia de npm que entre en el paquete.
- *`sessionStorage` en vez de `localStorage`.* Reduce la ventana a la pestaña,
  no la cierra: un script inyectado la lee igual. `8.2.2` nombra las dos.
- *Cookie sin prefijo `__Host-`.* Es lo que había. Deja abierta la
  sobrescritura desde un subdominio, que es un ataque que ninguna comprobación
  del servidor puede detectar — la cookie que llega es sintácticamente
  perfecta.

**Ventana de compatibilidad.** Al desplegar, los navegadores con sesión previa
traen la cookie de refresco vieja (sin prefijo, `Path=/api/v1/auth`). Se acepta
a la lectura y se anota (`compat.nombre_viejo`, clave `cookie:refresh_token`);
al cerrar sesión se borran todas las formas, porque una cookie solo se borra
desde el `Path` con que se creó. Se cierra con dato a los dos meses, como las
demás.

**Revisión:** si el API pasa a servirse desde un sitio distinto al de la web,
`SameSite=Strict` deja de ser viable y hay que rehacer la decisión entera.

---

## ADR-034 — La supresión de datos personales anonimiza; no borra

**Fecha:** 2026-08-07 · **Estado:** aceptada · **Decide:** owner

**Contexto.** `8.3.2` del mapeo ASVS pide «a method to remove **or** export
their data on demand», y `05-DATOS-PERSONALES.md` §5 ya declaraba la falta de
procedimiento como «la carencia más seria de este inventario». Al ir a
construirlo aparece el choque: **borrar de verdad a una persona rompe dos cosas
que este producto necesita**.

- `audit_log` es de **solo anexado por diseño** (AM-08, con trinquete propio).
  Es lo que permite reconstruir qué pasó ante un error o una disputa, y un
  registro que se puede borrar por partes deja de servir para eso.
- El historial de un proyecto es **dato del inquilino, no de la persona**. Quién
  aprobó un cambio de alcance en marzo es información de la organización que
  paga por la herramienta. Borrarla deja huecos en la trazabilidad de un tercero
  que no ha pedido nada.

**Decisión.** Se **anonimiza**: las filas se quedan y dejan de apuntar a nadie.
Nombre, correo, usuario y preferencias se sustituyen por un seudónimo estable y
no reversible, la cuenta queda inactiva, y el hash de contraseña se descarta. La
exportación va **antes** en la pantalla, porque una vez anonimizado no hay forma
de recuperar la copia.

Es lo estándar en SaaS B2B y no un atajo: el RGPD (considerando 26) sostiene que
un dato que ya no identifica a nadie deja de ser dato personal, y su art. 17.3
reconoce que el derecho de supresión cede ante obligaciones de conservación. Es
lo que hacen Atlassian, GitLab y Notion.

**Consecuencias.**

- El derecho se atiende sin romper la trazabilidad del inquilino, que es lo que
  hacía irreconciliables las dos exigencias.
- **El texto libre no se toca, y va escrito.** Una minuta que dice «lo comenta
  Ana en la reunión» sigue diciéndolo. Barrerlo exigiría recorrer todo el
  contenido de la plataforma con coincidencia difusa y decidir a mano cada
  acierto. Se declara como límite —en el propio archivo exportado y en
  `05-DATOS-PERSONALES.md`— en vez de fingir que no existe.
- El seudónimo es **estable**: dos filas del mismo usuario anonimizado siguen
  siendo del mismo, o el historial de un proyecto se vuelve incoherente. Y **no
  reversible**: si se pudiera deshacer no sería anonimización sino ofuscación, y
  el dato seguiría siendo personal. Por eso es un resumen y no el `user_id`, que
  aparece en otras tablas y permitiría volver a cruzar.
- Es irreversible, así que exige re-teclear el correo — el mismo patrón que el
  borrado permanente de entidades.

**Alternativas:**

- *Borrado físico en cascada.* Lo que la palabra «suprimir» sugiere. Choca de
  frente con `audit_log` y deja al inquilino con un historial roto que nadie le
  pidió romper.
- *Marcar la cuenta como inactiva y nada más.* Es lo que ya hacía el producto, y
  no es supresión: el correo y el nombre siguen ahí.
- *Exportación sola.* El control dice «remove **or** export», así que
  técnicamente bastaría. Deja abierta la carencia que `05-DATOS-PERSONALES.md`
  declaró como la más seria, que era justamente la de supresión.

**Revisión:** si entra un requisito contractual de borrado físico, o si el
inventario de datos personales suma una tabla que este procedimiento no cubra.

---

## ADR-035 — El segundo factor de administración es un código por correo

**Fecha:** 2026-08-07 · **Estado:** aceptada · **Decide:** owner

**Contexto.** `4.3.1` del mapeo ASVS pide segundo factor para las interfaces de
administración, y el producto no tenía ninguno. Las opciones reales eran TOTP
—`cryptography` ya lo trae, así que tampoco costaba una dependencia— o un código
por correo con la infraestructura de Resend que ya existe.

**Decisión.** **Código de seis dígitos por correo.** Lo pide el owner por dos
motivos prácticos: no hay que enrolar a nadie ni pedirle que instale una
aplicación, y reutiliza un canal que el producto ya usa para avisos de
seguridad.

Se exige a superadministradores y a cuentas con rol equivalente a administrador.
A un usuario normal no se le pide: no alcanza ninguna interfaz de administración
y sería fricción a cambio de nada. El interruptor `ADMIN_MFA_REQUIRED` viene
**encendido** — un control cuyo defecto es «apagado» está apagado en producción
el día que a alguien se le olvida encenderlo.

**Lo que esto cierra.** `4.3.1`, y de paso cuatro controles que estaban como NO
APLICA porque no había factor fuera de banda: `2.2.2` (el correo se usa como
verificación **secundaria**, nunca en lugar de la contraseña), `2.7.2` (caduca a
los diez minutos, literal), `2.7.3` (un solo uso y atado al desafío que lo pidió)
y `2.7.4` (canal independiente del navegador).

**Lo que esto NO cierra, y por eso `2.7.1` queda ACEPTADO.** El correo es un
factor **débil**: NIST 800-63B §5.1.3.1 dice que no debe usarse para
autenticación fuera de banda porque no demuestra posesión de un dispositivo —
quien controle el buzón, o el proveedor de correo, completa el segundo paso.
`2.7.1` pide ofrecer primero una alternativa más fuerte, y aquí no hay ninguna
que ofrecer.

Figura **ACEPTADO** y no CUMPLE, igual que se hizo con la política de
contraseñas en ADR-032. Lo que se acepta en concreto: si alguien tiene la
contraseña **y** acceso al correo de la persona, el segundo factor no lo
detiene. Lo que sí detiene —y es la amenaza realista— es una contraseña
reutilizada que aparece en una filtración: el atacante necesita además la cuenta
de correo, que casi nunca tiene.

**Consecuencias.**

- Entrar al panel pasa a ser dos pasos para ti y para cualquier administrador.
  El desbloqueo por inactividad de una cuenta de administración también manda a
  `/login`: si se saltara el factor, bastaría con esperar a que un administrador
  dejara la sesión bloqueada para entrar solo con la contraseña.
- **Si Resend está caído, un administrador no puede entrar.** Es la consecuencia
  incómoda de que el factor viaje por correo, y es preferible a la alternativa —
  dejar pasar sin segundo factor porque el correo no salió sería un control que
  se desactiva solo justo cuando algo va mal.
- Los intentos por desafío están acotados a cinco. Seis dígitos son un millón de
  combinaciones y sin freno se prueban enteras en minutos: el límite no es un
  detalle, es lo que hace que el factor valga algo.

**Alternativas:**

- *TOTP.* Más fuerte, cierra `2.7.1` sin residual y no depende de que el correo
  llegue. Cuesta enrolamiento con QR, códigos de recuperación y una pantalla
  más — y deja fuera a quien pierde el teléfono hasta que alguien le ayude.
- *Ambos, ofreciendo TOTP primero.* Es lo que `2.7.1` pide literalmente y la
  respuesta correcta a medio plazo. Se descarta ahora por alcance, no por
  postura.

### §Ventana — el código se pide una vez por equipo, no en cada entrada

**Decisión del owner, 2026-08-07**, tras probar la primera versión: pedir el
código en **cada** inicio de sesión es insoportable, y un control insoportable
acaba desactivado. Se recuerda el equipo **treinta días**.

Treinta es el techo de lo razonable y coincide con lo que ofrecen Google y
GitHub. Lo que sostiene ese número no es el número: son las tres garantías de
abajo. Sin ellas, treinta días sería demasiado; con ellas, **la ventana la
cierra la propia persona el día que sospecha**, cambiando su contraseña.

Es lo que hacen Google, GitHub y Microsoft, y no es una concesión: es lo que
mantiene el segundo factor encendido.

**Dentro de la ventana siguen siendo dos factores.** La cookie
`__Host-dispositivo` es un secreto de 256 bits que solo tiene ese navegador,
`HttpOnly` para que ningún guion lo lea — «algo que tienes»—, y la contraseña
sigue haciendo falta. Cambia el **soporte** del segundo factor, no su
existencia. Por eso `4.3.1` sigue CUMPLE.

Tres cosas sostienen que eso sea cierto, y las tres tienen prueba propia:

1. **La cookie está atada a la cuenta.** La comprobación exige que el resumen
   **y** el `user_id` coincidan. Sin lo segundo, un administrador con equipo
   recordado se saltaría el segundo factor de *cualquier otra* cuenta desde ese
   navegador — y el flujo seguiría funcionando igual, así que nadie lo vería.
2. **Cambiar la contraseña revoca todos los equipos.** Es la acción de «creo que
   me han entrado»; si la confianza sobreviviera, quien hubiera entrado una vez
   seguiría entrando con la contraseña nueva y sin código.
3. **Recordar un equipo nuevo manda un correo.** Si llega y no fuiste tú,
   alguien tiene tu contraseña *y* tu correo y acaba de conseguir un mes de
   entradas sin código. Es lo primero que hay que saber, y por eso este aviso
   es la garantía que más pesa cuanto más larga es la ventana.

La casilla viene **marcada** —es el comportamiento que se pidió— y se puede
desmarcar en un equipo prestado, donde recordar sería peor que la molestia que
ahorra.

**Lo que se acepta a cambio, y va escrito:** quien tenga acceso físico a un
equipo recordado y sepa la contraseña entra sin pasar por el correo durante los
treinta días. Contra eso están el bloqueo por inactividad, la revocación al cambiar
la contraseña y el aviso del equipo nuevo. Y en la auditoría queda anotado con
qué se entró (`mfa: dispositivo_confiable` frente a `mfa: email_otp`): sin ese
detalle, una entrada con segundo factor y una sin él serían la misma línea.

**Revisión:** al primer incidente de correo comprometido, o cuando el número de
administradores haga que enrolar TOTP salga a cuenta.

---

## ADR-036 — Se cierra el programa ASVS L1 y se aceptan los tres residuales

**Fecha:** 2026-08-07 · **Estado:** aceptada · **Decide:** owner

**Contexto.** El mapeo ASVS 4.0.3 L1 se midió entero el 2026-08-07 y sacó quince
huecos. Los quince se cerraron el mismo día (PR #584/#585). Queda:

    116 CUMPLE · 8 NO APLICA · 3 ACEPTADO · 0 HUECO

`SEG-01` sigue **PARCIAL** en el registro, porque tres controles L1 aplicables no
se cumplen, y MCS-CORE §6.2 no da crédito parcial. Llevarlo a CONFORME no era
trabajo pendiente: era **revertir dos decisiones ya tomadas**.

**Y hay un dato que cambia el marco:** *no hay auditoría externa*. Nadie va a
pedir este expediente. El trabajo se hizo para subir la calidad de la
plataforma, no para pasar una revisión.

**Decisión.** El owner **cierra el programa** y **acepta los tres residuales**.
N1 deja de ser un objetivo perseguido. El expediente queda como está.

**Qué se acepta, en concreto** — no «tres controles», sino esto:

1. **`2.1.1` + `2.1.9` (ADR-032).** Una contraseña de 8 caracteres es adivinable
   por fuerza bruta con recursos modestos **si alguien consigue los hashes**.
   Lo que lo contiene no es la política sino `bcrypt_sha256` con coste
   configurable, el retardo creciente del inicio de sesión, el límite por IP, y
   —desde esta ronda— el contraste contra 37.970 contraseñas filtradas que
   además pasan la política.
2. **`2.7.1` (ADR-035).** Si alguien tiene la contraseña de un administrador
   **y** acceso a su correo, el segundo factor no lo detiene. Lo que sí detiene,
   que es la amenaza realista, es una contraseña reutilizada que aparece en una
   filtración.

**Consecuencias.**

- **`SEG-01` se queda PARCIAL, y no se toca.** Marcarlo CONFORME sería la
  conformidad de papel que este expediente lleva siete recuentos evitando. El
  producto no cumple tres controles L1 aplicables; que la decisión sea
  deliberada no lo convierte en cumplimiento.
- **MCS se queda en N0**, con un solo requisito en contra. Es una postura, no un
  descuido, y ahora está escrita.
- `registro_conformidad.py` seguirá diciendo `BLOQUEAN N1 hoy: 1 ['SEG-01']`.
  **Es correcto y se deja así**: el derivador mide, no opina sobre si el nivel
  se persigue.

**Lo que NO se apaga, y es lo que más importa de esta decisión.**

Sin auditoría externa, la tentación es aflojar el aparato: los trinquetes, la
distinción `ACEPTADO`/`CUMPLE`, el techo de contexto, la verificación por
mutación. **Se quedan todos encendidos**, y el motivo es exactamente el que
acaba de darse: si nadie mira desde fuera, lo único que impide que la calidad se
degrade es que el CI lo haga desde dentro.

De hecho esta ronda demostró que hacen falta más que antes: **tres de los quince
controles tenían evidencia escrita a mano que no era cierta** —`10.3.2` decía
que no se cargaban recursos externos y cargaba tres—, y eso solo se descubre
cuando algo comprueba en vez de recordar.

En concreto siguen en el CI, y siguen siendo bloqueantes:

- `check_asvs.py` con tope de huecos en **0**.
- `check_subrecursos.py` y `check_password_input.py`, nacidos de esta ronda.
- El techo de contexto, el modelo de amenazas, la matriz de permisos, las
  magnitudes, el ER generado y los mensajes de error.

**Alternativas:**

- *Perseguir N1.* Exige contraseñas de 12 sin reglas de composición y TOTP
  ofrecido antes que el correo. Las dos son cambios que la gente nota, a cambio
  de un nivel que nadie va a pedir. Se descarta por eso, no por dificultad.
- *Declarar `SEG-01` CONFORME y cerrar el nivel.* Sería mentir en el propio
  expediente, y el barrido lo impide: un `ACEPTADO` sin ADR no pasa.

**Revisión:** si aparece un cliente que exija certificación, si entra un
requisito contractual de seguridad, o ante el primer incidente de credenciales.
Entonces esta decisión vuelve a la mesa con los tres residuales ya nombrados,
que es exactamente el valor de haberlos escrito.
