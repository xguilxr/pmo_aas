---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# EP005 — Gestión de Proyectos

| Campo | Valor |
|---|---|
| **ID** | EP005 |
| **Prioridad** | Alta |
| **Dependencias** | EP001, EP002, EP003 |
| **Módulo** | `projects` |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |
| **Última actualización** | 2026-08-19 — US-202: vocabulario de fases en español y `type` como enum (ADR-038) |

## Objetivo de negocio

El proyecto sigue un ciclo de vida completo: creación (manual o desde solicitud), edición, cambio de fase, vista detalle rica con toolbar a módulos transversales, y listado con filtros potentes.

---

## User Stories

### US-024 — Matriz de proyectos con filtros

**Como** PM / PMO Manager
**Quiero** ver todos los proyectos visibles con filtros avanzados
**Para** navegar rápido.

**Filtros obligatorios:**

| Filtro | Tipo |
|---|---|
| Fase (toggle chips) | `preparacion`/`ejecucion`/`hypercare`/`cerrado`/`cancelado` multiselect |
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
| `type` | ✅ — enum `transformacion \| operacion \| innovacion \| bau` (US-202) |
| `priority` (1-5) | ✅ |
| `organization_id` | ✅ |
| `program_id` | opcional |
| `phase` (default: `preparacion`) | ✅ |
| `pm_id` | ✅ |
| `sponsor` | opcional |
| `start_date`, `end_date` | opcional en preparación |
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
- [ ] **(2026-07-09, US-181):** el form de edición **ya no edita salud**.
  La salud tiene un único flujo de declaración (ver US-180/US-181 abajo);
  `PATCH /projects/{id}` deja de aceptar `health_status`/`status_rag`.

**Test Cases:**
- `TC-074` (integration) — Editar `folio` → 400 (read-only).
- `TC-075` (integration) — Diff en audit_log.

---

### US-180 / US-181 — Salud única híbrida por dimensiones (2026-07-09)

**Como** PM / PMO Manager
**Quiero** un solo semáforo de salud del proyecto, calculado por reglas pero
declarable manualmente con razón
**Para** dejar de mantener dos indicadores de salud paralelos y entender
**por qué** un proyecto está en amarillo/rojo.

**US-180 (`0f96dec`) — motor de reglas (backend):**
- **Un solo campo** `health_status` (verde/amarillo/rojo). Se **elimina**
  `status_rag` (ENH-101): quedaba redundante con `health_status` y
  confundía al PM sobre cuál era "la salud real". Migración `0091`
  (`20260708_0091_health_unified.py`) agrega `health_source`
  (`auto`|`manual`) + `health_reason`, absorbe `status_rag` como el caso
  `health_source='manual'` y **dropea la columna** `status_rag`.
- `services/project_health.py`: motor de reglas por **dimensión** —
  cronograma, presupuesto, riesgos/issues, decisiones y recursos (esta
  última activada por US-183 en EP017). Umbrales configurables **por
  tenant** (`tenants.settings.health_thresholds`), **las cinco desde la
  misma llave** desde D-4: recursos se configuraba en
  `capacity_thresholds` y dos de sus reglas estaban escritas a fuego.
  El color global = la peor dimensión.
- **El presupuesto se mide contra el avance, no contra sí mismo** (D-4,
  2026-08-05). La dimensión calcula un **índice de consumo**:
  `(gastado/presupuesto) ÷ (avance/100)`, el inverso del CPI de valor
  ganado. Vale 1,0 cuando el gasto va al ritmo del avance. Antes
  comparaba el ratio crudo: un proyecto con el **85 % del presupuesto
  gastado y el 10 % de avance salía verde**. Sin avance la dimensión
  queda **sin color**, igual que sin presupuesto configurado: dividir por
  cero no es «rojo», es «todavía no se puede decir». La función bulk
  (`refresh_health_bulk`) recalcula en batch desde snapshots/dashboards
  sin N+1.
- `health_source='auto'`: el color lo calcula el motor de reglas en cada
  refresh. `health_source='manual'`: el PM hizo override y el color queda
  fijo hasta que se vuelve a automático (recalcula al instante).
- **Override manual del PM** (`PATCH /projects/{id}/health`): declarar
  amarillo o rojo **requiere razón** (`health_reason` obligatorio en esos
  dos colores). Volver a automático (`health_source=auto`) dispara
  recálculo inmediato con el motor de reglas.
