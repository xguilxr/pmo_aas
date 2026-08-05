# SPRINT-DONE-HISTORY.md — Histórico de bloques completados (Sprint 1 v1.0 MVP)

> **Propósito:** Archivo de referencia histórica. Los bloques completados se mueven aquí desde SPRINT.md cuando se cierra un sprint. Permite que SPRINT.md mantenga solo lo pendiente para el sprint activo.

---

## Batches 2026-06-08 → 2026-07-18 — archivados desde `SPRINT.md` el 2026-08-03

> Archivados durante la acción 5 del plan de conformidad MCA
> (`docs/conformidad/plan.md`). `SPRINT.md` estaba en 521 líneas contra su
> propio límite declarado de ~250. Todo lo de abajo estaba `status:fix-committed`
> o cerrado; lo que seguía abierto se quedó en `SPRINT.md`.

### Mini-batch Plan UX (2026-07-18, owner por chat)

- **ENH-199** — Preview de import: 30 filas con scroll, jerarquía indentada,
  chips de estado, hitos ◆ — "como se ve en sistema". (`05496f3`)
- **ENH-200** — Botón '+' por fila del plan con menú Sub-tarea / Al mismo
  nivel; calcula el siguiente WBS y abre el form pre-llenado. (`34d4947`)
- **ENH-201** — Form de Nueva tarea en UNA línea (orden de columnas del
  plan/plantilla; avanzado colapsado). (`44b8f08`)
- **US-193** — Plantilla/export del plan profesional (aprobada sobre XLSX de
  muestra + ajuste Helvetica): una hoja estilo MS Project — encabezado, KPIs
  vivos, actividades, Gantt vivo por formato condicional; parser detecta la
  fila de headers automáticamente. (`5f683a4`)

> **ENH-202** (Helvetica en todos los exports) sigue **abierto** — no se
> archiva. Vive en `SPRINT.md`.

### Batch Feedback 16-jul (2026-07-18) — COMPLETO 8/8

Triage: `docs/epics/drafts/feedback-16jul-mejoras.md`. OK del owner por chat
(decisiones C/D delegadas: salud manual CONVIVE con motor auto, fecha libre
por evaluación, edición desde heatmap Y lista). Items 1-2 del PDF ya resueltos
por el batch Plan Import Revamp.

- **BUG-091** — RAID: riesgo con status legacy (minutas IA creaban
  'identified') ineditable → fix origen + update tolerante + mig 0095
  (data-only) + normalización FE. (`2859365` + `c662542`)
- **ENH-195** — RAID: campo Responsable en alta (pool completo) → vista
  resumen fiel. (`ce2cc28`)
- **ENH-196** — RAID: lista en 2 líneas por fila, 5 columnas combinadas, sin
  scroll horizontal. (`2f60c91`)
- **ENH-197** — Plan: jerarquía WBS por ancestro existente más cercano
  (rollup + chevron). (`80b9308`)
- **US-190** — Revisión de calidad del plan: 10 checks + score +
  `GET /plan/quality` + botón/modal. (`24e314c`)
- **US-191** — Salud 5+1 con historial: mig 0096 `project_health_evaluations`
  + POST/GET + modal con evolución. (`66971ba`)
- **US-192** — Portafolio: Evaluar por fila en heatmap + dot clickeable en
  /pmo/projects + Reporte de salud XLSX + `GET /dashboard/health-evaluations`.
  (`e135a2b`)
- **ENH-198** — Recursos: % Uso (teórica vs FTE) + filtro área/sub-área en
  Personas. (`828774f`)

**Migraciones:** **0095** (data-only RAID legacy), **0096** (health evaluations).

### Batch Plan Import Revamp (2026-07-18, branch `claude/plan-import-wbs-fixes-nwotng`) — COMPLETO 9/9

Epic: EP009. Diseño: `docs/epics/drafts/plan-import-revamp.md` (`585e80e`).
Sin migraciones.

**Bloque A — fidelidad de datos:**
- **BUG-088** — WBS fiel al archivo: parser respeta `number_format`
  (1.30 ≠ 1.3), plantilla/export fuerzan texto en WBS, warnings de celdas
  irrecuperables + huérfanos en preview, fix `compareWbs` FE. (`37c66ae`)
- **BUG-089** — % avance robusto: detección de formato % por celda (no por
  columna), sanity check anti-4500%, warnings por fila. (`48b33c3`)
- **BUG-090** — Confirm aplica lo que la plantilla promete: Responsable
  (fuzzy vs actors), Hito Relacionado (por WBS), Predecessors (JSON +
  TaskDependency + successors), Fin desde duración. (`b11c932`)

**Bloque B — contrato único + wizard:**
- **ENH-191** — Estado importable end-to-end (alias + normalización ES/EN +
  confirm aplica status). (`a39b3dc`)
- **ENH-192** — Wizard re-mapea TODOS los campos + preview interpretado en
  vivo (parsed_preview + POST /repreview). (`d86dbed`)
- **ENH-193** — Export/download backend = 15 columnas de la plantilla V1 +
  orden real del plan (no outline-first). (`63b34c2`)

**Bloque C — plantilla inteligente + IA + UX:**
- **ENH-194** — Plantilla con hoja Proyecto (charter) + hoja Gantt en Excel
  (mini MS Project); export con Gantt de datos reales. (`d2e4624`)
- **US-188** — Import inteligente IA 3 niveles: mapeo por contenido,
  normalización de valores en confirm, /ai-structure + use_ai_structure.
  (`eaaabce`)
- **US-189** — UX de import para no-PMs: drag & drop, resumen llano, mapeo
  colapsado, estrategias en llano. (`7acfaab`)

### Batch Revamp 1.0 — Portafolio/Salud/Recursos/Tablas/IA (2026-07-08, branch `claude/pmo-portfolio-architecture-6hbuen`, PR #570)

Ejecución directa por chat (0.1 solucionar>documentar; issues GitHub no
creados). Diseño: `docs/epics/drafts/portfolio-recursos-capacidad.md`.

**Decisiones del owner:** solo `resource_type` (sin origin); subárea = `teams`
(no `parent_area_id`); sin workstream; gobernanza de asignaciones diferida; UN
solo semáforo de salud (unifica `health_status` + `status_rag`, override manual
con razón, estilo avance ENH-155); memoria IA = extensión EP008 + reducir
prompts hardcodeados; Cambios/Lecciones heredan estructura RAID (se quedan a
nivel proyecto, export propio); Plan sin sort, solo chips de color de status.

**Bloque Salud:**
- **US-180** — Salud única híbrida BE: servicio `project_health`, mig 0091
  (unifica status_rag → override con razón), `GET health-detail` +
  `PATCH health`, dims a snapshots. (`0f96dec`)
- **US-181** — Salud UI: HealthStatusCard + declarar con razón + drill-down
  "¿por qué?" + foco PM + heatmap por dimensiones en N1
  (`GET /dashboard/health-matrix`); form ya no edita salud. (`0c0ad7d`)

**Bloque Tablas:**
- **ENH-186** — Cambios hereda RAID: sort, filtros, chips, inline título/tipo,
  toggle finalizados, export XLSX propio. (`acf8d46`)
- **ENH-187** — Lecciones hereda RAID: sort, filtros, chips inline,
  responsable, export XLSX propio. (`8114214`)
- **ENH-188** — Plan: chips de color para estados. (`d735e76`)
- **ENH-185** — /pmo/projects: filtros programa/sin-programa/prioridad mínima.
  (`9bb3338`)

**Bloque Recursos:**
- **US-182** — Pool de recursos sobre `actors` (mig 0092: tipo, función,
  seniority, escasez, skills, capacidades, flags) + API + admin UI. (`c3fdf7e`)
- **US-183** — FTE% + motor de saturación (mig 0093) + página /pmo/resources +
  conflictos + dimensión recursos del health. (`4aec20c`)
- **US-184** — Alertas de capacidad: 3 reglas sobre EP011, sweep semanal +
  fast-path, dedupe 7d. (`595dc4f`)

**Bloque IA (extensión EP008):**
- **US-185** — Memoria de proyecto (mig 0094 `project_ai_contexts`): contexto +
  instrucciones + resumen acumulativo IA, inyección en minutas/reportes, página
  /pmo/projects/[id]/ai-context. (`9770161`)
- **ENH-189** — Prompts composables: instrucciones permanentes por tenant
  (admin /admin/ai) + prompt_builder + fix prompts-catalog. (`a440efa`)

**COMPLETO 11/11** · Verificación: 728 pytest + 1 skip · ruff limpio · tsc +
next build verdes.

**Fase 2 (owner 2026-07-09) — mismo PR #570 — COMPLETA 3/3:**
- **ENH-190** — Label Organización/Portafolio configurable por tenant
  (`settings.org_label`, admin UI + branding + sweep de labels). (`7eca69b`)
- **US-186** — Organigrama con utilización: monthly_utilization + hojas
  Organigrama/Uso mensual con alertas 🟡 ≥80% / 🔴 >100% + 4 endpoints
  (proyecto extendido, programa, org, global). (`fa200bd`)
- **US-187** — Botones de descarga por nivel (org/programa/global en
  /pmo/resources) + EP017. (`42ed974`)

**Migraciones:** 0091-0094.

### Batch WBS+RAID+Áreas (2026-06-29, branch `claude/task-wbs-raid-updates-9nq7ns`)

Ejecución directa por chat del owner. Issues no creados en GitHub (batch
directo, 0.1 solucionar>documentar); IDs canónicos abajo.

**Plan / WBS:**
- **US-177** — Tags de atraso separados: "Atrasada" (rojo, no completada +
  vencida) y "Completada con atraso" (amarillo, cerró tarde). Rename
  Retrasada→Atrasada en chips/filtros/KPIs/reportes/S-17 (mig 0090). (`f05aa69`)
- **ENH-180** — Quitar drag de tareas + botón Auto-WBS; agrupado por WBS como
  default para mostrar/esconder. (`e959e30`)
- **ENH-181** — WBS automatizable: elegir tarea padre + "Bajar nivel"
  (siguiente número disponible del sub-nivel) en form nueva/edición. (`148e57f`)
- **ENH-182** — Centrar checkmarks de Criticidad e Hito. (`312f44c`)

**RAID:**
- **US-179** — Estados RAID unificados a 4 (Abierto/En Progreso/On Hold/
  Resuelto) con tags de color + detención (razón, dependencia área+responsable,
  tiempo detenido). Mig 0089. (`97af0ca`)
