---
responsable: propietario
estado: vigente
revisado: 2026-05-26
revisar_cada: 90d
---

# EP020 — Report Builder (Niveles 1, 2 y 4) + Catálogo de secciones atómicas

| Campo | Valor |
|---|---|
| **ID** | EP020 |
| **Prioridad** | Alta — siguiente frente operativo del PMO |
| **Dependencias** | EP005 (projects), EP006 (modules), EP007 (admin), EP008 (IA), EP014 (motor PDF + reportes operativos), EP018 (artefactos) |
| **Módulo** | `reports.builder`, `reports.catalog`, `reports.portfolio`, `ai.report_assist` |
| **Estado** | # IN-PROGRESS — Sprints 27-29, 31-32 entregados; rediseño Reportes proyecto + 4 tabs PMO/Org/Prog/Proyectos + builder unificado (Sprints 30-32) |
| **Versión objetivo** | v1.5 |
| **Catálogo detallado** | `docs/epics/drafts/EP020-secciones-atomicas.md` (working doc — referencia normativa de las 22 secciones) |

## Cambios recientes (2026-05-23)

**Sprint 31 Bloque 2 — Reportes a nivel PMO/Org/Prog/Proyectos rediseñados**
- ✅ Sidebar simplificado ("Módulos" sin dropdown Reportes) — ENH-116 (bf423ca).
- ✅ Tab "Proyectos" en `/pmo/reports` enriquecido (folio/tipo/período, filtro drafts, link detail) — ENH-120 (ba3aae1).
- ✅ Tab "PMO" con Status PMO via `exportBuilderPdf({level:1})` — US-144 (f639d88).
- ✅ Tab "Organizaciones" con filtro org — US-145 (ee8ab24).
- ✅ Tab "Programas" con filtros org+programa — US-146 (0b5af6a).
- ✅ Página detail reporte con iframe + regeneración — nueva ruta `/pmo/projects/[id]/reports/[reportId]/`.

**Sprint 32 Bloque 1 — Look-ahead + Generar/Historial/Programar tabs**
- ✅ Endpoint Look-ahead `POST /projects/{id}/reports/look-ahead` con ventana configurable — US-147 (2bd4032).
- ✅ Campos period_from/period_to en Avance/Seguimiento + dropdown "3 semanas" — ENH-122 (bf2eba8).
- ✅ 3 tabs Generar (con paneles Avance/Seguimiento/Look-ahead + catálogo plantillas)/Historial/Programar — ENH-121 (5e1c7f8).
- ✅ Header con un solo CTA "Builder" — ENH-121.

**Sprint 32 Bloque 2 — Builder unificado**
- ✅ Header con Modo + Ventana (value+unit dropdown), persistencia en template defaults — US-148 (9a14e31).
- ✅ Catálogo 22 secciones integrado en tab Generar — reusa US-120.
- ✅ Preview live con líneas amarillas A4 — ENH-124 (cb1abff).
- ✅ Navigation guard al salir sin guardar (`beforeunload` + onClick confirm) — ENH-125 (542ee5a).

**Cleanup minutas**
- ✅ Listing minutas (botón único + reorder columnas + sin MD/TXT) — ENH-117 (7ad1fd8).
- ✅ Detail minuta sin MD/TXT — ENH-118 (89a430b).
- ✅ Click nombre minuta → detail (no listing) — BUG-062 (bfe4efd).
- ✅ Backend minutas con source_type (transcript|minute|manual) + migración 0075 — US-143 (1fb672b).
- ✅ Frontend generador unificado 3 modos — US-142 (0bcf138).
- ✅ Labels claros estados RAID — ENH-119 (a6f5ffb).
- ✅ `/reports/tweak` → redirect `/reports/builder` — chore (def46f6).
- ✅ `/ai-minutes/new` → redirect `/minutes/new` — chore (US-142 anterior).

---

## Objetivo de negocio

Habilitar **4 niveles de reportes** del PMOaaS:

