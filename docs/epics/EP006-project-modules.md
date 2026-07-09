# EP006 — Módulos del Proyecto (Riesgos, Incidencias, Cambios, Documentos, Lecciones, Minutas)

| Campo | Valor |
|---|---|
| **ID** | EP006 |
| **Prioridad** | Alta |
| **Dependencias** | EP005 |
| **Módulos** | `risks`, `issues`, `change_requests`, `documents`, `lessons`, `meeting_minutes` |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |

## Objetivo de negocio

Los 6 módulos transversales son el **corazón operativo** del proyecto. Cada uno sigue el mismo patrón CRUD + filtros + detalle + historial. Tratarlos como un solo patrón acelera desarrollo, tests y UX consistente.

## Patrón común (aplica a los 6)

- **Header** con título del módulo, contador, botón "+ Nuevo".
- **Filtros** avanzados: estado, responsable, fecha (rango), texto libre.
- **Matriz** con paginación y orden.
- **Click en fila** → drawer lateral (slide desde la derecha) o ruta `/projects/{id}/{module}/{recordId}` con detalle completo.
- **Historial** de cambios visible en cada detalle (lee `audit_log` filtrado).
- **Folio único** por tipo: `RIS-`, `INC-`, `CHG-`, `DOC-`, `LEC-`, `MIN-`.

---

## US-031 — Módulo de Riesgos

**Como** PM
**Quiero** gestionar riesgos del proyecto
**Para** anticipar problemas.

**Campos específicos:**

| Campo | Notas |
|---|---|
| `title`, `description`, `category` | |
| `probability` (1-5), `impact` (1-5) | |
| `severity` | generada `P × I` |
| `mitigation_strategy` | texto |
| `owner_id`, `due_date` | |
| `status` | `open` / `in_progress` / `on_hold` / `resolved` |
| `on_hold_reason`, `on_hold_area_id`, `on_hold_actor_id`, `on_hold_since` | solo si `status='on_hold'` |

**Criterios:**
- [ ] Severidad color-coded: 1-5 verde, 6-12 amarillo, 13-25 rojo.
- [ ] Vista alternativa: **Matriz 5×5 P×I** con conteo de riesgos por celda.
- [ ] Estados unificados con riesgos e incidencias (US-179): `open` (Abierto), `in_progress` (En Progreso), `on_hold` (Detenido), `resolved` (Resuelto). On Hold es opcional, captura razón de detención + dependencia (área + responsable) + fecha de inicio de detención.
- [ ] `closure_note` ya no es obligatorio al resolver (2026-06-29).

**Test Cases:**
- `TC-082` (unit) — Cálculo severidad correcto.
- `TC-083` (integration) — Filtro `severity_min=13` solo lista rojos.
- `TC-084` (E2E) — Matriz P×I navegable.

**Cambios recientes (2026-06-29):**
- **US-179:** Estados unificados a 4. On Hold captura razón obligatoria + dependencia (área + responsable) + `on_hold_since` (fecha inicio detención, para visibilidad de tiempo detenido). `closure_note` ya no obligatorio al resolver.
- **US-178:** Edición inline de P, I (severity recomputada), estado, prioridad, etc. en la lista.
- **BUG-086:** Responsables asignables detectados via `eligible-actors` (área_id visible).

---

## US-032 — Módulo de Incidencias (AID)

**Campos específicos:**

| Campo | Notas |
|---|---|
| `type` | `action`/`issue`/`decision` (AID) |
| `priority` | 1-5 |
| `reported_at` | fecha elegida en el form de nuevo ítem, respetada al crear (US-178, BUG-084) |
| `committed_date` | fecha compromiso, grabada y limpiable (PATCH con exclude_unset) |
| `status` | `open` / `in_progress` / `on_hold` / `resolved` |
| `on_hold_reason`, `on_hold_area_id`, `on_hold_actor_id`, `on_hold_since` | solo si `status='on_hold'` |
| `resolution` | texto cuando `resolved` |
| `comments` | array con timestamp y autor |

**Criterios:**
- [ ] Alerta visual (badge rojo) cuando `committed_date < today AND status NOT IN ('on_hold','resolved')`.
- [ ] AIDs `open`/`in_progress` alimentan KPI del dashboard.
- [ ] Comentarios threaded: `POST /issues/{id}/comments`.
- [ ] Estados unificados con riesgos (US-179): `open`, `in_progress`, `on_hold`, `resolved`. On Hold captura razón obligatoria + dependencia (área + responsable) + fecha de inicio de detención.
- [ ] Edición inline de todos los campos en la lista (US-178): título, área, responsable, severidad (P/I), prioridad, estado, fechas de creación y compromiso.

