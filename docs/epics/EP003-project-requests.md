# EP003 — Solicitud y Aprobación de Proyectos

| Campo | Valor |
|---|---|
| **ID** | EP003 |
| **Prioridad** | Alta |
| **Dependencias** | EP001, EP002 |
| **Módulo** | `project_requests` |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |

## Objetivo de negocio

Estandarizar el proceso de solicitud de nuevos proyectos: formulario con datos mínimos, revisión por PMO Manager, aprobación o rechazo con motivo, y **conversión automática a proyecto** con los datos pre-rellenados.

## Roles

- **Solicitante** — cualquier user con permiso `project_requests:create`.
- **PMO Manager** — revisa y aprueba/rechaza.

---

## User Stories

### US-015 — Crear solicitud de proyecto

**Como** Solicitante
**Quiero** llenar un formulario con los datos del proyecto propuesto
**Para** iniciar el proceso formal de aprobación.

**Campos del formulario:**

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `folio` | auto | — | `SOL-YYYY-NNN` por tenant |
| `requested_at` | auto | — | `now()` |
| `requested_by` | auto | — | user en sesión |
| `title` | text(200) | ✅ | |
| `description` | text | ✅ | |
| `objective` | text | ✅ | |
| `organization_id` | uuid | ✅ | org del tenant |
| `business_unit` | text | ✅ | |
| `department` | text | ✅ | |
| `sponsor` | text | ✅ | |
| `benefits` | text | ✅ | |
| `budget` | numeric(14,2) | ✅ | MXN, formato `$X,XXX.XX` |
| `scope` | text | ✅ | |
| `attachments` | file[] | opcional | PDF/XLSX/DOCX/PPTX/PNG/JPG, ≤ 25 MB c/u |

**Criterios de aceptación:**
- [ ] `POST /api/v1/project-requests` (multipart).
- [ ] Validación en Pydantic; error 400 con `fields` detallado.
- [ ] Folio se genera atómicamente (secuencia tenant+año).
- [ ] `status` inicial = `in_review`.
- [ ] Audita `project_request.create`.
- [ ] Attachments guardados en `/data/uploads/tenants/{slug}/requests/{id}/…`.

**Test Cases:**
- `TC-042` (unit) — Validación de formato moneda.
- `TC-043` (integration) — Crear con campos mínimos → 201, folio `SOL-2026-001`.
- `TC-044` (integration) — Attachment > 25 MB → 413.
- `TC-045` (integration) — Attachment con MIME no whitelisted → 415.
- `TC-046` (E2E) — UI: formulario multi-step (info básica → alcance → adjuntos → revisar) con autosave.

---

### US-016 — Revisar solicitud como PMO Manager

**Como** PMO Manager
**Quiero** ver solicitudes pendientes con toda la información
**Para** decidir con contexto.

**Criterios de aceptación:**
- [ ] `GET /api/v1/project-requests?status=&organization_id=&q=&page=&limit=`.
- [ ] `GET /api/v1/project-requests/{id}` — detalle con todos los campos, solicitante, attachments (con URLs firmadas).
- [ ] Vista "Bandeja de solicitudes" con tabs: En revisión, Pendiente info, Aprobadas, Rechazadas.
- [ ] Columnas: folio, título, solicitante, fecha, presupuesto, estado.

**Test Cases:**
- `TC-047` (integration) — Listado filtra por estado.
- `TC-048` (E2E) — Revisor abre detalle, ve attachments descargables.

---

### US-017 — Aprobar / Rechazar / Solicitar info

**Como** PMO Manager
**Quiero** aprobar, rechazar (con motivo) o solicitar más información
**Para** decidir formalmente.

**Criterios de aceptación:**
- [ ] `POST /api/v1/project-requests/{id}/review` con `{decision, comment?}`.
- [ ] `decision ∈ {approve, reject, needs_info}`.
- [ ] Si `reject` o `needs_info`, `comment` obligatorio.
- [ ] Transiciones válidas:
  - `in_review` → `approved` | `rejected` | `needs_info`
  - `needs_info` → `in_review` (cuando solicitante re-somete) | `rejected`