1. **Nivel 1 PMO** — agregado interno de todos los proyectos del tenant (módulo nuevo `/pmo/reports/portfolio`).
2. **Nivel 2 Organización / Programa** — agregado por org o programa, cliente-facing (tab nuevo en organización).
3. **Nivel 3 Proyecto** — extiende Avance y Seguimiento (EP014) para que sean composiciones declarativas del catálogo de secciones atómicas.
4. **Nivel 4 PM / Usuario** — canvas drag-and-drop con preview en vivo y modo IA conversacional, plantillas privadas con opción "publicar al proyecto".

Las 22 secciones atómicas (catálogo cerrado en draft) son el ÚNICO bloque de composición. Los 4 niveles son combinaciones predefinidas o libres de las mismas secciones. Un solo motor de render, dos modos de composición (Avance "por sección" y Seguimiento "por área").

**Fuera de scope original (v1.0):** S-10 entregables formales; S-07 curva S (pendiente). **US-151 (2026-05-26) introdujo `metric_snapshots`** (foto semanal a 4 niveles), y **US-158 implementó S-05 (Tendencia)** —sparkline SVG server-side + tabla desde snapshots— y **S-15 (Matriz de riesgos 5x5)** como secciones del builder (project-level). Ambas seedeadas por migración 0080 y registradas en `SECTION_BUILDERS`. **US-161** implementó **S-07 (Curva-S)**: planeado (lineal `start_date`→`end_date`, capturado en `metric_snapshots.extras.avg_progress_plan`) vs real acumulado, como sección del builder con SVG dual server-side (migración 0081).

## Decisiones arquitectónicas (registradas en DECISIONS.md)

> Renumeradas a DEC-025..029 al cierre de la implementación: los IDs originales (DEC-018..022) ya estaban tomados por otras decisiones del repo cuando esta epic se materializó.

- **DEC-025** — Catálogo cerrado de 22 secciones atómicas como única unidad de composición para todos los niveles de reporte. Se cierra el dual-motor heredado de EP014 (Python templated) → se unifica en motor declarativo (data + render config en JSONB).
- **DEC-026** — Dos modos de composición: A "por sección × área" (Reporte de Avance) y B "por área × sección" (Reporte de Seguimiento). Ambos son una decisión de render, no de query.
- **DEC-027** — Sin snapshots históricos en v1.0. Estado actual únicamente. Snapshots se evalúan en v2.0.
- **DEC-028** — Método de cálculo de % avance configurable por tenant (3 opciones: weighted_duration default, weighted_effort, simple_count).
- **DEC-029** — Gantt snapshot (S-19) se renderiza como SVG Python en v1.0; la migración a headless browser (Playwright) queda como evolución v1.x cuando se valide el costo memoria/render en producción. El contrato HTTP (`image/svg+xml`) es estable.

---

## Backbone — Catálogo, motor y plantillas seed

### # DONE (reusado en Sprint 31-32) — US-120 — Modelo y seed del catálogo de secciones atómicas

**Como** plataforma
**Quiero** un catálogo de 22 secciones atómicas registradas con su contrato de datos, parámetros y variantes visuales
**Para** que los reportes de cualquier nivel se compongan combinando estas secciones.

**Criterios de aceptación:**
- [x] Tabla `report_sections_catalog` con campos: `id` (S-XX), `category` (HDR/EST/AVN/PLN/RAID/EQP/NAR/KPI/PRT), `name`, `description`, `data_contract` JSONB, `default_params` JSONB, `variants` JSONB, `supports_ia` BOOL, `levels` ARRAY, `enabled` BOOL.
- [x] Seed con las 22 secciones especificadas en el catálogo (`docs/epics/drafts/EP020-secciones-atomicas.md`).
- [x] Endpoint `GET /reports/sections-catalog` devuelve el catálogo filtrable por categoría / nivel.
- [x] Service `app/services/reports/catalog.py` con función de cálculo registrada por id de sección.
- [x] Pruebas: catálogo no rompe seed; cada id tiene función de cálculo registrada.

**Status:** Entregado en Sprint 31. Catálogo integrado en tab Generar de Reportes proyecto (ENH-121) y disponible en canvas builder.

**Test cases:** TC-200 catálogo seed completo; TC-201 endpoint filtrable; TC-202 función registrada por id.

### # PENDING — US-121 — Servicio de cálculo configurable por tenant

