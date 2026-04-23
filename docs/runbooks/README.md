# Runbooks — Guías de Setup

**Última actualización:** 2026-04-23 (post-v1.1, BUG-027)

Este directorio centraliza los runbooks operativos para desplegar y operar
**PMO·aaS** en producción. Cada runbook es autónomo: contiene el checklist
de validación y troubleshooting necesario para ese servicio.

> **Desde v1.1 (DEC-017):** la IA ya no usa cascada global (Ollama → Gemini →
> Claude). El modelo activo es **3 modos por-tenant** — `disabled`,
> `platform` (Groq hosteado por la plataforma), `byo` (proveedor del tenant:
> OpenAI / Claude / Gemini / Perplexity). Los runbooks viejos de Ollama /
> Gemini / Claude / local-model fueron archivados en
> [`docs/archive/runbooks-ai-legacy/`](../archive/runbooks-ai-legacy/).

---

## 📋 Checklist de Deploy v1.0 (mínimo requerido)

Marca cada bloque conforme lo completes. **El producto está listo para produción
cuando los 6 bloques estén ✅**.

### ✅ 1. Railway — servicios, env vars, plugins

**Runbooks:**
- [`railway/SETUP.md`](./railway/SETUP.md) — configuración de env vars por servicio
- [`railway/DEPLOYMENT.md`](./railway/DEPLOYMENT.md) — arquitectura, CI/CD, migraciones

**Tareas:**
- [ ] Crear proyecto `pmo-aas` en Railway con 3 servicios (api, worker, web)
- [ ] Plugin Postgres 16 + Plugin Redis 7 creados
- [ ] Variables de entorno configuradas (JWT secrets, Gemini key, Anthropic key, etc.)
- [ ] Auto-deploy ON en rama `main`
- [ ] Health checks respondiendo: `/health` en api, `/api/health` en web
- [ ] Logs accesibles vía `railway logs --tail`

**Checkpoint:** `curl https://<web>.up.railway.app/api/health` devuelve 200

---

### ✅ 2. Networking — Tailscale (opcional, legacy Ollama BYO)

**Runbook activo:** [`networking/tailscale-setup.md`](./networking/tailscale-setup.md)

> **Nota (DEC-017, 2026-04-22):** la plataforma ya **no requiere** Tailscale
> para operar la IA. El modo `platform` usa Groq hosteado (HTTPS público,
> sin tunneling). Este bloque sólo aplica si un tenant legacy sigue con
> Ollama + Tailscale como BYO propio. Ver
> [`docs/archive/runbooks-ai-legacy/local-ollama-setup.md`](../archive/runbooks-ai-legacy/local-ollama-setup.md)
> para el setup original.

**Tareas (sólo tenants legacy Ollama):**
- [ ] Ollama instalado en PC local con modelo propio
- [ ] Tailscale + ACL configurados (ver runbook archivado)
- [ ] `TS_AUTHKEY` en Railway `worker`

**Checkpoint:** Worker Railway resuelve MagicDNS y conecta a Ollama sin timeout

---

### ✅ 3. DNS — Cloudflare + subdomios Railway + HostGator landing

**Runbooks:**
- [`infra/dns-routing.md`](./infra/dns-routing.md) — Cloudflare, subdominios, apex

**Tareas:**
- [ ] Dominio `pmo-aas.com` nameservers apuntan a Cloudflare
- [ ] Custom Domain `app.pmo-aas.com` agregado a servicio `web` Railway
- [ ] Custom Domain `api.pmo-aas.com` agregado a servicio `api` Railway
- [ ] CNAME en Cloudflare: `app` → Railway web (DNS only), `api` → Railway api (DNS only)
- [ ] Registros DNS de Resend (SPF, DKIM) agregados a Cloudflare
- [ ] CNAME `www` → HostGator IP con proxy Cloudflare (naranja, Full strict SSL)
- [ ] Redirect Rule apex (`pmo-aas.com`) → `app.pmo-aas.com` (301) creado
- [ ] `https://app.pmo-aas.com` y `https://api.pmo-aas.com` sirven con cert válido

**Checkpoint:** `dig app.pmo-aas.com` resuelve a Railway; cert Let's Encrypt válido

---

### ✅ 4. Email — Resend + dominio verificado

**Runbooks:**
- [`email/resend-setup.md`](./email/resend-setup.md) — Resend, dominios, API key

