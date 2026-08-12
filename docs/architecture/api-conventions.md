---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 180d
---

# Convenciones del API REST

**ID:** `DOC-ARCH-API`
**Última verificación contra código:** 2026-05-23.

Reglas reales que sigue `apps/api`. Donde una sección dice "ideal" o "pendiente", describe un objetivo. El código actual todavía no lo cumple del todo.

---

## 1. Versionado y base URL

- Prefijo: `/api/v1/…` para toda la API.
- `v2` solo si rompemos contrato. Nuevas features no-breaking siguen en `v1`.
- Sin métricas formales por versión (no hay Sentry/APM integrado hoy).

---

## 2. Autenticación y tenancy

### Header obligatorio

| Header | Cuándo | Notas |
|---|---|---|
| `Authorization: Bearer <jwt>` | Todas las rutas excepto `/health`, `/api/v1/auth/login`, `/api/v1/auth/forgot-password`, `/api/v1/auth/reset`, `/api/v1/approve/*` | Access token JWT HS256 |

### Tenant activo

El tenant **NO** viaja en un header dedicado. Se resuelve del JWT:

1. Si `user.tenant_id is not None` → ese tenant.
2. Si el user es superadmin y trae `active_tenant_id` en el JWT (vía `POST /auth/switch-tenant` o `joinAsAdmin`) → ese.
3. Si no hay tenant → 403/404 en endpoints tenant-scoped.

Ver `apps/api/app/api/deps.py:CurrentUser.effective_tenant_id`.

> **No usamos `X-Tenant-ID`.** Versiones viejas del doc lo listaban. No existe en código.

### Lo que **NO** tenemos hoy

- ❌ `Idempotency-Key` header — no implementado. Si dos POST `/projects` llegan con el mismo body, se crean dos proyectos. Diferido.
- ❌ `Accept-Language` — los mensajes de error van en español, fijos en `errors.py`. No hay negociación de idioma.

---

## 3. Métodos y semántica

| Método | Uso | Idempotente |
|---|---|---|
| GET | Lectura | Sí |
| POST | Crear / acciones no-CRUD (`/approve`, `/cancel`, `/switch-tenant`) | No |
| PUT | Reemplazo total | Sí |
| PATCH | Actualización parcial | No |
| DELETE | Soft delete por default; `?permanent=true` o ruta dedicada para hard | Sí |

---

## 4. Convenciones de URL

- Plural y en inglés: `/projects`, `/risks`, `/meeting-minutes`.
- Sub-recursos jerárquicos: `/projects/{id}/risks`, `/projects/{id}/documents`, `/projects/{id}/charter`.
- Acciones no-CRUD como verbos sub-ruta:
  - `POST /change-requests/{id}/approve`
  - `POST /ai/jobs/{id}/cancel`
  - `POST /auth/switch-tenant`
  - `POST /superadmin/tenants/{id}/freeze`
- Filtros en query string: `?phase=execution&health=red&page=2&limit=20`.
- Search: `?q=consulta` (búsqueda LIKE case-insensitive; ver §5.2).

---

## 5. Paginación, orden y filtros

### 5.1 Formato actual: array plano + page/limit

La mayoría de los endpoints de listado devuelve **un array bare**, no un envelope:

```http
GET /api/v1/projects?page=1&limit=15&phase=execution

[
  { "id": "...", "folio": "PRJ-2026-001", "name": "...", ... },
  ...
]
```

- `page` ≥ 1, default 1.
- `limit` default **15**, máximo 100. (No 20 como decía el doc viejo.)
- Orden por default: `created_at DESC` (varía por endpoint).
- Filtros: query params whitelisted por endpoint (ver OpenAPI).
- Multi-valor: usar el query param repetido (`phase=planning&phase=execution`).

### 5.2 Búsqueda (`q`)

Hoy es `LOWER(field) LIKE %q%` server-side (sin `pg_trgm`, ver `database.md`). Min 2 chars recomendado.

### 5.3 Pendiente / no implementado

- ❌ Envelope `{ items, total, pages, has_next, has_prev }` — diferido. El frontend pagina sin saber el total.
- ❌ Cursor pagination — no implementada.
- ❌ Sort multi-columna (`sort=-priority,name`) — no implementado.
- ❌ Rangos de fecha `created_at_from/to` — solo en algunos endpoints (audit, raid_export). Caso por caso.

---

## 6. Esquemas y validación

- Request body: Pydantic v2 (`apps/api/app/schemas/`).
- Response: modelo `*Read` o `*Out` dedicado.
- **No todos los schemas usan `extra="forbid"`** todavía — depende del modelo. Tenerlo como objetivo en code review.

