---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-19
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
**Quiero** ver los indicadores del portafolio en tarjetas clickeables
**Para** entender su estado de un vistazo.

**Las seis tarjetas** (US-206 las dejó en estas; ver el detalle más abajo):

| KPI | Fuente |
|---|---|
| Proyectos activos | `count(projects WHERE phase IN FASES_ACTIVAS)` — las tres no terminales, derivadas de la constante y no escritas a mano en el endpoint. Pie: cuántos en la primera fase |
| Salud | `count(projects) GROUP BY health_status` — los tres conteos en una tarjeta, con barra proporcional |
| Avance plan vs real | `progress_avg` (rollup del plan con caída al campo manual, ENH-109) contra `plan_progress_avg` (avance esperado por calendario). Pie: la desviación en puntos |
| Presupuesto | `sum(projects.budget)` y `sum(projects.actual_budget)`, **agrupados por moneda** (BUG-092). Pie: consumido y restante |
| Riesgos severos | `count(risks WHERE severity >= 13 AND status != 'resolved')`. Pie: cuántos sin `owner_id` **ni** `owner_actor_id` |
| Sobreasignados | `count` de recursos con `over_pct > 0` en `/capacity/summary` |

El endpoint sigue devolviendo `requests_in_review`, `open_risks`,
`change_requests_in_review` y `open_issues`: son el insumo de otras superficies
y de las instantáneas. Lo que cambió es qué se pinta en el tablero.

**Criterios de aceptación:**
- [x] `GET /api/v1/dashboard/kpis` — retorna los valores de la tabla de arriba.
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
1. **Pie chart — Proyectos por fase**: Preparación / Ejecución / Hypercare / Cerrado / Cancelado.
2. **Bar chart — Avance promedio por fase**.
3. **Bar chart — Presupuesto por tipo de proyecto** (`transformacion`, `operacion`, `innovacion`, `bau`). Los proyectos sin tipo se agrupan bajo `unspecified`, que la API sintetiza para no perder el importe.
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

US-201 partió las superficies en dos familias, y la diferencia importa al llamarlas:

- **Las que filtran** aceptan la cascada `organization_id` + `portfolio_id` +
  `program_id`, acumulativa. Los tres se suman; una combinación que no se cruza
  (un programa de otro portafolio) devuelve vacío, no un error.
- **Las que scopean** toman `scope=` + `id=`: un solo nivel, el que se pide.
  `scope` admite `tenant | organization | portfolio | program | project`.

```
GET  /api/v1/dashboard/kpis?organization_id=&portfolio_id=&program_id=
GET  /api/v1/dashboard/charts?organization_id=&portfolio_id=&program_id=
GET  /api/v1/dashboard/plan-vs-actual?organization_id=&portfolio_id=&program_id=&phase=
GET  /api/v1/dashboard/plan-vs-actual/export.csv     # mismos filtros; delega en el anterior
# US-152 — analytics para dashboards N1/N2 (scope=, id=)
GET  /api/v1/dashboard/trends?scope=&id=&metric=&weeks=   # serie histórica (metric_snapshots)
GET  /api/v1/dashboard/risk-matrix?scope=&id=             # conteo prob×impacto (en vivo)
GET  /api/v1/dashboard/heatmap?organization_id=&portfolio_id=&program_id=   # Org×Salud (admin)
GET  /api/v1/dashboard/treemap?scope=&id=                 # Org→Portafolio→Programa→Proyecto
POST /api/v1/dashboard/snapshots/capture                  # seed on-demand del snapshot de hoy
GET  /api/v1/dashboard/health-matrix?organization_id=&portfolio_id=&program_id=  # US-181 — Proyecto×Dimensión
```

**El portafolio agrega todo lo suyo**: los proyectos de sus programas **y** los
que cuelgan directo de él. Filtrar por los programas del portafolio dejaría
fuera exactamente a los segundos, y el resultado no falla — devuelve un número
más chico.

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
  métricas de stock por scope: `tenant`, `organization`, `portfolio` (US-201),
  `program` y `project`. Habilita tendencias y desbloquea S-05/S-07 de EP020.
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
  (`phase != cerrado`; en su momento se escribió `closed`, que US-202 renombró).
  Respeta visibilidad de US-168 (no-admin ve solo sus proyectos vía
  `scoped_project_ids`).
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

