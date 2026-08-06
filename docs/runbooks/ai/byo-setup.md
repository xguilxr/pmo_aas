---
tipo: runbook
responsable: propietario
estado: vigente
revisado: 2026-05-23
revisar_cada: 180d
---

# Runbook · Conectar un proveedor BYO de IA

> Verificado contra `apps/api/app/services/ai/byo_catalog.py` (2026-05-23).
> Aplica desde **Sprint 2 v1.1 + DEC-019**. Este runbook es para el **admin
> del tenant** que quiere correr IA con su propia cuenta de proveedor en
> vez de usar la IA que hostea la plataforma (Groq).

**Providers reales del catálogo:**

| Key | Label | Notas |
|---|---|---|
| `openai` | OpenAI (ChatGPT) | gpt-4o-mini / gpt-4o / gpt-4-turbo |
| `claude` | Anthropic (Claude) | claude-3-5-haiku-* / claude-sonnet-4-6 |
| `gemini` | Google Gemini | gemini-1.5-flash / -pro |
| `perplexity` | Perplexity | sonar / sonar-pro |
| `azure` | **Microsoft Copilot M365 (Azure OpenAI)** | gpt-4o / gpt-4 / gpt-35-turbo; requiere endpoint + deployment + api_version |
| `custom` | Otro endpoint OpenAI-compatible | Together, Mistral, vLLM, LM Studio. Requiere ack de seguridad. |

> El provider `groq` también se puede conectar como BYO si el tenant trae su propia key.

Tiempo estimado: **10–15 min** por proveedor.

---

## 0. ¿Cuándo usar BYO?

Usa el modo **BYO** si tu tenant necesita:

- Llevarse el costo de IA a la cuenta de tu proveedor favorito (no al de la
  plataforma).
- Generar **drafts de reportes IA** además de minutas. El modo `platform`
  (Groq) está limitado a minutas; los reportes IA sólo funcionan con BYO.
- Usar un modelo específico (GPT-4o, Claude Sonnet 4.6, Gemini 1.5 Pro,
  Perplexity Sonar Pro) que no expone la plataforma.

Si sólo necesitas minutas y no te importa el modelo, quédate en modo
**platform (Groq)** — es gratis y ya está listo.

---

## 1. Pre-requisitos

- Rol **Admin** del tenant en la plataforma (capability `ai.configure`).
- Acceso a la consola del proveedor que vas a conectar.
- Un método de pago válido con el proveedor cuando aplique (la mayoría
  tienen free tier; Anthropic y Perplexity requieren saldo prepagado).

> El flag global `AI_BYO_ENABLED` mencionado en versiones viejas del
> doc **no existe**. BYO está siempre disponible. El badge
> "Próximamente" en `/admin/ai` se muestra solo cuando una card
> específica del catálogo viene marcada como `disabled` (caso a caso,
> no global).

---

## 2. Generar la API key en el proveedor

### 2.1 OpenAI

1. Ir a <https://platform.openai.com/api-keys>.
2. **Create new secret key** → nombre `pmo-aas-<tenant-slug>`.
3. **Permissions:** `Restricted` → habilitar sólo `Model capabilities` →
   `Read` y `Write`. No dar acceso a billing ni fine-tuning.
4. Copiar el valor `sk-...` (sólo se muestra una vez).
5. Verificar que el proyecto tiene un método de pago en
   <https://platform.openai.com/account/billing>. Sin eso, los modelos
   `gpt-4o` responden 429 `insufficient_quota`.

Modelos recomendados: `gpt-4o-mini` (barato, ~$0.0002/1K tokens in),
`gpt-4o` (premium).

### 2.2 Anthropic (Claude)

1. Ir a <https://console.anthropic.com/settings/keys>.
2. **Create Key** → nombre `pmo-aas-<tenant-slug>`.
3. **Workspace:** elegir uno con créditos asignados (Claude no tiene free
   tier; hay que precargar saldo).
4. Copiar el valor `sk-ant-...`.
5. En <https://console.anthropic.com/settings/workspaces> → **Spend limits**:
   poner un tope (ej. $10/mes) para evitar sorpresas.

