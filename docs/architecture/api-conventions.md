# Convenciones del API REST

**ID:** `DOC-ARCH-API`

Reglas para cualquier endpoint de `apps/api`. Cumplirlas hace el frontend trivial, el testing consistente y los clientes externos felices.

---

## 1. Versionado y base URL

- Prefijo: `/api/v1/…` — toda ruta.
- `v2` solo si rompemos contrato. Nuevas features no-breaking siguen en `v1`.
- Métricas por versión (Sentry tag `api_version`) para detectar uso de deprecadas.

---

## 2. Autenticación y tenancy

| Header | Obligatorio | Uso |
|---|---|---|
| `Authorization: Bearer <jwt>` | Sí (excepto `/auth/login`, `/health`) | Access token |
| `X-Tenant-ID: <uuid>` | En rutas tenant-scoped si el user tiene >1 tenant | Selecciona tenant activo (si omitido, usa `active_tenant_id` del JWT) |
| `Idempotency-Key: <uuid>` | Recomendado en POST que crean recursos | Evita duplicados |
| `Accept-Language: es|en` | Opcional | Controla idioma de mensajes de error |

Superadmin usa rutas `/api/v1/superadmin/*` y **no** envía `X-Tenant-ID` (inyecta `tenant_id` por body o query).

---

## 3. Métodos y semántica

| Método | Uso | Idempotente |
|---|---|---|
| GET | Lectura | Sí |
| POST | Crear / acciones no-CRUD (`/approve`) | No |
| PUT | Reemplazo total (poco usado) | Sí |
| PATCH | Actualización parcial | No garantizado, sí con `Idempotency-Key` |
| DELETE | Soft delete por default | Sí |

---

## 4. Convenciones de URL

- Plural y en inglés: `/projects`, `/risks`, `/meeting-minutes`.
- Sub-recursos jerárquicos cuando cae natural: `/projects/{id}/risks`, `/projects/{id}/documents`.
- Acciones no-CRUD como verbos sub-ruta: `POST /projects/{id}/phase/change`, `POST /change-requests/{id}/approve`.
- Filtros en query string: `?phase=execution&health=red&page=2&limit=20`.
- Search: `?q=consulta` (fuzzy, min 2 chars).

---

## 5. Paginación, orden y filtros

### Lista estándar

```http
GET /api/v1/projects?page=2&limit=20&sort=-created_at&phase=execution

{
  "items": [ ... ],
  "page": 2,
  "limit": 20,
  "total": 345,
  "pages": 18,
  "has_next": true,
  "has_prev": true
}
```

- `page` ≥ 1, default 1.
- `limit` default 20, máximo 100.
- `sort` sufijo: `name` (asc), `-created_at` (desc). Múltiple con coma.
- Filtros whitelisted por endpoint (documentados en OpenAPI).
- Fechas: `created_at_from=2026-01-01&created_at_to=2026-03-31` (ISO 8601).

### Cursor pagination (listas grandes)

Para `audit_log`, `tasks`:

```http
GET /api/v1/audit-logs?cursor=eyJ0IjoiMjAyNi0w...&limit=100
{ "items": [...], "next_cursor": "eyJ0..." }
```

---

## 6. Esquemas y validación

- Todo request body es un modelo Pydantic (`extra="forbid"`).
- Todo response es un modelo `*Out`.
- Generamos cliente TS vía `openapi-typescript` → `packages/sdk/`.

```python
class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=3, max_length=200)
    organization_id: UUID
    program_id: UUID | None = None
    type: Literal["innovation","transformation","operation","bau"]
    priority: int = Field(ge=1, le=5)
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = Field(default=None, ge=0)

class ProjectOut(BaseModel):
    id: UUID
    folio: str
    name: str
    phase: str
    progress: int
    health_status: str
    created_at: datetime
```

---

## 7. Respuestas de error

**Formato único:**

```json
{
  "detail": "Human-readable message in Accept-Language",
  "code": "VALIDATION_ERROR",
  "fields": {
    "name": ["String should have at least 3 characters"]
  },
  "trace_id": "a1b2c3..."
}
```

### Catálogo de códigos

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Body inválido |
| 401 | `UNAUTHENTICATED` | Token ausente/inválido/expirado |
| 403 | `FORBIDDEN` | Sin permiso |
| 403 | `ACCOUNT_LOCKED` | Bloqueo por intentos |
| 404 | `NOT_FOUND` | Recurso no existe (o tenant no lo ve) |
| 409 | `CONFLICT` | Duplicado (slug, folio, email) |
| 409 | `STATE_TRANSITION` | Transición de estado no permitida |
| 413 | `PAYLOAD_TOO_LARGE` | Archivo > 25 MB |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | MIME no whitelisted |
| 422 | `BUSINESS_RULE` | Regla de dominio violada (ej. fecha fin < inicio) |
| 429 | `RATE_LIMITED` | Demasiadas peticiones |
| 500 | `INTERNAL` | Inesperado. No exponemos stacktrace. |
| 503 | `DEPENDENCY_UNAVAILABLE` | Ollama/Claude/SMTP caído |

`trace_id` siempre incluido; el cliente lo muestra al usuario en errores 5xx para soporte.

---

## 8. Jobs asíncronos

Cuando una acción tarda >2 s (IA, import MS Project, envío masivo):

```http
POST /api/v1/ai/minutes
→ 202 Accepted
{
  "job_id": "uuid",
  "status": "queued",
  "status_url": "/api/v1/jobs/uuid",
  "estimated_duration_sec": 60
}

GET /api/v1/jobs/uuid
{
  "id": "uuid",
  "status": "running" | "succeeded" | "failed",
  "progress": 45,
  "result_url": "/api/v1/ai/minutes/{id}"  // cuando succeeded
}
```

Alternativa: **Server-Sent Events** (`text/event-stream`) para streaming de IA.

---

## 9. Uploads

- Multipart. Límite 25 MB.
- Response incluye `url` firmado con TTL 1 h para descargas.

```http
POST /api/v1/projects/{id}/documents
Content-Type: multipart/form-data

file=@plan.pdf
category=Plan
description=Plan maestro v1
```

Response:
```json
{
  "id": "uuid",
  "folio": "DOC-2026-0012",
  "filename": "plan.pdf",
  "size": 104857,
  "mime_type": "application/pdf",
  "version": 1,
  "download_url": "/api/v1/documents/uuid/download?token=…"
}
```

---

## 10. CORS

- `Access-Control-Allow-Origin`: lista estricta desde `ALLOWED_ORIGINS`.
- `Access-Control-Allow-Credentials: true` (cookies refresh).
- Preflight cacheado 1 día.

---

## 11. OpenAPI y SDK

- `GET /openapi.json` — spec completa.
- `GET /docs` — Swagger UI (deshabilitado en producción, solo staging).
- `GET /redoc` — ReDoc.
- Generamos el cliente TypeScript en CI:

```bash
pnpm openapi-typescript https://api-staging.pmoaas.com/openapi.json -o packages/sdk/src/schema.ts
```

---

## 12. Contract tests

- **Schemathesis** corre contra cada PR y valida cumplimiento del OpenAPI (status codes, headers, schemas).
- Diff del OpenAPI vs `main` comenta en el PR qué rompe.

---

## 13. Deprecación

- Se marca con header `Deprecation: Tue, 01 Jan 2027 00:00:00 GMT`.
- Documentado en CHANGELOG.md y en la descripción del endpoint OpenAPI.
- Al menos 2 releases mayores antes de remover.