**Tareas:**
- [ ] Cuenta Resend creada (free tier)
- [ ] Dominio `pmo-aas.com` agregado a Resend
- [ ] DNS records (SPF, DKIM) verificados en Resend dashboard
- [ ] API key `re_xxx` generada con alcance "Sending access"
- [ ] Variables en Railway `worker`: `RESEND_API_KEY`, `RESEND_FROM`, `APP_BASE_URL`
- [ ] Smoke test: crear solicitud, aprobar, verificar email recibido

**Checkpoint:** Email de prueba llega a inbox (no spam)

---

### ✅ 5. IA — Groq (platform) + BYO opcional por tenant

**Runbooks activos:**
- [`ai/groq-setup.md`](./ai/groq-setup.md) — **Obligatorio.** Habilitar Groq como IA base (modo `platform`).
- [`ai/byo-setup.md`](./ai/byo-setup.md) — Opcional por tenant: conectar OpenAI / Claude / Gemini / Perplexity.

**Runbooks archivados (cascada legacy, pre-DEC-017):**
Ver [`docs/archive/runbooks-ai-legacy/`](../archive/runbooks-ai-legacy/) —
Ollama tailnet, Gemini como fallback, Claude como fallback premium.

**Tareas v1.1+:**
- [ ] `AI_SECRETS_FERNET_KEY` en Railway (api + worker) — cifra la key de Groq y las BYO.
- [ ] Cuenta Groq creada + `GROQ_API_KEY` pegada en `/superadmin/ai` → Guardar.
- [ ] Modelo Groq = `llama-3.3-70b-versatile` (3.1 deprecado).
- [ ] "Probar conexión" en `/superadmin/ai` devuelve OK.
- [ ] `AI_BYO_ENABLED=1` en Railway **sólo cuando** quieras habilitar el wizard BYO
      para los tenants. Default off (DEC-019).
- [ ] Smoke test: tenant en modo `platform` genera minuta IA sin error.

**Checkpoint:** `/superadmin/ai` muestra `Groq · Configurado` y dashboard de uso > 0 requests.

---

### ✅ 6. Landing — HostGator

**Runbooks:**
- [`infra/landing-hostgator.md`](./infra/landing-hostgator.md) — subir landing estático

**Tareas:**
- [ ] Contenido de `landing/` compilado (si aplica build step)
- [ ] Archivos subidos a HostGator via FTP/cPanel (`public_html/`)
- [ ] SSL (AutoSSL HostGator o manual) funcionando
- [ ] `https://www.pmo-aas.com` carga landing sin errores
- [ ] Links internos y CTAs funcionando

**Checkpoint:** Visita `www.pmo-aas.com` en navegador, ve landing funcional

---

## 📚 Índice de Runbooks por Servicio

| Tema | Runbook | Estatus |
|---|---|---|
| **Railway** | [`railway/SETUP.md`](./railway/SETUP.md) | ✅ |
| **Railway** | [`railway/DEPLOYMENT.md`](./railway/DEPLOYMENT.md) | ✅ |
| **Tailscale (legacy Ollama BYO)** | [`networking/tailscale-setup.md`](./networking/tailscale-setup.md) | ⚠️ legacy |
| **Cloudflare DNS** | [`infra/dns-routing.md`](./infra/dns-routing.md) | ✅ |
| **HostGator Landing** | [`infra/landing-hostgator.md`](./infra/landing-hostgator.md) | 📝 |
| **Groq (IA plataforma)** | [`ai/groq-setup.md`](./ai/groq-setup.md) | ✅ |
| **BYO (IA del tenant)** | [`ai/byo-setup.md`](./ai/byo-setup.md) | ✅ |
| **Resend (emails)** | [`email/resend-setup.md`](./email/resend-setup.md) | ✅ |
| **IA legacy (archivado)** | [`../archive/runbooks-ai-legacy/`](../archive/runbooks-ai-legacy/) | 📦 |

---

## 🎯 Flujo recomendado

1. **Semana 1**: Completa Railway + DNS (bloques 1, 3).
   - Básico: app/api responden, dominios resuelven.
   - Tiempo estimado: **4 horas**.

2. **Semana 2**: Habilita Groq como IA plataforma (bloque 5) — 20 min con
   `ai/groq-setup.md`. Opcionalmente, habilita BYO para tenants específicos
   con `ai/byo-setup.md`.
   - Tiempo estimado: **30 min–1 h** (sin Ollama/Tailscale).

3. **Semana 3**: Resend (bloque 4) + landing (bloque 6).
   - Emails funcionales.
   - Landing en vivo.
   - Tiempo estimado: **2 horas**.

