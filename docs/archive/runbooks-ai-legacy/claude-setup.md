---
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Setup de Claude (3.º proveedor — fallback premium)

**ID:** `DOC-AI-CLAUDE`

Guía para habilitar Claude Sonnet como tercer proveedor de IA en la
cascada (Ollama → Gemini → **Claude**).

---

## 1. ¿Por qué Claude?

- **Mejor calidad**: Claude Sonnet 4.6 es SOTA en resumen y análisis.
- **Pricing razonable**: ~$0.003 por 1k tokens de input (es caro vs Gemini free,
  pero mejor que pagar GPU).
- **Contexto de 200k tokens**: permite procesar minutas de reuniones largas sin chunking.
- **Batch API**: procesa jobs en off-peak con 50% descuento (post-MVP).

**Limitación**: requiere pago. Solo se invoca cuando Ollama + Gemini fallan.

---

## 2. Obtener API key

1. Ve a https://console.anthropic.com/ (crea cuenta o login).
2. **API Keys** → **Create Key**.
3. Copia la key `sk-ant-…`.
4. En producción: guárdala en Railway variable `ANTHROPIC_API_KEY` del servicio
   `api` (y `worker` si aplica).

---

## 3. Instalación

```bash
pip install anthropic>=0.20.0
```

---

## 4. Configuración en Railway

Ver [`docs/runbooks/railway/SETUP.md`](../railway/SETUP.md) §3.2 para agregar variables.

**Servicio `api`:**
- `ANTHROPIC_API_KEY` = `sk-ant-…` (la key del paso anterior)
- `ANTHROPIC_MODEL` = `claude-sonnet-4-6` (default, o `claude-opus-4-7` para máxima calidad)

---

## 5. Configuración por tenant

En `tenants.settings.ai`:

```json
{
  "mode": "private_first",
  "providers": ["ollama", "gemini", "claude"],
  "claude": {
    "api_key_ref": "global",
    "model": "claude-sonnet-4-6",
    "max_tokens": 4096,
    "temperature": 0.4
  }
}
```

---

## 6. Fallback y cascada

Claude se invoca cuando:

- Ollama está `unhealthy` (ping falla 3× seguidas).
- Gemini está `unhealthy` (rate limit alcanzado o error persistente).
- Tenant tiene `providers=[..., "claude"]` (explícito).

Log cada fallback con `ai_cascade_fallback_total{from="gemini", to="claude"}`
para estimar coste.

---

## 7. Monitoreo de costes

Para evitar surpresas, agregar alertas en Railway o Sentry:

- Log cada llamada a Claude con `tokens_in` + `tokens_out`.
- Alertar si `cost_per_day > $1.00` (threshold que define el owner).

Pseudocódigo:
```python
CLAUDE_INPUT_COST_PER_1M = 3.00   # $/M tokens
CLAUDE_OUTPUT_COST_PER_1M = 15.00

cost = (tokens_in * CLAUDE_INPUT_COST_PER_1M + 
        tokens_out * CLAUDE_OUTPUT_COST_PER_1M) / 1_000_000

log.info(f"claude_call_cost={cost:.4f}")
```

---

## 8. Test de conexión

`POST /api/v1/admin/ai-settings/test` con `provider=claude`:

```python
@router.post("/admin/ai-settings/test")
async def test_provider(payload: TestProviderIn, admin = Depends(admin_user)):
    if payload.provider == "claude":
        client = Anthropic(api_key=payload.api_key or settings.ANTHROPIC_API_KEY)
        start = time.time()
        try:
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=100,
                messages=[{"role": "user", "content": "Responde: pong"}]
            )
            return {"ok": True, "latency_ms": int((time.time()-start)*1000),
                    "sample": resp.content[0].text[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)}
```

---

## 9. Batch API (post-MVP)

Para escalar sin coste, Anthropic ofrece **Batch API** (~50% descuento):

```python
# Procesa jobs en off-peak (después de las 24h)
batch = client.beta.messages.batches.create(
    requests=[
        {"custom_id": f"minute-{id}", "params": {...}},
        ...
    ]
)
# Revisar estado periódicamente, procesar resultados cuando completo
```

Implementar en post-MVP si costo se convierte en blocker.

---

## 10. Límites y costos

- **Pricing**: https://www.anthropic.com/pricing
  - Sonnet 4.6: $3/M input, $15/M output tokens
  - Opus 4.7: $15/M input, $75/M output tokens
- **Rate limits**: 100k RPM (suficiente para MVP).

Para 50 minutas/día × 10k tokens promedio = 500k tokens/día ≈ $2/día (input) + $5/día (output) = ~$210/mes.

Si coste es problema, desactivar Claude (`providers=["ollama", "gemini"]`) o subir threshold.

---

## 11. Disable/rollback

Para deshabilitar Claude sin quitar código:

1. Railway → `api` → borrar `ANTHROPIC_API_KEY`.
2. Restart del servicio.
3. Cascada salta de Gemini → error (notificación al tenant).

---

## Referencias

- Anthropic docs — https://docs.anthropic.com/
- Batch API — https://docs.anthropic.com/en/docs/build/batch
- Pricing — https://www.anthropic.com/pricing
- Railway setup — [`docs/runbooks/railway/SETUP.md`](../railway/SETUP.md) §3.2
- Cascada IA — [`docs/runbooks/ai/gemini-setup.md`](./gemini-setup.md)