**Como** plataforma
**Quiero** que el cálculo del % avance respete el método configurado por el tenant
**Para** que la misma sección S-06 dé el número correcto según convención del PMO.

**Criterios de aceptación:**
- [ ] Service `app/services/reports/progress.py` con tres implementaciones: `weighted_duration`, `weighted_effort`, `simple_count`.
- [ ] Lee `tenants.progress_calculation_method` y dispatcha.
- [ ] Validaciones: `weighted_effort` warning si hay tareas sin horas estimadas.
- [ ] Reusado por S-06, S-08, KPI-01, KPI-02, S-35.

**Dependencia:** ENH-098 (config tenant) debe entregarse antes o en paralelo.

**Test cases:** TC-203 los 3 métodos dan el mismo resultado con data uniforme; TC-204 weighted_effort warning con horas faltantes; TC-205 dispatch desde setting.

### # PENDING — US-122 — Modelo de plantillas + plantillas seed v1.0

**Como** PM
**Quiero** plantillas predefinidas para Avance, Seguimiento y los reportes de portafolio
**Para** generar un reporte estándar sin tener que construirlo desde cero.

**Criterios de aceptación:**
- [ ] Tabla `report_templates` con campos: `id`, `name`, `level` (1/2/3/4), `composition_mode` ('by_section'|'by_area'), `sections` JSONB (lista ordenada con sus params), `is_seed` BOOL, `owner_id` (NULL si seed/PMO/Org), `project_id` (NULL si privada o pública), `visibility` ('private'|'project'|'tenant').
- [ ] Plantillas seed cargadas:
  - **L3-AVANCE** — modo A — S-01, S-02, S-03, S-04, S-06, S-08, S-19, S-09, S-16, S-17, S-18, S-14, S-11, S-13, S-12
  - **L3-SEGUIMIENTO** — modo B — S-01, S-02, S-03, S-04 + por área: S-20, S-21, S-09, S-16, S-17, S-18, S-14, S-11, S-13, S-12
  - **L1-PORTAFOLIO** — modo A — S-01, S-35, S-36, S-33, S-34
  - **L2-ORG** — modo A — S-01, S-02, S-04, S-33, S-35, S-36, S-34
- [ ] Endpoint CRUD `/report-templates` con permisos por visibility.
- [ ] Migración Alembic.

**Test cases:** TC-206 seed cargado; TC-207 visibility private/project/tenant respetada; TC-208 migración idempotente.

### # DONE (2026-05-25, 67bb040) — US-123 — Engine de render con modos composición A/B

**Como** sistema
**Quiero** un motor único que tome una plantilla + scope (proyecto / org / portafolio) + ventana temporal y devuelva HTML + JSON estructurado
**Para** que cualquier nivel de reporte se renderice consistentemente.

**Criterios de aceptación:**
- [ ] Service `app/services/reports/engine.py` con `render(template, scope, window) -> {html, json, sections_meta}`.
- [ ] Soporta `composition_mode='by_section'` (default — secciones secuenciales, items ordenados por área→fecha).
- [ ] Soporta `composition_mode='by_area'` (matriz invertida — itera áreas, dentro de cada área renderiza la lista de secciones).
- [ ] Reusa motor PDF compartido (US-037) para export.
- [ ] Exclusiones cruzadas en PLN/RAID (S-17 excluye items que ya salen en S-09/S-16; S-18 ídem).
- [ ] Plantillas Jinja2 por sección en `apps/api/app/templates/pdf/sections/`.

**Test cases:** TC-209 modo A reproduce orden área→fecha; TC-210 modo B agrupa por área; TC-211 exclusiones cruzadas no duplican; TC-212 export PDF.

---

## Canvas Nivel 4 (PM / Usuario)

### # DONE (2026-05-25, d53daaa) — US-124 — Canvas drag-and-drop + preview en vivo

**Como** PM
**Quiero** arrastrar secciones desde el catálogo a un canvas con preview HTML en vivo
**Para** construir reportes personalizados sin tocar código.

