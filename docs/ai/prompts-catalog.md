---
tipo: guia
responsable: propietario
estado: vigente
revisado: 2026-07-09
revisar_cada: 180d
---

# Catálogo de Prompts

**ID:** `DOC-AI-PROMPTS`
**Última verificación contra código:** 2026-05-23.

Inventario real de prompts del sistema, ubicación exacta en código, y reglas de cambio.

> **Política:** cambiar un prompt en producción tiene blast radius alto (cambia output que el usuario edita). Va por PR como cualquier otro código. Cuando un prompt cambia, anotarlo abajo con commit/fecha.

---

## 1. Catálogo central — `apps/api/app/services/ai/prompts.py`

Tres prompts viven en este archivo y se importan desde el worker o desde endpoints.

### 1.1 `MINUTE_SYSTEM`

- **Consumido en:** `apps/api/app/workers/tasks/ai.py:331` (task `ai.generate_minute`).
- **Propósito:** estructurar una minuta operativa a partir de una transcripción de reunión.
- **Disponible en:** modo `platform` (Groq) y `byo` (todos los providers).
- **Schema de output** (JSON estricto, sin campos extra):

```json
{
  "header": {
    "title": "string",
    "date": "string|null",
    "time": "string|null",
    "duration": "string|null",
    "modality": "string|null",
    "location": "string|null",
    "facilitator": "string|null"
  },
  "participants": {
    "attendees":          [{"name": "...", "role": "?", "area": "?"}],
    "absent_justified":   [{"name": "...", "role": "?", "area": "?"}],
    "absent_unjustified": [{"name": "...", "role": "?", "area": "?"}]
  },
  "summary": "string (2-3 oraciones)",
  "topics":  [{"title": "...", "bullets": ["...", "..."]}],
  "raid":    [
    {
      "type": "A|R|D|I",
      "description": "...",
      "responsible": "string|null",
      "due_date": "string|null",
      "status": "Open|In Progress|Pending|Closed"
    }
  ],
  "free_notes": "string|null"
}
```

- **Reglas críticas** (codificadas en el system prompt):
  - **ENH-102:** `raid` solo lleva A/R/D/I. **Sin** Lecciones aprendidas ni Solicitudes de cambio (si aparecen en el transcript, se descartan; un validador posterior también las filtra). Cada Acción debe llevar `responsible` y `due_date` si se mencionan.
  - **ENH-105:** las 6 claves van exactas, en ese orden. `topics[*].bullets` son enunciados factuales, no prosa. "Próximos pasos calendarizados" sin responsable van a `free_notes`; con responsable y fecha van a `raid` como Acción.
- **Few-shot anchor:** Highlander EAM-BNF (ver el system prompt para los números target — ~12 temas, 7 acciones, 4 riesgos, 4 decisiones, 1 issue en una sesión de 46 min).

### 1.2 `REPORT_SYSTEM`

- **Consumido en:** `apps/api/app/workers/tasks/ai.py:496` (task `ai.draft_report`).
- **Propósito:** generar el draft estructurado de un reporte ejecutivo.
- **Disponible en:** solo modo `byo`. En modo `platform` el endpoint devuelve `409 AI_PLATFORM_SCOPE_LIMITED` (Groq se limita a minutas; DEC-017).
- **Schema de output** (JSON estricto):

```json
{
  "executive_summary": "...",
  "achievements": ["...", "..."],
  "next_activities": ["...", "..."],
  "top_risks": ["...", "..."],
  "budget_status": "..."
}
```

### 1.3 `HTML_TWEAK_SYSTEM`

- **Consumido en:** `apps/api/app/api/v1/endpoints/ai.py:313` (endpoint `POST /api/v1/ai/reports/tweak-html`).
- **Propósito:** aplicar una instrucción del usuario sobre el HTML de un reporte ya generado.
- **Disponible en:** modo `byo`.
- **Output:** HTML completo (desde `<!DOCTYPE html>` hasta `</html>`), **no JSON**.
- **Reglas críticas:**
  - Preserva clases, estructura `<details>` colapsables, `<style>` inline y JS embebido.
  - Si la instrucción es ambigua, aplica la interpretación más conservadora.

---

## 2. Prompts inline (vivos en su endpoint)

No están en `prompts.py` porque su template depende del estado del request.

### 2.1 `_AI_REPORT_SYSTEM_PROMPT` — `apps/api/app/api/v1/endpoints/reports.py:782`

- **Endpoint:** `POST /projects/{project_id}/reports/ai-generate`.
- **Propósito:** redactar un reporte completo en HTML para un proyecto, listo para mostrar.
- **Reglas (codificadas en string concatenation):**
  - HTML limpio sin wrappers (`<html>`/`<body>`), solo el bloque interno.
  - `<h2>` para títulos de sección, `<p>`/`<ul>` para contenido.
  - **ENH-064:** foco default en (1) hitos, (2) tareas `priority in (high, critical)`, (3) tareas retrasadas (`end_date < hoy AND status != 'done'`). Excluye tareas de baja prioridad y completadas a menos que el user lo pida en notas adicionales.
  - **US-101:** se concatena `REPORT_GLOBAL_ORDER_RULES` (regla global de orden para todo output del módulo de reportes).
  - Máximo 6–8 secciones cortas.

### 2.2 `SYSTEM_PROMPT` — `apps/api/app/api/v1/endpoints/report_builder_chat.py:91`