```python
class ProjectCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    organization_id: UUID
    program_id: UUID | None = None
    type: Literal["innovation","transformation","operation","bau"] | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = Field(default=None, ge=0)

class ProjectRead(BaseModel):
    id: UUID
    folio: str
    name: str
    phase: str
    progress: int
    health_status: str
    status_rag: str | None
    created_at: datetime
```

---

## 7. Respuestas de error

**Formato real** (vía `app.core.errors.AppError`):

```json
{
  "detail": {
    "detail": "mensaje legible",
    "code": "CODIGO_ESTABLE",
    "fields": { "name": ["..."] }
  }
}
```

> El body real lleva un **doble `detail`** por cómo FastAPI envuelve `HTTPException.detail`. El frontend lo aplana al consumir. No hay `trace_id` (no hay APM ni tracing distribuido).

### Catálogo de códigos reales (de `core/errors.py`)

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Body inválido |
| 401 | `UNAUTHENTICATED` | Token ausente/inválido/expirado |
| 403 | `FORBIDDEN` | Sin permiso / capability |
| 404 | `NOT_FOUND` | Recurso no existe (o el tenant no lo ve) |
| 409 | `CONFLICT` | Duplicado (slug, folio, email) |
| 422 | `BUSINESS_RULE` | Regla de dominio violada |
| 429 | `RATE_LIMITED` | El llamador superó su cuota (AM-09: fallos de login por IP) |
| 503 | `SERVICE_UNAVAILABLE` | Provider de IA caído u otra dependencia externa |

### Cómo se escribe el texto de un error (MCS LEN-02)

> **Norma para lo nuevo, decidida el 2026-08-05.** Los cinco defectos del
> catálogo ya cumplen. Los mensajes con texto propio se arreglan **al tocar el
> endpoint**, no en una tanda. Medido ese día: de 159 mensajes con texto
> explícito, 152 dicen solo qué pasó. 21 nombran campos internos. Cerrar eso de
> golpe es trabajo uno por uno, sin palanca común. No compra nada que un
> usuario note antes que el resto del roadmap.

Todo mensaje nuevo dice **las tres cosas**, en este orden:

| | Pregunta | Ejemplo |
|---|---|---|
| **Qué** | ¿Qué ocurrió? | «No pudimos verificar tu identidad.» |
| **Por qué** | ¿Por qué ocurrió? | «El usuario o la contraseña no coinciden, o la sesión expiró.» |
| **Qué hacer** | ¿Qué puede hacer quien lee? | «Vuelve a iniciar sesión; si no lo consigues, usa «¿Olvidaste tu contraseña?».» |

Tres reglas que salen de los defectos que la auditoría encontró:

1. **Nada de nombres de campo internos.** «cambia `pm_id` primero» no significa
   nada para quien lo lee. Se nombra el concepto —«el responsable del
   proyecto»—, no la columna.
2. **El «qué hacer» lleva verbo.** Si no propone una acción que el usuario pueda
   ejecutar, no es un «qué hacer». Es un lamento. Si de verdad no hay nada que
   pueda hacer, se dice a quién acudir.
3. **El cliente reacciona por `code`, nunca por el texto.** El texto se reescribe
   sin avisar. El `code` es el contrato.

Cuando el sitio **no** pasa texto propio, se aplica el defecto del catálogo
(`app/core/errors.py`). Las tres partes se guardan como campos separados
—`que`, `porque`, `accion`—. Así no se pueden rellenar a medias.
Lo vigila `tests/test_len02_mensajes_de_error.py`.

Códigos adicionales que algunos endpoints emiten ad-hoc (no centralizados):

- `ACCOUNT_LOCKED` (403) — login después de 5 fails.
- Errores de IA específicos (`gemini_no_api_key`, `claude_connect_error`, `groq_no_api_key`, etc.) — los genera cada provider. Llegan como `code` granular.

> **Códigos del doc viejo que NO están** en código: `PAYLOAD_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `STATE_TRANSITION`, `INTERNAL` formal. `RATE_LIMITED` sí está desde el 2026-08-05 (AM-09). Si los necesitas, agregarlos al catálogo central.

---

## 8. Jobs asíncronos

Tareas IA, importación MS Project larga y generación de reportes corren en el worker Celery. El endpoint encola y responde `202`:

```http
POST /api/v1/ai/minutes
Content-Type: multipart/form-data

→ 202 Accepted
Location: /api/v1/ai/jobs/{job_id}

