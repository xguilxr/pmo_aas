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

El módulo de Reportes existente (US-022) cubre el caso de reporte "manual/IA editable tipo Notion". Esta épica agrega un **segundo motor** de reportes (Python templated) para casos operativos recurrentes y un **postprocesamiento** de minuta IA para alinearla al formato corporativo.

## DEC a registrar en DECISIONS.md al cierre del bloque

- **DEC-014** — Reportes operativos (Avance, Seguimiento) se generan con Python + plantillas Jinja2; no pasan por IA. La IA sigue siendo opcional en el módulo de Reportes (EP006 / EP008) para reportes narrativos.
- **DEC-015** — WeasyPrint es el motor oficial de PDF (ya mencionado en US-030); se valida como infra compartida para todos los exports (charter, minutas, reportes).
- **DEC-016** — Minuta IA devuelve siempre la misma estructura post-procesada (ver US-040) y expone endpoints de export `.docx` / `.md` / `.txt`.

---

## # DONE — US-037 — Infra compartida de exportación a PDF

**Como** backend
**Quiero** una utilidad centralizada para renderizar HTML → PDF
**Para** que charter, minuta y reportes usen el mismo motor y estilo.

**Criterios de aceptación:**
- [x] Módulo `apps/api/app/services/pdf_renderer.py` con funciones `render_html(template_name, context) -> str` y `render_pdf(template_name, context) -> bytes`.
- [x] Motor: **WeasyPrint 68.1** vía `HTML(string=html).write_pdf()`.
- [x] Plantillas Jinja2 en `apps/api/app/templates/pdf/`:
  - `base.html` con header/footer configurables (@page, counter de páginas, tenant_name, title, generated_at), CSS tipografía + colores del design system (`--chrome = #182e4e`).
  - `_smoke.html` para tests.
- [x] Convención: cada recurso (charter, minuta, reporte) tendrá su propio endpoint `.../export?format=pdf` que invoca `render_pdf(...)`. Endpoint helper centralizado se integra por módulo (EP014 US-038/039/040).
- [x] Manejo de errores: fallo de render envuelto en `AppError(502, PDF_RENDER_FAILED)`. Dep faltante devuelve `AppError(502, PDF_ENGINE_UNAVAILABLE)`.
- [x] Dependencias registradas: `weasyprint==68.1`, `jinja2==3.1.4` en `requirements.txt`.

**Test Cases (4/4 verdes):**
- `test_usnew037_render_html_basic` — Jinja renderiza y contiene generated_at.
- `test_usnew037_render_pdf_returns_valid_bytes` — bytes empiezan con `%PDF` y terminan con `%%EOF`.
- `test_usnew037_render_pdf_unknown_template_raises` — template inexistente lanza excepción.
- `test_usnew037_render_pdf_handles_unicode` — acentos/emoji no rompen el render.

**Commit:** `feat(api): US-037 — infra de exportación a PDF con WeasyPrint + Jinja2`.

---

## # DONE — US-038 — Reporte de Avance de Proyecto (Python, BD, PDF)

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
- [ ] UI en `/pmo/projects/{id}?tab=reports`:
  - Botón "Generar Reporte de Avance" (nuevo) — sin IA, sin edición.
  - Al generar, descarga automática + row nuevo en listado con badge "Avance".

**Implementación:**
- Migración Alembic `20260420_0015`: añade `reports.generator` (default 'manual') + `reports.cut_off_date`.
- `apps/api/app/services/operational_reports.py::build_avance_context()` arma el contexto desde BD: info de proyecto (org/programa/PM), plan (total/done/in_progress/not_started/avg), presupuesto plan vs real, hitos cumplidos en últimos 14 días, hitos próximos, top 5 riesgos abiertos, AIDs abiertas con flag `overdue`, y count de cambios en revisión.
- Plantilla `apps/api/app/templates/pdf/reports/avance.html` extiende `base.html` (header, footer con paginación).
- Endpoints `POST /api/v1/projects/{id}/reports/avance` y `GET /api/v1/reports/{id}/avance/download` (re-descarga usa snapshot persistido en `reports.sections`).
- Frontend: botón "Reporte de Avance (PDF)" en tab Reportes del proyecto; descarga directa vía `fetch` + Blob (apiFetch no soporta respuestas binarias).

