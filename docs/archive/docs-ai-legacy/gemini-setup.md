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
IA intensiva es justo; por eso sigue siendo el **segundo** proveedor, no el
primero.

---

## 2. Obtener API key

1. Ve a https://aistudio.google.com/app/apikey (login con Google).
2. "Create API key" → asigna a un proyecto GCP (crea uno si no tienes).
3. Copia la key `AIza…`.
4. En producción: guárdala en Railway variable `GEMINI_API_KEY` del servicio
   `api` (y `worker` si aplicable).
5. En desarrollo: en `.env` como `GEMINI_API_KEY=AIza…`.

---

## 3. Instalación

```bash
pip install google-generativeai==0.8.*
```

---

## 4. Provider implementation (referencia)

```python
# apps/api/app/ai/providers/gemini.py
import google.generativeai as genai
from .base import AIProvider, ProviderError

class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": 0.3,
                "response_mime_type": "application/json",
            },
        )

    async def generate_minute(self, transcript, context, lang):
        prompt = render_prompt("minute.from_transcript.v2",
                               transcript=transcript, context=context, lang=lang)
        try:
            resp = await self.model.generate_content_async(prompt)
            return MinuteDraft.model_validate_json(resp.text)
        except Exception as e:
            raise ProviderError(f"gemini: {e}") from e

    def healthy(self) -> bool:
        # ping cached 60s
        return self._ping_cached(timeout=2)
```

---

## 5. Configuración por tenant

En `tenants.settings.ai`:

```json
{
  "mode": "private_first",
  "providers": ["ollama", "gemini", "claude"],
  "ollama": { ... },
  "gemini": {
    "api_key_ref": "global",
    "model": "gemini-1.5-flash",
    "timeout_sec": 60
  },
  "claude": null
}
```

`api_key_ref=global` significa que usa la key de la plataforma (no del
tenant). Si el tenant trae su propia key (para cuota propia), se guarda
cifrada en `tenants.secrets.gemini_key` y se referencia como
`api_key_ref="tenant"`.

---

## 6. Manejo del rate limit

- **Client-side**: `google-generativeai` tiene retry built-in con backoff
  exponencial para 429. Lo dejamos activo.
- **Server-side (nuestro)**: Redis token bucket por proveedor global.
  ```python
  # apps/api/app/ai/rate_limit.py
  GEMINI_BUCKET = "ai:ratelimit:gemini:global"
  # 15 requests por 60s rolling
  ```
- Si el bucket está vacío, el cascade salta a provider #3 (Claude) si está
  disponible, o falla con `ai_rate_limited` y reencola con `countdown=60s`.

---

## 7. Prompt caching (context caching)

Para reportes quincenales del mismo proyecto, el contexto cambia poco.
Gemini soporta **context caching**:

```python
cache = genai.caching.CachedContent.create(
    model="gemini-1.5-flash",
    contents=[large_project_snapshot_json],
    ttl="1h"
)
model = genai.GenerativeModel.from_cached_content(cache)
```

Coste efectivo en free tier: **no reduce tu cuota de tokens/día**, pero sí
latencia y carga de red.

---

## 8. Test de conexión

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

## 9. Fallback y cascada

La orquestación vive en `AIProviderCascade` (ver `docs/ai/README.md`).
Gemini se invoca cuando:

- Ollama está `unhealthy` (ping falla 3 veces seguidas).
- Ollama devuelve error 5xx o timeout > `OLLAMA_TIMEOUT_SEC`.
- Tenant tiene `providers=["gemini", ...]` (Gemini como primero explícito).

Log cada fallback con `ai_cascade_fallback_total{from="ollama", to="gemini"}`
para saber cuánto dependes del free tier.

---

## 10. Alternativas si Gemini free tier se queda corto

| Opción | Costo | Cuándo |
|---|---|---|
| Google AI Studio paid | pay-as-you-go | 10× cuota |
| Groq free tier (Llama 3.1) | $0 | backup adicional |
| Mistral Small via La Plateforme | free tier | si priorizas EU |
| Cerebras Inference free | $0 limited | ultra-rápido, límites mensuales |

Documento dedicado post-MVP si llegamos a saturar Gemini.