- **US-178** — Edición inline de todos los campos de la lista RAID + botón
  Editar (modal, vuelve a la lista) + Borrar; folio link, título inline.
  (`2e26269`)
- **BUG-084** — Fecha de creación respetada (no "hoy") + fecha compromiso se
  guarda/limpia (exclude_unset). (`392a2ef`)

**Áreas / Recursos:**
- **BUG-085** — Crear área desde un proyecto (deriva org del proyecto +
  auto-assignment + propagación org→hijos / program→proyectos /
  proyecto→queda). (`dc98be4`)
- **BUG-086** — Recursos/áreas asignados a un proyecto asignables en RAID
  (servicio `area_visibility`; eligible-actors incluye actores de áreas
  visibles). (`dc98be4`)
- **ENH-183** — En proyecto listar sólo asignados + "traer existente" al crear
  (áreas; recursos ya soportado; equipos siguen su área; roles globales).
  (`14a4037`)
- **BUG-087** — Las áreas de las tareas ya no desaparecen un instante en el
  Plan (loadAreas en paralelo). (`2ddc1bd`)

Epics actualizadas: EP006 (RAID), EP009 (plan), EP017 (áreas) + DB-CHANGES.
**Migración:** 0089, 0090.

### Batch feedback owner (2026-06-29, branch `claude/task-form-layout-parsing-amjjmj`)

Incluye el batch previo "Form de tarea / parsing import / minuta docx"
(5 items: 3 BUG + 2 ENH, `status:fix-committed`).

- **BUG-081 #562** — Import lee 100% como 1%: `_coerce_progress`/`parse_xlsx`
  detectan el `number_format` de la columna de avance y escalan las fracciones
  %-formateadas ×100 (openpyxl da 1 para 100%). (`4f78e5a`)
- **BUG-082 #563** — Evolución de avance en 0s: el snapshot (`avg_progress`)
  usa el rollup WBS derivado (`plan_rollup_map`), no la columna
  `Project.progress` stale. (`ac103df`)
- **BUG-083 #564** — Subir minuta .docx daba 400 de Groq: endpoint backend
  `/ai/extract-text` (python-docx) + front lo usa para .docx; hardening de
  reintentos 4xx + log del body. (`f5ebca2` + `a202cea`)
- **ENH-178 #565** — Form editar tarea compacto + Modal con scroll interno
  (cap al viewport, size `xl`). (`2675d49`)
- **ENH-179 #566** — Matching de columnas del import en grilla de tarjetas
  (mapeo separado de la vista previa). (`07702de`)

Epics actualizadas: EP004 (snapshot avg_progress derivado), EP008
(extract-text), EP009 (parser %, modal, matching) — commit `e784a41`.
Verificación: pytest de las suites tocadas verdes (56+ TC) · ruff limpio ·
tsc + next build verdes.

### Sprint 35 — Plan page + RAID mejoras (2026-06-28, branch `claude/minutes-plans-upload-error-driwcd`) — COMPLETO 14/14

Ejecución directa por chat del owner (planear + ejecutar de principio a fin).
PR #560 abierto, **CI verde** (run #538).

**Plan page (`/pmo/projects/[id]/plan`):**
- **ENH-161** — Quitar botón CSV. (`9b19b6b`)
- **ENH-162** — Mover Plantilla/Importar/Descargar al header (nivel título +
  breadcrumbs).
- **ENH-163** — Columna HITO junto a CRITICIDAD en la lista.
- **ENH-164** — Reemplazar botón MSP por configurador de columnas
  (obligatorias: WBS, TAREA, ÁREA, INICIO, FIN, AVANCE, ESTADO, CRITICIDAD,
  HITO).
- **ENH-165** — Agrupación por WBS nivel 0 (colapsa todo, sólo raíces).
- **US-171** — "Fecha de Cierre" editable + lógica de atraso para cerradas +
  tag "Retrasada" rojo (BE + mig 0086 + FE + docs).
- **US-172** — Auto-WBS con niveles + anti-duplicados (BE endpoint
  renumber-wbs + botón FE).
- **US-173** — Edición inline de tareas (área dropdown, fechas calendario,
  avance dblclick, estado dropdown, criticidad+hito checkmarks).

**RAID (`/pmo/projects/[id]/raid`):**
- **ENH-166** — Listas excluyen finalizados por default + orden por
  estado/severidad (+ toggle "Mostrar finalizados").
- **ENH-167** — Filtros de área en RAID.
- **ENH-168** — Descarga individual por tipo (R/A/I/D) + mantener el de 4
  hojas (BE `?only=` + FE).
- **US-174** — Kanban con drag (avanzar/retroceder fase) + toggle
  Lista/Kanban por tipo.
- **US-175** — Edición inline RAID (estado inline en listas R/A/I/D).
- **ENH-169** — Alinear/complementar campos RAID: análisis + recomendaciones
  en `UIUX-ANALYSIS-Sprint35.md`.

**Migración:** 0086.

### Follow-ups post-análisis UIUX-ANALYSIS-Sprint35 (branch `claude/minutes-plans-upload-error-driwcd`)

**Fase 1 — quick wins:**
- **ENH-170** — Ícono Diamond para Hito (consistencia DS). (`bef532e`)
- **ENH-171** — RAID: menú "Exportar ▾" + hint del Kanban. (`0cf014b`)
- **ENH-172** — Unificar label "Nota de cierre" en issues RAID. (`a7ee838`)

**Fase 2-3:**
- **ENH-173** — Edición inline "on-click" (`InlineSelectCell`) + updates
  optimistas con revert (Plan y RAID). (`4fb79fb`)
- **ENH-174** — A11y del Kanban: botones ←/→ por tarjeta (teclado). (`2083113`)

**Fase 4 — aprobada por owner excepto auto-WBS (2026-06-28):**
- **ENH-175** — Columna Responsable en listas RAID + resolución Actor en el read.
- **ENH-176** — Severidad inline en riesgos (probability/impact, optimista).
- **ENH-177** — `category` para issues (mig 0087 + UI detalle).
- **US-176** — Auto-WBS / orden manual: **versión mínima** (columna
  `tasks.position` mig 0088, endpoint `/tasks/{id}/move`, drag por fila con
  handle en vista plana sin filtros, `list_tasks`/`renumber-wbs` respetan
  `position`). Draft `docs/epics/drafts/auto-wbs-position.md` con lo diferido
  (drag de subárbol, orden por hermanos).

**Migraciones:** 0087, 0088.

### Hotfix — Error "No se pudo conectar" al subir minutas/planes (2026-06-28, branch `claude/minutes-plans-upload-error-driwcd`)

Reporte: usuario no podía subir minutas/planes ("No se pudo conectar con el
servidor"); Railway mostraba `sqlalchemy.exc.MultipleResultsFound`. Auditoría
encontró 5 sitios `scalar_one_or_none` sobre cláusulas WHERE no únicas + el
enmascaramiento CORS.

- **BUG-078** — `MultipleResultsFound` al subir planes/documentos: endurece 5
  lookups (`tasks.py` import merge ×2, `modules.py` document versioning ×2,
  `_validate_area` JOIN). (`2071b93`)
- **BUG-079** — Los 500 no manejados ahora salen con headers CORS (handler
  global en `main.py`), así el front muestra el error real en vez de "No se
  pudo conectar". (`7d94012`)
- **BUG-080** — El export CSV de auditoría incluye la columna `details`
  (contexto del job). (`ff33937`)

Verificación: 5 TC nuevos + 83 TC de suites relacionadas verdes · ruff limpio.

### Sprint 34 Bloque 1 — Roles + Visibilidad + Recursos (2026-06-08, branch `claude/friendly-bell-EYlVB`)

Aprobado por owner 2026-06-08 (plan + decisiones en sesión).

- **ENH-159 #551** — Nav sidebar: proyectos sin programa bajo "Sin Programa".
- **US-166 #552** — Rol `pm_sr`: nuevo role_type con acceso admin completo.
- **US-167 #553** — Modelo `UserScopeAssignment`: asignaciones de visibilidad
  para PM.
- **US-169 #555** — UI: árbol de asignación Org→Prog→Proyecto en admin de
  usuarios.
- **US-170 #556** — Catálogo de áreas/equipos/actores a nivel organización.

> **US-168 #554** (filtrado de API y sidebar por visibilidad de PM) quedó
> `status:in-progress` y **no se archiva**. Vive en `SPRINT.md`.

### ENH-160 #558 — Inactividad con blur + re-login (2026-06-25, branch `claude/nice-thompson-omcizv`)

Inactividad pasa de logout duro a bloqueo con blur + overlay de re-login (no se
pierde progreso). (`0b6811c`). tsc + next build verdes. Epic EP001 actualizado.

### Notas de sesión archivadas

- **2026-06-06 (batch feedback owner — MERGED #549 a main 2026-06-07):** branch
  `claude/owner-feedback-batch`, 5 commits atómicos, sin migraciones. CI verde.
  - **ENH-155** — Avance derivado del plan (rollup WBS jerárquico): padre =
    promedio de avance de hijos recursivo; general = promedio de nivel más alto.
    Read-side en lista de tareas, resumen de proyectos, detalle, dashboard
    (KPIs/charts/plan-vs-actual) y reporte de avance; manual como fallback para
    proyectos sin plan. Helper `compute_wbs_rollup` + `round_half_up` en
    `plan_metadata.py`.
  - **ENH-156** — Salud/semáforo solo-color (sin "Green"/"Verde"): reporte de
    avance (`.dot`), charter `.docx` (● coloreado) y 5 vistas read-only del
    front. No se tocaron los selectores interactivos.
  - **ENH-157** — Logos PMO+cliente en el `.docx` del charter
    (`resolve_charter_logos`, disco + httpx, solo PNG/JPEG). Complementa
    ENH-153, que cubrió el header HTML/PDF.
  - **ENH-158** — Borrar/cancelar tickets de RAID/Lecciones/Cambios:
    soft-delete + audit; Cambios además cancela (status `cancelled`) e invalida
    los ApprovalToken EP019. Cualquier miembro puede hacerlo.
  - **BUG-077** — Guardar minuta devolvía 422 (título < 2 chars): guard ≥2 +
    parser del 422 nativo de FastAPI en `lib/api.ts`. Re-aplicado en
    `minutes/new/page.tsx` tras el merge.
  - ⚠️ **Nota de IDs:** los commits aterrizaron etiquetados `ENH-109/110/111/112`
    y `BUG-062` — se eligieron contra una base desactualizada (`9c904a2`, max
    ENH-108/BUG-061) antes de ver los 196 commits de main, que ya habían
    consumido esos números (ENH-109/110 = #417/#418, ENH-111/112 = #430/#431,
    BUG-062 = "click en minuta abre el detail"). Historia ya mergeada → **no se
    reescribe**; los IDs **canónicos** de este batch son
    **ENH-155..158 / BUG-077**.

- **2026-06-05 (batch gantt/áreas/reportes/RAID fixes):** branch
  `claude/gantt-areas-fixes`, 9 commits de trabajo, `status:fix-committed`.
  Sesión previa: BUG-073/074/076 #538/539/542 + ENH-150/151/153 #540/541/543.
  Esta sesión cerró los 4 restantes: ENH-149 #544 (ya estaba implementado, solo
  verificación), BUG-075 #545 (estado RAID editable), ENH-154 #546 (sección
  Acciones en Seguimiento), ENH-152 #547 (export RAID XLSX 4 hojas ES
  unificado). Sin migraciones. Epics EP006/EP014/EP018 actualizadas.

