# EP016 — Modelo IA local (Ollama + Tailscale)

| Campo | Valor |
|---|---|
| **ID** | EP016 |
| **Prioridad** | Alta — bloque 13 del sprint (reabierto) |
| **Dependencias** | EP008 (IA minutas y reportes), EP014 US-NEW-040 (formato estandarizado minuta) |
| **Módulo** | `ai.local`, `infrastructure`, `docs/ai` |
| **Estado** | # REOPENED — pivote de canal (CF Tunnel → Tailscale) |
| **Versión objetivo** | v1.0 |
| **Origen** | Requerimiento del owner: host propio con Ollama, accesible desde backend productivo en Railway, sin costos de token y sin datos fuera del perímetro. |

## Objetivo de negocio

Habilitar minutas generadas con IA **sin costo por token** y **sin sacar datos del perímetro del cliente**, corriendo Ollama en la PC local del propietario y accesible desde el worker de Railway vía un **tailnet privado de Tailscale**. Reutiliza la cascada de proveedores IA definida en EP008 — Ollama es el primer motor, Gemini/Claude son fallback.

### Pivote arquitectónico — CF Tunnel → Tailscale (2026-04-21)

El diseño original (US-NEW-044 + US-NEW-045) exponía Ollama con **Cloudflare Tunnel + Cloudflare Access (Service Token)**. El despliegue real en producción encontró blockers reproducibles:

- Managed ruleset "Block AI bots" de Cloudflare devuelve 403 a requests con UA no-browser, aun con skip rules a nivel custom.
- UI de Cloudflare One fragmenta el flujo (Access Controls → Applications, Policies, Service Credentials, Access Settings) y tiene bugs de estado al guardar policies.
- Exposición pública del endpoint (aun con token) es superficie innecesaria para un API que solo consume el worker.

La decisión **DEC-011** (ver DECISIONS.md) reemplaza el canal por **Tailscale tailnet**: cero exposición pública, admin console nativa, setup reproducible. US-NEW-044/045 quedan **SUPERSEDED**; la implementación real entra por US-NEW-046/047/048.

### Topología nueva

```
PC Windows (tailscaled service, nssm)          Railway worker (sidecar tailscaled)
 └─ Ollama 0.0.0.0:11434                         └─ http://ollama-host.<tailnet>.ts.net:11434
 └─ tailnet IP 100.x.y.z                                   │
 └─ Windows Firewall: inbound 11434 solo                   │
    desde 100.64.0.0/10 (tailnet)                          │
                    └──── tailnet WireGuard ───────────────┘
                       (direct NAT traversal o DERP relay)
```

### Contexto técnico

- **Host local**: PC Windows del owner con Ollama y `tailscaled` como servicio (`nssm` si se requiere arranque pre-login).
- **Motor**: Ollama corriendo en `0.0.0.0:11434` (no solo localhost), accesible desde interfaces tailnet.
- **Red**: Tailscale free tier (100 devices, 3 users). `TS_AUTHKEY` ephemeral reusable para el worker.
- **Uso en PMO**: worker EP008 arranca con `tailscaled` sidecar, luego `exec celery`. Llama a Ollama vía MagicDNS o IP tailnet.

## Decisiones registradas en DECISIONS.md

- **DEC-011** — Tailscale reemplaza CF Tunnel + Access para el canal PC→Railway.
- **DEC-012** — BD productiva en Railway Postgres (no HostGator MySQL); dominio `pmo-aas.com` conserva `app.*`, `api.*`, `www.*`; `ollama.*` se retira.

> Las DEC-023/024/025 planeadas en la versión anterior de EP016 (CF Tunnel + CF-Access headers) **no se registran** — quedan absorbidas por DEC-011.

---

## # SUPERSEDED — US-NEW-044 — Runbook `local-ollama-setup.md` (CF Tunnel)

> **Superseded por US-NEW-046 (2026-04-21)**. El runbook actual
> `docs/ai/local-ollama-setup.md` describe CF Tunnel + nssm; se reescribe
> en US-NEW-046 con flujo Tailscale. El archivo histórico queda en git
> (commit `f03a9bb`) como referencia de la arquitectura descartada.

