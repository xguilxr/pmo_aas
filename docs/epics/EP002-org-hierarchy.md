# EP002 — Jerarquía de Clientes/Proyectos

| Campo | Valor |
|---|---|
| **ID** | EP002 |
| **Prioridad** | Alta |
| **Dependencias** | EP001 |
| **Módulo** | `organizations`, `programs`, `superadmin.tenants` |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |

## Objetivo de negocio

Modelar la realidad del PMO como una jerarquía clara: **PMO (tenant) → Organización → Programa → Proyecto**. Esto permite agrupar, filtrar, reportar y controlar permisos de manera natural.

## Roles involucrados

- Super Admin (gestiona tenants).
- Administrador y PMO Manager (gestionan organizaciones y programas dentro del tenant).

---

## User Stories

### US-008 — CRUD de organizaciones

**Como** Administrador
**Quiero** gestionar organizaciones dentro de mi tenant
**Para** reflejar la estructura corporativa del cliente.

**Criterios de aceptación:**
- [ ] Campos: `name` (único por tenant), `reason_social`, `industry`, `country`, `contact_email`, `logo_url`, `is_active`.
- [ ] `POST /api/v1/organizations` — crear.
- [ ] `GET /api/v1/organizations?q=&is_active=` — listar con búsqueda y filtro.
- [ ] `PATCH /api/v1/organizations/{id}` — editar.
- [ ] `DELETE /api/v1/organizations/{id}` — soft delete (`is_active=false`).
- [ ] Al soft-deletar, los proyectos asociados NO se borran, quedan inaccesibles para nuevos escritos; lectura con banner "Organización inactiva".
- [ ] Upload de logo: PNG/JPG/SVG/WEBP ≤ 2 MB, guardado en `/data/uploads/tenants/{slug}/organizations/{id}.{ext}`.

**Test Cases:**
- `TC-023` (integration) — Crear org con nombre duplicado → 409.
- `TC-024` (integration) — Soft delete no afecta proyectos existentes (lectura).
- `TC-025` (integration) — Upload logo > 2 MB → 413.
- `TC-026` (E2E) — CRUD completo desde UI admin.

---

### US-009 — CRUD de programas

**Como** PMO Manager
**Quiero** agrupar proyectos bajo programas
**Para** alinear con objetivos estratégicos.

**Criterios de aceptación:**
- [ ] Campos: `name`, `description`, `strategic_alignment`, `organization_id`, `start_date`, `end_date`, `is_active`.
- [ ] Un programa pertenece a exactamente **una** organización.
- [ ] `GET /api/v1/programs?organization_id=&is_active=`.
- [ ] Al asignar programa a proyecto, valida que ambos estén en la misma organización.

**Test Cases:**
- `TC-027` (integration) — Asignar programa de org A a proyecto de org B → 422 `BUSINESS_RULE`.
- `TC-028` (integration) — Listar programas filtrados por org.

---

### US-010 — Jerarquía visual y navegación

**Como** Project Manager
**Quiero** ver breadcrumb PMO > Org > Programa > Proyecto
**Para** orientarme siempre donde estoy.

**Criterios de aceptación:**
- [ ] Breadcrumb visible en todas las pantallas dentro de un proyecto.
- [ ] Cada segmento clickeable navega al nivel correspondiente.
- [ ] Si el proyecto no tiene programa, breadcrumb salta ese nivel.
- [ ] Sidebar izquierdo muestra árbol expandible de Org → Programas → Proyectos de los que el user es miembro.
- [ ] Árbol filtrable por `q` (busca en nombre de cualquier nivel).

**Test Cases:**
- `TC-029` (E2E) — Click en cada segmento del breadcrumb → navega correctamente.
- `TC-030` (E2E) — Sidebar muestra solo los proyectos asignados al user.

---

### US-011 — Provisión de tenant (Super Admin)

**Como** Super Admin
**Quiero** crear un tenant nuevo con un admin inicial
**Para** onboarding rápido de nuevos clientes.

**Criterios de aceptación:**
- [ ] `POST /api/v1/superadmin/provision` — body: `{name, slug, admin_email, admin_password?, admin_full_name}`.
- [ ] Si `admin_password` no se provee, se genera aleatorio (24 chars) y se devuelve **una sola vez** en la response.
- [ ] `slug` único platform-wide, regex `^[a-z0-9-]+$`.
- [ ] Crea: tenant, directorio `/data/uploads/tenants/{slug}/`, roles sistema, usuario admin, asignación `Administrador`.
- [ ] Transacción atómica: si falla algún paso, rollback total.
- [ ] Audita `tenant.provisioned`.

