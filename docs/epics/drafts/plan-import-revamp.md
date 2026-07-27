# Draft — Retrabajo del import/export de Plan (WBS, Estado, %, IA)

> **Fase A — draft vivo.** Origen: feedback del owner 2026-07-18
> ("el import de plan no jala bien los campos con su propio template,
> no tiene opción de tomar campo de estado, el WBS 1.30 lo toma como
> 1.3 y deja huérfanas a 1.30.1/1.30.2, y no hay cómo ordenar el WBS
> si los IDs son numéricos").
> Epic afectado: **EP009** (import MS Project/XLSX) + toques a EP005/EP006.
> Estado: **pendiente de cierre de scope por el owner.**

---

## 1. Mapa del estado actual (as-is)

### 1.1 Piezas del flujo

| Pieza | Archivo | Rol |
|---|---|---|
| Plantilla descargable | `apps/web/lib/plan-template.ts` | XLSX generado **client-side** (ExcelJS): 15 columnas V1, data-validation, hoja Instrucciones |
| Export "Descargar" | `apps/web/app/(app)/pmo/projects/[id]/plan/page.tsx` (`exportToExcel`, ~1679) | XLSX client-side con las mismas 15 columnas, datos actuales |
| Download backend | `GET /projects/{id}/plan/download` → `apps/api/app/services/plan_regenerator.py` | Regenera XLSX/CSV desde DB con **otro** set de 11 columnas (`PLAN_HEADERS`) |
| Wizard de import | `apps/web/components/import-wizard.tsx` | upload → hoja → preview + mapeo → confirm |
| Parser XLSX | `apps/api/app/services/xlsx_task_parser.py` | Auto-detección de headers (`HEADER_ALIASES`), coerción de tipos |
| Parser CSV | `apps/api/app/services/csv_task_parser.py` | Reusa aliases/coerciones del XLSX |
| Parsers MSP | `services/msproject/mpp_parser.py`, `xml_parser.py` | MPP vía MPXJ (Java), MSPDI XML |
| Endpoints import | `apps/api/app/api/v1/endpoints/tasks.py` (`/import`, `/import/preview`, `/import/{job}/confirm`) | One-shot legacy + wizard (Redis TTL 1h) |
| Sugerencia de mapeo IA | `apps/api/app/services/import_mapping_suggest.py` (ENH-053) | Heurística de sinónimos + LLM del tenant (`generate_for_tenant`), merge por confianza |
| Orden/jerarquía | `services/plan_metadata.py` (`wbs_sort_key`, `compute_wbs_rollup`, `parent_wbs`) + `compareWbs` en `plan/page.tsx` | Orden natural por segmento; jerarquía derivada del string WBS en read-time (no hay `parent_id` al importar) |

### 1.2 Contratos de campos (la raíz de "no jala los campos")

Hay **cuatro listas de campos distintas** que deberían ser una sola:

| Fuente | Campos |
|---|---|
| Plantilla + export frontend (15) | WBS, Tarea, Outline Level, Inicio, Fin, Duración, Avance (%), **Estado**, Área Responsable, Responsable, Criticidad, Es hito, Hito Relacionado, Predecessors, Successors |
| Parser (`HEADER_ALIASES`, 13) | name, wbs, start, end, duration, progress, is_milestone, criticality, is_critical, related_milestone, predecessors, area, resources — **sin `status`** |
| Wizard (`SYSTEM_FIELDS` FE+BE, 9) | name, wbs, start, end, duration, progress, is_milestone, predecessors, resources — sin status, área, criticidad, hito relacionado |
| Regenerator backend (11) | WBS, Nombre, Inicio, Fin, Duración, Avance, Hito, Estado, Criticidad, is_critical, Outline — sin área/responsable/predecesoras |

### 1.3 Qué pasa hoy al subir la propia plantilla llena

Verificado empíricamente contra el parser real (script de repro):

- **Estado → se ignora silenciosamente.** Sin alias "estado", sin campo
  en `ParsedTask`, sin opción en el wizard; el confirm hardcodea
  `status="not_started"` (tasks.py:765 y 1237).
- **Responsable → se descarta.** Se parsea a `resources_raw` pero el
  shim del confirm no lo copia; el fuzzy-match contra usuarios que
  promete la hoja Instrucciones **no existe**.
- **Hito Relacionado → se descarta.** `related_milestone_wbs` parseado
  pero no aplicado en confirm.
- **Predecessors → se descartan.** El wizard confirma con
  `dependencies_created: 0` siempre; `Task.predecessors` nunca se llena
  desde import (la hoja Instrucciones promete reconstrucción).
- **WBS numérico → colapsa.** Celda numérica `1.30` llega como float
  `1.3` (openpyxl) → se guarda "1.3": colisiona con el 1.3 real y
  `1.30.1`/`1.30.2` quedan huérfanas (el rollup/orden derivan la
  jerarquía del string). Ocurre incluso con formato `0.00` visible
  ("1.30" en pantalla). La plantilla NO fuerza formato texto en la
  columna WBS, así que Excel convierte a número lo que el usuario tipee.
- **% con formato → puede irse a 100%.** La detección BUG-081 es
  **por columna** (si alguna de las primeras 30 celdas tiene formato %,
  escala todo ×100): enteros "45" en columna %-formateada → 4500 →
  clamp 100; formatos mixtos → los enteros planos quedan en 100.
- **Criticidad / Es hito / Área** → sí funcionan (alias exactos).
- "Fin se calcula desde duración si está vacío" (Instrucciones) → no
  implementado.

### 1.4 Orden del WBS

- **Guardado:** `tasks.wbs` es `String(64)` — el tipo es correcto, el
  daño ocurre al parsear (float) y al ordenar.
- **Backend list:** `wbs_sort_key` ordena por segmento numérico
  (natural: 1.2 < 1.10) ✔.
- **Backend download:** ordena `outline_level` primero y luego WBS
  **como string** → el Excel descargado agrupa todos los nivel-1, luego
  todos los nivel-2 (rompe el orden del plan) ✘.
- **Frontend `compareWbs`:** `parseInt` por segmento — correcto para
  1.30 vs 1.3 (30≠3) pero colapsa segmentos alfanuméricos a 0 y empata
  "1.03" con "1.3" ✘ (menor).
- **Jerarquía:** nunca se asigna `parent_id` al importar; todo deriva
  del string WBS → cualquier corrupción del WBS rompe rollup de avance,
  agrupado y Gantt.

### 1.5 IA existente

`suggest_column_mapping` (ENH-053) ya usa el LLM del tenant para mapear
**headers** (solo nombres de columna, sin filas de muestra), con
heurística como fallback y umbral 0.7. Infra disponible:
`generate_for_tenant` (BYO/Groq por tenant, `ai_mode`), worker Celery.

---

## 2. Deficiencias priorizadas

| # | Deficiencia | Severidad | Evidencia |
|---|---|---|---|
| D1 | WBS numérico pierde formato (1.30→1.3), hijos huérfanos | **Alta** | repro caso 1-2; reporte owner |
| D2 | Estado no importable (ni auto, ni manual) | **Alta** | reporte owner; parser sin alias |
| D3 | % mal escalado con formato %/mixto (todo 100%) | **Alta** | repro caso 3-4 |
| D4 | Responsable / Hito Relacionado / Predecessors descartados en confirm | Alta | código confirm; Instrucciones prometen lo contrario |
| D5 | Wizard solo re-mapea 9 campos (sin estado/área/criticidad/hito rel.) | Media | `SYSTEM_FIELDS` FE/BE |
| D6 | Download backend desordenado (outline primero, WBS lexicográfico) y con columnas distintas a la plantilla | Media | `download_plan` + `PLAN_HEADERS` |
| D7 | Preview del wizard muestra valores crudos (0.45, floats) sin interpretación ni warnings | Media | `_serialize_sample` |
| D8 | 4 contratos de columnas paralelos (plantilla/parser/wizard/regenerator) | Media | §1.2 |
| D9 | `compareWbs` FE: alfanuméricos→0, zero-padding empata | Baja | plan/page.tsx:92 |

---

## 3. Propuesta de retrabajo (to-be)

### Bloque A — Fidelidad de datos (bugs)

**BUG-088 — WBS fiel al archivo (1.30 ≠ 1.3) + huérfanos.**
- Parser XLSX: leer la columna WBS respetando el **texto mostrado**:
  segunda pasada con `number_format` (mismo patrón que BUG-081 para %)
  — celda numérica con formato `0.00` → "1.30"; sin formato → advertir
  y formatear con los decimales del formato/heurística.
- Plantilla + export: forzar formato **texto (`@`)** en la columna WBS
  y escribir siempre strings.
- Preview: validación de jerarquía — detectar hijos cuyo padre WBS no
  existe y avisar ("N tareas quedarían huérfanas") antes del confirm.
- FE `compareWbs`: comparar segmentos como texto-numérico sin colapsar
  alfanuméricos (reusar la semántica de `wbs_sort_key`).

**BUG-089 — Porcentaje de avance robusto.**
- Detección de formato % **por celda** (no por columna).
- Sanity check: si tras escalar el valor excede 100 → usar el valor
  original si era ≤100 y registrar warning por fila (visible en preview).
- Preview muestra el % ya interpretado, no la fracción cruda.

**BUG-090 — La plantilla propia importa TODO lo que promete.**
- Confirm aplica: Responsable (fuzzy-match ≥0.85 contra usuarios del
  tenant, como ya promete Instrucciones), Hito Relacionado (resolución
  por WBS post-alta), Predecessors (llenar `Task.predecessors` +
  `recompute_successors_for_project` + crear `TaskDependency`).
- "Fin vacío + duración → calcular Fin" (o quitar la promesa de la
  hoja Instrucciones — decidir).

### Bloque B — Contrato único + wizard completo

**ENH-191 — Estado importable end-to-end.**
- Alias "estado/status/state" en parser + `ParsedTask.status` +
  normalización de valores: enum crudo (`in_progress`), labels ES de la
  UI ("En Progreso", "Completado"…), EN comunes ("done"→completed).
- `SYSTEM_FIELDS` (FE+BE) + suggester + confirm aplican status; sin
  columna → default `not_started` (comportamiento actual).

**ENH-192 — Wizard re-mapea todos los campos + preview interpretado.**
- Unificar `SYSTEM_FIELDS` FE/BE con la lista completa del parser
  (status, área, criticidad, is_critical, hito relacionado).
- Paso de preview muestra la **interpretación** (WBS como texto, %
  escalado, estado normalizado, responsable matcheado) + warnings por
  fila (huérfanos, % dudoso, estado no reconocido) con opción de
  corregir el mapeo antes de confirmar.

**ENH-193 — Export/download consistente con la plantilla.**
- `plan_regenerator.PLAN_HEADERS` = las 15 columnas V1 de la plantilla
  (una sola fuente de verdad, idealmente compartida).
- Orden del archivo = orden del plan (position → `wbs_sort_key`), no
  outline-first.
- Estado exportado en enum crudo (compatible con la data-validation de
  la plantilla) — el round-trip cierra al combinarse con ENH-191.

### Bloque C — Import inteligente (IA)

**US-188 — Interpretación asistida por IA de archivos de plan.**
Escalera de 3 niveles (cada uno con fallback al anterior; todo pasa por
preview editable, nunca auto-commit):
1. **Mapeo por contenido** (extiende ENH-053): enviar al LLM headers +
   5-10 filas de muestra para decidir por los **valores** (una columna
   "45%" o "En curso" se identifica aunque el header sea críptico).
2. **Normalización de valores**: estados libres ("en curso", "OK",
   "terminada"), fechas ambiguas (DD/MM vs MM/DD), responsables →
   usuarios, escala de %. Heurística primero; IA solo para lo no
   resuelto; salida JSON estricto validada server-side, con confianza
   por celda visible en preview.
3. **Estructura**: para Excel "sucio" (títulos de sección, indentación
   en vez de WBS, celdas combinadas): el LLM propone el árbol WBS
   completo (structured output con schema), el usuario ve el plan
   propuesto en diff y confirma. Archivos grandes → job Celery por
   chunks.
- Gating por `tenant.ai_mode` (como ENH-053); sin IA la escalera queda
  en heurística. Costo acotado: solo muestras/filas problemáticas van
  al LLM, no el archivo completo.

### Orden sugerido de ejecución

1. Bloque A (BUG-088/089/090) — restaura confianza en el import actual.
2. Bloque B (ENH-191/192/193) — cierra el round-trip plantilla↔plan.
3. Bloque C (US-188) — inteligencia sobre una base ya sólida.

---

## 4. Decisiones del owner (2026-07-18)

1. **WBS sin formato:** la plantilla y el export fuerzan la columna
   WBS a **texto** (`@`). El parser además respeta `number_format`
   decimal y avisa en preview cuando una celda numérica en General es
   irrecuperable.
2. **Fin desde duración:** se implementa (Fin vacío + Inicio +
   Duración → Fin calculado), coherente con la promesa de la hoja
   Instrucciones. Barato y sin riesgo; owner puede vetar en review.
3. **US-188 (IA):** van **los 3 niveles** (mapeo por contenido,
   normalización de valores, estructura).
4. **Prioridad:** se ataca **todo el concepto** como un batch para
   robustecer el import end-to-end.

### Scope adicional pedido por el owner

- **ENH-194 — Plantilla inteligente por proyecto:** la plantilla se
  genera con información del proyecto (nombre, fechas, contexto del
  charter cuando existe) y una hoja **Gantt** en Excel (barras por
  formato condicional sobre las fechas del Plan) — "un mini MS Project
  en Excel" para quien no tiene MS Project.
- **US-189 — UX de import para no-PMs:** el wizard debe ser usable por
  gente que no es PM: drag & drop, auto-mapeo silencioso, resumen en
  lenguaje llano ("Se importarán 45 tareas, 3 avisos"), mapeo manual
  escondido detrás de "Ajustar columnas", advertencias entendibles.

---

**Última actualización:** 2026-07-18 · sesión `claude/plan-import-wbs-fixes-nwotng` · batch en ejecución
