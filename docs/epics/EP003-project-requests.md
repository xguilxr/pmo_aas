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