**Test Cases:**
- `TC-086` (integration) — Query `issues?overdue=true` lista vencidas.
- `TC-087` (E2E) — Badge vencido visible en listado.

**Cambios recientes (2026-06-29):**
- **US-179:** Estados RAID unificados a 4 (`open`/`in_progress`/`on_hold`/`resolved`). Migración 0089 agrega columnas `on_hold_*` a `issues` y `risks`. Mapeo legacy: `identified`/`analyzing`/`mitigating`→`in_progress`; `materialized`/`closed`→`resolved` (riesgos); `closed`→`resolved` (incidencias).
- **US-178:** Edición inline de todos los campos en la lista RAID (título, área, responsable, severidad P/I, prioridad, estado con tag de color, fechas creación/compromiso). Folio es el único link que abre el ticket; título es editable. Acciones por fila: vista rápida, Editar (modal → vuelve a lista), Borrar.
- **BUG-084:** `reported_at` (issues) respeta fecha elegida en form de nuevo ítem. `committed_date` (issues) / `due_date` (riesgos) se guardan y pueden limpiarse (PATCH con `exclude_unset`).
- **BUG-086:** Actores con `area_id` directo a un área visible del proyecto son asignables como responsables en RAID (endpoint `eligible-actors` unifica participaciones + cascada de áreas vía `area_visibility`).

---

## US-033 — Módulo de Cambios

**Campos específicos:**

| Campo | Notas |
|---|---|
| `type` | `scope`/`time`/`cost`/`resource` |
| `impact` | texto |
| `requested_by`, `requested_at` | |
| `status` | `in_review`/`approved`/`rejected`/`implemented` |
| `approved_by`, `approved_at` | |

**Criterios:**
- [ ] Solo users con permiso `change_requests:approve` pueden aprobar.
- [ ] Transiciones: `in_review → approved/rejected → implemented`.
- [ ] Contador `in_review` alimenta KPI dashboard.
- [ ] Al aprobar, sugerir (opcional) crear tarea vinculada.

**Test Cases:**
- `TC-088` (integration) — User sin permiso aprobar → 403.
- `TC-089` (integration) — Transición `rejected → approved` → 409.

**ENH-186 (2026-07-09, `acf8d46`) — hereda estructura RAID:**
- La lista de Cambios pasa a tabla estilo RAID: sort por columna,
  filtros de estado/tipo, chips de color por estado, toggle "Mostrar
  finalizados" (oculta `approved`/`rejected`/`cancelled` por default).
- Edición inline de título/tipo con update optimista. **El estado
  conserva su flujo de aprobación de EP019** (no se edita inline, sigue
  el mismo camino `in_review → approved/rejected → implemented`).
- Folio pasa a ser el único link que abre el detalle del cambio.
- Export propio: `GET /projects/{id}/changes/export` → XLSX de 1 hoja
  ("Cambios", en español), `services/change_export.py` (mismo patrón que
  `raid_export`).

**Estado de integración:** DONE (ENH-186). 4 TC nuevos
(`test_enh186_changes_export.py`).

---

## US-034 — Módulo de Documentos

**Campos específicos:**

| Campo | Notas |
|---|---|
| `name`, `description`, `category` | `plan`/`report`/`contract`/`other` |
| `file_url`, `mime_type`, `size_bytes` | |
| `version` | auto: si mismo `name`+`category`, incrementa |
| `uploaded_by`, `uploaded_at` | auto |

**Criterios:**
- [ ] MIME whitelist: PDF, XLSX, DOCX, PPTX, PNG, JPG, CSV.
- [ ] Max 25 MB por archivo.
- [ ] URL de descarga firmada TTL 1 h.
- [ ] Versionado automático: si subes "plan.pdf" y ya existe con misma categoría, `version = max+1`.
- [ ] Listado colapsa versiones antiguas bajo el doc principal.
- [ ] Post-MVP: preview inline de PDFs y imágenes.

**Test Cases:**
- `TC-090` (integration) — Subir misma name → `version=2`.
- `TC-091` (integration) — MIME `application/x-msdownload` → 415.
- `TC-092` (integration) — URL de descarga expirada → 403.
- `TC-MT-007` (integration) — Descarga cross-tenant → 404.

