---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# EP009 — Integración con Microsoft Project

| Campo | Valor |
|---|---|
| **ID** | EP009 |
| **Prioridad** | Media (v1.1) |
| **Dependencias** | EP005 |
| **Módulo** | `tasks`, `msproject` |
| **Estado** | **POST-MVP / v1.1** (ENH-008, 2026-04-21) |

> **ENH-008 (2026-04-21):** el owner mueve la integración MS Project
> (.mpp / .xml / .xlsx) a **v1.1**. No entra en el MVP v1.0. El MVP
> prioriza flujos nativos del PMO-aaS (RAID, minutas IA, reportes)
> sobre interoperabilidad con herramientas externas. MSP requiere
> MPXJ (Java) o parsing complejo de XLSX. El costo no se justifica
> para v1.0.
>
> Ninguna US de este epic entra al sprint v1.0. En la UI del Plan,
> los botones "Importar MSP / Exportar XLSX" (si existen) se ocultan
> o muestran el aviso "Disponible en v1.1".

## Objetivo de negocio

Elimina el ping-pong de archivos MS Project entre PMs. Importa `.xml`, `.xlsx` y `.mpp`. Muestra un Gantt interactivo en la app. Permite gestión manual de tareas sin depender de MS Project standalone.

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
- [ ] Worker parsea y extrae: `name`, `wbs_code`, `start_date`, `end_date`, `duration_days`, `progress`, `is_milestone`, `predecessors` (con tipo FS/SS/FF/SF y lag), `resource_names`, `notes`.
- [ ] **Vista previa** antes de confirmar: tabla con las tareas, checkboxes para excluir, alertas por errores.
- [ ] `POST /api/v1/projects/{id}/tasks/import/{job_id}/confirm` aplica import con selección.
- [ ] Re-import permitido: `--strategy=merge|replace`. `merge` matchea por `external_id` o `wbs_code`.
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
como MUST, sin feature flag (always-on). Scope completo en el issue
(OpenJDK 21 + MPXJ CLI en worker + runbook).

(Post-MVP — no se entrega en v1.0.)

---

## US-067 — Import XLSX → tareas del proyecto (entregado 2026-04-24)