---

### US-201 — La cascada Organización → Portafolio → Programa ✅ (2026-08-19)

**Como** PMO Manager / Administrador
**Quiero** filtrar el tablero y las vistas cross por portafolio y por programa
**Para** mirar la cartera de un cliente al nivel al que se decide sobre ella.

**Criterios de aceptación:**
- [x] Las siete superficies del tablero aceptan el nivel de portafolio: `kpis`,
  `charts`, `plan-vs-actual` (+ CSV), `heatmap` y `health-matrix` por filtro;
  `trends`, `risk-matrix` y `treemap` por `scope=portfolio`.
- [x] `treemap` devuelve cuatro niveles: Organización → Portafolio → Programa →
  Proyecto. El portafolio es un nivel propio y no una etiqueta del programa,
  porque un proyecto puede colgar del portafolio **sin** programa. Antes esos
  proyectos salían bajo el mismo «Sin programa» que los no clasificados: dos
  situaciones distintas dibujadas igual.
- [x] Las cinco vistas cross (`/tenant/risks`, `issues`, `change-requests`,
  `meeting-minutes`, `reports`) aceptan `portfolio_id`.
- [x] `metric_snapshots` gana el scope `portfolio`, y el recorrido semanal lo
  escribe **antes** que los programas: si el snapshot falla a mitad, lo que
  queda escrito es el nivel de arriba, que es el que se mira.
- [x] `GET /programs` acepta `portfolio_id`. Es lo que impide que el
  desplegable de programa ofrezca los de otro portafolio.
- [x] `/dashboard` y `TenantCrossFilters`: cascada de tres (o cuatro) niveles
  donde **cada cambio limpia los de abajo**, y los tres en la URL
  (`?org_id=&portfolio_id=&program_id=`) para que un tablero filtrado se pueda
  enviar por chat.

**Test Cases:**
- `TC-201.1` — Los KPIs de un portafolio suman sus programas **y** sus proyectos
  directos (700k = 100k + 200k del programa + 400k directo, no 300k).
- `TC-201.2` — Cruzar un portafolio con un programa ajeno devuelve vacío, no un
  error; y `/programs?portfolio_id=` no ofrece ese programa.
- `TC-201.3` — El snapshot con `scope=portfolio` se captura y se lee en
  `trends`, con el mismo total que el KPI de hoy.
- `TC-201.4` — Mover un programa de portafolio arrastra sus proyectos: los dos
  KPIs cambian y siguen sumando el total.

**Nota de diseño:** el filtro de organización que había duplicado en la cabecera
de «Plan vs Real» se retiró. Con un nivel se puede repetir el mismo estado dos
veces en la pantalla; con tres serían seis controles para tres filtros.

**Decisiones:** ADR-037.

**Estado de integración:** DONE (US-201).

---

### US-206 — El tablero ejecutivo en cuatro filas ✅ (2026-08-20)

**Como** PMO Manager / patrocinador
**Quiero** que el tablero se lea de arriba abajo como una conversación de comité
**Para** saber cómo va la cartera, qué mirar primero y por qué, sin abrir cinco
pantallas.

De los mockups aprobados el 2026-08-19, artboard «Dashboard ejecutivo».

**Las cuatro filas:**

1. **Seis tarjetas** — activos, salud, plan vs real, presupuesto, riesgos
   severos, sobreasignados. Cada una con su pie: el número solo no acciona
   nada. «7 riesgos severos» es un estado; «7, 2 sin responsable» es una tarea.
2. **Tres listas cortas** — top en riesgo, top con atraso, top sobrecarga de
   recursos. Existen porque un agregado dice que algo pasa y una lista dice
   **dónde**. Cinco filas como máximo: una de veintitrés vuelve a ser la tabla
   que ya está abajo, y entonces no ordena nada.
3. **Cuatro distribuciones** — por salud, por fase, por programa, por sponsor.
   Las dos últimas son nuevas: son las preguntas que un comité hace («¿quién
   coordina esto?», «¿quién lo pidió?») y que las dos primeras no contestan.
4. **Tendencia y semáforo consolidado** — las cinco dimensiones de salud 5+1
   agregadas para la cartera.