---

## US-035 — Módulo de Lecciones Aprendidas

**Campos específicos:**

| Campo | Notas |
|---|---|
| `title`, `description` | |
| `category` | `success`/`improvement`/`error` |
| `phase` | fase del proyecto cuando se identificó |
| `recommendation` | texto |
| `tags` | array de strings |

**Criterios:**
- [ ] Lecciones son **cross-proyecto**: `GET /api/v1/lessons?q=&category=&tag=&project_id=&organization_id=`.
- [ ] Busqueda full-text en `title`+`description`+`recommendation` (Postgres `tsvector`).
- [ ] Exportable a CSV para workshops post-mortem.
- [ ] Lectura abierta a cualquier user autenticado del tenant (modelo capability-based DEC-024: no hay capability dedicada para módulos de proyecto).

**Test Cases:**
- `TC-093` (integration) — Busqueda fuzzy (`ILIKE`) encuentra lección por keyword.
- `TC-094` (integration) — Cualquier user del tenant lee lecciones de todos los proyectos del tenant (el rol `viewer` fue eliminado; ya no aplica).

**ENH-187 (2026-07-09, `8114214`) — hereda estructura RAID:**
- La lista de Lecciones pasa a tabla estilo RAID: sort, filtros
  categoría/fase/búsqueda, chips de color editables inline
  (categoría/fase vía `ChipSelectCell`).
- Responsable (`owner_actor`) editable inline vía `eligible-actors`
  (mismo mecanismo de EP017 US-117 para el resto de módulos RAID).
- Folio pasa a ser el único link que abre el detalle. Modal "+ Nueva
  lección" se conserva sin cambios.
- Export propio: `GET /projects/{id}/lessons/export` → XLSX de 1 hoja
  ("Lecciones", en español), `services/lessons_export.py` (mismo patrón
  que `raid_export` / ENH-186).

**Estado de integración:** DONE (ENH-187). 4 TC nuevos
(`test_enh187_lessons_export.py`).

---

## US-036 — Módulo de Minutas

**Campos específicos:**

| Campo | Notas |
|---|---|
| `title`, `meeting_date` | |
| `participants` | array de `{user_id?, name, email?}` (externos permitidos) |
| `topics` | array de `{title, notes}` |
| `agreements` | array de `{description, owner_id, due_date, status}` |
| `next_meeting_date` | opcional |
| `attachments` | array de URLs |
| `transcript_file_id` | opcional (link a archivo subido para IA) |
| `generated_by_ai` | bool |

**Criterios:**
- [ ] CRUD manual disponible siempre.
- [ ] Generación con IA (ver EP008) pre-rellena el objeto — usuario edita y guarda.
- [ ] Acuerdos pueden convertirse en incidencias tipo `action` con un click.
- [ ] Export a PDF con plantilla corporativa.
- [ ] Filtros: `project_id`, `participant_id`, rango de fechas.

**Test Cases:**
- `TC-095` (integration) — Convertir acuerdo a issue `action`.
- `TC-096` (E2E) — Export PDF con layout limpio.
- `TC-097` (integration) — Minuta generada por IA marca `generated_by_ai=true`.

---

## Endpoints (patrón repetido por módulo)

Reemplazando `{module}` por `risks` / `issues` / `change-requests` / `documents` / `lessons` / `meeting-minutes`:

```
GET    /api/v1/projects/{project_id}/{module}
POST   /api/v1/projects/{project_id}/{module}
GET    /api/v1/{module}/{id}
PATCH  /api/v1/{module}/{id}
DELETE /api/v1/{module}/{id}                 (soft)
GET    /api/v1/{module}/{id}/history         (audit_log filtrado)
```

Específicos:
```
POST /api/v1/change-requests/{id}/approve
POST /api/v1/change-requests/{id}/reject
POST /api/v1/issues/{id}/comments
POST /api/v1/projects/{project_id}/documents         (multipart)
GET  /api/v1/documents/{id}/download                 (URL firmada)
POST /api/v1/meeting-minutes/{id}/convert-agreement  (→ issue)

# 2026-07-09 — export XLSX propio por módulo (patrón RAID, ENH-186/ENH-187)
GET  /api/v1/projects/{id}/changes/export
GET  /api/v1/projects/{id}/lessons/export
```

---

## Implementación recomendada