---

## Batches post-Sprint 33 mergeados a main — 2026-05-26 → 2026-05-29

> Archivados desde `SPRINT.md` IN-PROGRESS el 2026-06-05 (branches confirmadas mergeadas a `origin/main` vía `git branch -r --merged`).

### Batch "deepwork reportes/RAID/IA/charts" — branch `claude/deepwork-reports-raid-ai-charts` (2026-05-28/29)
- BUG-069 #524 — charts: donut se llena al 100% (Pie con stroke-dasharray), colores de marca en programa, dedup de métricas, KpiCard compartido, empty states más limpios.
- ENH-146 #525 — reportes con logos (PMO+cliente, data-URL) + paleta/tipo on-brand (PDF y HTML inline) + donut/gauge reales + KPI cards + gantt inline (S-19) + fix on_time_pct.
- ENH-147 #526 — minutas→RAID confiables: json_mode por proveedor + parser tolerante (fences/comas) + repair-retry sin pérdida silenciosa.
- US-165 #527 — asistente IA conversacional: modelo de conversación (mig. **0084**) + endpoint /assistant + widget flotante global (Ctrl/⌘-K).
- ENH-148 #528 — housekeeping: README/env/epics al día, sin Ollama, dead code removido (require_permission, workspaces field).
- Diferidos (no bloqueantes): dashboard eyebrows (NEEDS-VISUAL-CHECK), KPI band en builder.html, borrado de packages/sdk (riesgo frozen-lockfile), dedup de RAID por chunk.

### Batch "bugs logos + /pmo + rediseño big canvas" — branch `claude/friendly-lamport-LZ45l` (2026-05-26)
- BUG-068 #514 (e87c55f + 70f377a) — upload PNG de logos de org (data-URL en DB, mig. **0082**) + preview circular. Follow-up: logo del tenant a data-URL (mig. **0083**).
- ENH-142 #515 (1ad5ed3) — botones crear org/programa/proyecto en /pmo.
- ENH-143 #516 (c7551b4) — org detail: botón Nuevo proyecto, renombra Status, quita toggle Resumen/Reportes.
- US-164 #517 (766f9f4) — rediseño "big canvas" global (lienzo cream + sidebar azul flotante + topbar full-width + pinch-zoom + dark mode). Supersede chrome navy DEC-006.
- Doc follow-up diferido (US-164): navigation.md + ADR/DEC del supersede de chrome navy DEC-006.

### Batch "chrome: logo full-size + iconos org/programa" — branch `claude/gracious-pascal-MPjsq` (2026-05-26)
- ENH-144 #520 (e5f70e1) — logo del tenant a tamaño completo en topbar + branding "PMO-aaS"; elimina el nombre del tenant en texto.
- ENH-145 #521 (d5974a9) — iconos distintos: organizaciones `Building2`, programas `Layers`; corrige mislabel del nav admin.

---

## Sprint 1 (v1.0 MVP) — Completado 2026-04-21

### ✅ DONE (histórico reciente Sprint 1)

