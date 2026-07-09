# Draft — Portafolio ejecutivo, recursos compartidos y capacidad (retro socio 2026-07-08)

> **Fase A — doc vivo.** Interpretación de la retro del socio + gap analysis
> contra el codebase actual (branch base `main` @ `df69b69`, migración head 0090).
> Se itera con el owner antes de convertirse en issues/epics.
> Incluye además: (2) plan de consistencia UI/UX de tablas y (3) evaluación
> de "memoria de proyecto" para IA.

---

## 1. Interpretación de la propuesta

La retro define 4 capas de producto y un modelo de datos de capacidad:

1. **Vista ejecutiva de portafolio** — tablero de todos los proyectos con
   semáforo global + score por dimensiones (cronograma, presupuesto, recursos,
   riesgos/issues, decisiones pendientes), filtros ejecutivos y heatmap.
2. **Drill-down de causas** — el semáforo explica *por qué* (hito atrasado,
   decisión pendiente, recurso saturado, dependencia, sobrepresupuesto) +
   tarjeta "foco PM" (qué pasó / impacto / responsable / siguiente acción /
   fecha compromiso).
3. **Recursos compartidos** — `resource_pool` maestro (capacidad nominal vs
   capacidad para proyectos, tipo/origen, seniority, escasez) +
   `project_resource_assignment` transaccional (FTE%, ventanas de fechas,
   rol/workstream/fase, status, criticidad).
4. **Gobernanza de capacidad** — saturación individual / por rol / por área en
   ventanas temporales (hoy, semana, 3 semanas, mes), vista de conflictos y
   alertas.

Principio rector del socio: **modelar capacidad consumible, no organigrama.**
La saturación vive en la relación recurso-proyecto, no en el recurso.

Nota del owner: la propuesta viene del punto de vista de un cliente
gestionando su propio portafolio (1 organización ≈ 1 portafolio/sombrilla);
es simétrico a E4 operando PMO-AAS multi-cliente. Aplica a toda la plataforma
rumbo a 1.0.

---

## 2. Qué existe hoy (estado real del codebase)

### 2.1 Jerarquía organizacional — ya cubierta casi completa

```
tenants → organizations → (business_units → departments) → programs → projects
```

- `Project` ya tiene: `organization_id`, `program_id?`, `business_unit_id?`,
  `department_id?`, `type`, `priority`, `phase`, `pm_id`, `sponsor` (texto
  libre), `budget` + `actual_budget`, `progress`, `health_status`,
  `status_rag` (override manual del PM, ENH-101), `manually_edited_fields`.
- **No existe entidad `Portfolio`** — y no hace falta crearla: la
  `Organization` cumple ese rol (decisión implícita del producto; el owner
  la confirma en la retro: "una organización es como un portafolio").
- `BusinessUnit`/`Department` ya dan la dimensión "unidad de negocio" que la
  propuesta pide como filtro.

### 2.2 Áreas / actores (EP017) — el 60% del resource_pool ya existe

- `areas`: catálogo **tenant-level con scope opcional por organización**
  (`organization_id` nullable, BUG-061). Sin jerarquía de subáreas.
- `teams`: equipo operativo bajo un área.
- `actors`: persona tenant-level. Tiene `company`, `job_title`,
  `manager_actor_id`, `area_id`/`team_id`, `user_id?`, `email`, flags
  `auto_created/verified`. **NO tiene**: capacidad (nominal ni para
  proyectos), tipo/origen de recurso, seniority, escasez, skills, ubicación,
  costo, flags shared/key.
- `area_assignments` (US-103): cascada de visibilidad de áreas a
  org/programa/proyecto — patrón reutilizable.
- `project_participations` (US-114): **es el embrión exacto de
  `project_resource_assignment`** — ya tiene `project_id`, `actor_id`,
  `operational_team_id`, `project_role_id`, `functional_area_id`,
  `is_area_lead`, `is_primary`, `start_date`, `end_date`, `is_active`.
  **NO tiene**: `allocation_pct` (FTE%), workstream, fase, tipo de
  asignación, status (tentativa/activa/cerrada), criticidad, aprobación,
  source_type.
- `project_roles`: catálogo tenant de roles (PM, SME…) — base del
  `role_catalog` propuesto.