**Tests (5/5 verdes):**
- `test_usnew038_generate_and_pdf` — genera PDF válido, content-type + disposition correctos.
- `test_usnew038_persists_report_row` — row en `reports` con `generator='avance'` + snapshot del contexto.
- `test_usnew038_redownload_uses_snapshot` — endpoint de download funciona.
- `test_usnew038_cross_tenant_404` — aislamiento multi-tenant.
- `test_usnew038_non_admin_cannot_generate` — sin `projects:update` → 403.

**Commit:** `feat(api,web): US-038 — reporte de avance ejecutable sin IA`.

---

## # DONE — US-039 — Reporte de Seguimiento de Actividades (Python, BD, PDF)

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

**Implementación:**
- `operational_reports.build_seguimiento_context()` unifica tareas del plan (no cerradas) y AIDs tipo `action` abiertas, clasifica en Vencidas / En curso / Próximas y agrupa por responsable (con bucket "Sin responsable" para items sin owner).
- Plantilla `templates/pdf/reports/seguimiento.html` renderiza 3 secciones con una tabla por owner.
- Endpoints `POST /api/v1/projects/{id}/reports/seguimiento` (body: `cut_off_date?`, `window_days?`) y `GET /api/v1/reports/{id}/seguimiento/download`.
- Frontend: botón "Reporte de Seguimiento (PDF)" junto al de Avance.

**Tests (5/5 verdes):**
- `test_usnew039_generate_and_groups` — tareas + acciones clasificadas correctamente.
- `test_usnew039_persists_snapshot` — snapshot guardado con `counts` y 3 grupos.
- `test_usnew039_redownload_uses_snapshot` — re-descarga funciona.
- `test_usnew039_cross_tenant_404` — aislamiento multi-tenant.
- `test_usnew039_empty_project_no_crash` — proyecto vacío sigue generando PDF.

**Commit:** `feat(api,web): US-039 — reporte de seguimiento por responsable`.

---

## # DONE — US-040 — Formato estandarizado + export de Minuta IA

**Como** PM
**Quiero** que la minuta generada con IA siempre tenga el mismo formato y pueda descargarse en `.docx`, `.md` o `.txt`
**Para** compartirla en canales corporativos sin reformateo manual.

**Cambios posteriores (Sprint 30 Bloque 2, 2026-05-23):**
- **ENH-117 (commit `7ad1fd8`)** — Listing rediseñado: botón único "Generar Minuta" (consolidó "Generar con IA" + "Llenar manualmente"); tabla con columnas Folio | Minuta | Fecha | Tipo | Exportar | Preview | Borrar.
- **ENH-118 (commit `89a430b`)** — Exportación simplificada: solo PDF y DOCX visibles en UI; MD/TXT removidos del detail (backend sigue aceptándolos por compatibilidad).
- **BUG-062 (commit `bfe4efd`)** — Navegación en listing `/pmo/minutes` (tenant-wide): al hacer click en el nombre, abre el detail `/pmo/projects/X/minutes/Y` (antes apuntaba al listing del proyecto).

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
  - `GET /api/v1/meeting-minutes/{id}/export?format=docx|md|txt|pdf` — PDF reutiliza US-037. Backend sigue aceptando MD/TXT por compat.
  - Si `format=pdf`, filename: `Minuta_{proyecto_folio}_{fecha}.pdf`; igual para los demás.
- [ ] UI: dentro del editor de minutas (post-generación IA), botón "Descargar" con menú desplegable (PDF / DOCX). **Cambio ENH-118 (2026-05-23):** MD/TXT removidos de UI.
- [ ] Minutas **manuales** (no IA) también pueden usarse con el mismo formatter si cumplen el schema mínimo (campos opcionales se muestran como vacíos).