**Criterios de aceptación:**
- [ ] Ruta `/pmo/projects/{id}/reports/builder` (canvas nivel 4 para proyecto).
- [ ] Layout: catálogo lateral (filtrable por categoría) + canvas central + panel parámetros derecha.
- [ ] Drag-and-drop con `dnd-kit` o similar; reorden vertical de secciones.
- [ ] Preview en vivo se re-renderiza al cambiar params (debounced ~500ms).
- [ ] Persistencia local del canvas en `report_drafts` (autosave cada 30s).

**Test cases:** TC-213 drag y drop reordena; TC-214 cambio de param refresca preview; TC-215 autosave persiste.

### # DONE (2026-05-25, ec63303) — US-125 — Panel de parámetros transversales

**Como** PM
**Quiero** configurar área, ventana temporal, top N, modo resumen/detalle, ordenamiento y agrupación de cada sección desde un panel uniforme
**Para** no tener que aprender un UI distinto por sección.

**Criterios de aceptación:**
- [ ] Componente `<SectionParamsPanel>` que lee `data_contract` de la sección y renderiza form correspondiente.
- [ ] Parámetros transversales aplican según `applies_to` declarado en el catálogo (área, ventana, top N, modo, orden, agrupación).
- [ ] Validación: ventana ≤ rango del proyecto; top N ≥ 1.

**Test cases:** TC-216 form se construye dinámicamente desde data_contract; TC-217 validaciones funcionan.

### # DONE (2026-05-25, 88bbcac, migración 0073) — US-126 — Plantillas privadas + publicar al proyecto

**Como** PM
**Quiero** guardar mi canvas como plantilla privada y opcionalmente publicarla al proyecto
**Para** reusarla en los próximos cortes o compartirla con otros PMs del mismo proyecto.

**Criterios de aceptación:**
- [ ] Botón "Guardar como plantilla" → modal con nombre + visibility (private/project).
- [ ] Plantillas privadas solo las ve el owner; publicadas al proyecto las ven todos los miembros del proyecto.
- [ ] Galería "Mis plantillas" + "Plantillas del proyecto" en la pantalla de canvas.
- [ ] Permisos: solo el owner puede publicar/despublicar la suya.

**Test cases:** TC-218 privacidad respetada; TC-219 publicar/despublicar; TC-220 aislamiento por proyecto (filtro `project_id` en la query — no RLS, ver `architecture/database.md`).

### # DONE (2026-05-25, 5436224) — US-127 — Modo IA conversacional construyendo el reporte

**Como** PM
**Quiero** un panel de chat lateral donde le pido a la IA "agrega los hitos críticos de las próximas 3 semanas" y la IA agrega la sección con los parámetros correctos
**Para** construir reportes hablando, sin tocar el catálogo manualmente.

**Criterios de aceptación:**
- [ ] Panel chat lateral colapsable en `/builder`.
- [ ] IA tiene tool calls registrados: `add_section(id, params)`, `remove_section(idx)`, `update_section_params(idx, params)`, `reorder_section(from, to)`.
- [ ] Modelo: reusa el provider del tenant (Groq plataforma o BYO según `tenant.ai_mode`). **No es cascada** — se eliminó en BUG-053; ver `EP008-ai.md`.
- [ ] Cada acción del IA es revisable + revertible por el PM (transcript visible).
- [ ] Contexto inyectado: lista del catálogo + data del proyecto.

**Test cases:** TC-221 IA llama add_section con id válido; TC-222 PM puede revertir. *(TC-223 "fallback entre modelos" se descarta: no hay cascada de providers post BUG-053.)*

---

## Niveles 1, 2, 3 — Módulos UI (Sprint 31-32)

### # DONE (2026-05-23) — Rediseño Reportes Nivel 1, 2, 3 (4 tabs PMO/Org/Prog/Proyectos) — ENH-116, ENH-120, US-144, US-145, US-146

Integra reportes a nivel PMO (Status), Organización, Programa y Proyectos en una estructura 4-tabs unificada bajo `/pmo/reports`.

**Ruta principal:** `/pmo/reports`