**Criterios de aceptación:**
- [x] `GET /dashboard/kpis` añade `plan_progress_avg`,
  `budget_consumed_by_currency` y `severe_risks_unassigned`. Los dos avances
  promedian **el mismo conjunto** de proyectos: la resta de la tarjeta solo
  significa algo si los dos lados cubren lo mismo.
- [x] «Sin responsable» son los **dos** campos vacíos —`owner_id` legacy y
  `owner_actor_id` del catálogo (ENH-079)—. Mirar uno solo cuenta como huérfano
  lo que tiene dueño.
- [x] `GET /dashboard/charts` añade `projects_by_program` y
  `projects_by_sponsor`, con `LEFT JOIN`: los proyectos que cuelgan del
  portafolio sin programa (DEC-030) son un grupo real y la clave `""` los
  nombra. Con `INNER JOIN` desaparecían y el gráfico sumaba menos que el total
  sin que nada fallara.
- [x] `GET /dashboard/tops` — las dos listas de proyectos, con `limite`
  (5 por defecto, 20 como techo). El atraso se calcula en el servidor con
  `_plan_progress_for`, la misma función que usa `plan-vs-actual` fila a fila:
  derivarlo en el cliente dejaría la definición de «atraso» en dos sitios.
- [x] Los proyectos **sin fechas** no entran en «top con atraso». Su avance
  esperado por calendario es 0, así que uno al 90 % saldría como «+90 pts
  adelantado» contra un plan que no existe.
- [x] La tercera lista sale de `/capacity/summary`, no de un endpoint nuevo: ya
  ordena por holgura y conoce los umbrales del inquilino. Y filtra por
  organización y **no** por portafolio a propósito — una persona está
  sobreasignada por la suma de todos sus proyectos, no por los de una cartera.
- [x] **Bug de scoping cerrado**: los conteos de riesgos, cambios y AIDs se
  filtraban solo ante `organization_id`. Elegir un portafolio con «todas las
  organizaciones» —el estado más común del switcher del header— dejaba esos
  tres números contando la cartera entera al lado de un avance que sí era del
  portafolio.
- [x] Semáforo consolidado: cada dimensión toma **el peor color que aparece**
  en la cartera, con el conteo al lado. Un promedio de colores diría «amarillo»
  de veintidós verdes y un rojo, y eso esconde el rojo detrás de la mayoría; un
  umbral («rojo si más del 20 %») elige un número que nadie puede defender
  delante del proyecto que quedó fuera. El conteo no es opcional: sin él la
  regla vuelve todo rojo y la pantalla no sirve.
- [x] La tendencia es **semanal** y el rótulo lo dice. El mockup pide
  bi-semanal; la cadencia se cambia en US-213 y este gráfico lee lo que haya.

**Test Cases:**
- `TC-206.1` — `portfolio_id` sin `organization_id` filtra los riesgos severos
  (2 en una cartera, 1 en la otra, 3 sin filtro).
- `TC-206.2` — Un riesgo con `owner_actor_id` deja de contar como huérfano.
- `TC-206.3` — Consumido por moneda; y un portafolio vacío devuelve `null` en
  los dos avances, no `0` (DAT-09/DAT-12).
- `TC-206.4` — «Por programa» de un portafolio incluye el proyecto sin programa
  y la distribución suma el total.
- `TC-206.5` — Las dos listas ordenan, respetan el filtro de portafolio y
  recortan al límite; «top con atraso» excluye los proyectos sin calendario.

**Nota de alcance.** El desglose de la Fase 2 decía que esta US fusionaba
`/dashboard` y `/pmo`. El mockup dice lo contrario: su sidebar lleva
**Dashboard** y **Portafolio** como dos items del grupo Organización. Manda el
mockup. `/pmo` sigue siendo la vista de portafolio; lo que absorbe sus tablas es
la vista maestra de US-207.

**Estado de integración:** DONE (US-206).

---

### US-207 — La vista maestra del portafolio (control tower) ✅ (2026-08-20)

**Como** PMO Manager
**Quiero** una tabla de ancho completo con una fila por proyecto y el estado que
se revisa en seguimiento
**Para** contestar «¿qué pasa con ESTE proyecto?» de veintitrés proyectos a la
vez, que es la pregunta de la reunión.

De los mockups aprobados, artboard «Portafolio — Vista maestra». Vive en `/pmo`.