**Implementación:**
- `apps/api/app/services/minutes_formatter.py`: `build_view()` normaliza `MeetingMinute` al formato corporativo (título, sesión, fecha, participantes, temas enumerados, RAID tabulado con acciones agrupadas por área/responsable, notas). Exporters: `to_markdown()`, `to_plain_text()`, `to_docx()` (python-docx) y `to_pdf()` (reutiliza infra US-037).
- Plantilla `apps/api/app/templates/pdf/minutes/minute.html` extiende `base.html`.
- Endpoint `GET /api/v1/meeting-minutes/{id}/export?format=pdf|docx|md|txt` con content-type y filename apropiados (rechaza formatos inválidos con 422; cross-tenant → 404).
- `python-docx==1.2.0` añadido a requirements.

**Nota sobre el prompt IA:** el criterio original pedía actualizar el prompt de EP008 US-043 para devolver el schema extendido (`title_short`, `session_number`, etc.). El formatter tolera tanto la forma actual (`title`, `participants`, `topics`, `agreements`) como variantes futuras; el refactor del prompt queda como follow-up de EP008 cuando se quiera habilitar session_number/duration automáticos.

**Frontend:**
- `lib/api/modules.ts::exportMinute(id, format)` usa `fetch` + Blob.
- Tabla de minutas en `/pmo/projects/[id]/minutes` gana columna "Exportar" con 2 botones (PDF / DOCX) que descargan directo.
- **Cambio ENH-118 (2026-05-23):** UI expone solo PDF y DOCX; MD/TXT removidos de UI aunque el backend sigue aceptándolos por compatibilidad.
- **Cambio ENH-117 (2026-05-23):** Botón único "Generar Minuta" en lugar de "Generar con IA" + "Llenar manualmente". Columnas reordenadas: Folio | Minuta | Fecha | Tipo | Exportar (PDF/DOCX) | Preview | Borrar.

**Tests (7/7 verdes, 186 en total):**
- `test_usnew040_export_md_contains_sections` — 5 separadores `========`, "Resumen e Hitos", "RAID", "Notas adicionales", acciones agrupadas.
- `test_usnew040_export_txt` — content-type text/plain.
- `test_usnew040_export_docx_is_valid` — cabecera ZIP (`PK`) válida.
- `test_usnew040_export_pdf` — `%PDF` header.
- `test_usnew040_export_rejects_bad_format` — `?format=xlsx` → 422.
- `test_usnew040_export_cross_tenant_404` — aislamiento.
- `test_usnew040_view_groups_actions_by_owner` — unit test de build_view.

**Commit:** `feat(api,web): US-040 — export estandarizado de minuta (.pdf/.docx/.md/.txt)`.

---

## # DONE — US-056 — Calendarización automática de reportes vía Resend

**Como** PM / admin
**Quiero** programar el envío automático de un Reporte de Avance o
Seguimiento a una lista de emails con cadencia diaria/semanal/mensual
**Para** no tener que generarlo y enviarlo a mano cada periodo.

**Criterios de aceptación:**
- [x] Tabla `scheduled_reports` con: tenant_id, project_id, report_type
  (avance/seguimiento), cadence (daily/weekly/monthly), recipients
  (JSON), enabled, last_run_at, next_run_at.
- [x] CRUD endpoints: `GET|POST /api/v1/projects/{id}/scheduled-reports`
  + `PATCH|DELETE /api/v1/scheduled-reports/{id}`.
- [x] UI en `/pmo/projects/{id}/reports`: sección "Envíos automáticos
  programados" con add/edit/toggle/delete modal.
- [x] Celery beat schedule cada 5 min (`scheduled_reports.dispatch_due`)
  que busca filas `enabled=true AND next_run_at <= now()` y encola una
  task `scheduled_reports.send` por cada una.
- [x] Worker genera el PDF (Avance o Seguimiento) con el mismo
  `operational_reports.build_*_context` + `pdf_renderer.render_pdf`,
  persiste un row en `reports` (status=sent, generator=avance|seguimiento)
  y manda email vía Resend con el PDF como attachment base64.
- [x] Audit log `scheduled_report.create|update|delete|sent`.
- [x] Retry policy: `send_scheduled_report` con `max_retries=3` y
  `countdown=60s` (misma política que `notifications.send_email`).

