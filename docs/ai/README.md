# Capa de IA — PMO·aaS

**Actualizado:** 2026-04-23 (post-DEC-017 + ENH-022).

Documentación técnica vigente de la IA generativa en la plataforma.

## Archivos activos

- [`prompts-catalog.md`](./prompts-catalog.md) — prompts versionados
  (`minute.from_transcript.v2`, `report.progress_draft.v1`,
  `transcript.chunk_merge.v1`) con sus schemas Pydantic, few-shot y
  reglas de guardrails. Es la **única doc técnica** que queda aquí —
  los runbooks de operación viven en `docs/runbooks/ai/`.

## Runbooks de operación

Ver [`docs/runbooks/ai/`](../runbooks/ai/):

- [`groq-setup.md`](../runbooks/ai/groq-setup.md) — habilitar Groq como
  IA base de la plataforma (modo `platform` de US-057).
- [`byo-setup.md`](../runbooks/ai/byo-setup.md) — conectar un proveedor
  BYO (OpenAI / Claude / Gemini / Perplexity) desde `/admin/ai`.

## Arquitectura vigente

Desde US-057 + DEC-017 la IA funciona con **tres modos por-tenant**
(`disabled | platform | byo`):

| Modo | Proveedor | Scope | Costo |
|---|---|---|---|
| `disabled` | — | IA apagada | $0 |
| `platform` | Groq (`llama-3.3-70b-versatile`) | sólo minutas | hosteado por plataforma, free tier |
| `byo` | OpenAI / Claude / Gemini / Perplexity | minutas + reportes | a cuenta del tenant |

Ver `docs/epics/EP008-ai.md` para el modelo completo y
`docs/epics/DECISIONS.md` para el historial de decisiones (DEC-017,
DEC-019).

## Historial y diseño superseded

El diseño original (cascada `ollama → gemini → claude` vía Tailscale
tailnet) quedó archivado en:

- [`docs/archive/docs-ai-legacy/`](../archive/docs-ai-legacy/) — docs
  de la cascada (README, Gemini setup, Ollama setup, local model
  comparison).
- [`docs/archive/cancelled-epics/EP016-local-ai-tunnel.md`](../archive/cancelled-epics/EP016-local-ai-tunnel.md)
  — épica del tunnel Ollama (superseded por DEC-017).
- [`docs/archive/runbooks-ai-legacy/`](../archive/runbooks-ai-legacy/)
  — runbooks de operación pre-DEC-017.
