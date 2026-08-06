---
responsable: propietario
estado: vigente
revisado: 2026-05-23
revisar_cada: 180d
---

# Modelo de datos — PostgreSQL 16

**ID:** `DOC-ARCH-DB`
**Última verificación contra código:** 2026-05-23.

> Refleja el estado real en `apps/api/app/models/` y `apps/api/alembic/versions/`. Hay **~49 tablas activas** (vs las ~17 que documentábamos antes) y la app es portable a SQLite para tests, lo que condiciona varias decisiones de tipos.

---

## Principios reales

1. **Todas las tablas tenant-scoped llevan `tenant_id` (UUID como `String(36)`) indexado.** La columna es `NOT NULL` salvo en casos puntuales (ej. `users.tenant_id` puede ser NULL para superadmins globales; `audit_log.tenant_id` puede ser NULL para eventos platform-wide).
2. **PK = UUID v4 serializado como `String(36)`** (no v7). Cross-dialect: el helper `app/db/base.py:new_uuid()` devuelve `str(uuid4())`. Decisión: poder correr la suite de tests contra SQLite sin extensiones nativas de Postgres.
3. **Mixin `TimestampMixin`** agrega `created_at` y `updated_at` (timestamptz). El campo `deleted_at` se declara explícitamente por tabla donde aplica (no global).
4. **Soft delete** vía `deleted_at IS NULL` en los queries. No hay vista materializada ni filtro automático.
5. **Folios** por tenant + año vía tabla **`folio_sequences`** (no via sequence Postgres nativa). Patrón: `PRJ-2026-001`, `RIS-2026-007`, etc.
6. **Timestamps en UTC** (`timestamptz` server-side). Formateo a TZ del tenant en el frontend.

### Lo que NO usamos (a pesar de lo que decía la versión vieja del doc)

| Mito | Realidad |
|---|---|
| Row-Level Security (RLS) habilitado | **No.** Cero migraciones tocan `ENABLE ROW LEVEL SECURITY`. El aislamiento se hace en la capa de aplicación: cada endpoint filtra `WHERE tenant_id = :tenant_id`. Los tests `TC-MT-*` aún validan el aislamiento end-to-end. |
| `SET LOCAL app.tenant_id` por request | **No.** No existe ese mecanismo en el código. |
| Roles Postgres `app_user` / `app_superadmin` con `BYPASSRLS` | **No.** La app conecta con un solo rol; el bypass de superadmin se hace en la capa Python omitiendo el filtro `tenant_id` cuando `is_superadmin`. |
| Extensiones `pg_trgm`, `uuid-ossp`, `pgcrypto` | **No instaladas.** Ninguna migración tiene `CREATE EXTENSION`. Búsqueda fuzzy hoy es `ILIKE`. |
| UUID v7 | UUID v4 (`uuid.uuid4()`). |

> **Implicación:** la "defensa en profundidad" via RLS no existe. Un bug en una query que omita el filtro `tenant_id` rompería el aislamiento. Esto se mitiga con (a) los tests de aislamiento, (b) revisar cada endpoint nuevo en code review, y (c) el helper de queries que toma `tenant_id` como dependencia obligatoria. Migrar a RLS real está en `DECISIONS.md` como deuda técnica.

---

## Diagrama ER

**El diagrama se genera del modelo** (MCS DOC-03): vive en
[`er-generado.md`](er-generado.md) y lo produce `scripts/generar_er.py` desde
`Base.metadata`, el mismo origen del que Alembic saca las migraciones.

Aquí había uno dibujado a mano, y el encabezado de la sección siguiente decía
«las 49 reales» cuando eran **56**. Siete de más, y nadie lo notó: un diagrama a
mano no falla, envejece. `tests/test_doc03_er_generado.py` falla si el generado
se queda atrás del modelo.

Lo que **no** se genera —y por eso sigue abajo, escrito por personas— es para
qué sirve cada tabla y qué invariantes tiene. Eso no está en el modelo.

---

## Tabla de tablas

> El conteo vive en [`er-generado.md`](er-generado.md), que lo deriva. Escribirlo
> aquí es cómo llegó a decir 49 con 56 tablas en el modelo.

Agrupadas por dominio. Todas heredan `TimestampMixin` salvo `audit_log` y tablas con timestamp ad-hoc.

### Auth / tenancy

