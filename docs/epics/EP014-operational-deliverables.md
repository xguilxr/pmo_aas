# EP014 — Entregables operativos (reportes Python + formato estandarizado de minuta)

| Campo | Valor |
|---|---|
| **ID** | EP014 |
| **Prioridad** | Alta — bloque 10 del sprint |
| **Dependencias** | EP005, EP006 (reportes module), EP008 (IA minutas) completos |
| **Módulo** | `reports.python`, `pdf`, `ai.minutes.format` |
| **Estado** | # PENDING |
| **Versión objetivo** | v1.1 |
| **Issue origen** | [#18 — Formato de Reportes y Minutas](https://github.com/xguilxr/pmo_aas/issues/18) |

## Objetivo de negocio

El usuario pide **dos flujos operativos concretos** que hoy no existen:

1. **Reportes ejecutables sin IA** — pura automatización con Python que lee la BD y genera HTML + PDF descargable. Dos tipos:
   - Reporte de Avance de Proyecto
   - Reporte de Seguimiento de Actividades
2. **Formato estandarizado de Minuta IA** — cuando la minuta se genera con IA (EP008), debe devolverse en un layout fijo y exportable a `.docx` / `.txt` / `.md`.

El módulo de Reportes existente (US-NEW-022) cubre el caso de reporte "manual/IA editable tipo Notion". Esta épica agrega un **segundo motor** de reportes (Python templated) para casos operativos recurrentes y un **postprocesamiento** de minuta IA para alinearla al formato corporativo.

## DEC a registrar en DECISIONS.md al cierre del bloque

- **DEC-014** — Reportes operativos (Avance, Seguimiento) se generan con Python + plantillas Jinja2; no pasan por IA. La IA sigue siendo opcional en el módulo de Reportes (EP006 / EP008) para reportes narrativos.
- **DEC-015** — WeasyPrint es el motor oficial de PDF (ya mencionado en US-030); se valida como infra compartida para todos los exports (charter, minutas, reportes).
- **DEC-016** — Minuta IA devuelve siempre la misma estructura post-procesada (ver US-NEW-040) y expone endpoints de export `.docx` / `.md` / `.txt`.

---

## # DONE — US-NEW-037 — Infra compartida de exportación a PDF

**Como** backend
**Quiero** una utilidad centralizada para renderizar HTML → PDF
**Para** que charter, minuta y reportes usen el mismo motor y estilo.

**Criterios de aceptación:**
- [x] Módulo `apps/api/app/services/pdf_renderer.py` con funciones `render_html(template_name, context) -> str` y `render_pdf(template_name, context) -> bytes`.
- [x] Motor: **WeasyPrint 68.1** vía `HTML(string=html).write_pdf()`.
- [x] Plantillas Jinja2 en `apps/api/app/templates/pdf/`:
  - `base.html` con header/footer configurables (@page, counter de páginas, tenant_name, title, generated_at), CSS tipografía + colores del design system (`--chrome = #182e4e`).
  - `_smoke.html` para tests.
- [x] Convención: cada recurso (charter, minuta, reporte) tendrá su propio endpoint `.../export?format=pdf` que invoca `render_pdf(...)`. Endpoint helper centralizado se integra por módulo (EP014 US-NEW-038/039/040).
- [x] Manejo de errores: fallo de render envuelto en `AppError(502, PDF_RENDER_FAILED)`. Dep faltante devuelve `AppError(502, PDF_ENGINE_UNAVAILABLE)`.
- [x] Dependencias registradas: `weasyprint==68.1`, `jinja2==3.1.4` en `requirements.txt`.

**Test Cases (4/4 verdes):**
- `test_usnew037_render_html_basic` — Jinja renderiza y contiene generated_at.
- `test_usnew037_render_pdf_returns_valid_bytes` — bytes empiezan con `%PDF` y terminan con `%%EOF`.
- `test_usnew037_render_pdf_unknown_template_raises` — template inexistente lanza excepción.
- `test_usnew037_render_pdf_handles_unicode` — acentos/emoji no rompen el render.

**Commit:** `feat(api): US-NEW-037 — infra de exportación a PDF con WeasyPrint + Jinja2`.

---

## # PENDING — US-NEW-038 — Reporte de Avance de Proyecto (Python, BD, PDF)

**Como** PM
**Quiero** generar un Reporte de Avance del proyecto con un click, que consulta automáticamente la BD y se descarga en PDF
**Para** compartirlo por correo sin editar nada manualmente.

**Referencia de diseño:** adjuntos en [issue #18](https://github.com/xguilxr/pmo_aas/issues/18):
- `Reporte_Avance_2026-03-25.html` (layout esperado)
- `Reporte_Avance_2026-03-25.json` (shape de datos)
- `generar_reporte_avance.py` (lógica de ejemplo, local — hay que re-modelarlo para BD + sistema)

**Criterios de aceptación:**
- [ ] Endpoint `POST /api/v1/projects/{id}/reports/avance` con body `{ cut_off_date?: date }`. Default = hoy.
- [ ] Backend arma el contexto desde la BD (sin IA):
  - Info general del proyecto (folio, nombre, PM, sponsor, org, programa, fase, salud).
  - Avance plan vs real (usa tareas y `plan-vs-actual`).
  - Presupuesto asignado / ejecutado.
  - Hitos próximos (tareas con `is_milestone=true` y `due_date` ≥ cut_off).
  - Hitos cumplidos en el periodo (desde último reporte o últimos 14 días si no hay previo).
  - Top 5 riesgos abiertos por severidad.
  - AIDs abiertas priorizadas.
  - Cambios en revisión (count).
- [ ] Renderiza con plantilla `reports/avance.html` (basada en el HTML adjunto del issue).
- [ ] Devuelve PDF directamente (content-type `application/pdf`, filename `Reporte_Avance_{folio}_{YYYY-MM-DD}.pdf`).
- [ ] Guarda copia en `documents` con `category='report'` + referencia al `reports` row (metadata: tipo `avance`, cut_off).
- [ ] Endpoint `GET /api/v1/reports/{id}/avance/download` para re-descargar versión histórica.
- [ ] UI en `/admin/projects/{id}?tab=reports`:
  - Botón "Generar Reporte de Avance" (nuevo) — sin IA, sin edición.
  - Al generar, descarga automática + row nuevo en listado con badge "Avance".

**Test Cases:**
- `TC-NEW-038-1` (integration) — Proyecto sin tareas → reporte se genera con secciones vacías (no crash).
- `TC-NEW-038-2` (integration) — Top 5 riesgos ordenado por `severity` desc.
- `TC-NEW-038-3` (integration) — PDF incluye folio y cut_off correctos en header.
- `TC-NEW-038-4` (E2E) — Click "Generar Reporte de Avance" → descarga inicia en ≤ 5s.
- `TC-NEW-038-5` (integration) — Cross-tenant: usuario de tenant B no puede generar reporte del proyecto del tenant A → 404.

---

## # PENDING — US-NEW-039 — Reporte de Seguimiento de Actividades (Python, BD, PDF)

**Como** PM
**Quiero** generar un Reporte de Seguimiento que liste actividades vencidas, en curso y próximas con responsables agrupados
**Para** preparar la reunión semanal ("lunes de persecución") sin armarlo a mano.

**Referencia de diseño:** adjuntos en [issue #18](https://github.com/xguilxr/pmo_aas/issues/18):
- `Reporte_Seguimiento_2026-03-25.html`
- `Reporte_Seguimiento_2026-03-25.json`
- `generar_reporte_seguimiento.py`

**Criterios de aceptación:**
- [ ] Endpoint `POST /api/v1/projects/{id}/reports/seguimiento` con body `{ window_days?: int }`. Default = 14 (semana pasada + siguiente).
- [ ] Contexto desde la BD:
  - Actividades vencidas (`due_date < today AND status NOT IN ('resolved','closed','done')`). Incluye tareas del plan y AIDs tipo action.
  - Actividades en curso.
  - Actividades próximas (hasta `window_days` adelante).
  - Agrupación: **por responsable** (nombre del usuario o area_reference).
  - Alertas: items con > N días vencidos resaltados en rojo.
- [ ] Plantilla `reports/seguimiento.html` con tabla por responsable.
- [ ] PDF descargable (filename `Reporte_Seguimiento_{folio}_{YYYY-MM-DD}.pdf`).
- [ ] Copia guardada en `documents` (`category='report'`, metadata tipo `seguimiento`).
- [ ] UI: botón "Generar Reporte de Seguimiento" en la tab Reportes.
- [ ] Endpoint `GET /api/v1/reports/{id}/seguimiento/download`.

**Test Cases:**
- `TC-NEW-039-1` (integration) — Vencidos + en curso + próximos cuentan sólo items del proyecto.
- `TC-NEW-039-2` (integration) — Agrupación por responsable: items sin `owner_id` caen en bucket "Sin responsable".
- `TC-NEW-039-3` (integration) — Items con `due_date NULL` no aparecen en vencidos.
- `TC-NEW-039-4` (E2E) — PDF descargable con sección por responsable.

---

## # PENDING — US-NEW-040 — Formato estandarizado + export de Minuta IA

**Como** PM
**Quiero** que la minuta generada con IA siempre tenga el mismo formato y pueda descargarse en `.docx`, `.md` o `.txt`
**Para** compartirla en canales corporativos sin reformateo manual.

**Formato requerido (ver issue #18):**

```
========
Título - "Minuta Reunión {nombre_reunion_sintetizado}" — {Proyecto} — {Fecha}
========
Sesión: {n}
Fecha: {YYYY-MM-DD}
Duración: {hh:mm}
Participantes:
  - {nombre} ({rol/area})
========
Resumen e Hitos
  {lista de puntos claves agrupados por tema principal, enumerados, muy conciso}
========
RAID (en tabla)
  - Riesgos  | descripción | severidad | owner
  - Acciones | descripción | responsable/area (agrupado) | due_date
  - Incidentes / Decisiones
========
Notas adicionales
  {texto libre}
```

**Criterios de aceptación:**
- [ ] El prompt de EP008 US-043 se actualiza para devolver JSON con exactamente las secciones: `title_short`, `session_number`, `date`, `duration_minutes`, `participants[]`, `summary_topics[]`, `raid_table[]`, `additional_notes`. Schema documentado en `docs/ai/prompts-catalog.md`.
- [ ] Post-procesador Python `backend/app/services/minutes_formatter.py` convierte el JSON en:
  - Vista de preview (HTML) que respeta el layout de 5 secciones.
  - Export `.md` (markdown con separadores `========`).
  - Export `.txt` (texto plano).
  - Export `.docx` (usa `python-docx`; plantilla con estilo corporativo).
- [ ] Acciones del RAID se **agrupan por area o responsable** en el render (criterio explícito del issue).
- [ ] Endpoints:
  - `GET /api/v1/meeting-minutes/{id}/export?format=docx|md|txt|pdf` — PDF reutiliza US-NEW-037.
  - Si `format=pdf`, filename: `Minuta_{proyecto_folio}_{fecha}.pdf`; igual para los demás.
- [ ] UI: dentro del editor de minutas (post-generación IA), botón "Descargar" con menú desplegable (docx / md / pdf).
- [ ] Minutas **manuales** (no IA) también pueden usarse con el mismo formatter si cumplen el schema mínimo (campos opcionales se muestran como vacíos).

**Test Cases:**
- `TC-NEW-040-1` (integration) — JSON IA con schema válido → render HTML con 5 secciones.
- `TC-NEW-040-2` (integration) — Export `.docx` abre en Word sin errores (verificación con `python-docx` round-trip).
- `TC-NEW-040-3` (integration) — RAID con 3 acciones de diferentes owners → agrupa por owner.
- `TC-NEW-040-4` (E2E) — Descargar minuta en `.md` → archivo con separadores `========` correctos.
- `TC-NEW-040-5` (integration) — Minuta sin `additional_notes` → sección aparece con "—" en lugar de crash.

---

## Endpoints nuevos

```
POST /api/v1/projects/{id}/reports/avance                         [US-NEW-038]
POST /api/v1/projects/{id}/reports/seguimiento                    [US-NEW-039]
GET  /api/v1/reports/{id}/avance/download                         [US-NEW-038]
GET  /api/v1/reports/{id}/seguimiento/download                    [US-NEW-039]
GET  /api/v1/meeting-minutes/{id}/export?format=docx|md|txt|pdf   [US-NEW-040]
```

## Cambios de schema

Mínimos. Aprovechar `reports` existente:

```sql
-- Tipificar el reporte ejecutable
ALTER TABLE reports ADD COLUMN generator TEXT DEFAULT 'manual';
    -- 'manual' | 'ai' | 'avance' | 'seguimiento'
ALTER TABLE reports ADD COLUMN cut_off_date DATE;          -- para avance/seguimiento
```

Agregar a `DB-CHANGES.md` bajo nueva sección **EP014**.

## Dependencias técnicas

- Python: `weasyprint`, `python-docx`, `jinja2` (Jinja2 ya es parte del stack).
- Node libs para UI: ninguna nueva (la descarga es vía `<a href>` a endpoint backend).

---

## Definition of Done

- [ ] Infra PDF compartida funcional (US-NEW-037).
- [ ] 2 reportes Python ejecutables, sin IA, descargables en PDF (US-NEW-038, 039).
- [ ] Minuta IA con formato estandarizado + 4 formatos de export (US-NEW-040).
- [ ] Documentos generados quedan en `documents` con `category` correcta para trazabilidad.
- [ ] Tests unit + integration + al menos 1 E2E por US.
- [ ] DEC-014, DEC-015, DEC-016 registrados en DECISIONS.md.
