---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# EP002 — Jerarquía de Clientes/Proyectos

| Campo | Valor |
|---|---|
| **ID** | EP002 |
| **Prioridad** | Alta (BLOQUEANTE para EP003-EP007) |
| **Dependencias** | EP001 |
| **Módulo** | `organizations`, `portfolios`, `programs`, `superadmin.tenants` (`business_units`/`departments`: en retiro, ADR-037) |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |
| **Última actualización** | 2026-08-19 — US-201: la cascada Organización → Portafolio → Programa filtra el tablero y las vistas cross (ADR-037) |

## Objetivo de negocio

El PMO modela su jerarquía completa:
**PMO (tenant) → Organización → Portafolio ⊃ Programa → Proyecto**

El portafolio agrupa por **decisión de inversión** — qué se hace, con qué, y qué
se deja de hacer— y es lo que mira un comité de dirección. El programa agrupa por
**coordinación**: proyectos que comparten un objetivo y se gestionan juntos.

Admin del tenant o Senior PMO configuran la jerarquía. El programa es opcional:
un proyecto puede colgar directo de su portafolio. El portafolio del proyecto
también es opcional —un proyecto recién importado todavía no está clasificado—,
pero no puede contradecir a su programa (ver US-198).

> **Unidad de Negocio y Departamento están en retiro** (ADR-037, 2026-08-19).
> Modelaban el organigrama del cliente, no su cartera, y nunca se usaron en
> producción. Portafolio y Programa los reemplazan directamente, sin mapeo de
> datos. Sus tablas siguen en el esquema hasta W8 y sus endpoints se retiran en
> US-199; las US-002/003/004 de más abajo quedan como registro histórico.

## Roles involucrados

- Super Admin (gestiona tenants).
- Administrador y PMO Manager Senior (gestionan organizaciones, portafolios y programas).

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
*(actualizado 2026-08-19: el programa vive dentro de un portafolio)*

**Como** PMO Manager
**Quiero** agrupar proyectos bajo programas
**Para** alinear con objetivos estratégicos.

**Criterios de aceptación:**
- [ ] Campos: `name`, `description`, `strategic_alignment`, `organization_id`, `portfolio_id` (**obligatorio**), `start_date`, `end_date`, `is_active`.
- [ ] Un programa pertenece a una organización y a **un portafolio de esa misma organización**.
- [ ] Un alta sin portafolio cae en el «Portafolio General» de la organización, que se crea al vuelo (DEC-030). Nadie tiene que inventarse una taxonomía para registrar su primer programa.
- [ ] `GET /api/v1/programs?organization_id=&portfolio_id=&is_active=`.
- [ ] Al asignar programa a proyecto, valida que ambos estén en la misma organización y **autocompleta el portafolio del proyecto** con el del programa (US-198).

**Test Cases:**
- `TC-027` (integration) — Asignar programa de org A a proyecto de org B → 422.
- `TC-028` (integration) — Listar programas filtrados por org o por portafolio.

---

### US-010 — Jerarquía visual y navegación (breadcrumb)
*(actualizado 2026-08-19: la jerarquía es la de ADR-037; BU y Depto salen)*

**Como** Project Manager
**Quiero** ver breadcrumb PMO > Org > [Portafolio >] [Programa >] Proyecto
**Para** orientarme siempre donde estoy.

**Criterios de aceptación:**
- [ ] Breadcrumb visible en todas las pantallas dentro de un proyecto.
- [ ] Cada segmento clickeable navega al nivel correspondiente.
- [ ] Si el proyecto no tiene portafolio ni programa, el breadcrumb omite esos
  niveles. Los dos casos existen y son distintos: un proyecto puede colgar del
  portafolio sin programa, o no estar clasificado todavía.
- [x] Sidebar muestra árbol expandible Org → Portafolio → Programa → Proyecto,
  con los cajones «Sin programa» y «Sin clasificar» (lo cumplió **US-200**).
- [ ] Árbol filtrable por `q`.

**Test Cases:**
- `TC-029` (E2E) — Breadcrumb navegable en todos sus niveles.
- `TC-030` (E2E) — Sidebar muestra solo proyectos asignados al user.

---