**Trece de las dieciséis columnas.** Proyecto · Organización · Portafolio ·
Programa · Tipo · Fase · Prio · Salud · Avance P/R · Presup. P/R · Fin ·
Riesgos · Issues · Últ. act. Las tres que faltan —«Próximo hito», «Reporte» y
«Completitud»— no existen como dato: son US-211 y US-210. El configurador de
columnas las nombra como pendientes en vez de callarlas, porque quien conoce el
mockup va a buscarlas y no encontrarlas sin explicación se lee como que se
perdieron.

**Criterios de aceptación:**
- [x] **Header y primera columna fijos.** Con dieciséis columnas se hace scroll
  horizontal siempre, y sin la columna del nombre pegada uno pierde de qué fila
  estaba leyendo. Es el fallo que convierte una tabla ancha en inútil. La celda
  fija lleva fondo propio: sin él se ve el texto de las columnas de debajo
  pasando por detrás.
- [x] **Columnas configurables, recordadas** en `localStorage`. Nadie mira las
  dieciséis: el PMO de riesgos quiere seis y el de presupuesto, otras seis.
  Volver a esconder cinco en cada visita es el motivo por el que alguien deja de
  usar la vista. La selección guardada se filtra contra las columnas que existen
  hoy, para que una renombrada no deje un hueco ni una casilla fantasma.
- [x] **XLSX de lo que se ve**, no de las dieciséis: exportar columnas que no
  están en pantalla entrega algo distinto de lo que se acordó mirar.
- [x] **Cuatro filtros** —portafolio, programa, fase, salud— en la URL, para que
  una vista filtrada se pueda enviar por chat. La organización no está: se elige
  en el header (US-205) y aquí sería el mismo control dos veces.
- [x] **La columna «Organización» solo cuando el header agrega.** `/pmo` está en
  `RUTAS_QUE_AGREGAN`, así que puede mostrar cuatro organizaciones a la vez y sin
  esa columna las filas son indistinguibles. Con una elegida repetiría el mismo
  valor veintitrés veces. Se enciende por contexto y se puede apagar a mano: es
  una preferencia de arranque, no un candado.
- [x] **Edición inline** en salud declarada y prioridad, y el «?» de la columna
  de salud abre el desglose del cálculo. Van como dos acciones separadas: si un
  click hiciera las dos, consultar el porqué cambiaría el dato.
- [x] El orden de la columna de fase sigue el ciclo de vida (`PHASE_ORDER`) y no
  el alfabeto; el de «Avance P/R» ordena por la **desviación** y no por el
  avance, porque la pregunta de la columna es «¿va atrasado?» y ordenar por el
  real pone arriba al que acaba de empezar.
- [x] `plan-vs-actual` devuelve las trece columnas. Los nombres de organización,
  portafolio y programa y los conteos de riesgos e issues salen de cinco
  consultas agrupadas, **no** de una por fila: la tabla tiene veintitrés filas
  hoy y ninguna razón para no tener doscientas.
- [x] La ruta **no** se renombró aunque el nombre quedó estrecho: el CSV de
  exportación se comparte por enlace, y romper los guardados no compra nada que
  el usuario note.

**Lo que se retiró, y a dónde fue:**
- La tabla «Plan vs Real» del tablero **es** esta vista: las mismas filas con
  seis columnas, sin configurador ni export, y con el orden roto en la mitad de
  sus cabeceras (los getters citaban `project_name` y `end_plan`, campos que el
  contrato nunca tuvo). El tablero ahora enlaza aquí, con sus filtros puestos.
- El heatmap, el treemap y las tendencias que `/pmo` dibujaba se fueron al
  tablero con US-206. Dos pantallas dibujando el mismo treemap es cómo se llega
  a que digan números distintos.
- Las tarjetas de organización de `/pmo` se van: su trabajo era navegar, y
  navegar ya no se hace ahí. No se pierde nada — `/admin/organizations` tiene las
  mismas tarjetas con su franja de salud (`listOrganizationPanels`), y el
  drill-down a `/pmo/organizations/[id]` sigue desde el heatmap del tablero.

**Lo que se conservó a propósito:** el status PMO en PDF y el reporte de salud en
XLSX son entregables que alguien manda por correo, y la matriz salud × dimensión
con su evaluación 5+1 (US-192) es la única superficie donde se declara salud sin
abrir cada proyecto. Van debajo de la tabla.

