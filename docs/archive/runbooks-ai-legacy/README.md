---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Runbooks IA — Archivo legacy (pre-DEC-017)

**Archivados:** 2026-04-23 como parte de BUG-027 (follow-up DEC-019).

Estos runbooks describen el **modelo de cascada IA del MVP** (US-045,
US-047, US-048): Ollama local vía Tailscale como proveedor #1, Gemini
como fallback #2, Claude como fallback #3. El modo se seleccionaba con
la env var global `AI_MODE` + la config per-tenant `settings.ai_mode`.

Ese diseño quedó **retirado en US-057 + DEC-017 (Sprint 2 v1.1)**. El
nuevo modelo usa 3 modos por-tenant (`disabled | platform | byo`) con
Groq como IA base de la plataforma y 4 proveedores cloud (OpenAI,
Claude, Gemini, Perplexity) para BYO. Ollama queda soportado en el
worker como valor legacy pero ya no se ofrece desde la UI.

## ¿Cuándo consultar estos archivos?

- Si encuentras un tenant con `settings.ai.ollama.base_url` en BD y
  necesitas entender cómo se configuraba originalmente el tailnet.
- Si reactivamos Ollama como opción BYO oficial (hoy queda soportado
  sólo para tenants legacy).
- Auditoría histórica / análisis retro-compat.

## ¿Qué runbooks están activos?

Ver `docs/runbooks/ai/`:

- [`groq-setup.md`](../../runbooks/ai/groq-setup.md) — modo `platform`
  (IA base de la plataforma).
- [`byo-setup.md`](../../runbooks/ai/byo-setup.md) — modo `byo`
  (proveedor propio del tenant).

## Archivos aquí

- `claude-setup.md` — setup de Claude como fallback #3 (pre-DEC-017).
- `gemini-setup.md` — setup de Gemini como fallback #2 (pre-DEC-017).
- `local-model-setup.md` — selección de modelo Ollama + hardware.
- `local-ollama-setup.md` — Ollama + Tailscale tailnet (US-047).

## Decisiones relevantes

- **DEC-017** — IA multi-modo por tenant (retiró la cascada global).
- **DEC-019** — Catálogo BYO sin Ollama + feature flag del wizard.