| US | Título | Commit | Fecha |
|---|---|---|---|
| US-001 | Setup inicial — análisis de gaps v1→v2 | `docs: gap analysis v2` | 2026-04-20 |
| US-002 | Tablas business_units + departments + FKs | `feat(org): US-002 — tablas BU y departments con FK` | 2026-04-20 |
| US-003 | CRUD Business Units API | `feat(org): US-003 — CRUD Business Units API` | 2026-04-20 |
| US-004 | CRUD Departments API | `feat(org): US-004 — CRUD Departments API` | 2026-04-20 |
| US-005 | Sidebar org tree nav (Frontend) | `feat(web): US-005 — sidebar org tree nav` | 2026-04-20 |
| US-006 | Vista paneles de organizaciones (cards + métricas) | `feat(web): US-006 — paneles de organizaciones` | 2026-04-20 |
| BUG-001 | Fix 404 en página de Programas | `fix(web): BUG-001 — crea /admin/programs` | 2026-04-20 |
| US-007 | Toggle dark/light mode en dropdown usuario | `feat(web): US-007 — toggle dark/light en user dropdown` | 2026-04-20 |
| US-008 | Toggle de idioma (ES/EN) en dropdown usuario | `feat(web): US-008 — toggle idioma en user dropdown` | 2026-04-20 |
| US-010 | Color chrome #182e4e + Senior PMO como admin | `feat(auth): US-010 — chrome #182e4e + Senior PMO admin` | 2026-04-20 |
| US-009 | Página /account (perfil + cambiar password) | `feat(web): US-009 — página /account perfil + password` | 2026-04-20 |
| US-011 | Campos adicionales en solicitud + FK BU/Depto | `feat(requests): US-011 — campos adicionales en solicitud` | 2026-04-20 |
| US-012 | Project Charter: tabla + generación al aprobar | `feat(requests): US-012 — project_charters + auto-gen` | 2026-04-20 |
| US-013 | Charter aparece como documento del proyecto | `feat(requests): US-013 — charter como documento` | 2026-04-20 |
| US-014 | Filtro de organización en dashboard | `feat(dashboard): US-014 — filtro organización` | 2026-04-20 |
| BUG-002 | Fix distorsión en gráficas de barra | `fix(dashboard): BUG-002 — distorsión gráficas barra` | 2026-04-20 |
| US-015 | KPIs respetan jerarquía de roles | `feat(dashboard): US-015 — KPIs respetan jerarquía roles` | 2026-04-20 |
| BUG-003 | Fix layout Plan vs Real + columna PM | `fix(dashboard): BUG-003 — layout Plan vs Real` | 2026-04-20 |
| US-016 | Unificar Plan + Gantt en una pestaña | `feat(projects): US-016 — unificar plan + gantt` | 2026-04-20 |
| US-018 | Módulo Áreas/Organigrama del proyecto | `feat(projects): US-018 — módulo áreas del proyecto` | 2026-04-20 |
| US-019 | Consolidar RAID (vista unificada) | `feat(projects): US-019 — consolidar RAID` | 2026-04-20 |
| US-020 | Categorías de documentos actualizadas | `feat(projects): US-020 — categorías de documentos` | 2026-04-20 |
| US-021 | Consolidar pestañas de Minutas | `feat(projects): US-021 — consolidar minutas` | 2026-04-20 |
| US-022 | Módulo Reportes dentro del proyecto | `feat(projects): US-022 — módulo reportes` | 2026-04-20 |
| US-023 | Gestión de Tenant (info + stats + editar) | `feat(admin): US-023 — gestión de tenant` | 2026-04-20 |
| US-024 | Gestión jerarquía org (BU + Depto) en Admin | `feat(admin): US-024 — jerarquía org en admin` | 2026-04-20 |
| US-025 | Iconos en paneles de tenant + jerarquía | `feat(superadmin): US-025 — iconos en paneles` | 2026-04-20 |
| US-026 | Visión General = Tenants + Health unificados | `feat(superadmin): US-026 — visión general unificada` | 2026-04-20 |
| US-031 | Upload y display del logo del tenant en chrome | `feat(branding): US-031 — upload y display del logo del tenant en chrome` | 2026-04-20 |
| US-032 | Restructurar sidebar principal (drill-down real) | `feat(web): US-032 — sidebar drill-down real; elimina duplicado y módulos de proyecto` | 2026-04-20 |
| US-033 | Panel de organización → página de recursos reales | `feat(web,api): US-033 — panel de organización con recursos reales` | 2026-04-20 |
| US-034 | Página resumen de programa | `feat(web,api): US-034 — página resumen de programa con KPIs y donut` | 2026-04-20 |
| US-035 | Tabs inline en detalle de proyecto (supersede US-017) | `feat(web): US-035 — tabs inline en detalle de proyecto (supersede US-017)` | 2026-04-20 |
| US-036 | Restructurar sidebar Admin (4 ítems raíz) | `feat(web): US-036 — sidebar admin con 4 ítems raíz y /admin/tenant tabbed` | 2026-04-20 |
| US-037 | Infra compartida de exportación a PDF (WeasyPrint) | `feat(api): US-037 — infra de exportación a PDF con WeasyPrint + Jinja2` | 2026-04-20 |
| US-038 | Reporte de Avance de Proyecto (Python, BD, PDF) | `feat(api,web): US-038 — reporte de avance ejecutable sin IA` | 2026-04-20 |
| US-039 | Reporte de Seguimiento de Actividades (Python, BD, PDF) | `feat(api,web): US-039 — reporte de seguimiento por responsable` | 2026-04-20 |
| US-040 | Formato estandarizado + export de Minuta IA (.pdf/.docx/.md/.txt) | `feat(api,web): US-040 — export estandarizado de minuta` | 2026-04-20 |
| US-041 | Sidebar super admin aislado (4 ítems raíz) | `feat(web): US-041 — sidebar super admin aislado (4 ítems raíz)` | 2026-04-20 |
| US-042 | Página `/superadmin/users` cross-tenant | `feat(api,web): US-042 — /superadmin/users cross-tenant` | 2026-04-20 |
| US-043 | Visión General con Health al top | `feat(web): US-043 — health al top en visión general del superadmin` | 2026-04-20 |
| US-044 | Runbook Ollama + Cloudflare Tunnel + nssm | `docs(ai): US-044 — runbook Ollama + Cloudflare Tunnel + nssm` | 2026-04-20 |
| US-045 | Config + smoke test del túnel + secrets cifrados | `feat(api,web): US-045 — config y smoke del modelo IA local (Cloudflare Tunnel)` | 2026-04-20 |
| BUG-004 | Railway no redeploy tras PR #20 — troubleshooting documentado | `fix(infra): BUG-004 — Railway auto-deploy troubleshooting tras PR #20` | 2026-04-21 |
| BUG-005 | Sidebar super admin respeta user.is_superadmin en first paint | `fix(web): BUG-005 — sidebar super admin respeta user.is_superadmin en first paint` | 2026-04-21 |
| US-046 | Runbook Ollama + Tailscale (reemplaza CF Tunnel) | `docs(ai): US-046 — runbook Ollama + Tailscale (reemplaza CF Tunnel)` | 2026-04-21 |
| US-047 | Refactor config Ollama a Tailscale (quita CF-Access) | `feat(api,web): US-047 — refactor config Ollama a Tailscale (quita CF-Access)` | 2026-04-21 |
| US-048 | Sidecar Tailscale en worker Railway + config por-tenant en OllamaProvider | `feat(worker): US-048 — sidecar Tailscale en worker Railway + config por-tenant en OllamaProvider` | 2026-04-21 |
| US-049 | DNS routing pmo-aas.com (Railway + HostGator) | `docs(infra): US-049 — DNS routing pmo-aas.com (Railway + HostGator)` | 2026-04-21 |
| US-050 | Landing estático www.pmo-aas.com en HostGator | `feat(landing): US-050 — landing estático www.pmo-aas.com en HostGator` | 2026-04-21 |
| BUG-006 | Runbook Ollama+Tailscale §3.2 — advertir PATH no refrescado en PowerShell | `fix(docs): BUG-006 — runbook Tailscale §3.2 advierte PATH no refrescado en PowerShell` | 2026-04-21 |
| US-051 | Mover generación IA (minuta + reporte) a Celery worker con polling | `feat(api,web): US-051 — IA minuta+reporte dispatchan a Celery worker; UI hace polling a /ai/jobs/{id}` | 2026-04-21 |
| BUG-010 | Topbar duplica logo tenant; reemplazar por "PMO · aaS" | `fix(web): BUG-010 — topbar muestra "PMO · aaS" plataforma en vez de duplicar logo tenant` | 2026-04-21 |
| ENH-002 | Sidebar raíz "Organizaciones" → "PMO" | `feat(web): ENH-002 — sidebar nodo raíz "Organizaciones" → "PMO"` | 2026-04-21 |
| BUG-021 | Superadmin post-login redirect a /superadmin | `fix(web): BUG-021 — superadmin redirect post-login a /superadmin` | 2026-04-21 |
| BUG-011 | KPI "Riesgos abiertos" sin href (evita 404) | `fix(web): BUG-011 — KPI sin href` | 2026-04-21 |
| BUG-012 | KPI "Riesgos severos" sin href (evita 404) | `fix(web): BUG-012 — KPI sin href` | 2026-04-21 |
| BUG-013 | KPI "Cambios en revisión" sin href (evita 404) | `fix(web): BUG-013 — KPI sin href` | 2026-04-21 |
| BUG-014 | KPI "AIDs abiertos" sin href (evita 404) | `fix(web): BUG-014 — KPI sin href` | 2026-04-21 |
| BUG-015 | Dashboard filtros Plan vs Real horizontales en sm+ | `fix(dashboard): BUG-015 — filtros horizontales` | 2026-04-21 |
| BUG-016 | Botón Cancelar de nueva solicitud usa variant danger (rojo) | `fix(requests): BUG-016 — cancelar danger variant` | 2026-04-21 |
| BUG-019 | Panel org abre resumen en /[id]; edición en /[id]/edit | `fix(web): BUG-019 — panel organización abre resumen` | 2026-04-21 |
| ENH-004 | Tabs de proyecto centradas | `feat(web): ENH-004 — tabs-bar centrado` | 2026-04-21 |
| ENH-003 | Botón "Nuevo programa" en toolbar de organizaciones | `feat(org): ENH-003 — botón Nuevo programa` | 2026-04-21 |
| BUG-020 | Runbook Ollama+Tailscale §4: solo Allow (sin Block Any) | `fix(docs): BUG-020 — runbook §4 solo Allow tailnet` | 2026-04-21 |
| ENH-008 | EP009 (MSP/xlsx) reclasificado a v1.1; botón en UI disabled | `docs(epics): ENH-008 — EP009 a v1.1 + botón Importar MSP disabled en UI` | 2026-04-21 |
| BUG-022 | Documentos sin file_url muestran "Sin archivo" (UX) | `fix(projects): BUG-022 — documentos sin file_url` | 2026-04-21 |
| BUG-017 | Crear proyecto desde solicitud abre charter para complementar | `fix(requests): BUG-017 — crear proyecto desde solicitud abre charter` | 2026-04-21 |
| BUG-018 | Nuevo proyecto auto-crea charter + redirige a editarlo | `fix(projects): BUG-018 — nuevo proyecto auto-crea charter` | 2026-04-21 |
| BUG-008 | Chrome en dark mode alineado con paleta gris | `fix(web): BUG-008 — chrome dark mode paleta gris` | 2026-04-21 |
| BUG-009 | Theme consistency post-login vía pmoaas:user-updated | `fix(web): BUG-009 — theme post-login consistency` | 2026-04-21 |
| ENH-001 | Componente BackLink + integración en detalles | `feat(web): ENH-001 — componente BackLink` | 2026-04-21 |
| ENH-005 | Resumen cambia botones a tarjetas KPI | `feat(projects): ENH-005 — tarjetas KPI en Resumen` | 2026-04-21 |
| ENH-006 | Editor de tareas integrado en /plan; /tasks → redirect | `feat(projects): ENH-006 — editor inline en /plan` | 2026-04-21 |
| ENH-007 | Matriz P×I inline en pestaña Riesgos del RAID | `feat(projects): ENH-007 — matriz P×I inline` | 2026-04-21 |
| US-053 | Preview "ojito" estilo Jira en RAID/Lecciones/Minutas | `feat(web): US-053 — preview ojito` | 2026-04-21 |
| US-052 | Sidebar cross-tenant Proyectos/RAID/Cambios/Minutas/Reportes | `feat(web,api): US-052 — sidebar + vistas cross-tenant` | 2026-04-21 |
| ENH-009 | Reconectar hrefs dashboard a /admin/raid y /admin/changes | `feat(dashboard): ENH-009 — reconecta hrefs KPIs` | 2026-04-21 |
| ENH-010 | Endpoints cross-tenant incluyen folio+name del proyecto | `feat(api,web): ENH-010 — folio+name en cross-tenant` | 2026-04-21 |
| BUG-007 | WeasyPrint libs nativas en Dockerfile (cierra 502 de Reporte Avance) | `fix(infra): BUG-007 — libs WeasyPrint en Dockerfile` | 2026-04-21 |
| US-027 | Notificaciones in-app (tabla + API + bell + página) | `feat(api,web): US-027 — notifications in-app` | 2026-04-21 |
| US-028 | Email notifications vía Resend + preferencias + runbook | `feat(api,web,docs): US-028 — email via Resend + preferencias + runbook` | 2026-04-21 |
| ENH-011 | `AI_TIMEOUT_S` env leído en OllamaProvider (antes hardcoded a 120s) | `feat(ai): ENH-011 — leer AI_TIMEOUT_S de env en OllamaProvider` | 2026-04-21 |
| US-054 | Config de AI a nivel de plataforma (superadmin): tabla `platform_ai_settings` + endpoints + UI | `feat(ai,superadmin): US-054 — platform_ai_settings editable por superadmin` | 2026-04-21 |

---

### Bloque 1-22 (Sprint 1 v1.0 MVP completados — ver SPRINT.md anterior para detalles)

**Resumen:** 22 bloques (+ hotfixes intercalados) completados con ~94 items (US, BUGs, ENHs). Sprint 1 cierra v1.0 MVP productivo.

**Bloques principales:**
- Bloque 1-8: Jerarquía org, topbar, charter, dashboard, proyecto, RAID, admin, superadmin.
- Bloque 9-11: Refactores de navegación (sidebar principal, admin, superadmin).
- Bloque 12-16: IA local + notificaciones.
- Bloque 18-22: Hotfixes operativos + tuning post-pruebas.
- Bloque 17: CANCELADO (EP012 MySQL HostGator, ver DEC-013).

**Status:** v1.0 MVP en producción con todas las features bloqueantes. Listo para pruebas masivas.

---

**Última actualización:** 2026-05-05 (cierre Sprint 9)

---

## Sprint 2 (v1.1) — CERRADO 2026-04-23

**18 items en 4 bloques + hotfix Railway. Branch consolidado a main.**

### Bloque 1 — Setup: navegación + bugs + permisos (7 items) ✅
- [x] BUG-026 — Auth: timeout de inactividad a 15 minutos — #87 ✅ 77dc093
- [x] US-055 — Export tareas (CSV/Excel) — Opción A descarga instantánea — #71 ✅ 023a99c
- [x] ENH-012 — Sidebar: módulo "Módulos de Proyecto" — #72 ✅ e2e420f
- [x] ENH-013 — Botón "Nuevo Programa" abre modal en Organizaciones — #73 ✅ b47f19a
- [x] BUG-023 — Project Charter: link a editor cuando no hay archivo — #74 ✅ d81d036
- [x] BUG-024 — Lógica de uploads no configurada — #75 ✅ 3cd997d
- [x] BUG-025 — Rol "Reportes" sin módulo de permisos — #76 ✅ b1954c7

### Bloque 2 — Reportes + Dashboard (5 items) ✅
- [x] ENH-014 — Reportes: filename datetime + preview PDF — #77 ✅ 02cfaa6
- [x] US-056 — Calendarizar reportes vía Resend — #78 ✅ 51947ef
- [x] ENH-015 — Dashboard: expandir barra navegación — #80 ✅ 55956f9
- [x] ENH-017 — RAID: filtros en línea horizontal — #82 ✅ 6832199
- [x] ENH-016 — Solicitudes: reabrir si proyecto no existe — #81 ✅ ade6ee7