**Test Cases:**
- `TC-031` (integration) — Happy path → 201 con admin_password.
- `TC-032` (integration) — Slug duplicado → 409, rollback completo.
- `TC-033` (integration) — Slug inválido (`"Foo Bar"`) → 400.
- `TC-034` (E2E) — UI superadmin → provisiona tenant → login con admin temp funciona.

---

### US-012 — Listar y drill-down de tenants

**Como** Super Admin
**Quiero** ver tenants con sus métricas
**Para** monitorear la plataforma.

**Criterios de aceptación:**
- [ ] `GET /api/v1/superadmin/tenants?include_inactive=false` — lista con `user_count`, `project_count`.
- [ ] `GET /api/v1/superadmin/tenants/{id}/detail` — incluye programas, proyectos, usuarios, requests poblados.
- [ ] Sin N+1 queries (usar `selectinload` / `joinedload`).
- [ ] Tenant inexistente → 404; non-superadmin → 403.

**Test Cases:**
- `TC-035` (integration) — Detail devuelve objetos poblados correctamente.
- `TC-036` (integration) — Queries ejecutadas ≤ 6 (verificado con `pytest-sqlcounter`).

---

### US-013 — Soft / Hard delete de tenant

**Como** Super Admin
**Quiero** desactivar y (con confirmación) eliminar permanentemente un tenant
**Para** cumplir con terminación de contratos.

**Criterios de aceptación:**
- [ ] `DELETE /api/v1/superadmin/tenants/{id}` — soft delete, `is_active=false`, usuarios no pueden login.
- [ ] `DELETE /api/v1/superadmin/tenants/{id}/permanent?confirm_slug={slug}` — borra todo (rows + archivos) solo si `confirm_slug` coincide exacto.
- [ ] Misconfirmación → 400.
- [ ] Audita ambas acciones platform-wide.
- [ ] Hard delete no reversible; runbook obliga a exportar antes.

**Test Cases:**
- `TC-037` (integration) — Soft delete: login imposible, lectura readonly vía superadmin.
- `TC-038` (integration) — Hard delete con slug mal → 400.
- `TC-039` (integration) — Hard delete ok → queries a tablas del tenant devuelven 0.

---

### US-014 — "Actuar como admin" en un tenant

**Como** Super Admin
**Quiero** asumir rol admin en cualquier tenant
**Para** dar soporte sin pedir credenciales al cliente.

**Criterios de aceptación:**
- [ ] `POST /api/v1/superadmin/tenants/{id}/join-as-admin`.
- [ ] Asigna rol "Administrador" en ese tenant (sin duplicar si ya lo tiene).
- [ ] Setea `active_tenant_id = {id}` en el nuevo access token.
- [ ] Frontend almacena `pmo_tenant_id` en localStorage para envío automático de `X-Tenant-ID`.
- [ ] Audita `superadmin.join_as_admin`.

**Test Cases:**
- `TC-040` (integration) — Tras join, GET `/projects` lista proyectos del tenant.
- `TC-041` (E2E) — UI: botón "Ingresar como admin" en tenant detail.

---

## Notas técnicas

### Modelos involucrados
- `tenants`, `organizations`, `programs`, `users`, `user_roles`, `roles`, `audit_log`.

### Endpoints resumidos
```
GET    /api/v1/organizations
POST   /api/v1/organizations
PATCH  /api/v1/organizations/{id}
DELETE /api/v1/organizations/{id}
POST   /api/v1/organizations/{id}/logo

GET    /api/v1/programs
POST   /api/v1/programs
PATCH  /api/v1/programs/{id}
DELETE /api/v1/programs/{id}

GET    /api/v1/superadmin/tenants
POST   /api/v1/superadmin/provision
GET    /api/v1/superadmin/tenants/{id}
GET    /api/v1/superadmin/tenants/{id}/detail
PATCH  /api/v1/superadmin/tenants/{id}
DELETE /api/v1/superadmin/tenants/{id}
DELETE /api/v1/superadmin/tenants/{id}/permanent
POST   /api/v1/superadmin/tenants/{id}/join-as-admin
POST   /api/v1/superadmin/tenants/{id}/logo
```

---

## Definition of Done

- [ ] Todas las US cubiertas por tests (unit + integration + al menos 1 E2E por flujo core).
- [ ] Jerarquía 4 niveles navegable desde el frontend con breadcrumb consistente.
- [ ] Super Admin tools funcionales desde UI y API.
- [ ] TC-MT-001 (isolation tenant↔tenant) verde.
- [ ] Runbook "eliminar tenant permanentemente" documentado.
- [ ] UI admin: tablas de tenants y organizaciones con búsqueda y filtros.
