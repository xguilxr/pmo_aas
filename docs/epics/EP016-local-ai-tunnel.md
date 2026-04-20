# EP016 — Modelo IA local (Ollama + Cloudflare Tunnel + nssm)

| Campo | Valor |
|---|---|
| **ID** | EP016 |
| **Prioridad** | Alta — bloque 12 del sprint |
| **Dependencias** | EP008 (IA minutas y reportes), EP014 US-NEW-040 (formato estandarizado minuta) |
| **Módulo** | `ai.local`, `infrastructure`, `docs/ai` |
| **Estado** | # PENDING |
| **Versión objetivo** | v1.1 |
| **Origen** | Requerimiento del owner: host propio con Ollama, expuesto vía Cloudflare Tunnel (servicio como Windows Service con `nssm`), para alimentar minutas con IA sin depender de proveedores cloud. |

## Objetivo de negocio

Habilitar minutas generadas con IA **sin costo por token** y **sin sacar datos del perímetro del cliente**, corriendo Ollama en la PC local del propietario y exponiéndolo al backend productivo vía un Cloudflare Tunnel con autenticación. Reutiliza la cascada de proveedores IA definida en EP008 — Ollama es el primer motor, Gemini/Claude son fallback.

### Contexto técnico proporcionado

- **Host local**: PC del owner (Windows asumido, por `nssm`).
- **Motor**: Ollama corriendo en `http://localhost:11434`.
- **Exposición**: Cloudflare Tunnel (`cloudflared`) publica el servicio en `ollama.{dominio}` o similar, con Cloudflare Access (Zero Trust) como auth.
- **Persistencia**: `nssm` registra `cloudflared` (y opcionalmente `ollama`) como servicio de Windows → arranque automático.
- **Uso en PMO**: el worker de EP008 hace request al túnel cuando genera minuta desde transcript (US-043). El output JSON se post-procesa con el formatter de US-NEW-040 (EP014).

## DEC a registrar en DECISIONS.md al cierre del bloque

- **DEC-023** — La URL del endpoint Ollama local (vía túnel Cloudflare) se guarda en `tenants.settings.ai.ollama.base_url`. Es por-tenant, no global — cada cliente puede tener su propio host. Si no se define, se cae al siguiente proveedor de la cascada.
- **DEC-024** — La autenticación al túnel se hace con **Cloudflare Access Service Token** (header `CF-Access-Client-Id` + `CF-Access-Client-Secret`). Los tokens se guardan cifrados en `tenants.settings.ai.ollama.auth` (JSONB, Fernet) y nunca se loggean.
- **DEC-025** — Smoke test del túnel es parte del pipeline de release: `scripts/ai-local-smoke.py {tenant_id}` valida que el endpoint responde un prompt básico dentro de 5 s.

---

## # PENDING — US-NEW-044 — Runbook `local-ollama-setup.md`

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

**Commit:** `docs(ai): US-NEW-044 — runbook Ollama + Cloudflare Tunnel + nssm`.

---

## # PENDING — US-NEW-045 — Config y smoke test del túnel desde PMO

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
- [ ] Al generar una minuta IA (EP008), si el `base_url` falla con 5xx/timeout, la cascada sigue (Gemini → Claude) y métrica `ai_cascade_fallback_total{from=ollama,to=gemini}` incrementa.
- [ ] Tests:
  - `test_usnew045_settings_persisted_encrypted` — secret se guarda cifrado.
  - `test_usnew045_test_connection_mocked_ok` — mock HTTP responde 200, endpoint devuelve `ok=true` con latencia.
  - `test_usnew045_test_connection_unreachable` — mock timeout → 502 con mensaje accionable.
  - `test_usnew045_fallback_on_local_failure` — Ollama 5xx → Gemini toma el relevo (si configurado) o error con trace claro.

**Commit:** `feat(api,web): US-NEW-045 — config y smoke del modelo IA local (Cloudflare Tunnel)`.

---

## Endpoints nuevos

```
POST /api/v1/admin/ai/test-connection       (US-NEW-045)
```

## Cambios de schema

Ninguno estructural. `tenants.settings.ai.ollama` usa la columna JSONB existente. La clave Fernet vive en env (`AI_SECRETS_FERNET_KEY`) — añadir al `Settings` pydantic (BaseSettings) con default dev.

---

## Dependencias externas (documentar en runbook)

- [Ollama](https://ollama.com) (modelo local).
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) (exposición segura).
- [nssm](https://nssm.cc) (wrapper de servicio para Windows).

---

## Definition of Done

- [ ] `docs/ai/local-ollama-setup.md` escrito y verificado por el owner en ambiente limpio.
- [ ] Config IA tenant extendida con `ollama.{base_url, model, timeout_sec, auth}`.
- [ ] `POST /admin/ai/test-connection` valida el túnel y devuelve latencia.
- [ ] Worker EP008 respeta la config por-tenant y cae a Gemini/Claude cuando falla.
- [ ] Smoke script `scripts/ai-local-smoke.py` funcionando.
- [ ] Al menos una minuta IA de prueba generada contra el túnel + post-procesada con el formatter de EP014 US-NEW-040 (se guarda PDF/MD en `/data/test-artifacts/` como prueba).
- [ ] DEC-023, DEC-024, DEC-025 registrados en DECISIONS.md.