- [ ] Response incluye `reviewed_by`, `reviewed_at`, `review_comment`.
- [ ] Notificación (in-app + email) al solicitante.
- [ ] Audita `project_request.{approve|reject|needs_info}`.

**Test Cases:**
- `TC-049` (integration) — Reject sin comment → 400.
- `TC-050` (integration) — Aprobar solicitud ya aprobada → 409 `STATE_TRANSITION`.
- `TC-051` (integration) — needs_info → solicitante puede editar y re-someter.

---

### US-018 — Crear proyecto desde solicitud aprobada

**Como** PMO Manager
**Quiero** convertir una solicitud aprobada en proyecto con datos pre-cargados
**Para** no capturar dos veces.

**Criterios de aceptación:**
- [ ] `POST /api/v1/project-requests/{id}/create-project` → crea `Project` con:
  - `name = request.title`
  - `description = request.description`
  - `organization_id = request.organization_id`
  - `sponsor = request.sponsor`
  - `budget = request.budget`
  - `request_id = request.id` (traza)
  - `phase = 'planning'`
  - `pm_id` a elegir (body: `{pm_id}`).
- [ ] Solo funciona si `request.status = 'approved'`.
- [ ] Idempotente: si ya existe `project` con `request_id`, devuelve ese.
- [ ] Redirige UI al detalle del proyecto creado.

**Test Cases:**
- `TC-052` (integration) — Aprobar + crear proyecto → `project.folio = PRJ-…`.
- `TC-053` (integration) — Crear desde solicitud en `in_review` → 422.
- `TC-054` (integration) — Idempotencia: 2 llamadas → mismo `project_id`.

---

### US-019 — Re-someter solicitud con info adicional

**Como** Solicitante
**Quiero** editar mi solicitud devuelta como `needs_info` y re-someterla
**Para** responder a las dudas del revisor.

**Criterios de aceptación:**
- [ ] `PATCH /api/v1/project-requests/{id}` — solo campos editables cuando `status = 'needs_info'`.
- [ ] `POST /api/v1/project-requests/{id}/resubmit` → `status = 'in_review'`.
- [ ] Historial visible: quién editó qué (audit log).

**Test Cases:**
- `TC-055` (integration) — Editar con `status='approved'` → 409.
- `TC-056` (E2E) — Solicitante ve comentario del revisor y lo responde editando.

---

## Notas técnicas

- Folios: secuencia Postgres por `(tenant_id, prefix='SOL', year)`.
- Notificaciones: tabla `notifications` + email vía Resend.
- Tokens firmados para descargar attachments (TTL 1 h).

### Endpoints
```
POST   /api/v1/project-requests
GET    /api/v1/project-requests
GET    /api/v1/project-requests/{id}
PATCH  /api/v1/project-requests/{id}
POST   /api/v1/project-requests/{id}/review
POST   /api/v1/project-requests/{id}/resubmit
POST   /api/v1/project-requests/{id}/create-project
GET    /api/v1/project-requests/{id}/attachments/{attId}/download
```

---

## Definition of Done

- [ ] Formulario multi-step con autosave cada 30 s (`localStorage` + server draft).
- [ ] Validaciones en cliente replican servidor (Zod compartido vía `packages/sdk`).
- [ ] Notificaciones in-app + email configuradas.
- [ ] E2E: crear → aprobar → convertir a proyecto sin errores.
- [ ] 95%+ cobertura en servicios de transición de estado.

---

## # PENDING — User Stories nuevas

### US-NEW-011 — Campos adicionales en solicitud + FK BU/Depto

**Como** solicitante
**Quiero** capturar contactos (sponsor_email, solicitante) y detalles extra
(entregables, personas clave, if_not_done, observaciones)
**Para** que los revisores tengan contexto completo y FK reales a BU/Depto.

**Criterios de aceptación:**
- [x] Migración Alembic `20260420_0011`: columnas `requester_name`,
  `requester_email`, `sponsor_email`, `key_people`, `if_not_done`,
  `observations`, `entregables`.
