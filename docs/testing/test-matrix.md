---
responsable: propietario
estado: vigente
revisado: 2026-05-23
revisar_cada: 180d
---

# Matriz de Trazabilidad Épica ↔ US ↔ TC

**ID:** `DOC-TEST-MATRIX`

Esta matriz es **la fuente de la verdad** para saber qué cubre qué. Debe mantenerse alineada con los archivos de épicas. Cada fila corresponde a un Test Case único.

**Leyenda de estado:**
- 🟡 `planned` — definido, aún no implementado
- 🟢 `passing`
- 🔴 `failing`
- ⏸️ `quarantined`
- 🗑️ `obsolete` — eliminado pero se mantiene registro por 1 release

---

## Épica EP001 — Autenticación y usuarios

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| TC-001 | US-001 | unit | Política de password rechaza débiles | 🟡 |
| TC-002 | US-001 | int | POST user con email duplicado → 409 | 🟡 |
| TC-003 | US-001 | int | Crear user happy path → hash y audit log | 🟡 |
| TC-004 | US-001 | e2e | Admin crea → user hace login | 🟡 |
| TC-005 | US-002 | int | Login con username ok → 200, JWT válido | 🟡 |
| TC-006 | US-002 | int | Login con email ok → 200 | 🟡 |
| TC-007 | US-002 | int | Password mal → 401 + failed+=1 | 🟡 |
| TC-008 | US-002 | int | User inactivo → 403 | 🟡 |
| TC-009 | US-002 | e2e | Login UI persiste sesión | 🟡 |
| TC-010 | US-003 | int | 5 fails → 6º bloqueado 403 | 🟡 |
| TC-011 | US-003 | int | Expira lockout, login permitido | 🟡 |
| TC-012 | US-003 | int | Admin unlock | 🟡 |
| TC-013 | US-004 | int | Change password happy path | 🟡 |
| TC-014 | US-004 | int | New = current → 422 | 🟡 |
| TC-015 | US-004 | int | New débil → 400 | 🟡 |
| TC-016 | US-005 | int | Admin reset → temp password | 🟡 |
| TC-017 | US-006 | unit | Validar módulos/acciones permitidas | 🟡 |
| TC-018 | US-006 | int | Delete rol sistema → 403 | 🟡 |
| TC-019 | US-006 | int | Modificar rol actualiza permisos en vivo | 🟡 |
| TC-020 | US-006 | e2e | Matriz checkboxes guarda JSON ok | 🟡 |
| TC-021 | US-007 | int | Busqueda fuzzy nombre | 🟡 |
| TC-022 | US-007 | int | Filtro is_active=false | 🟡 |

## Épica EP002 — Jerarquía

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| TC-023 | US-008 | int | Org con nombre duplicado → 409 | 🟡 |
| TC-024 | US-008 | int | Soft delete no borra proyectos | 🟡 |
| TC-025 | US-008 | int | Logo > 2MB → 413 | 🟡 |
| TC-026 | US-008 | e2e | CRUD orgs desde admin | 🟡 |
| TC-027 | US-009 | int | Programa org A en proyecto org B → 422 | 🟡 |
| TC-028 | US-009 | int | Lista programas filtrados | 🟡 |
| TC-029 | US-010 | e2e | Breadcrumb navegable | 🟡 |
| TC-030 | US-010 | e2e | Sidebar muestra sólo proyectos del user | 🟡 |
| TC-031 | US-011 | int | Provision happy path → admin_password | 🟡 |
| TC-032 | US-011 | int | Slug duplicado → 409 con rollback | 🟡 |
| TC-033 | US-011 | int | Slug inválido → 400 | 🟡 |
| TC-034 | US-011 | e2e | UI superadmin provisiona tenant | 🟡 |
| TC-035 | US-012 | int | Detail devuelve populado | 🟡 |
| TC-036 | US-012 | int | Sin N+1 (≤6 queries) | 🟡 |
| TC-037 | US-013 | int | Soft delete impide login | 🟡 |
| TC-038 | US-013 | int | Hard delete con slug mal → 400 | 🟡 |
| TC-039 | US-013 | int | Hard delete ok → tablas del tenant vacías | 🟡 |
| TC-040 | US-014 | int | Join-as-admin → lista proyectos | 🟡 |
| TC-041 | US-014 | e2e | UI botón "Ingresar como admin" | 🟡 |