### Bloque 3 — RAID + Áreas (5 items) ✅
- [x] ENH-019 — RAID: filtros avanzados (status + severidad) — #85 ✅ fe3b001
- [x] ENH-018 — RAID: agregar toggle Kanban — #84 ✅ c894f12
- [x] US-058 — RAID: preview panel editable + comentarios — #83 ✅ e239caa
- [x] ENH-020 — Áreas: múltiples recursos/contactos — #86 ✅ 009c0f2
- [x] US-062 — Áreas/Recursos: Area Leader + recursos asignados — #91 ✅ 009c0f2

### Bloque 4 — IA multi-modo (1 item) ✅
- [x] US-057 — IA multi-modo por tenant: disabled / platform (Groq) / byo — #79 ✅ (9 commits, hotfix 40c4176)

---

## Sprint 3 (v1.2) — CERRADO 2026-04-24

**5 items en 2 bloques.**

### Bloque 1 — Limpieza post-v1.1 + Auth self-service (2 items) ✅
- [x] ENH-021 — Superadmin AI: quitar defaults editables Ollama — #96 ✅ b70c887
- [x] US-063 — Recuperación y cambio de contraseña por correo — #95 ✅ (6 commits)

### Bloque 2 — Cleanup IA legacy post-DEC-017 (3 items) ✅
- [x] BUG-027 — /admin/tenant: retirar dropdown Modo IA + form Ollama — #100 ✅ 1b62045
- [x] ENH-022 — Housekeeping docs/ai/ + archivar EP016 — #102 ✅ 6315d19
- [x] ENH-023 — Retirar sidecar Tailscale del worker — #103 ✅ f541171

---

## Sprint 4 (v1.3) — CERRADO

**14 items en 4 bloques.**

### Bloque 1 — Reworks del review (8 items) ✅
- [x] BUG-015 — Dashboard: botón "Exportar CSV" rework — #40 ✅ d3523bb
- [x] BUG-029 — Upload Excel falla + botón sin styling — #105 ✅ 3f6ac90
- [x] ENH-003 — Modal "Nuevo programa" en /admin — #50 ✅ b47f19a
- [x] ENH-024 — Reporte: filename correcto al descargar — #106 ✅ 33c043c
- [x] ENH-025 — Filtros RAID horizontales definitivo — #107 ✅ ca9dc1d
- [x] ENH-026 — Consolidar Panel RAID en /admin/raid — #108 ✅ 8d69623
- [x] ENH-027 — Panel editable RAID en /admin/projects/[id]/raid — #109 ✅ 3001959
- [x] ENH-028 — Export tareas Excel MPP-like + CSV BOM UTF-8 — #110 ✅ f1db32a

### Bloque 2 — Infra + RAID robusto + charter + PMO (5 items) ✅
- [x] US-066 — Uploads: object storage S3 (Cloudflare R2) — #113 ✅ e0f9c2e
- [x] BUG-028 — Charter .docx real en bucket + editable — #104 ✅ 342e2b3
- [x] US-064 — RAID: área obligatoria + responsable + fechas — #111 ✅ 798c89f
- [x] US-065 — RAID: página dedicada + historial — #112 ✅ 76277ac
- [x] US-068 — Página PMO de organización separada de admin — #116 ✅ 8f78d9b

### Bloque 3 — Import Project/Excel (1 item) ✅
- [x] US-067 — Import XLSX → tareas — #114 ✅ e9ef28b

### Bloque 4 — Auth simplificada post-DEC-020 (2 items) ✅
- [x] US-059 — Roles Admin/User/Viewer + backend gate — #88 ✅ 13eca87
- [x] US-060 — Hook useMyPermissions + gate UI — #89 ✅ 4fd19ca

---

## Sprint 5 (v1.4) — CERRADO

**10 items en 6 bloques + 1 follow-up.**

### Bloque 0 — Hotfix admin lockout ✅
- [x] BUG-031 — Admin lockout post-US-059/060 — #121 ✅ PR #129

### Bloque 0.5 — Infra CI ✅
- [x] ENH-030 — Acelerar suite tests + CI Fase 1/2/3 — #130 ✅ PR #131
- [x] ENH-032 + ENH-033 — Ruff + path filters + concurrency — #133/#138 ✅ PR #139
- [x] ENH-031 — Engine session-scoped + clean tables — #132 ✅ PR #141 a5cfab1

### Bloque 1 — SuperAdmin safety net ✅
- [x] US-072 — SuperAdmin: editar role_type — #125 ✅ PR #134
- [x] US-073 — SuperAdmin: overrides permisos por tenant (DEC-021) — #126 ✅ PR #140 (mig 0027)
- [x] US-074 — SuperAdmin: cambiar email + password — #127 ✅ PR #134

### Bloque 2 — Import inteligente de planes ✅
- [x] US-069 — Import MPP nativo vía MPXJ (OpenJDK 21) — #122 ✅ PR #143
- [x] US-070 — Wizard de mapeo de columnas Excel/CSV/MPP — #123 ✅ PRs #146 + frontend
- [x] US-071 — Plantilla vacía descargable del plan — #124 ✅ PR #135

