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
`docs/conformidad/2026-08-04-mcs-r1.md`) dio el número: **54 de los 68 módulos de
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

**Estado:** ✅ Aceptada — 2026-08-05 · **Implementación:** US propia, sin abrir

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
