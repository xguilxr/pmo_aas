# EP005 — Gestión de Proyectos

| Campo | Valor |
|---|---|
| **ID** | EP005 |
| **Prioridad** | Alta |
| **Dependencias** | EP001, EP002, EP003 |
| **Módulo** | `projects` |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |

## Objetivo de negocio

Gestionar el ciclo de vida completo de un proyecto: creación (manual o desde solicitud), edición, cambio de fase, vista detalle rica con toolbar a módulos transversales, y listado con filtros potentes.

---

## User Stories

### US-024 — Matriz de proyectos con filtros

**Como** PM / PMO Manager
**Quiero** ver todos los proyectos visibles con filtros avanzados
**Para** navegar rápido.

**Filtros obligatorios:**

| Filtro | Tipo |
|---|---|
| Fase (toggle chips) | `planning`/`execution`/`support`/`closed` multiselect |
| Organización | select |
| Programa | select (depende de org) |
| Tipo | multiselect |
| Prioridad | range 1-5 |
| Búsqueda | text (nombre, folio, sponsor) |
| Rango de fechas | date range (start_date) |
| Salud | multiselect green/yellow/red |
| Solo mis proyectos | toggle |

**Criterios de aceptación:**
- [ ] `GET /api/v1/projects?…` con todos los filtros combinables (AND lógico).
- [ ] Paginación estándar, default `limit=15`.
- [ ] Orden por click en encabezados (`sort=-created_at`).
- [ ] Debounce 300 ms en búsqueda.
- [ ] URL refleja filtros (shareable).
- [ ] Vista alternativa: cards (kanban-style por fase).

**Test Cases:**
- `TC-067` (integration) — Filtros combinados dan resultado esperado.
- `TC-068` (integration) — Búsqueda fuzzy "proy" encuentra "Nuevo Proyecto".
- `TC-069` (E2E) — Cambiar filtro actualiza URL, F5 preserva estado.

---

### US-025 — Crear proyecto manual

**Como** PMO Manager
**Quiero** crear un proyecto desde cero
**Para** casos que no pasaron por solicitud.

**Campos:**

| Campo | Obligatorio |
|---|---|
| `name` | ✅ |
| `description` | ✅ |
| `type` | ✅ |
| `priority` (1-5) | ✅ |
| `organization_id` | ✅ |
| `program_id` | opcional |
| `phase` (default: planning) | ✅ |
| `pm_id` | ✅ |
| `sponsor` | opcional |
| `start_date`, `end_date` | opcional en planning |
| `budget` | opcional |

**Criterios de aceptación:**
- [ ] `POST /api/v1/projects`.
- [ ] `folio` auto `PRJ-YYYY-NNN`.
- [ ] Creador auto-asignado al team como `Project Manager`.
- [ ] Validación: `end_date > start_date` si ambos presentes.
- [ ] Audita `project.create`.

**Test Cases:**
- `TC-070` (integration) — Validar fechas inconsistentes → 422.
- `TC-071` (integration) — PM auto-asignado al team.

---

### US-026 — Detalle del proyecto

**Como** PM
**Quiero** una vista rica con toda la info del proyecto
**Para** gestionarlo sin saltar de pantalla.

**Secciones:**
1. Header con breadcrumb, folio, nombre, fase (con acción "Cambiar fase"), salud.
2. KPIs del proyecto: avance, presupuesto plan/real, riesgos abiertos, cambios pendientes.
3. Tabs: `Resumen | Equipo | Avance | Presupuesto | Timeline | Actividad`.
4. Toolbar lateral izquierdo con 6 iconos: Riesgos, Incidencias, Cambios, Documentos, Lecciones, Minutas (+ Tareas/Gantt).
5. Acciones header: Editar, Cambiar fase, Exportar (PDF/JSON).

**Criterios de aceptación:**
- [ ] `GET /api/v1/projects/{id}` — devuelve proyecto + members + counts de cada módulo.
- [ ] Permiso `projects:read` requerido; 404 si el user no es miembro (salvo PMO Manager/Admin).
- [ ] Actividad (timeline): últimos 20 eventos del `audit_log` relacionados al proyecto.

**Test Cases:**
- `TC-072` (integration) — Detail incluye counts correctos por módulo.
- `TC-073` (E2E) — Toolbar abre cada módulo dentro del proyecto.

---

### US-027 — Editar proyecto

**Como** PM / PMO Manager
**Quiero** editar campos del proyecto
**Para** mantenerlo actualizado.

**Criterios de aceptación:**
- [ ] `PATCH /api/v1/projects/{id}` — campos parciales.
- [ ] Campos read-only después de crear: `folio`, `created_at`, `created_by`, `tenant_id`.
- [ ] Cambiar `pm_id` dispara notificación al PM entrante y saliente.
- [ ] Audita qué campos cambiaron (diff antes/después).

**Test Cases:**
- `TC-074` (integration) — Editar `folio` → 400 (read-only).
- `TC-075` (integration) — Diff en audit_log.

---

### US-028 — Cambiar fase del proyecto

**Como** PMO Manager
**Quiero** mover un proyecto de fase
**Para** reflejar avance real.

**Transiciones válidas:**

```
planning → execution → support → closed
planning → closed (cancelado)
execution → closed (cancelado)
```