### US-011 — Provisión de tenant (Super Admin) — sin cambios
### US-012 — Listar y drill-down de tenants — sin cambios
### US-013 — Soft / Hard delete de tenant — sin cambios
### US-014 — "Actuar como admin" en un tenant — sin cambios

*(Ver versión original para criterios completos)*

---

## # PENDING — User Stories nuevas

### US-002 — Migración BD: tablas business_units y departments ✅ DONE ⚠️ RETIRADA (ADR-037)

> Registro histórico. Las dos tablas quedan sin lectores nuevos tras US-198 y se
> dropean en W8. Lo vigente es US-198, más abajo.

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

### US-003 — CRUD Business Units (API) ⚠️ RETIRADA (ADR-037)

> Se conserva como registro de lo que existió. Los endpoints se retiran en
> US-199 y la tabla se dropea en W8. Lo sustituye US-198 (portafolios).

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

### US-004 — CRUD Departments (API) ⚠️ RETIRADA (ADR-037)

> Igual que US-003: registro histórico. La coordinación de proyectos la hace el
> programa; el agrupador de inversión, el portafolio.

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
- [x] Cada org expandible muestra sus Portafolios → Programas → Proyectos
  (**US-200**), más los proyectos que cuelgan del portafolio sin programa.
- [ ] Click en org → navega a detalle de organización.
- [ ] Click en programa → navega a listado de proyectos del programa.
- [ ] Respeta permisos: user solo ve orgs/proyectos donde tiene acceso.
- [x] Árbol lazy-load: cada nivel se pide al expandirlo (**US-200**).
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
- [ ] Cada card muestra: logo, nombre, `#Portafolios`, `#Programas`,
  `#Proyectos activos`, salud de la cartera. Los KPI de portafolios y programas
  ya los pinta el panel (**US-199/US-201**).
- [ ] Click en card → navega a `/organizations/{id}` con detalle de la org.
- [ ] En el detalle: tabs con Portafolios, Programas, Proyectos, Métricas.
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

### ENH-190 — Label de UI configurable por tenant ⛔ RETIRADA (DEC-032)

**2026-07-09, retirada el 2026-08-19.** Permitía a un inquilino ver
"Portafolio/Portafolios" en vez de "Organización/Organizaciones" en toda la
interfaz: `tenants.settings.org_label`, propagado por
`GET /api/v1/me/tenant-branding` y consumido por el hook `useOrgLabel()`.

**Por qué se retiró.** ADR-037 la volvió **inválida**, no obsoleta: «Portafolio»
pasó a ser una entidad **dentro** de la organización, así que un inquilino con el
label puesto vería «Portafolio → Portafolio → Programa» en el árbol del sidebar,
en los filtros del tablero y en los desplegables de los formularios. No es una
etiqueta confusa — es una jerarquía ilegible.

Se fue el mecanismo entero y no solo la opción: con un único valor posible
quedaba un control que se abre, se mira y se cierra, más el código de leerlo,
propagarlo por el branding y ramificar el texto en once pantallas. La
organización se llama «Organización» para todos los inquilinos.

Detalle, alternativas y qué pasa con los inquilinos que la tenían puesta:
[`DEC-032`](DECISIONS.md). Migración 0111 · trinquete
`tests/test_dec032_retiro_org_label.py`.

---

### US-198 — El portafolio como agrupador de inversión ✅ (schema y regla)

**Como** Administrador / Senior PMO
**Quiero** agrupar programas y proyectos en portafolios
**Para** decidir a nivel de cartera qué se hace, con qué y qué se deja de hacer.

**Criterios de aceptación:**
- [x] Entidad `portfolios` por organización: `name` (único por organización), `code`, `description`, `owner_actor_id` (el sponsor ejecutivo, que casi nunca tiene cuenta en la plataforma), `is_active`, soft-delete.
- [x] Sin métricas propias: salud, presupuesto y conteos se **derivan** de los proyectos. Una columna calculada aquí sería un valor que se queda viejo entre cálculos.
- [x] `programs.portfolio_id` obligatorio; `projects.portfolio_id` opcional (el proyecto puede colgar directo del portafolio, o no estar clasificado todavía).
- [x] **Regla de consistencia**: con programa asignado, el portafolio del proyecto es el del programa. Al asignar programa se autocompleta; un par contradictorio se rechaza. Un proyecto que reportara al programa A contando en el portafolio B no es un dato raro, es un dato mentiroso: la vista ejecutiva de B mostraría un proyecto que su programa no reporta.
- [x] Los programas que ya existían quedaron en el «Portafolio General» de su organización (migración 0108).
- [ ] CRUD por API y UI → **US-199** y **US-200**.