- Deuda EP017 pendiente que interactúa con esto: ENH-109 (PersonPicker),
  US-119 (drop columnas legacy `actors.team_id`, `tasks/risks/issues.area_id`),
  US-133/134 (RBAC migra de `project_members` a `project_participations`).

### 2.3 Salud / semáforo — hoy es manual con patrón de override ya sentado

- `Project.health_status` (green/yellow/red): campo editable, default green.
- `Project.status_rag` (ENH-101): RAG **declarado por el PM**; si está
  seteado prevalece en UI/reportes. Con audit log dedicado
  (`project.status_rag.set`).
- **No existe motor de reglas** que calcule salud por dimensiones. El
  "cómputo" hoy es el valor manual de `health_status`.
- Señales que YA existen para calcular dimensiones automáticas:
  - **Cronograma**: `tasks.end_date/closed_at/status` + tags
    Atrasada/Completada-con-atraso (US-171/177), hitos (`is_milestone`),
    `milestones_due_7/14/30` en snapshots, rollup WBS de avance (ENH-155).
  - **Presupuesto**: `projects.budget` vs `actual_budget` (ya en
    `metric_snapshots.budget_plan/actual`).
  - **Riesgos/issues**: `risks.severity` (P×I), `open_risks/severe_risks/
    open_issues` en snapshots, estados RAID 4-fases con `on_hold` (US-179).
  - **Decisiones pendientes**: `issues.type='decision'` con status abierto —
    la entidad ya existe.
  - **Recursos**: ÚNICO gap real — `task_load_thresholds` (tenant setting
    green_max/amber_max) solo cuenta tareas por responsable; no hay FTE%.
- `metric_snapshots` (US-151): foto semanal por scope
  (tenant/org/program/project) con salud, avance, presupuesto, RAID,
  hitos + campo `extras` JSON para métricas nuevas **sin migración**.
- **En la UI**: el semáforo se edita en 2 lugares — `HealthCard` en el
  detalle del proyecto (3 pills, cambio instantáneo, **sin justificación**)
  y el select "Salud" en `project-form.tsx`. **`status_rag` es un campo
  fantasma**: existe en modelo/API/audit-log pero NO tiene ningún control
  de edición en el frontend.

### 2.3-bis Vistas ejecutivas que ya existen (frontend)

- **N1** `pmo/page.tsx`: cards por organización con conteo 🟢/🟡/🔴 +
  **Heatmap Organización × Salud** + **Treemap presupuesto × salud**
  (org→programa→proyecto) + sparklines 12 semanas — todo en
  `components/dashboard-charts.tsx` (Pie, Bars, Gauge, TrendLines,
  RiskMatrix, Heatmap, Treemap). PDF de status portafolio.
- **N2 org/programa**: KPIs, pie de salud, RiskMatrix P×I, gauges de
  avance/presupuesto, riesgos top, tabla de proyectos con dot de salud,
  tab Reportes (`ScopedReportsPanel`).
- **Listado `/pmo/projects`**: filtros URL-sync (búsqueda libre, org,
  "sólo míos", fase, tipo, salud) + vista Lista/Tablero (kanban por fase).
  La API soporta filtros que la UI no expone (`priority_min/max`,
  `program_id`, `no_program`). **No hay filtro por PM, sponsor (texto
  libre, no entidad) ni unidad de negocio** — aunque BU/departamento
  existen en el modelo.
- **No existe**: drill-down de causas, score por dimensiones, vista de
  carga por PM ("cuántos proyectos lleva y cuántos en rojo"), ni nada de
  capacidad/recursos en la UI.

### 2.4 Lo que NO existe (gaps duros)

1. Capacidad en el recurso: `nominal_capacity_pct` / `project_capacity_pct`.
2. `allocation_pct` (FTE%) y metadata de asignación en participations.
3. Clasificación del recurso: `resource_type` (cliente_negocio/cliente_it/
   e4_pmo/e4_tecnologia/vendor_externo), `resource_origin`, `seniority`,
   `scarcity_level`, `skills`, `key/shared` flags.
4. Jerarquía área→subárea (hoy `areas` es plano; `teams` es otra dimensión).
5. Motor de saturación por ventana temporal + vistas
   `resource_capacity_summary` / `resource_conflict_view`.
6. Alertas de capacidad (el sistema de notificaciones existe, pero no hay
   triggers de carga).
