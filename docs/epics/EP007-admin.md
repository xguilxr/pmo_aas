---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# EP007 — Panel de Administración

| Campo | Valor |
|---|---|
| **ID** | EP007 |
| **Prioridad** | Alta |
| **Dependencias** | EP001, EP002 |
| **Módulo** | `admin.*` |
| **Estado** | MVP |

## Objetivo de negocio

Un panel único centraliza la gestión de usuarios, roles, organizaciones y proyectos del tenant, con vistas optimizadas para operaciones rápidas (crear, editar, desactivar, resetear, etc.).

---

## US-037 — Panel de administración de usuarios

**Como** Administrador
**Quiero** una tabla completa de usuarios con acciones rápidas
**Para** onboardear y gestionar el equipo.

**Criterios de aceptación:**
- [ ] Columnas: nombre, username, email, roles (chips), estado (activo/bloqueado), último login, acciones.
- [ ] Acciones inline: editar, activar/desactivar, resetear password, desbloquear, impersonate (solo superadmin).
- [ ] Búsqueda fuzzy + filtros (rol, estado).
- [ ] Export CSV/XLSX con filtros aplicados.
- [ ] No se permite desactivar la cuenta propia.
- [ ] Bulk actions: asignar rol a varios seleccionados, desactivar masivo (con confirmación).

**Test Cases:**
- `TC-098` (integration) — Desactivar cuenta propia → 422 `BUSINESS_RULE`.
- `TC-099` (integration) — Bulk asignar rol a 10 users → todos afectados, audit log con 10 entradas.
- `TC-100` (E2E) — Export CSV descarga con headers correctos.

---

## US-038 — Panel de administración de roles

**Como** Administrador
**Quiero** definir roles con matriz de permisos (checkboxes por módulo × acción)
**Para** controlar acceso granular.

**Criterios de aceptación:**
- [ ] Tabla de roles con `name`, `description`, `user_count`, acciones.
- [ ] Editor de rol: matriz visual 12×8 (módulos × acciones) con checkboxes.
- [ ] Toggle "seleccionar todos" por fila y por columna.
- [ ] Preview "Este cambio afecta a N usuarios: …" antes de guardar.
- [ ] Roles sistema (`is_system=true`) muestran badge "Sistema" y deshabilitan borrar.
- [ ] Duplicar rol (as template).

**Test Cases:**
- `TC-101` (E2E) — Toggle "todos" marca fila completa.
- `TC-102` (E2E) — Preview muestra lista de afectados.
- `TC-103` (integration) — Duplicar rol → copia `permissions` pero `is_system=false`.

---

## US-039 — Panel de administración de organizaciones

**Como** Administrador
**Quiero** gestionar organizaciones desde un panel con métricas
**Para** ver impacto.

**Criterios de aceptación:**
- [ ] Cards con métricas por org: `project_count_active`, `budget_total`, `user_count`.
- [ ] Link rápido a "Ver proyectos de esta org".
- [ ] Upload logo inline con preview + crop 1:1.
- [ ] Soft delete con confirmación y advertencia de proyectos afectados.

**Test Cases:**
- `TC-104` (integration) — Métricas por org coinciden con queries directas.
- `TC-105` (E2E) — Upload logo con crop → guardado correcto.

---

## US-040 — Panel del Tenant (supervisión global de proyectos)

**Como** Administrador
**Quiero** ver **todos** los proyectos del tenant sin filtro de miembro
**Para** supervisión global.

**Criterios de aceptación:**
- [ ] Ruta `/admin/supervision` (label en sidebar: **"Panel del Tenant"**, bajo el dropdown _Admin_).
- [ ] Endpoint especial `GET /api/v1/admin/projects` — bypass filtro `is_member`.
- [ ] Solo accesible con permiso `admin.projects:read`.
- [ ] Métricas globales: total, por estado, por organización, desviaciones.
- [ ] Acciones: cambiar PM, forzar cierre (con comentario).

**Test Cases:**
- `TC-106` (integration) — User sin `admin.projects:read` → 403.
- `TC-107` (integration) — Admin ve todos los proyectos incluidos los de orgs inactivas.

---

## US-041 — Configuración del tenant

**Como** Administrador
**Quiero** configurar preferencias del tenant
**Para** personalizar.

**Criterios de aceptación:**
- [ ] Sección "Configuración" con:
  - Idioma default (`es-MX` / `en-US`).
  - Moneda default (`MXN`, `USD`, `EUR`).
  - Formato de fecha.
  - Timezone.
  - Logo corporativo + color primario (para PDFs exportados).
  - Modo IA (`platform` / `byo` / `disabled`). El modo se configura en
    `/admin/ai` (no en este panel). Ver `EP008-ai.md`. El catálogo BYO
    incluye OpenAI / Claude / Gemini / Perplexity / Azure Copilot M365 /
    Custom / Groq. Ollama fue eliminado (BUG-053).
