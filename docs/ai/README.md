# Capa de IA — PMO-aaS

**ID:** `DOC-AI`

Documentación de cómo integramos IA generativa en la plataforma: selección de
modelo, cascada de proveedores, hosting local, prompts.

## Archivos

- [`local-model-setup.md`](./local-model-setup.md) — Ollama, hardware, modelos, home-host con Cloudflare Tunnel, Railway GPU.
- [`gemini-setup.md`](./gemini-setup.md) — Segundo proveedor gratuito (Gemini 1.5 Flash).
- [`prompts-catalog.md`](./prompts-catalog.md) — Prompts versionados para minutas y reportes.
- (futuro) `fine-tuning.md` — si llegamos a afinar.

---

## Estrategia — cascada de 3 proveedores

Ver ADR-007. Orden de prioridad por default:

| # | Proveedor | Privacidad | Costo | Calidad | Cuándo se usa |
|---|---|---|---|---|---|
| 1 | **Ollama local** (default) | ⭐⭐⭐⭐⭐ | **$0/token** | ⭐⭐⭐⭐ | Siempre que esté healthy |
| 2 | **Gemini 1.5 Flash** (free tier) | ⭐⭐ | **$0** (1M tok/día) | ⭐⭐⭐⭐ | Si Ollama down/lento o tenant lo prefiere |
| 3 | **Claude Sonnet 4.6** | ⭐⭐ | ~$0.02/minuta | ⭐⭐⭐⭐⭐ | Solo si tenant lo activa + aporta API key |

La cascada se ejecuta **por request**: el `AIProviderCascade` intenta #1, si
falla (timeout, error, unhealthy) pasa a #2, y así. La política por tenant
puede desactivar cualquier proveedor.

```python
# apps/api/app/ai/cascade.py (pseudo)
class AIProviderCascade(AIProvider):
    def __init__(self, tenant_settings):
        self.providers = build_chain(tenant_settings.ai.providers)

    async def generate_minute(self, transcript, ctx, lang):
        last_err = None
        for p in self.providers:
            if not p.healthy(): continue
            try:
                return await p.generate_minute(transcript, ctx, lang)
            except ProviderError as e:
                last_err = e; log.warning(f"{p.name} failed, cascading: {e}")
        raise AIUnavailable(last_err)
```

## Modos soportados por tenant

| Modo | Providers habilitados | Recomendado para |
|---|---|---|
| `private_only` | ollama | Tenants con data sensible o compliance estricto |
| `private_first` (default) | ollama → gemini → claude? | MVP / mayoría de tenants |
| `cloud_first` | gemini → claude | Tenants sin preferencia de privacidad |
| `claude_only` | claude | Tenants que traen su API key y quieren máxima calidad |
| `disabled` | — | IA apagada |

Configurado por tenant en `tenants.settings.ai.mode` + `tenants.settings.ai.providers`.

## Contrato técnico

```python
class AIProvider(Protocol):
    name: str
    async def generate_minute(self, transcript: str, context: ProjectContext, lang: str) -> MinuteDraft: ...
    async def generate_report(self, project_data: ProjectSnapshot, style: str, lang: str) -> ReportDraft: ...
    def healthy(self) -> bool: ...

class OllamaProvider(AIProvider): ...
class GeminiProvider(AIProvider): ...
class ClaudeProvider(AIProvider): ...
class AIProviderCascade(AIProvider): ...
```

## Validación de outputs

- Todo output se **parsea como JSON** contra un Pydantic schema.
- Si falla: 1 reintento con prompt corregido explicitando el formato.
- Si falla otra vez: job `failed`, usuario ve mensaje claro + opción de reintentar manual.
- Métrica por provider: `ai_retries_total{provider, kind}`.

## Privacy-first

- **Ollama no envía data fuera** por construcción.
- **Gemini**: Google procesa el texto. El admin del tenant debe aceptarlo
  explícitamente (banner en `/admin/ai`). No se usa para entrenamiento si se
  marca `user_data_use=opt_out` (disponible en Gemini API).
- **Claude**: igual que Gemini. Anthropic no entrena con inputs de API por
  default, pero el admin debe activarlo explícitamente.
- Logs de IA no guardan el texto completo — solo `hash + metadata`. El texto
  vive en `ai_jobs.output` con acceso restringido por RLS.

## Observabilidad

Métricas capturadas por job:
- `ai_request_duration_seconds{provider, model, kind}`
- `ai_tokens_total{provider, direction=in|out}`
- `ai_failures_total{provider, error_type}`
- `ai_cascade_fallback_total{from, to}`

Dashboard en `/admin/ai` con consumo del mes, tokens top projects, health de
cada provider.