**Hacer un paquete compartido** `packages/modules-core` (frontend) con:
- `<ModuleShell>` componente que renderiza header + filtros + tabla + paginación.
- `<ModuleDrawer>` para detalle.
- Hooks `useModuleList(moduleName)` y `useModuleRecord(moduleName, id)`.
- Configuración declarativa por módulo: columnas, filtros, schema Zod.

Resultado: agregar un módulo nuevo son ~100 líneas de configuración.

En backend, mismo approach con un mixin `TenantScopedModel` + un router factory `module_router(model, schemas)`.

---

## Definition of Done

- [ ] 6 módulos operativos con CRUD completo y permisos granulares.
- [ ] Filtros idénticos en UI y API (misma Zod schema).
- [ ] Historial por detalle lee del `audit_log`.
- [ ] Permisos verificados (TC-MT-002, TC-MT-003, TC-MT-007).
- [ ] Componente `<ModuleShell>` usado por los 6 → 0 duplicación visual.
- [ ] Matriz P×I de riesgos accesible con tooltips.
- [ ] Alerta visual de AIDs vencidas.

---

## # PENDING — User Stories nuevas

### US-019 — Consolidar RAID (vista unificada)

**Como** PM
**Quiero** ver Riesgos + Acciones + Incidentes + Decisiones juntos
**Para** revisar el estado completo sin saltar entre módulos.

**Criterios de aceptación (DEC-007):**
- [x] Nueva ruta `/pmo/projects/{id}/raid` con 4 sub-tabs R/A/I/D.
- [x] Tab persistido en URL como `?tab=risks|actions|incidents|decisions`.
- [x] Counters por categoría visibles en el header de cada tab.
- [x] Riesgos: tabla `risks`.
- [x] Acciones: tabla `issues WHERE type='action'`.
- [x] Incidentes: tabla `issues WHERE type='issue'` (label UI = "Incidente").
- [x] Decisiones: tabla `issues WHERE type='decision'`.
- [x] Export RAID → **ENH-152 (2026-06-05):** XLSX único con 4 hojas en
  español (Riesgos / Acciones / Incidencias / Decisiones), columnas
  legibles y filename `RAID-[Nombre Proyecto].xlsx`; mismo archivo para el
  botón de `/raid` y el de Documentos. (Antes: CSV cliente + XLSX follow-up.)
- [x] Sidebar: "Riesgos" + "AIDs" reemplazados por una sola entrada
  "RAID" (los enlaces legacy siguen funcionando).
- [x] `ISSUE_TYPE_LABEL['issue']` actualizado de "Incidencia" a
  "Incidente" (DEC-007).
- [x] **ENH-168 (Sprint 35):** export individual por tipo —
  `GET /projects/{id}/raid/export?only=risks|actions|incidents|decisions`
  devuelve un XLSX de 1 hoja (`{proyecto}-{tipo}.xlsx`). Sin `only` sigue
  devolviendo el combinado de 4 hojas. Botones "Exportar {tipo}" + "Exportar
  RAID (4 hojas)" en la página `/raid`.
- [x] **ENH-166 (Sprint 35):** las listas R/A/I/D ocultan finalizados por
  default (riesgos: closed; issues: resolved/closed) con toggle "Mostrar
  finalizados"; orden por fase de estado y luego severidad/prioridad.
- [x] **ENH-167 (Sprint 35):** filtro por área en la página RAID.
- [x] **US-174 (Sprint 35):** vista **Kanban** por tipo (toggle Lista/Kanban,
  persistido en `?view=`). Columnas = fases del estado (riesgos:
  identified→…→closed; issues: open→…→closed). Drag & drop para avanzar/
  retroceder de fase (PATCH status). Mover un riesgo a closed/materialized pide
  la nota de cierre (regla de negocio existente).
- [x] **US-175 (Sprint 35):** **cambio de estado inline** en las listas R/A/I/D
  (dropdown en la celda Estado → PATCH status, reusa el handler del Kanban con
  la nota de cierre para riesgos).
- [x] **ENH-175 (Sprint 35):** columna **Responsable** en las listas RAID;
  `responsible_name` se resuelve en el read (Actor del catálogo con fallback a
  Usuario, igual que el export).
- [x] **ENH-176 (Sprint 35):** **severidad inline** en riesgos — P e I editables
  en la celda (severity = P × I, recomputada por el backend).
- [x] **ENH-177 (Sprint 35):** **`category` para issues** (acciones/incidencias/
  decisiones), en paralelo a `risks.category` (migración 0087). Editable en el
  detalle del item.

