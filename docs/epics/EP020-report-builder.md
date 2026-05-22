# EP020 — Report Builder (Niveles 1, 2 y 4) + Catálogo de secciones atómicas

| Campo | Valor |
|---|---|
| **ID** | EP020 |
| **Prioridad** | Alta — siguiente frente operativo del PMO |
| **Dependencias** | EP005 (projects), EP006 (modules), EP007 (admin), EP008 (IA), EP014 (motor PDF + reportes operativos), EP018 (artefactos) |
| **Módulo** | `reports.builder`, `reports.catalog`, `reports.portfolio`, `ai.report_assist` |
| **Estado** | # PENDING |
| **Versión objetivo** | v1.5 |
| **Catálogo detallado** | `docs/epics/drafts/EP020-secciones-atomicas.md` (working doc — referencia normativa de las 22 secciones) |

## Objetivo de negocio

Habilitar **4 niveles de reportes** del PMOaaS:

1. **Nivel 1 PMO** — agregado interno de todos los proyectos del tenant (módulo nuevo `/pmo/reports/portfolio`).
2. **Nivel 2 Organización / Programa** — agregado por org o programa, cliente-facing (tab nuevo en organización).
3. **Nivel 3 Proyecto** — extiende Avance y Seguimiento (EP014) para que sean composiciones declarativas del catálogo de secciones atómicas.
4. **Nivel 4 PM / Usuario** — canvas drag-and-drop con preview en vivo y modo IA conversacional, plantillas privadas con opción "publicar al proyecto".

Las 22 secciones atómicas (catálogo cerrado en draft) son el ÚNICO bloque de composición. Los 4 niveles son combinaciones predefinidas o libres de las mismas secciones. Un solo motor de render, dos modos de composición (Avance "por sección" y Seguimiento "por área").

**Fuera de scope (postergado a v2.0):** snapshots históricos de KPIs y semáforo (S-05 tendencia, sparklines, deltas, S-07 curva S, S-10 entregables formales). Para v1.0 los reportes muestran estado actual sin series temporales.

## Decisiones arquitectónicas a registrar en DECISIONS.md al cierre

- **DEC-018** — Catálogo cerrado de 22 secciones atómicas como única unidad de composición para todos los niveles de reporte. Se cierra el dual-motor heredado de EP014 (Python templated) → se unifica en motor declarativo (data + render config en JSONB).
- **DEC-019** — Dos modos de composición: A "por sección × área" (Reporte de Avance) y B "por área × sección" (Reporte de Seguimiento). Ambos son una decisión de render, no de query.
- **DEC-020** — Sin snapshots históricos en v1.0. Estado actual únicamente. Snapshots se evalúan en v2.0.
- **DEC-021** — Método de cálculo de % avance configurable por tenant (3 opciones: weighted_duration default, weighted_effort, simple_count).
- **DEC-022** — Render del Gantt para PDF vía headless browser (puppeteer/playwright) que captura el SVG client-side.

---

## Backbone — Catálogo, motor y plantillas seed

### # PENDING — US-120 — Modelo y seed del catálogo de secciones atómicas

**Como** plataforma
**Quiero** un catálogo de 22 secciones atómicas registradas con su contrato de datos, parámetros y variantes visuales
**Para** que los reportes de cualquier nivel se compongan combinando estas secciones.

**Criterios de aceptación:**
- [ ] Tabla `report_sections_catalog` con campos: `id` (S-XX), `category` (HDR/EST/AVN/PLN/RAID/EQP/NAR/KPI/PRT), `name`, `description`, `data_contract` JSONB, `default_params` JSONB, `variants` JSONB, `supports_ia` BOOL, `levels` ARRAY, `enabled` BOOL.
- [ ] Seed con las 22 secciones especificadas en el catálogo (`docs/epics/drafts/EP020-secciones-atomicas.md`).
- [ ] Endpoint `GET /reports/sections-catalog` devuelve el catálogo filtrable por categoría / nivel.
- [ ] Service `app/services/reports/catalog.py` con función de cálculo registrada por id de sección.
- [ ] Pruebas: catálogo no rompe seed; cada id tiene función de cálculo registrada.

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

### # PENDING — US-123 — Engine de render con modos composición A/B

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

### # PENDING — US-124 — Canvas drag-and-drop + preview en vivo

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

### # PENDING — US-125 — Panel de parámetros transversales

**Como** PM
**Quiero** configurar área, ventana temporal, top N, modo resumen/detalle, ordenamiento y agrupación de cada sección desde un panel uniforme
**Para** no tener que aprender un UI distinto por sección.

**Criterios de aceptación:**
- [ ] Componente `<SectionParamsPanel>` que lee `data_contract` de la sección y renderiza form correspondiente.
- [ ] Parámetros transversales aplican según `applies_to` declarado en el catálogo (área, ventana, top N, modo, orden, agrupación).
- [ ] Validación: ventana ≤ rango del proyecto; top N ≥ 1.

**Test cases:** TC-216 form se construye dinámicamente desde data_contract; TC-217 validaciones funcionan.

### # PENDING — US-126 — Plantillas privadas + publicar al proyecto