**Criterios de aceptación:**
- [x] Tab "PMO" — Status PMO via `exportBuilderPdf({level:1})` — US-144 (f639d88).
- [x] Tab "Organizaciones" — filtro por org, scope nivel 2 — US-145 (ee8ab24).
- [x] Tab "Programas" — filtro org+programa — US-146 (0b5af6a).
- [x] Tab "Proyectos" — folio, tipo, período enriquecidos; filtro drafts; link a detail — ENH-120 (ba3aae1).
- [x] Sidebar simplificado: "Módulos" sin dropdown Reportes separado — ENH-116 (bf423ca).
- [x] Página detail: `/pmo/projects/[id]/reports/[reportId]/` con iframe + regeneración.

**Generación:** cada tab usa `exportBuilderPdf({level})` disparado desde generador backend 3-paneles (Avance/Seguimiento/Look-ahead — ver ENH-121).

### # ARCHIVED — US-128, US-129 (Nivel 1 y 2 anteriores, modelo viejo)

Los módulos UI separados `/pmo/reports/portfolio` y `/pmo/organizations/{id}/reports` se reemplazan por la arquitectura 4-tabs unificada (Sprint 31-32). El viejo modelo point-and-click de "Nuevo reporte" se reemplaza por generador backend 3-paneles + catálogo plantillas builder integrado.

---

## Reportes Proyecto Rediseñados (Sprint 31-32)

### # DONE (2026-05-23) — US-147, ENH-122, ENH-121, US-148, ENH-124, ENH-125 — Tabs Generar/Historial/Programar + Look-ahead + Builder unificado

Rediseña `/pmo/projects/[id]/reports` con 3 tabs y builder unificado con Modo + Ventana persistentes.

**Tabs:**
- **Generar** — 3 paneles (Avance/Seguimiento/Look-ahead) + catálogo plantillas builder — ENH-121 (5e1c7f8).
- **Historial** — tabla reportes generados (sin cambios respecto anterior).
- **Programar** — cron scheduling (sin cambios respecto anterior; forma existente soporta custom).

**Look-ahead:** `POST /projects/{id}/reports/look-ahead` con `{window_value, window_unit}` — US-147 (2bd4032). Persiste `Report(generator='look_ahead')`. Excluye vencidas.

**Generador parámetros:**
- Campos `period_from`/`period_to` en Avance + Seguimiento para rango custom — ENH-122 (bf2eba8).
- Dropdown "3 semanas" prepoblado — ENH-122.

**Builder unificado:**
- Header con Modo (Avance/Seguimiento/Look-ahead) + Ventana (value+unit dropdown) — US-148 (9a14e31).
- Persistencia en `default_parameters._template` — US-148.
- Load plantilla directo vía `?template_id=X` — US-148.
- Preview live con líneas amarillas marcando cortes A4 — ENH-124 (cb1abff).
- Navigation guard al salir sin guardar (`beforeunload` + onClick confirm en Link "Volver") — ENH-125 (542ee5a).

**Status:** El rediseño consolida la experiencia anterior ("Catálogo → Historial → Builder → Creación") en 3 tabs claros (Generar/Historial/Programar) con header unificado de Modo+Ventana.

### # DONE (2026-05-23) — ENH-117, ENH-118, BUG-062, US-143, US-142, ENH-119 — Cleanup minutas

Simplifica la lista/detalle minutas y agrupa generación (transcript/minute/manual) en un solo flujo.

- [x] Listing minutas: un solo botón + reorder columnas + sin MD/TXT — ENH-117 (7ad1fd8).
- [x] Detail minuta: sin MD/TXT — ENH-118 (89a430b).
- [x] Click nombre minuta → detail (no listing) — BUG-062 (bfe4efd).
- [x] Backend minutas con `source_type ENUM (transcript|minute|manual)` + migración 0075 — US-143 (1fb672b).
- [x] Frontend generador 3 modos unificado (transcript import/minuta + manual) — US-142 (0bcf138).
- [x] Labels RAID con estado visual claro (color + icon) — ENH-119 (a6f5ffb).
- [x] Redirect `/reports/tweak` → `/reports/builder` — chore (def46f6).
- [x] Redirect `/ai-minutes/new` → `/minutes/new` — chore (anterior US-142).

## Exports y suscripciones

### # DONE (2026-05-25, 0dba512) — US-130 — Export PDF de reportes custom

**Como** PM
**Quiero** descargar el reporte custom como PDF con el mismo estilo de los reportes operativos
**Para** compartirlo fuera de la plataforma.