### Bloque 3 — Refactor navegación TO-BE ✅
- [x] US-075 — Recursos de proyecto bajo /pmo/* (DEC-022) — #128 ✅ 33b0c7a

### Follow-ups detectados
- [x] ENH-034 — Diagnosticar bottleneck 38s en 9 tests — #142 ✅ (causa: Celery .delay() sin broker)

---

## Sprint 6 (v1.5) — CERRADO 2026-04-25

**5 items en 5 bloques. PR #156 mergeado a main. Suite 339 pass / 1 skip.**

### Bloque 1 — Refactor backend permisos ✅
- [x] US-076 — Modelo capability-based + migración 0028 — #151 ✅ fabf8c3

### Bloque 2 — Eliminar UI/endpoints legacy de roles ✅
- [x] US-077 — Borrar /admin/roles/*, role-editor.tsx, admin_roles.py — #152 ✅ fc93bb3

### Bloque 3 — UI nueva gestión users + capabilities ✅
- [x] US-078 — /admin/users/[id] (10 acciones) + /admin/permissions + mig 0029 — #153 ✅ 1fc8ad8

### Bloque 4 — Tests matriz role × endpoint ✅
- [x] US-079 — test_permission_matrix.py con clasificación estática — #154 ✅ 2a0315a

### Bloque 5 — Cierre actualización docs ✅
- [x] US-080 — Consolidar EP001, DECISIONS, DB-CHANGES, CLAUDE.md, SPRINT.md — #155 ✅

---

## Sprint 7 (v1.6) — CERRADO 2026-04-28

**10 items en 6 bloques (1 diferido a v2.0). PR #169 mergeado a main 2026-04-28.**

### Bloque 0 — Hotfix verificación post-Sprint 6 ✅
- [x] BUG-032 — SuperAdmin /me email change con take-over — #159 ✅ 2f86f38
- [x] BUG-033 — UI superadmin dropdown role inline — #160 ✅ 3ad5e9a

### Bloque 1 — Charter universal + downloads ✅
- [x] BUG-034 — Documents download via presigned URL R2 — #161 ✅ 49358e8
- [x] US-083 — Charter universal + descarga DOCX/PDF — #165 ✅ c740a59

### Bloque 2 — RAID polish ✅
- [x] ENH-036 — RAID detail page edit form — #162 ✅ a48aa2b
- [x] BUG-035 — RAID comments con nombre del autor — #163 ✅ 7766281

### Bloque 3 — Reportes Resend funcional ✅
- [x] BUG-036 — Scheduled reports beat + run-now — #166 ✅ e441a07

### Bloque 4 — Tenant ↔ SuperAdmin permission tickets ✅
- [x] US-082 — Tickets de permisos con notif email — #164 ✅ 3533d21

### Bloque 5 — UX programas ✅
- [x] ENH-037 — Botón Nuevo Programa /pmo/orgs/[id] — #167 ✅ c5798bf

### Diferido a v2.0
- ENH-035 #158 — Análisis profundo optimización CI tests pesados (post-MVP).

### Migraciones agregadas
- 0030 charter_for_legacy_projects
- 0031 permission_change_requests

---

## Sprint 8 (v1.7) — CERRADO 2026-04-29

**13 items entregados (12 completed + 1 not_planned). Branch `claude/fix-issue-resolution-S3i4e`. Cerrado por batch cleanup (decisión owner: solucionar > documentar, ver CLAUDE.md §0).**

### Bloque 0 — Hotfix prod api deploy ✅
- [x] BUG-039 — Boolean default Postgres-compatible permission_change_requests — #184 ✅ 62c4f96

### Bloque 1 — Solicitud cambios chicos ✅
- [x] ENH-038 — Mostrar fecha solicitud + restricción entrega — #170 ✅ 86d5936
- [x] BUG-037 — Botón Enviar UX con campos faltantes — #171 ✅ 09af27c
- [x] ENH-039 — Cambios: mostrar aprobador + fechas — #172 ✅ 04cf8a7

### Bloque 2 — Solicitud cambios medianos ✅
- [x] ENH-040 — Presupuesto opcional — #173 ✅ c62109b
- [x] ENH-041 — BU select catálogo + "Otra…" — #174 ✅ b04818e

### Bloque 3 — Plan + Minutas UX ✅
- [x] US-084 — Plan: edición manual con flag — #175 ✅ a6f5b7a
- [x] ENH-042 — Minutas: IA como primary action — #176 ✅ 58ee920

### Bloque 4 — Cambios grandes (MVP foundation) ✅
- [x] US-085 — Solicitud "Otra…" org + creación inactiva + notif — #177 ✅ 21eb835
- [x] US-086 — Stakeholders catálogo Opción B — #178 ✅
- [x] US-087 — Reportes KPIs numéricos + fechas — #179 ✅ deee5a8

### Bloque 5 — Workaround docs ✅
- [x] ENH-043 — Programas cross-empresa workaround + ADR-016 — #180 ✅ 6cf20c4

### Bloque 6 — CI improvement ✅
- [x] ENH-044 — CI gate alembic upgrade head Postgres efímero — #185 ✅ 2f9c458

### Reverificados — ya implementados en Sprint 7 ✅
- [x] BUG-035 — RAID detail sidebar nombre — #163 ✅ 4193f24 (cherry-pick)
- [x] BUG-040 — Documents extensión + 1MB — #186 ✅ a5c3a2c (cherry-pick)
- [x] BUG-033 — role_type editable modal — #160 ✅ 711be4e (cherry-pick)
- [x] ENH-036 — RAID detail edit form — #162 ✅ a48aa2b
- [x] US-082 — Tickets permisos tenant→SA — #164 ✅ 3533d21
- [x] US-083 — Charter universal + DOCX/PDF — #165 ✅ c740a59

### Cerrados sin código
- [-] BUG-038 — Solicitud "Pendiente" + "Aprobada" simultáneo — #181 cerrado `not_planned` (sin repro).

### Migraciones agregadas
- 0032 project_request_delivery_date (ENH-038)
- 0033 project_request_budget_nullable (ENH-040)
- 0034 project_manual_edited_fields (US-084)
- 0035 stakeholders_catalog (US-086)

---

## Sprint 9 (v1.8) — CERRADO 2026-05-05

**6 items entregados en 2 bloques + hotfix UX. Branch `claude/resolve-merge-conflicts-4MmJK` (PR #213 mergeado a main 044dc08).**

### Bloque 1 — Hard delete two-step ✅
- [x] US-088 — Hard delete two-step para 6 entidades admin (programs/orgs/BUs/depts/users/stakeholders) + ADR-017 — #189 ✅
  - Backend: `core/hard_delete.py`, `schemas/hard_delete.py`, 12 endpoints (preview + DELETE permanent).
  - Frontend: `components/hard-delete-button.tsx` reusable + clientes API.
  - Tests: 9/9 passing. Suites EP002 + EP007 + US-042 = 42/42 sin regresión.

### Bloque 2 — Batch 3 items ✅
- [x] ENH-045 — Password policy 12 → 8 chars — #192 ✅ 990d138
- [x] US-089 — Email bienvenida con creds al crear usuario (Resend + must_change_password) — #193 ✅ 77ac31b
- [x] ENH-046 — Reportes programados: día de semana + hora (recurrentes) y fecha + hora (one-time) + migración 0036 — #194 ✅

### Hotfix UX post-US-088 ✅
- [x] BUG-041 — Documents bajan como `.file` (Content-Disposition fix) — #191 ✅
- [x] (chore) Botón "Desactivar" con icono `PowerOff` + label visible en 6 entidades.
- [x] (docs) README actualizado a estado Sprint 9 v1.8.

### Diferidos (follow-up)
- Hard-delete de User cuando hay `project_request.requested_by` bloqueado — futuro endpoint reasignación.
- Lista organizations (cards) sin botón inline de hard-delete — entrar al detalle es el lugar natural.

### Limpieza branches
- `claude/sprint-issues-backlog-setup-EMiLA` → SAFE TO DELETE (6 commits ahead, todos superseded por cherry-picks Sprint 8).

---

## Sprint 10 (v1.9) — CERRADO 2026-05-06

**14 items entregados en 6 bloques. Branch `claude/archive-sprint-tasks-Ee7XC` (PR #215 mergeado a main `7e03332`).**

### Bloque 1 — Plan visualización ✅
- [x] ENH-047 — Toggle agrupación por WBS en lista de tareas — #196 ✅ 8457513
- [x] ENH-048 — Filtros chip multi-select Hitos / Críticos / Retrasados — #197 ✅ be046e6
- [x] ENH-049 — Columna Responsable visible en lista — #198 ✅ 2b743c0

### Bloque 2 — Plan template + columnas ✅
- [x] ENH-050 — Campo "Hito Relacionado" en form de tarea — #199 ✅ b3a9202
- [x] ENH-051 — Campo "Criticidad" en form de tarea — #200 ✅ 58afc29
- [x] US-090 — Outline Level / Duration / Predecessors / Successors — #201 ✅ ec694a1

### Bloque 3 — Plan import/export UX ✅
- [x] ENH-052 — Botones Plantilla/Descargar/Importar misma fila + colores distintos — #202 ✅ 2ab9bb1
- [x] ENH-053 — Mapeo de columnas asistido por IA al importar — #203 ✅ 006b8ee

### Bloque 4 — RAID editable completo ✅
- [x] ENH-054 — Toda la información de ítems RAID editable inline/modal — #204 ✅ 1c4c854

### Bloque 5 — Áreas / Equipos / Actores ✅
- [x] US-091 — Jerarquía Área→Equipo→Actor + teléfono + UI rediseñada — #205 ✅ 4ec5877

### Bloque 6 — Reportes 3 vistas + cadencia mensual ✅
- [x] ENH-055 — Reportes layout 3 vistas (Catálogo / Historial / Creación) — #209 ✅ 2554baa
- [x] US-092 — Historial de reportes generados (DB + R2) — #210 ✅ 728fe06
- [x] ENH-056 — Reportes programados: cadencia mensual con día del mes (1-31) + clamp — #212 ✅ 5b74e34
- [x] US-093 — Creación con IA + preview (tercera vista) — #211 ✅ bbd8b4b

### Migraciones agregadas
- 0037 task_criticality (ENH-051)
- 0038 task_related_milestone (ENH-050)
- 0039 task_outline_pred_succ (US-090)
- 0040 scheduled_reports_dom (ENH-056)
- 0041 project_areas_team_phone (US-091)
- 0042 report_history (US-092)

### Notas
- 14 commits referenciando 14 issues; todos siguen `OPEN` con `status:ready` — owner cierra manualmente tras verificación (CLAUDE.md §3 paso 7).
- BUG-042 (#206) + BUG-043 (#207) creados en triage Sprint 10 quedaron asignados a Sprint 11 desde el inicio (decisión owner 2026-05-05).

---

## Sprint 16 (v1.14) — CERRADO 2026-05-07

> Sprints 11-15 quedan provisionalmente en `SPRINT.md` hasta verificación owner; Sprint 16 entró/salió completo en la misma cadencia y se archiva aquí para no contaminar el archivo activo.

### Bloque 1 — Reportes (4 issues entregados, todos `state:closed completed`)
- [x] US-101 #253 — "Crear reporte con IA" — fix Groq init + endpoint `POST /reports/ai-generate` + reglas globales de orden (agrupar por área, fecha-fin más cercana primero) — closed 2026-05-07
- [x] ENH-071 #250 — Reglas/condiciones de filtrado configurables (rango fechas custom + área/fase/responsable/severidad multi-select + persistencia localStorage) — closed 2026-05-08
- [x] ENH-072 #251 — Ordenamiento configurable por columna + persistencia por template — closed 2026-05-07
- [x] ENH-073 #252 — Refresh visual (DM Sans + JetBrains Mono, KPI cards pastel clicables, segmented tabs, drawer detalle, dual-mode HTML interactivo + PDF render server-side) — closed 2026-05-07

### Notas
- Sprint 16 fue parte del paquete Sprint 13-16 triagado 2026-05-06 con scope original "Reportes refinement". Entregado y cerrado en menos de 48h.
- Status final: todos los issues llegaron a `closed completed` por owner.
- Sin migraciones Alembic.

---

## Sprint 17 (v1.16) — CERRADO 2026-05-08

### Bloque 0 — BUG-053 cleanup Ollama (gate pre-arranque)
- [x] BUG-053 #254 — Eliminación de runtime Ollama embebido / configuración legacy — MERGED PR #297

### Bloque 0.5 — US-104 BYO config
- [x] US-104 #298 — Módulo BYO: test-before-save + custom provider + retry — entregado
- Branch sesión: `claude/setup-ai-module-8HYs1`

### Bloque 1 — IA conversacional global → POSTERGADO
- US-102 / ENH-074 / ENH-075 / ENH-076 (#255-#258) movidos a Deferred 2026-05-08.

---

## Sprint 18 (v1.17) — CERRADO 2026-05-08

### Bloque 1 — Documentos & Plan vivo (3 issues)
- [x] US-106 #308 — Sistema de Artefactos por proyecto — `6e2f947`
- [x] ENH-081 #309 — Charter auto-creación + backfill + completeness banner — `0b43755`
- [x] ENH-080 #310 — Plan vivo: regeneradores xlsx/csv + fallback mpp — `13f51ed`

**Migraciones:** 0055 (project_artifacts table) + 0056 (charter backfill).
Branch: `claude/review-start-next-sprint-R8JWc`.

### Diferidos del bloque
- US-106 CA6 endpoint genérico de upload (cubierto vía endpoints nativos).
- Tab Organigrama placeholder hasta redefinición Áreas/Recursos.
- US-105 #311 wizard matching responsables — Deferred a Sprint 25 EP017.

---

## Sprint 19 (v1.18) — CERRADO 2026-05-09

### Bloque 1 — RAID polish + vistas dedicadas (6 issues)
- [x] US-107 — risk_actions + assignees N:N + endpoints — `9d94fc9`
- [x] ENH-082 — Export RAID 4 sheets con styling — `0c59aaa`
- [x] ENH-083 — RiskActionsCard inline en raid-detail-page — `5eb6b69`
- [x] ENH-088 — Floating preview RAID — `e021a97`
- [x] ENH-086 — Lessons dedicated page — `b3798d9`
- [x] ENH-087 — Changes dedicated page — `4d91009`

**Migraciones:** 0057 (risk_actions).
Branch: `claude/continue-sprint-tasks-jR3zt`.

---

## Sprint 20 (v1.19) — CERRADO 2026-05-09

### Bloque 1 — IA Minutas (5 issues)
- [x] ENH-084 — Prompt + post-procesador con `_normalize_raid_block` — `719fe50`
- [x] US-108 — CRUD minuta + bulk approve crea tickets reales — `236990a`
- [x] BUG-055 — Cancel endpoint + worker check — `eb9baa9`
- [x] ENH-090 — Preview page con 4 secciones colapsables + editor embebido — `a392350`
- [x] ENH-091 — Confirm modal en lista — `8188685`

**Migraciones:** 0058.
Branch: `claude/continue-sprint-tasks-jR3zt`.

---

## Sprint 21 (v1.20) — CERRADO 2026-05-09

### Bloque 1 — Reportes redesign HTML (4 issues)
- [x] ENH-085 — Tabla `report_templates` + columna `reports.html_content` — `73bf661`
- [x] US-111 — `html_report_renderer` reusable para reportes y minutas — `8c33cbd`
- [x] US-109 — Tweaker UI + endpoint sync `/ai/reports/tweak-html` — `69d1e84`
- [x] ENH-089 — `/reports/{id}/export?format=html|pdf|txt` — `fdac553`

**Migraciones:** 0059.
Branch: `claude/continue-sprint-tasks-jR3zt`.

---

## Sprint 22 (v1.21) — CERRADO 2026-05-09

### Bloque 1 — Cambios / Approval workflow (2 issues)
- [x] US-112 — Backend con migración 0060 + tablas `change_approvers` + `approval_tokens` — `e72b445`
- [x] US-113 — Endpoints públicos + landing `/approve/[token]` — `e44efdc`

**Migraciones:** 0060.
JWT HS256 firmado con `APPROVAL_TOKEN_SECRET`; DB guarda solo SHA256 hash. Re-trigger borra tokens previos. Email cae a `logger.info` cuando EP011 no expone `send_email`.

---

## Sprint 23 (v1.22) — CERRADO 2026-05-09

### Bloque 1 — BYO universal + Copilot M365 (1 issue)
- [x] US-110 — BYO universal (custom OpenAI-compat) + Azure OpenAI / Copilot M365 — `1c5674d`

Sin migraciones (settings.ai.byo soporta dict flexible).
Branch: `claude/continue-sprint-work-mcmzX`.

**Diferido:** CA4 enforcement (rate-limiter activo) hasta que se reporten costos descontrolados; los límites se persisten ya y `load_tenant_ai` los propaga al worker.

---

## Sprint 24 (v1.23) — CERRADO 2026-05-09

### Bloques 1+2+3+4 — Feedback batch (12 items)
- [x] BUG-056 + ENH-092 + BUG-057 + ENH-093 + ENH-094 + ENH-095 + ENH-096 + BUG-058 + US-109 (rework) + US-111 (rework) + BUG-059 + BUG-060.

Sin migración Alembic. 12 commits separados sobre branch `claude/fix-project-charter-issues-RFoAy`.

**Highlights:**
- Helper `app.services.filename_slug` con patrón canónico `{project-slug}-{kind}.{ext}` reusado por Charter / Plan / RAID.
- `MeetingMinuteCreate` ahora acepta `raid_suggestions`; `MeetingMinuteUpdate` extendido con `participants/topics/agreements` editables desde preview.
- Prompt MINUTE_SYSTEM mejorado para bullets de 2-5 oraciones.
- `ensure_duration_max_21` se vuelve no-op (warning visual en plan).
- `download_report_history` y `export_report?format=html` respetan `rep.html_content` (último tweak) e `inline=true`.
- `update_provider_config` permite `body.byo=null` cuando hay config previa.

---

## Sprint 25 (v1.24) — CERRADO 2026-05-10

### Bloques 1+2 — EP017 Directorio de Proyecto (5 issues)
- [x] US-114 #349 — Schema additivo: `project_participations` + `project_roles` + actors enriquecido — `6842344` (migración 0061)
- [x] US-115 #350 — API: endpoints participations + project_roles + servicio `derived_assignment` — `49ea588`
- [x] US-116 #351 — UI: tab Directorio + DirectoryView + AddPersonModal + EditParticipationModal — `a24212f`
- [x] US-117 #352 — eligible-actors endpoint + PersonPicker + lessons.owner_actor_id (migración 0062) — `4236214`
- [x] US-118 #353 — Fase 1 doble escritura `project_members → project_participations` — `2896787`

**Migraciones:** 0061 + 0062.
Branch: `claude/design-areas-resources-8DIfi`.
Epic doc: `docs/epics/EP017-project-directory.md`.

### Diferidos (sin issue, no bloqueantes)
- `/admin/areas` rediseño completo (Toggle 2 con 5 sub-tabs).
- Cableado de `PersonPicker` en cada formulario existente (TaskAssigneeDropdown, RiskOwnerDropdown, IssueOwnerDropdown, ChangeApproverPicker, LessonOwnerDropdown, ParticipantPicker minutas).
- Filtros/agrupadores de Plan por dimensiones derivadas (depende de PersonPicker integrado + ENH-077).
- US-118 Fases 2 (RBAC migra a leer participations) y 3 (drop project_members).
- US-119 cleanup: drop legacy actors.team_id, actors.is_lead, teams.area_id, tasks/risks/issues.area_id.

---

## Sprints 11-15 — CERRADOS (verificación owner posterior)

### Sprint 11 (v1.9) — Cerrado 2026-05-06
Bloques 1+2+3 — Nav review, Nav cleanup (cierra patrón BUG-042), RAID polish. Migración Alembic 0042.

### Sprint 12 (v1.10/v1.11) — Cerrado 2026-05-06
Bloques 1+2+3 — Plan fixes + plantilla, Admin restructure, Reportes refinamiento. Migración Alembic 0043 (backfill `tasks.outline_level`).

### Sprint 13 (v1.12) — Cerrado 2026-05-07
Bloque 1 — Áreas + Plan (7 issues). Migraciones 0044 (areas/teams/actors) + 0045 (tasks.area_id).

### Sprint 14 (v1.13) — Cerrado 2026-05-07
Bloque 1 — RAID detail redesign "Denso" (4 issues, #246-#249). Rewrite completo de `raid-detail-page.tsx` (188→765 líneas). Sin migraciones.

### Sprint 15 (v1.14) — Cerrado 2026-05-07
Bloque 1 — Áreas refinement + Plan responsables (4 issues, #263-#266). Migraciones 0048+0049+0050. `project_areas` dropeado; catálogo tenant fuente única; PMO seed global + sync PMO users → Actores.

---

## Sprint 26 (v1.25) — CERRADO 2026-05-22

### Bloque 0 — Minutas v1.0 (1 BUG + 7 ENH)
- [x] **BUG-061 #391** — Preview RAID vs save persistence (lane).
- [x] **ENH-102 #392** — Parser RAID estricto A/R/D/I + validador post-IA + gold standard Highlander — `4fa8072` (PR #408).
- [x] **ENH-103 #393** — Match participantes ↔ actores del proyecto.
- [x] **ENH-104 #394** — Título auto desde nombre de archivo.
- [x] **ENH-105 #395** — Estructura de minuta v1.0 (6 secciones fijas) — `9d637b0` (PR #408).
- [x] **ENH-106 #396** — `meeting_minutes.origin` audit field — `7b7ee3d` (PR #406, migración `20260523_0068`).
- [x] **ENH-107 #397** — `scheduled_minutes` (cron + email) — `c711af5` (PR #407, migración `20260522_0068`).
- [x] **ENH-108 #398** — Copy-paste directo de transcript.

**Branches sesión:** múltiples lanes paralelos (A/B/C/D/E).
**Hotfix:** PR #409 (`fix-alembic-multiple-heads-0068`) — merge migration `20260523_0069` para unificar los heads paralelos 0068.
**Fixtures gold standard:** `apps/api/tests/fixtures/minutes/highlander-eam-bnf-20260323.{txt,expected.json}`.

### Bloque 1 — Dependencias del sistema EP020 (5 ENH)
- [x] **ENH-097 #373** — `tasks.is_critical BOOLEAN` (reemplaza columna `critical` legacy) — migración `20260522_0067`.
- [x] **ENH-098 #374** — `tenants.progress_calculation_method` ENUM por tenant.
- [x] **ENH-099 #375** — `tenants.task_load_thresholds` JSONB por tenant.
- [x] **ENH-100 #376** — `organizations.client_logo_url` + UI upload — migración `20260522_0064`.
- [x] **ENH-101 #377** — `projects.status_rag` declarativo del PM — migración `20260522_0065`.

**Migraciones agregadas:** 0064, 0065, 0066 (merge heads logo+rag), 0067.

### Bloque 2 — Backbone EP020 (3 US)
- [x] **US-120 #378** — `report_sections` catálogo + seed 22 secciones atómicas — `1796189` (PR #411, migración `20260523_0070`).
- [x] **US-121 #379** — Servicio cálculo % avance configurable por tenant — PR #405 (`fe1a857`).
- [x] **US-122 #380** — `report_builder_templates` + 4 plantillas seed (L3-AVANCE, L3-SEGUIMIENTO, L1-PORTAFOLIO, L2-ORG) — `501d66b` (PR #411, migración `20260523_0071`).

**Migraciones agregadas:** 0070, 0071. Hubo collision con revision IDs 0068/0069 (paralelización lane B0 vs lane B2 sin coordinación); fix en `4b12123` renumerando los archivos del lane B2 a 0070/0071.

### Lecciones aprendidas — Sprint 26

1. **Paralelización con migraciones es peligrosa.** Tres alembic-heads-collisions distintos en este sprint:
   - 0064 ↔ 0065 (logo + status_rag desde Bloque 1) — resuelto con 0066 merge.
   - 20260522_0068 ↔ 20260523_0068 (scheduled_minutes + minute_origin del Bloque 0) — resuelto con 20260523_0069 merge.
   - 20260522_0068 ↔ 20260522_0069 vs nombres ya usados por Bloque 0 — resuelto renombrando archivos del Bloque 2 a 0070/0071.
2. **Decisión owner 2026-05-22:** volver a desarrollo **secuencial puro** para evitar este tipo de errores. 1 sesión activa a la vez, 1 lane, 1 branch, 1 migración consecutiva. La paralelización agresiva costó múltiples rondas de fix.
3. **Skill `/handoff` creado** para mantener bridge entre sesiones y forzar cleanup de SPRINT.md.

### Otros artefactos producidos
- `docs/epics/EP020-report-builder.md` — epic oficial con 13 US (US-120 a US-132) + 5 ENH dependencias.
- `docs/epics/drafts/EP020-secciones-atomicas.md` — catálogo de 22 secciones (referencia normativa).
- `docs/epics/drafts/minute-gold-standard.md` — Highlander EAM-BNF (transcript + minuta esperada + pipeline parser IA).
- `.claude/skills/handoff/SKILL.md` — skill para bridges entre sesiones (PR #412).
- 26 issues creados en GitHub (#373-#398), todos con labels aplicados.

---

## Sprints 30-32 (v1.27) — Rediseño Minutas + Reports — Cerrados 2026-05-23

22 items entregados secuencialmente en branch `claude/zen-brown-ivCbz`. Owner decisión 2026-05-23: rediseño grande de Minutas y Reports tras feedback de uso real.

### Sprint 30 — Pre-requisitos + Sidebar + Minutas cosmético (7 items)

**Bloque 1 — Pre-requisitos backend (ya en main vía commits previos):**
- [x] **US-140 #428** — Persistir reports del builder (`d65805c`, verificado).
- [x] **US-136 #424** — Tabs Resumen/Reportes en `/pmo/organizations/[id]` (`a9edbae`).
- [x] **US-137 #425** — Tabs Resumen/Reportes en `/pmo/programs/[id]` (`03f06ff`).

**Bloque 2 — Sidebar + bug + minutas cosmético:**
- [x] **ENH-116 #450** — Sidebar "Módulos" + aplanar dropdown Reportes (`bf423ca`).
- [x] **BUG-062 #451** — Click en nombre minuta abre detail (`bfe4efd`).
- [x] **ENH-117 #452** — Listing minutas simplificado + columnas Folio/Minuta/Fecha/Tipo/Exportar/Preview/Borrar (`7ad1fd8`).
- [x] **ENH-118 #453** — Detail minuta sin MD/TXT export (`89a430b`).

### Sprint 31 — Minutas generador + Reports PMO 4 tabs (7 items)

**Bloque 1 — Minutas generador unificado:**
- [x] **US-143 #455** — Backend `source_type=transcript|minute|manual` + migración 0075 + nuevo `MINUTE_NORMALIZE_SYSTEM` (`1fb672b`).
- [x] **US-142 #454** — Frontend `/minutes/new` con 3 modos. `/ai-minutes/new` redirect 301 (`0bcf138`).
- [x] **ENH-119 #456** — Labels RAID claros en detail (`a6f5ffb`).

**Bloque 2 — Reports `/pmo/reports` 4 tabs:**
- [x] **ENH-120 #460** — Tab "Proyectos" rediseñado + backend enriquece folio/tipo/período + filtra drafts + detail page nuevo (`ba3aae1`).
- [x] **US-144 #457** — Tab "PMO" con descarga Status PMO (`f639d88`).
- [x] **US-145 #458** — Tab "Organizaciones" con filtro org (`ee8ab24`).
- [x] **US-146 #459** — Tab "Programas" con filtros org+programa (`0b5af6a`).

### Sprint 32 — Reports proyecto + Builder unificado (8 items)

**Bloque 1 — Reports proyecto rediseñado:**
- [x] **US-147 #462** — Endpoint Look-ahead + template (`2bd4032`).
- [x] **ENH-122 #463** — `period_from`/`period_to` en Avance/Seguimiento (`bf2eba8`).
- [x] **ENH-121 #461** — 3 tabs Generar/Historial/Programar + 3 paneles default + catálogo builder templates (`5e1c7f8`).
- [x] **ENH-114 #433** — Schedule type=custom (`1d2b04f` preexistente, verificado).

**Bloque 2 — Builder unificado:**
- [x] **US-148 #464** — Header Modo + Ventana value+unit persistida + `?template_id` (`9a14e31`).
- [x] **ENH-123 #465** — Catálogo 22 secciones verificado (sin commit nuevo).
- [x] **ENH-124 #466** — Preview live con marcas A4 (`cb1abff`).
- [x] **ENH-125 #467** — Navigation guard al salir sin guardar (`542ee5a`).

**Cleanup:**
- [x] **chore** — `/reports/tweak` → redirect a `/reports/builder` (`def46f6`).

### Migraciones agregadas
- **0075** — `meeting_minutes.origin` admite `'minute_ai'` (US-143).

### Decisiones de diseño tomadas

1. **Cascarón intencional** para historial PMO/Org/Prog: la persistencia de reportes Level=1/2 requiere decisión de schema (`Report.project_id` nullable o tabla aparte) que owner difiere a sesión separada de diseño del Reporte Status PMO.
2. **`_template` bucket en `default_parameters`** del Builder: persiste `window_days`, `window_value`, `window_unit` sin migración nueva.
3. **Modo manual de minutas** persiste directo en `MeetingMinute` (no pasa por celery) — endpoint distingue por `source_type` y retorna 201 + minute_id en sync (vs 202 + job_id en transcript/minute).
4. **MD/TXT de minutas deprecados en UI** pero backend sigue aceptándolos por compat.

### 16 issues triage cerrados al inicio del Sprint 30

- 12 duplicados exactos (#435-#446 cerrados como `duplicate of`).
- 4 superseded por rediseño: US-135 (#423), US-138 (#426), US-139 (#427), US-141 (#429) — labels conflictantes con la nueva organización de tabs.

---

## 🗂️ Sprint 33 (v1.28) — Dashboards N1/N2 + reportes derivados + revamp — CERRADO 2026-05-26

Branch `claude/laughing-carson-stUJu` (19 commits sobre `origin/main` con #511 ya mergeado). Tests backend 583 passed/1 skipped; ruff + tsc + next build verdes; render real de PDF (WeasyPrint) validado. **Esperando merge a main + QA visual del owner.**

### Fundación de datos (BE)
- [x] **US-151** `77f977c` — modelo `MetricSnapshot` + migración **0079** + servicio de cómputo/persistencia idempotente a 4 niveles (tenant/org/programa/proyecto) + job semanal Celery (lunes 02:00 UTC).
- [x] **US-152** `ab40c73` — endpoints analytics: `/dashboard/trends`, `risk-matrix`, `heatmap`, `treemap`, `POST snapshots/capture`.

### Primitivos + dashboards (FE)
- [x] **US-153** `a6f0ba5` — primitivos SVG (`Gauge`, `TrendLines`, `RiskMatrix`, `Heatmap`, `Treemap`) + píldora de tendencia en `KpiCard` + cliente `lib/api/analytics.ts`.
- [x] **US-154** `af41833` — `/dashboard`: matriz de riesgos + heatmap + tendencias + treemap + botón capturar snapshot.
- [x] **US-155** `44bcac6` — `/pmo`: heatmap + treemap + tendencias del tenant.
- [x] **US-156** `5f9913d` — `/pmo/organizations/[id]` Resumen: salud + riesgos + tendencias org.
- [x] **US-157** `0c9ff4d` — `/pmo/programs/[id]` Resumen: gauges + riesgos + tendencias programa.

### Reportes derivados N1/N2 (BE+FE)
- [x] **US-158** `647795a` — secciones builder **S-05 Tendencia** + **S-15 Matriz** + migración **0080**.
- [x] **US-160** `3451eeb` — reportes de status N1 (portafolio) y N2 (org/programa) en PDF, fuera del builder; endpoints + plantilla `scope_status.html` + botones de descarga.
- [x] **US-161** `ffbb38b` — sección **S-07 Curva-S** (planeado vs real; planeado en `extras.avg_progress_plan`) + migración **0081**.
- [x] **US-163** `6e61149` — heatmap + treemap embebidos en los PDF N1/N2.

### Revamp + follow-ups
- [x] **US-159** `411a44b` — revamp v1: radio de tarjetas 16→10px (`--radius-xl`) + `tabular-nums` global. Navy chrome + paleta intactos.
- [x] **US-162** `360e5ee` — vistas/reportes agregados accesibles a PMs con scoping por `scoped_project_ids` (capturar snapshots sigue admin-only).
- [x] **ENH-141** `9a669c6` — `ProgressGauge` inline del project detail (#511) consolidado en el `Gauge` compartido.

### Migraciones agregadas
- **0079** — `metric_snapshots` (foto semanal de stock, 4 niveles).
- **0080** — seed idempotente secciones `S-05`, `S-15`.
- **0081** — seed idempotente sección `S-07`.

### Decisiones / notas
1. **Snapshots históricos SÍ en v1.x** (revierte el diferido a v2.0): cadencia semanal por scope; el dashboard es fuente de verdad y los reportes se derivan.
2. **S-07 Curva-S reactivada** (estaba "descartada"): el planeado se deriva lineal de `start_date`→`end_date`.
3. **Reportes N1/N2 viven fuera del Report Builder** (que es project-only por migración 0078): generación on-demand vía endpoints dedicados, sin persistir `Report` rows (la persistencia L1/L2 sigue como backlog v2.0).
4. **Vistas agregadas accesibles a PMs** scoped a sus proyectos (decisión owner 2026-05-26).

---

## Sesión 2026-08-05 — auditoría + producto (branch `claude/audit-continuation-fzrtko`)

Dos PR: **#577** (remediación post-R1) y el que sigue. Todo verificado por
mutación, un commit por item.

### Conformidad

- **SUM-02** contenedor sin privilegios · **DES-03** `/health` con `SELECT 1`
  acotado y 503 · **DIS-02** 34/34 pares AA en los dos temas + job
  `contraste-wcag` · **AM-09** límite por IP en el login · **AM-08/SEG-07**
  `audit_log` de solo anexado · **SEG-01** PyJWT · **D-7** y **D-9**.
- **AUT-01** cerró con evidencia observada: el guard interceptó dos comandos en
  sesión real. Con CAP-01 (#576), **MCA alcanza N2**, su objetivo.
- **OPS-02**: el worker no reportaba a Sentry — `sentry_sdk.init` vivía en
  `main.py` y ese proceso arranca `celery` directo. La mitad de producción
  quedaba muda, y era la que menos se ve.

### Producto

| Item | Qué | Migración |
|---|---|---|
| ENH-202 | Helvetica en los cuatro caminos de export; cerró AM-12 | — |
| D-2 | `support` → `hypercare` (ADR-019) | 0098 |
| D-8 | `portfolio_function` → `discipline` (ADR-021) | 0099 |
| AM-10 | Bloqueo de cuenta → retardo creciente | — |
| US-194 | `tasks.wbs` → `wbs_code` (D-3, ADR-020) | **0100** |
| US-195 | Fase `cancelled` (ADR-022) | sin migración |
| US-196 | D-4: índice de consumo + pisos de amarillo | — |
| US-197 | Paleta de gráficos, arco frío (ADR-023) | — |

### Hallazgos que la medición no podía ver

1. **El `REVOKE` de AM-08 no habría funcionado** — la aplicación se conecta con
   el rol dueño y en PostgreSQL el dueño conserva privilegios. Van disparadores.
2. **Los informes llevaban meses saliendo en DejaVu Sans**: el CSS pedía DM Sans
   y la imagen no instalaba ninguna de las fuentes declaradas.
3. **PyJWT 2.10.1 traía 7 CVE propias** — la migración cambiaba cinco por siete.
   Lo cazó `pip-audit` en el primer CI; se subió a 2.13.0.
4. **La migración 0098 escribía en `lessons_learned`**, tabla inexistente, y su
   prueba fijaba el literal del código fuente en vez de la propiedad.
5. **El presupuesto del semáforo no miraba el tiempo**: 85 % gastado con 10 % de
   avance salía verde.
6. **`#dc2626` marcaba «ruta crítica» y el semáforo «en problemas»** en la misma
   página.