**Estado de integración:** DONE (US-019). Export XLSX nativo queda
como follow-up; CSV cubre el caso de uso principal.

---

### US-020 — Categorías de documentos actualizadas

**Criterios de aceptación:**
- [x] Campo `category` en documentos acepta los 9 valores:
  `charter | plan | raid_export | transcript | minute | report | lesson |
  contract | other`.
- [x] `GET /projects/{id}/documents?category=` filtra por categoría.
- [x] `PATCH /api/v1/documents/{id}` permite actualizar title /
  description / category sin subir un archivo nuevo.
- [x] El charter al crearse queda como `category='charter'`
  (ya implementado en US-013).
- [x] Category inválida → 422 (pydantic Literal).

**Test Cases:**
- `test_usnew020_accepts_new_categories` — 9 categorías válidas ✅
- `test_usnew020_rejects_invalid_category` → 422 ✅
- `test_usnew020_filter_by_category` ✅
- `test_usnew020_patch_document_category` ✅

**Estado de integración:** DONE (US-020).

---

### US-021 — Consolidar pestañas de Minutas en 1

**Criterios de aceptación:**
- [x] Entrada separada "Minuta IA" eliminada del sidebar.
- [x] Pestaña única "Minutas" ahora incluye:
  - Listado de minutas pasadas (ya existía).
  - Botón "Nueva minuta" → modal de registro manual (ya existía).
  - Botón "Generar con IA" → navega a `/ai-minutes/new` (flujo de IA).
- [x] Regex del nodo sidebar `mod-minutes` ahora matchea también
  `/ai-minutes/*` para mantener el nodo activo durante el flujo IA.
- [x] La minuta generada con IA entra al mismo flujo de revisión/edición
  (ya estaba persistiendo en la misma tabla `meeting_minutes`).

**Cambios de componente:**
- `ModuleShell` admite nuevo prop opcional `headerExtras` para renderizar
  acciones adicionales junto al botón "Nuevo" (aplicable a cualquier
  módulo). La página Minutas lo usa para el CTA "Generar con IA".

**Estado de integración:** DONE (US-021).

---

### US-022 — Módulo Reportes dentro del proyecto

**Como** PM
**Quiero** generar y gestionar reportes de estado del proyecto
**Para** comunicar avance a stakeholders periódicamente.

**Criterios de aceptación:**
- [x] Migración Alembic `20260420_0014`: `reports.period` (String(16)).
- [x] `Report.period` en el ORM (nullable).
- [x] CRUD endpoints dedicados en `reports.py`:
  - `GET /projects/{id}/reports?status=&period=&limit=`
  - `POST /projects/{id}/reports` (crea borrador manual; secciones
    pre-llenadas por default).
  - `GET /reports/{id}`
  - `PATCH /reports/{id}` (título, periodo, destinatarios, secciones —
    rechaza si el reporte ya fue enviado).
  - `DELETE /reports/{id}` (solo borradores).
- [x] Periodicidades: `daily | weekly | monthly` (Literal pydantic).
- [x] Secciones default sugeridas: resumen_ejecutivo, avance_plan,
  acciones_pendientes, decisiones_requeridas, riesgos_top.
- [x] "Generar con IA" reutiliza endpoint EP008 existente
  (`POST /ai/projects/{id}/reports/draft`).
- [x] Frontend `/pmo/projects/{id}/reports`:
  - Listado con fecha de creación, periodo, estado, destinatarios.
  - Badge "IA" para generados con IA.
  - Botón "Nuevo reporte" → modal (título, periodo, destinatarios).
  - Botón "Generar con IA" → crea borrador vía AI y abre editor.
  - Editor: periodo, destinatarios, asunto, 5 secciones tipo Notion
    editables. Guardar / Enviar / Eliminar.
  - Reportes enviados quedan read-only.
  - Modo editor accesible vía `?report={id}` (deep-link).

**Test Cases:**
- `test_usnew022_create_and_list_reports` ✅
- `test_usnew022_patch_report_sections` ✅
- `test_usnew022_invalid_period_rejected` → 422 ✅
- `test_usnew022_filter_by_period` ✅
- `test_usnew022_delete_draft` ✅

**Estado de integración:** DONE (US-022). Caso de uso "lunes de
persecución" queda como flow de UI a futuro (requiere KPIs específicos
de acciones vencidas en el editor).
