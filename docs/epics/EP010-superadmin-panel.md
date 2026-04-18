# EP010 — Panel de Super Admin (platform-wide)

| Campo | Valor |
|---|---|
| **ID** | EP010 |
| **Prioridad** | Alta |
| **Dependencias** | EP001, EP002 |
| **Módulo** | `superadmin.*` |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |

## Objetivo de negocio

Consolidar en una **experiencia dedicada** todas las operaciones platform-wide
que hace el Super Admin (dueño de la plataforma, no del tenant). Es la página
principal de gestión de clientes del MVP. Cubre: visión agregada, provisión y
baja de tenants, drill-down por cliente, logs y salud de infra, y
configuración global.

> EP002 contiene ya las APIs base de Super Admin (provisión, delete,
> join-as-admin, etc.). EP010 añade la **UI de alto nivel** y los
> **dashboards y herramientas** que faltaban como épica propia, además de
> algunas capacidades nuevas (health, configuración global, búsqueda
> cross-tenant).

## Roles involucrados

- Super Admin (único rol autorizado). El resto no ve ni la ruta.

## Decisiones clave

- El panel vive en `app.pmoaas.com/superadmin` con `middleware.ts` que
  verifica `is_superadmin`. Si no, 404 (no mostramos que exista).
- El dominio puede mudarse post-MVP a un subdominio separado
  (`admin.pmoaas.com`) con auth reforzada (2FA obligatorio).
- Todas las acciones de esta épica se **auditan en `audit_log` con
  `scope=platform`** — visibles solo para super admins.

---

## User Stories

### US-053 — Dashboard platform-wide

**Como** Super Admin
**Quiero** ver de un vistazo el estado de toda la plataforma
**Para** detectar problemas antes que los clientes.

**Criterios de aceptación:**
- [ ] Pantalla principal `/superadmin` con:
  - KPI cards: total tenants, activos, inactivos, usuarios totales,
    proyectos totales, storage usado, IA tokens del mes.
  - Gráfica "Tenants activos por mes" (12 meses).
  - Top 5 tenants por uso (proyectos activos + IA tokens).
  - Alertas: tenants con errores recientes, jobs IA fallidos, storage > 80% de
    límite, healthcheck rojo.
  - Widget de "Actividad reciente" (últimos 20 eventos `scope=platform`).
- [ ] Refresh auto cada 60s (Cmd+R manual también).
- [ ] Export snapshot del dashboard como PDF.

**Test Cases:**
- `TC-140` (integration) — KPI cards reflejan el count exacto de la BD.
- `TC-141` (E2E) — Dashboard carga bajo 1.5s con 50 tenants poblados.
- `TC-142` (integration) — Widget actividad solo muestra eventos `scope=platform`.

---

### US-054 — Lista maestra de tenants con filtros y búsqueda

**Como** Super Admin
**Quiero** una tabla con todos los tenants y acciones rápidas
**Para** operar sin hacer clic por cada uno.

**Criterios de aceptación:**
- [ ] Tabla columnas: slug, name, plan, estado, created_at, user_count,
      project_count, storage_mb, ai_mode, último login activo.
- [ ] Búsqueda fuzzy (slug, name, admin_email).
- [ ] Filtros: plan, estado, ai_mode, created_at rango.
- [ ] Acciones inline por fila: drill-down, join-as-admin, soft delete, toggle
      banner "modo lectura".
- [ ] Bulk actions: exportar CSV de seleccionados.
- [ ] Sort por cualquier columna.
- [ ] Paginación cursor (no offset) para escalar a 10k+ tenants.

**Test Cases:**
- `TC-143` (integration) — Filtros combinados devuelven count exacto.
- `TC-144` (E2E) — Click acción inline "Join" redirige al tenant con admin role.
- `TC-145` (integration) — CSV export con 500 tenants completa en < 5s.

---

### US-055 — Drill-down de tenant (página completa)

**Como** Super Admin
**Quiero** abrir un tenant y ver todo su estado
**Para** dar soporte y auditar.

**Criterios de aceptación:**
- [ ] Ruta `/superadmin/tenants/{slug}` con tabs:
  - **Overview**: datos, logo, admin principal, config IA, plan.
  - **Usuarios**: lista con roles, estado, último login.
  - **Proyectos**: tabla con fase, salud, PM, org.
  - **Billing** (post-MVP placeholder): consumo mes, límites.
  - **Logs**: audit log del tenant (últimos 500 events, filtros).
  - **IA**: jobs recientes, tokens mes, errores.
  - **Archivos**: storage usado, top 20 archivos por tamaño.
  - **Danger zone**: soft delete, hard delete, congelar, renombrar slug.
- [ ] Breadcrumb: Super Admin > Tenants > {slug}.
- [ ] Query único backend `GET /api/v1/superadmin/tenants/{id}/detail`
      (ya existe en EP002, se extiende con `include=` granular).