**Test Cases:**
- `TC-198.1` (integration) — Portafolio → programa dentro → proyecto con ambos: consistente.
- `TC-198.2` (integration) — Proyecto con programa de otro portafolio → rechazado.
- `TC-198.3` (integration) — Migración con programas existentes: todos con «Portafolio General» de **su** organización; los proyectos heredan el portafolio de su programa; el proyecto sin programa se queda sin portafolio.

**Decisiones:** ADR-037 (jerarquía nueva, irreversible) · DEC-030 («Portafolio General» como destino por defecto).

---

### US-199 — CRUD de portafolios y retiro de BU/departamentos ✅ (API)

**Como** Administrador / Senior PMO
**Quiero** administrar portafolios desde la API y clasificar proyectos y solicitudes en ellos
**Para** que la cartera se pueda gestionar sin tocar la base de datos.

**Criterios de aceptación:**
- [x] CRUD anidado en organización: `POST|GET /organizations/{org_id}/portfolios`, `GET|PATCH|DELETE /portfolios/{id}`. Nombre único por organización; el dueño (`owner_actor_id`) tiene que ser una persona del catálogo del propio inquilino.
- [x] `PortfolioRead` trae `program_count` y `active_project_count` **derivados** —el portafolio no guarda métricas (ADR-037)— y el conteo de proyectos suma los de sus programas más los que cuelgan directo, excluyendo cerrados.
- [x] Papelera de dos pasos (ADR-017): `DELETE` desactiva; con programas activos dentro exige `force=true` y los desactiva en cascada. `GET /portfolios/{id}/hard-delete-preview` declara qué se lleva el borrado permanente, separado en tres números: programas, proyectos de esos programas, y proyectos directos. `DELETE /portfolios/{id}/permanent?confirm=<slug>` lo ejecuta.
- [x] **El borrado permanente borra proyectos** de los programas que caen con el portafolio (`programs.portfolio_id` es NOT NULL: no hay forma de dejar un programa sin portafolio). Los proyectos que cuelgan **directo** no se borran: se desreferencian. Perder un proyecto por un cambio de taxonomía sería peor que perder la taxonomía.
- [x] Programas: `portfolio_id` en el alta (opcional → «Portafolio General») y en la edición. **Mover un programa de portafolio arrastra sus proyectos**; si no, quedarían en el portafolio viejo violando la regla de consistencia en el instante siguiente.
- [x] Proyectos y solicitudes aceptan `portfolio_id`/`program_id` con la regla de consistencia; la solicitud aprobada pasa los dos al proyecto y a su acta.
- [x] Sub-routers `business-units` y `departments` retirados: sus rutas responden **404**. Ni 410 ni redirect — un concepto retirado no se mantiene vivo a medias.
- [x] El panel de organización pasa a portafolio ⊃ programa (`portfolios` con sus programas anidados, más la lista plana de programas); las tarjetas cuentan portafolios en vez de BU/departamentos, y el detalle de inquilino del Super Admin igual.
- [x] Migración 0109: suelta las siete columnas BU/departamento **verificando que estén vacías** y crea `portfolio_id`/`program_id` en solicitudes y actas.
- [x] UI de todo esto → **US-200** (admin y formularios) y **US-201** (filtros del tablero y las vistas cross, ver EP004).

**Nota de vocabulario:** `project_requests.business_unit` y `.department` (texto
libre) **se quedan**. No son la jerarquía de la plataforma: son las palabras del
solicitante sobre qué parte de su empresa pide el trabajo. Renombrarlos es una
decisión de vocabulario propia, no parte de este retiro.

**Test Cases:**
- `TC-199.1` (integration) — CRUD completo con administrador y con usuario plano: el segundo crea, lee y edita, y **no** manda a la papelera (`organizations.delete` es de administrador).
- `TC-199.2` (integration) — Solicitud con programa → portafolio autocompletado → proyecto y acta con los dos, consistentes.
- `TC-199.3` (integration) — Rutas de BU/departamentos: 404 en los nueve verbos/rutas retirados.
- `TC-199.4` (integration) — La migración 0109 se niega si queda una referencia viva, y no suelta nada.