### Historial original — US-NEW-044 (DONE 2026-04-20)

**Como** owner/operador
**Quiero** un paso-a-paso para instalar y exponer Ollama localmente
**Para** conectarlo al PMO productivo en < 30 min sin adivinar pasos.

**Criterios de aceptación:**
- [ ] Archivo `docs/ai/local-ollama-setup.md` con las secciones:
  1. **Pre-requisitos**: Windows 10/11 (PowerShell elevado), 16+ GB RAM, conexión estable, dominio Cloudflare, acceso al dashboard Zero Trust.
  2. **Instalar Ollama** (MSI/winget), jalar el modelo (`ollama pull qwen2.5:7b-instruct-q4_K_M` u otro alineado con EP008) y verificar.
  3. **Validar API local** (`curl http://localhost:11434/api/generate`).
  4. **Instalar `cloudflared`** (MSI de Cloudflare) y loguearse (`cloudflared tunnel login`).
  5. **Crear túnel** (`cloudflared tunnel create pmoaas-ollama`), guardar credenciales y configurar `config.yml`:
     ```yaml
     tunnel: <id>
     credentials-file: C:\Users\<user>\.cloudflared\<id>.json
     ingress:
       - hostname: ollama.<tu-dominio>
         service: http://localhost:11434
       - service: http_status:404
     ```
  6. **DNS**: `cloudflared tunnel route dns pmoaas-ollama ollama.<tu-dominio>`.
  7. **Cloudflare Access**: proteger `ollama.<tu-dominio>` con una aplicación Self-hosted y emitir un **Service Token** (Client-Id + Client-Secret). Guardar ambos valores.
  8. **Registrar `cloudflared` como servicio con `nssm`**:
     ```
     nssm install CloudflaredOllama "C:\Program Files (x86)\cloudflared\cloudflared.exe"
     nssm set CloudflaredOllama AppParameters "tunnel --config C:\Users\<user>\.cloudflared\config.yml run"
     nssm set CloudflaredOllama Start SERVICE_AUTO_START
     nssm start CloudflaredOllama
     ```
  9. **Registrar Ollama como servicio con `nssm`** (equivalente, ejecutable `ollama serve`).
  10. **Smoke test externo**: `curl -H "CF-Access-Client-Id: …" -H "CF-Access-Client-Secret: …" https://ollama.<tu-dominio>/api/tags` → 200 con lista de modelos.
  11. **Registrar en PMO**: navegar a `/admin/tenant?tab=config`, sección "Configuración IA" (o `settings.ai.ollama`), guardar `base_url`, `model`, `cf_access_client_id` (visible), `cf_access_client_secret` (password field masked).
  12. **Troubleshooting**: tabla con fallas comunes (puerto ocupado, permisos nssm, Access bloqueando, modelo demasiado grande para la RAM).
- [ ] Diagrama ASCII simple de la topología (PC → cloudflared → Cloudflare Edge → backend PMO).
- [ ] Sección "Rollback": cómo detener/desinstalar todo en orden inverso.
- [ ] Enlaces oficiales a Ollama, Cloudflare Tunnel, nssm.

**Test Cases:**
- N/A (runbook). Verificación manual: el owner ejecuta el runbook paso a paso en una PC limpia y llega al smoke test en verde.

**Archivo:** [`docs/ai/local-ollama-setup.md`](../ai/local-ollama-setup.md) — incluye topología ASCII, 10 pasos ejecutables, troubleshooting tabular y rollback.

**Commit:** `docs(ai): US-NEW-044 — runbook Ollama + Cloudflare Tunnel + nssm`.

---

## # SUPERSEDED — US-NEW-045 — Config y smoke test (CF Access headers)