- **`GET /projects/{id}/health-detail`**: desglose por dimensión + causas
  detectadas por el motor + tarjetas "Foco PM" (qué atender, quién,
  próxima acción).
- Snapshot semanal (`services/analytics/snapshots.py`) refresca la salud
  auto de **todos** los proyectos del tenant antes de contar, y persiste
  el desglose de dimensiones en `metric_snapshots.extras.health_dimensions`
  (scope `project`) para tendencias.

**US-181 (`0c0ad7d`) — UI (frontend):**
- `components/health-panel.tsx`: `HealthStatusCard` (semáforo + fuente +
  mini-dots por dimensión), `HealthDeclareModal` (razón obligatoria en
  amarillo/rojo + botón "volver a automática"), `HealthWhyPanel`
  (dimensiones con causas + tarjetas Foco PM) y `HealthDimensionMatrix`
  (heatmap Proyecto × Dimensión — ver también EP004).
- Detalle del proyecto: la tarjeta de 3 pills vieja se reemplaza por
  `HealthStatusCard` + panel "¿Por qué?"; `health-detail` refresca el
  color auto al abrir la página. Actividad del proyecto muestra "Salud
  declarada" cuando hay override manual.
- **Form de edición del proyecto ya no tiene campo de salud** (ver nota
  en US-027). `status_rag` / `STATUS_RAG_LABEL` eliminados del frontend.

**Test Cases:**
- `test_us180_project_health.py` — 9 TC del motor de reglas + override ✅
- Suite dashboard (39 TC) verde tras el cambio de UI.

**Estado de integración:** DONE (US-180/US-181).

**Batch feedback 16-jul (2026-07-18):**
Evaluaciones de salud manual con historial (US-191/US-192, ver también EP004):
- Tabla `project_health_evaluations` (migración 0096) registra evaluaciones 5+1 (5 dimensiones + overall). Nota obligatoria en amarillo/rojo. Convive con motor automático sin reemplazarlo.
- Modal `HealthEvaluationModal` en `/pmo/projects/[id]` detail + botón de evaluación masiva en heatmap del portafolio.

---

### US-028 — Cambiar fase del proyecto

**Como** PMO Manager
**Quiero** mover un proyecto de fase
**Para** reflejar avance real.

**Transiciones válidas:**

```
preparacion → ejecucion → hypercare → cerrado
                       ↘          ↘
        cualquiera de las tres → cancelado
```

El vocabulario está en español desde US-202 (**ADR-038**): `planning →
preparacion`, `execution → ejecucion`, `closed → cerrado`, `cancelled →
cancelado`. El API sigue aceptando los nombres viejos a la entrada durante una
ventana de compatibilidad y devuelve siempre el canónico. El catálogo, el orden y
este grafo viven en `app/dominio/proyecto.py` — un solo sitio.

`hypercare` **no** se tradujo: no tiene traducción que no sea peor, y ADR-019 ya
lo renombró una vez desde `support` (esa ventana sigue abierta, con su propio
contador).

**`cancelado` es un final distinto de `cerrado`** (ADR-022). Antes, un proyecto
cortado a mitad se registraba como cerrado y quedaba indistinguible de uno que
llegó al final: contaba como entregado en toda métrica de éxito, y sus lecciones
se mezclaban con las de los que cumplieron.

Los dos son **terminales** y ninguno cuenta como fase activa. `cerrado` no lleva
a `cancelado`: un proyecto que llegó al final ya tuvo su final.

**«Solicitud» no es fase del proyecto** (US-202): vive en
`project_requests.status`, y el proyecto nace en `preparacion`. Meterla como fase
obligaría a que todo proyecto pasara por ella, incluido el que se captura directo
o el que entra por importación masiva.

**Criterios de aceptación:**
- [ ] `POST /api/v1/projects/{id}/phase/change` con `{new_phase, comment?}`.
- [ ] Transición inválida → 409 `STATE_TRANSITION`.
- [ ] Al pasar a `ejecucion`: `start_date` obligatoria si null.
- [ ] Al pasar a `cerrado`: bloquea edición (readonly), excepto lecciones aprendidas.
- [ ] Audita `project.phase_change` con from→to.

**Test Cases:**
- `TC-076` (integration) — Transición inválida `cerrado→ejecucion` → 409.
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

