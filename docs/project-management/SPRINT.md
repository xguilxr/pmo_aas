# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-29 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Sesión 2026-07-18 · Branch: claude/plan-import-wbs-fixes-nwotng
DOS batches completos en la misma branch (PR único):

1. "Plan Import Revamp" 9/9 — WBS fiel, estado/% importables, wizard
   completo + IA 3 niveles, plantilla con Gantt, UX no-PM. Sin
   migraciones. Diseño: drafts/plan-import-revamp.md (585e80e).
2. "Feedback 16-jul" 8/8 — RAID fixes, jerarquía WBS, linter de plan,
   salud 5+1 con historial, portafolio, recursos. Migraciones
   0095-0096. Triage: drafts/feedback-16jul-mejoras.md.

Ejecución directa por chat (0.1 solucionar>documentar).
Pendiente: verificación owner + PR + alembic upgrade head (0095-0096).
Próximo libre: US-193, BUG-092, ENH-199.
```

---

## 📥 INBOX / TRIAGE

### Batch Feedback 16-jul (2026-07-18) — COMPLETO 8/8

Triage: `docs/epics/drafts/feedback-16jul-mejoras.md`. OK del owner por
chat (decisiones C/D delegadas: salud manual CONVIVE con motor auto,
fecha libre por evaluación, edición desde heatmap Y lista). Items 1-2
del PDF ya resueltos por el batch Plan Import Revamp.

- [x] **BUG-091** — RAID: riesgo con status legacy (minutas IA creaban
  'identified') ineditable → fix origen + update tolerante + mig 0095
  (data-only) + normalización FE. `status:fix-committed`
  (`2859365`+`c662542`)
- [x] **ENH-195** — RAID: campo Responsable en alta (pool completo) →
  vista resumen fiel. `status:fix-committed` (`ce2cc28`)
- [x] **ENH-196** — RAID: lista en 2 líneas por fila, 5 columnas
  combinadas, sin scroll horizontal. `status:fix-committed` (`2f60c91`)
- [x] **ENH-197** — Plan: jerarquía WBS por ancestro existente más
  cercano (rollup + chevron). `status:fix-committed` (`80b9308`)
- [x] **US-190** — Revisión de calidad del plan: 10 checks + score +
  GET /plan/quality + botón/modal. `status:fix-committed` (`24e314c`)
- [x] **US-191** — Salud 5+1 con historial: mig 0096
  `project_health_evaluations` + POST/GET + modal con evolución.
  `status:fix-committed` (`66971ba`)
- [x] **US-192** — Portafolio: Evaluar por fila en heatmap + dot
  clickeable en /pmo/projects + Reporte de salud XLSX +
  GET /dashboard/health-evaluations. `status:fix-committed` (`e135a2b`)
- [x] **ENH-198** — Recursos: % Uso (teórica vs FTE) + filtro
  área/sub-área en Personas. `status:fix-committed` (`828774f`)

Migraciones nuevas: **0095** (data-only RAID legacy), **0096**
(health evaluations) — correr `alembic upgrade head` en Railway.

### Mini-batch Plan UX (2026-07-18, owner por chat)

- [x] **ENH-199** — Preview de import: 30 filas con scroll, jerarquía
  indentada, chips de estado, hitos ◆ — "como se ve en sistema".
  `status:fix-committed` (`05496f3`)
- [x] **ENH-200** — Botón '+' por fila del plan con menú Sub-tarea /
  Al mismo nivel; calcula el siguiente WBS y abre el form pre-llenado.
  `status:fix-committed` (`34d4947`)
- [x] **ENH-201** — Form de Nueva tarea en UNA línea (orden de columnas
  del plan/plantilla; avanzado colapsado). `status:fix-committed`
  (`44b8f08`)
- [x] **US-193** — Plantilla/export del plan profesional (aprobada
  sobre XLSX de muestra + ajuste Helvetica): una hoja estilo MS
  Project — encabezado, KPIs vivos, actividades, Gantt vivo por
  formato condicional; parser detecta la fila de headers
  automáticamente. `status:fix-committed` (`5f683a4`)
- [ ] **ENH-202** — Helvetica en TODOS los exports/reportes (cambio
  masivo de fuente; el plan ya la usa vía US-193). Plan:
  1. Backend XLSX (openpyxl): helper `export_fonts.py` con
     FONT="Helvetica" aplicado en `raid_export.py`, `change_export.py`
     (y export de Lecciones), `organigrama_export.py` (+ utilización
     US-186) y `plan_regenerator.py`.
  2. PDFs (WeasyPrint): `font-family: Helvetica, Arial, sans-serif`
     en el CSS base de `templates/pdf/**` (reportes, minutas,
     look-ahead, status PMO) y el renderer HTML inline.
  3. DOCX charter (`charter_generator.py`): estilo Normal → Helvetica.
  4. FE ExcelJS: reusar `XLSX_FONT` de plan-template en el reporte de
     salud del portafolio (US-192) y cualquier export client-side.
  Pendiente de arrancar (siguiente batch).

Próximo libre: US-194, BUG-092, ENH-203.

### Batch Plan Import Revamp (2026-07-18, branch: claude/plan-import-wbs-fixes-nwotng)

Epic: EP009. Diseño: `docs/epics/drafts/plan-import-revamp.md`.

**Bloque A — fidelidad de datos:**
- [x] **BUG-088** — WBS fiel al archivo: parser respeta `number_format`
  (1.30 ≠ 1.3), plantilla/export fuerzan texto en WBS, warnings de
  celdas irrecuperables + huérfanos en preview, fix `compareWbs` FE.
  `status:fix-committed` (`37c66ae`)
- [x] **BUG-089** — % avance robusto: detección de formato % por celda
  (no por columna), sanity check anti-4500%, warnings por fila.
  `status:fix-committed` (`48b33c3`)
- [x] **BUG-090** — Confirm aplica lo que la plantilla promete:
  Responsable (fuzzy vs actors), Hito Relacionado (por WBS),
  Predecessors (JSON + TaskDependency + successors), Fin desde
  duración. `status:fix-committed` (`b11c932`)

**Bloque B — contrato único + wizard:**
- [x] **ENH-191** — Estado importable end-to-end (alias + normalización
  ES/EN + confirm aplica status). `status:fix-committed` (`a39b3dc`)
- [x] **ENH-192** — Wizard re-mapea TODOS los campos + preview
  interpretado en vivo (parsed_preview + POST /repreview).
  `status:fix-committed` (`d86dbed`)
- [x] **ENH-193** — Export/download backend = 15 columnas de la
  plantilla V1 + orden real del plan (no outline-first).
  `status:fix-committed` (`63b34c2`)

**Bloque C — plantilla inteligente + IA + UX:**
- [x] **ENH-194** — Plantilla con hoja Proyecto (charter) + hoja Gantt
  en Excel (mini MS Project); export con Gantt de datos reales.
  `status:fix-committed` (`d2e4624`)
- [x] **US-188** — Import inteligente IA 3 niveles: mapeo por
  contenido, normalización de valores en confirm, /ai-structure +
  use_ai_structure. `status:fix-committed` (`eaaabce`)
- [x] **US-189** — UX de import para no-PMs: drag & drop, resumen
  llano, mapeo colapsado, estrategias en llano.
  `status:fix-committed` (`7acfaab`)

**BATCH COMPLETO 9/9** (2026-07-18) — pendiente verificación owner + PR.

### Batch Revamp 1.0 — Portafolio/Salud/Recursos/Tablas/IA (2026-07-08, branch: claude/pmo-portfolio-architecture-6hbuen)

Ejecución directa por chat (0.1 solucionar>documentar; issues GitHub no
creados). Decisiones owner: solo `resource_type` (sin origin); subárea =
`teams` (no parent_area_id); sin workstream; gobernanza de asignaciones
diferida; UN solo semáforo de salud (unifica `health_status`+`status_rag`,
override manual con razón, estilo avance ENH-155); memoria IA = extensión
EP008 + reducir prompts hardcodeados; Cambios/Lecciones heredan estructura
RAID (se quedan a nivel proyecto, export propio); Plan sin sort, solo
chips de color de status.

**Bloque Salud (primero):**
- [x] **US-180** — Salud única híbrida BE: servicio `project_health`, migración
  0091 (unifica status_rag → override con razón), `GET health-detail` +
  `PATCH health`, dims a snapshots. `status:fix-committed` (`0f96dec`)
- [x] **US-181** — Salud UI: HealthStatusCard + declarar con razón +
  drill-down "¿por qué?" + foco PM + heatmap por dimensiones en N1
  (`GET /dashboard/health-matrix`); form ya no edita salud.
  `status:fix-committed` (`0c0ad7d`)
**Bloque Tablas:**
- [x] **ENH-186** — Cambios hereda RAID: sort, filtros, chips, inline
  título/tipo, toggle finalizados, export XLSX propio. `status:fix-committed` (`acf8d46`)
- [x] **ENH-187** — Lecciones hereda RAID: sort, filtros, chips inline,
  responsable, export XLSX propio. `status:fix-committed` (`8114214`)
- [x] **ENH-188** — Plan: chips de color para estados. `status:fix-committed` (`d735e76`)
- [x] **ENH-185** — /pmo/projects: filtros programa/sin-programa/prioridad
  mínima. `status:fix-committed` (`9bb3338`)
**Bloque Recursos:**
- [x] **US-182** — Pool de recursos sobre `actors` (mig 0092: tipo, función,
  seniority, escasez, skills, capacidades, flags) + API + admin UI.
  `status:fix-committed` (`c3fdf7e`)
- [x] **US-183** — FTE% + motor de saturación (mig 0093) + página
  /pmo/resources + conflictos + dimensión recursos del health.
  `status:fix-committed` (`4aec20c`)
- [x] **US-184** — Alertas de capacidad: 3 reglas sobre EP011, sweep
  semanal + fast-path, dedupe 7d. `status:fix-committed` (`595dc4f`)
**Bloque IA (extensión EP008):**
- [x] **US-185** — Memoria de proyecto (mig 0094 `project_ai_contexts`):
  contexto + instrucciones + resumen acumulativo IA, inyección en
  minutas/reportes, página /pmo/projects/[id]/ai-context.
  `status:fix-committed` (`9770161`)
- [x] **ENH-189** — Prompts composables: instrucciones permanentes por
  tenant (admin /admin/ai) + prompt_builder + fix prompts-catalog.
  `status:fix-committed` (`a440efa`)

**BATCH COMPLETO 11/11** · Verificación final: 728 pytest + 1 skip ·
ruff limpio · tsc + next build verdes · PR #570.

**Fase 2 (owner 2026-07-09) — mismo PR #570:**
- [x] **ENH-190** — Label Organización/Portafolio configurable por tenant
  (`settings.org_label`, admin UI + branding + sweep de labels).
  `status:fix-committed` (`7eca69b`)
- [x] **US-186** — Organigrama con utilización: monthly_utilization +
  hojas Organigrama/Uso mensual con alertas 🟡 ≥80% / 🔴 >100% + 4
  endpoints (proyecto extendido, programa, org, global).
  `status:fix-committed` (`fa200bd`)
- [x] **US-187** — Botones de descarga por nivel (org/programa/global en
  /pmo/resources) + EP017. `status:fix-committed` (`42ed974`)

**FASE 2 COMPLETA 3/3** (ENH-190, US-186, US-187).
Próximo libre tras Fase 2: US-188, BUG-088, ENH-191.

### Batch WBS+RAID+Áreas 2026-06-29 (branch: claude/task-wbs-raid-updates-9nq7ns)

Ejecución directa por chat del owner. Issues no creados en GitHub (batch
directo, 0.1 solucionar>documentar); IDs canónicos abajo.

**Plan / WBS:**
- [x] **US-177** — Tags de atraso separados: "Atrasada" (rojo, no completada +
  vencida) y "Completada con atraso" (amarillo, cerró tarde). Rename
  Retrasada→Atrasada en chips/filtros/KPIs/reportes/S-17 (mig 0090). `status:fix-committed` (`f05aa69`)
- [x] **ENH-180** — Quitar drag de tareas + botón Auto-WBS; agrupado por WBS
  como default para mostrar/esconder. `status:fix-committed` (`e959e30`)
- [x] **ENH-181** — WBS automatizable: elegir tarea padre + "Bajar nivel"
  (siguiente número disponible del sub-nivel) en form nueva/edición. `status:fix-committed` (`148e57f`)
- [x] **ENH-182** — Centrar checkmarks de Criticidad e Hito. `status:fix-committed` (`312f44c`)

**RAID:**
- [x] **US-179** — Estados RAID unificados a 4 (Abierto/En Progreso/On Hold/
  Resuelto) con tags de color + detención (razón, dependencia área+responsable,
  tiempo detenido). Mig 0089. `status:fix-committed` (`97af0ca`)
- [x] **US-178** — Edición inline de todos los campos de la lista RAID + botón
  Editar (modal, vuelve a la lista) + Borrar; folio link, título inline. `status:fix-committed` (`2e26269`)
- [x] **BUG-084** — Fecha de creación respetada (no "hoy") + fecha compromiso se
  guarda/limpia (exclude_unset). `status:fix-committed` (`392a2ef`)

**Áreas / Recursos:**
- [x] **BUG-085** — Crear área desde un proyecto (deriva org del proyecto +
  auto-assignment + propagación org→hijos / program→proyectos / proyecto→queda). `status:fix-committed` (`dc98be4`)
- [x] **BUG-086** — Recursos/áreas asignados a un proyecto asignables en RAID
  (servicio `area_visibility`; eligible-actors incluye actores de áreas visibles). `status:fix-committed` (`dc98be4`)
- [x] **ENH-183** — En proyecto listar sólo asignados + "traer existente" al
  crear (áreas; recursos ya soportado; equipos siguen su área; roles globales). `status:fix-committed` (`14a4037`)
- [x] **BUG-087** — Las áreas de las tareas ya no desaparecen un instante en el
  Plan (loadAreas en paralelo). `status:fix-committed` (`2ddc1bd`)

Epics actualizadas: EP006 (RAID), EP009 (plan), EP017 (áreas) + DB-CHANGES.
Próximo libre tras este batch: US-180, BUG-088, ENH-184.

### Batch previo "Form de tarea / parsing import / minuta docx" (2026-06-29 — branch claude/task-form-layout-parsing-amjjmj)

Ejecución directa end-to-end. 5 items (3 BUG + 2 ENH), `status:fix-committed`.
Pendiente PR + verificación del owner.

### Batch feedback owner 2026-06-29 (branch: claude/task-form-layout-parsing-amjjmj)

Ejecución directa por chat del owner. Issues creados + fix-committed en el mismo batch.

- [x] **BUG-081 #562** — Import lee 100% como 1%: `_coerce_progress`/`parse_xlsx`
  detectan el `number_format` de la columna de avance y escalan las fracciones
  %-formateadas ×100 (openpyxl da 1 para 100%). Commit `4f78e5a`. `status:fix-committed`
- [x] **BUG-082 #563** — Evolución de avance en 0s: el snapshot (`avg_progress`)
  usa el rollup WBS derivado (`plan_rollup_map`), no la columna `Project.progress`
  stale. Commit `ac103df`. `status:fix-committed`
- [x] **BUG-083 #564** — Subir minuta .docx daba 400 de Groq: endpoint backend
  `/ai/extract-text` (python-docx) + front lo usa para .docx; hardening de
  reintentos 4xx + log del body. Commits `f5ebca2` + `a202cea`. `status:fix-committed`
- [x] **ENH-178 #565** — Form editar tarea compacto + Modal con scroll interno
  (cap al viewport, size `xl`). Commit `2675d49`. `status:fix-committed`
- [x] **ENH-179 #566** — Matching de columnas del import en grilla de tarjetas
  (mapeo separado de la vista previa). Commit `07702de`. `status:fix-committed`

Epics actualizadas: EP004 (snapshot avg_progress derivado), EP008 (extract-text),
EP009 (parser %, modal, matching) — commit `e784a41`. Verificación: pytest de las
suites tocadas verdes (56+ TC) · ruff limpio · tsc + next build verdes.

Próximo libre tras este batch: US-177, BUG-084, ENH-180.

### Sprint 35 — Plan page + RAID mejoras (branch: claude/minutes-plans-upload-error-driwcd)

Ejecución directa por chat del owner 2026-06-28 (planear + ejecutar de principio a fin).

**Plan page (`/pmo/projects/[id]/plan`):**
- [x] **ENH-161** — Quitar botón CSV. `status:fix-committed` (`9b19b6b`)
- [x] **ENH-162** — Mover Plantilla/Importar/Descargar al header (nivel título + breadcrumbs). `status:fix-committed`
- [x] **ENH-163** — Columna HITO junto a CRITICIDAD en la lista. `status:fix-committed`
- [x] **ENH-164** — Reemplazar botón MSP por configurador de columnas (obligatorias: WBS, TAREA, ÁREA, INICIO, FIN, AVANCE, ESTADO, CRITICIDAD, HITO). `status:fix-committed`
- [x] **ENH-165** — Agrupación por WBS nivel 0 (colapsa todo, sólo raíces). `status:fix-committed`
- [x] **US-171** — "Fecha de Cierre" editable + lógica de atraso para cerradas + tag "Retrasada" rojo (BE + migración 0086 + FE + docs). `status:fix-committed`
- [x] **US-172** — Auto-WBS con niveles + anti-duplicados (BE endpoint renumber-wbs + botón FE). `status:fix-committed`
- [x] **US-173** — Edición inline de tareas (área dropdown, fechas calendario, avance dblclick, estado dropdown, criticidad+hito checkmarks). `status:fix-committed`

**RAID (`/pmo/projects/[id]/raid`):**
- [x] **ENH-166** — Listas excluyen finalizados por default + orden por estado/severidad (+ toggle "Mostrar finalizados"). `status:fix-committed`
- [x] **ENH-167** — Filtros de área en RAID. `status:fix-committed`
- [x] **ENH-168** — Descarga individual por tipo (R/A/I/D) + mantener el de 4 hojas (BE `?only=` + FE). `status:fix-committed`
- [x] **US-174** — Kanban con drag (avanzar/retroceder fase) + toggle Lista/Kanban por tipo. `status:fix-committed`
- [x] **US-175** — Edición inline RAID (estado inline en listas R/A/I/D). `status:fix-committed`
- [x] **ENH-169** — Alinear/complementar campos RAID: **análisis + recomendaciones entregados** en `UIUX-ANALYSIS-Sprint35.md`. Cambios de schema/campos (columna Responsable, category en issues, severidad inline) quedan **[requiere OK]** del owner antes de ejecutar. `status:fix-committed`

Análisis UI/UX final entregado en `docs/project-management/UIUX-ANALYSIS-Sprint35.md`
(mejoras, docs, styling, aprovechamiento de espacio, deuda/follow-ups).

**Batch Sprint 35 COMPLETO** (14/14 items). PR #560 abierto, **CI verde** (run #538).

### Follow-ups post-análisis (UIUX-ANALYSIS-Sprint35.md) — branch claude/minutes-plans-upload-error-driwcd

**Fase 1 — quick wins (sin decisión):**
- [x] **ENH-170** — Ícono Diamond para Hito (consistencia DS). `status:fix-committed` (`bef532e`)
- [x] **ENH-171** — RAID: menú "Exportar ▾" + hint del Kanban. `status:fix-committed` (`0cf014b`)
- [x] **ENH-172** — Unificar label "Nota de cierre" en issues RAID. `status:fix-committed` (`a7ee838`)

**Fase 2-3 — hechas:**
- [x] **ENH-173** — Edición inline "on-click" (`InlineSelectCell`) + updates optimistas con revert (Plan y RAID). `status:fix-committed` (`4fb79fb`)
- [x] **ENH-174** — A11y del Kanban: botones ←/→ por tarjeta (teclado). `status:fix-committed` (`2083113`)

**Fase 4 — aprobada por owner excepto auto-WBS (2026-06-28):**
- [x] **ENH-175** — Columna Responsable en listas RAID + resolución Actor en el read. `status:fix-committed`
- [x] **ENH-176** — Severidad inline en riesgos (probability/impact, optimista). `status:fix-committed`
- [x] **ENH-177** — `category` para issues (migración 0087 + UI detalle). `status:fix-committed`
- [x] **US-176** — Auto-WBS / orden manual: **versión mínima** implementada (columna `tasks.position` mig 0088, endpoint `/tasks/{id}/move`, drag por fila con handle en vista plana sin filtros, `list_tasks`/`renumber-wbs` respetan `position`). Draft `docs/epics/drafts/auto-wbs-position.md` con lo diferido (drag de subárbol, orden por hermanos). `status:fix-committed`

Próximo libre tras este batch: US-177, BUG-081, ENH-178.

### Sprint 34 — Bloque 1 — Roles + Visibilidad + Recursos (branch: claude/friendly-bell-EYlVB)

Aprobado por owner 2026-06-08 (plan + decisiones en sesión).

- [x] **ENH-159 #551** — Nav sidebar: proyectos sin programa bajo "Sin Programa". `status:fix-committed`
- [x] **US-166 #552** — Rol `pm_sr`: nuevo role_type con acceso admin completo. `status:fix-committed`
- [x] **US-167 #553** — Modelo `UserScopeAssignment`: asignaciones de visibilidad para PM. `status:fix-committed`
- [ ] **US-168 #554** — Filtrado de API y sidebar por visibilidad de PM. `status:in-progress`
- [x] **US-169 #555** — UI: árbol de asignación Org→Prog→Proyecto en admin de usuarios. `status:fix-committed`
- [x] **US-170 #556** — Catálogo de áreas/equipos/actores a nivel organización. `status:fix-committed`

### Hotfix — Error "No se pudo conectar" al subir minutas/planes (branch: claude/minutes-plans-upload-error-driwcd)

Ejecución directa por chat del owner 2026-06-28. Reporte: usuario no podía
subir minutas/planes ("No se pudo conectar con el servidor"); Railway mostraba
`sqlalchemy.exc.MultipleResultsFound`. Auditoría (workflow) encontró 5 sitios
`scalar_one_or_none` sobre cláusulas WHERE no únicas + el enmascaramiento CORS.

- [x] **BUG-078** — `MultipleResultsFound` al subir planes/documentos: endurece
  5 lookups (`tasks.py` import merge x2, `modules.py` document versioning x2,
  `_validate_area` JOIN). Commit `2071b93`. `status:fix-committed`.
- [x] **BUG-079** — los 500 no manejados ahora salen con headers CORS (handler
  global en `main.py`), así el front muestra el error real en vez de "No se
  pudo conectar". Commit `7d94012`. `status:fix-committed`.
- [x] **BUG-080** — el export CSV de auditoría incluye la columna `details`
  (contexto del job). Commit `ff33937`. `status:fix-committed`.

Verificación: 5 TC nuevos + 83 TC de suites relacionadas verdes · ruff limpio.
Pendiente PR + verificación del owner.

### Cross-cutting / sin sprint asignado
- [ ] **ENH-115 #434** — Breadcrumbs consistentes en `/pmo/**/reports`. `status:ready` desde 2026-05-23 pero diferido al cierre del rediseño grande. Owner pasa a ready o reasigna sprint cuando lo prioriza.
- [x] **ENH-160 #558** — Inactividad: bloqueo con blur + re-login (en vez de logout duro). `status:fix-committed` · branch `claude/nice-thompson-omcizv` (ejecución directa por chat del owner 2026-06-25). Pendiente PR + verificación.

### Batch previo pendiente de PR
- `claude/gantt-areas-fixes` — `status:fix-committed`. Owner crea PR manualmente:
  ENH-149 #544, BUG-075 #545, ENH-154 #546, ENH-152 #547.

---

## ⏸️ Deferred — re-evaluación post EP020

> Issues abiertos sin asignación de versión. Se retoman cuando owner decida.

### IA conversacional global (ex Sprint 17 Bloque 1)
- [ ] US-102 #255 — Side-panel chat IA en cada página (Ctrl+K + flotante)
- [ ] ENH-074 #256 — Context-awareness por página
- [ ] ENH-075 #257 — Tool-use (crear tarea / RAID / nav)
- [ ] ENH-076 #258 — Historial persistente + summary rolling

**Decisión owner 2026-05-08:** posterga el chat global. Volver a evaluar necesidad post-EP020.

### Pendiente redefinición Áreas/Recursos (cubierto parcial por EP017 Sprint 25)
- [ ] **US-105 #311** — Import Plan: wizard matching responsables → Actor.
- [ ] **Tab Organigrama de US-106** — placeholder UI; cableado funcional depende del paquete EP017 final.
- [ ] **US-119 #414** — EP017 cleanup: drop legacy `actors.team_id`, `actors.is_lead`, `teams.area_id`, `tasks/risks/issues.area_id`. **Bloqueado por ENH-109.**
- [ ] **ENH-109 #417** — PersonPicker cableado en formularios existentes. **Bloquea US-119 y ENH-110.**
- [ ] **ENH-110 #418** — Filtros / agrupadores de Plan por dimensiones derivadas. Depende de ENH-109.
- [ ] **US-133 #415** — US-118 Fase 2: RBAC migra a leer `project_participations`.
- [ ] **US-134 #416** — US-118 Fase 3: drop `project_members` table.

### Admin UI settings (cross — sin sprint asignado al rediseño Minutas/Reports)
- [ ] **ENH-111 #430** — UI admin tenant para `progress_calculation_method`.
- [ ] **ENH-112 #431** — UI admin tenant para `task_load_thresholds`.
- [ ] **ENH-113 #432** — UI admin org para upload `client_logo_url`.

### Reportes / snapshots (estado actualizado 2026-05-26)
- ✅ Snapshots periódicos de KPIs y semáforo → **implementado** (US-151, `metric_snapshots`, cadencia semanal).
- ✅ S-07 Curva-S → **implementado** (US-161, planeado lineal start→end).
- [ ] S-10 Entregables formales (concepto no configurado) — sigue diferido.

---

## ✅ DONE

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo.**

> Batches post-Sprint 33 (deepwork reportes/RAID/IA #524-528, big canvas #514-517, chrome #520-521) mergeados a main 2026-05-26/29 → archivados en `SPRINT-DONE-HISTORY.md` el 2026-06-05.

| Sprint | Versión | Cerrado | Items |
|---|---|---|---|
| 1 | v1.0 MVP | 2026-04-21 | ~94 (22 bloques) |
| 2 | v1.1 | 2026-04-23 | 18 |
| 3 | v1.2 | 2026-04-24 | 5 |
| 4 | v1.3 | 2026-04-24 | 14 |
| 5 | v1.4 | 2026-04-24 | 10 |
| 6 | v1.5 | 2026-04-25 | 5 |
| 7 | v1.6 | 2026-04-28 | 10 |
| 8 | v1.7 | 2026-04-29 | 13 |
| 9 | v1.8 | 2026-05-05 | 6 |
| 10 | v1.9 | 2026-05-06 | 14 |
| 11 | v1.9 | 2026-05-06 | 12 |
| 12 | v1.10/v1.11 | 2026-05-06 | 9 |
| 13 | v1.12 | 2026-05-07 | 7 |
| 14 | v1.13 | 2026-05-07 | 4 |
| 15 | v1.14 | 2026-05-07 | 4 |
| 16 | v1.14 | 2026-05-07 | 4 |
| 17 | v1.16 | 2026-05-08 | 2 |
| 18 | v1.17 | 2026-05-08 | 3 |
| 19 | v1.18 | 2026-05-09 | 6 |
| 20 | v1.19 | 2026-05-09 | 5 |
| 21 | v1.20 | 2026-05-09 | 4 |
| 22 | v1.21 | 2026-05-09 | 2 |
| 23 | v1.22 | 2026-05-09 | 1 |
| 24 | v1.23 | 2026-05-09 | 12 |
| 25 | v1.24 | 2026-05-10 | 5 |
| 26 | v1.25 | 2026-05-22 | 16 (3 bloques — Minutas v1.0 + Dependencias EP020 + Backbone EP020) |
| 27-29 | v1.26 | 2026-05-25 | 10 (mega-PR EP020: US-123 a US-132) |
| 30-32 | v1.27 | 2026-05-23 | 22 (rediseño Minutas + Reports — ver `SPRINT-DONE-HISTORY.md`) |
| 33 | v1.28 | 2026-05-26 | 13 (Dashboards N1/N2 + reportes derivados + revamp + follow-ups — ver `SPRINT-DONE-HISTORY.md`) |

---

## 📋 Backlog v2.0 (post-v1.x)

> **Contexto (DEC-020):** plataforma definida como herramienta de apoyo/visualización sin aprobaciones jerárquicas.

- [ ] ENH-035 #158 — Análisis profundo optimización CI tests pesados.
- [ ] US-081 — Borrar físicamente tablas `roles` + `user_roles`.
- [ ] ENH futuro — Filtrado efectivo de queries por `organization_user_exclusions`.
- [ ] Cross-empresa nativo (post-ENH-043): si ≥3 grupos lo solicitan, abrir US con `program_organizations`.
- [ ] US-086 fase 2 — Cablear stakeholders FK en Charter.
- [ ] US-084 fase 2 — Banner de divergencias cuando importadores MPP/XLSX detecten diferencia entre manual y calculado.
- [ ] US-087 fase 2 — Campos `Task.hours_estimated/hours_actual`.
- [ ] Hard-delete User cuando hay `project_request.requested_by` (US-088 fase 2).
- [x] ~~Snapshots históricos de KPIs y semáforo~~ → hecho en v1.28 (US-151).
- [ ] KPIs custom por admin tenant.
- [ ] **Cleanup post-Sprint 32**: borrar `apps/web/app/(app)/pmo/projects/[id]/ai-minutes/` y `.../reports/tweak/` carpetas enteras (hoy son redirects 301). Tras 1 sprint en main sin reportes de bookmarks rotos.
- [ ] **Persistencia reports L1/L2** (PMO/Org/Prog): la **generación** ya existe (v1.28, US-160: PDF on-demand vía `/dashboard/reports/portfolio`, `/organizations/{id}/reports/status`, `/programs/{id}/reports/status`). Falta **persistir** el histórico: agregar `generator='pmo'|'organization'|'program'` + nullable `project_id` o tabla aparte.
- [ ] **Dirty-flag fino en builder** (mejora ENH-125): comparar canvas vs plantilla cargada para detectar cambios sin guardar incluso cuando hay `loadedTemplateId`.
- [ ] **Export RAID — Lecciones/Cambios** (follow-up ENH-152): si se necesita exportar Lessons / ChangeRequests, abrir un export aparte (ENH-152 los descartó del XLSX RAID por decisión del owner 2026-06-05).

---

## Notas y cambios recientes

> Histórico de sprints anteriores en `SPRINT-DONE-HISTORY.md`.

- **2026-06-28 (hotfix subir minutas/planes — branch claude/minutes-plans-upload-error-driwcd):**
  BUG-078 (`2071b93`) MultipleResultsFound en subir planes/documentos;
  BUG-079 (`7d94012`) 500 no manejados sin CORS → "No se pudo conectar";
  BUG-080 (`ff33937`) export CSV auditoría sin columna `details`. 5 TC nuevos +
  83 TC relacionados verdes, ruff limpio. `status:fix-committed`, sin PR aún.
  Próximo libre: US-171, BUG-081, ENH-161.

- **2026-06-25 (ENH-160 #558 — branch claude/nice-thompson-omcizv):** inactividad
  pasa de logout duro a bloqueo con blur + overlay de re-login (no se pierde
  progreso). Commit `0b6811c`. tsc + next build verdes. Epic EP001 actualizado.
  `status:fix-committed`, sin PR aún. Próximo libre: US-171, BUG-078, ENH-161.

- **2026-06-08 (batch Roles+Visibilidad+Recursos — branch claude/friendly-bell-EYlVB):**
  6 issues creados: ENH-159 #551, US-166 #552, US-167 #553, US-168 #554, US-169 #555, US-170 #556.
  Próximo libre: US-171, BUG-078, ENH-160.
- **2026-06-06 (batch feedback owner — MERGED #549 a main 2026-06-07):**
  branch `claude/owner-feedback-batch`, 5 commits atómicos, sin migraciones.
  CI verde, tsc/ruff/lint limpios.
  - **ENH-155** — avance derivado del plan (rollup WBS jerárquico): padre =
    promedio de avance de hijos recursivo; general = promedio de nivel más
    alto. Read-side en lista de tareas, resumen de proyectos, detalle,
    dashboard (KPIs/charts/plan-vs-actual) y reporte de avance; manual como
    fallback para proyectos sin plan. Helper `compute_wbs_rollup` +
    `round_half_up` en `plan_metadata.py`.
  - **ENH-156** — salud/semáforo solo-color (sin "Green"/"Verde"): reporte de
    avance (`.dot`), charter `.docx` (● coloreado) y 5 vistas read-only del
    front. No se tocaron los selectores interactivos.
  - **ENH-157** — logos PMO+cliente en el `.docx` del charter
    (`resolve_charter_logos`, disco + httpx, solo PNG/JPEG). Complementa
    ENH-153, que cubrió el header HTML/PDF.
  - **ENH-158** — borrar/cancelar tickets de RAID/Lecciones/Cambios:
    soft-delete + audit; Cambios además cancela (status `cancelled`) e
    invalida los ApprovalToken EP019. Cualquier miembro puede hacerlo.
  - **BUG-077** — guardar minuta devolvía 422 (título < 2 chars): guard ≥2 +
    parser del 422 nativo de FastAPI en `lib/api.ts`. Re-aplicado en
    `minutes/new/page.tsx` tras el merge (el llenado manual se movió ahí).
  ⚠️ **Nota de IDs:** los commits aterrizaron etiquetados `ENH-109/110/111/112`
  y `BUG-062` — se eligieron contra una base desactualizada (`9c904a2`,
  max ENH-108/BUG-061) antes de ver los 196 commits de main, que ya habían
  consumido esos números (ENH-109/110 = #417/#418, ENH-111/112 = #430/#431,
  BUG-062 = "click en minuta abre el detail"). Historia ya mergeada → **no se
  reescribe**; los IDs **canónicos** de este batch son **ENH-155..158 /
  BUG-077** (los labels de commit quedan como referencia histórica).
- **2026-06-05 (batch gantt/áreas/reportes/RAID fixes):** branch
  `claude/gantt-areas-fixes`, 9 commits de trabajo, `status:fix-committed`,
  **sin PR aún**. Sesión previa: BUG-073/074/076 #538/539/542 +
  ENH-150/151/153 #540/541/543. Esta sesión cerró los 4 temas restantes:
  ENH-149 #544 (ya estaba implementado, solo verificación), BUG-075 #545
  (estado RAID editable), ENH-154 #546 (sección Acciones en Seguimiento),
  ENH-152 #547 (export RAID XLSX 4 hojas ES unificado). Sin migraciones.
  Epics EP006/EP014/EP018 actualizadas. Branch detrás de origin/main →
  rebase al armar el PR si CI lo pide.
- **2026-05-26/29 (3 batches mergeados):** deepwork reportes/RAID/IA
  (#524-528, mig. 0084), big canvas (#514-517, migs 0082/0083), chrome
  logo/iconos (#520-521). Archivados en `SPRINT-DONE-HISTORY.md`.

---

## Instrucción para Claude Code

Cuando arranques una sesión nueva:

1. Lee `docs/project-management/HANDOFF.md` PRIMERO.
2. Luego `CLAUDE.md` + este archivo + el epic referenciado en IN-PROGRESS.
3. Mueve la siguiente US/ENH/BUG de **INBOX** (marcada `status:ready`) a **IN-PROGRESS** antes de empezar.
4. Cambia label del issue: `status:ready` → `status:in-progress`.
5. Implementa con tests verdes + typecheck.
6. Commit con header `<tipo>(<scope>): <ID> — <desc> (refs #<issue>)` y push.
7. Cambia label → `status:fix-committed` + comment con template CLAUDE.md §3 paso 6.
8. Mueve item a DONE en este archivo o a la tabla histórica si cierra sprint.
9. Resumen de ronda al owner siguiendo CLAUDE.md §11.
10. Al cierre de sesión: invocar `/handoff` para limpiar SPRINT.md y dejar bridge.

**Regla sagrada:** 1 US = 1 commit. No mezclar varios IDs en el mismo commit.

**Regla post-Sprint 26 (decisión owner 2026-05-22):** desarrollo secuencial puro. 1 sesión activa, 1 lane, 1 branch. Migraciones consecutivas sin paralelización.