{ "job_id": "uuid", "status": "queued", ... }
```

```http
GET /api/v1/ai/jobs/{job_id}

{
  "id": "uuid",
  "status": "queued" | "running" | "succeeded" | "failed",
  "kind": "minute_from_transcript",
  "provider": "groq",
  "output": { ... },     // cuando succeeded
  "error": "...",        // cuando failed
  "tokens_in": 1234,
  "tokens_out": 567,
  "duration_ms": 4500
}
```

Cancelación: `POST /api/v1/ai/jobs/{job_id}/cancel`.

**No usamos Server-Sent Events** ni websockets — el frontend hace **polling** con `lib/hooks/use-ai-job-polling.ts`.

---

## 9. Uploads

- Multipart (`Content-Type: multipart/form-data`).
- Storage según `STORAGE_BACKEND` (`local` Railway Volume o `s3` Cloudflare R2 — ver `stack.md`).
- Límites configurados por endpoint (`/projects/{id}/documents`, `/project-artifacts`, etc.) — no hay límite global formal.
- Validación de MIME caso por caso. No hay whitelist central.

Ejemplo:

```http
POST /api/v1/projects/{id}/documents
Content-Type: multipart/form-data

file=<bytes>
category=Plan
description=Plan maestro v1
```

Response típica:

```json
{
  "id": "uuid",
  "folio": "DOC-2026-0012",
  "file_url": "...",
  "mime_type": "application/pdf",
  "size_bytes": 104857,
  "version": 1
}
```

> Las URLs firmadas con TTL no están implementadas como mecanismo general. Descarga directa por endpoint dedicado o por proxy del backend.

---

## 10. CORS

- `Access-Control-Allow-Origin`: lista estricta desde `ALLOWED_ORIGINS` (coma-separado).
- `Access-Control-Allow-Credentials: true` (para la cookie de refresh).
- `expose_headers=["Content-Disposition"]` — permite que el frontend lea el nombre de archivo real en descargas.

---

## 11. OpenAPI y SDK

- `GET /openapi.json` — spec completa.
- `GET /docs` — Swagger UI. **Habilitado en todos los entornos hoy** (no hay env gate). Si quieres ocultarlo en prod, pasar `docs_url=None` cuando `PYTHON_ENV=production`.
- `GET /redoc` — ReDoc.

### SDK

`packages/sdk/` existe como package del workspace (`@pmoaas/sdk`). Es un placeholder (solo `index.ts` + `package.json`). No hay generación automática vía `openapi-typescript`. El frontend consume el API con `fetch` envuelto en `apps/web/lib/api/*.ts` (un archivo por dominio: `projects.ts`, `risks.ts`, etc.).

---

## 12. Contract tests

- **No hay Schemathesis** en CI hoy. Diferido.
- La validación de regresiones del API depende de los tests de pytest convencionales (`apps/api/tests/`).

---

## 13. Deprecación

- Sin política formal de header `Deprecation`.
- Cambios breaking se documentan en epic + commit con `BREAKING`. Se anuncian al owner. Cuando consolidemos un CHANGELOG, este apartado se formaliza.

---

## 14. Sobre el doble `detail`

El `AppError` envuelve la información en `HTTPException.detail`. FastAPI serializa esa key tal cual. Resultado en wire:

```json
{
  "detail": {
    "detail": "No pudimos verificar tu identidad. El usuario o la contraseña no coinciden, o la sesión expiró. Vuelve a iniciar sesión; si no lo consigues, usa «¿Olvidaste tu contraseña?».",
    "code": "UNAUTHENTICATED",
    "fields": {}
  }
}
```

El frontend deshace el envelope al consumir errores (`apps/web/lib/api/*` mira `data.detail?.detail || data.detail`).

> **El texto es largo a propósito** (MCS LEN-02, 2026-08-05). Antes decía
> «Credenciales inválidas»: un qué sin un porqué y sin salida. Los cuatro
> defectos del catálogo —`UNAUTHENTICATED`, `FORBIDDEN`, `NOT_FOUND` e
> `INTERNAL_SERVER_ERROR`— viven en `app/core/errors.py`. Guardan tres campos
> separados (`que`, `porque`, `accion`), no una frase. Así no se
> pueden rellenar a medias. **El cliente sigue reaccionando por `code`**. El
> texto es para quien lo lee. No debe usarse para bifurcar lógica.

Si quieres una forma `{ code, detail, fields }` plana, registra un `exception_handler` en `main.py` que normalice antes de devolver. Es deuda técnica baja-prioridad.