Modelos recomendados: `claude-3-5-haiku-20241022` (barato, rápido),
`claude-sonnet-4-6` (premium, calidad alta).

### 2.3 Google Gemini

1. Ir a <https://aistudio.google.com/app/apikey>.
2. **Create API key** → elegir un Google Cloud project (o crear uno nuevo
   con nombre `pmo-aas-<tenant-slug>`).
3. Copiar el valor `AIza...`.
4. El free tier da **1M tokens/día** de `gemini-1.5-flash` — suficiente
   para un tenant de tamaño medio sin pagar nada.

Modelos recomendados: `gemini-1.5-flash` (free, rápido, 1M tokens/día),
`gemini-1.5-pro` (paid, context window más grande).

### 2.4 Perplexity

1. Ir a <https://www.perplexity.ai/settings/api>.
2. Generar una **API key** (requiere Perplexity Pro, ~$20/mes, o comprar
   créditos sueltos).
3. Copiar el valor `pplx-...`.

Modelos recomendados: `sonar` (búsqueda web en tiempo real),
`sonar-pro` (más reasoning, más caro).

### 2.5 Microsoft Copilot M365 (Azure OpenAI)

1. En <https://portal.azure.com> → tu recurso **Azure OpenAI Service**
   → **Keys and Endpoint**.
2. Copiar **Endpoint** (ej. `https://my-resource.openai.azure.com`) y
   **KEY 1** (no es un Bearer — Azure usa el header `api-key`).
3. En **Model deployments** del recurso, anotar el **Deployment name**
   exacto (no es el nombre del modelo) y la **API version** usada
   (ej. `2024-08-01-preview`).

El wizard pide los 4 campos: `endpoint (base_url)`, `api_key`,
`deployment_name`, `api_version`.

### 2.6 Custom (Together / Mistral / vLLM / LM Studio / …)

1. Crear la API key en la consola de tu proveedor.
2. Anotar `base_url` con la ruta `/v1` incluida (ej.
   `https://api.together.xyz/v1`).
3. Anotar el nombre del modelo tal como lo expone el endpoint.

En el wizard hay que aceptar un **security ack** (la plataforma no
audita el proveedor custom; el tenant es responsable de cumplimiento y
retención de datos).

---

## 3. Conectar desde `/admin/ai`

1. Log in como admin del tenant.
2. Ir a **Admin → IA** (sidebar izquierdo, icono ✨).
3. En el selector de modo, elegir **"Conectar tu propio proveedor"**.
4. Bajo "Conectar tu proveedor", aparecen 4 cards (OpenAI / Claude /
   Gemini / Perplexity). Click en la del que vas a usar.
5. El wizard abre en 4 pasos:

   **Paso 1 — Intro:** explicación + deep-link "Generar API key" que te
   lleva directo a la consola del proveedor. Click "Continuar".

   **Paso 2 — Key + modelo:**
   - Pegar la API key que copiaste en §2.
   - Elegir modelo (hay un datalist con sugerencias; puedes escribir uno
     custom si sabes lo que haces).
   - Si el proveedor requiere `base_url` (raro, sólo para proxies privados),
     el campo aparece.
   - Click "Continuar".

   **Paso 3 — Probar conexión:** el wizard manda un request mínimo al
   proveedor con tu key + modelo.
   - Esperado: `Conexión OK · <latencia>ms` (200–1500 ms típico).
   - Errores comunes:
     - `HTTP 401` → key mal copiada.
     - `HTTP 402` / `insufficient_quota` → falta crédito/billing.
     - `HTTP 429` → rate limit; espera 1 min y reintenta.
     - `HTTP 404` con modelo → el modelo no existe (typo) o tu cuenta no
       tiene acceso a él.
   - Click "Continuar" cuando pase.

   **Paso 4 — Guardar:** revisa el resumen (proveedor, modelo, últimos 4
   dígitos de la key) y click **"Guardar y activar"**.

6. La key se cifra con `AI_SECRETS_FERNET_KEY` antes de persistirse. No
   volverás a verla en claro.

---

## 4. Smoke test

1. Ir a `/pmo/projects/<id>/minutes` (US-075 movió las rutas de proyecto
   de `/admin/projects/*` a `/pmo/projects/*`; redirect 301 cubre los
   bookmarks viejos) → botón "Generar con IA" → pegar una transcripción
   breve → encolar minuta.