> **Superseded por US-NEW-047 (2026-04-21)**. El endpoint `POST
> /api/v1/admin/ai/test-connection`, el formulario `OllamaLocalAiForm`,
> y el script `app/scripts/ai_local_smoke.py` **siguen existiendo y pasan
> tests**, pero traen campos `cf_access_client_id` / `cf_access_client_secret`
> que con Tailscale dejan de tener sentido. US-NEW-047 refactoriza:
> quita esos campos, cambia `base_url` default a hostname MagicDNS,
> elimina Fernet encryption para secrets (no hay secret que guardar), y
> simplifica el smoke test a un GET sin headers de auth.

### Historial original — US-NEW-045 (DONE parcial 2026-04-20)

**Como** backend PMO
**Quiero** que al guardar la config IA del tenant con la URL del túnel + service token, PMO valide conexión y use ese endpoint en la próxima minuta IA
**Para** cerrar el loop del runbook sin que el owner tenga que correr pruebas manuales.

**Criterios de aceptación:**
- [ ] `tenants.settings.ai.ollama` (JSONB) formalizado con shape:
  ```json
  {
    "base_url": "https://ollama.example.com",
    "model": "qwen2.5:7b-instruct-q4_K_M",
    "timeout_sec": 60,
    "auth": {
      "type": "cf_access",
      "client_id": "<CF-Access-Client-Id>",
      "client_secret": "<cifrado Fernet>"
    }
  }
  ```
- [ ] Endpoint `POST /api/v1/admin/ai/test-connection` (admin-only) — toma `{provider: 'ollama'}` y hace un ping al `base_url/api/tags` con los headers CF-Access. Devuelve `{ok: true, latency_ms, model_present: bool}` o `{ok: false, error}`.
- [ ] El cliente Ollama del worker EP008 lee `tenants.settings.ai.ollama`, incluye headers `CF-Access-Client-Id` / `CF-Access-Client-Secret` cuando están configurados, y respeta `timeout_sec`.
- [ ] Secretos cifrados: el secret llega en texto plano al PATCH, se cifra con Fernet antes de persistir; el GET lo devuelve enmascarado (`"••••<últimos 4>"`).
- [ ] UI `/admin/tenant?tab=config`:
  - Subsección "Proveedor IA local (Ollama)".
  - Campos: `base_url`, `model`, `timeout_sec`, `cf_access_client_id`, `cf_access_client_secret` (password).
  - Botón "Probar conexión" → llama el endpoint y muestra latencia o error inline.
- [ ] Script `scripts/ai-local-smoke.py` CLI que toma `--tenant {slug}` y hace end-to-end: leer config → pingear túnel → enviar prompt de 3 líneas → validar JSON → reportar.
- [x] Al guardar el config, el secret **llega en texto plano al PATCH y se cifra con Fernet** antes de persistir. El GET devuelve el secret enmascarado (`••••<últimos 4>`).
- [x] Endpoint `POST /admin/ai/test-connection` con body `{provider: "ollama"}`. Hace `GET {base_url}/api/tags` con headers CF-Access y devuelve `{ok, latency_ms, model_present, tags_count, error, code}`.
- [x] `AI_SECRETS_FERNET_KEY` agregada a `Settings` con fallback dev; `app.services.ai_secrets` con `encrypt/decrypt/mask`.
- [x] UI `/admin/tenant?tab=config` incluye sección `<OllamaLocalAiForm />` con los campos (`base_url`, `model`, `timeout_sec`, `cf_access_client_id`, `cf_access_client_secret`), botón **Probar conexión**, botón **Quitar secret** y banner de resultado (latencia o error).
- [x] Script CLI `app/scripts/ai_local_smoke.py` — `python -m app.scripts.ai_local_smoke --tenant {slug}` resuelve config, descifra token, pingea `/api/tags` y `/api/generate`. Exit 0 si ambos pasan.
- [ ] **Follow-up:** integrar este config por-tenant en `OllamaProvider.generate()` de `app/services/ai/provider.py` (hoy usa env). El endpoint de test-connection valida el túnel; el worker real lo adoptará en un refactor del provider. Criterio DoD: `ai_cascade_fallback_total{from=ollama,to=gemini}` incrementa cuando `base_url` del tenant 5xx/timeout.