7. Score de salud por dimensiones + motor de reglas + heatmap + drill-down
   de causas + tarjeta "foco PM".
8. Calendarios de disponibilidad (propuesta los menciona; se difieren).

---

## 3. Decisión central de diseño: extender, no duplicar

**Recomendación: NO crear tablas `resource_pool` ni
`project_resource_assignment` nuevas. Extender `actors` y
`project_participations`.**

Razones:
- `actors` ya es el catálogo maestro de personas del tenant y TODO el
  producto ya apunta a él (`tasks.assignee_actor_id`,
  `risks/issues/lessons.owner_actor_id`, minutas, matcher IA, directorio).
  Una tabla paralela duplicaría identidad de personas — exactamente el
  anti-patrón que la retro quiere evitar ("Eli vive una sola vez").
- `project_participations` ya modela la relación recurso-proyecto con
  ventanas de fechas y N filas por (proyecto, actor) — la regla del socio
  ("si cambia FTE/fase se crea otra asignación") es compatible tal cual.
- El costo de extender es 2 migraciones aditivas; el costo de duplicar es
  sincronizar dos fuentes de verdad para siempre.

Mapeo propuesta → modelo real:

| Propuesta socio | Se materializa en |
|---|---|
| `resource_pool` | `actors` + columnas nuevas |
| `tenant_id` / `organization_id` | `actors.tenant_id` ya existe; **agregar `actors.organization_id?`** (nullable = pool tenant-global, mismo patrón que `areas`) |
| `resource_type` / `resource_origin` | `actors.resource_type` (enum). `origin` es derivable del type — un solo enum basta (decisión owner pendiente) |
| `macro_area` / `sub_area` | `areas.parent_area_id?` (jerarquía 2 niveles) — actor apunta a la subárea; macroárea derivada |
| `base_role` | `actors.job_title` (ya existe) |
| `portfolio_function` | `actors.portfolio_function` (enum normalizado) |
| `seniority`, `scarcity_level`, `location`, `skills_tags`, `fte_cost_rate` | columnas nuevas en `actors` |
| `nominal_capacity_pct` / `project_capacity_pct` | columnas nuevas en `actors` (Numeric(5,2), defaults 100/100) |
| `shared_resource_flag` / `key_resource_flag` | columnas nuevas en `actors` (bool) |
| `manager_owner` | `actors.manager_actor_id` (ya existe) |
| `company_name` | `actors.company` (ya existe) |
| `active_flag` | `actors.is_active` (ya existe) |
| `calendar_id` | **diferido** (v2; el gap de calendarios no bloquea saturación v1) |
| `project_resource_assignment` | `project_participations` + columnas nuevas |
| `allocation_pct` | `project_participations.allocation_pct` Numeric(5,2) nullable (NULL = sin dato, no cuenta para saturación) |
| `workstream` | `functional_area_id` ya cubre "área en el proyecto"; `workstream` texto libre opcional (decisión owner) |
| `project_phase` | `project_participations.phase?` (texto, opcional) |
| `assignment_type` | enum nuevo (directa/advisory/backup/shared_service/steerco_only) |
| `status` | enum nuevo (tentativa/activa/cerrada/cancelada); hoy `is_active` bool — backfill activa/cerrada |
| `critical_assignment_flag` / `primary_assignment_flag` | `is_primary` ya existe; agregar `is_critical` |
| `approved_by/date`, `source_type` | columnas nuevas (gobernanza; opcional v1) |

### Saturación (servicio nuevo, sin tablas)

`app/services/capacity.py`:
- `resource_capacity_summary(scope, window)` — por actor: suma
  `allocation_pct` de participations activas que intersectan la ventana vs
  `project_capacity_pct` → gap + color. Query on-the-fly (los volúmenes son
  chicos: cientos de actores, no miles).
- Agregación por `portfolio_function` (rol) y por área/subárea.
- `resource_conflict_view(scope)` — actores con gap < 0: proyectos en
  choque, semanas afectadas (intersección de ventanas), criticidad.
- Ventanas: hoy / semana / 3 semanas / mes — parámetro `window`.
- Histórico: métricas agregadas de capacidad entran a
  `metric_snapshots.extras` (sin migración).

### Reglas de negocio (las 6 del socio) — todas implementables

