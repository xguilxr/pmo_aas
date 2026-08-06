---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Setup de Ollama local

**ID:** `DOC-AI-OLLAMA`

Guía completa para instalar, configurar y operar Ollama (motor de inferencia local)
para generar minutas y reportes en PMO·aaS.

Este runbook reemplaza el previo que usaba Cloudflare Tunnel (ver `docs/epics/EP016`
para detalles). El nuevo diseño usa Tailscale (ver [`docs/runbooks/networking/tailscale-setup.md`](../networking/tailscale-setup.md)).

---

## 1. Comparativa de modelos

| Modelo | Parámetros | RAM (Q4) | VRAM GPU | Calidad ES | Calidad resumen | Recomendado para |
|---|---:|---:|---:|---|---|---|
| **Qwen 2.5 7B Instruct** | 7.6B | ~6 GB | 6 GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **Default MVP** — mejor relación calidad/velocidad |
| Qwen 2.5 14B Instruct | 14B | ~10 GB | 10 GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Servidores con GPU decente |
| Llama 3.1 8B Instruct | 8B | ~6 GB | 6 GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | Alternativa Meta |
| Llama 3.3 70B (Q4) | 70B | ~42 GB | 42 GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Solo si tienes H100 / A100 40G |
| Gemma 2 9B | 9B | ~6 GB | 6 GB | ⭐⭐⭐⭐ | ⭐⭐⭐ | Alternativa Google |
| Phi-3.5 Mini | 3.8B | ~3 GB | 3 GB | ⭐⭐ | ⭐⭐⭐ | Laptops sin GPU |

**Recomendación por escenario:**

| Hardware | Modelo | Cuantización |
|---|---|---|
| MacBook Air M2 8 GB (dev local) | `qwen2.5:3b-instruct-q4_K_M` o `phi3.5:mini` | Q4_K_M |
| MacBook Pro M2/M3 16-32 GB (dev) | `qwen2.5:7b-instruct-q4_K_M` | Q4_K_M |
| Mac Studio / workstation 64 GB | `qwen2.5:14b-instruct-q4_K_M` | Q4_K_M |
| Servidor Linux con GPU 8-12 GB | `qwen2.5:7b-instruct` | Q5_K_M |
| Servidor con GPU 24 GB+ | `qwen2.5:14b-instruct` | Q5_K_M |

**Nuestra elección default para MVP**: **`qwen2.5:7b-instruct-q4_K_M`**
- 4.4 GB en disco, 6-8 GB RAM en uso.
- Excelente español, sigue instrucciones JSON bien.
- Latencia ~20 tok/s en M2, ~60 tok/s en RTX 4060+.

---

## 2. Instalación local

### 2.1 macOS / Linux

```bash
# macOS: Homebrew
brew install ollama
# O descargar .dmg desde https://ollama.com

# Lanzar
ollama serve &

# Linux: curl installer
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable --now ollama

# Ambos: descargar modelo
ollama pull qwen2.5:7b-instruct-q4_K_M

# Smoke test
curl http://localhost:11434/api/tags
# { "models": [ { "name": "qwen2.5:..." } ] }
```

### 2.2 Windows

- Descargar desde https://ollama.com/download/windows.
- MSI con privilegios de admin.
- `ollama` disponible en PowerShell.

```powershell
ollama pull qwen2.5:7b-instruct-q4_K_M
```

### 2.3 Docker

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama-models:
```

```bash
docker-compose up -d
docker exec -it pmoaas-ollama-1 ollama pull qwen2.5:7b-instruct-q4_K_M
```

---

## 3. Hosting en producción

### Opción A — Home-host + Tailscale (recomendado para MVP)

Ver [`docs/runbooks/networking/tailscale-setup.md`](../networking/tailscale-setup.md).

**Ventajas:**
- $0 mes a mes (sin contar electricidad y hardware ya comprado).
- Privacidad total — la data jamás sale a terceros.
- Modelos más grandes que ningún free tier te da.

### Opción B — VPS con GPU (para escalar)

Proveedores económicos (abr 2026):
- **Hetzner GEX44** (L4): ~€250/mes
- **OVH Advance-2** (A4000): ~€220/mes
- **Paperspace Core** (RTX 4000): ~$180/mes

Setup:
```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable --now ollama
ollama pull qwen2.5:7b-instruct-q4_K_M