**Tests (10/10 verdes; suite completa 204/204):**
- `test_usnew045_encrypt_decrypt_roundtrip` + `test_usnew045_mask_secret` — utils de secrets.
- `test_usnew045_get_empty_config` — respuesta base.
- `test_usnew045_patch_persists_encrypted` — secret se cifra en BD (verificado leyendo `settings.ai.ollama`).
- `test_usnew045_clear_secret` — borra el secret cifrado.
- `test_usnew045_test_connection_not_configured` — devuelve `code=NOT_CONFIGURED`.
- `test_usnew045_test_connection_ok_mocked` — mock `httpx.AsyncClient.get` → 200 + modelo → `ok=true, model_present=true`.
- `test_usnew045_test_connection_timeout` — `TimeoutException` → `code=TIMEOUT`.
- `test_usnew045_test_connection_http_error` — 401 → `code=HTTP_ERROR`.
- `test_usnew045_non_admin_forbidden` — GET/PATCH sin `admin.users:update` → 403.

**Commit:** `feat(api,web): US-NEW-045 — config y smoke del modelo IA local (Cloudflare Tunnel)`.

---

---

## # PENDING — US-NEW-046 — Runbook `local-ollama-setup.md` reescrito para Tailscale

**Como** owner/operador
**Quiero** un paso-a-paso Tailscale para exponer Ollama al worker de Railway
**Para** reemplazar el runbook CF Tunnel sin perder el tiempo que invertí en instalar Ollama y el modelo.

**Criterios de aceptación:**
- [ ] Sobrescribir `docs/ai/local-ollama-setup.md` (commit preserva historial vía git log). Secciones:
  1. **Topología ASCII** (PC tailnet ↔ Railway worker tailnet).
  2. **Pre-requisitos**: Windows 10/11, Ollama ya instalado (reusa paso del runbook anterior), cuenta Tailscale (free tier).
  3. **Instalar Tailscale en Windows**: MSI de <https://tailscale.com/download/windows>, login con GitHub/Google/email.
  4. `tailscale up --hostname=ollama-host` + anotar IP tailnet (`tailscale ip -4`) o MagicDNS.
  5. **Exponer Ollama al tailnet**: `[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")` + reiniciar Ollama desde system tray.
  6. **Windows Firewall** (opcional pero recomendado): permitir inbound 11434 solo desde `100.64.0.0/10`.
  7. **Smoke test local en tailnet**: desde otro device del tailnet, `curl http://ollama-host:11434` → `Ollama is running`.
  8. **Registrar Tailscale como servicio con `nssm`** (arranque pre-login). Similar al bloque §6 del runbook anterior pero con binario `tailscaled`.
  9. **Generar TS_AUTHKEY** en <https://login.tailscale.com/admin/settings/keys>: Reusable + Ephemeral + tags `tag:railway-worker`. Copiar a password manager.
  10. **Registrar endpoint en PMO** (`/admin/tenant?tab=config`): `base_url = http://ollama-host.<tu-tailnet>.ts.net:11434`, `model = qwen2.5:7b-instruct-q4_K_M`. **No se llenan Client Id/Secret** (queda deprecado en UI — ver US-NEW-047).
