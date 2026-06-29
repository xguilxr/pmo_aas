# EP009 — Integración con Microsoft Project

| Campo | Valor |
|---|---|
| **ID** | EP009 |
| **Prioridad** | Media (v1.1) |
| **Dependencias** | EP005 |
| **Módulo** | `tasks`, `msproject` |
| **Estado** | **POST-MVP / v1.1** (ENH-008, 2026-04-21) |

> **ENH-008 (2026-04-21):** el owner decidió mover la integración MS
> Project (.mpp / .xml / .xlsx) a **v1.1**. No entra en el MVP v1.0.
> Razón: el MVP prioriza flujos nativos del PMO-aaS (RAID, minutas IA,
> reportes) sobre interoperabilidad con herramientas externas. MSP
> requiere MPXJ (Java) o parsing complejo de XLSX; el costo no se
> justifica para v1.0.
>
> Cualquier US de este epic queda fuera del sprint v1.0. En la UI del
> Plan, los botones "Importar MSP / Exportar XLSX" (si existen) deben
> ocultarse o mostrar un aviso "Disponible en v1.1".

## Objetivo de negocio

Eliminar el ping-pong de archivos MS Project entre PMs: importar `.xml`, `.xlsx`, `.mpp`, mostrar Gantt interactivo en la app, y permitir gestión manual de tareas sin depender de MS Project standalone.

---

## Decisiones técnicas

| Tema | Decisión | Rationale |
|---|---|---|
| Parser principal | **MPXJ** (Java) | Única lib open-source que lee `.mpp` binario + `.xml`/`.xlsx` |
| Visualización | **SVG propio** (`components/gantt-view.tsx`) | frappe-gantt fue descartado; el wrapper SVG manual cumple para el alcance actual y evita una dependencia extra |
| Formatos aceptados | `.xlsx`, `.csv`, `.mpp`, `.xml` (MSPDI), `.mpx` | Todos integrados (US-069 agregó `.mpp` nativo) |
| Java runtime | **Embebido en el Dockerfile** (JRE 21 + MPXJ pinned) | Ya está en producción; ver `runbooks/infra/mpp-import.md` |
| Backend de parsing | **Worker job** (Celery) | Parsing puede tardar >30 s en proyectos grandes |

---

## US-047 — Importar archivo MS Project (XML/XLSX)

**Como** PM
**Quiero** subir un `.xml` o `.xlsx` exportado de MS Project
**Para** tener las tareas en la app.