## Épica EP003 — Solicitud de proyectos

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| TC-042 | US-015 | unit | Validación formato moneda | 🟡 |
| TC-043 | US-015 | int | Crear request → folio SOL-YYYY-NNN | 🟡 |
| TC-044 | US-015 | int | Attachment > 25MB → 413 | 🟡 |
| TC-045 | US-015 | int | MIME no whitelisted → 415 | 🟡 |
| TC-046 | US-015 | e2e | Form multi-step con autosave | 🟡 |
| TC-047 | US-016 | int | Listado filtra por estado | 🟡 |
| TC-048 | US-016 | e2e | Revisor abre detalle con attachments | 🟡 |
| TC-049 | US-017 | int | Reject sin comment → 400 | 🟡 |
| TC-050 | US-017 | int | Aprobar 2× → 409 state transition | 🟡 |
| TC-051 | US-017 | int | needs_info → editar → re-submit | 🟡 |
| TC-052 | US-018 | int | Approved → create project con datos pre-cargados | 🟡 |
| TC-053 | US-018 | int | Create desde in_review → 422 | 🟡 |
| TC-054 | US-018 | int | Idempotencia en create-project | 🟡 |
| TC-055 | US-019 | int | PATCH en approved → 409 | 🟡 |
| TC-056 | US-019 | e2e | Solicitante ve comment + responde | 🟡 |

## Épica EP004 — Dashboard

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| TC-057 | US-020 | int | Admin ve todo; Viewer solo asignados | 🟡 |
| TC-058 | US-020 | int | Caché Redis segunda llamada <50ms | 🟡 |
| TC-059 | US-020 | e2e | Click KPI navega a filtrado | 🟡 |
| TC-060 | US-021 | int | Datasets de gráficos agregan correcto | 🟡 |
| TC-061 | US-021 | e2e | Gráficos accesibles + tooltips | 🟡 |
| TC-062 | US-022 | int | Cálculo salud (desvío>10% → yellow) | 🟡 |
| TC-063 | US-022 | int | Export CSV PlanVsReal | 🟡 |
| TC-064 | US-022 | e2e | Filtros actualizan sin reload | 🟡 |
| TC-065 | US-023 | e2e | Snapshot visual 3 breakpoints | 🟡 |
| TC-066 | US-023 | unit | Preferencias persisten | 🟡 |

## Épica EP005 — Proyectos

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| TC-067 | US-024 | int | Filtros combinados | 🟡 |
| TC-068 | US-024 | int | Busqueda fuzzy | 🟡 |
| TC-069 | US-024 | e2e | URL refleja filtros | 🟡 |
| TC-070 | US-025 | int | Fechas inconsistentes → 422 | 🟡 |
| TC-071 | US-025 | int | PM auto-asignado | 🟡 |
| TC-072 | US-026 | int | Detail incluye counts | 🟡 |
| TC-073 | US-026 | e2e | Toolbar abre módulos | 🟡 |
| TC-074 | US-027 | int | Editar folio → 400 | 🟡 |
| TC-075 | US-027 | int | Diff en audit_log | 🟡 |
| TC-076 | US-028 | int | Transición inválida → 409 | 🟡 |
| TC-077 | US-028 | int | Closed bloquea writes (salvo lessons) | 🟡 |
| TC-078 | US-029 | int | Agregar member duplicado → 409 | 🟡 |
| TC-079 | US-029 | int | Remover PM → 422 | 🟡 |
| TC-080 | US-030 | int | JSON export válido | 🟡 |
| TC-081 | US-030 | e2e | PDF descarga y abre | 🟡 |

## Épica EP006 — Módulos

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| TC-082 | US-031 | unit | Cálculo severidad P×I | 🟡 |
| TC-083 | US-031 | int | Filtro severity_min=13 | 🟡 |
| TC-084 | US-031 | e2e | Matriz P×I | 🟡 |
| TC-085 | US-031 | int | Close sin closure_note → 422 | 🟡 |
| TC-086 | US-032 | int | Query issues overdue | 🟡 |
| TC-087 | US-032 | e2e | Badge vencido | 🟡 |
| TC-088 | US-033 | int | Aprobar sin permiso → 403 | 🟡 |
| TC-089 | US-033 | int | rejected→approved → 409 | 🟡 |
| TC-090 | US-034 | int | Mismo name → version=2 | 🟡 |
| TC-091 | US-034 | int | MIME no whitelisted → 415 | 🟡 |
| TC-092 | US-034 | int | URL download expirada → 403 | 🟡 |
| TC-093 | US-035 | int | Búsqueda full-text por tag | 🟡 |
| TC-094 | US-035 | int | Viewer lee lecciones cross-proyecto | 🟡 |
| TC-095 | US-036 | int | Convertir acuerdo → issue action | 🟡 |
| TC-096 | US-036 | e2e | Export PDF minuta | 🟡 |
| TC-097 | US-036 | int | Minuta IA marca flag | 🟡 |