### US-202 — Vocabulario de fases en español y tipo como enum ✅

**Como** PMO
**Quiero** que las fases y los tipos se llamen como los llamamos al hablar
**Para** no tener que traducirlos en cada pantalla y poder agrupar la cartera por tipo.

**Criterios de aceptación:**
- [x] Fases: `preparacion | ejecucion | hypercare | cerrado | cancelado`. `hypercare` no se traduce (ADR-038).
- [x] `type`: enum `transformacion | operacion | innovacion | bau`. Deja de ser texto libre, que es lo que impedía contestar «cuánto de mi cartera es transformación».
- [x] Ventana de compatibilidad por nombre retirado: la API acepta el viejo, guarda el canónico y deja rastro (`compat.nombre_viejo`). Cinco ventanas para las fases —se cierran por separado— y una compartida para los tres tipos en inglés.
- [x] El texto libre que ya había en `type` **se lee** (la columna sigue siendo texto) y no se vuelve a escribir. La migración no lo convierte ni lo vacía: lo anota.
- [x] Catálogo, orden, transiciones y etiquetas en un solo sitio: `app/dominio/proyecto.py`. Antes, `"closed"` estaba escrito a mano en trece archivos.
- [x] UI: selects, badges, tablero por fase y filtros del listado con el vocabulario nuevo.
- [x] La fase `cerrado` se dice «Cierre» cuando etiqueta una **lección**: el proyecto *está* cerrado (estado), la lección se aprendió *en el cierre* (etapa).

**Test Cases:**
- `TC-202.1` (unit) — Un tipo legado (`innovation`) se lee, se guarda como `innovacion` y deja rastro; un tipo inventado se rechaza.
- `TC-202.2` (integration) — La migración renombra `projects.phase` **y** `lessons.phase`, mapea los tres tipos, deja el tipo libre intacto y revierte.
- `TC-202.3` (unit) — Transiciones `preparacion→ejecucion→hypercare→cerrado`; `cancelado` desde cualquier fase viva; los dos terminales sin salida.
- `TC-202.4` (unit) — Las cinco copias del catálogo coinciden, incluido el tipo de TypeScript del frontend.

**Decisiones:** ADR-038 (supersede en vocabulario a ADR-019 y ADR-022) · DEC-031 (puntero).

---

### US-210 — Completitud de datos por proyecto ✅ (2026-08-20)

**Como** PMO
**Quiero** saber de qué proyectos se puede hablar
**Para** no leer un tablero donde seis proyectos sin capturar bajan el promedio
sin que nada lo diga.

De los mockups aprobados: la columna «Compl.» del artboard «Portafolio — Vista
maestra» y el «checklist de onboarding» de «Onboarding masivo». Son la misma
cosa: el porcentaje resume y el checklist detalla.

**Para qué sirve.** Un proyecto sin fechas no tiene desviación de calendario;
uno sin presupuesto no tiene consumo; uno sin PM no tiene a quién preguntarle.
En un tablero esos proyectos no salen mal: salen **vacíos**, y un hueco se lee
como un cero. Es también la única lista de tareas honesta después de una
importación masiva (US-216).

**Criterios de aceptación:**
- [x] **Se deriva, no se guarda.** Un porcentaje persistido habría que
  recalcularlo en cada edición del proyecto, en cada tarea, en cada
  participación y en cada acta; el día que se olvide un camino, la columna dice
  96 % de un proyecto al que le faltan tres campos. Mismo criterio que el avance
  del plan (ENH-109). **Sin migración**: el desglose de la Fase 2 asumía una
  para cada US de la oleada 2C y esta no la necesita.
- [x] Once requisitos, **todos con el mismo peso**. Ponderarlos exige defender
  por qué el sponsor vale el doble que el presupuesto, y esa discusión no tiene
  respuesta: los dos son obligatorios o no lo son. Un porcentaje con pesos
  secretos es peor que uno plano porque nadie puede reproducirlo.
- [x] **No se piden `name`, `folio` ni `phase`**: son NOT NULL, y una casilla que
  nunca puede fallar infla el porcentaje sin decir nada. La completitud mide lo
  que **puede** faltar.
- [x] Un presupuesto declarado de **cero cuenta como capturado** — es un
  proyecto sin costo, no un dato ausente. Es DAT-12 del lado del que evalúa. Un
  sponsor de espacios en blanco, en cambio, no cuenta: «capturado con nada» no
  es capturado.
