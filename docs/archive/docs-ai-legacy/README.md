---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Docs IA — Archivo legacy (pre-DEC-017)

**Archivados:** 2026-04-23 como parte de ENH-022 (follow-up de BUG-027).

Estos archivos describen el **diseño de IA del MVP** (US-044/045/046/047/048
+ EP008 versión original): una cascada de 3 proveedores

```
Ollama local (vía Tailscale tailnet)
    ↓ fallback si down/lento
Gemini 1.5 Flash (Google, free tier)
    ↓ fallback final premium
Claude Sonnet (Anthropic, pay-as-you-go)
```

Con modos por-tenant como `private_only`, `private_first`, `cloud_first`,
`claude_only`, `disabled`.

## ¿Por qué están archivados?

En **US-057 + DEC-017 (Sprint 2 v1.1, 2026-04-22)** la cascada global
fue reemplazada por **3 modos por-tenant** (`disabled | platform | byo`):

- `platform` usa Groq hosteado por la plataforma. Ollama tailnet dejó
  de ser parte del flujo productivo.
- `byo` deja al tenant configurar su propio proveedor (OpenAI / Claude
  / Gemini / Perplexity) vía `/admin/ai`.
- Ollama queda soportado en el worker como valor legacy BYO pero ya no
  se ofrece desde la UI (DEC-019).

Los conceptos técnicos que siguen vigentes (schemas Pydantic,
guardrails, chunking, A/B testing de prompts) **no se perdieron** —
viven en `docs/ai/prompts-catalog.md` y en el código
(`apps/api/app/services/ai/`).

## ¿Cuándo consultar estos archivos?

- Analizar el razonamiento del pivote Ollama → Groq.
- Revisar la comparativa de modelos Ollama / hardware si un tenant
  legacy quiere configurar Ollama como BYO propio (requiere setup
  manual, no hay wizard oficial).
- Auditoría histórica de decisiones.

## Archivos aquí

- `cascade-design.md` — diseño de cascada original (ollama → gemini →
  claude) con modos por-tenant legacy. Era `docs/ai/README.md`.
- `gemini-setup.md` — setup de Gemini como fallback #2 en la cascada.
- `local-model-setup.md` — comparativa de modelos Ollama + hardware +
  cuantización (Qwen 2.5, Llama, Phi, Gemma).
- `local-ollama-setup.md` — setup Ollama en Windows (CF Tunnel + nssm
  original, después se actualizó a Tailscale vía US-046/047).

## Docs vigentes

- [`docs/ai/README.md`](../../ai/README.md) — índice actual.
- [`docs/ai/prompts-catalog.md`](../../ai/prompts-catalog.md) —
  prompts versionados de producción.
- [`docs/runbooks/ai/`](../../runbooks/ai/) — runbooks de operación
  (Groq + BYO).

## Decisiones relevantes

- **DEC-017** — IA multi-modo por tenant (retiró la cascada global).
- **DEC-019** — Catálogo BYO sin Ollama + feature flag del wizard.
- **EP008** — Epic IA (actualizado post-DEC-017).
- **EP016** — Epic tunnel Ollama local, archivada en
  [`docs/archive/cancelled-epics/EP016-local-ai-tunnel.md`](../cancelled-epics/EP016-local-ai-tunnel.md).