**Test Cases:**
- `TC-207.1` — La fila lleva los nombres de la jerarquía, y un proyecto sin
  portafolio ni programa devuelve `null` **sin desaparecer** de la tabla: es lo
  que un `JOIN` implícito se come sin fallar.
- `TC-207.2` — Riesgos e issues abiertos por proyecto; `resolved` no cuenta, y
  cero es `0` y no una clave ausente.
- `TC-207.3` — Tipo, fase, prioridad, fuente de salud y `updated_at`.
- `TC-207.4` — El scoping: filtrar por portafolio incluye los proyectos sin
  programa (regla de TC-201.1) y los conteos de un proyecto no se cuelan en otro.

**Estado de integración:** DONE (US-207).

---

### US-213 — La tendencia por corte de reporte y el historial de cortes ✅ (2026-08-20)

**Como** PMO Manager
**Quiero** ver la tendencia con la cadencia con la que reportamos, y la tabla de
los cortes
**Para** poder decir «al corte del 4 de agosto íbamos al 63 %» y que alguien lo
pueda comprobar.

De los mockups: «Tendencia bi-semanal — avance y salud» (artboard «Dashboard
ejecutivo») y «Historial de cortes (snapshot por periodo)» (artboard «Reportes —
organización»).

**Criterios de aceptación:**
- [x] **Se muestrea al leer, no al capturar.** Las instantáneas siguen siendo
  semanales (US-151, lunes 02:00 UTC) y `/trends` acepta `cadencia_dias` para
  devolver un punto por periodo. Bajar la frecuencia del job sería irreversible:
  el día que alguien quiera la evolución semanal de un mes concreto —la pregunta
  normal cuando algo se torció— no habría de dónde sacarla. Es lo que hace un
  almacén de series temporales: guardar fino, agregar en la consulta. **Sin
  migración.**
- [x] **El corte es el último punto del periodo, no el promedio.** Un corte es
  una foto del estado al cerrar: «al 4 de agosto la cartera iba al 63 %». El
  promedio de las dos semanas no es ningún estado real, y presentarlo como el
  corte convierte un dato verificable en uno que nadie puede reproducir abriendo
  la aplicación ese día.
- [x] **Los periodos se anclan en hoy**, no en el primer punto de la serie. Con
  el otro anclaje, añadir un punto viejo al histórico correría todos los límites
  y la serie entera cambiaría de forma sin que nada hubiera pasado en la cartera.
- [x] **El default es sin muestrear**, y a propósito: varias superficies consumen
  `/trends`, y cambiarles la forma de la serie por debajo sería cambiarles el
  gráfico sin que lo pidieran. `0` es «sin muestrear» explícito; más de 365 se
  rechaza, porque un año no es una cadencia de reporte.
- [x] La cadencia viaja con el branding del inquilino
  (`reporting_cadence_days`), por el mismo motivo que la moneda: la necesitan el
  rótulo del gráfico, el muestreo y el historial, y ninguno debería ir a pedirla
  aparte. La fuente es el ajuste de US-211.
- [x] El rótulo del gráfico dice la cadencia **real** («corte bi-semanal»,
  «corte semanal», «corte cada 17 días») y no la palabra escrita a mano, que se
  quedaría vieja el día que el inquilino la cambie.
- [x] **Historial de cortes**: la misma serie muestreada, en tabla, del corte más
  reciente al más viejo, con la variación respecto del anterior. Un gráfico
  contesta «¿va subiendo?» y una tabla contesta «¿cuánto era exactamente al
  corte del 4 de agosto?», que es la pregunta cuando alguien discute un número
  en comité. El corte más viejo no tiene variación: es «—» y no «0», que se
  leería como «no se movió».
- [x] `limites_del_periodo` nombra los periodos aunque alguno no tenga
  instantánea: un periodo sin datos es información —el job no corrió— y omitirlo
  hace que la tabla parezca continua cuando tiene un hueco.

**Test Cases:** `test_us213_cortes.py`
- `TC-213.1` (unit) — El corte es el último del periodo; un punto por periodo en
  orden cronológico; los periodos se anclan en hoy (añadir un punto viejo no
  mueve el corte reciente); cadencia cero devuelve la serie tal cual; los
  límites son contiguos y terminan hoy.