- [ ] Se guarda en `tenants.settings` (JSONB).
- [ ] Cambio de idioma default no afecta preferencia individual de users.

**Test Cases:**
- `TC-108` (integration) — Actualizar `settings.locale` → próximo login muestra UI en ese idioma.
- `TC-109` (integration) — Color primario se refleja en PDF exportado.

---

## US-042 — Logs de auditoría (visible para Admin del tenant)

**Como** Administrador
**Quiero** consultar quién hizo qué cuándo
**Para** forensía y compliance.

**Criterios de aceptación:**
- [ ] `GET /api/v1/admin/audit-logs?action=&user_id=&entity_type=&date_from=&date_to=&cursor=`.
- [ ] Solo ve eventos del **tenant propio** (filtro `tenant_id` en la query; no hay RLS Postgres, ver `architecture/security-multitenant.md`).
- [ ] Incluye `action`, `module`, `entity_type`, `entity_id`, `details`, `ip_address`, `occurred_at`, `user_display`.
- [ ] Export CSV para período.

**Test Cases:**
- `TC-110` (integration) — Admin A no ve eventos de tenant B (TC-MT-006).
- `TC-111` (integration) — Filtros combinados devuelven exacto.

---

## US-043 — Navegación jerárquica del sidebar (SUPERSEDED)

> ⚠️ **Esta US está superseded por US-138** (sidebar capability-based
> con TOP_NAV / ADMIN_NAV / SUPERADMIN_NAV separados; ver
> `components/app-shell.tsx`). El árbol "Organizaciones → Solicitudes /
> Programas / Proyectos → Módulos" se reemplazó por:
>
> - `OrgTreeNav` (drill-down vivo orgs → programas → proyectos).
> - Tabs dentro de `/pmo/projects/[id]/*` (US-035) para los módulos.
> - Items planos en TOP_NAV para Requests, Projects, RAID, Cambios, etc.
> - Las rutas `/admin/projects`, `/admin/programs`, `/admin/raid`, etc.
>   ahora son redirects 301 a `/pmo/*` (US-075 / DEC-022).
> - `/admin/settings` y `/admin/supervision` → redirects a
>   `/admin/tenant?tab={config|stats}` (US-036).
> - `/admin/roles` → redirect a `/admin/permissions`.
>
> El árbol descrito abajo refleja el diseño original. Queda como
> contexto histórico.

**Como** usuario autenticado (cualquier rol)
**Quiero** un sidebar organizado en grupos colapsables con dropdowns anidados
**Para** escanear rápido las áreas de la app y reducir la fricción de navegación.

**Criterios de aceptación:**
- [ ] El sidebar expone **tres grupos top-level** en este orden:
  1. **Tablero** — link directo a `/dashboard`.
  2. **Organizaciones** (dropdown; el label navega a `/admin/organizations`):
     - Solicitudes → `/admin/requests`.
     - Programas → `/admin/programs`.
     - Proyectos (sub-dropdown; label navega a `/admin/projects`):
       - **Módulos de Proyectos** (sub-grupo expandible) con: Riesgos, AIDs, Cambios, Documentos, Lecciones, Minutas, Tareas, Gantt, Minuta IA, Reporte IA.
  3. **Admin** (dropdown):
     - **Panel del Tenant** → `/admin/supervision` (reemplaza el label "Supervisión").
     - Usuarios → `/admin/users`.
     - Roles → `/admin/roles`.
     - Auditoría → `/admin/audit-logs`.
     - Configuración → `/admin/settings`.
- [ ] Los grupos con `href` + `children` actúan como **link + toggle**: clic en el label navega, clic en el chevron (lado derecho) expande/colapsa.
- [ ] **Auto-expand**: al montar el shell o al cambiar `pathname`, las ramas que contienen la ruta activa se expanden automáticamente.
- [ ] Los ítems bajo _Módulos de Proyectos_ resuelven su `href` contra el proyecto en curso cuando la URL calza `/admin/projects/:id/...`; en caso contrario caen al listado `/admin/projects`.
- [ ] El estado activo usa pill de fondo (`--chrome-active`) sin border; cada nivel de anidación agrega `0.75rem` de indent.
- [ ] La sección **Super admin** (Visión general, Tenants, Logs platform, Health) sólo se renderiza si `user.is_superadmin === true` y queda por fuera del árbol principal.
- [ ] Los chevrones tienen `aria-expanded` y labels `aria-label="Expandir/Colapsar <grupo>"`.