1. N asignaciones activas por recurso → ya soportado (N participations).
2. Comparar vs `project_capacity_pct`, no vs 100 → servicio.
3. `is_critical` pesa más en alertas → servicio.
4. Tentativas se muestran aparte → `status='tentativa'` excluida del cálculo
   base, visible como "demanda tentativa".
5. Vencidas no cuentan → filtro por ventana de fechas.
6. `shared_resource_flag=false` en >1 proyecto activo → warning en el write
   + alerta.

---

## 4. Salud híbrida (pregunta H del socio) — recomendación

**Híbrido, confirmando la recomendación del socio.** La plataforma ya tiene
la mitad del patrón: `status_rag` es el override manual declarado, con
auditoría. Falta el lado automático:

- **Nuevo servicio `project_health.py`**: calcula un RAG por dimensión con
  reglas sobre datos existentes:
  - `schedule`: % tareas atrasadas + hitos vencidos/próximos.
  - `budget`: `actual_budget / budget` (si no hay budget → N/A, no penaliza).
  - `risks`: riesgos severos abiertos (severity ≥ umbral) + issues abiertos.
  - `decisions`: `issues.type='decision'` abiertas > X días.
  - `resources`: recursos clave del proyecto sobreasignados (depende de
    Fase Capacidad; hasta entonces N/A).
  - Umbrales por tenant en `tenant.settings` (patrón `task_load_thresholds`).
- **Semáforo efectivo** = `status_rag` (manual) si está seteado; si no, el
  peor color de las dimensiones calculadas. Cuando difieren, la UI muestra
  ambos: "PM declara Verde / cálculo dice Amarillo" — eso ES la conversación
  de gobernanza que la PMO quiere provocar.
- `health_status` (campo actual) queda como el valor computado persistido
  (lo escribe el servicio, deja de ser editable a mano) — evita romper
  snapshots/reportes que ya lo leen.

---

## 5. Fasaje propuesto (bloques)

> Orden pensado para que cada bloque entregue valor solo y el siguiente se
> monte encima. Estimaciones gruesas por bloque.

**Bloque 1 — Salud por dimensiones + drill-down (sin capacidad) · ~3-4 días**
- Servicio `project_health.py` + endpoint `GET /projects/{id}/health-detail`.
- Dimensiones: cronograma, presupuesto, riesgos/issues, decisiones (recursos
  queda N/A hasta Bloque 2/3).
- UI: score por dimensiones en dashboard N1/N2 + panel drill-down "por qué"
  + tarjeta foco PM (mapea a: issue/riesgo/hito top + owner_actor +
  committed_date/due_date — todos campos existentes).
- Heatmap de portafolio (proyectos × dimensiones) en dashboard N1.
- Umbrales configurables en admin tenant.
- Migración: 0 (solo lectura de datos existentes). Riesgo bajo.

**Bloque 2 — Pool de recursos con capacidad · ~2-3 días**
- Migración A: columnas nuevas en `actors` (+`organization_id`,
  capacidades, tipo, seniority, escasez, skills, flags) + `areas.parent_area_id`.
- CRUD extendido en `/actors` + admin catálogo (US-170 UI se extiende).
- Import CSV/XLSX del pool (opcional pero recomendado para onboarding
  de un cliente con 35 proyectos).

**Bloque 3 — Asignaciones con FTE% + saturación · ~3-4 días**
- Migración B: columnas nuevas en `project_participations`
  (`allocation_pct`, `assignment_type`, `status`, `is_critical`, `phase`,
  aprobación/source opcionales).
- Servicio `capacity.py` (summary + conflictos + ventanas).
- Endpoints: `GET /capacity/summary`, `GET /capacity/conflicts`,
  `GET /actors/{id}/load`, `GET /projects/{id}/resource-load`.
- UI: vistas por persona / por rol / por área + vista de conflictos.
  Navegación: nueva sección "Recursos" en sidebar PMO (nivel portafolio) +
  tab de carga en el directorio del proyecto.
- Dimensión "recursos" del health se activa.

**Bloque 4 — Alertas de capacidad · ~1-2 días**
- Reglas: >100% asignado, pico en 2-4 semanas, recurso clave en ≥3 proyectos
  amarillos/rojos, proyecto dependiente de 1 especialista, no-shared en >1
  proyecto.