**Estado:** DONE en Sprint 4 v1.3, commit `e9ef28b`. Parser XLSX
síncrono con auto-detect por alias de headers ES/EN. MPP queda como
follow-up y se promueve a **US-069** (#122) en Sprint 5.

Ver `apps/api/app/services/xlsx_task_parser.py`.

**Mejoras (2026-07-18):**
- **BUG-088** (`37c66ae`, fix-committed) — WBS fiel al importar. El parser XLSX
  respeta el `number_format` de celdas numéricas (`'0.00'` + `1.3` → `"1.30"`) y
  ya no colapsa `1.30→1.3`. Emite warnings nuevos en preview/confirm:
  `WBS_NUMERIC_GENERAL` (celda sin formato específico) y `WBS_ORPHANS` (padre WBS
  ausente). La plantilla y los exports fuerzan formato texto (`@`) en la columna
  WBS para evitar pérdida de dígitos.
- **BUG-089** (`48b33c3`, fix-committed) — % de avance: detecta el formato `%`
  **POR CELDA**, no por columna entera. Enteros tipeados en celdas %-formateadas
  se leen como `0-100` literal (ej. `100` en celda % = 100%, no 1%). Emite warning
  `PROGRESS_PCT_AS_INTEGER` cuando hay duda.

---

## US-069 — Import MPP nativo vía MPXJ (Sprint 5)

Promueve US-048 a MUST. Issue **#122**. Enchufa al wizard de US-070
vía interfaz `ParsedTask` compartida. Requiere Dockerfile.worker
extendido con OpenJDK 21 + `mpxj-cli`.

**Estado (2026-04-24):** fix-committed en Sprint 5. Implementación:
wrapper Java propio (`apps/api/app/services/msproject/mpxj_cli/MpxjCli.java`)
compilado en build-stage contra MPXJ **13.7.0**. JRE 21 headless se
copia desde `eclipse-temurin:21-jre-jammy` al Dockerfile compartido
`apps/api/Dockerfile` (no hay worker dir separado; mismo image con
start command diferente). `parse_mpp(data)` devuelve
`XlsxParseResult`, el mismo shape que `parse_xlsx`, y reusa el
adaptador `_TaskShim` del endpoint. Los tests mockean
`subprocess.run` (no hay fixture binario .mpp en el repo). Runbook:
`docs/runbooks/infra/mpp-import.md`.

---

## US-070 — Wizard de mapeo de columnas Excel/CSV/MPP (Sprint 5)

Reemplaza el flujo síncrono auto-detect de US-067 por un wizard de
4 pasos: upload → sheet selector (Excel) → preview + column mapping
manual → confirm. Divide `/tasks/import` en `/preview` +
`/{job_id}/confirm` con Redis como store. Agrega un parser CSV
nuevo. Issue **#123**. Cierra el preview/confirm de US-047, que
nunca se implementó.

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
  pasos lógicos: Upload → Sheet (se salta si es CSV/MPP/XML o Excel
  de 1 sola hoja) → Preview + mapping → Done.
  - Mapping (ENH-179, 2026-06-29): grilla responsive de 2-3
    columnas; cada tarjeta = columna del archivo + `<select>` al
    campo destino (auto-detect pre-rellenado + `— ignorar —`) +
    valor de ejemplo. La vista previa de datos queda en una tabla
    compacta aparte que muestra el campo asignado (`→ Campo`) bajo
    cada header. Antes era un `<select>` alto por columna dentro del
    header de la tabla, que se estiraba a lo ancho/alto.
  - Validación inline: sin columna mapeada a `name`, banner warning
    y botón Importar deshabilitado.
  - Selector de estrategia (merge/replace) en el step de preview,
    con `confirm()` antes de un replace destructivo.
  - MPP/XML omiten el row de selectores (shape ya normalizado) y
    muestran preview informativo.
- `app/(app)/pmo/projects/[id]/plan/page.tsx` — control inline
  `<select strategy>` + `<input type=file>` reemplazado por un
  botón "Importar" que abre el wizard. Se remueven `importBusy`,
  `importStrategy` y `importPlanFile()` (~60 LoC de lógica vieja).
  El callback `onImported` refresca la lista vía
  `loadTasksAndGantt()`.

**Cambios recientes (2026-06-29):**
- **BUG-081** — el parser XLSX (`_coerce_progress` / `parse_xlsx`) leía las
  columnas de avance **formateadas como porcentaje** en Excel como fracciones.
  openpyxl devuelve 0.3/0.5/0.7 para 30/50/70% y el entero `1` para 100%, así
  que 100% quedaba en 1%. Ahora `parse_xlsx` detecta el `number_format` de la
  columna de avance y siempre escala las fracciones ×100; respeta las columnas
  numéricas planas, donde `1` equivale a 1%.
- **ENH-178** — el modal de **editar tarea** del plan se salía de pantalla sin
  scroll. El componente `Modal` ahora limita el alto al viewport con scroll
  interno (header/footer fijos, nuevo size `xl`). Los modales Nueva/Editar
  tarea usan size `lg`. En editar, las fechas Inicio | Fin | Cierre van en una
  fila de 3 columnas.
- **ENH-180** — elimina el reordenamiento por arrastre de filas
  (handle/drop-zones/endpoint move) y el botón Auto-WBS. La agrupación
  jerárquica por WBS pasa a ser el mecanismo por default. Los endpoints
  `/tasks/{id}/move` y `/tasks/renumber-wbs` siguen existiendo, pero ya no se
  usan desde la UI del Plan.
- **ENH-181** — WBS automatizable en los forms de nueva/editar tarea: se
  selecciona el padre, "Bajar nivel" asigna el siguiente número WBS
  disponible. El campo WBS sigue editable a mano.
- **ENH-182** — las columnas Criticidad e Hito (header + celdas) se centran.
- **ENH-188 (2026-07-09, `d735e76`)** — la columna Estado del Plan pasa de
  un `InlineSelectCell` plano a `TaskStatusInlineCell`: un chip `StatusBadge`
  con color (gris `not_started` / azul `in_progress` / verde `completed`)
  clickeable, que abre un `<select>` nativo para editar inline (el mismo
  patrón `StatusInlineCell` que ya usan las listas RAID).

**Batch "Plan Import Revamp" (2026-07-18):**
- **ENH-197** (`80b9308`, fix-committed) — **Jerarquía WBS por ancestro más cercano:** nueva función `nearest_ancestor_wbs()` en `plan_metadata.py` resuelve el padre de una tarea buscando el ancestro existente más próximo. Rollup de avance % y chevron del agrupado cuelgan la tarea en la posición jerárquica correcta aunque falten filas intermedias (ej., tarea `1.30.1` cuelga de `1` si `1.30` no existe).
- **US-190** (`24e314c`, fix-committed) — **Revisión de calidad del plan:** servicio nuevo `services/plan_quality.py` con 10 checks automáticos: WBS sin código/duplicado/huérfano/huecos en numeración; plan sin hitos; secciones sin hito de cierre; sin tareas críticas; duraciones >21 días en hojas; sin fechas; sin responsable; tareas vencidas sin avance. Motor genera score 0-100. Endpoint `GET /projects/{id}/plan/quality` + botón "Revisar calidad" en `/plan` abre modal de observaciones con recomendaciones por check.
- **BUG-090** (`b11c932`, fix-committed) — el `confirm` del wizard aplica
  coerción inteligente de campos: (1) **Responsable** — fuzzy match ≥0.85 contra
  actors del tenant → `assignee_actor_id`; (2) **Hito Relacionado** — resolución
  por WBS; (3) **Predecessors** — mapeo a `Task.predecessors` JSON + creación de
  `TaskDependency` FS; ciclos omitidos best-effort y successors recomputados;
  (4) **Fin calculado** — cuando viene vacío pero hay Inicio + Duración.
- **ENH-191** (`a39b3dc`, fix-committed) — **Estado importable end-to-end**: alias
  `estado`/`status` (ES/EN), normalización de enum crudo + labels en ES con
  sinónimos EN (`en_synonyms`). Default `not_started` si no se detecta; warning
  `STATUS_UNRECOGNIZED` en preview cuando hay valor desconocido. Campo mapeable
  en el wizard (select `→ Estado`).
- **ENH-192** (`d86dbed`, fix-committed) — **Wizard re-mapea 14 campos**: una sola
  lista `SYSTEM_FIELDS` compartida con el suggester (antes había hardcoding en
  varias partes). **Preview interpretado**: nuevo campo `parsed_preview` con
  primeras 10 tareas ya coercionadas al tipo target (no solo valores crudos).
  Endpoint nuevo: `POST /projects/{id}/tasks/import/{job_id}/repreview` — re-interpreta
  con mapping manual sin persistir, para preview live mientras se ajusta.
- **ENH-193** (`63b34c2`, fix-committed) — **GET `/plan/download`**: exporta todas
  las tareas del plan en **15 columnas idénticas a la plantilla V1** (WBS, Tarea,
  Outline Level, Inicio, Fin, Duración (días), Avance (%), Estado, Área Responsable,
  Responsable, Criticidad, Es hito, Hito Relacionado, Predecessors, Successors).
  Orden real del plan (según `position` → WBS natural). FKs resueltos a texto
  legible (actor names, estado label, etc.).
- **ENH-194** (`d2e4624`, fix-committed) — **Plantilla descargable extendida**:
  nueva hoja "Proyecto" (contexto del charter: objetivo, alcance, sponsor, fechas
  planeadas). Nueva hoja "Gantt" (timeline semanal con barras por conditional
  formatting; hitos en morado). El export "Descargar" (`GET /plan/download`) también
  genera la hoja Gantt con datos reales en la línea de tiempo.
- **US-188** (`eaaabce`, fix-committed) — **Import inteligente IA** (3 niveles,
  gateado por `tenant.ai_mode`, fallback heurístico): (1) `suggest-mapping` acepta
  `sample_rows` para mapear por contenido; (2) normalización IA en confirm
  (estados no reconocidos + responsables sin match fuzzy → respuesta `ai_normalized`);
  (3) `POST /import/{job_id}/ai-structure` — la IA propone el plan completo desde
  un archivo sucio, el usuario lo revisa en preview, el confirm lo persiste con
  `use_ai_structure=true`. Servicio nuevo: `apps/api/app/services/import_ai.py`.
- **2026-08-04** (`8908556`) — **La IA ya no puede desmapear una columna.** En
  `suggest-mapping`, un `field: null` del modelo con confianza alta pisaba el
  mapeo que la heurística había acertado, y la columna llegaba sin asignar al
  wizard. La puerta de confianza arbitra entre dos respuestas; la ausencia de
  respuesta ya no gana por ser confiada. Un valor que no es objeto se descarta
  antes de mirar la confianza. Lo encontró el conjunto de evaluación de IA
  (caso `EV-C-35`), no un reporte de usuario.
- **US-189** (`7acfaab`, fix-committed) — **Wizard UX para no-PMs**: drag & drop
  nativo en upload step; resumen llano ("Se importarán N tareas · M avisos");
  mapeo colapsado como avanzado (requiere expandir); estrategias en lenguaje plain
  ("Agregar y actualizar" / "Reemplazar todo el plan" en lugar de merge/replace).

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
- [ ] **US-177 — Atraso (tags separados, 2026-06-29):** 
  - **"Atrasada" (rojo)** — tarea NO completada con `end_date < hoy`.
  - **"Completada con atraso" (amarillo)** — tarea completada con `closed_at > end_date`.
  - Antes ambos casos usaban un único tag "Retrasada" (rojo). Se renombra "Retrasada"→"Atrasada" en toda la plataforma: badge y chip de filtro del Plan, KPI card y filtro de reportes, sección S-17 ("Tareas Atrasadas") y avance.html. En backend, `_is_delayed` cuenta solo las no completadas vencidas; `_is_completed_late` marca las completadas tarde. (La migración 0090 renombra el catálogo de status.)
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
| `wbs_code` | **ENH-181 (2026-06-29):** WBS automatizable en el form de nueva/editar tarea — selecciona padre y "Bajar nivel" asigna el siguiente número WBS disponible. Reemplaza al Auto-WBS (removido). Campo sigue editable a mano. |
| `position` | **ENH-180 (2026-06-29):** reordenamiento por arrastre (`POST /projects/{id}/tasks/{id}/move`) y botón Auto-WBS (`renumber-wbs`) fueron removidos de la UI. Endpoints siguen existiendo pero no se usan. Agrupación jerárquica por WBS (colapsar/expandir) es el mecanismo por default. |
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

## US-218 — Dependencias entre tareas de proyectos distintos ✅ (2026-08-20)

**Como** PMO Manager
**Quiero** encadenar una tarea de mi plan con una de otro proyecto
**Para** que el cronograma diga que esto no puede empezar hasta que aquello
cierre.

Del artboard «Proyecto — Plan»: «Gantt (baseline vs actual, ruta crítica,
**dependencias inter-proyecto**)».

**Sin migración.** `task_dependencies` enlaza por identificador y ya podía
guardar el enlace; hasta ahora solo lo llenaba el importador de MS Project, y
solo dentro de un proyecto. Lo que faltaba era la API, el guardarraíl y la forma
de verlo. Dentro de un proyecto las dependencias siguen en `Task.predecessors`
por código WBS (US-090) — un WBS no sirve para cruzar proyectos porque el `1.2`
de uno no es el `1.2` de otro.

**Criterios de aceptación:**
- [x] `GET/POST/DELETE /projects/{id}/external-dependencies`. Se puede quitar
  desde **cualquiera** de los dos proyectos: los dos planes están encadenados y
  los dos dueños pueden desligarlos.
- [x] **La validación de ciclos es a nivel de TAREA, no de proyecto.** La
  respuesta fácil —«si A depende de B, prohíbe que B dependa de A»— bloquearía
  un caso normal: «les entregamos el ambiente en la fase 1 y ellos nos devuelven
  la certificación en la fase 3». Eso es A→B y B→A a nivel de proyecto y no hay
  ningún ciclo real: son dos cadenas que no se tocan.
- [x] **El recorrido cruza las dos clases de arista**: las internas por WBS
  (`predecessors`/`successors`) y las externas por identificador. Mirar solo una
  deja pasar el ciclo que alterna entre ambas, que es el que un plan grande
  produce sin que nadie lo vea venir.
- [x] Las tareas se cargan **por proyecto y a demanda**: un plan entra de golpe
  porque sus aristas internas están en sus propias filas, y solo se abre otro
  proyecto si una arista externa lleva hasta él. Sin tope artificial — un tope
  convertiría un ciclo real en un «no encontré ninguno», y aceptar la arista es
  peor que tardar.
- [x] **Una dependencia dentro del mismo proyecto se rechaza** con el motivo
  escrito: tener dos mecanismos para lo mismo es cómo empiezan a discrepar.
- [x] Los cuatro vínculos de MS Project (`FS`/`SS`/`FF`/`SF`) se aceptan: el
  importador ya los escribe, y rechazarlos aquí haría que una dependencia
  importada no se pudiera recrear a mano.
- [x] Repetir la misma dependencia es **idempotente**: quien la vuelve a pedir
  quiere que exista, y ya existe.
- [x] **`task_dependencies` no lleva `tenant_id`** —enlaza por identificador—,
  así que el recorrido filtra por inquilino con un `join` a la tarea
  predecesora, y el borrado comprueba que la dependencia toca a una tarea de
  **este** proyecto. Sin eso, un identificador adivinado tocaría la dependencia
  de otro cliente.
- [x] Una tarea de otro inquilino da **404 y no 422**: desde fuera no se
  distingue «no existe» de «es de otro inquilino», y decirlo confirmaría que
  existe.
- [x] Las dependencias internas que el importador escribió en
  `task_dependencies` **no** se listan como externas: duplicarían lo que ya dice
  `predecessors`.

**Un panel, no flechas en el Gantt.** Una flecha necesita dos extremos en
pantalla, y la tarea del otro proyecto está en otro plan con otras fechas y otra
escala: la flecha saldría del borde apuntando a la nada, lo que obliga a adivinar
a dónde va. Lo que sí comunica es nombrar el otro extremo con su proyecto y su
fecha: «esto no puede empezar hasta que PRJ-2026-004 cierre su corte de
servicios, previsto el 12 de septiembre».

**Entrantes y salientes van separadas** porque significan cosas distintas: una
entrante es algo que este proyecto **espera** y que puede retrasarlo; una
saliente es alguien esperándonos, y a quien hay que avisar si nos movemos.
Mezcladas obligan a leer el sentido en cada fila.

**Test Cases:** `test_us218_dependencias_externas.py`
- `TC-218.1` — Crear, idempotencia, auto-dependencia, mismo proyecto, tipo
  inventado, los cuatro vínculos válidos.
- `TC-218.2` — El ciclo directo se rechaza; **el que alterna aristas internas y
  externas también**; la ida y la vuelta en cadenas disjuntas se permiten (el
  caso que un guardarraíl a nivel de proyecto bloquearía).
- `TC-218.3` — Entrantes y salientes separadas; el otro extremo trae su
  proyecto; se quita desde cualquiera de los dos; no desde un tercero; una tarea
  de otro inquilino da 404; las internas del importador no se listan.

**Estado de integración:** DONE (US-218).

---

## US-212 / D-6 — Línea base del plan ✅ (2026-08-20)

Del artboard «Proyecto — Plan» de los mockups aprobados el 2026-08-19:
«Baseline (capturar / comparar)», marcado como nuevo, y un Gantt «baseline vs
actual». Cierra la brecha **B-1** del diagnóstico y la decisión **D-6** del
glosario.

**Como** PM
**Quiero** guardar el plan acordado como promesa y comparar el de hoy contra él
**Para** que «desviación», «retraso» y «sobrecosto» dejen de ser palabras sin
referente.

**El problema que resuelve, dicho sin rodeos.** Un Gantt que se mueve solo no
está atrasado respecto de nada. Hasta ahora la plataforma usaba las tres
palabras —en reportes, en el tablero, en el semáforo de salud— midiendo contra
el plan de hoy, que es el que acaba de cambiar. Es como medir un retraso contra
el reloj que ya se adelantó.

**Dos tablas y no dos columnas en `tasks`.** `baseline_start` /
`baseline_end` junto a las fechas vivas es más barato y solo aguanta **una**
línea base: la segunda captura pisa la primera, y con ella el histórico de
replanificaciones — que es justo lo que un comité de cambios pide ver
(«¿cuántas veces se movió esta fecha?»). Con dos tablas, un proyecto tiene
tantas líneas base como veces haya vuelto a prometer, cada una con quién la
capturó y por qué.

**Se emparejan por identificador, no por código EDT.** El código parece la clave
natural y no lo es: el propio plan tiene un botón que lo renumera
(`renumber-wbs`). Emparejar por código haría que una renumeración —que no mueve
ninguna fecha— apareciera como «todas las tareas retiradas y otras tantas
nuevas».

**Se devuelven dos derivas por tarea, y esa es la parte que importa.** La del
**plan** (`slip_days`) se puede hacer desaparecer reescribiendo fechas; la
**real** (`actual_slip_days`, el cierre contra el fin prometido) no. Un tablero
que solo mira la primera premia replanificar, que es lo contrario de lo que una
línea base sirve para vigilar.

**Criterios de aceptación:**
- [x] `POST /projects/{id}/plan/baselines` — copia el plan de hoy. Las capturas
  se **apilan**: no sustituyen a la anterior. Nombre obligatorio («Línea base 3»
  no dice contra qué se compara), nota opcional (exigir justificación cada vez
  acaba llenándose de «replan»).
- [x] `GET /projects/{id}/plan/baselines` — el listado, la más reciente primero,
  con el nombre de quien capturó resuelto en una sola consulta.
- [x] `GET /projects/{id}/plan/baseline-comparison?baseline_id=` — la
  comparación contra la vigente o contra cualquier captura anterior.
- [x] **Sin línea base devuelve `has_baseline: false` y nada más**, no una
  comparación de ceros. Es la diferencia entre «no se desvió» y «no sabemos si
  se desvió porque nadie prometió nada» (MCS DAT-12), y la interfaz lo dice con
  esas palabras: «su desviación no es cero: es desconocida».
- [x] Una tarea sin fecha de fin tiene deriva `null`, no 0. Decir 0 la contaría
  como «en fecha», que es la lectura opuesta a la verdad.
- [x] Alcance agregado (`nueva`) y quitado (`retirada`) se cuentan **aparte** de
  las corridas. Un proyecto puede tener cero tareas corridas y treinta nuevas:
  eso no es un plan que se cumple, es un plan que creció.
- [x] **Borrar una tarea no encoge la promesa.** La fila de la foto sobrevive —
  `plan_baseline_tasks.task_id` no lleva clave ajena a propósito—, o la
  comparación mentiría en la dirección cómoda.
- [x] El resumen da la **peor** deriva, no el promedio: veinte tareas en fecha y
  una corrida cuatro meses dan un promedio tranquilizador. Y sin ninguna tarea
  corrida no hay «peor» — devolver la menos adelantada bajo ese nombre haría
  leer un adelanto como un atraso.
- [x] `DELETE` de una línea base capturada por error. **No hay forma de
  editarla**: cambiarle las fechas sería falsificar la promesa contra la que se
  mide el plan.
- [x] Un proyecto en fase `cerrado` no admite captura nueva. Un plan vacío sí —
  capturar antes de detallar es una secuencia legítima, y la comparación dirá
  que todo el plan es alcance nuevo, que es lo que pasó.
- [x] Las dos operaciones de escritura quedan en la auditoría.

**Tests (`tests/test_us212_linea_base.py`, 22):**
- `TC-212.1` — La regla sin base de datos (MCS DEV-02, 12 casos): sin cambio,
  corrida, adelantada, deriva `None` sin fecha, alcance nuevo y retirado,
  emparejamiento por id tras renumerar el EDT, deriva real ≠ deriva del plan,
  conteos por separado, peor deriva y no promedio, sin corridas no hay peor,
  deriva del proyecto por el fin más tardío.
- `TC-212.2` — Contra la API (10 casos): sin línea base la respuesta lo dice;
  capturar copia el plan; mover una fecha aparece como corrida con los días
  exactos; una tarea agregada después es alcance nuevo; borrar una tarea deja su
  fila en la foto; las capturas se apilan y se puede comparar contra una vieja;
  borrado; plan vacío capturable; una línea base de otro proyecto da 404; el
  nombre es obligatorio (422).

**Diferido (no bloqueante):** las barras de línea base **dentro** del Gantt SVG.
El artboard las pide, y el panel de comparación ya contesta la pregunta
(«¿qué se movió y cuánto?») con números exactos en vez de con dos barras a
escala. Dibujarlas es trabajo del componente `gantt-view.tsx` y no del modelo,
que es lo que esta US tenía que resolver.

**Estado de integración:** DONE (US-212).

---

## US-216 — Onboarding masivo: importar proyectos y recursos ✅ (2026-08-20)

Del artboard «Onboarding masivo — Importación» de los mockups aprobados el
2026-08-19 y del bloque **B5**: «cubre la carga inicial de 23 proyectos sin
captura manual».

**Como** PMO que arranca con un cliente nuevo
**Quiero** subir su cartera en un Excel
**Para** no teclear 23 proyectos y 40 personas a mano.

**Por qué está en esta epic.** Es el mismo trabajo que el importador de planes
visto una altura más arriba: aquel carga las tareas de un proyecto, este carga los
proyectos. Comparten el patrón «vista previa → confirmar» y el mismo almacén de
preview; documentarlos aparte esconde que un arreglo en uno debería mirar al otro.

**Qué importa y qué no.** Proyectos y recursos, al nivel de la organización. Los
**planes** ya tienen su importador —por proyecto, porque un código WBS es del
proyecto: el `1.2` de uno no es el `1.2` de otro—. Duplicar aquí ese camino daría
dos importadores de lo mismo que divergen con el primer arreglo. La pantalla lo
dice, para que nadie suba un plan aquí y no entienda el 415.

**Una fila mala no tumba el archivo.** Un archivo de 23 proyectos con un error en
el 7 tiene 22 filas buenas. Abortar entero obliga a arreglar y resubir a ciegas
—sin saber si hay más errores detrás—, que es el bucle que hace abandonar una
importación. Se valida todo, se reporta fila por fila, y se confirma lo válido.

**Una duplicada se salta y NO se actualiza.** Es la decisión con más consecuencias
de la US. Una importación se corre dos veces —se cayó la red, alguien la repitió,
el archivo llegó corregido— y las dos alternativas son peores:

- **Duplicar** convierte 23 proyectos en 46, sin forma barata de deshacerlo.
- **Actualizar en silencio** pisa lo que alguien editó a mano después de la
  primera corrida. El caso concreto: se importa, el PM corrige las fechas en la
  aplicación, alguien resube el Excel original y las fechas vuelven atrás sin que
  nadie se enterase.

Saltar y reportar deja el trabajo hecho intacto y la decisión en manos de quien la
puede tomar. Actualizar en masa es otra operación, con su propia confirmación, y
no se disfraza de importación.

**El nombre es la clave de un proyecto** porque no hay otra: un Excel mantenido a
mano no trae identificadores de esta plataforma, y el folio lo genera el sistema
—en la primera carga no existe—. Se compara normalizado (sin acentos, sin
mayúsculas, sin espacios de sobra) porque «Migración ERP» y «migracion erp  » son
el mismo proyecto escrito por dos personas. Para un recurso la clave es el
**correo**, que sí identifica sin ambigüedad; sin correo se cae al nombre, con la
misma salvedad.

**Criterios de aceptación:**
- [x] `GET /imports/columns?kind=` — el catálogo de columnas con su ayuda, sus
  alias y sus valores admitidos. Se sirve desde el backend porque el vocabulario
  cerrado (tipos, fases, unidades de tarifa) vive en el dominio: dos listas
  separadas divergen en cuanto se añade un tipo.
- [x] `POST /imports/preview` valida el archivo entero y **no escribe nada**.
  Devuelve fila por fila su estado —`valida` / `invalida` / `duplicada`— y sus
  problemas, con la **línea real del archivo** contando el encabezado: enumerar
  las filas ya filtradas desplazaría los números en cuanto hubiera una fila vacía
  en medio, y entonces «revisa la fila 12» no apuntaría a la fila 12 del Excel.
- [x] `POST /imports/{job_id}/confirm` crea las válidas. El preview se **borra**
  al confirmar: confirmar dos veces el mismo trabajo daría el doble de proyectos,
  y es el error que la detección de duplicados no puede atrapar dentro de la misma
  transacción.
- [x] Los encabezados se emparejan por **alias** («Cartera» → portafolio, «Fecha
  inicio» → `start_date`). Lo que no reconoce queda sin mapear y se **reporta**:
  descartar en silencio una columna «Owner» deja creer que entró.
- [x] Faltando una columna obligatoria, el error es **del archivo** y no de las
  filas. Decirlo así evita un reporte de 23 filas inválidas por la misma causa.
- [x] Duplicados **dentro del mismo archivo** cuentan igual. La primera aparición
  entra y las siguientes se saltan — no al revés: quien lee el reporte espera que
  la de arriba sea la que pasó.
- [x] Una fila inválida **no** se marca además como duplicada: esconder el error
  que hay que arreglar primero es peor que no reportar el segundo.
- [x] El portafolio, el programa y el área **se crean si no existen**, con el
  nombre que trae la fila. Exigir que existan antes convierte la importación en
  dos pasos, y el primero se hace a ciegas porque nadie sabe qué portafolios hay
  hasta ver el archivo. Lo que **no** se crea es un usuario: `pm_email`
  desconocido deja el proyecto sin PM. Crear cuentas desde un Excel es una
  decisión de seguridad, no de carga de datos.
- [x] Los tres números —creados, inválidos, duplicados— van **juntos** en la
  respuesta y en la pantalla. «18 creados» sin decir que 5 quedaron fuera es la
  misma mentira por omisión que un costo total sin las asignaciones sin tarifa
  (US-215).
- [x] La **plantilla mínima** que pide el artboard («simplificada según tamaño»)
  es la misma lista filtrada por obligatorias, no otra plantilla — así no puede
  desincronizarse de la grande. Se genera en el navegador desde las columnas que
  el backend declara: un archivo estático se queda viejo el día que se añade una
  columna, y el usuario descubre el desajuste al subirlo.
- [x] Techo de 10 MB y 2.000 filas, con aviso cuando se trunca. Un archivo
  equivocado no debe intentar crear cien mil proyectos antes de que alguien lo
  note.
- [x] El `job_id` lleva el inquilino que lo creó: es un UUID y no un secreto, y
  sin la comprobación quien lo adivinara escribiría en otro inquilino.
- [x] La organización de destino viene del **selector del header** (US-205), no de
  un selector propio: importar «en todas» no significa nada, porque un proyecto
  vive en una organización.
- [x] La escritura queda en la auditoría con los tres conteos.

**Tests (`tests/test_us216_importacion_masiva.py`, 25):**
- `TC-216.1` — La regla sin base de datos (MCS DEV-02, 13 casos): normalización,
  emparejado por alias, fila completa válida, obligatoria faltante nombrada,
  valor fuera del vocabulario nombrando los admitidos, fin antes del inicio,
  prioridad 1–5, tarifa sin unidad que avisa sin invalidar, duplicada del
  catálogo, duplicada dentro del archivo, una inválida no se marca duplicada, el
  resumen de tres estados, las obligatorias como plantilla mínima.
- `TC-216.2` — Contra la API (12 casos): el catálogo de columnas, clase
  inexistente rechazada, el preview valida todo y no escribe, confirmar crea solo
  las válidas creando portafolio y programa, **correr la importación dos veces no
  duplica la cartera**, **una duplicada no se actualiza** —se corrige a mano, se
  resube el original, el dato corregido sigue ahí—, columnas obligatorias
  faltantes, recursos con tarifa y unidad, un job de otro inquilino da 404,
  confirmar dos veces el mismo job da 404, archivo vacío, formato no soportado que
  apunta al importador correcto.

**Diferido (no bloqueante):** el **mapeo manual** de columnas en la interfaz. El
backend ya devuelve `mapping` y `unmapped_headers`, y la pantalla los muestra;
lo que no hay es el control para reasignar una columna a mano. Con los alias
declarados, un archivo hecho desde la plantilla no lo necesita, y uno ajeno se
arregla renombrando encabezados — que es lo que la pantalla dice hacer. La
sugerencia asistida por IA que el plan tiene (US-188) también aplicaría aquí y
está fuera de esta US.

**Estado de integración:** DONE (US-216).

---

## Notas técnicas

- **Librería Python para XML/XLSX**: `openpyxl` (xlsx) más parsers
  custom en `apps/api/app/services/msproject/`.
- **Librería Java para .mpp** (US-069, DONE): **MPXJ embebido en el
  Dockerfile** (no sidecar). El wrapper `MpxjCli.java` se compila en
  el build; el endpoint invoca `java -cp /opt/mpxj/lib/*:/opt/mpxj/cli
  MpxjCli <file>` vía `subprocess`. Ver `runbooks/infra/mpp-import.md`.
- **Gantt visual**: SVG propio en `apps/web/components/gantt-view.tsx`
  (no `frappe-gantt`, no `dhtmlx-gantt`).
- **Performance**: con muchas tareas, virtualiza y dibuja solo las
  barras visibles.

### Endpoints
```
POST   /api/v1/projects/{id}/tasks/import
POST   /api/v1/projects/{id}/tasks/import/preview        (anterior endpoint, parte de US-070 wizard)
POST   /api/v1/projects/{id}/tasks/import/{job_id}/confirm
POST   /api/v1/projects/{id}/tasks/import/{job_id}/repreview    (ENH-192, 2026-07-18)
POST   /api/v1/projects/{id}/tasks/import/{job_id}/ai-structure (US-188, 2026-07-18)
GET    /api/v1/projects/{id}/tasks
POST   /api/v1/projects/{id}/tasks
GET    /api/v1/tasks/{id}
PATCH  /api/v1/tasks/{id}
DELETE /api/v1/tasks/{id}
POST   /api/v1/tasks/{id}/dependencies
DELETE /api/v1/task-dependencies/{id}
GET    /api/v1/projects/{id}/external-dependencies              (US-218)
POST   /api/v1/projects/{id}/external-dependencies              (US-218)
DELETE /api/v1/projects/{id}/external-dependencies/{dep_id}     (US-218)
POST   /api/v1/projects/{id}/tasks/recalculate
GET    /api/v1/projects/{id}/tasks/export
GET    /api/v1/projects/{id}/plan/download              (ENH-193, 2026-07-18)
GET    /api/v1/projects/{id}/plan/baselines                      (US-212)
POST   /api/v1/projects/{id}/plan/baselines                      (US-212)
DELETE /api/v1/projects/{id}/plan/baselines/{baseline_id}        (US-212)
GET    /api/v1/projects/{id}/plan/baseline-comparison            (US-212)

Carga masiva a nivel de organización (US-216) — los planes siguen siendo por
proyecto, arriba:
GET    /api/v1/imports/columns?kind=projects|resources           (US-216)
POST   /api/v1/imports/preview                                   (US-216)
POST   /api/v1/imports/{job_id}/confirm                          (US-216)
POST   /api/v1/projects/{id}/tasks/renumber-wbs          (no se usa en UI; ENH-180, 2026-06-29)
POST   /api/v1/tasks/{id}/move                           (no se usa en UI; ENH-180, 2026-06-29)
```

---

## Definition of Done

- [ ] Import XML/XLSX funcional end-to-end con preview.
- [ ] Gantt interactivo con 500 tareas sin lag (p95 < 2 s).
- [ ] CRUD manual y CPM recalculando en <500 ms para 200 tareas.
- [ ] Export XML valida XSD MSP.
- [ ] Drag&drop queda documentado pero no implementado en v1.0 (feature-flag off).
