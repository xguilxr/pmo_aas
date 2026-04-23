# DNS routing productivo — `pmo-aas.com`

**ID:** `DOC-INFRA-DNS`
**Alcance:** EP016 US-049 / Bloque 15 del sprint
**Referencias:** DEC-012 (BD en Railway, landing en HostGator), DEC-011
(Tailscale reemplaza CF Tunnel — subdominio `ollama.*` retirado).

Este runbook describe la configuración de DNS productiva del dominio
`pmo-aas.com` en **Cloudflare**, combinando servicios hospedados en
**Railway** (app + api) y el landing estático en **HostGator**. Es una
referencia operativa: los cambios se ejecutan desde el dashboard de
Cloudflare, no desde el repo.

> **Pre-requisito:** el dominio `pmo-aas.com` ya fue trasladado a los
> nameservers de Cloudflare (NS de Cloudflare Free tier). Si aún está en
> el registrar, hacer el cambio ahí primero y esperar propagación
> (~2–24 h) antes de seguir.

---

## 1. Mapa de rutas

```
                      ┌────────────────────────────────────┐
                      │  Cloudflare DNS (pmo-aas.com zone) │
                      └────────────────────────────────────┘
                                 │
  ┌──────────────────────────────┼───────────────────────────────┐
  │                              │                               │
  ▼ apex (page rule 301)         ▼ app / api (DNS only)          ▼ www (proxied)
  pmo-aas.com        →     app.pmo-aas.com  ──► Railway web      │
                           api.pmo-aas.com  ──► Railway api      │
                                                                 │
                                                      www.pmo-aas.com
                                                                 │
                                                                 ▼
                                                      HostGator shared (landing)
```

| Host | Tipo | Destino | Proxy | Uso |
|---|---|---|---|---|
| `pmo-aas.com` (apex) | Page Rule / CNAME flattening | 301 → `https://app.pmo-aas.com` | Proxied (naranja) | Acceso humano a la app vía dominio raíz |
| `app.pmo-aas.com` | CNAME | `<web>.up.railway.app` | **DNS only (gris)** | Frontend Next.js |
| `api.pmo-aas.com` | CNAME | `<api>.up.railway.app` | **DNS only (gris)** | FastAPI backend |
| `www.pmo-aas.com` | A o CNAME | IP HostGator (ver §3) | Proxied (naranja) | Landing estático de marketing |
| `ollama.pmo-aas.com` | — | **retirado** | — | EP016 original; ya no aplica (DEC-011) |

**Por qué cada proxy:**

- `app.*` y `api.*` van **DNS only** (nube gris) porque Railway
  termina el TLS con el cert que auto-provisiona cuando se agrega un
  Custom Domain. Si se pone en proxy (naranja), Cloudflare intercepta
  y requiere Full SSL + cert válido, pero además meter Cloudflare en
  medio agrega ruleset AI-bot-blocking que puede tirar requests del
  worker (ver DEC-011, mismo patrón que bloqueó CF Tunnel para
  Ollama). Para una app autenticada, prefiere que el usuario llegue
  directo a Railway.
- `www.*` va **proxied** porque el landing es estático público; el
  proxy de Cloudflare da CDN, caching y TLS terminator contra el
  origen HostGator (que puede o no tener cert propio — Full SSL
  soluciona cualquier caso).

---

## 2. Subdominios Railway — `app.pmo-aas.com` y `api.pmo-aas.com`

### 2.1 Agregar Custom Domain en Railway

Por cada servicio:

1. Railway UI → proyecto `pmo-aas` → servicio `web`.
2. Settings → **Networking** → **+ Custom Domain**.
3. Escribir `app.pmo-aas.com` → **Add**.
4. Railway muestra un valor **CNAME** tipo `sg5x7h8p.up.railway.app`
   (el ID cambia por servicio). **Copiarlo.**
5. Repetir para el servicio `api` con `api.pmo-aas.com` → copiar su
   CNAME.

### 2.2 Crear los CNAME en Cloudflare

Dashboard Cloudflare → zona `pmo-aas.com` → **DNS → Records → + Add
record**:

| Type | Name | Target | Proxy status |
|---|---|---|---|
| CNAME | `app` | `<railway-web-cname>.up.railway.app` | DNS only (gris) |
| CNAME | `api` | `<railway-api-cname>.up.railway.app` | DNS only (gris) |

