# Runbooks — Guías de Setup para v1.0

**Última actualización:** 2026-04-21

Este directorio centraliza todos los runbooks operativos para desplegar y operar
**PMO·aaS v1.0** en producción. Cada runbook es autónomo: contiene el checklist
de validación y troubleshooting necesario para ese servicio.

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

### ✅ 2. Networking — Tailscale + Ollama local

**Runbooks:**
- [`networking/tailscale-setup.md`](./networking/tailscale-setup.md) — Tailscale en PC + Railway

**Tareas:**
- [ ] Ollama instalado en PC local, modelo `qwen2.5:7b-instruct-q4_K_M` descargado
- [ ] Ollama expuesto a `0.0.0.0:11434` (no solo localhost)
- [ ] Tailscale instalado en PC local con hostname `ollama-host`
- [ ] Auth key reutilizable generada con tag `tag:railway-worker` (en Tailscale admin)
- [ ] ACL en Tailscale permite tag `tag:railway-worker` → `tag:ollama:11434`
- [ ] MagicDNS habilitado en tailnet
- [ ] Firewall Windows: solo 1 regla "Ollama allow tailnet" para `100.64.0.0/10`
- [ ] `TS_AUTHKEY` y `TS_HOSTNAME=pmo-worker-railway` en Railway `worker`
- [ ] Desde otro device del tailnet: `curl http://ollama-host.<tailnet>.ts.net:11434` devuelve "Ollama is running"

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

### ✅ 5. IA — Gemini + Anthropic keys

**Runbooks:**
- [`ai/gemini-setup.md`](./ai/gemini-setup.md) — Google Gemini free tier
- [`ai/claude-setup.md`](./ai/claude-setup.md) — Anthropic Claude (fallback premium)
- [`ai/local-ollama-setup.md`](./ai/local-ollama-setup.md) — Ollama (local, prioridad 1)

**Tareas (por orden de prioridad):**
- [ ] Ollama local: `TS_AUTHKEY` configurada en Railway worker (ver Networking ✅ 2)
- [ ] Gemini: API key `AIza...` generada en Google AI Studio, configurada en Railway
- [ ] Anthropic: API key `sk-ant-...` generada en console.anthropic.com, configurada
- [ ] `AI_MODE` en Railway api/worker = `ollama` (prioridad 1, fallback automático a Gemini → Claude)
- [ ] Test de conexión: Admin panel → IA settings → test Ollama/Gemini/Claude
- [ ] Cascada probada: desconectar Ollama deliberadamente, verificar fallback a Gemini
- [ ] Minuta generada exitosamente desde la app

**Checkpoint:** Minuta generada con Ollama; cascada funciona si Ollama cae

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
| **Tailscale + Ollama** | [`networking/tailscale-setup.md`](./networking/tailscale-setup.md) | ✅ |
| **Cloudflare DNS** | [`infra/dns-routing.md`](./infra/dns-routing.md) | ✅ |
| **HostGator Landing** | [`infra/landing-hostgator.md`](./infra/landing-hostgator.md) | 📝 |
| **Gemini (2.º fallback)** | [`ai/gemini-setup.md`](./ai/gemini-setup.md) | ✅ |
| **Claude (3.º fallback)** | [`ai/claude-setup.md`](./ai/claude-setup.md) | 📝 |
| **Ollama local** | [`ai/local-ollama-setup.md`](./ai/local-ollama-setup.md) | ✅ |
| **Modelos AI** | [`ai/local-model-setup.md`](./ai/local-model-setup.md) | ✅ |
| **Resend (emails)** | [`email/resend-setup.md`](./email/resend-setup.md) | ✅ |

---

## 🎯 Flujo recomendado

1. **Semana 1**: Completa Railway + DNS (bloques 1, 3).
   - Básico: app/api responden, dominios resuelven.
   - Tiempo estimado: **4 horas**.

2. **Semana 2**: Añade Ollama + Tailscale (bloque 2) + IA keys (bloque 5).
   - App genera minutas con Ollama local.
   - Cascada probada.
   - Tiempo estimado: **3 horas**.

3. **Semana 3**: Resend (bloque 4) + landing (bloque 6).
   - Emails funcionales.
   - Landing en vivo.
   - Tiempo estimado: **2 horas**.

**Total estimado: ~9 horas** de trabajo si no hay inconvenientes.

---

## 🔧 Stack mínimo para v1.0

| Componente | Tech | Costo | Estado |
|---|---|---|---|
| Frontend | Next.js 15 | Railway ~$30/mes | ✅ |
| Backend | FastAPI + Celery | Railway ~$30/mes | ✅ |
| DB | PostgreSQL 16 | Railway ~$15/mes | ✅ |
| Cache | Redis 7 | Railway ~$10/mes | ✅ |
| DNS | Cloudflare | $0 (free tier) | ✅ |
| IA local | Ollama (home-host) | $0 | ✅ |
| IA 2.º fallback | Gemini 1.5 Flash | $0 (free tier) | ✅ |
| IA 3.º fallback | Claude Sonnet | $$ (pay-as-you-go) | ✅ |
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

**P:** Minuta genera pero con latencia alta (> 10s).  
**R:** Ver [`ai/local-ollama-setup.md` §9](./ai/local-ollama-setup.md#9-troubleshooting-común).
- Verifica modelo cacheado: `ollama list`.
- Revisa latencia Tailscale: `tailscale ping ollama-host` > 200ms indica DERP relay.
- Si cascada salta a Gemini, revisa Gemini rate limit (15 RPM).

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

- Epic deployment: [`docs/epics/EP016-local-ai-tunnel.md`](../epics/EP016-local-ai-tunnel.md)
- Decisiones arquitectónicas: [`docs/epics/DECISIONS.md`](../epics/DECISIONS.md) (DEC-011 Tailscale, DEC-012 Railway+HostGator)
- Dev local: [`docs/setup-dev.md`](../setup-dev.md)
- API conventions: [`docs/architecture/api-conventions.md`](../architecture/api-conventions.md)