**Test Cases:**
- `TC-112` (e2e) — Al entrar a `/admin/users`, el grupo _Admin_ aparece expandido y _Usuarios_ activo; el resto colapsado.
- `TC-113` (e2e) — Al entrar a `/admin/projects/:id/risks`, quedan abiertos _Organizaciones → Proyectos → Módulos de Proyectos_ con _Riesgos_ activo.
- `TC-114` (e2e) — Clic en el label "Organizaciones" navega a `/admin/organizations` **y** expande el grupo; clic en el chevron sólo expande.
- `TC-115` (unit) — `buildNav(pathname)` devuelve hrefs de módulos apuntando al proyecto en curso cuando `pathname` incluye `/admin/projects/:id`.
- `TC-116` (a11y) — Navegación completa con teclado (Tab + Enter sobre chevron) respeta focus ring y `aria-expanded` cambia de estado.

---

## Notas técnicas

- Panel admin es una ruta protegida `/admin` en Next.js con `middleware.ts` que verifica permiso.
- Bulk actions usan endpoints que aceptan arrays, con validación de tamaño máx (100).
- Logs de auditoría usan cursor pagination por performance (tabla grande).

### Endpoints
```
GET    /api/v1/admin/users
POST   /api/v1/admin/users/bulk
POST   /api/v1/admin/users/{id}/impersonate      (superadmin only)

GET    /api/v1/admin/roles
POST   /api/v1/admin/roles
POST   /api/v1/admin/roles/{id}/duplicate
GET    /api/v1/admin/roles/{id}/impact           (preview de afectados)

GET    /api/v1/admin/organizations
GET    /api/v1/admin/projects                    (bypass member filter)

GET    /api/v1/admin/settings
PATCH  /api/v1/admin/settings
POST   /api/v1/admin/settings/logo

GET    /api/v1/admin/audit-logs
GET    /api/v1/admin/audit-logs/export.csv
```

---

## Definition of Done

- [ ] Panel accesible en `/admin` con sidebar de dropdowns anidados (ver US-043): _Admin_ agrupa Panel del Tenant, Usuarios, Roles, Auditoría, Configuración; _Organizaciones_ agrupa Solicitudes, Programas y Proyectos → Módulos.
- [ ] Bulk actions probadas con 100 elementos sin degradar performance.
- [ ] TC-MT-005 (admin A no gestiona B) y TC-MT-006 (logs aislados) verdes.
- [ ] UI elegante con tablas densas estilo macOS Finder (ver design system).

---

## # PENDING — User Stories nuevas

### US-023 — Gestión de Tenant (acciones propuestas)

**Como** Admin / Senior PMO
**Quiero** un panel para ver y editar la información de mi tenant
**Para** mantener identidad y conocer uso sin depender de super admin.

**Criterios de aceptación:**
- [x] `GET /api/v1/admin/tenant` devuelve: id, slug, name, logo_url,
  is_active, plan, settings y stats (active_users, total_users,
  total_organizations, total_projects, storage_bytes).
- [x] `PATCH /api/v1/admin/tenant` permite actualizar `name` y `logo_url`.
  Rechaza nombres < 2 caracteres. Ignora `slug` silenciosamente
  (solo super admin lo cambia).
- [x] Página `/admin/tenant`:
  - Tarjeta con logo, nombre (editable), slug (readonly).
  - Tarjeta de plan actual con link "Contactar soporte".
  - Stats: usuarios activos, organizaciones, proyectos, storage humano.
  - Link a `/admin/settings` para idioma, moneda, timezone, IA.
- [x] Storage calculado sumando `documents.size_bytes` current.
- [x] Entrada "Mi tenant" agregada al nodo Admin del sidebar.

**Test Cases:**
- `test_usnew023_get_tenant_info_with_stats` ✅
- `test_usnew023_patch_tenant_name_and_logo` ✅
- `test_usnew023_patch_ignores_slug` ✅
- `test_usnew023_patch_name_too_short` → 422 ✅

**Estado de integración:** DONE (US-023).

---

### US-024 — Gestión jerarquía org completa (BU + Depto) en Admin

**Criterios de aceptación:**
- [x] En `/admin/organizations/{id}`, debajo del formulario de edición
  de la org, se muestra sección "Jerarquía: unidades de negocio y
  departamentos" con tree expandible.
- [x] Tree Org → BUs → Deptos con acciones inline por fila:
  - "Nuevo departamento" (solo en filas de BU).
  - "Editar" (abre modal de nombre + descripción).
  - "Desactivar" (modal con toggle `force` para cascada).
- [x] Botón "Nueva BU" en el header de la sección.
- [x] Botón "Ver proyectos" en el header de la sección → filtra
  `/admin/projects?organization_id={id}`.
- [x] Deptos se cargan lazy al expandir la BU.
- [x] Reutiliza los endpoints existentes (US-003/004); sin cambios
  de backend.

**Notas:**
- Modal de desactivar muestra el mensaje `BU_HAS_ACTIVE_DEPARTMENTS` o
  `DEPT_HAS_ACTIVE_CHILDREN` cuando aplica, y sugiere el toggle force.

**Estado de integración:** DONE (US-024).