**Test Cases:**
- `TC-146` (integration) — `include=users,projects,billing` devuelve solo esas keys.
- `TC-147` (E2E) — Tabs cargan lazy (no fetch hasta que se activan).
- `TC-148` (integration) — Drill-down de tenant inexistente → 404 (no filtra
      información en el error).

---

### US-056 — Wizard de provisión de tenant (UI del API de EP002)

**Como** Super Admin
**Quiero** crear un tenant paso a paso desde UI
**Para** onboardear clientes sin tocar API directamente.

**Criterios de aceptación:**
- [ ] Wizard 3 pasos:
  1. **Cliente**: name, slug (sugerido desde name, editable), industry,
     country.
  2. **Admin inicial**: full_name, email, password (generar 24 chars o dictar);
     checkbox "enviar email de bienvenida".
  3. **Config inicial**: locale, currency, timezone, ai_mode, plan.
- [ ] Validación: slug único + regex `^[a-z0-9-]+$`, email RFC.
- [ ] Preview final con todos los datos y botón "Provisionar".
- [ ] Al éxito, muestra credenciales **una sola vez** con botones copiar y
      "Enviar por email ahora".
- [ ] Rollback visible si falla algún paso (transacción atómica backend).

**Test Cases:**
- `TC-149` (E2E) — Happy path wizard → tenant creado + admin puede login.
- `TC-150` (E2E) — Slug duplicado → mensaje inline en paso 1, no avanza.
- `TC-151` (integration) — Falla en paso 3 (crear roles sistema) → rollback
      total (no queda tenant huérfano).

---

### US-057 — Logs platform-wide con búsqueda avanzada

**Como** Super Admin
**Quiero** buscar eventos a través de **todos** los tenants
**Para** debugging y forensía.

**Criterios de aceptación:**
- [ ] `GET /api/v1/superadmin/audit-logs` con filtros:
      `tenant_id`, `user_id`, `action`, `entity_type`, `date_from`, `date_to`,
      `q` (fuzzy en `details`).
- [ ] Scope: ve logs de todos los tenants + platform (union).
- [ ] Paginación cursor; máximo 10k results por query.
- [ ] UI tipo Datadog Logs: stream en tiempo real (SSE) + filtros activos
      como chips.
- [ ] Export CSV/JSON del resultado filtrado.
- [ ] Guardar consultas favoritas por super admin.

**Test Cases:**
- `TC-152` (integration) — Filtro `tenant_id=X` + `action=login.failed` →
      solo eventos que cumplen ambas.
- `TC-153` (integration) — SSE emite dentro de 2s cuando nuevo evento ocurre.
- `TC-154` (integration) — Export CSV con 5000 rows no corrompe caracteres UTF-8.

---

### US-058 — Join as admin con sesión dual (UI de US-014)

**Como** Super Admin
**Quiero** entrar como admin de un tenant desde el panel
**Para** dar soporte con sus propios permisos.

**Criterios de aceptación:**
- [ ] Botón "Ingresar como admin" en drill-down (US-055) y en la tabla
      (US-054).
- [ ] Confirmación modal con motivo (text field obligatorio) y duración
      sesión (default 1h, max 8h).
- [ ] Sesión impersonated visible con banner rojo persistente: "Sesión como
      Admin de {tenant} — volver a Super Admin".
- [ ] Todos los eventos ejecutados durante impersonation registran
      `impersonated_by_superadmin_id` en `audit_log`.
- [ ] Al terminar, volver automático al panel Super Admin.

**Test Cases:**
- `TC-155` (integration) — Motivo vacío → 400.
- `TC-156` (integration) — Audit log incluye `impersonated_by_superadmin_id`
      en cada acción hecha durante la sesión.
- `TC-157` (E2E) — Banner visible en todas las páginas durante sesión.

---

### US-059 — Baja de tenant guiada

**Como** Super Admin
**Quiero** desactivar o eliminar un tenant con un flujo seguro
**Para** evitar borrados accidentales.

**Criterios de aceptación:**
- [ ] Dos acciones separadas: **Desactivar** (soft) y **Eliminar permanente**
      (hard).
- [ ] **Desactivar**: confirmación simple con motivo; usuarios no pueden
      login, datos quedan en BD.
- [ ] **Eliminar permanente** (runbook de 4 pasos):
  1. Exportar tenant (obligatorio; descargar ZIP con `tenant_export_*.zip`
     firmado + SHA256).
  2. Confirmación tipeando el slug exacto.
  3. Ventana de "arrepentimiento" 24h (scheduled job, no inmediato).
  4. Ejecución efectiva (delete rows + archivos + cache invalidation).
- [ ] Super Admin puede cancelar en la ventana 24h.
- [ ] Audit log con secuencia `tenant.export → tenant.delete_scheduled →
      tenant.delete_executed`.

**Test Cases:**
- `TC-158` (integration) — Slug mal escrito → 400, no programa delete.
- `TC-159` (integration) — Cancelar dentro de 24h → job cancelado, tenant
      intacto.
- `TC-160` (integration) — Tras ejecutar, queries de ese tenant devuelven 0.
- `TC-161` (E2E) — Export ZIP contiene `tenant.json`, `users.csv`,
      `projects/{folio}/*.json`, etc.