**Criterios de aceptación:**
- [ ] Endpoint `POST /reports/{id}/export?format=pdf` reusa motor US-037.
- [ ] Plantilla base + plantilla por sección (extendida del motor US-123).
- [ ] Footer con metadata: PM, fecha emisión, plantilla aplicada, scope.

**Test cases:** TC-230 PDF valida `%PDF` header; TC-231 incluye todas las secciones del canvas.

### # DONE (2026-05-25, 176448b, migración 0074) — US-131 — Suscripciones de reportes custom

**Como** PM
**Quiero** programar la emisión periódica de un reporte custom (cron) con envío a una lista de destinatarios
**Para** automatizar la cadencia de reportes recurrentes.

**Criterios de aceptación:**
- [ ] Reusa motor `scheduled_reports` (US-056) extendiéndolo para aceptar plantillas custom (no solo Avance/Seguimiento).
- [ ] UI: botón "Programar" en el detalle del reporte custom → modal con cron + destinatarios.
- [ ] Destinatarios pueden ser usuarios internos o emails externos (siempre vía Resend).

**Test cases:** TC-232 schedule custom corre en cron; TC-233 email se envía; TC-234 destinatario externo.

---

## Render avanzado

### # DONE (2026-05-25, d97943f) — US-132 — Render del Gantt WBS-1 para S-19 (SVG Python; headless Playwright queda como evolución)

**Como** sistema
**Quiero** capturar el Gantt client-side renderizado por la app y exportarlo como PNG/SVG embebible en PDF
**Para** que S-19 muestre el mismo Gantt que se ve en pantalla.

**Criterios de aceptación:**
- [ ] Worker headless (puppeteer o playwright) en el container worker existente.
- [ ] Endpoint `GET /projects/{id}/gantt/snapshot?wbs_level=1&window_start=...&window_end=...` devuelve `image/png` o `image/svg+xml`.
- [ ] Tiempo de render < 10s por proyecto típico (100-1000 tasks); fallback a SVG si timeout.
- [ ] Plantilla S-19 inserta la imagen vía `<img>` en el HTML/PDF.

**Test cases:** TC-235 endpoint devuelve PNG válido; TC-236 timeout fallback; TC-237 imagen embebida en PDF.

---

## Dependencias del sistema (ENH a otros epics)

Se abren como issues separados con label del epic afectado. **Deben entregarse antes o en paralelo con las US que las consumen.**

### # PENDING — ENH-097 — EP006 Plan: tasks.is_critical boolean (reemplaza columna existente)

- Reemplazar la columna `critical` actual por `tasks.is_critical BOOLEAN NOT NULL DEFAULT FALSE`.
- Migración Alembic: convertir valores truthy → true, dropear columna vieja.
- Plantilla import Excel/CSV: columna "Crítica" (Sí/No).
- Form edición tarea: checkbox "Crítica" hermano de "Hito".
- Mapping MS Project import si trae flag.
- **Consume:** US-120 (catálogo, S-16).

### # PENDING — ENH-098 — EP007 Admin: progress_calculation_method por tenant

- `tenants.progress_calculation_method ENUM ('weighted_duration','weighted_effort','simple_count') DEFAULT 'weighted_duration'`.
- UI admin tenant: radio buttons con explicación corta de cada opción.
- Validación: warning si selecciona weighted_effort y hay tasks sin horas estimadas.
- Migración Alembic.
- **Consume:** US-121.

### # PENDING — ENH-099 — EP007 Admin: task_load_thresholds por tenant

- `tenants.task_load_thresholds JSONB DEFAULT {"green":5, "amber":10}`.
- UI admin tenant: 2 inputs numéricos.
- **Consume:** US-120 (catálogo, S-21).

### # PENDING — ENH-100 — EP002 Organización: client_logo_url

- `organizations.client_logo_url TEXT NULL`.
- UI admin organización: upload de logo (S3/R2 storage).
- Default placeholder neutro si vacío.
- Migración Alembic.
- **Consume:** US-120 (catálogo, S-01).

### # PENDING — ENH-101 — EP005 Projects: status_rag declarativo