## Épica EP007 — Admin

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| TC-098 | US-037 | int | Desactivar propia → 422 | 🟡 |
| TC-099 | US-037 | int | Bulk asignar rol a 10 users | 🟡 |
| TC-100 | US-037 | e2e | Export CSV | 🟡 |
| TC-101 | US-038 | e2e | Toggle "todos" en matriz | 🟡 |
| TC-102 | US-038 | e2e | Preview afectados | 🟡 |
| TC-103 | US-038 | int | Duplicar rol | 🟡 |
| TC-104 | US-039 | int | Métricas por org coinciden | 🟡 |
| TC-105 | US-039 | e2e | Upload logo con crop | 🟡 |
| TC-106 | US-040 | int | Sin permiso admin.projects:read → 403 | 🟡 |
| TC-107 | US-040 | int | Admin ve proyectos en orgs inactivas | 🟡 |
| TC-108 | US-041 | int | Locale change afecta UI | 🟡 |
| TC-109 | US-041 | int | Color primario en PDF | 🟡 |
| TC-110 | US-042 | int | Admin solo ve logs propios | 🟡 |
| TC-111 | US-042 | int | Filtros combinados | 🟡 |

## Épica EP008 — IA

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| ~~TC-112~~ | US-043 | unit | Chunking overlap | ❌ N/A — no hay chunking en código (post BUG-053) |
| TC-113 | US-043 | int | Mock provider IA → JSON schema válido contra `MinuteDraft` | 🟡 |
| ~~TC-114~~ | US-043 | int | ~~Ollama timeout → fallback Claude~~ | ❌ N/A — no hay cascada (BUG-053) |
| TC-115 | US-043 | e2e | Upload→generar→editar→guardar minuta | 🟡 |
| TC-116 | US-043 | int | Transcript > 5 MB → 413 PAYLOAD_TOO_LARGE | 🟡 |
| TC-117 | US-044 | int | Draft incluye top risks | 🟡 |
| TC-118 | US-044 | int | Send sin destinatarios → 400 | 🟡 |
| TC-119 | US-044 | e2e | Envío llega (mailcatcher) | 🟡 |
| TC-120 | US-044 | int | Duplicar reporte | 🟡 |
| TC-121 | US-045 | int | `POST /admin/ai/provider/test` con provider configurado → ok+latency | 🟡 |
| ~~TC-121b~~ | US-045 | — | ~~Cascade Ollama→Gemini~~ | ❌ N/A — no hay cascada |
| ~~TC-121c~~ | US-045 | — | ~~Cascade Gemini→Claude~~ | ❌ N/A |
| ~~TC-121d~~ | US-045 | — | ~~Admin reordena cascada~~ | ❌ N/A — UI no es drag&drop, es selección única por modo |
| TC-122 | US-045 | int | API key BYO cifrada Fernet + enmascarada en GET | 🟡 |
| TC-123 | US-045 | e2e | `ai_mode=disabled` oculta botones "Generar con IA" | 🟡 |
| TC-124 | US-046 | int | Agregados de tokens/costo (vía `/superadmin/ai/groq-usage`) | 🟡 |
| TC-125 | US-046 | int | Filtro `ai_jobs.status=failed` | 🟡 |

## Épica EP009 — MS Project

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| TC-126 | US-047 | unit | Parser deps FS/SS/FF/SF + lag | 🟡 |
| TC-127 | US-047 | int | XML 500 tareas importadas | 🟡 |
| TC-128 | US-047 | int | Archivo corrupto → 422 | 🟡 |
| TC-129 | US-047 | int | Re-import merge | 🟡 |
| TC-130 | US-047 | e2e | Preview + exclude + confirm | 🟡 |
| TC-131 | US-049 | e2e | Gantt 200 tareas <2s | 🟡 |
| TC-132 | US-049 | e2e | Zoom 4 niveles | 🟡 |
| TC-133 | US-049 | e2e | Tooltip dependencias | 🟡 |
| TC-134 | US-050 | unit | Detección ciclos | 🟡 |
| TC-135 | US-050 | int | Progreso padre recalculado | 🟡 |
| TC-136 | US-050 | int | Dep FS respeta lag | 🟡 |
| TC-137 | US-051 | unit | CPM camino crítico | 🟡 |
| TC-138 | US-051 | int | Move date → recalc ruta crítica | 🟡 |
| TC-139 | US-052 | int | Export XML válido vs XSD | 🟡 |