2. Verificar que el job pasa a `succeeded` en 3–15 s (depende del modelo).
3. (Opcional, sólo BYO) Ir a `/pmo/projects/<id>/reports` → botón
   "Generar reporte IA" o desde el Report Builder. Esta función **no**
   funciona en modo `platform` (Groq se limita a minutas; DEC-017).
   En modo `platform` el endpoint responde `409 AI_PLATFORM_SCOPE_LIMITED`.

Si algo falla:
- Regresar a `/admin/ai` → card del proveedor → "Probar conexión" para
  revalidar.
- Revisar el panel **`/superadmin/ai` → Tenants · Estado de IA** (si
  tienes acceso de superadmin); la columna "Último test" muestra el
  resultado más reciente.

---

## 5. Rotación de la API key

Cuando toque rotar la key (recomendado cada 90 días, o inmediatamente si
hay sospecha de filtración):

1. Generar una nueva key en la consola del proveedor (§2).
2. Ir a `/admin/ai` → card del proveedor activo → se reabre el wizard.
3. Pegar la nueva key en el paso 2; el wizard re-ejecuta test y save.
4. **Después** de confirmar que la nueva funciona, revocar la vieja en la
   consola del proveedor.

> ⚠️ No revoques la vieja antes de guardar la nueva — dejarías al tenant
> sin IA durante el gap.

---

## 6. Cambiar de proveedor BYO

Ej.: pasar de OpenAI a Claude.

1. `/admin/ai` → seleccionar la card de Claude → completar el wizard
   (pasos 1-4) con tu nueva key.
2. Al guardar, la config BYO se sobreescribe (la key de OpenAI se
   reemplaza). El histórico de jobs sigue intacto en BD.
3. Los nuevos jobs de IA arrancan usando Claude automáticamente.

---

## 7. Volver a modo `platform` o `disabled`

`/admin/ai` → seleccionar el radio de **"IA de la plataforma (Groq)"**
o **"Sin IA"** → confirmar el modal. Se preserva la config BYO cifrada
por si vuelves más adelante (no tienes que re-pegar la key).

---

## 8. Troubleshooting

**P:** Una card específica aparece con badge "Próximamente" y no se puede
seleccionar.
**R:** Es por provider, no global. Esa entrada del catálogo
(`byo_catalog.py`) viene marcada como `disabled` por decisión del owner
(ej. integración aún sin terminar). Pídelo si lo necesitas — el flag
está en código, no en env.

**P:** "Conexión OK" pero al generar minuta el job falla con
`provider_error`.
**R:** El test del wizard usa un prompt mínimo (4 tokens). Puede pasar
que tu modelo tenga rate limits más agresivos al procesar una minuta
real. Revisa los logs del worker en `/superadmin/logs` → filtrar por
`module=ai.jobs`.

**P:** La minuta generada está vacía o truncada.
**R:** Probablemente el modelo no soporta JSON mode estricto. Cambia a un
modelo más capaz (ej. de `gpt-4o-mini` a `gpt-4o`, o de
`claude-3-5-haiku` a `claude-sonnet-4-6`).

**P:** Perplexity devuelve HTTP 400 `"invalid_model"`.
**R:** El modelo `sonar` requiere **pplx-api** (no Perplexity Pro web).
Verifica que generaste la key en <https://perplexity.ai/settings/api>,
no en la app web.

**P:** Gemini falla en prod pero funcionó en dev.
**R:** Algunas regiones de Google Cloud restringen `generativelanguage.googleapis.com`.
Verifica que el proyecto tiene habilitada la **Generative Language API**
en <https://console.cloud.google.com/apis/library>.

---

## Referencias

- `/admin/ai` — UI de configuración BYO.
- `/superadmin/ai` — panel de estado por tenant + uso de Groq.
- Runbook Groq (modo `platform`): [`groq-setup.md`](./groq-setup.md).
- DEC-017 — IA multi-modo por tenant.
- DEC-019 — Catálogo BYO sin Ollama + feature flag del wizard.
- EP008 — Epic IA.