| Tabla | Propósito |
|---|---|
| `tenants` | Org cliente de la plataforma. |
| `users` | Cuentas. `tenant_id` NULL solo en superadmins globales. |
| `roles` | Catálogo de roles por tenant. |
| `user_roles` | N:M user ↔ role. |
| `tenant_role_permission_overrides` | Override puntual de permisos por tenant. |
| `refresh_tokens` | Tokens de refresh persistidos (revocables). |
| `password_reset_tokens` | Tokens 1-uso para reset. |
| `approval_tokens` | Tokens para `/approve/[token]` (project requests). |
| `permission_change_requests` | Solicitudes de elevación de permisos (modera superadmin). |
| `platform_ai_settings` | Singleton row con config de Groq para modo `platform`. |

### Estructura organizacional

| Tabla | Propósito |
|---|---|
| `organizations` | Empresas/clientes dentro del tenant. |
| `business_units` | BUs dentro de la organización. |
| `departments` | Departamentos dentro de la BU. |
| `programs` | Programas (agrupan proyectos). |
| `areas` | Áreas funcionales (catálogo del tenant). |
| `teams` | Equipos dentro de un área. |
| `actors` | Personas/contactos del tenant (no necesariamente usuarios). |
| `area_assignments` | N:M área ↔ asignable. |
| `organization_user_exclusions` | Excluye usuarios específicos de una org. |
| `stakeholders` | Catálogo de stakeholders. |

### Proyectos y módulos

| Tabla | Propósito |
|---|---|
| `project_requests` | Solicitudes previas al proyecto. |
| `projects` | Tabla central. |
| `project_charters` | 1:1 charter editable por proyecto. |
| `project_artifacts` | Artefactos asociados (HTML, archivos, etc.). |
| `project_members` | Miembros con rol en el proyecto. |
| `project_participations` | Participación N:M de actores/usuarios. |
| `project_roles` | Catálogo de roles dentro de un proyecto (PM, sponsor, etc.). |
| `risks` | Riesgos. |
| `risk_actions` | Acciones para mitigar/eliminar riesgos. |
| `risk_action_assignees` | N:M risk_action ↔ asignable. |
| `issues` | AIDs (Acciones / Issues / Decisiones; campo `type` discrimina). |
| `change_requests` | Cambios. |
| `change_approvers` | Aprobadores por change request. |
| `documents` | Biblioteca documental del proyecto. |
| `lessons` | Lecciones aprendidas. |
| `meeting_minutes` | Minutas. |
| `tasks` | Tareas del cronograma. |
| `task_dependencies` | FS/SS/FF/SF entre tareas. |

### AI / reportes

| Tabla | Propósito |
|---|---|
| `ai_jobs` | Estado de jobs IA (transcripción, reporte, etc.). |
| `reports` | Reporte ejecutivo generado (AI o manual). |
| `report_history` | Versiones inmutables de reportes. |
| `report_sections` | Secciones reutilizables. |
| `report_templates` | Plantillas de layout. |
| `ai_report_templates` | Plantillas de prompt para reportes IA. |
| `report_builder_templates` | Plantillas del wizard (`/reports/builder`). |
| `scheduled_reports` | Reportes programados (cron + recipients). |
| `scheduled_minutes` | Minutas programadas. |

### Operativo / forense

| Tabla | Propósito |
|---|---|
| `notifications` | Centro de notificaciones por usuario. |
| `folio_sequences` | Contadores de folio por tenant + prefijo + año. |
| `audit_log` | Bitácora forense (ver abajo). |

---

## Tablas centrales — schema real

> Tipos según `sqlalchemy.orm` mapeados a Postgres. Donde dice `String(36)` es porque la app es portable a SQLite (tests); en Postgres es `varchar(36)`.

### `projects` (real, con campos que el doc viejo omitía)

```python
class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("tenant_id", "folio"),)

    id              String(36) PK  # uuid4
    tenant_id       String(36) NOT NULL INDEX
    organization_id String(36) NOT NULL FK organizations.id
    program_id      String(36)     FK programs.id
    business_unit_id String(36)    FK business_units.id
    department_id   String(36)     FK departments.id
    folio           String(32) NOT NULL          # 'PRJ-2026-001'
    name            String(200) NOT NULL
    description     String(5000)
    type            String(50)                   # innovation/transformation/operation/bau
    priority        SmallInt                     # 1..5
    phase           String(32) NOT NULL default 'planning'
    pm_id           String(36)     FK users.id
    sponsor         String(200)
    start_date      Date
    end_date        Date
    budget          Numeric(14,2)
    actual_budget   Numeric(14,2)
    progress        SmallInt NOT NULL default 0  # 0..100
    health_status   String(16) NOT NULL default 'green'   # computado
    status_rag      String(8)                    # ENH-101: override manual del PM (gana sobre health_status)
    request_id      String(36)                   # FK project_requests.id (sin constraint formal)
    deleted_at      DateTime(tz)
    manually_edited_fields  JSON NOT NULL default {}      # US-084: {field: {edited_at, edited_by}}
```