**Como** PM
**Quiero** guardar mi canvas como plantilla privada y opcionalmente publicarla al proyecto
**Para** reusarla en los próximos cortes o compartirla con otros PMs del mismo proyecto.

**Criterios de aceptación:**
- [ ] Botón "Guardar como plantilla" → modal con nombre + visibility (private/project).
- [ ] Plantillas privadas solo las ve el owner; publicadas al proyecto las ven todos los miembros del proyecto.
- [ ] Galería "Mis plantillas" + "Plantillas del proyecto" en la pantalla de canvas.
- [ ] Permisos: solo el owner puede publicar/despublicar la suya.

**Test cases:** TC-218 privacidad respetada; TC-219 publicar/despublicar; TC-220 RLS por proyecto.

### # PENDING — US-127 — Modo IA conversacional construyendo el reporte

**Como** PM
**Quiero** un panel de chat lateral donde le pido a la IA "agrega los hitos críticos de las próximas 3 semanas" y la IA agrega la sección con los parámetros correctos
**Para** construir reportes hablando, sin tocar el catálogo manualmente.

**Criterios de aceptación:**
- [ ] Panel chat lateral colapsable en `/builder`.
- [ ] IA tiene tool calls registrados: `add_section(id, params)`, `remove_section(idx)`, `update_section_params(idx, params)`, `reorder_section(from, to)`.
- [ ] Modelo: reusa cascada EP008 (Groq plataforma o BYO tenant).
- [ ] Cada acción del IA es revisable + revertible por el PM (transcript visible).
- [ ] Contexto inyectado: lista del catálogo + data del proyecto.

**Test cases:** TC-221 IA llama add_section con id válido; TC-222 PM puede revertir; TC-223 fallback entre modelos.

---

## Niveles 1 y 2 — Módulos UI

### # PENDING — US-128 — Módulo UI Reportes Nivel 1 (PMO Portafolio)

**Como** usuario PMO
**Quiero** una ruta `/pmo/reports/portfolio` con listado de reportes generados + botón "Nuevo reporte de portafolio"
**Para** generar y consultar reportes Nivel 1.

**Criterios de aceptación:**
- [ ] Ruta y sidebar item nuevos.
- [ ] Listado de reportes generados (histórico) con filtros por plantilla, fecha, creador.
- [ ] Botón "Nuevo reporte" → selector de plantilla seed (L1-PORTAFOLIO) o "desde blanco" → canvas Nivel 4 con flag `level=1`.
- [ ] Permisos: solo roles PMO / admin del tenant.

**Test cases:** TC-224 acceso restringido por rol; TC-225 listado paginado; TC-226 generar desde seed.

### # PENDING — US-129 — Módulo UI Reportes Nivel 2 (Organización / Programa)

**Como** PMO o cliente con acceso
**Quiero** un tab "Reportes" en el detalle de organización/programa
**Para** generar reportes Nivel 2 con scope filtrado a esa org.

**Criterios de aceptación:**
- [ ] Tab "Reportes" en `/pmo/organizations/{id}` y `/pmo/programs/{id}`.
- [ ] Listado + botón nuevo, símil US-128.
- [ ] Plantilla seed L2-ORG aplicada por default con scope filtrado a la org/programa.
- [ ] Permisos: usuarios con acceso a la organización (incluye clientes).

**Test cases:** TC-227 scope filtrado; TC-228 RLS por org; TC-229 cliente puede consultar.

---

## Exports y suscripciones

### # PENDING — US-130 — Export PDF de reportes custom

**Como** PM
**Quiero** descargar el reporte custom como PDF con el mismo estilo de los reportes operativos
**Para** compartirlo fuera de la plataforma.

**Criterios de aceptación:**
- [ ] Endpoint `POST /reports/{id}/export?format=pdf` reusa motor US-037.
- [ ] Plantilla base + plantilla por sección (extendida del motor US-123).
- [ ] Footer con metadata: PM, fecha emisión, plantilla aplicada, scope.

**Test cases:** TC-230 PDF valida `%PDF` header; TC-231 incluye todas las secciones del canvas.

### # PENDING — US-131 — Suscripciones de reportes custom

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

### # PENDING — US-132 — Render headless del Gantt WBS-1 para S-19

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

## Plan de sprints sugerido

| Sprint | Bloque | Items | Foco |
|---|---|---|---|
| **26** | 1 | ENH-097, ENH-098, ENH-099, ENH-100, ENH-101 | Dependencias del sistema (modelo + admin UI) |
| **26** | 2 | US-120, US-121, US-122 | Backbone catálogo + cálculo + plantillas seed |
| **27** | 1 | US-123, US-130 | Motor de render + export PDF |
| **27** | 2 | US-124, US-125, US-126 | Canvas Nivel 4 (drag-drop + params + plantillas privadas) |
| **28** | 1 | US-127 | IA conversacional |
| **28** | 2 | US-131 | Suscripciones custom |
| **29** | 1 | US-128, US-129 | Módulos UI Niveles 1 y 2 |
| **29** | 2 | US-132 | Render headless Gantt |

**Estimado:** 4 sprints (~8 semanas) para EP020 completo, sujeto a velocidad real.

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
