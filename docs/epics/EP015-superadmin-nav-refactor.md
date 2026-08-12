---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# EP015 — Refactor de navegación del SuperAdmin

| Campo | Valor |
|---|---|
| **ID** | EP015 |
| **Prioridad** | Alta — bloque 11 del sprint |
| **Dependencias** | EP010 (SuperAdmin panel) completo |
| **Módulo** | `web.nav`, `superadmin`, `api.superadmin` |
| **Estado** | Entregada (v1.1) — bloque original DONE (2026-05-23); ver índice |
| **Versión objetivo** | v1.1 |
| **Issue origen** | [#19 — SuperAdmin barra de navegación](https://github.com/xguilxr/pmo_aas/issues/19) |

## Objetivo de negocio

Hoy, cuando un super admin inicia sesión, el sidebar muestra las entradas de la experiencia de tenant (Tablero, Solicitudes, Organizaciones, Admin), que no le sirven. El super admin **no usa esas páginas**: opera la plataforma, no ejecuta PM.

Esta epic deja al super admin con **exactamente 4 ítems** en su sidebar, en este orden:

```
1. Visión General        (Health de plataforma al top)
2. Tenants
3. Usuarios              (nueva página cross-tenant)
4. Logs platform
```

Toda otra entrada del sidebar queda oculta para super admins.

## DEC a registrar en DECISIONS.md al cierre del bloque

- **DEC-020** — El sidebar del super admin es **exclusivo**: no muestra TOP_NAV (Tablero, Solicitudes) ni OrgTreeNav ni ADMIN_NAV. El super admin entra a un tenant vía "Join as admin" (US-058) si necesita operar ahí.
- **DEC-021** — La página `/superadmin` ("Visión General") renderiza Health de la plataforma como primera sección (sobre KPIs / Tenants / Actividad). Antes de US-026 estaban en rutas separadas; ahora Health va arriba por criticidad operativa.
- **DEC-022** — `/superadmin/users` es cross-tenant y permite a super admin modificar: activar/desactivar, cambiar rol (si el rol existe en el tenant destino), forzar reset de password, impersonar. Cada acción se audita con `scope=platform`.

---

## # DONE — US-041 — Sidebar super admin aislado

**Como** super admin
**Quiero** que mi sidebar muestre SÓLO entradas de super admin (sin Tablero / Solicitudes / Organizaciones / Admin)
**Para** no mezclar operación de plataforma con operación de un tenant.

**Criterios de aceptación:**
- [x] Cuando `user.is_superadmin === true`, el sidebar renderiza **sólo** SUPERADMIN_NAV con 4 ítems, en este orden:
  1. `Visión General` → `/superadmin`
  2. `Tenants` → `/superadmin/tenants`
  3. `Usuarios` → `/superadmin/users` (entrada nueva; página que llega con US-042, hasta entonces responderá 404)
  4. `Logs platform` → `/superadmin/logs`
- [x] TOP_NAV (Tablero, Solicitudes) oculto para super admin.
- [x] `<OrgTreeNav />` oculto para super admin (vía `adminVisible`).
- [x] ADMIN_NAV oculto para super admin (vía `adminVisible`).
- [x] Link del brand en el sidebar apunta a `/superadmin` para super admin (antes `/dashboard` para todos).
- [x] Header visual duplicado "Super admin" eliminado — ya no aplica dualidad.

**Commit:** `feat(web): US-041 — sidebar super admin aislado (4 ítems raíz)`.

---

## # DONE — US-042 — Página `/superadmin/users` cross-tenant

**Como** super admin
**Quiero** listar y editar usuarios de **todos** los tenants en una sola pantalla
**Para** dar soporte sin entrar a cada tenant vía impersonate.

**Criterios de aceptación:**
- [ ] Endpoint `GET /api/v1/superadmin/users` con filtros `q` (fuzzy por nombre/email/username), `tenant_id`, `is_active`, `is_superadmin`, `role_name`, `page`, `limit`. Paginado.
- [ ] Response incluye: `id`, `username`, `email`, `full_name`, `is_active`, `is_superadmin`, `tenant_id`, `tenant_slug`, `tenant_name`, `roles[]`, `last_login_at` (si se registra).
- [ ] Endpoint `PATCH /api/v1/superadmin/users/{id}` permite a super admin:
  - `is_active` toggle.
  - `full_name`, `email` (validado), `username` update.
  - Sin tocar password directamente desde aquí (reset se gestiona en endpoint separado si se requiere — follow-up).
  - 403 si el usuario objetivo es otro super admin (protección mutua salvo auto-edición).
- [ ] Endpoint `POST /api/v1/superadmin/users/{id}/toggle-active` con motivo obligatorio.
- [ ] Cada acción auditada con `scope=platform` (`user.superadmin_update`, `user.superadmin_toggle_active`).
- [ ] Frontend `/superadmin/users`:
  - Tabla con columnas: Usuario (name + username), Email, Tenant (slug clickable al drill-down), Roles, Estado, Acciones.
  - Búsqueda (`q` con debounce 300 ms).
  - Filtros: tenant select, rol, estado.
  - Badge "Super admin" para usuarios con ese flag.
  - Acción inline "Editar" (abre drawer / modal con form).
  - Acción inline "Desactivar" con confirmación + motivo.

**Tests (8/8 verdes):**
- `test_usnew042_list_requires_superadmin` — 403 a no-superadmin.
- `test_usnew042_list_cross_tenant` — lista usuarios de todos los tenants.
- `test_usnew042_filter_by_tenant` — filtro por `tenant_id`.
- `test_usnew042_search_q_matches_email_username` — fuzzy search.
- `test_usnew042_patch_user` — update ok.
- `test_usnew042_patch_other_superadmin_forbidden` — 403 a otro super admin.
- `test_usnew042_toggle_active_audits` — 2 toggles → 2 rows de audit.
- `test_usnew042_cannot_deactivate_self` — auto-desactivación → 422.

**Implementación:**
- `GET /api/v1/superadmin/users` con filtros `q`, `tenant_id`, `is_active`, `is_superadmin`, `role_name`, paginación. Resuelve `tenant_{slug,name}` y roles en un mini JOIN para evitar N+1.
- `PATCH /api/v1/superadmin/users/{id}` — `full_name`, `email`, `username`, `is_active`. 403 si target es otro super admin.
- `POST /api/v1/superadmin/users/{id}/toggle-active` con `reason` obligatorio. Auditado con `scope=platform`.
- Frontend `/superadmin/users`: tabla con search (debounce 300 ms), filtro activos/inactivos, modales para editar y toggle con motivo.

**Commit:** `feat(api,web): US-042 — /superadmin/users cross-tenant`.

---

## # DONE — US-043 — Visión General con Health al top

**Como** super admin
**Quiero** ver el Health de la plataforma **inmediatamente** al abrir `/superadmin`, antes que KPIs y tenants
**Para** detectar problemas de infra antes de revisar métricas comerciales.

**Criterios de aceptación:**
- [ ] En `/superadmin`, la sección de Health (`<SuperadminHealthSection />`, existente de US-026) se mueve al **primer bloque después del breadcrumb/título**.
- [ ] Orden final de secciones: `Health → KPIs → Top tenants → Actividad reciente`.
- [ ] No se rompe el auto-refresh de Health cada 15 s.
- [ ] Breadcrumb / título conservan el copy actual ("Visión general").

**Test Cases:**
- `TC-NEW-043-1` (E2E) — `/superadmin` renderiza Health antes que KPIs.
- `TC-NEW-043-2` (regresión) — Health sigue refrescándose cada 15 s.

**Commit:** `feat(web): US-043 — health al top en visión general del superadmin`.

---

## Endpoints nuevos

```
GET    /api/v1/superadmin/users               (US-042)
PATCH  /api/v1/superadmin/users/{id}          (US-042)
POST   /api/v1/superadmin/users/{id}/toggle-active
```

## Cambios de schema

Ninguno. Tablas `users`, `tenants`, `user_roles` ya tienen todo lo necesario.

---

## Definition of Done

- [ ] Super admin sólo ve 4 ítems en sidebar (US-041).
- [ ] Página `/superadmin/users` funcional con filtros, edición y toggle activo (US-042).
- [ ] Health al top de Visión General (US-043).
- [ ] Regresión: admin regular sigue viendo TOP_NAV + OrgTree + ADMIN_NAV sin cambios.
- [ ] DEC-020, DEC-021, DEC-022 registrados en DECISIONS.md.