**Decisiones:** ADR-037 · DEC-030.

---

### US-200 — La UI de la jerarquía: Portafolio ⊃ Programa ✅

**Como** Administrador / Senior PMO
**Quiero** administrar portafolios y sus programas desde la pantalla
**Para** no tener que llamar a la API a mano para estructurar la cartera.

**Criterios de aceptación:**
- [x] **Sección de jerarquía del admin de organización** reescrita: acordeón Portafolio ⊃ Programa con alta, edición, archivado (con cascada opcional) y papelera de dos pasos en los dos niveles. Los programas se cargan **al expandir**, no todos de golpe.
- [x] **KPI cards**: «Portafolios» y «Programas» en lugar de «BUs» y «Departamentos», en el panel de organización (`/pmo` y `/admin`) y en el detalle de inquilino del Super Admin.
- [x] **`project-form.tsx`**: selects anidados Portafolio → Programa. Elegir programa **autocompleta** su portafolio —es lo que el servidor va a guardar de todos modos— y elegir portafolio filtra los programas a los suyos.
- [x] **`request-form.tsx`**: los mismos dos selects, **opcionales**. Quien solicita no siempre sabe en qué portafolio cae, y obligarlo a adivinar produce una clasificación peor que ninguna: la PMO la ajusta al revisar. Con organización nueva («Otra…») la clasificación se deja para la revisión, que es cuando la organización existe.
- [x] **Árbol del sidebar** (`org-tree-nav.tsx`): Organización → Portafolio → Programa → Proyecto, con dos cajones para lo que no encaja: «Sin programa» (cuelga del portafolio) y «Sin clasificar» (sin portafolio todavía — el caso de la importación masiva). **Retirado en US-205**: la organización se eligió una sola vez en el header y el drill-down por portafolio y programa se quedó en los filtros de cada vista, donde se combina con los demás. Los dos cajones no se perdieron — son dos valores del filtro de portafolio (`sin_programa` y `sin_portafolio`), que es lo que TC-200.1 ejercita.
- [x] **`program-modal.tsx`**: selector de portafolio, con «Portafolio General (por defecto)» como primera opción (DEC-030).
- [x] Estados vacío/cargando/error en cada nivel del árbol y de la sección; tokens del design system; `check_tokens` y `check_contraste` en verde.

**Nota de vocabulario:** los campos de texto libre de la solicitud pasan a llamarse **«Área que solicita»** y **«Equipo o sub-área»**. Siguen siendo `business_unit` y `department` en el contrato —son las palabras del solicitante, no la jerarquía— pero sus etiquetas decían el nombre de una entidad retirada.

**Test Cases:**
- `TC-200.1` (integration) — La lista de proyectos filtra por portafolio, por «del portafolio sin programa» y por «sin portafolio», que es lo que el árbol necesita para sus tres cubos.
- `TC-200.2` (manual) — Alta de portafolio y programa desde el admin, visibles en el árbol del sidebar.
- `TC-200.3` (manual) — Crear proyecto eligiendo solo programa → portafolio autocompletado en el select.
- `TC-200.4` (manual) — Usuario sin `organizations.delete` no ve acciones de archivado (el 403 de la API ya está cubierto en TC-199.1).

**Decisiones:** ADR-037 · DEC-030.

---

## Definition of Done (EP002 completo)

- [ ] Jerarquía completa: tenant → org → portafolio ⊃ programa → proyecto.
- [ ] CRUD completo de portafolios con permisos (US-199).
- [ ] BU y Departamentos retirados de la superficie (US-199) y del esquema (W8).
- [ ] Sidebar con árbol navegable.
- [ ] Vista de organizaciones como paneles.
- [ ] Breadcrumb adaptable a jerarquías incompletas.
- [ ] Aislamiento app-level en tablas nuevas verificado vía `TC-MT-001` extendido (no RLS, ver DEC-003 / `architecture/security-multitenant.md`).
- [ ] Bug 404 programas resuelto.
- [ ] Migración BD documentada y reversible.