# Exponer con nginx + TLS
# Ver docs/architecture/deployment-railway.md §11 para detalles
```

### Opción C — Railway GPU (cuando esté disponible)

Ver `docs/runbooks/railway/DEPLOYMENT.md` cuando Railway habilite GPU.

---

## 4. Configuración fina

### Parámetros del modelo

En `tenants.settings.ai`:

```json
{
  "mode": "ollama",
  "ollama": {
    "base_url": "http://ollama-host.<tailnet>.ts.net:11434",
    "auth_user": null,
    "auth_password": null,
    "model": "qwen2.5:7b-instruct-q4_K_M",
    "timeout_sec": 180,
    "options": {
      "temperature": 0.3,
      "top_p": 0.9,
      "num_ctx": 8192,
      "num_predict": 2048,
      "repeat_penalty": 1.05
    }
  }
}
```

`temperature=0.3` para tareas de extracción/resumen (determinístico).

### Context window

Qwen 2.5 soporta 128k tokens, pero Ollama expone `num_ctx` (default 2048).
Para minutas largas, subir a `8192` o `16384`:

```bash
cat > Modelfile <<EOF
FROM qwen2.5:7b-instruct-q4_K_M
PARAMETER num_ctx 16384
PARAMETER temperature 0.3
EOF
ollama create pmo-minute-model -f Modelfile
```

### Chunking si transcript excede context

```python
def generate_minute_chunked(transcript: str):
    chunks = chunk_text(transcript, max_tokens=3000, overlap=200)
    partials = [extract_from_chunk(c) for c in chunks]
    merged = merge_minute_partials(partials)
    return merged
```

---

## 5. Monitoreo y salud

### Healthcheck

Ollama expone `GET /api/tags` — debe retornar 200.

```python
async def check_ollama(base_url: str, timeout: int = 3) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as c:
        try:
            r = await c.get(f"{base_url}/api/tags")
            r.raise_for_status()
            return {"status": "healthy", "latency_ms": int(r.elapsed.total_seconds()*1000),
                    "models": [m["name"] for m in r.json()["models"]]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
```

### Alertas

- `ollama_failures_total` > 5 en 5 min → warning
- `ollama_request_duration_seconds p95` > 30s → warning
- Healthcheck failing → critical, fallback automático a Claude activado

---

## 6. Costos y sizing

Para 10 tenants activos:
- Volumen: 50 minutas/día × 9000 tokens = 450k tokens/día
- Latencia media: 50 tok/s usables → minuta de 1h en ~180 s
- Costo por minuta: ~€0.10 con infra propia vs ~$0.02 con Claude (con cache)

---

## 7. Troubleshooting

| Síntoma | Causa | Solución |
|---|---|---|
| `connection refused` | servicio no arrancado | `systemctl status ollama` o `docker logs ollama` |
| Generación muy lenta (< 5 tok/s) | sin GPU o modelo muy grande | Verificar `nvidia-smi`, bajar a modelo más chico |
| `context window exceeded` | input muy largo | Bajar chunk size o usar modelo con mayor contexto |
| Output roto (no parsea JSON) | temperature alta o prompt ambiguo | Bajar temperature a 0.2, revisar prompt |
| Modelo no responde en español | modelo inglés puro | Cambiar a Qwen (multilingüe) |
| Memory leak | `OLLAMA_KEEP_ALIVE` muy alto | Bajarlo a `5m` o `0` para liberar tras request |
| Race condition con requests | `OLLAMA_NUM_PARALLEL=1` | Subir a `2-4` según VRAM |

---

## 8. Checklist de deploy

- [ ] Ollama accesible desde API/Worker (local o Tailscale).
- [ ] Modelo descargado (`ollama list`).
- [ ] `num_ctx` configurado a ≥ 8192 via Modelfile.
- [ ] Health check integrado en `/admin/ai` con ping periódico.
- [ ] Fallback a Claude configurado y **probado en staging**.
- [ ] Backup del volumen `/root/.ollama` (opcional, ahorra re-pull).
- [ ] Rate limit por tenant configurado (max 5 jobs concurrentes).

---

## Referencias

- Ollama docs — https://ollama.com/docs
- Tailscale networking — [`docs/runbooks/networking/tailscale-setup.md`](../networking/tailscale-setup.md)
- Railway deployment — [`docs/runbooks/railway/DEPLOYMENT.md`](../railway/DEPLOYMENT.md)
- Epic EP016 — [`docs/epics/EP016-local-ai-tunnel.md`](../../epics/EP016-local-ai-tunnel.md)