- `TC-213.2` — Sin `cadencia_dias` la serie viene completa; con 14 queda un
  punto por periodo y es el más reciente de cada uno; `0` explícito no muestrea;
  900 se rechaza con 422.
- `TC-213.3` — El branding trae la cadencia, por defecto y configurada.

**Estado de integración:** DONE (US-213).

---

### US-219 — Portfolio Board: los proyectos por estatus de reporte ✅ (2026-08-20)

**Como** PMO Manager
**Quiero** ver los proyectos apilados por si están reportados
**Para** saber qué persigo esta semana sin leer una columna de veintitrés filas.

Del artboard «Boards». Ruta `/pmo/board`.

**Por qué las columnas son el estatus de reporte.** Porque es el único eje que la
PMO puede accionar directamente: pedir un reporte es una acción con dueño y
fecha. La salud no se acciona —se explica—, y la fase avanza por sí sola.

**Criterios de aceptación:**
- [x] Cuatro columnas en orden de urgencia: **sin reporte · vencido · por vencer
  · al día**. `sin_reporte` va primero, antes que `vencido`, porque el hueco es
  más grande: un proyecto que nunca se reportó no incumplió una fecha, no ha
  empezado. En un onboarding es exactamente la columna que hay que vaciar.
- [x] **«Con decisiones pendientes» no es una columna**, aunque el mockup la
  nombre junto a las otras dos. Es otro eje: un proyecto al día también puede
  tener decisiones esperando, y un kanban no admite que una tarjeta esté en dos
  columnas a la vez —o se duplica, y entonces los conteos de columna dejan de
  sumar el total, o se elige una arbitrariamente y se esconde la otra mitad del
  dato—. Va como **marcador de la tarjeta**, con enlace al RAID.
- [x] **Los cerrados quedan fuera.** Un proyecto cerrado no se reporta: tenerlo
  en «sin reporte» para siempre convierte la columna en un cementerio y esconde
  los vivos.
- [x] **No se arrastra**, y se dice en la pantalla. El estatus es **derivado** —de
  la fecha del último reporte contra la cadencia—, así que mover una tarjeta a
  «al día» no significaría nada: el dato volvería a su sitio en el siguiente
  refresco. Para cambiarlo hay que generar el reporte, y a eso lleva el enlace de
  la tarjeta. Un board que acepta un arrastre que no persiste es peor que uno que
  no lo acepta.
- [x] Cada columna dice **qué hacer con su pila** («pasaron de su fecha: pide el
  reporte»). Un board sin verbo es una lista con bordes.
- [x] La tarjeta trae fase, salud, días de retraso, decisiones pendientes y
  próximo hito: sin eso hay que abrir el proyecto para saber si es urgente, que
  es lo que un board viene a evitar.
- [x] `GET /dashboard/portfolio-board` y **no** derivarlo de `plan-vs-actual`: la
  fila de la vista maestra trae dieciséis columnas y el board usa cinco. Pedir la
  tabla entera para agrupar por una columna es traer el acta, el presupuesto y la
  completitud de veintitrés proyectos para no pintarlos.
- [x] **Sin migración.** El estatus lo dejó consultable US-211 y las decisiones
  son `issues` de tipo `decision`.

**Test Cases:** `test_us219_portfolio_board.py`
- `TC-219.1` — Las cuatro columnas en orden de urgencia, con su etiqueta en
  español desde el servidor; cada proyecto cae en la suya.
- `TC-219.2` — Los cerrados quedan fuera del board y del total.
- `TC-219.3` — Las columnas suman el total: la comprobación que detecta que una
  tarjeta se duplicó o se perdió.
- `TC-219.4` — Un proyecto al día con dos decisiones abiertas **sigue** en «al
  día» con su marcador; la decisión resuelta y el issue no cuentan.
- `TC-219.5` — La tarjeta trae retraso, hito, salud y fase; el filtro de
  organización recorta.

**Lo que queda del artboard:** el **Project Board** (kanban de tareas por estado
dentro de un proyecto). Ahí sí se arrastra, porque `tasks.status` es un dato
declarado y no derivado, y `raid-kanban.tsx` ya tiene el mecanismo. Queda como
ENH sobre esta US.

**Estado de integración:** DONE (US-219, Portfolio Board).