**Total estimado: ~7 horas** de trabajo si no hay inconvenientes.

---

## 🔧 Stack mínimo para v1.1

| Componente | Tech | Costo | Estado |
|---|---|---|---|
| Frontend | Next.js 15 | Railway ~$30/mes | ✅ |
| Backend | FastAPI + Celery | Railway ~$30/mes | ✅ |
| DB | PostgreSQL 16 | Railway ~$15/mes | ✅ |
| Cache | Redis 7 | Railway ~$10/mes | ✅ |
| DNS | Cloudflare | $0 (free tier) | ✅ |
| IA plataforma | Groq (llama-3.3-70b-versatile) | $0 (free tier) | ✅ |
| IA BYO (opcional) | OpenAI / Claude / Gemini / Perplexity | $$ (cuenta del tenant) | ✅ |
| Email | Resend | $0 (3k/mes free) | ✅ |
| Landing | HostGator | $$ (anual) | ✅ |
| **Total mínimo** | — | **~$85/mes** (sin HostGator anual) | — |

---

## ❓ Troubleshooting rápido

**P:** El worker no alcanza Ollama — `connection timeout`.  
**R:** Ver [`networking/tailscale-setup.md` §9](./networking/tailscale-setup.md#9-troubleshooting).
- Verifica `tailscale status` dentro del worker.
- Confirma `TS_AUTHKEY` y `TS_HOSTNAME` en Railway.
- Revisa firewall Windows: solo 1 regla Allow para `100.64.0.0/10`.

---

**P:** Email no se envía, solo notif in-app.  
**R:** Ver [`email/resend-setup.md`](./email/resend-setup.md).
- Verifica `RESEND_API_KEY` no está vacía en Railway `worker`.
- Revisa dominio verificado en Resend: DNS records propagados.
- Comprueba que `RESEND_FROM` usa el mismo dominio.

---

**P:** `https://app.pmo-aas.com` da SSL error o no resuelve.  
**R:** Ver [`infra/dns-routing.md` §2](./infra/dns-routing.md#2-subdominios-railway--apppmo-aascom-y-apipmo-aascom).
- Railway Custom Domain tarda ≤10 min en provisionar cert.
- Confirma CNAME en Cloudflare va a `<railway-id>.up.railway.app` (DNS only, nube gris).
- Espera 5 min si acabas de crear el CNAME.

---

**P:** Minuta genera pero con latencia alta (> 10s) en modo `platform` (Groq).
**R:** Ver [`ai/groq-setup.md`](./ai/groq-setup.md).
- Revisa `/superadmin/ai` → "Uso de Groq": si estás cerca del límite de
  requests/tokens/día, Groq empieza a tirar 429.
- Verifica que el modelo sigue siendo `llama-3.3-70b-versatile` (si el
  superadmin puso un modelo que Groq deprecó, cada request devuelve error).

**P:** Un tenant en modo `byo` no puede conectar su proveedor.
**R:** Ver [`ai/byo-setup.md`](./ai/byo-setup.md) §8.
- Confirma que el owner encendió `AI_BYO_ENABLED=1` en Railway.
- Revisa la API key en la consola del proveedor (billing/quota/region).

---

## 📞 Support

Si algo no funciona tras seguir el runbook:

1. Revisa la sección **Troubleshooting** del runbook relevante.
2. Consulta los **logs**:
   - Railway: `railway logs --service <api|worker|web> --tail`
   - Tailscale: `C:\ProgramData\Tailscale\Logs\tailscaled.log` (Windows)
   - Ollama: `~/.ollama/server.log`
3. Si persiste, documenta el error en GitHub issue con tag `v1.0-deploy`.

---

## 📄 Referencias cruzadas

- Epic IA: [`docs/epics/EP008-ai.md`](../epics/EP008-ai.md)
- Epic deployment legacy: [`docs/archive/cancelled-epics/EP016-local-ai-tunnel.md`](../archive/cancelled-epics/EP016-local-ai-tunnel.md) — archivada tras DEC-017 (ENH-022)
- Decisiones arquitectónicas: [`docs/epics/DECISIONS.md`](../epics/DECISIONS.md) — **DEC-017** IA multi-modo, **DEC-019** BYO sin Ollama + feature flag, DEC-011 Tailscale (legacy), DEC-012 Railway+HostGator
- Dev local: [`docs/setup-dev.md`](../setup-dev.md)
- API conventions: [`docs/architecture/api-conventions.md`](../architecture/api-conventions.md)
