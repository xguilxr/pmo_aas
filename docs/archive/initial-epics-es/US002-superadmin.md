---
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# US002 — Super Admin (quick-onboarding de tenants)

Épica origen: [EP002 — Jerarquía clientes](../../epics/EP002-jerarquia-clientes.md)

> **Framing crítico**: el panel `/superadmin` **no** es un admin genérico.
> Es la herramienta del operador de la plataforma para montar tenants nuevos
> listos para usar "straight away". Cualquier fricción en este flujo bloquea
> el onboarding → severidad **C**.

## US002-A — Lista de tenants

**Como** super admin
**quiero** ver todos los tenants (activos e inactivos)
**para** monitorear la plataforma.

### Criterios de aceptación
- GET `/superadmin/tenants` → lista con `user_count` + `project_count`.
- `?include_inactive=false` (default) filtra los soft-deleted / is_active=false.
- `?include_inactive=true` los incluye.

**Test:** `TC-010`

## US002-B — Detalle de tenant (drill-down)

**Como** super admin
**quiero** ver programas, proyectos, usuarios y requests de un tenant
**para** entender su estado sin cambiar de sesión.

### Criterios de aceptación
- GET `/superadmin/tenants/{id}/detail` → 200 con todas las listas populadas.
- `programs` es `list[dict]` — no puede ser ORM raw (regresión 2026-04-17).
- `projects` incluye `program_name` resuelto sin N+1.
- `users` incluye roles desde `selectinload`.
- Counts coinciden con las queries independientes.
- Tenant inexistente → 404.
- Non-superadmin → 403.

**Test:** `TC-011`

## US002-C — Provisionar tenant nuevo (happy path onboarding)

**Como** super admin
**quiero** crear un tenant + admin inicial en un solo paso
**para** que el cliente reciba credenciales y empiece a usar el sistema.

### Criterios de aceptación
- POST `/superadmin/provision` con nombre+slug → 201 con `admin_password` en claro.
- El admin creado tiene rol `"Administrador"` y pertenece SOLO al tenant nuevo.
- Se crea el directorio `backend/static/tenants/{slug}/` con `.gitkeep`.
- Password autogenerado es `token_urlsafe(12)` si no se provee.
- Slug duplicado → 400 sin dejar el tenant huérfano (rollback completo).
- Username/email duplicado → 400, rollback del tenant también.

**Test:** `TC-012`

## US002-D — Soft delete vs hard delete

**Como** super admin
**quiero** dos modos de borrado: soft (reversible) y hard (test tenants).

### Criterios de aceptación
- DELETE `/superadmin/tenants/{id}` → 204, `is_active=false`, `deleted_at=now()`.
  El tenant deja de aparecer en `/superadmin/tenants` (sin `?include_inactive`).
- DELETE `/superadmin/tenants/{id}/permanent?confirm_slug=X` →
  204 si el slug coincide; **borra** proyectos, programas, requests, resources,
  user_organizations, usuarios huérfanos, y el dir de assets.
- Slug de confirmación no coincide → 400.

**Test:** `TC-013`

## US002-E — Subir logo del tenant

**Como** super admin
**quiero** subir un logo para el tenant
**para** personalizar branding.

### Criterios de aceptación
- POST `/superadmin/tenants/{id}/logo` con PNG/JPG/SVG/WEBP ≤ 2MB → 200.
- El archivo queda en `backend/static/tenants/{slug}/logo.{ext}`.
- Variantes previas de logo se borran (solo queda uno).
- `org.logo_url = "/static/tenants/{slug}/logo.{ext}"`.
- Tipo no soportado → 400.
- Tamaño > 2MB → 400.

**Test:** `TC-014`

## US002-F — Auditoría de logins platform-wide

**Como** super admin
**quiero** ver todos los intentos de login de la plataforma
**para** detectar incidentes de seguridad.

### Criterios de aceptación
- GET `/superadmin/login-events` → lista con
  `{timestamp, user_id, username, action, organization_name, ip_address, details}`.
- Solo devuelve filas donde `module='auth'` y `organization_id IS NULL`
  (una fila por login, no una por org).
- Paginación vía `?offset=N&limit=M` (max 500).
- Non-superadmin → 403.

**Test:** `TC-015`

## US002-G — Actualización de tenant

**Como** super admin
**quiero** editar datos del tenant sin perder sus datos
**para** corregir info de contacto, colores, dominio.

### Criterios de aceptación
- PATCH `/superadmin/tenants/{id}` con campos parciales → 200.
- Cambiar `slug` renombra el dir de assets (crea el nuevo si no existe).
- Slug/name duplicado → 400.
- Cache de tenants se invalida (`invalidate_tenant_cache()`).

**Test:** `TC-016` (pendiente)

## Multi-tenant safety (transversal)

Cualquier superadmin endpoint **no debe** requerir `get_current_tenant` —
solo `get_superadmin_user`. Ver TC-011 que explícitamente verifica que
`/superadmin/tenants/{id}/detail` no dispara "Super admin debe especificar X-Tenant-ID".
