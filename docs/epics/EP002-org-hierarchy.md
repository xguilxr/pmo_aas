# EP002 — Jerarquía de Clientes/Proyectos

| Campo | Valor |
|---|---|
| **ID** | EP002 |
| **Prioridad** | Alta (BLOQUEANTE para EP003-EP007) |
| **Dependencias** | EP001 |
| **Módulo** | `organizations`, `business_units`, `departments`, `programs`, `superadmin.tenants` |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |
| **Última actualización** | 2026-04-20 — jerarquía extendida BU + Depto |

## Objetivo de negocio

Modelar la realidad del PMO con jerarquía completa:
**PMO (tenant) → Organización → Unidad de Negocio → Departamento → Programa → Proyecto**

La jerarquía es configurable por Admin del tenant o Senior PMO. BU y Departamento son opcionales (tenant puede operar con Org → Programa → Proyecto directamente).

## Roles involucrados

- Super Admin (gestiona tenants).
- Administrador y PMO Manager Senior (gestionan organizaciones, BU, departamentos y programas).

---

## User Stories existentes

### US-008 — CRUD de organizaciones
*(sin cambios respecto a v1)*

**Como** Administrador
**Quiero** gestionar organizaciones dentro de mi tenant
**Para** reflejar la estructura corporativa del cliente.

**Criterios de aceptación:**
- [ ] Campos: `name` (único por tenant), `reason_social`, `industry`, `country`, `contact_email`, `logo_url`, `is_active`.
- [ ] `POST /api/v1/organizations` — crear.
- [ ] `GET /api/v1/organizations?q=&is_active=` — listar con búsqueda y filtro.
- [ ] `PATCH /api/v1/organizations/{id}` — editar.
- [ ] `DELETE /api/v1/organizations/{id}` — soft delete (`is_active=false`).
- [ ] Al soft-deletar, los proyectos asociados NO se borran; lectura con banner "Organización inactiva".
- [ ] Upload de logo: PNG/JPG/SVG/WEBP ≤ 2 MB.

**Test Cases:**
- `TC-023` (integration) — Crear org con nombre duplicado → 409.
- `TC-024` (integration) — Soft delete no afecta proyectos existentes.
- `TC-025` (integration) — Upload logo > 2 MB → 413.
- `TC-026` (E2E) — CRUD completo desde UI admin.

---

### US-009 — CRUD de programas
*(actualizado: programa puede colgar de departamento)*

**Como** PMO Manager
**Quiero** agrupar proyectos bajo programas
**Para** alinear con objetivos estratégicos.

**Criterios de aceptación:**
- [ ] Campos: `name`, `description`, `strategic_alignment`, `organization_id`, `department_id` (opcional), `start_date`, `end_date`, `is_active`.
- [ ] Un programa pertenece a una organización; opcionalmente a un departamento.
- [ ] `GET /api/v1/programs?organization_id=&department_id=&is_active=`.
- [ ] Al asignar programa a proyecto, valida que ambos estén en la misma organización.

**Test Cases:**
- `TC-027` (integration) — Asignar programa de org A a proyecto de org B → 422.
- `TC-028` (integration) — Listar programas filtrados por org o por departamento.

---

### US-010 — Jerarquía visual y navegación (breadcrumb)
*(actualizado: incluye BU y Depto)*

**Como** Project Manager
**Quiero** ver breadcrumb PMO > Org > [BU >] [Depto >] Programa > Proyecto
**Para** orientarme siempre donde estoy.

**Criterios de aceptación:**
- [ ] Breadcrumb visible en todas las pantallas dentro de un proyecto.
- [ ] Cada segmento clickeable navega al nivel correspondiente.
- [ ] Si el proyecto no tiene BU/Depto/Programa, breadcrumb omite esos niveles.
- [ ] Sidebar muestra árbol expandible de Org → BU → Depto → Programas → Proyectos.
- [ ] Árbol filtrable por `q`.

**Test Cases:**
- `TC-029` (E2E) — Breadcrumb con 4 niveles navegable.
- `TC-030` (E2E) — Sidebar muestra solo proyectos asignados al user.

---

### US-011 — Provisión de tenant (Super Admin) — sin cambios
### US-012 — Listar y drill-down de tenants — sin cambios
### US-013 — Soft / Hard delete de tenant — sin cambios
### US-014 — "Actuar como admin" en un tenant — sin cambios

*(Ver versión original para criterios completos)*

---

## # PENDING — User Stories nuevas

### US-002 — Migración BD: tablas business_units y departments ✅ DONE