- [x] `business_unit_id` y `department_id` validados contra tenant+org
  (422 si no pertenecen o cruzan BU).
- [x] Campos text legacy (`business_unit`, `department`) se mantienen en
  paralelo hasta migración de datos (fase 2).
- [x] `sponsor_email` obligatorio y validado como email.
- [x] Defaults: si `requester_name`/`requester_email` no vienen, se toma
  `user.full_name` / `user.email`.
- [x] Formulario multi-step actualizado con todos los nuevos campos y
  validación client-side (regex de email).
- [x] Sidebar: "Solicitudes" movido a top-level (fuera de Organizaciones).

**Test Cases:**
- `test_usnew011_full_payload` — crea con todos los campos ✅
- `test_usnew011_sponsor_email_invalid` — 422 con email mal formado ✅
- `test_usnew011_requester_defaults` — defaults al user autenticado ✅
- `test_usnew011_bu_fk_mismatch` — BU fuera del tenant → 422 ✅
- `test_usnew011_dept_in_wrong_bu` — depto no pertenece a BU → 422 ✅
- `test_usnew011_bu_dept_fk_happy_path` — FKs correctas → 201 ✅

**Estado de integración:** DONE (US-NEW-011). Charter (US-NEW-012) siguiente.

---

### US-NEW-012 — Project Charter: tabla + generación al aprobar

**Como** PMO Manager
**Quiero** que al aprobar una solicitud se genere automáticamente un
Project Charter
**Para** tener el documento fundacional del proyecto listo.

**Criterios de aceptación:**
- [x] Migración Alembic `20260420_0012`: tabla `project_charters` con
  secciones 1-3 estructuradas.
- [x] Al ejecutar `POST /project-requests/{id}/create-project` se crea un
  charter pre-llenado desde la solicitud y el proyecto.
- [x] Sección 2: `sponsor`, `sponsor_email`, `pm_id` heredados; líderes
  (negocio + técnico) quedan en blanco para completar.
- [x] Sección 4 (Gestión) se deriva dinámicamente desde `projects` al
  consultar (DEC-008).
- [x] `GET /api/v1/projects/{id}/charter` devuelve el charter completo.
- [x] `PATCH /api/v1/projects/{id}/charter` edita secciones 1-3 (valida
  FKs BU/Depto).
- [x] `GET /api/v1/projects/{id}/charter/pdf` devuelve HTML imprimible
  (generado on-demand). Renderer PDF nativo queda como follow-up; el
  navegador puede imprimir esta vista para obtener el PDF.
- [x] El proyecto generado hereda `business_unit_id` y `department_id` de
  la solicitud.

**Test Cases:**
- `TC-NEW-019` — charter auto-creado con datos correctos ✅
- `TC-NEW-020` — sección 4 refleja datos actuales del proyecto ✅
- `TC-NEW-021` — HTML imprimible contiene las 4 secciones ✅
- `test_charter_patch_edits_sections_1_to_3` ✅
- `test_charter_404_when_missing` ✅

**Estado de integración:** DONE (US-NEW-012).

---

### US-NEW-013 — Charter aparece como documento del proyecto

**Como** PM
**Quiero** ver el Project Charter listado en el módulo de Documentos del
proyecto
**Para** acceder a él desde el mismo lugar que el resto de entregables.

**Criterios de aceptación:**
- [x] Al crear el proyecto desde la solicitud, además del charter
  estructurado se registra un `Document` con `category='charter'`.
- [x] `Document.file_url` apunta a `/api/v1/projects/{id}/charter/pdf`
  (HTML imprimible on-demand, no se almacena archivo).
- [x] `mime_type='text/html'`, `is_current=true`.
- [x] Folio secuencial con prefijo `DOC-` por tenant.
- [x] Respuesta del endpoint `create-project` incluye `charter_doc_id`.

**Test Cases:**
- `TC-NEW-022` — charter aparece como documento con category='charter' ✅

**Estado de integración:** DONE (US-NEW-013).