---

### US-060 — Health platform-wide

**Como** Super Admin
**Quiero** ver el estado de la infraestructura y providers
**Para** reaccionar antes que los clientes se quejen.

**Criterios de aceptación:**
- [ ] Página `/superadmin/health` con tarjetas:
  - API (p95 últimos 15min, error rate).
  - Worker (queue depth, jobs por minuto, failed rate).
  - Postgres (conexiones, slow queries, size).
  - Redis (memoria, hit rate).
  - IA providers: **Ollama** (healthy + modelos disponibles + latencia),
    **Gemini** (healthy + rate limit restante), **Claude** (configured?).
  - Storage (volume / S3 usage %).
  - Email (Resend errors últimos 24h).
- [ ] Refresh cada 15s.
- [ ] Detalle expandible con últimas 10 fallas por sistema.
- [ ] Integra con GlitchTip para mostrar top errores recientes.

**Test Cases:**
- `TC-162` (integration) — Tarjeta Ollama muestra `unhealthy` si el endpoint
      tarda > 3s en responder.
- `TC-163` (integration) — Rate limit Gemini consumido → tarjeta amarilla con
      "14/15 RPM usados".

---

### US-061 — Configuración global de plataforma

**Como** Super Admin
**Quiero** ajustar parámetros platform-wide
**Para** gobernar el sistema.

**Criterios de aceptación:**
- [ ] Página `/superadmin/settings` con secciones:
  - **Proveedores IA globales**: keys Gemini y Claude de plataforma, models
    default, rate limits internos.
  - **Defaults tenants nuevos**: locale, currency, plan, ai_mode inicial.
  - **Feature flags globales**: on/off por feature (e.g., `ai_minutes`,
    `ms_project_mpp`).
  - **Límites por plan**: storage, projects, users, ai_tokens/mes.
  - **Maintenance mode**: checkbox — si ON, banner global y endpoints
    read-only.
- [ ] Cambios requieren 2ª confirmación.
- [ ] Audit log con diff antes/después.

**Test Cases:**
- `TC-164` (integration) — Activar maintenance mode → POST de write
      devuelve 503.
- `TC-165` (integration) — Cambiar `defaults.ai_mode` → tenants nuevos nacen
      con ese valor.
- `TC-166` (E2E) — UI de diff muestra "antes" y "después" en cambios.

---

## Notas técnicas

### Modelos involucrados
- `tenants`, `users`, `roles`, `audit_log`, `platform_settings` (nueva tabla),
  `impersonation_sessions` (nueva tabla para US-058).

### Nuevas tablas
```sql
CREATE TABLE platform_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE impersonation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    superadmin_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    reason TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ
);

CREATE TABLE tenant_delete_schedule (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
    scheduled_at TIMESTAMPTZ NOT NULL,
    scheduled_by UUID NOT NULL REFERENCES users(id),
    confirmation_slug TEXT NOT NULL,
    canceled_at TIMESTAMPTZ
);
```

### Endpoints nuevos (complementan los de EP002)
```
GET    /api/v1/superadmin/dashboard              (US-053)
GET    /api/v1/superadmin/tenants                (US-054, extiende EP002)
GET    /api/v1/superadmin/tenants/{id}/detail    (US-055, extiende EP002 con include=)
POST   /api/v1/superadmin/tenants/provision-wizard (US-056 — wrapper del POST de EP002)
GET    /api/v1/superadmin/audit-logs             (US-057)
GET    /api/v1/superadmin/audit-logs/stream      (SSE)
POST   /api/v1/superadmin/tenants/{id}/impersonate (US-058, evoluciona join-as-admin)
POST   /api/v1/superadmin/tenants/{id}/impersonate/end
POST   /api/v1/superadmin/tenants/{id}/schedule-delete (US-059)
POST   /api/v1/superadmin/tenants/{id}/cancel-delete
GET    /api/v1/superadmin/health                 (US-060)
GET    /api/v1/superadmin/settings               (US-061)
PATCH  /api/v1/superadmin/settings
```

### Seguridad adicional
- Ruta `/superadmin` requiere sesión con `is_superadmin=true` y 2FA verificado
  en últimos 30 min (post-MVP si ya tenemos 2FA implementado).
- Rate limit especial: 300 requests/min por superadmin.
- IP allowlist configurable en `platform_settings.key='superadmin.ip_allowlist'`.

---

## Definition of Done

- [ ] Ruta `/superadmin` visible solo para super admins (middleware + API guard).
- [ ] 9 US completas con UI + API + tests.
- [ ] TC-MT-005 y TC-MT-006 siguen verdes (aislamiento multi-tenant preservado
      incluso en ventana super admin).
- [ ] Runbook "eliminar tenant" documentado con screenshots.
- [ ] Dashboard carga < 1.5s con dataset de 50 tenants y 10k users.
- [ ] Al menos 1 E2E por US-056, US-058, US-059 (los flujos críticos).
