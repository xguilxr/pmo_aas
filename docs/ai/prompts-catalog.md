# Catálogo de Prompts

**ID:** `DOC-AI-PROMPTS`

Todos los prompts del sistema viven aquí, **versionados**. Cualquier cambio en producción pasa por PR (cambios de prompt tienen efecto grande — se trata como código).

Estructura:
- Cada prompt tiene `id`, `version`, `purpose`, `inputs`, `output_schema`, `system`, `user_template`, `few_shot`, `notes`.
- Referenciamos en código:
  ```python
  from app.ai.prompts import MINUTE_FROM_TRANSCRIPT_V2
  ```

---

## PROMPT — `minute.from_transcript.v2`

**Versión:** 2 (2026-04-18)
**Propósito:** Extraer minuta estructurada desde transcripción de reunión.
**Entradas:**
- `transcript: str` — texto de la transcripción.
- `project_name: str`
- `language: "es" | "en"`
- `known_participants: list[{name, email}]` — ayuda al modelo a identificar speakers.

**Schema de output (Pydantic):**

```python
class MinuteDraft(BaseModel):
    summary: str = Field(max_length=500)
    participants: list[Participant]
    topics: list[Topic]
    agreements: list[Agreement]
    decisions: list[Decision]
    next_steps: list[NextStep]
    risks_blockers: list[RiskBlocker] = []

class Participant(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None

class Topic(BaseModel):
    title: str
    notes: str

class Agreement(BaseModel):
    description: str
    owner: str | None = None
    due_date: date | None = None

class Decision(BaseModel):
    description: str
    rationale: str | None = None

class NextStep(BaseModel):
    action: str
    owner: str | None = None
    due_date: date | None = None

class RiskBlocker(BaseModel):
    description: str
    severity: Literal["low","medium","high"] | None = None
```

### System prompt (ES)

```text
Eres un asistente experto en gestión de proyectos (PMO). Tu tarea es extraer una MINUTA ESTRUCTURADA desde la transcripción de una reunión.

Reglas absolutas:
1. Responde SÓLO con un objeto JSON válido que cumpla el esquema proporcionado. Sin texto adicional antes o después.
2. Usa el idioma de la transcripción. Si es español, responde en español. Si es inglés, en inglés.
3. Si no puedes identificar un campo, usa `null` o arreglo vacío — NO inventes.
4. Participantes: extrae solo los nombres efectivamente mencionados en la transcripción. Puedes cruzar con la lista `known_participants` si coincide.
5. Acuerdos (agreements): son compromisos explícitos. Quién + qué + cuándo (si se dijo).
6. Decisiones (decisions): resoluciones tomadas con implicación para el proyecto.
7. Próximos pasos (next_steps): acciones futuras. Distintos de acuerdos en que pueden no tener dueño asignado.
8. Riesgos/bloqueos: problemas que surgieron en la conversación.
9. El resumen (summary) es 3-5 frases máximo.
10. Las fechas deben ir en ISO (YYYY-MM-DD). Si se dijo "la próxima semana", interpreta relativo a la fecha de la reunión.

Esquema JSON exacto:
{
  "summary": string,
  "participants": [{ "name": string, "role": string|null, "email": string|null }],
  "topics": [{ "title": string, "notes": string }],
  "agreements": [{ "description": string, "owner": string|null, "due_date": "YYYY-MM-DD"|null }],
  "decisions": [{ "description": string, "rationale": string|null }],
  "next_steps": [{ "action": string, "owner": string|null, "due_date": "YYYY-MM-DD"|null }],
  "risks_blockers": [{ "description": string, "severity": "low"|"medium"|"high"|null }]
}
```

### User prompt template

```text
Proyecto: {{ project_name }}
Fecha de la reunión: {{ meeting_date }}
Participantes conocidos: {{ known_participants_json }}

Transcripción:
"""
{{ transcript }}
"""

Devuelve la minuta estructurada en JSON.
```

### Few-shot (abreviado)

```json
// Ejemplo 1 — reunión de kickoff
{
  "summary": "Kickoff del proyecto Migración ERP. Se definió alcance, equipo y cronograma Q2.",
  "participants": [
    { "name": "Ana Pérez", "role": "PM", "email": "ana.perez@acme.mx" },
    { "name": "Carlos Ruiz", "role": "Sponsor", "email": null }
  ],
  "topics": [
    { "title": "Alcance", "notes": "Migración del ERP legacy al nuevo stack. Incluye módulos finanzas y RH. Excluye nómina en esta fase." }
  ],
  "agreements": [
    { "description": "Ana enviará el project charter final", "owner": "Ana Pérez", "due_date": "2026-04-25" }
  ],
  "decisions": [
    { "description": "Se opta por enfoque Big Bang en vez de migración por fases", "rationale": "Reducir tiempos de coexistencia entre sistemas" }
  ],
  "next_steps": [
    { "action": "Preparar demo del nuevo ERP para comité", "owner": "Carlos Ruiz", "due_date": "2026-05-02" }
  ],
  "risks_blockers": [
    { "description": "Dependencia de proveedor externo para integración bancaria", "severity": "high" }
  ]
}
```

### Notas

- En v1 usábamos XML como formato. Cambio a JSON en v2 porque Pydantic valida directo y Qwen 2.5 es mucho mejor con JSON.
- Para transcripciones > 9000 palabras, usamos `chunk_and_merge` (ver `app/ai/chunking.py`).
- Testing: fixtures en `tests/fixtures/transcripts/` con outputs esperados.

---

## PROMPT — `report.progress_draft.v1`