- Se monta en el sistema de notificaciones existente + panel en dashboard.

**Bloque 5 — UI/UX consistencia de tablas · (ver §6)**

**Bloque 6 — Memoria de proyecto para IA · (ver §7)**

Total estimado Bloques 1-4: ~2 semanas de trabajo efectivo.

---

## 6. Consistencia UI/UX de tablas (fase 2 del owner)

### Estado actual: 3 familias de tabla conviviendo

| Familia | Dónde | Features | Le falta |
|---|---|---|---|
| **Plan** (tabla manual, ~2525 líneas) | `projects/[id]/plan/page.tsx` | Configurador de columnas (`ColumnsDropdown`/`ColVis`), edición inline, chips de atraso con contadores, agrupación WBS/área, acciones en header, export/import XLSX, Gantt | Sort por columna (único sin `SortableTh`) |
| **SortableTh + useSortableRows** (compartido, 8+ páginas) | RAID proyecto/portafolio, cambios/minutas/requests portafolio, admin users/audit-logs, directorio | Sort consistente; RAID proyecto además: inline edit (3 celdas compartidas), kanban, matriz P×I, filtros, export por tipo | Configurador de columnas; inline edit fuera de RAID proyecto |
| **ModuleShell** (wrapper CRUD declarativo) | Cambios/Lecciones/Minutas de proyecto, documents/legacy | Tabla + modal "nuevo" + preview | Sort, filtros, export, inline edit — todo |

Divergencias detectadas:
- Celdas inline compartidas (`inline-select-cell.tsx`: `InlineSelectCell`/
  `InlineTextCell`/`InlineDateCell`) solo las usan Plan y RAID proyecto; y
  Plan usa inputs de fecha propios + un `InlineProgressCell` local en vez
  de las compartidas.
- **Kanban duplicado**: `RaidKanban` (compartido) solo lo usa RAID
  proyecto; RAID portafolio reimplementa su propio board.
- Lecciones es la tabla más pobre (sin sort/filtros/export/inline) y no
  tiene vista portafolio (cambios/minutas/raid sí).
- Minutas exporta solo por fila; RAID por tipo; Plan todo — 3 patrones de
  export distintos.

### Patrón estándar propuesto ("tabla PMO-AAS")

Combinar lo mejor de las 3 familias — **extracción incremental, NO
refactor big-bang del plan page** (frágil, 2525 líneas):

1. **Extraer de Plan** el configurador de columnas como
   `components/ui/columns-dropdown.tsx` genérico (Plan primero lo consume,
   luego el resto).
2. **Evolucionar `ModuleShell`** (no reemplazarlo) para aceptar
   `sortCtrl` (useSortableRows), `colVis`, celdas inline y menú export —
   los módulos CRUD simples heredan el estándar gratis.
3. **Estándar por tabla**: sort (`SortableTh`) + configurador de columnas
   + edición inline on-click con update optimista (patrón ENH-173) + chips
   de estado con tokens DS + acciones en header + export menú + toggle
   "mostrar finalizados" donde aplique.

### Orden de replicación sugerido (esfuerzo)

| # | Tabla | Delta principal | Esfuerzo |
|---|---|---|---|
| 1 | Lecciones (proyecto) | sort + filtros + inline (owner/categoría/fase) vía ModuleShell evolucionado | M |
| 2 | Cambios (proyecto) | ídem + chips estado + toggle finalizados | M |
| 3 | Minutas (proyecto) | sort + filtros; export ya existe por fila | S |
| 4 | RAID portafolio | inline edit + reusar `RaidKanban` (matar board duplicado) | M |
| 5 | Cambios/Minutas portafolio | inline edit ligero + export | S |
| 6 | Plan | adoptar `ColumnsDropdown` extraído + celdas de fecha compartidas | S |

Quick win paralelo (sin diseño): exponer en `/pmo/projects` los filtros
que la API ya soporta (`priority_min/max`, `program_id`, `no_program`).

---

## 7. Memoria de proyecto para IA (nuevo requerimiento del owner)

### Estado actual (verificado en código)

- Prompts **100% hardcoded** (`services/ai/prompts.py` + inline en
  `reports.py:904`, `report_builder_chat.py:91`, `assistant.py:29`). Sin
  configuración por tenant ni proyecto. Cambiarlos = PR + deploy.
