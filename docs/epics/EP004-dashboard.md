---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

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

El dashboard da a Project Managers y PMO Managers una vista única del portafolio: KPIs accionables, gráficos de salud y una matriz Plan vs Real. Todo respeta los permisos del usuario.

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
- [x] **La ausencia de dato se ve distinta del cero** (MCS DAT-12, 2026-08-06).
      Un KPI sin dato —presupuesto no cargado, o el indicador aún
      cargando— muestra «—» atenuado con etiqueta accesible «sin dato», no
      un `0`. La distinción importa: un proyecto sin presupuesto cargado y
      uno con presupuesto cero piden acciones distintas. «0 riesgos
      abiertos» puede ser un proyecto sano o uno sin riesgos registrados.
      La convención vive en `apps/web/lib/sin-dato.ts`.
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
GET  /api/v1/dashboard/kpis
GET  /api/v1/dashboard/charts
GET  /api/v1/dashboard/plan-vs-actual
GET  /api/v1/dashboard/plan-vs-actual/export.csv
# US-152 — analytics para dashboards N1/N2 (scope=tenant|organization|program|project, id=)
GET  /api/v1/dashboard/trends?scope=&id=&metric=&weeks=   # serie histórica (metric_snapshots)
GET  /api/v1/dashboard/risk-matrix?scope=&id=             # conteo prob×impacto (en vivo)
GET  /api/v1/dashboard/heatmap                            # Org×Salud (portafolio, admin)
GET  /api/v1/dashboard/treemap?scope=&id=                 # Org→Programa→Proyecto
POST /api/v1/dashboard/snapshots/capture                  # seed on-demand del snapshot de hoy
GET  /api/v1/dashboard/health-matrix                      # US-181 (2026-07-09) — heatmap Proyecto×Dimensión
```

---

## Definition of Done

- [ ] TTFB dashboard ≤ 200 ms (con caché caliente).
- [ ] Los 8 KPIs y 4 gráficos se pintan en < 1 s (p95).
- [ ] Todos los permisos de visibilidad verificados por tests (TC-MT-001).
- [ ] Modo oscuro consistente con design system.
- [ ] Accesibilidad: gráficos tienen tabla HTML alternativa (`<table>` oculta visualmente pero leíble por screen reader).

---

## # PENDING — User Stories nuevas

### US-014 — Filtro de organización en dashboard

**Como** Admin / PMO Manager
**Quiero** filtrar todo el dashboard (KPIs, gráficas, Plan vs Real) por
una organización específica
**Para** enfocarme en el portafolio de un cliente.

**Criterios de aceptación:**
- [x] Filtro por organización visible en la parte superior del dashboard.
- [x] Default vacío (sin filtro → muestra todo el tenant).
- [x] Al seleccionar una org, KPIs, gráficos y Plan vs Real se filtran
  simultáneamente.
- [x] Estado del filtro sincronizado con la URL (`/dashboard?org_id=...`).
- [x] Botón "Limpiar" regresa a vista completa.
- [x] Backend: endpoints `/dashboard/kpis` y `/dashboard/charts` aceptan
  `organization_id` opcional; `/plan-vs-actual` ya lo aceptaba.

**Tests:**
- `test_usnew014_kpis_filtered_by_org` — KPIs se filtran correctamente ✅
- `test_usnew014_charts_filtered_by_org` — charts se filtran ✅

**Estado de integración:** DONE (US-014).

---

### US-015 — KPIs respetan jerarquía de roles

**Como** usuario según su rol
**Quiero** ver sólo los KPIs relevantes a mi scope
**Para** enfocarme en los datos que me corresponden.

**Criterios de aceptación:**
- [x] Helper `scoped_project_ids(cu, db, tenant_id, org_id)` en
  `dashboard.py`: devuelve lista de project_ids visibles o `None` si
  admin-equivalente.
- [x] Admin / Senior PMO: sin restricción (via `is_admin_equivalent`).
- [x] Project Manager y otros roles: proyectos donde es `pm_id` o está en
  `project_members`.
- [x] Aplica a `/dashboard/kpis`, `/dashboard/charts` y
  `/dashboard/plan-vs-actual`.
- [x] Solicitudes (in_review) para no-admin: sólo las que el usuario creó.
- [x] Usuario sin proyectos asignados → conteos en 0, sin error.

**Test Cases:**
- Admin ve todo ✅
- PM ve sólo proyectos donde es pm_id ✅
- PM ve sólo proyectos donde es miembro ✅
- Usuario sin asignaciones → 0 ✅
- Charts y Plan-vs-Real respetan scoping ✅

**Notas:**
- La granularidad "Program Manager ve su programa + PMs bajo él" queda
  pendiente para una US posterior. Requiere modelar ownership de
  programas; hoy no existe en el schema.

**Estado de integración:** DONE (US-015).

---

### BUG-003 — Fix layout Plan vs Real (filtros horizontales + columna PM)

**Criterios de aceptación:**
- [x] Filtros Organización + Fases al mismo nivel horizontal que el
  botón "Exportar CSV" (ya estaba, verificado).
- [x] Tabla con columna nueva "PM asignado":
  - Celda vacía ("—") si el proyecto no tiene `pm_id`.
  - Link clickeable al perfil (`/admin/users/{id}`) cuando hay nombre.
- [x] Backend `/dashboard/plan-vs-actual` devuelve `pm_id` + `pm_name`
  (precargados con un solo SELECT IN).
- [x] CSV export incluye columna `pm_name`.

**Test Cases:**
- `test_usbug003_pm_name_in_plan_vs_actual` — pm_id y pm_name presentes ✅

**Estado de integración:** DONE (BUG-003).

---

### US-151 / US-152 — Fundación analítica + dashboards N1/N2 (2026-05-26)

Los dashboards Nivel 1 (PMO/Portafolio) y Nivel 2 (Organización/Programa) son
ricos y **derivan** los reportes N1/N2. El dashboard es la vista interactiva;
el reporte es el mismo contenido congelado a PDF.

**US-151 — fundación de datos (`metric_snapshots`):**
- Tabla `metric_snapshots`: foto **semanal** (lunes 02:00 UTC, Celery beat) de
  métricas de stock a 4 niveles de scope (tenant/org/programa/proyecto). Habilita
  tendencias y desbloquea S-05/S-07 de EP020.
- Servicio `services/analytics/snapshots.py` (cómputo + upsert idempotente);
  job `workers/tasks/snapshots.py`.
- **BUG-082 (2026-06-29):** `avg_progress` del snapshot (base de la *evolución de
  avance* en `/dashboard/trends`) ahora usa el **avance efectivo derivado del
  rollup WBS del plan** (`plan_rollup_map`), igual que el dashboard en vivo. Antes
  leía la columna `Project.progress` (manual), que queda en 0 desde ENH-155 para
  proyectos cuyo avance se deriva del plan → la serie salía en 0. Los snapshots ya
  escritos en 0 no se recalculan. Recapturar (job semanal o `snapshots/capture`)
  corrige de hoy en adelante.

**US-152 — endpoints de analytics:** `trends`, `risk-matrix`, `heatmap`,
`treemap`, `POST snapshots/capture` (ver bloque Endpoints). Authz: vistas
agregadas (tenant/org/programa) son admin-equivalente; scope=project respeta
`scoped_project_ids`. Multi-tenant por `tenant_id` en toda query.

**US-153 — primitivos SVG + cliente analytics:** `Gauge`, `TrendLines`,
`RiskMatrix`, `Heatmap`, `Treemap` en `components/dashboard-charts.tsx` (tokens
del design-system); `KpiCard` gana píldora de tendencia; `lib/api/analytics.ts`.

**US-154/155/156/157 — analítica en las 4 páginas:**
- `/dashboard`: matriz de riesgos + heatmap (click filtra) + banda de tendencias
  + treemap + botón "Capturar snapshot". Respeta filtro de organización.
- `/pmo`: heatmap (click navega a la org) + treemap + tendencias del tenant.
- `/pmo/organizations/[id]` (Resumen): donut de salud + matriz de riesgos +
  tendencias org-scoped.
- `/pmo/programs/[id]` (Resumen): gauges avance/presupuesto + matriz de riesgos
  + tendencias program-scoped.
- Las vistas agregadas (heatmap/treemap/tendencias tenant/org/programa) son
  admin-equivalente; detección por capacidad (si el endpoint 403ea se ocultan).

**Test Cases:**
- `test_us151_metric_snapshots` — cómputo 4 niveles + idempotencia ✅
- `test_us152_analytics` — trends/risk-matrix/heatmap/treemap/capture + authz ✅
- Front: `tsc --noEmit` + `next build` verdes (sin tests de UI en el repo).

**US-160 — reportes de status N1/N2 (PDF, fuera del builder):** se derivan de
los dashboards y se descargan desde sus páginas. `build_scope_status_context`
(KPIs + salud + tendencias sparkline desde snapshots + matriz de riesgos +
tabla comparativa) → plantilla `reports/scope_status.html`. Endpoints
`POST /dashboard/reports/portfolio` (N1), `POST /organizations/{id}/reports/status`
y `POST /programs/{id}/reports/status` (N2, admin). Botones de descarga en `/pmo`,
org y programa. Helper SVG en `reports/svg.py` (compartido con el motor).

**Estado de integración:** backend + frontend DONE (Fase 1-5) + follow-ups:
- **ENH-141** — `ProgressGauge` del project detail consolidado en el `Gauge`
  compartido (tras merge de #511).
- **US-161** — sección de reporte **S-07 Curva-S** (planeado vs real; planeado
  capturado en `metric_snapshots.extras.avg_progress_plan`).
- **US-162** — vistas/reportes agregados N1/N2 **accesibles a PMs** con scoping
  por `scoped_project_ids` (capturar snapshots sigue admin-only).
- **US-163** — **heatmap + treemap** embebidos en los PDF de status N1/N2.

Único pendiente: verificación manual en navegador + revisión visual de los PDF.

---

### US-181 — Heatmap de salud por dimensión en dashboard N1 (2026-07-09)

**Como** PM / PMO Manager
**Quiero** ver un heatmap Proyecto × Dimensión de salud en el dashboard N1
**Para** detectar de un vistazo qué proyectos están mal y en qué dimensión
(cronograma, presupuesto, riesgos/issues, decisiones — ver US-180 en
EP005).

**Implementación (`0c0ad7d`):**
- `GET /api/v1/dashboard/health-matrix` — antes de responder, refresca la
  salud automática de los proyectos visibles **en bulk**
  (`refresh_health_bulk`) y devuelve solo proyectos activos
  (`phase != closed`). Respeta visibilidad de US-168 (no-admin ve solo
  sus proyectos vía `scoped_project_ids`).
- Sección "Salud por dimensión (proyectos activos)" en `/pmo` con
  click-through al proyecto.
- El snapshot semanal (`services/analytics/snapshots.py`) también
  refresca la salud auto de **todos** los proyectos del tenant y persiste
  el desglose de dimensiones en `metric_snapshots.extras.health_dimensions`
  (scope proyecto). Esto habilita tendencias de salud por dimensión a
  futuro.

**Estado de integración:** DONE (US-181, ver también EP005).

---

### US-191 — Evaluación de salud 5+1 con historial (2026-07-18)

**Como** PM / PMO Manager
**Quiero** declarar manualmente la salud del proyecto en 5 dimensiones + overall, con historial de evaluaciones anteriores
**Para** auditar cambios de percepción y crear una bitácora de decisiones de salud.

**Implementación (`66971ba`):**
- Tabla nueva `project_health_evaluations` (migración 0096): 5 dimensiones nullable (cronograma/presupuesto/riesgos/issues/decisiones) + `overall` NOT NULL + `evaluated_at` timestamp + `note` texto (obligatorio si overall = amarillo/rojo).
- Endpoints: `POST /projects/{id}/health-evaluations` (crear evaluación), `GET /projects/{id}/health-evaluations` (listar historial).
- El `overall` se aplica al semáforo del proyecto como **declaración manual** (complementa/convive con motor automático US-180). Nota obligatoria en amarillo/rojo.
- Frontend: `HealthEvaluationModal` (6 selects RAG para dimensiones + fecha + nota + tabla de evaluaciones anteriores) + botón "Evaluar salud" en la tarjeta de Salud del proyecto detail.

**Estado de integración:** DONE (US-191).

---

### US-192 — Heatmap de salud por dimensión en portafolio + reporte XLSX (2026-07-18)

**Como** PMO Manager
**Quiero** desde el dashboard portafolio ver un heatmap de salud por dimensión con botones de evaluación masiva y exportar historial de evaluaciones
**Para** gestionar la salud de todos los proyectos desde un solo lugar.

**Implementación (`e135a2b`):**
- Heatmap "Salud por dimensión" en `/pmo` (reutiliza `GET /dashboard/health-matrix`) con botón "Evaluar por fila" (abre `HealthEvaluationModal` para el proyecto).
- Botón "Reporte de salud (XLSX)" descarga archivo de 2 hojas:
  - **Matriz Actual:** estado de salud de cada proyecto por dimensión (hoy).
  - **Historial de Evaluaciones:** todas las evaluaciones registradas (fecha, proyecto, dimensiones, nota).
- Endpoint nuevo: `GET /dashboard/health-evaluations` con visibilidad respetada (health-matrix scoping).
- En `/pmo/projects` el dot de Salud abre el modal de evaluación y se repinta tras guardar.

**Estado de integración:** DONE (US-192).

---

### ENH-185 — Filtros de programa y prioridad mínima en `/pmo/projects` (2026-07-09)

**Como** PMO Manager
**Quiero** filtrar el listado de proyectos por programa (incluyendo "sin
programa") y por prioridad mínima
**Para** enfocarme en un subconjunto del portafolio.

**Implementación (`9bb3338`):** el frontend expone filtros que la API ya
soportaba — `program_id`, `no_program`, `priority_min` — con cascada
Organización → Programa y sincronización a la URL (`/pmo/projects?...`).
Sin cambios de contrato en backend (los query params ya existían).

**Estado de integración:** DONE (ENH-185).