### `users`

```python
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id                String(36) PK
    tenant_id         String(36) INDEX  # NULL para superadmins globales
    username          String(150)        # UNIQUE(tenant_id, username)
    email             String(255)        # UNIQUE(tenant_id, email)
    password_hash     String(255)
    full_name         String(200)
    avatar_url        String(500)
    locale            String(10) default 'es-MX'
    is_active         Boolean default true
    is_superadmin     Boolean default false  # bypass del filtro tenant en la app
    last_login        DateTime(tz)
    failed_login_attempts  SmallInt default 0
    locked_until      DateTime(tz)
    # NOTA: `mfa_secret` NO existe en el modelo actual; MFA está diferido.
```

### Patrón módulos (`_ModuleBase` mixin)

Todos los módulos (`risks`, `issues`, `change_requests`, `documents`, `lessons`, `meeting_minutes`) comparten:

```python
class _ModuleBase:
    id              String(36) PK
    tenant_id       String(36) NOT NULL INDEX
    project_id      String(36) NOT NULL FK projects.id
    folio           String(32) NOT NULL  # 'RIS-2026-001', etc.
    title           String(200) NOT NULL
    description     String(5000)
    status          String(32) NOT NULL
    created_by      String(36) FK users.id
    deleted_at      DateTime(tz)
    # UNIQUE(tenant_id, folio)
```

Campos específicos:

