# Capa de IA — PMO-aaS

**ID:** `DOC-AI`

Documentación de cómo integramos IA generativa en la plataforma: selección de modelo, setup local, fallback cloud, prompts.

## Archivos

- [`local-model-setup.md`](./local-model-setup.md) — Ollama, hardware, modelos recomendados, integración con Railway
- [`prompts-catalog.md`](./prompts-catalog.md) — Prompts versionados para minutas y reportes
- (futuro) `fine-tuning.md` — si llegamos a afinar

## Estrategia

Usamos IA **solo** para dos tareas concretas del MVP:

1. **Redacción de minutas** a partir de transcripciones.
2. **Generación de reportes de avance** con datos del proyecto.

En ambas, la IA produce un **borrador estructurado** que el humano revisa y aprueba. Nunca auto-envía nada.

## Modos soportados

| Modo | Cuándo | Ventaja | Desventaja |
|---|---|---|---|
| `ollama` (local) | Default / tenants con datos sensibles | $0 por token, privado, sin límite | Requiere hardware dedicado, latencia variable |
| `claude` (cloud) | Tenants que prefieren calidad | Muy alta calidad, rápido | Coste por token, data sale del perímetro |
| `disabled` | Tenants que no quieren IA | — | — |

Configurado por tenant en `tenants.settings.ai`.

## Contrato técnico (agnóstico)

El módulo `apps/api/app/ai/` expone una interfaz única:

```python
class AIProvider(Protocol):
    async def generate_minute(self, transcript: str, context: ProjectContext, lang: str) -> MinuteDraft: ...
    async def generate_report(self, project_data: ProjectSnapshot, style: str, lang: str) -> ReportDraft: ...

class OllamaProvider(AIProvider): ...
class ClaudeProvider(AIProvider): ...
```

El worker selecciona el provider según `tenant.settings.ai.mode` y falla elegantemente si no disponible.

## Validación de outputs

- Todo output del modelo se **parsea como JSON** contra un Pydantic schema.
- Si falla: 1 reintento con prompt corregido explicitando el formato.
- Si falla otra vez: job `failed`, usuario ve mensaje claro + opción de reintentar manual.

## Privacy-first

- Ningún prompt incluye PII más allá de nombres y correos (lo imprescindible).
- El admin del tenant autoriza explícitamente el modo Claude; se muestra banner.
- Logs de IA no guardan el texto completo — solo hash + metadata. El texto vive en `ai_jobs.output` con acceso restringido.

## Observabilidad

Métricas capturadas por job:
- Modelo usado
- Tokens in / out
- Duración
- Éxito / Fallo (tipo de error)
- Tenant / Project / User

Dashboard en `/admin/ai` para consumo del admin.