**Criterios de aceptación:**
- [ ] `POST /api/v1/projects/{id}/tasks/import` (multipart).
- [ ] Formatos aceptados MVP: `application/xml` (MSP XML), `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- [ ] Max 50 MB.
- [ ] Response 202 + `job_id`.
- [ ] Worker parsea y extrae: `name`, `wbs`, `start_date`, `end_date`, `duration_days`, `progress`, `is_milestone`, `predecessors` (con tipo FS/SS/FF/SF y lag), `resource_names`, `notes`.
- [ ] **Vista previa** antes de confirmar: tabla con las tareas, checkboxes para excluir, alertas por errores.
- [ ] `POST /api/v1/projects/{id}/tasks/import/{job_id}/confirm` aplica import con selección.
- [ ] Re-import permitido: `--strategy=merge|replace`. `merge` matchea por `external_id` o `wbs`.
- [ ] Mapeo de recursos → users del tenant por nombre (fuzzy match ≥ 0.85); UI permite corregir mapping.
- [ ] Log: tareas importadas / ignoradas / errores, visible en detalle del job.

**Test Cases:**
- `TC-126` (unit) — Parser extrae correctamente deps FS/SS/FF/SF con lag.
- `TC-127` (integration) — XML con 500 tareas → todas importadas.
- `TC-128` (integration) — Archivo corrupto → 422 con mensaje claro.
- `TC-129` (integration) — Re-import con `merge` actualiza existing.
- `TC-130` (E2E) — UI preview → exclude 2 tareas → confirm → sólo 498 creadas.

---

## US-048 — Importar .mpp nativo (post-MVP)

**Como** PM
**Quiero** subir directamente `.mpp`
**Para** no tener que exportar a XML manualmente.

**Criterios:**
- [ ] Requiere Java 21 runtime en worker (sidecar).
- [ ] Parsing via MPXJ subprocess.
- [ ] Mismo flujo que US-047.
- [ ] Marcado como feature-flag `msp_native_import`.

**Estado (2026-04-24):** promovida a **US-069** (#122) en Sprint 5
como MUST. Feature flag removido (always-on). Ver el issue para
scope completo (OpenJDK 21 + MPXJ CLI en worker + runbook).

(Post-MVP — no se entrega en v1.0.)

---

## US-067 — Import XLSX → tareas del proyecto (entregado 2026-04-24)

**Estado:** DONE en Sprint 4 v1.3, commit `e9ef28b`. Parser XLSX
síncrono con auto-detect por alias de headers ES/EN. MPP quedó como
follow-up → promovido a **US-069** (#122) en Sprint 5.

Ver `apps/api/app/services/xlsx_task_parser.py`.

---

## US-069 — Import MPP nativo vía MPXJ (Sprint 5)

Promueve US-048 a MUST. Issue **#122**. Enchufa al wizard de US-070
vía interfaz `ParsedTask` compartida. Requiere Dockerfile.worker
extendido con OpenJDK 21 + `mpxj-cli`.

**Estado (2026-04-24):** fix-committed en Sprint 5. Implementación:
wrapper Java propio (`apps/api/app/services/msproject/mpxj_cli/MpxjCli.java`)
compilado en build-stage contra MPXJ **13.7.0**; JRE 21 headless
copiado desde `eclipse-temurin:21-jre-jammy` al Dockerfile compartido
`apps/api/Dockerfile` (no hay worker dir separado — mismo image con
start command diferente). `parse_mpp(data)` devuelve
`XlsxParseResult` — mismo shape que `parse_xlsx`, reusa el adaptador
`_TaskShim` del endpoint. Tests mockean `subprocess.run` (no hay
fixture binario .mpp en el repo). Runbook:
`docs/runbooks/infra/mpp-import.md`.

---

## US-070 — Wizard de mapeo de columnas Excel/CSV/MPP (Sprint 5)

Reemplaza el flujo síncrono auto-detect actual (US-067) por un
wizard de 4 pasos: upload → sheet selector (Excel) → preview + column
mapping manual → confirm. Parte `/tasks/import` en `/preview` +
`/{job_id}/confirm` con Redis como store. Agrega parser CSV nuevo.
Issue **#123**. Cierra el preview/confirm de US-047 que nunca se
implementó.

**Estado (2026-04-24):** completa (sub-bloques A + B fix-committed).

- `app/services/import_job_store.py` — Redis set/get/delete con TTL
  1h (`JOB_TTL_SECONDS = 3600`). Key `import:job:{uuid}`. Fail-loud.
- `app/services/csv_task_parser.py` — detecta delimitador `,`/`;`/`\t`
  con `csv.Sniffer` + BOM UTF-8/16. Shape = `XlsxParseResult`.
- `xlsx_task_parser` extendido: `sheets[]`, `sheet_used`,
  `sample_rows[]` (10 filas para el preview), `sheet` param,
  `columns_override` param (mapping manual), `strict` flag.
- Endpoints nuevos en `endpoints/tasks.py`:
  - `POST /projects/{id}/tasks/import/preview` — multipart, límite
    10MB (vs 50MB del endpoint viejo por el storage Redis), guarda
    el binario base64 + metadata. Devuelve `job_id, source, sheets,
    sheet_used, columns_detected, sample_rows, task_count, errors,
    ttl_seconds, system_fields`.
  - `POST /projects/{id}/tasks/import/{job_id}/confirm` — body con
    `mapping` opcional (solo xlsx/csv) y `strategy` (merge/replace).
    Ownership enforced: distinto user/tenant/project → 404/403.
    Preview expirado → 410. Mapping sin `name` → 422.
- Audit logs nuevos: `tasks.import_preview` y `tasks.import_confirm`.
- Endpoint one-shot `POST /tasks/import` mantiene funcionalidad para
  tests viejos y uploads que no necesiten wizard.

**Sub-bloque B — Frontend wizard** ✅ fix-committed
- `apps/web/lib/api/tasks.ts` extendido con `importPreview()` /
  `importConfirm()` + tipos `ImportPreviewResult`,
  `ImportConfirmResult`, `SystemField`, `SYSTEM_FIELD_LABELS`. La
  función vieja `importMsProject()` se mantiene para el endpoint
  one-shot (compat).
- `apps/web/components/import-wizard.tsx` — modal `<Lg>` con 4
  pasos lógicos: Upload → Sheet (skip auto si CSV/MPP/XML o si
  Excel con 1 sola hoja) → Preview + mapping → Done.
  - Mapping (ENH-179, 2026-06-29): grilla responsive de 2-3
    columnas; cada tarjeta = columna del archivo + `<select>` al
    campo destino (auto-detect pre-rellenado + `— ignorar —`) +
    valor de ejemplo. La vista previa de datos queda en una tabla
    compacta aparte que muestra el campo asignado (`→ Campo`) bajo
    cada header. Antes era un `<select>` alto por columna dentro del
    header de la tabla, que se estiraba a lo ancho/alto.
  - Validación inline: si no hay columna mapeada a `name` muestra
    Banner warning y deshabilita el botón Importar.
  - Selector de estrategia (merge/replace) integrado en el step de
    preview, con `confirm()` antes de un replace destructivo.
  - MPP/XML omiten el row de selectores (su shape ya viene
    normalizado) y muestran preview informativo.
- `app/(app)/pmo/projects/[id]/plan/page.tsx` — control inline
  `<select strategy>` + `<input type=file>` reemplazado por un
  botón "Importar" que abre el wizard. Removidos `importBusy`,
  `importStrategy` y `importPlanFile()` (toda la lógica vieja
  ~60 LoC eliminada). El callback `onImported` refresca la lista
  vía `loadTasksAndGantt()`.

**Cambios recientes (2026-06-29):**
- **BUG-081** — el parser XLSX (`_coerce_progress` / `parse_xlsx`) leía las
  columnas de avance **formateadas como porcentaje** en Excel como fracciones:
  openpyxl devuelve 0.3/0.5/0.7 para 30/50/70% y el entero `1` para 100%, así
  que 100% quedaba en 1%. Ahora `parse_xlsx` detecta el `number_format` de la
  columna de avance y escala las fracciones ×100 siempre; las columnas numéricas
  planas (donde `1` == 1%) se respetan.
- **ENH-178** — el modal de **editar tarea** del plan se salía de pantalla sin
  scroll. El componente `Modal` limita el alto al viewport con scroll interno
  (header/footer fijos, nuevo size `xl`); los modales Nueva/Editar tarea usan
  size `lg`; en editar, las fechas Inicio | Fin | Cierre van en una fila de 3
  columnas.

---

## US-049 — Visualizar Gantt

**Como** PM
**Quiero** ver las tareas como Gantt en la página del proyecto
**Para** entender cronograma y dependencias.

**Criterios de aceptación:**
- [ ] Ruta `/projects/{id}/gantt`.
- [ ] Vista con:
  - Columna izquierda: jerarquía expandible (WBS, nombre, responsable, % avance).
  - Área derecha: barras horizontales en timeline.
  - Flechas entre tareas según dependencias (FS/SS/FF/SF diferenciadas visualmente).
  - Hitos como diamantes (♦).
  - Línea "hoy" marcada.
- [ ] Colores por estado: azul (en progreso), verde (completada), rojo (retrasada vs plan), gris (no iniciada).
- [ ] **US-171 — Atraso ("Retrasada", rojo + tag):** tarea NO completada → retrasada si `end_date < hoy`. Tarea completada → retrasada sólo si `closed_at > end_date` (cerró tarde). Sin `closed_at` una tarea completada no se considera retrasada. Esto permite registrar una actividad cerrada a tiempo aunque se capture en fecha posterior (ajustando `closed_at`).
- [ ] Barra interna de avance (%).
- [ ] Zoom: día / semana / mes / trimestre.
- [ ] Tooltip al hover con todos los detalles.
- [ ] Click en tarea abre drawer con edición.
- [ ] Drag&drop para reagendar — **post-MVP**.
- [ ] Performance: render fluido con 500 tareas.

**Test Cases:**
- `TC-131` (E2E) — Gantt renderiza con 200 tareas en < 2 s.
- `TC-132` (E2E) — Zoom funciona en 4 niveles.
- `TC-133` (E2E) — Tooltip muestra dependencias.

---

## US-050 — Gestión manual de tareas

**Como** PM
**Quiero** CRUD manual de tareas sin importar MS Project
**Para** proyectos ad-hoc.

**Campos:**

| Campo | Notas |
|---|---|
| `name` | ✅ |
| `description` | |
| `wbs` | US-172: `POST /projects/{id}/tasks/renumber-wbs` renumera todo el proyecto jerárquico + único (1, 1.1, 1.2, 2, …), resuelve duplicados y remapea predecesoras |
| `position` | US-176: orden manual del plan. `POST /projects/{id}/tasks/{id}/move {after_id}` reordena (drag por fila en vista plana). Si hay `position`, manda sobre el WBS en `list_tasks` y en `renumber-wbs`. Null = orden natural por WBS. |
| `parent_id` | tarea padre |
| `start_date`, `end_date` | fecha planeada |
| `closed_at` | US-171: fecha de cierre **real** (editable). Auto = hoy al completar sin fecha. |
| `duration_days` | calculado si hay fechas |
| `progress` | 0-100 |
| `is_milestone` | bool |
| `owner_id` | |
| `priority` | 1-5 |
| `status` | `not_started`/`in_progress`/`completed`/`on_hold` |
| `dependencies` | array `{predecessor_id, type, lag_days}` |

**Criterios:**
- [ ] `POST /api/v1/projects/{id}/tasks`.
- [ ] `PATCH /api/v1/tasks/{id}`.
- [ ] Dependencias validadas: no ciclos, no self-reference.
- [ ] `progress` del padre se recalcula: promedio ponderado de hijos por duración.
- [ ] Cambios reflejados en Gantt en tiempo real (React Query invalidate).
- [ ] Ordenamiento por WBS / `start_date` / `priority`.
- [ ] Delete: marca soft; Gantt oculta, drawer muestra "archivada".

**Test Cases:**
- `TC-134` (unit) — Detección de ciclos en dependencias.
- `TC-135` (integration) — Progreso padre se recalcula al actualizar hijo.
- `TC-136` (integration) — Dependency type FS respeta `start = predecessor.end + lag`.

---

## US-051 — Recalcular cronograma

**Como** PM
**Quiero** recalcular fechas automáticamente según dependencias
**Para** impactar cambios en cascada.

**Criterios:**
- [ ] `POST /api/v1/projects/{id}/tasks/recalculate`.
- [ ] Motor simple **CPM** (Critical Path Method):
  - Forward pass: early start/finish.
  - Backward pass: late start/finish.
  - Marcar tareas críticas (slack = 0).
- [ ] Output incluye `critical_path_ids[]`.
- [ ] Tareas críticas se pintan con borde rojo en Gantt.
- [ ] Job puede correr en background para proyectos grandes.

**Test Cases:**
- `TC-137` (unit) — CPM en proyecto de ejemplo conocido → camino crítico correcto.
- `TC-138` (integration) — Mover fecha → ruta crítica recalculada.

---

## US-052 — Exportar a MS Project (.xml)

**Como** PM
**Quiero** exportar tareas a `.xml` compatible
**Para** compartir con stakeholders que usan MS Project.

**Criterios:**
- [ ] `GET /api/v1/projects/{id}/tasks/export?format=xml` → devuelve archivo MSP XML.
- [ ] Conserva: jerarquía WBS, deps con tipo y lag, recursos, fechas, avance.

**Test Cases:**
- `TC-139` (integration) — XML exportado puede abrirse en MS Project sin errores (validación XSD).

---

## Notas técnicas

- **Librería Python para XML/XLSX**: `openpyxl` (xlsx) + parsers custom en
  `apps/api/app/services/msproject/`.
- **Librería Java para .mpp** (US-069, DONE): **MPXJ embebido en el
  Dockerfile** (no sidecar). Wrapper `MpxjCli.java` se compila en el
  build; el endpoint invoca `java -cp /opt/mpxj/lib/*:/opt/mpxj/cli
  MpxjCli <file>` vía `subprocess`. Ver `runbooks/infra/mpp-import.md`.
- **Gantt visual**: SVG propio en `apps/web/components/gantt-view.tsx`
  (no `frappe-gantt`, no `dhtmlx-gantt`).
- **Performance**: con muchas tareas, virtualización (solo dibujar
  barras visibles).

### Endpoints
```
POST   /api/v1/projects/{id}/tasks/import
POST   /api/v1/projects/{id}/tasks/import/{job_id}/confirm
GET    /api/v1/projects/{id}/tasks
POST   /api/v1/projects/{id}/tasks
GET    /api/v1/tasks/{id}
PATCH  /api/v1/tasks/{id}
DELETE /api/v1/tasks/{id}
POST   /api/v1/tasks/{id}/dependencies
DELETE /api/v1/task-dependencies/{id}
POST   /api/v1/projects/{id}/tasks/recalculate
GET    /api/v1/projects/{id}/tasks/export
```

---

## Definition of Done

- [ ] Import XML/XLSX funcional end-to-end con preview.
- [ ] Gantt interactivo con 500 tareas sin lag (p95 < 2 s).
- [ ] CRUD manual y CPM recalculando en <500 ms para 200 tareas.
- [ ] Export XML valida XSD MSP.
- [ ] Drag&drop queda documentado pero no implementado en v1.0 (feature-flag off).
