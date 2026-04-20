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
| `status` | `identified`/`analyzing`/`mitigating`/`materialized`/`closed` |

**Criterios:**
- [ ] Severidad color-coded: 1-5 verde, 6-12 amarillo, 13-25 rojo.
- [ ] Vista alternativa: **Matriz 5×5 P×I** con conteo de riesgos por celda.
- [ ] Cierre requiere comentario `closure_note` cuando `status='closed'` o `'materialized'`.

**Test Cases:**
- `TC-082` (unit) — Cálculo severidad correcto.
- `TC-083` (integration) — Filtro `severity_min=13` solo lista rojos.
- `TC-084` (E2E) — Matriz P×I navegable.
- `TC-085` (integration) — Cerrar sin `closure_note` → 422.

---

## US-032 — Módulo de Incidencias (AID)

**Campos específicos:**

| Campo | Notas |
|---|---|
| `type` | `action`/`issue`/`decision` (AID) |
| `priority` | 1-5 |
| `reported_at` | auto |
| `committed_date` | fecha compromiso |
| `status` | `open`/`in_progress`/`resolved`/`closed` |
| `resolution` | texto cuando `resolved`/`closed` |
| `comments` | array con timestamp y autor |

**Criterios:**
- [ ] Alerta visual (badge rojo) cuando `committed_date < today AND status NOT IN ('resolved','closed')`.
- [ ] AIDs `open`/`in_progress` alimentan KPI del dashboard.
- [ ] Comentarios threaded: `POST /issues/{id}/comments`.

**Test Cases:**
- `TC-086` (integration) — Query `issues?overdue=true` lista vencidas.
- `TC-087` (E2E) — Badge vencido visible en listado.

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
- [ ] Permiso `lessons:read` global dentro del tenant (no restringido por proyecto).

**Test Cases:**
- `TC-093` (integration) — Busqueda full-text encuentra lección por tag.
- `TC-094` (integration) — User viewer puede leer lecciones de todos los proyectos del tenant.

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

### US-NEW-019 — Consolidar RAID (vista unificada)

**Como** PM
**Quiero** ver Riesgos + Acciones + Incidentes + Decisiones juntos
**Para** revisar el estado completo sin saltar entre módulos.

**Criterios de aceptación (DEC-007):**
- [x] Nueva ruta `/admin/projects/{id}/raid` con 4 sub-tabs R/A/I/D.
- [x] Tab persistido en URL como `?tab=risks|actions|incidents|decisions`.
- [x] Counters por categoría visibles en el header de cada tab.
- [x] Riesgos: tabla `risks`.
- [x] Acciones: tabla `issues WHERE type='action'`.
- [x] Incidentes: tabla `issues WHERE type='issue'` (label UI = "Incidente").
- [x] Decisiones: tabla `issues WHERE type='decision'`.
- [x] Export RAID → CSV con 4 secciones (un archivo); el XLSX con 4
  sheets queda como follow-up.
- [x] Sidebar: "Riesgos" + "AIDs" reemplazados por una sola entrada
  "RAID" (los enlaces legacy siguen funcionando).
- [x] `ISSUE_TYPE_LABEL['issue']` actualizado de "Incidencia" a
  "Incidente" (DEC-007).

**Estado de integración:** DONE (US-NEW-019). Export XLSX nativo queda
como follow-up; CSV cubre el caso de uso principal.
