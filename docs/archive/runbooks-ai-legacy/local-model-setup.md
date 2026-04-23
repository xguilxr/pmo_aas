# Comparativa de modelos y elección

**ID:** `DOC-AI-MODELS`

Referencia para elegir qué modelo descargar según tu hardware y use case.

---

## 1. Tabla comparativa

| Modelo | Parámetros | RAM (Q4) | VRAM GPU | Calidad ES | Resumen | Velocidad | Recomendado para |
|---|---:|---:|---:|---|---|---|---|
| **Qwen 2.5 7B** | 7.6B | ~6 GB | 6 GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 20–60 tok/s | **MVP default** |
| Qwen 2.5 14B | 14B | ~10 GB | 10 GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 15–50 tok/s | Mejor calidad |
| Llama 3.1 8B | 8B | ~6 GB | 6 GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | 25–70 tok/s | Meta alts |
| Llama 3.3 70B | 70B | ~42 GB | 42 GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 5–20 tok/s | Sólo H100/A100 |
| Gemma 2 9B | 9B | ~6 GB | 6 GB | ⭐⭐⭐⭐ | ⭐⭐⭐ | 30–80 tok/s | Google alt |
| Phi-3.5 Mini | 3.8B | ~3 GB | 3 GB | ⭐⭐ | ⭐⭐⭐ | 60–150 tok/s | Laptop sin GPU |

---

## 2. Recomendación por hardware

| Hardware | Modelo default | Alternativas |
|---|---|---|
| **MacBook Air M2 8GB** | `qwen2.5:3b-instruct-q4_K_M` | `phi3.5:mini` |
| **MacBook Pro M2/M3 16GB** | `qwen2.5:7b-instruct-q4_K_M` | `llama2:7b` |
| **Mac Studio 64GB** | `qwen2.5:14b-instruct-q4_K_M` | `qwen2.5:32b-instruct-q4_K_M` |
| **Linux GPU 8–12GB** | `qwen2.5:7b-instruct-q5_K_M` | `llama2:7b` |
| **Linux GPU 24GB+** | `qwen2.5:14b-instruct-q5_K_M` | `qwen2.5:32b-instruct-q4_K_M` |
| **Windows (home-host)** | `qwen2.5:7b-instruct-q4_K_M` | — |

**MVP elegido:** `qwen2.5:7b-instruct-q4_K_M`
- 4.4 GB en disco.
- 6–8 GB RAM típico.
- Excelente soporte español.
- Sigue instrucciones JSON confiable.

---

## 3. Descargar un modelo

```bash
ollama pull qwen2.5:7b-instruct-q4_K_M

# Alternativamente, sin ser default (ej. para comparativas)
ollama pull llama2:7b
ollama pull gemma:7b
```

Ver disponibles en https://ollama.com/library.

---

## 4. Crear cuantización custom (Q4 vs Q5)

Si necesitas mayor precisión o mayor velocidad:

```bash
# Ver oferta de cuantizaciones de un modelo
ollama pull qwen2.5:latest --list

# Alternativas comunes:
# - q4_K_M: balance calidad/velocidad (default MVP)
# - q5_K_M: mejor calidad, 20% más lento
# - q6_K: máxima calidad, 40% más lento
# - q3_K_M: rápido pero baja calidad
```

---

## 5. Fine-tuning local (post-MVP)

Con 500+ minutas corregidas por humanos, entrenar **LoRA** sobre Qwen 2.5:

```bash
# Preparar dataset
# ... (procesar minutas con anotaciones)

# Fine-tuning con Ollama (si soporta LoRA)
# O usar frameworks externos (HuggingFace, LLaMA-Factory)
ollama create pmo-minute-tuned -f Modelfile
```

Esto mejora significativamente calidad en dominio PMO sin coste de cloud.

---

## 6. Context window y chunking

Qwen 2.5 soporta 128k tokens nativos, pero Ollama default es 2048. Para minutas largas:

```bash
cat > Modelfile <<EOF
FROM qwen2.5:7b-instruct-q4_K_M
PARAMETER num_ctx 16384
PARAMETER temperature 0.3
EOF
ollama create pmo-minute-model -f Modelfile
```

Si transcript aún excede 16k tokens, usar **chunking**:

```python
def generate_minute_chunked(transcript: str):
    chunks = chunk_text(transcript, max_tokens=3000, overlap=200)
    partial_results = [extract_from_chunk(c) for c in chunks]
    final = merge_minute_partials(partial_results)
    return final
```

---

## 7. Parámetros de generación (temperature, top_p)

```json
{
  "temperature": 0.3,  // 0.0 = determinístico (resumen), 0.9 = creativo
  "top_p": 0.9,        // nucleus sampling; bajar a 0.7 para más foco
  "num_ctx": 16384,    // context window
  "num_predict": 2048, // max tokens generados
  "repeat_penalty": 1.05 // penaliza repetición de tokens
}
```

Para minutas y reportes: `temperature=0.2–0.4` (estable, menos creatividad).

---

## 8. Benchmarks en casa (tu hardware)

```bash
# Velocidad de generación
time ollama run qwen2.5:7b-instruct-q4_K_M "Genera 500 palabras sobre PMO"

# Token count
echo "Tu texto largo" | wc -w  # aprox 0.75 tokens per word

# Latencia de primer token (TTFT)
# ...log de Ollama muestra timing
```

---

## 9. Troubleshooting

| Síntoma | Causa | Solución |
|---|---|---|
| Modelo muy lento (< 5 tok/s) | sin GPU activada | `nvidia-smi` en Linux, verificar config macOS |
| Output roto | temperature muy alta | bajar a 0.1–0.2 |
| Modelo no en español | modelo base inglés | cambiar a Qwen o Llama multilingüe |
| Memoria agotada (OOM) | modelo muy grande para hardware | bajar a modelo más chico o usar Q3 cuantización |
| Alucinaciones frecuentes | prompt ambiguo | mejorar prompt con few-shot examples |

---

## 10. Checklist

- [ ] Hardware identificado (RAM, GPU, CPU cores).
- [ ] Modelo descargado: `ollama list`.
- [ ] Humo test: `ollama run <model> "test"`.
- [ ] Latencia medida (tok/s esperados vs reales).
- [ ] Context window configurado si necesario (> 2048).
- [ ] Parámetros de generación ajustados (temperature).
- [ ] Prompt template de minuta testeado en dev.
- [ ] Fallback a Gemini + Claude configurado.

---

## Referencias

- Ollama library — https://ollama.com/library
- Qwen 2.5 docs — https://github.com/QwenLM/Qwen2.5
- Fine-tuning LoRA — https://github.com/hiyouga/LLaMA-Factory
- Runbook Ollama — [`docs/runbooks/ai/local-ollama-setup.md`](./local-ollama-setup.md)