- **Endpoint:** chat del Report Builder (`/reports/builder` en el frontend).
- **Propósito:** convertir mensajes del usuario en **acciones sobre el canvas** del builder, eligiendo secciones de un **catálogo cerrado** de "secciones atómicas".
- **Output JSON estricto:**

```json
{
  "message": "respuesta corta al usuario",
  "actions": [
    {"type": "add_section", "code": "S-09"},
    {"type": "remove_section", "index": 2},
    {"type": "update_section_params", "index": 0, "params": {"top_n": 5}},
    {"type": "reorder_section", "from": 1, "to": 3}
  ]
}
```

- **Guardrails:** `code` debe existir en el catálogo (se inyecta abajo del system prompt). Índices 0-based. Sin texto fuera del JSON. Si la petición no requiere cambios, `actions: []`.

### 2.3 `_AI_SYSTEM_PROMPT` — `apps/api/app/services/import_mapping_suggest.py:72`

- **Endpoint:** `POST /tasks/import/suggest-mapping` (mapeo automático de columnas al importar `.xlsx`/`.csv`).
- **Propósito:** dado un set de headers del archivo, mapearlos a los `SYSTEM_FIELDS` del importer (campos de la tabla `tasks`).
- **Idioma del prompt:** inglés (el resto son en español).
- **Output JSON estricto:**

```json
{
  "<header_original>": {"field": "<system_field>|null", "confidence": 0.92}
}
```

- **Estrategia híbrida:** la heurística (`heuristic_suggestion`) corre primero; la IA es fallback / refinamiento.

---

## 3. Resolución del provider

El runtime (`apps/api/app/services/ai/provider.py:resolve_provider`) selecciona la implementación según `tenant.ai_mode`:

| `ai_mode` | Provider real |
|---|---|
| `disabled` | `DisabledProvider` → 409 `AI_DISABLED` en endpoints IA |
| `platform` | `GroqProvider` con key de plataforma (env `GROQ_API_KEY` o `platform_ai_settings.groq_api_key_encrypted`) |
| `byo` | El provider configurado en `/admin/ai` para ese tenant. Catálogo: `openai`, `claude`, `gemini`, `perplexity`, `azure` (Microsoft Copilot M365 vía Azure OpenAI), `groq`, `custom` |

API keys de tenants en modo `byo` se cifran con **Fernet** (`services/ai_secrets.py`) antes de persistir.

---

## 4. Versionado y cambios

- **No hay sufijo `.v{N}`** en los identificadores hoy. Los prompts viven en `prompts.py` como constantes top-level y se cambian editando el archivo.
- **No hay flag por tenant para A/B testing** de prompts (la versión vieja del doc lo sugería como ideal; no implementado).
- **No hay golden dataset** (`tests/ai/golden/`) ni runner de comparación semántica. Diferido.
- Cambios pasan por PR con commit referenciando el ENH/BUG (ej. ENH-102, ENH-105 mencionados arriba).

### Arquitectura de composición por capas (ENH-189 + US-185, 2026-07-08)

Los prompts base siguen versionados en código, pero ahora se **componen**
con dos capas configurables sin deploy:

```
system efectivo  = base (prompts.py)
                 + <INSTRUCCIONES_DEL_TENANT>      ← tenants.settings.ai.instructions_md
                                                     (admin UI /admin → IA; máx 2000 chars;
                                                      services/ai/prompt_builder.py)
prompt de usuario = <CONTEXTO_DEL_PROYECTO>        ← project_ai_contexts (US-185):
                    (contexto curado + instrucciones   contexto/glosario/reglas del PM +
                     del PM + resumen acumulativo)     resumen que la IA actualiza por minuta
                  + payload de la tarea (transcript / datos del reporte)
```

Aplica a: minutas (`_run_minute`, cada chunk) y reportes
(`/reports/ai-generate`). Las instrucciones nunca pueden cambiar el
contrato de salida (regla de precedencia explícita en el builder).
Prompt nuevo: `PROJECT_MEMORY_SYSTEM` (resumen acumulativo de proyecto,
task Celery `ai.update_project_context`).

---

## 5. Guardrails reales

- **Parseo JSON con retry implícito.** Si el JSON viene mal, el worker captura la excepción y marca el job `failed` con `error="ai_invalid_json"`. **No hay retry automático** hoy.
- **Validación Pydantic:** los workers validan output contra schemas (`MinuteDraft`, `ReportDraft`, etc.) antes de persistir.
- **Sin censura activa de PII en logs.** Los logs del worker pueden contener el prompt completo si `LOG_LEVEL=DEBUG`. En prod (`INFO`) solo se loguean `tenant_id`, `model`, `tokens_in/out` y `duration_ms`.
- **Chunking: SÍ existe** (corrección ENH-189 — este doc decía lo contrario). `chunk_text` vive en `app/services/ai/provider.py` (~4 chars/token, `max_tokens=3000`, `overlap_tokens=200`) y `_run_minute` procesa cada chunk por separado (validator + merge en cascada). El bloque `<CONTEXTO_DEL_PROYECTO>` (US-185) se antepone a **cada** chunk.

> Si quieres reintroducir retry automático, golden dataset o sanitización de PII, abrir issues — es deuda razonable.

---

## 6. Historial superseded

- **Doc viejo (pre BUG-053):** documentaba `minute.from_transcript.v2`, `report.progress_draft.v1`, `transcript.chunk_merge.v1` con schemas y few-shots que **no coinciden con el código actual**. La cascada Ollama→Gemini→Claude y el chunking quedaron en `docs/archive/docs-ai-legacy/`.
- Hoy el contrato real está en `app/services/ai/prompts.py` y este doc.