- **`risks`** → `category`, `probability`, `impact`, `severity` (Integer, **computado en la app**, no `GENERATED ALWAYS AS` — necesitamos compat con SQLite), `mitigation_strategy`, `owner_id`, `owner_actor_id`, `area_id`, `identified_at`, `due_date`, `closure_note`, `comments` (JSON).
- **`issues`** → `type` (`action`/`issue`/`decision`), `priority`, `reported_at`, `committed_date`, `resolution`, `owner_id`, `owner_actor_id`, `area_id`, `comments`.
- **`change_requests`** → `type` (`scope`/`time`/`cost`/`resource`), `impact`, `requested_by`, `requested_at`, `approved_by`, `approved_at`. Aprobadores N:M en `change_approvers`.
- **`documents`** → `category`, `file_url`, `mime_type`, `size_bytes`, `version`. El storage real lo decide `STORAGE_BACKEND` (local Railway volume o Cloudflare R2 vía boto3) — ver [`stack.md`](./stack.md#storage-de-archivos).
- **`lessons`** → `category` (`success`/`improvement`/`error`), `phase`, `recommendation`.
- **`meeting_minutes`** → `meeting_date`, `participants` (JSON), `agreements` (JSON), `next_meeting_date`.

### `tasks`

```python
class Task(Base, TimestampMixin):
    id              String(36) PK
    tenant_id       String(36) NOT NULL INDEX
    project_id      String(36) NOT NULL FK projects.id ON DELETE CASCADE
    wbs             String(64)            # '1.2.3'
    parent_id       String(36) FK tasks.id
    name            String(300) NOT NULL
    description     String(5000)
    start_date      Date
    end_date        Date
    duration_days   Integer
    progress        SmallInt default 0
    is_milestone    Boolean default false
    owner_id        String(36) FK users.id
    priority        SmallInt
    status          String(32) default 'not_started'
    source          String(16) default 'manual'   # manual / msproject
    external_id     String(100)                    # id en el .mpp/.xml original
    imported_at     DateTime(tz)
```

```python
class TaskDependency(Base):
    id              String(36) PK
    predecessor_id  String(36) NOT NULL FK tasks.id
    successor_id    String(36) NOT NULL FK tasks.id
    type            String(2)  default 'FS'      # FS/SS/FF/SF
    lag_days        Integer    default 0
    # UNIQUE(predecessor_id, successor_id)
```

### `ai_jobs` y `reports`

```python
class AIJob(Base, TimestampMixin):
    id              String(36) PK
    tenant_id       String(36) NOT NULL INDEX
    project_id      String(36)
    kind            String(64) NOT NULL    # minute_from_transcript | progress_report | ...
    status          String(32) default 'queued'   # queued/running/succeeded/failed
    input           JSON default {}
    output          JSON
    model_used      String(100)
    tokens_in       Integer
    tokens_out      Integer
    duration_ms     Integer
    error           String(2000)
    requested_by    String(36) FK users.id
    completed_at    DateTime(tz)
    provider        String(32) INDEX        # groq/openai/claude/gemini/perplexity/azure/custom
```

```python
class Report(Base, TimestampMixin):
    id              String(36) PK
    tenant_id       String(36) NOT NULL INDEX
    project_id      String(36) NOT NULL INDEX
    title           String(200) NOT NULL
    sections        JSON default {}
    status          String(32) default 'draft'
    period          String(16)
    sent_at         DateTime(tz)
    recipients      JSON default []
    generated_by_ai Boolean default false
    generator       String(32) default 'manual'
    cut_off_date    Date
    created_by      String(36) FK users.id
    html_content    Text default ''
```

### `audit_log`

```python
class AuditLog(Base):
    id              Integer PK autoincrement     # NO bigserial; SmallInt sería corto
    tenant_id       String(36)                   # NULL para eventos platform-wide
    user_id         String(36)
    action          String(100) NOT NULL
    module          String(50)
    entity_type     String(50)
    entity_id       String(36)
    details         JSON NOT NULL default {}
    ip_address      String(64)
    user_agent      String(500)
    occurred_at     DateTime(tz) server_default now() NOT NULL
    # INDEX (tenant_id, occurred_at)
    # INDEX (user_id, occurred_at)
    # INDEX (action, occurred_at)
```

---

## Aislamiento multi-tenant (sin RLS)

Patrón estándar en cada endpoint:

```python
@router.get("/projects")
async def list_projects(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),  # del JWT
):
    stmt = select(Project).where(
        Project.tenant_id == tenant_id,
        Project.deleted_at.is_(None),
    )
    return (await db.execute(stmt)).scalars().all()
```

**Tests bloqueantes:** los `TC-MT-*` en `docs/testing/multi-tenant-isolation.md` validan que un user del tenant A nunca pueda leer/escribir contra tenant B. Ver también `tests/test_tenant_isolation*`.

**Superadmin:** los endpoints `/api/v1/superadmin/*` dependen de `get_superadmin_user` (chequea `user.is_superadmin == True`) y omiten el filtro `tenant_id` o reciben el `tenant_id` objetivo como query param explícito.

---

## Migraciones

- Tool: **Alembic**. Convención: `YYYYMMDD_NNNN_slug.py` (74 migraciones al 2026-05-25; ver `apps/api/alembic/versions/`).
- **1 PR = 1 migración** preferible. Migraciones grandes se dividen.
- **`DROP COLUMN` en 2 pasos:** primero deprecar en código, luego drop en migración siguiente. Ver `DB-CHANGES.md` para el log.
- `alembic downgrade` debe funcionar siempre; valida CI.
- **No hay seeds en Alembic.** Los datos iniciales (roles sistema, tenant demo, superadmin) se crean por scripts dedicados o por endpoints del superadmin.

---

## Backups & retención

- **Railway Postgres**: backup diario automático (retención según plan).
- Snapshot semanal externo: pendiente de configurar (ver `runbooks/`).
- DR test: pendiente formalizar cadencia.

---

## Índices clave reales

Hoy se declaran en los modelos (vía `index=True`) y en algunas migraciones explícitas:

```python
# audit_log
INDEX (tenant_id, occurred_at)
INDEX (user_id, occurred_at)
INDEX (action, occurred_at)

# projects (declarados via index=True en columnas)
INDEX (tenant_id)

# tasks, risks, issues, ... mismo patrón sobre tenant_id, project_id
```

> **Pendiente** (mencionado como deuda): índices parciales `WHERE deleted_at IS NULL` para listados frecuentes, GIN trigram para búsqueda fuzzy. Hoy no existen. Crear migración cuando se priorice perf.

---

## Deuda técnica conocida (DB)

| Item | Estado | Notas |
|---|---|---|
| Migrar a RLS real | Pendiente | Defensa en profundidad para multi-tenant. |
| Extensiones `pg_trgm`/`pgcrypto`/`uuid-ossp` | No instaladas | Si se quiere fuzzy server-side. |
| UUID v7 (ordenables por tiempo) | No | Mejorarían locality de índices, pero rompen compat con `uuid.UUID(str)` simple. |
| Índices parciales `deleted_at IS NULL` | No | Mejoraría listados grandes. |
| Snapshot semanal externo (S3/R2) | No formalizado | Solo Railway daily hoy. |