Implementada en la migración Alembic
[`20260420_0009_business_units_departments.py`](../../apps/api/alembic/versions/20260420_0009_business_units_departments.py).
Ver detalle del shape en
[`DB-CHANGES.md` §EP002](./DB-CHANGES.md#ep002--jerarquía-org).

**Resultado:**
- `business_units(id, tenant_id, organization_id, name, …)` +
  `departments(id, tenant_id, business_unit_id, name, …)`.
- FKs nullable en `programs.department_id`, `projects.department_id`,
  `projects.business_unit_id`,
  `project_requests.{business_unit_id, department_id}`.
- Índices parciales por `deleted_at IS NULL`.
- Aislamiento multi-tenant por filtro `tenant_id` en el ORM + helpers
  de repositorio (no por RLS — ver DEC-003).

**Test Cases cubiertos:**
- `TC-NEW-001` (unit) — Migración up/down.
- `TC-NEW-002` (integration) — Filtro `tenant_id` impide cross-tenant.

---

### US-003 — CRUD Business Units (API)

**Como** Administrador / Senior PMO
**Quiero** crear, editar y desactivar unidades de negocio dentro de una organización
**Para** estructurar la jerarquía corporativa.

**Criterios de aceptación:**
- [ ] `POST /api/v1/organizations/{org_id}/business-units` — crear.
- [ ] `GET /api/v1/organizations/{org_id}/business-units?q=&is_active=` — listar.
- [ ] `PATCH /api/v1/business-units/{id}` — editar.
- [ ] `DELETE /api/v1/business-units/{id}` — soft delete.
- [ ] Al soft-deletar BU con departamentos activos → advertencia, requiere `force=true`.
- [ ] Nombre único por `(tenant_id, organization_id)`.
- [ ] Permiso requerido: `admin.organizations:update`.

**Test Cases:**
- `TC-NEW-003` (integration) — Crear BU nombre duplicado en misma org → 409.
- `TC-NEW-004` (integration) — Soft delete BU con deptos activos sin force → 422 con lista de deptos.
- `TC-NEW-005` (integration) — Listar BUs filtradas por org.

---

### US-004 — CRUD Departments (API)

**Como** Administrador / Senior PMO
**Quiero** crear, editar y desactivar departamentos dentro de una unidad de negocio
**Para** completar la jerarquía.

**Criterios de aceptación:**
- [ ] `POST /api/v1/business-units/{bu_id}/departments` — crear.
- [ ] `GET /api/v1/business-units/{bu_id}/departments?q=&is_active=` — listar.
- [ ] `PATCH /api/v1/departments/{id}` — editar.
- [ ] `DELETE /api/v1/departments/{id}` — soft delete.
- [ ] Al soft-deletar Depto con programas/proyectos activos → advertencia.
- [ ] Nombre único por `(tenant_id, business_unit_id)`.

**Test Cases:**
- `TC-NEW-006` (integration) — Crear Depto nombre duplicado en misma BU → 409.
- `TC-NEW-007` (integration) — Soft delete con programas activos → 422.

---

### US-005 — Sidebar con organizaciones del tenant para nav rápida

**Como** usuario autenticado
**Quiero** ver las organizaciones del tenant en el sidebar con árbol expandible
**Para** navegar rápidamente a programas y proyectos.

**Criterios de aceptación:**
- [ ] Sidebar expande sección "Organizaciones" con lista de orgs del tenant.
- [ ] Cada org expandible muestra sus BUs → Deptos → Programas → Proyectos.
- [ ] Click en org → navega a detalle de organización.
- [ ] Click en programa → navega a listado de proyectos del programa.
- [ ] Respeta permisos: user solo ve orgs/proyectos donde tiene acceso.
- [ ] Árbol lazy-load: no carga BU/Depto/Programas hasta expandir.
- [ ] Estado expandido persiste en `localStorage` por sesión.

**Test Cases:**
- `TC-NEW-008` (E2E) — Árbol navega hasta proyecto en 3 clicks.
- `TC-NEW-009` (E2E) — PM solo ve orgs donde tiene proyectos asignados.

---

### US-006 — Vista de organizaciones como paneles informativos

**Como** Administrador / PMO Manager
**Quiero** ver cada organización como un panel con métricas
**Para** entender el estado de cada cliente de un vistazo.

**Criterios de aceptación:**
- [ ] Ruta `/organizations` muestra grid de cards por organización.
- [ ] Cada card muestra: logo, nombre, `#BU`, `#Departamentos`, `#Programas`, `#Proyectos activos`, salud del portafolio.
- [ ] Click en card → navega a `/organizations/{id}` con detalle de la org.
- [ ] En el detalle: tabs con Programas, Proyectos, BUs/Deptos, Métricas.
- [ ] Botón "Nueva Organización" visible para Admin/Senior PMO.

**Test Cases:**
- `TC-NEW-010` (integration) — Métricas de card coinciden con queries directas.
- `TC-NEW-011` (E2E) — Grid de cards responsive, navega a detalle.

---

### BUG-001 — Fix 404 en página de Programas

**Como** usuario
**Quiero** que la página de programas cargue correctamente
**Para** poder ver y gestionar programas.

**Criterios de aceptación:**
- [ ] Ruta `/programs` o equivalente no devuelve 404.
- [ ] Listado de programas muestra todos los del tenant/org según permisos.
- [ ] Fix incluye tests para evitar regresión.

---

## Definition of Done (EP002 completo)

- [ ] Jerarquía 6 niveles completa: tenant → org → BU → depto → programa → proyecto.
- [ ] CRUD completo para BU y Departamentos con permisos.
- [ ] Sidebar con árbol navegable.
- [ ] Vista de organizaciones como paneles.
- [ ] Breadcrumb adaptable a jerarquías incompletas.
- [ ] RLS en tablas nuevas verificado (TC-MT-001 extendido).
- [ ] Bug 404 programas resuelto.
- [ ] Migración BD documentada y reversible.