- [ ] **Sección troubleshooting** actualizada: tailscale status, ts ping, logs de tailscaled en Windows (`C:\ProgramData\Tailscale\Logs\`).
- [ ] **Sección rollback**: `tailscale logout`, desinstalar MSI, revocar TS_AUTHKEY, borrar Ollama firewall rule.
- [ ] **Referencia cruzada** a US-NEW-048 (sidecar en worker) — sin ese lado el endpoint no es consumible.
- [ ] El owner ejecuta el runbook en ambiente limpio y llega al smoke test en verde.

**Archivo:** `docs/ai/local-ollama-setup.md` (overwrite).
**Commit:** `docs(ai): US-NEW-046 — runbook Ollama + Tailscale (reemplaza CF Tunnel)`.

---

## # PENDING — US-NEW-047 — Refactor config + test-connection para Tailscale

**Como** backend PMO
**Quiero** que el admin tenant pueda configurar Ollama sin campos de CF-Access
**Para** que el formulario y el smoke test reflejen el nuevo canal Tailscale.

**Criterios de aceptación:**
- [ ] Schema `tenants.settings.ai.ollama` reducido a:
  ```json
  {
    "base_url": "http://ollama-host.<tailnet>.ts.net:11434",
    "model": "qwen2.5:7b-instruct-q4_K_M",
    "timeout_sec": 60
  }
  ```
  Se elimina la rama `auth.{type, client_id, client_secret}`. Si hay datos previos en BD, migración lee `auth.*` y los ignora (no borra — se archiva como `auth_legacy`).
- [ ] Endpoint `POST /api/v1/admin/ai/test-connection` simplificado: hace `GET {base_url}/api/tags` **sin** headers `CF-Access-*`. Devuelve igual shape (`{ok, latency_ms, model_present, tags_count, error, code}`).
- [ ] Formulario `OllamaLocalAiForm`: remover inputs `cf_access_client_id` y `cf_access_client_secret`. Remover botón "Quitar secret". Agregar nota inline: "Este endpoint debe ser accesible desde el worker de Railway (vía tailnet Tailscale). Ver [runbook](../docs/ai/local-ollama-setup.md)".
- [ ] Deprecar `AI_SECRETS_FERNET_KEY` del `Settings` — mantener la key por compatibilidad con secrets legacy guardados, pero no se genera ni lee en flujo nuevo. Marcar en código con `# DEPRECATED US-NEW-047` para remover en cleanup futuro.
- [ ] Script CLI `app/scripts/ai_local_smoke.py` simplificado: sin headers, solo `GET /api/tags` + `POST /api/generate` con prompt "Responde OK" y validar respuesta.
- [ ] Tests existentes (`test_usnew045_*`): los que validan CF-Access headers se **renombran** a `test_usnew047_*` y se refactorizan (ya no esperan headers). Los que validan encrypt/decrypt se mueven a `test_legacy_fernet_roundtrip` (skip con marker `@pytest.mark.legacy`).
- [ ] Documentar en PR la nota de migración: "Tenants con config previa mantienen `base_url` y `model`; deben actualizar `base_url` al hostname tailnet manualmente (UI muestra el valor viejo editable)."

**Commit:** `feat(api,web): US-NEW-047 — refactor config Ollama a Tailscale (quita CF-Access)`.

**Riesgo/nota:** este refactor **no** toca `OllamaProvider.generate()` (sigue pendiente el follow-up original). Solo lado admin-UI + test-connection.

---

## # PENDING — US-NEW-048 — Sidecar Tailscale en el worker de Railway

**Como** worker EP008 corriendo en Railway
**Quiero** ser miembro del tailnet del owner al arrancar
**Para** poder resolver `ollama-host.<tailnet>.ts.net` y hacer requests HTTP directo sin headers de auth.

**Criterios de aceptación:**
- [ ] **Dockerfile custom** para `apps/api` (worker comparte imagen con api):
  ```dockerfile
  FROM python:3.12-slim
  RUN apt-get update && apt-get install -y curl ca-certificates iptables \
      && curl -fsSL https://tailscale.com/install.sh | sh \
      && rm -rf /var/lib/apt/lists/*
  COPY requirements.txt /tmp/
  RUN pip install --no-cache-dir -r /tmp/requirements.txt
  COPY . /app
  WORKDIR /app
  COPY start-worker.sh /start-worker.sh
  RUN chmod +x /start-worker.sh
  CMD ["/start-worker.sh"]
  ```
- [ ] `apps/api/start-worker.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  # Arranca tailscaled en user-space (Railway no da /dev/net/tun)
  /usr/sbin/tailscaled --tun=userspace-networking --state=mem: --socket=/tmp/tailscaled.sock &
  TSD_PID=$!
  # Dar tiempo a que el socket esté vivo
  for i in {1..10}; do
    [ -S /tmp/tailscaled.sock ] && break
    sleep 0.5
  done
  tailscale --socket=/tmp/tailscaled.sock up \
    --authkey="${TS_AUTHKEY:?TS_AUTHKEY no configurado}" \
    --hostname=railway-worker \
    --accept-dns=true
  # Exec celery; si muere, todo el container muere (deseado)
  exec celery -A app.worker worker -l info
  ```
- [ ] **`railway.json` / `worker.railway.toml`**: apuntar a `apps/api/Dockerfile` en vez de Nixpacks default. Watch Paths siguen siendo `apps/api/**`.
- [ ] **Shared Variables en Railway**: agregar `TS_AUTHKEY` (generada en US-NEW-046 paso 9, reusable ephemeral). Nunca rotar desde Railway UI — rotar en Tailscale admin.
- [ ] **Lado api**: el servicio `api` NO necesita Tailscale (no habla con Ollama directo; solo el worker). Dejar Dockerfile default.
- [ ] **Healthcheck worker**: `celery inspect ping` sigue funcionando; agregar check opcional `tailscale --socket=/tmp/tailscaled.sock status` en `/health` interno.
- [ ] **Documentar en `RAILWAY_SETUP.md`**: nueva sección "Servicio `worker` — sidecar Tailscale" con los shared vars.
- [ ] **Smoke desde Railway**: deploy + desde Railway shell del worker, `tailscale status` muestra `ollama-host` como peer. `curl http://ollama-host:11434` desde el shell devuelve 200.
- [ ] Follow-up del follow-up: refactorizar `OllamaProvider.generate()` para leer `tenants.settings.ai.ollama.base_url` y hacer request. Criterio: `ai_cascade_fallback_total{from=ollama,to=gemini}` incrementa cuando el worker no puede resolver el hostname tailnet.

**Commit:** `feat(worker): US-NEW-048 — sidecar Tailscale para acceso a Ollama local`.

---

## Endpoints nuevos

```
(sin cambios — POST /api/v1/admin/ai/test-connection sigue existiendo,
 se simplifica en US-NEW-047.)
```

## Cambios de schema

Ninguno estructural. `tenants.settings.ai.ollama` pierde la rama `auth.*` (migración lógica en app, no en BD). `AI_SECRETS_FERNET_KEY` se marca deprecado.

---

## Dependencias externas (documentar en runbook)

- [Ollama](https://ollama.com) — motor de inferencia local.
- [Tailscale](https://tailscale.com/download) — tailnet privado WireGuard.
- [`tailscale` Docker install](https://tailscale.com/kb/1282/docker) — sidecar en containers.
- [nssm](https://nssm.cc) — wrapper de servicio para Windows (opcional, arranque pre-login).

---

## Definition of Done

- [ ] `docs/ai/local-ollama-setup.md` reescrito con flujo Tailscale y verificado por el owner en ambiente limpio (US-NEW-046).
- [ ] Config IA tenant simplificada: solo `{base_url, model, timeout_sec}` (US-NEW-047).
- [ ] `POST /admin/ai/test-connection` funciona sin headers CF-Access (US-NEW-047).
- [ ] Worker Railway tiene sidecar `tailscaled` y resuelve hostname tailnet (US-NEW-048).
- [ ] `OllamaProvider.generate()` usa config por-tenant y cae a Gemini/Claude cuando el tailnet está caído (follow-up de US-NEW-048).
- [ ] Al menos una minuta IA de prueba generada contra Ollama (vía tailnet) + post-procesada con el formatter EP014 US-NEW-040 (PDF/MD en `/data/test-artifacts/`).
- [ ] `RAILWAY_SETUP.md` actualizado con sección sidecar Tailscale.
- [ ] DEC-011 y DEC-012 registradas en DECISIONS.md ✅ (hechas 2026-04-21).
- [ ] ADR-014 marcada Reemplazada por ADR-015 ✅ (hecha 2026-04-21).
- [ ] Subdominio `ollama.pmo-aas.com` retirado del DNS de Cloudflare + tunnel `pmoaas-ollama` borrado de `cloudflared tunnel list`.