- `MINUTE_SYSTEM` no recibe NINGÚN contexto del proyecto — ni nombre,
  ni descripción, ni minutas previas, ni glosario.
- El generador de reportes (`/reports/ai-generate`) arma bloques
  `<DATOS_DEL_PROYECTO>` / `<INSTRUCCIONES_DEL_USUARIO>` pero **no incluye
  `project.description`** (bug menor: `build_avance_context` lo trae y el
  endpoint no lo copia) y las `free_notes` son efímeras por-request.
- `AIReportTemplate` persiste config estructural del wizard, no contexto
  narrativo.
- No existe tabla ni campo tipo `project_memory` / glosario / reglas.

### Propuesta: `project_ai_context` (memoria curada + acumulativa)

- **Tabla nueva** `project_ai_context` (1:1 con project, extensible a
  scope org/tenant después): `context_md` (texto curado por el PM:
  objetivo, glosario, siglas, reglas de negocio, tono), `auto_summary_md`
  (resumen acumulativo mantenido por IA), `instructions_md` (instrucciones
  permanentes para generación: formato, idioma, qué destacar),
  `updated_by`, timestamps, versionado simple (JSON history o tabla hija).
- **Inyección**: bloque `<CONTEXTO_DEL_PROYECTO>` antepuesto en
  `_run_minute` (worker) y en `ai-generate`/`_run_report` — el patrón de
  bloques ya existe en `reports.py`.
- **Alimentación**: al aprobar una minuta, job asíncrono (patrón `ai_jobs`)
  actualiza `auto_summary_md` (resumen incremental: decisiones, acuerdos,
  actores, temas recurrentes). El PM puede editar/podar.
- **Fix de paso**: incluir `project.description` en el prompt de reportes;
  corregir `docs/ai/prompts-catalog.md` (afirma "sin chunking" pero
  `chunk_text` existe y se usa).
- Esto es un mini-epic propio (EP008 extensión o EP021 nuevo — decisión
  owner). Estimación: ~3-4 días MVP (tabla + UI de edición + inyección en
  minutas y reportes + resumen incremental).

---

## 8. Impacto / blast radius

- **Migraciones**: 2 aditivas (actors + participations) + 1 tabla nueva
  (project_ai_context) + backfills triviales. Sin drops. Compatible con la
  deuda EP017 (US-119 sigue igual de viable; ENH-109 PersonPicker se vuelve
  MÁS valioso porque el picker mostrará carga).
- **RBAC/visibilidad**: sin cambios de modelo — `user_scope_assignment` y
  `area_visibility` filtran las vistas de capacidad igual que hoy filtran
  proyectos.
- **Snapshots/reportes**: `metric_snapshots.extras` absorbe métricas de
  capacidad sin migración; reportes S-xx y dashboards N1/N2 se extienden,
  no se rompen. `health_status` mantiene su semántica de lectura.