## Épica EP010 — Panel Super Admin

| TC | US | Tipo | Descripción | Estado |
|---|---|---|---|---|
| TC-140 | US-053 | int | KPI cards reflejan count exacto | 🟡 |
| TC-141 | US-053 | e2e | Dashboard < 1.5s con 50 tenants | 🟡 |
| TC-142 | US-053 | int | Actividad filtrada a `scope=platform` | 🟡 |
| TC-143 | US-054 | int | Filtros combinados devuelven count exacto | 🟡 |
| TC-144 | US-054 | e2e | Join inline redirige con admin role | 🟡 |
| TC-145 | US-054 | int | Export CSV 500 tenants < 5s | 🟡 |
| TC-146 | US-055 | int | `include=` granular devuelve solo esas keys | 🟡 |
| TC-147 | US-055 | e2e | Tabs lazy-load | 🟡 |
| TC-148 | US-055 | int | Tenant inexistente → 404 sin filtrar info | 🟡 |
| TC-149 | US-056 | e2e | Wizard happy path → login admin ok | 🟡 |
| TC-150 | US-056 | e2e | Slug duplicado → inline error | 🟡 |
| TC-151 | US-056 | int | Falla en paso 3 → rollback total | 🟡 |
| TC-152 | US-057 | int | Filtros combinados logs platform-wide | 🟡 |
| TC-153 | US-057 | int | SSE emite en < 2s | 🟡 |
| TC-154 | US-057 | int | Export CSV UTF-8 íntegro | 🟡 |
| TC-155 | US-058 | int | Motivo vacío → 400 | 🟡 |
| TC-156 | US-058 | int | Audit log con `impersonated_by_superadmin_id` | 🟡 |
| TC-157 | US-058 | e2e | Banner persistente en impersonation | 🟡 |
| TC-158 | US-059 | int | Slug mal → 400, no programa delete | 🟡 |
| TC-159 | US-059 | int | Cancel dentro de 24h → job cancelado | 🟡 |
| TC-160 | US-059 | int | Hard delete → tablas del tenant vacías | 🟡 |
| TC-161 | US-059 | e2e | Export ZIP con estructura correcta | 🟡 |
| TC-162 | US-060 | int | `POST /superadmin/ai/groq/ping` con key inválida → ok=false | 🟡 |
| TC-163 | US-060 | int | `GET /superadmin/ai/groq-usage` cerca del límite → tarjeta amarilla | 🟡 |
| TC-164 | US-061 | int | Maintenance mode → writes 503 | 🟡 |
| TC-165 | US-061 | int | `defaults.ai_mode` hereda a nuevos tenants | 🟡 |
| TC-166 | US-061 | e2e | Diff antes/después en UI | 🟡 |

## Multi-tenant isolation (transversal)

| TC | Descripción | Estado |
|---|---|---|
| TC-MT-001 | Tenant A no lee proyectos de B | 🟡 |
| TC-MT-002 | No lee risks/issues/changes/docs/lessons/minutes de B | 🟡 |
| TC-MT-003 | No edita/borra recursos de B | 🟡 |
| TC-MT-004 | No accede a reports/share-links de B | 🟡 |
| TC-MT-005 | Admin A no resetea pwd de user B | 🟡 |
| TC-MT-006 | audit_log filtra por tenant_id | 🟡 |
| TC-MT-007 | Uploads aislados por slug | 🟡 |
| TC-MT-008 | Jobs IA no procesan archivos cruzados | 🟡 |

**Total TCs documentados:** 139 (EP001–EP009) + 27 (EP010) + 8 MT = ~174 (los 4 TCs de cascada IA quedaron N/A tras BUG-053).

> **Nota 2026-05-23:** esta matriz lista los TCs planeados/documentados.
> El estado real (verde/amarillo/rojo) no se está manteniendo en CI con
> un dashboard formal — los tests reales viven en `apps/api/tests/` y
> CI corre todos los que existen (`pytest -m "not heavy"` smoke +
> `pytest -m "heavy"` en push a main). Si quieres una matriz viva,
> abrir issue para generar reporte automático desde `pytest --collect-only`.

Ver detalle de TC-MT-* en [`multi-tenant-isolation.md`](./multi-tenant-isolation.md).