**Implementación:**
- Migración **0018** (`scheduled_reports`) — ver `DB-CHANGES.md`.
- `app/models/scheduled_report.py` — modelo ORM.
- `app/services/scheduled_reports.py::compute_next_run(cadence)` —
  calcula el próximo `next_run_at` (daily=+1d, weekly=+7d, monthly=+30d).
- `app/api/v1/endpoints/scheduled_reports.py` — CRUD con permiso
  `projects:update` (crear/editar/eliminar) y `projects:read` (listar).
- `app/workers/tasks/scheduled_reports.py` — `dispatch_due_scheduled_reports`
  (beat) + `send_scheduled_report` (envía PDF vía Resend + actualiza
  `last_run_at`/`next_run_at` + audit log).
- `app/services/email.py::send_email_via_resend` extendido con soporte
  para múltiples destinatarios (`to: list[str]`) y `attachments`.
- `app/workers/celery_app.py` — include + beat schedule cada 5 min.
- Frontend: `apps/web/lib/api/scheduled-reports.ts` + sección
  `ScheduledReportsSection` en `/pmo/projects/[id]/reports/page.tsx`.

**Tests (9/9 verdes):**
- `test_compute_next_run_cadences` — unit de cálculo de cadencia.
- `test_us056_create_scheduled_report` — POST crea con `next_run_at`.
- `test_us056_update_toggles_next_run` — pausar/reactivar recomputa.
- `test_us056_delete_scheduled_report` — DELETE + list vacío.
- `test_us056_cross_tenant_404` — aislamiento multi-tenant.
- `test_us056_non_admin_cannot_create` — sin `projects:update` → 403.
- `test_us056_validates_recipients_not_empty` — body vacío → 422.
- `test_us056_worker_send_persists_report_and_updates_next_run` — el
  worker genera PDF, llama Resend con attachment y deja snapshot.
- `test_us056_worker_dispatch_only_due_schedules` — solo vencidos y
  habilitados se despachan.

**Commit:** `feat(api,web): US-056 — scheduled reports via Resend`.

---

## Endpoints nuevos

```
POST /api/v1/projects/{id}/reports/avance                         [US-038]
POST /api/v1/projects/{id}/reports/seguimiento                    [US-039]
GET  /api/v1/reports/{id}/avance/download                         [US-038]
GET  /api/v1/reports/{id}/seguimiento/download                    [US-039]
GET  /api/v1/meeting-minutes/{id}/export?format=docx|md|txt|pdf   [US-040]
GET  /api/v1/projects/{id}/scheduled-reports                      [US-056]
POST /api/v1/projects/{id}/scheduled-reports                      [US-056]
PATCH /api/v1/scheduled-reports/{id}                              [US-056]
DELETE /api/v1/scheduled-reports/{id}                             [US-056]
```

## Cambios de schema

Aplicados en dos migraciones sobre la tabla `reports`:

- [`20260420_0014_reports_period.py`](../../apps/api/alembic/versions/20260420_0014_reports_period.py) — columnas de período.
- [`20260420_0015_reports_generator_cut_off.py`](../../apps/api/alembic/versions/20260420_0015_reports_generator_cut_off.py) — `generator` (`'manual' | 'ai' | 'avance' | 'seguimiento'`) + `cut_off_date`.

US-040 (formato estandarizado de minuta IA) es post-procesamiento
sobre `meeting_minutes`; no toca BD. Ver
[`DB-CHANGES.md` §EP014](./DB-CHANGES.md#ep014--entregables-operativos).

## Dependencias técnicas

- Python: `weasyprint`, `python-docx`, `jinja2` (Jinja2 ya es parte del stack).
- Node libs para UI: ninguna nueva (la descarga es vía `<a href>` a endpoint backend).

---

## Definition of Done

- [ ] Infra PDF compartida funcional (US-037).
- [ ] 2 reportes Python ejecutables, sin IA, descargables en PDF (US-038, 039).
- [ ] Minuta IA con formato estandarizado + 4 formatos de export (US-040).
- [ ] Documentos generados quedan en `documents` con `category` correcta para trazabilidad.
- [ ] Tests unit + integration + al menos 1 E2E por US.
- [ ] DEC-014, DEC-015, DEC-016 registrados en DECISIONS.md.
