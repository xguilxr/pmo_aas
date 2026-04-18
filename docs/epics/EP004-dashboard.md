# EP004 — Dashboard del Project Manager

| Campo | Valor |
|---|---|
| **ID** | EP004 |
| **Prioridad** | Alta |
| **Dependencias** | EP001, EP002, EP005 |
| **Módulo** | `dashboard` |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |

## Objetivo de negocio

Dar a Project Managers y PMO Managers una vista en un solo lugar del estado del portafolio: KPIs accionables, gráficos de salud y una matriz Plan vs Real — todo respetando permisos del usuario.

---

## User Stories

### US-020 — KPIs en tarjetas

**Como** PM / PMO Manager
**Quiero** ver 8 KPIs en tarjetas clickeables
**Para** entender el estado del portafolio de un vistazo.

**KPIs obligatorios:**

| KPI | Fuente |
|---|---|
| Proyectos Activos | `count(projects WHERE phase IN ('planning','execution','support'))` |
| Solicitudes en Revisión | `count(project_requests WHERE status='in_review')` |
| Riesgos Abiertos | `count(risks WHERE status NOT IN ('closed'))` |
| Riesgos Severos | `count(risks WHERE severity >= 13 AND status NOT IN ('closed'))` |
| Cambios en Revisión | `count(change_requests WHERE status='in_review')` |
| AIDs Abiertos | `count(issues WHERE status IN ('open','in_progress'))` |
| Presupuesto Total | `sum(projects.budget)` |
| Avance Promedio | `avg(projects.progress)` |

**Criterios de aceptación:**
- [ ] `GET /api/v1/dashboard/kpis` — retorna los 8 valores.
- [ ] Caché Redis 5 min por `(tenant_id, user_id)` (porque respeta permisos).
- [ ] Respeta filtro por proyectos asignados: user con rol `Viewer` solo ve KPIs de proyectos donde es miembro.
- [ ] Cada tarjeta tiene `link_to` → navega a vista filtrada.
- [ ] Skeleton mientras carga; números animan de 0 al valor final (Framer Motion).

**Test Cases:**
- `TC-057` (integration) — Admin ve todos los proyectos, Viewer solo asignados.
- `TC-058` (integration) — Caché: 2da llamada < 50 ms.
- `TC-059` (E2E) — Click en "Riesgos Severos" navega a `/risks?severity_min=13`.

---

### US-021 — Gráficos del portafolio

**Como** PMO Manager
**Quiero** 4 gráficos visuales
**Para** detectar patrones.

**Gráficos:**
1. **Pie chart — Proyectos por fase**: Planificación / Ejecución / Soporte / Cerrado.
2. **Bar chart — Avance promedio por fase**.
3. **Bar chart — Presupuesto por tipo de proyecto** (innovation, transformation, operation, bau).
4. **Pie chart — Salud del portafolio**: Verde / Amarillo / Rojo.

**Criterios de aceptación:**
- [ ] `GET /api/v1/dashboard/charts` — retorna los 4 datasets.
- [ ] Tooltips al hover muestran valor absoluto y %.
- [ ] Colores consistentes con design tokens (`--color-health-green`, `-yellow`, `-red`).
- [ ] Responsive: 2 columnas desktop, 1 columna mobile.
- [ ] Librería: **Recharts** (compatible con RSC via client component wrapper).

**Test Cases:**
- `TC-060` (integration) — Datos agregados correctos para un set fixture.
- `TC-061` (E2E) — Gráficos renderizan, tooltips funcionan, accesibilidad (aria-label).

---

### US-022 — Matriz Plan vs Real

**Como** PM
**Quiero** una matriz comparativa planeado vs real por proyecto
**Para** identificar desviaciones.

**Columnas de la matriz:**

| Col | Descripción |
|---|---|
| Proyecto | nombre + folio |
| Fecha fin plan | `end_date` |
| Fecha fin real / proyectada | basada en avance y tasks |
| Presupuesto plan | `budget` |
| Presupuesto real | `actual_budget` |
| Avance plan (%) | calculado por fecha actual vs rango |
| Avance real (%) | `progress` |
| Salud | badge Verde/Amarillo/Rojo |

**Criterios de aceptación:**
- [ ] `GET /api/v1/dashboard/plan-vs-actual?organization_id=&program_id=&phase=`.
- [ ] Filtros combinables por org, programa, fase.
- [ ] Orden default: salud desc (rojo primero).
- [ ] Export CSV disponible.
- [ ] Click en fila → detalle del proyecto.

**Test Cases:**
- `TC-062` (integration) — Cálculo de salud: fecha desviada > 10% → yellow.
- `TC-063` (integration) — Export CSV incluye todas las filas con mismas columnas.
- `TC-064` (E2E) — Filtros actualizan la tabla sin reload.

---

### US-023 — Responsive y personalización mínima

**Como** PM
**Quiero** que el dashboard funcione en mobile y tablet
**Para** consultarlo desde cualquier lado.

**Criterios de aceptación:**
- [ ] Breakpoints: mobile < 640px (1 col), tablet 640-1024 (2 col), desktop ≥ 1024 (4 col para KPIs).
- [ ] Tarjetas de KPI tienen orden fijo; usuario puede ocultar con ajuste en `users.preferences` (post-MVP: drag&drop).
- [ ] Modo oscuro respeta preferencia de sistema.

**Test Cases:**
- `TC-065` (E2E) — Snapshot visual en 3 breakpoints.
- `TC-066` (unit) — Preferencias de usuario persisten.

---

## Notas técnicas

- **Agregaciones** en queries SQL dedicadas (no cargar todo en memoria).
- **Redis cache** con key `dashboard:kpis:{tenant_id}:{user_id}`, TTL 300.
- **Invalidación**: al crear/editar/borrar projects, risks, issues, changes → `DEL` de las keys del tenant (pattern delete).

### Endpoints
```
GET /api/v1/dashboard/kpis
GET /api/v1/dashboard/charts
GET /api/v1/dashboard/plan-vs-actual
GET /api/v1/dashboard/plan-vs-actual/export.csv
```

---

## Definition of Done

- [ ] TTFB dashboard ≤ 200 ms (con caché caliente).
- [ ] Los 8 KPIs y 4 gráficos se pintan en < 1 s (p95).
- [ ] Todos los permisos de visibilidad verificados por tests (TC-MT-001).
- [ ] Modo oscuro consistente con design system.
- [ ] Accesibilidad: gráficos tienen tabla HTML alternativa (`<table>` oculta visualmente pero leíble por screen reader).