- **Imports de plan**: sin impacto (assignee sigue siendo actor).
- **Riesgo principal**: calidad de datos — la saturación solo sirve si los
  PMs capturan `allocation_pct`. Mitigación: defaults visibles ("sin FTE
  capturado"), import masivo, y que la vista de conflictos marque
  explícitamente cobertura de datos ("X% de participations con FTE").

---

## 9. Preguntas abiertas para el owner — ✅ RESUELTAS (owner 2026-07-08)

> 1. Solo `resource_type` (sin `resource_origin`). 2. Subárea = `teams`
> existentes (no `parent_area_id`). 3. `functional_area_id` basta (sin
> workstream). 4. Gobernanza de asignaciones diferida. 5. Salud primero;
> los cambios posteriores que impacten salud deben considerarla. 6. Memoria
> IA = extensión de EP008 + robustecer capacidades IA (menos prompts
> hardcodeados). 7. Sí: persistir desglose de dimensiones en snapshots.
> 8. Justificación al declarar SÍ, pero **UN solo semáforo** (unificar
> `health_status`+`status_rag`; estilo avance derivado ENH-155). 9. Plan
> sin sort, solo chips de color de status; Cambios y Lecciones heredan la
> estructura RAID (nivel proyecto, export propio).
>
> Rename "Organizaciones"→"Portafolios": pendiente decisión owner
> (recomendación: solo label de UI, no schema).

### Preguntas originales (referencia)

1. **¿`resource_type` + `resource_origin` como 2 campos o 1 enum?**
   Recomendación: solo `resource_type` (5 valores); origin derivable.
2. **¿Subáreas vía `areas.parent_area_id` (recomendado) o reutilizar
   `teams` como subárea?** Recomendación: parent_area_id; teams sigue
   siendo equipo operativo (otra dimensión, EP017 lo separó a propósito).
3. **¿`workstream` texto libre en la asignación o basta
   `functional_area_id`?** Recomendación: empezar con functional_area_id,
   agregar workstream solo si un cliente lo pide.
4. **¿Gobernanza de asignaciones (approved_by/approved_date) en v1?**
   Recomendación: diferir — DEC-020 definió plataforma sin aprobaciones
   jerárquicas; capturar `source_type` sí (barato y útil para el matcher).
5. **Orden de bloques**: ¿Salud primero (valor ejecutivo inmediato, 0
   migraciones) o Recursos primero (el gap duro)? Recomendación: Salud
   (Bloque 1) primero.
6. **Memoria IA**: ¿EP nuevo (EP021) o extensión de EP008?
7. **Semáforo por dimensiones**: ¿se persiste el desglose (snapshot semanal
   en `extras`) para tendencias? Recomendación: sí, es gratis.
8. **UX del RAG declarado**: al construir la UI de `status_rag` (hoy campo
   fantasma), ¿el PM debe capturar justificación obligatoria al declarar
   amarillo/rojo? Recomendación: sí — alimenta directo la tarjeta "foco PM".
9. **Tablas**: ¿Lecciones gana vista portafolio (hoy no existe)? ¿Cambios/
   Lecciones ganan export propio? (ENH-152 los excluyó del XLSX RAID por
   decisión owner 2026-06-05 — el backlog ya tiene el follow-up).

---

**Última actualización:** 2026-07-08 · Sesión branch `claude/pmo-portfolio-architecture-6hbuen`

---

## 10. Fase 2 — Organigramas con utilización de recursos (propuesta 2026-07-09)

**Decisiones owner:** ENH-190 label Organización/Portafolio configurable
por tenant (`settings.org_label`). Organigramas con %FTE en 3 niveles.

### Diseño propuesto

Un solo servicio `organigrama_export.py` parametrizado por scope
(`project | program | organization | tenant`), reutilizando
`capacity._load_assignments` con ventana mensual:

- **Hoja 1 "Organigrama"** (todos los niveles): recursos ACTIVOS en el
  scope — nombre, rol/función, área/equipo, manager, tipo de recurso,
  %FTE sumado dentro del scope, %FTE total (todos sus proyectos del
  tenant), capacidad para proyectos, flags clave/compartido.
- **Hoja 2 "Uso mensual"** (programa, organización/portafolio y tenant;
  opcional en proyecto): matriz Recurso × Mes (12 meses rolling) — % de
  uso por mes = suma de allocation_pct de asignaciones activas que
  intersectan el mes, sumado por los proyectos del scope + columna
  "Total tenant". **Formato condicional: fill amarillo ≥80%, rojo
  >100%** + columna "Meses en alerta".
- **Tenants con org_label=portfolios**: los recursos son reutilizables a
  nivel tenant → botón "Organigrama global" en /pmo/resources (scope
  tenant) además del de cada portafolio.

Endpoints: `GET /projects/{id}/organigrama/export` (extender el
existente con FTE), `GET /programs/{id}/organigrama/export`,
`GET /organizations/{id}/organigrama/export`, `GET /capacity/organigrama/export`
(tenant/global).

**Dónde viven (UX):** botón "Organigrama (XLSX)" junto al botón "Status
(PDF)" existente en los headers de `/pmo/organizations/[id]` y
`/pmo/programs/[id]`; en proyecto ya existe (gana la hoja FTE); global en
`/pmo/resources`. Deuda propuesta: unificar en menú "Descargas ▾" por
nivel.

### IDs propuestos
- **ENH-190** — label configurable (en ejecución).
- **US-186** — BE: servicio organigrama multi-scope + uso mensual + alertas 80/100 + 4 endpoints.
- **US-187** — UX: botones por nivel + organigrama global + hoja FTE en proyecto + navigation/epics.