- [x] Una clave que nadie averiguó cuenta como **faltante**: colapsar «no lo
  tiene» y «no lo miré» hacia el lado optimista es cómo un porcentaje acaba
  diciendo 100 % de un proyecto vacío.
- [x] El porcentaje redondea **hacia abajo**: con diez de once, «90 %» es más
  honesto que «91 %» — al proyecto le falta algo y el redondeo no puede
  insinuar que casi no.
- [x] Cada faltante viaja con su **etiqueta y su porqué**, no solo con la clave.
  Una casilla sin consecuencia se ignora, y la consecuencia es lo que hace que
  alguien capture el dato. Además evita traducir once claves a español en las
  tres superficies que lo pintan.
- [x] La regla vive en `app/dominio/completitud.py` y **no importa SQLAlchemy**
  (MCS DEV-02): recibe hechos y devuelve el veredicto, así que se prueba sin
  base de datos. Los hechos los averigua `app/services/completitud.py` en **tres
  consultas agrupadas** para todos los proyectos a la vez, no tres por fila.
- [x] `GET /projects/{id}/completeness` y el campo `completeness` en la fila de
  la vista maestra. El detalle viaja con la fila: una ida al servidor por
  proyecto para abrir el checklist es la razón por la que nadie lo abriría.
- [x] La columna usa **tres tramos de color** (100 · ≥80 · resto) y no un
  degradado: la pregunta es «¿este proyecto se puede leer?» y tiene tres
  respuestas. El 100 tiene su propio color porque es el único que significa «no
  falta nada» — pintar el 99 % igual que el completo es lo que hace que nadie lo
  termine.

**Test Cases:** `test_us210_completitud.py`
- `TC-210.1` (unit, sin base) — Todo/nada; una clave ausente cuenta como
  faltante; el redondeo va hacia abajo; el total se deriva de la lista; ningún
  faltante se explica con una frase hueca; no se piden los NOT NULL.
- `TC-210.2` — Presupuesto cero cuenta y `NULL` no; un sponsor de espacios no
  cuenta; los ocho del registro y los tres de gobierno; el acta de un proyecto
  no cuenta para otro; con la lista vacía no se consulta nada.
- `TC-210.3` — La vista maestra trae el porcentaje y el detalle; el endpoint del
  proyecto devuelve el checklist con sus cinco grupos; un proyecto de otro
  inquilino no se consulta.

**Estado de integración:** DONE (US-210).

## Notas técnicas

- Folios por tenant+año (Postgres sequences o función).
- Member list cacheable 60 s.
- Al cerrar proyecto, dispara job para generar reporte final con IA (opcional, ver EP008).

### Endpoints
```
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{id}
GET    /api/v1/projects/{id}/completeness   # US-210 (derivado, no persistido)
PATCH  /api/v1/projects/{id}
DELETE /api/v1/projects/{id}                 (soft)
POST   /api/v1/projects/{id}/phase/change

GET    /api/v1/projects/{id}/health-detail   # US-180/US-181 (2026-07-09)
PATCH  /api/v1/projects/{id}/health          # US-180/US-181 (2026-07-09)

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

### US-071 — Plantilla vacía descargable del Plan (Sprint 5)

**Como** PM sin plan previo
**Quiero** descargar una plantilla XLSX con las columnas que el
sistema espera
**Para** armar el plan offline y después subirlo.

Issue **#124**. Usa las 9 columnas canónicas de ENH-028 (WBS · Tarea
· Inicio · Fin · Duración · Avance · Es hito · Estado · Responsable)
+ hoja de instrucciones con formatos válidos + data validation. Botón
"Descargar plantilla" visible aun con plan vacío en
`/pmo/projects/[id]/plan`. Generación client-side con exceljs
(sin backend). Estado: `status:triage`.

---

### US-016 — Unificar Plan + Gantt en una sola pestaña

**Como** PM
**Quiero** ver la lista de tareas y el Gantt en una misma vista
**Para** navegar planeación sin saltar entre pestañas.

**Criterios de aceptación:**
- [x] Ruta `/pmo/projects/{id}/plan` con layout unificado.
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
- [x] Página frontend `/pmo/projects/{id}/areas` con CRUD completo
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