- Campos sobre `projects`: `status_rag ENUM`, `status_comment TEXT`, `status_updated_at TIMESTAMP`, `status_updated_by UUID`.
- UI: dropdown + textarea en proyecto para que el PM declare/actualice el estado.
- Cada update sobreescribe (sin historia — sale del scope v1.0).
- Migración Alembic.
- **Consume:** US-120 (catálogo, S-03, S-33, S-34, S-35, S-36).

---

## Plan de sprints (actualizado 2026-05-23)

| Sprint | Bloque | Items | Foco | Status |
|---|---|---|---|---|
| **26** | 1 | ENH-097, ENH-098, ENH-099, ENH-100, ENH-101 | Dependencias del sistema (modelo + admin UI) | ✅ DONE |
| **26** | 2 | US-120, US-121, US-122 | Backbone catálogo + cálculo + plantillas seed | ✅ DONE (US-120 reusado Sprint 31) |
| **27** | 1 | US-123, US-130 | Motor de render + export PDF | ✅ DONE |
| **27** | 2 | US-124, US-125, US-126 | Canvas Nivel 4 (drag-drop + params + plantillas privadas) | ✅ DONE |
| **28** | 1 | US-127 | IA conversacional | ✅ DONE |
| **28** | 2 | US-131 | Suscripciones custom | ✅ DONE |
| **29** | 1 | US-128, US-129 | Módulos UI Niveles 1 y 2 (modelo viejo) | ⚠️ ARCHIVED (reemplazado Sprint 31) |
| **29** | 2 | US-132 | Render headless Gantt | ✅ DONE |
| **31** | 2 | ENH-116, ENH-120, US-144, US-145, US-146 | 4 tabs PMO/Org/Prog/Proyectos rediseñados | ✅ DONE (2026-05-23) |
| **32** | 1 | US-147, ENH-122, ENH-121, US-148 | Tabs Generar/Historial/Programar + Look-ahead + Builder unificado | ✅ DONE (2026-05-23) |
| **32** | 2 | ENH-124, ENH-125, ENH-117, ENH-118, BUG-062, US-143, US-142, ENH-119 | Preview A4 + navigation guard + cleanup minutas + generador unificado | ✅ DONE (2026-05-23) |

**Estimado:** EP020 backbone (Sprints 26-29) completado. Rediseño Reportes (Sprints 31-32) completado. Canvas Nivel 4 y IA conversacional están listos para reutilización en nuevos flujos.

## Riesgos

- **Render headless en producción** — puppeteer/playwright agrega memoria al worker; medir antes de habilitar en prod.
- **Concurrencia de plantillas publicadas** — dos PMs editando la misma plantilla del proyecto requiere locking optimista (resolver en US-126).
- **Coste IA Nivel 4** — el chat con tool calls puede generar muchas llamadas; aplicar rate limit por proyecto (reusa rate limiting EP008).
- **Migración de columna `critical`** (ENH-097) — riesgo de pérdida de datos si conversión truthy → bool no se hace bien; validar en staging antes.
- **Plantillas seed cambiantes** — si se redefinen los seeds después de release, hay que decidir si actualizan plantillas ya generadas o solo las nuevas. Recomendación: snapshot del template en cada reporte generado (template_snapshot JSONB), las plantillas vivas solo aplican a reportes nuevos.

## Definition of Done de la épica

- [ ] Las 22 secciones del catálogo cargan, calculan y renderizan correctamente (HTML + PDF).
- [ ] 4 plantillas seed (L3-AVANCE, L3-SEGUIMIENTO, L1-PORTAFOLIO, L2-ORG) generan reportes funcionales.
- [ ] Canvas Nivel 4 permite construir reporte custom + guardar plantilla privada + publicar al proyecto.
- [ ] Chat IA construye reporte vía tool calls.
- [ ] Suscripciones programan emisión recurrente.
- [ ] Niveles 1 y 2 accesibles desde sus rutas dedicadas.
- [ ] Tests verdes (TC-200 a TC-237).
- [ ] DECISIONS.md actualizado con DEC-018 a DEC-022.
- [ ] DB-CHANGES.md actualizado con migraciones de ENH-097 a ENH-101.
