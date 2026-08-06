---
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Setup de Google Gemini (2.º proveedor — free tier)

**ID:** `DOC-AI-GEMINI`

Guía para habilitar Gemini 1.5 Flash como segundo proveedor de IA en la
cascada (Ollama → **Gemini** → Claude).

---

## 1. ¿Por qué Gemini?

- **Free tier real y público**: 15 RPM, 1 000 000 tokens/día, sin tarjeta.
- Calidad suficiente para minutas y reportes (≈ Qwen 2.5 14B en ES).
- SDK oficial Python maduro (`google-generativeai`).
- JSON mode confiable con `response_schema`.
- Caching automático disponible (`context_caching`) para contextos > 32k.

**Limitación principal**: rate limit 15 RPM. Para > 10 tenants activos con
IA intensiva es justo; por eso sigue siendo el **segundo** proveedor.

---

## 2. Obtener API key

1. Ve a https://aistudio.google.com/app/apikey (login con Google).
2. "Create API key" → asigna a un proyecto GCP (crea uno si no tienes).
3. Copia la key `AIza…`.
4. En producción: guárdala en Railway variable `GEMINI_API_KEY` del servicio
   `api` (y `worker` si aplica).

---

## 3. Instalación

```bash
pip install google-generativeai==0.8.*
```

---

## 4. Configuración en Railway

Ver [`docs/runbooks/railway/SETUP.md`](../railway/SETUP.md) §3.2 para agregar variables.

**Servicio `api`:**
- `GEMINI_API_KEY` = `AIza…` (la key del paso anterior)
- `GEMINI_MODEL` = `gemini-1.5-flash` (default)

---

## 5. Configuración por tenant

En `tenants.settings.ai`:

```json
{
  "mode": "private_first",
  "providers": ["ollama", "gemini", "claude"],
  "gemini": {
    "api_key_ref": "global",
    "model": "gemini-1.5-flash",
    "timeout_sec": 60
  }
}
```

`api_key_ref=global` significa que usa la key de la plataforma (no del tenant).

---

## 6. Manejo del rate limit

- **Client-side**: `google-generativeai` tiene retry built-in con backoff exponencial para 429.
- **Server-side**: Redis token bucket por proveedor global.
  ```python
  # apps/api/app/ai/rate_limit.py
  GEMINI_BUCKET = "ai:ratelimit:gemini:global"
  # 15 requests por 60s rolling
  ```
- Si el bucket está vacío, el cascade salta a provider #3 (Claude) si está
  disponible, o reencola con `countdown=60s`.

---

## 7. Test de conexión

`POST /api/v1/admin/ai-settings/test` con `provider=gemini`:

```python
@router.post("/admin/ai-settings/test")
async def test_provider(payload: TestProviderIn, admin = Depends(admin_user)):
    if payload.provider == "gemini":
        p = GeminiProvider(api_key=payload.api_key or settings.GEMINI_API_KEY)
        start = time.time()
        try:
            resp = await p.model.generate_content_async("Responde: pong")
            return {"ok": True, "latency_ms": int((time.time()-start)*1000),
                    "sample": resp.text[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)}
```

UI muestra "online" verde, "slow" amarillo (>3s), "error" rojo.

---

## 8. Fallback y cascada

Gemini se invoca cuando:

- Ollama está `unhealthy` (ping falla 3 veces seguidas).
- Ollama devuelve error 5xx o timeout.
- Tenant tiene `providers=["gemini", ...]` (Gemini como primero explícito).

Log cada fallback con `ai_cascade_fallback_total{from="ollama", to="gemini"}`
para saber cuánto dependes del free tier.

---

## 9. Límites y costos

- **Free**: 15 RPM, 1M tokens/día.
- **Paid**: pay-as-you-go.
- Ver https://ai.google.dev/pricing.

Para MVP + primeros clientes (≤ 50 minutas/día) el tier Free cubre.

---

## 10. Alternativas si Gemini se queda corto

| Opción | Costo | Cuándo |
|---|---|---|
| Google AI Studio paid | pay-as-you-go | 10× cuota |
| Groq free tier (Llama 3.1) | $0 | backup adicional |
| Mistral Small (La Plateforme) | free tier | si priorizas EU |

---

## Referencias

- Google Generative AI docs — https://ai.google.dev/docs
- Rate limiting — [`docs/runbooks/railway/SETUP.md`](../railway/SETUP.md) §3.2
- Cascada IA — [`docs/runbooks/ai/claude-setup.md`](./claude-setup.md)