TTL: Auto.

### 2.3 Verificar

```bash
# Debe devolver el CNAME target de Railway
dig app.pmo-aas.com CNAME +short
dig api.pmo-aas.com CNAME +short

# Una vez propagado (~5 min) debe servir con TLS válido
curl -I https://app.pmo-aas.com/api/health
curl -I https://api.pmo-aas.com/health
```

Railway auto-provisiona el cert Let's Encrypt en ≤ 10 min tras agregar
el Custom Domain. Si después de 30 min no resuelve, revisar que
`Proxy status = DNS only` en Cloudflare (si está en naranja, Let's
Encrypt ACME challenge falla).

### 2.4 Actualizar variables de Railway

Una vez que los dominios responden, actualizar las variables de los
servicios para reflejarlos (ver `RAILWAY_SETUP.md` §5):

- `api` → `ALLOWED_ORIGINS` = `https://app.pmo-aas.com`
- `web` → `NEXT_PUBLIC_API_URL` = `https://api.pmo-aas.com`
- `web` → `NEXTAUTH_URL` = `https://app.pmo-aas.com`

Trigger redeploy de `api` + `web` al guardar.

---

## 3. Landing `www.pmo-aas.com` — HostGator

### 3.1 Obtener IP de HostGator

Desde cPanel de HostGator → sección **General Information**:

- **Shared IP Address**: `192.xxx.yyy.zzz` (copiar).
- Alternativa: `ping <tu-dominio-hostgator>.com` desde tu shell.

### 3.2 Crear registro en Cloudflare

| Type | Name | Target | Proxy status |
|---|---|---|---|
| A | `www` | `<IP HostGator>` | Proxied (naranja) |

Si HostGator provee un hostname (ej. `gator1234.hostgator.com`) que sí
resuelve estable, prefiere CNAME:

| Type | Name | Target | Proxy status |
|---|---|---|---|
| CNAME | `www` | `gator1234.hostgator.com` | Proxied (naranja) |

### 3.3 SSL Cloudflare ↔ HostGator

Dashboard Cloudflare → zona → **SSL/TLS → Overview → Encryption mode**:

- Si HostGator sirve con cert propio (AutoSSL de cPanel):
  **Full (strict)** — Cloudflare exige cert válido en origen.
- Si HostGator sirve con cert self-signed o sin cert:
  **Full** (no strict) — Cloudflare acepta cert no verificado.
- **Nunca** usar *Flexible* (HTTP al origen): el tráfico entre
  Cloudflare y HostGator viaja en claro y es susceptible a MITM.

Recomendado: habilitar AutoSSL en HostGator cPanel (**Security → SSL/TLS
Status**) y usar **Full (strict)**.

### 3.4 Verificar

```bash
dig www.pmo-aas.com +short
# Debe devolver IPs de Cloudflare (104.21.x.x / 172.67.x.x)

curl -I https://www.pmo-aas.com
# 200 OK con headers `cf-ray` y `server: cloudflare`
```

---

## 4. Apex `pmo-aas.com` — redirect 301

El apex debe llevar al usuario a la app autenticada (`app.pmo-aas.com`),
no al landing de marketing.

### 4.1 Opción A (recomendada) — Bulk Redirects

Cloudflare → **Rules → Redirect Rules → + Create rule**:

- Rule name: `apex → app`.
- If:
  - Field: **Hostname**
  - Operator: `equals`
  - Value: `pmo-aas.com`
- Then:
  - Type: **Static**
  - URL: `https://app.pmo-aas.com`
  - Status code: **301 — Permanent redirect**
  - Preserve query string: ON
  - Preserve path: ON (quieres que `pmo-aas.com/login` → `app.pmo-aas.com/login`)

### 4.2 Opción B (fallback) — CNAME flattening

Si la cuenta no tiene Redirect Rules disponibles (Free tier limita a 10):

1. DNS → + Add record:
   - Type: `CNAME`
   - Name: `@` (apex)
   - Target: `app.pmo-aas.com`
   - Proxy status: Proxied (naranja) — obligatorio para CNAME
     flattening.
2. El apex ahora resuelve a la misma IP que `app.*` y sirve la app
   Next.js. **Peligro:** sin redirect 301 estricto, los robots indexan
   `pmo-aas.com/login` y `app.pmo-aas.com/login` como contenido
   duplicado. Agregar un `<link rel="canonical">` a `app.*` en el
   layout de Next.js si se usa esta opción.