**Criterios de aceptación:**
- [ ] `POST /api/v1/projects/{id}/phase/change` con `{new_phase, comment?}`.
- [ ] Transición inválida → 409 `STATE_TRANSITION`.
- [ ] Al pasar a `execution`: `start_date` obligatoria si null.
- [ ] Al pasar a `closed`: bloquea edición (readonly), excepto lecciones aprendidas.
- [ ] Audita `project.phase_change` con from→to.

**Test Cases:**
- `TC-076` (integration) — Transición inválida `closed→execution` → 409.
- `TC-077` (integration) — Cerrar proyecto: subsecuentes escrituras en módulos (salvo lessons) → 403.

---

### US-029 — Gestión del equipo del proyecto

**Como** PM
**Quiero** agregar/quitar miembros del equipo con rol por proyecto
**Para** controlar visibilidad y permisos.

**Criterios de aceptación:**
- [ ] `GET /api/v1/projects/{id}/members`.
- [ ] `POST /api/v1/projects/{id}/members` con `{user_id, role_in_project}`.
- [ ] `DELETE /api/v1/projects/{id}/members/{user_id}`.
- [ ] Roles en proyecto: `pm` (único), `team`, `viewer`, `stakeholder`.
- [ ] No se puede remover al PM vigente (primero cambiar PM).

**Test Cases:**
- `TC-078` (integration) — Agregar duplicado → 409.
- `TC-079` (integration) — Remover PM → 422.

---

### US-030 — Exportar proyecto

**Como** PM
**Quiero** exportar el proyecto a PDF / JSON
**Para** compartirlo fuera del sistema.

**Criterios de aceptación:**
- [ ] `GET /api/v1/projects/{id}/export?format=pdf|json`.
- [ ] PDF: plantilla con header, KPIs, últimas minutas, riesgos top 5.
- [ ] Generación PDF: **WeasyPrint** (backend) o Chromium headless (Puppeteer en worker).
- [ ] JSON: todos los campos + relaciones necesarias para re-importar.

**Test Cases:**
- `TC-080` (integration) — JSON export válido (schema check).
- `TC-081` (E2E) — PDF se descarga y abre.

---

## Notas técnicas

- Folios por tenant+año (Postgres sequences o función).
- Member list cacheable 60 s.
- Al cerrar proyecto, dispara job para generar reporte final con IA (opcional, ver EP008).

### Endpoints
```
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{id}
PATCH  /api/v1/projects/{id}
DELETE /api/v1/projects/{id}                 (soft)
POST   /api/v1/projects/{id}/phase/change

GET    /api/v1/projects/{id}/members
POST   /api/v1/projects/{id}/members
DELETE /api/v1/projects/{id}/members/{user_id}

GET    /api/v1/projects/{id}/export
```

---

## Definition of Done

- [ ] Listado < 300 ms p95 con 1000 proyectos seed.
- [ ] Detail carga < 500 ms p95.
- [ ] Transiciones de fase cubiertas por state machine con tests.
- [ ] Export PDF con layout limpio (coincide con design system).
- [ ] Permisos verificados por tests (`TC-MT-002` para reads de módulos de otro tenant).

---

## # PENDING — User Stories nuevas

### US-016 — Unificar Plan + Gantt en una sola pestaña

**Como** PM
**Quiero** ver la lista de tareas y el Gantt en una misma vista
**Para** navegar planeación sin saltar entre pestañas.

**Criterios de aceptación:**
- [x] Ruta `/admin/projects/{id}/plan` con layout unificado.
- [x] Toggle `Lista / Dividida / Gantt` persistido en URL (`?view=list|gantt`).
- [x] Default = "Dividida" (lista arriba, Gantt abajo).
- [x] En "Lista" se muestra tabla read-only con link "Abrir editor
  completo" → `/tasks` (edición detallada sin refactorizar).
- [x] Pestaña "Gantt" separada eliminada del sidebar.
- [x] `/gantt` continúa funcionando como redirect permanente a
  `/plan?view=gantt`.

**Estado de integración:** DONE (US-016).

---

### US-018 — Módulo Área/Organigrama del proyecto

**Como** PM
**Quiero** registrar áreas y actores del proyecto (stakeholders sin
cuenta en la plataforma)
**Para** referenciarlos en tareas, RAIDs y minutas.

**Criterios de aceptación:**
- [x] Migración Alembic `20260420_0013`: tabla `project_areas`.
- [x] Modelo `ProjectArea` (DEC-009: no son usuarios del sistema).
- [x] CRUD endpoints:
  - `GET /projects/{id}/areas?q=&type=&is_active=`
  - `POST /projects/{id}/areas`
  - `GET /project-areas/{id}`
  - `PATCH /project-areas/{id}`
  - `DELETE /project-areas/{id}`
- [x] Validación de email en `contact_email` (EmailStr).
- [x] Tipo: `area | actor | team`.
- [x] Filtrado por tipo en listado.
- [x] Aislamiento multi-tenant verificado (404 en proyecto ajeno).
- [x] Página frontend `/admin/projects/{id}/areas` con CRUD completo
  (modal de crear/editar + confirmación de eliminar + búsqueda +
  filtro por tipo).
- [x] Entrada "Áreas" en el sidebar de módulos del proyecto.

**Test Cases:**
- `TC-NEW-025` — CRUD completo ✅
- `test_areas_invalid_email` → 422 ✅
- `test_areas_filter_by_type` ✅
- `test_areas_scoped_to_project` ✅
- `test_areas_multitenant_isolation` ✅

**Estado de integración:** DONE (US-018).