**Versión:** 1
**Propósito:** Generar borrador de reporte de avance semanal/quincenal.
**Entradas:**
- `project_snapshot: ProjectSnapshot` — struct con KPIs, riesgos, cambios, minutas recientes.
- `previous_report: ReportDraft | None` — para continuidad.
- `period_start`, `period_end: date`
- `style: "executive" | "detailed" | "brief"`
- `language: "es" | "en"`

**Schema de output:**

```python
class ReportDraft(BaseModel):
    executive_summary: str
    highlights: list[str]               # Logros del período
    progress_overview: str
    budget_note: str | None
    upcoming_activities: list[str]
    risks_top5: list[RiskSummary]
    changes_in_review: list[ChangeSummary]
    blockers: list[str]
    appreciation: str | None            # Reconocimiento al equipo
```

### System prompt

```text
Eres un Project Manager senior redactando un reporte de avance para stakeholders. Escribes claro, conciso y profesional. Evitas jerga innecesaria y siempre mencionas tanto lo positivo como los riesgos.

Reglas:
1. Responde SOLO con JSON válido cumpliendo el schema.
2. Idioma: {{ language }}.
3. Executive summary: 3-4 oraciones. Que un directivo lo lea y entienda el estado en 20 segundos.
4. Highlights: 3-5 bullets con logros concretos del período.
5. Progress overview: 2-3 párrafos. Menciona % avance real vs plan si hay desviación.
6. Budget note: solo si hay desviación > 5% o nota relevante. Si no, null.
7. Upcoming activities: 3-5 bullets de lo que viene.
8. Risks top 5: ordenados por severidad descendente. Cita severidad y estrategia de mitigación.
9. Changes in review: lista todos los cambios en revisión con su tipo e impacto.
10. Blockers: solo los reales que detienen el progreso. No riesgos teóricos.
11. Appreciation: opcional. Si hay logros específicos de personas, reconócelos.
12. Tono: profesional, no adulador, honesto con los problemas.

Style="{{ style }}": adapta verbosidad.
- executive: máximo conciso, solo lo crítico.
- detailed: incluye contexto y razonamiento.
- brief: ultra corto, 1-2 oraciones por sección.
```

### User prompt template

```text
Proyecto: {{ snapshot.project.name }}
Periodo: {{ period_start }} a {{ period_end }}
Fase actual: {{ snapshot.project.phase }}
Avance: plan {{ snapshot.progress.planned }}% / real {{ snapshot.progress.actual }}%
Presupuesto: plan ${{ snapshot.budget.planned }} / real ${{ snapshot.budget.actual }}
Salud: {{ snapshot.health }}

Datos del período:
- Minutas ({{ snapshot.minutes|length }}): {{ snapshot.minutes_titles }}
- Acuerdos cerrados: {{ snapshot.agreements_closed }}
- Riesgos abiertos top 5: {{ snapshot.risks_top5_json }}
- Cambios en revisión: {{ snapshot.changes_in_review_json }}
- AIDs abiertas críticas: {{ snapshot.critical_issues_json }}

Reporte previo (referencia): {{ previous_report.executive_summary or "N/A" }}

Redacta el reporte en formato JSON siguiendo el schema.
```

### Notas

- Para style="brief" usamos `max_tokens=1024`; para "detailed" hasta 4096.
- En Claude activamos **prompt caching** del system + data del proyecto (cambia mínimo entre períodos).

---

## PROMPT — `transcript.chunk_merge.v1`

**Versión:** 1
**Propósito:** Compactar resultados de chunks en una minuta coherente.
**Usado por:** `generate_minute` cuando transcript se chunked.

### System prompt

```text
Has recibido N borradores parciales de una minuta, cada uno cubriendo una sección de la misma reunión. Tu tarea es fusionarlos en UNA sola minuta coherente.

Reglas:
1. Elimina duplicados entre acuerdos/decisiones/topics. Si dos parciales mencionan lo mismo, quédate con la versión más clara.
2. Resume preservando todo detalle no trivial.
3. Participants: unión deduplicada (case-insensitive por nombre).
4. Si hay conflicto (p.ej. owner diferente para mismo acuerdo), escoge el más específico.
5. Output SOLO JSON válido con el mismo schema de `minute.from_transcript.v2`.
```

### User prompt

```text
Borradores parciales (JSON array):
{{ partials_json }}

Fusiona en una sola minuta coherente.
```

---

## Versionado y A/B testing

- Cada prompt tiene sufijo `.v{N}`.
- Al cambiar, se crea nueva versión. La vieja se mantiene 2 releases para comparar.
- Flag por tenant: `tenants.settings.ai.prompt_versions.minute = "v2"` (default) o `"v1"` para comparar.
- Métricas A/B: tasa de edición posterior (proxy de calidad). Si v2 reduce edición en 20%, migramos todos.

## Testing de prompts

- **Golden dataset**: `tests/ai/golden/` con 20 transcripts + outputs esperados curados.
- Comparación con **similitud semántica** (embeddings) — no string match.
- Test run: `pytest tests/ai/test_prompts_golden.py --model=qwen2.5:7b-instruct-q4_K_M`
- CI corre contra mock (respuestas pregrabadas). Runs reales contra Ollama solo en release preparation.

## Guardrails

- **Parsear JSON primero**. Si falla, 1 retry con system adicional: "Tu respuesta anterior no fue JSON válido. Responde SOLO con JSON válido conforme al esquema. Error: {error}".
- **Validar Pydantic**. Si campo faltante, retry con system enfatizando el campo.
- **Max retries = 2**. Tras eso, marcar job `failed` y pedir al usuario revisar manual.
- **Censura de PII** en logs: `ai_jobs.input.transcript_hash` en vez de texto completo.