### 4.3 Verificar

```bash
curl -I https://pmo-aas.com
# HTTP/2 301
# location: https://app.pmo-aas.com/

curl -I https://pmo-aas.com/login
# HTTP/2 301
# location: https://app.pmo-aas.com/login  ← (opción A, preserve path)
```

---

## 5. Retirar `ollama.pmo-aas.com` (DEC-011)

El pivote a Tailscale (ver
[`docs/archive/runbooks-ai-legacy/local-ollama-setup.md`](../archive/runbooks-ai-legacy/local-ollama-setup.md))
elimina la necesidad de exponer Ollama vía CF Tunnel con hostname
público. Desde DEC-017 (Sprint 2 v1.1) Ollama ya no es parte del
flujo productivo — la IA de la plataforma usa Groq hosteado — pero
este cleanup de DNS sigue siendo válido.

Cleanup en Cloudflare:

1. DNS → encontrar el CNAME `ollama` → **Delete**.
2. Zero Trust → **Access → Applications** → `PMO-aaS Ollama` →
   **Delete**.
3. Zero Trust → **Access → Service Auth → Service Tokens** → revocar
   todos los tokens relacionados a `pmoaas-ollama`.

El `cloudflared` local del owner se retira siguiendo el runbook
archivado
[`docs/archive/runbooks-ai-legacy/local-ollama-setup.md`](../archive/runbooks-ai-legacy/local-ollama-setup.md)
§10 "Rollback CF Tunnel".

---

## 6. Checklist final

- [ ] Registrar propietario autorizó el cambio de nameservers a Cloudflare.
- [ ] Custom Domain `app.pmo-aas.com` agregado al servicio `web` de
      Railway; CNAME en Cloudflare (DNS only).
- [ ] Custom Domain `api.pmo-aas.com` agregado al servicio `api` de
      Railway; CNAME en Cloudflare (DNS only).
- [ ] `https://app.pmo-aas.com/api/health` y `https://api.pmo-aas.com/health`
      devuelven 200 con cert Let's Encrypt válido.
- [ ] `ALLOWED_ORIGINS`, `NEXT_PUBLIC_API_URL`, `NEXTAUTH_URL` en
      Railway actualizados y servicios redeployados.
- [ ] CNAME `www` apuntando a HostGator con proxy Cloudflare (naranja)
      + Full (strict).
- [ ] Redirect Rule apex → `app.pmo-aas.com` (301) funcionando.
- [ ] CNAME `ollama` borrado + Access App + Service Tokens revocados.
- [ ] Prueba final: usuario escribe `pmo-aas.com` en browser → aterriza
      en `app.pmo-aas.com/login`.
- [ ] Prueba final: usuario escribe `www.pmo-aas.com` → aterriza en el
      landing de marketing.

---

## 7. Rollback

Si algún paso rompe producción:

1. **Custom Domain Railway**: Settings → Networking → remove domain →
   el servicio vuelve a ser accesible por `<servicio>.up.railway.app`.
2. **CNAME en Cloudflare**: DNS → editar registro → cambiar target o
   borrar. Propagación suele tomar < 5 min con proxy, hasta 1 h sin.
3. **Redirect rule apex**: Rules → Redirect Rules → toggle OFF.
4. **Full downgrade**: si Cloudflare es el problema, pausar la zona
   (**Overview → Advanced → Pause Cloudflare on site**). DNS sigue
   respondiendo pero sin proxy ni rulesets.

No tocar nameservers del registrar salvo emergencia — volver de
Cloudflare a un DNS externo toma 24–48 h de propagación.

---

## Referencias

- Cloudflare Custom Domains en Railway — <https://docs.railway.com/guides/public-networking#custom-domains>
- Cloudflare Redirect Rules — <https://developers.cloudflare.com/rules/url-forwarding/>
- Cloudflare SSL modes — <https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/>
- DEC-011 (Tailscale) — [`docs/epics/DECISIONS.md`](../epics/DECISIONS.md)
- DEC-012 (DB Railway + HostGator landing) — [`docs/epics/DECISIONS.md`](../epics/DECISIONS.md)
- DEC-013 (Railway tier upgrade, EP012 cancelado) — [`docs/epics/DECISIONS.md`](../epics/DECISIONS.md)
