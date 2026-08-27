---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 30d
---

# SPRINT-DONE-HISTORY.md — Histórico de bloques completados (Sprint 1 v1.0 MVP)

> **Propósito:** Archivo de referencia histórica. Los bloques completados se mueven aquí desde SPRINT.md cuando se cierra un sprint. Permite que SPRINT.md mantenga solo lo pendiente para el sprint activo.

---

## Ronda 2026-08-27 — Revamp de diseño v2 (batch del owner, sin US)

- Branch `claude/platform-design-revamp-y8rpqw`, **48 commits, 683 archivos**.
  Ejecutado como batch directo del owner (especificación + mockup
  `Refresh UI v1.dc.html` de 30 pantallas); sin US individuales a propósito —
  un commit por pantalla/grupo hace de unidad de revisión.
- **Qué cambió**: `globals.css` pasa del sistema «big canvas» (lienzo
  gris-azul + islas + sidebar navy) a superficie blanca única con filetes con
  profundidad (`--linea-surco`, `--relieve-*`, `--hundido`); iconos
  lucide-react → set Keyline completo (`public/icons/stroke/`, MIT) vía
  `<Icono>` por mask-image, y la dependencia se retiró del `package.json`;
  primitivas `ui/*`, las 30 pantallas del mockup y una barrida final sobre
  las ~69 restantes sin mockup propio. Dos pantallas nuevas de superadmin
  (Seguridad `/superadmin/security` y Sistema en `/superadmin/health`, que
  deja de ser redirect); nav de superadmin en 4 grupos rotulados.
- **Desviaciones deliberadas**: `--text-tertiary` se oscureció de `#82878F`
  (el literal de la especificación) a `#666B73` porque el literal falla WCAG
  AA (gate `check_contraste.py`); toda métrica sin endpoint quedó en
  `SIN_DATO` + «pendiente de backend», nunca cifras inventadas.
- **Verificación**: `check_tokens.py`, `check_contraste.py` (36/36 AA),
  `tsc --noEmit` y `next build` en verde. Docs `mapa-frontend.md` y
  `navigation.md` actualizados en la misma ronda.
- **Lo que quedó pendiente** salió como plan, no como deuda suelta:
  `docs/epics/drafts/plan-post-revamp.md` (backend R1/R2, dark theme R3,
  deuda visual R4, operación eficiente O, reportes/minutas G).

---

## Ronda 2026-08-06 — Ola 2, `SEG-04` y verificación local

- **2026-08-06 (Ola 2 + SEG-04):** quince commits. `SEG-04` era la única
  CRÍTICA y el hueco era explotable: un PM asignado a un proyecto podía abrir
  cualquier otro de su inquilino con solo tener el identificador — nueve copias
  del resolvedor de proyecto y solo una comprobaba el alcance.
  Lo que la medición no veía: el acta en
  `.docx` se firmaba con la paleta anterior a DIS-02; once citas a tokens
  inexistentes hacían que la página de documentos pintara tema claro en modo
  oscuro y que la tabla de permisos saliera sin fondo; el gate de tipos daba
  verde sin analizar nada; el worker no configuraba su registro y Celery se lo
  llevaba por delante; y la etiqueta del formulario de ajustes seguía diciendo
  «Ámbar». **Seis hallazgos**, ninguno de leer código: los seis salieron de
  medir contra el texto del requisito.

- **2026-08-06 (verificación local por caída de Actions):** con GitHub Actions
  caído se corrieron a mano los cuatro trabajos que no reportaron. Todos en
  verde. De ahí salieron dos correcciones que el CI no habría dado:
  `api-migrations-postgres` **no ejercía** la migración 0101 —corre sobre base
  limpia y ninguna migración inserta inquilinos, así que el bucle recorría cero
  filas—, y la justificación escrita en el encabezado de esa migración era
  **falsa**: la versión con `sa.text` que se creía rota pasa contra Postgres.
  Se comprobó mutándola. Suite nueva `test_dat06_migracion_0101.py` y paso
  nuevo en el trabajo del CI.

  El detalle de la sesión del 2026-08-05 está en `SPRINT-DONE-HISTORY.md`.

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


## Sprints 1-33 y batches de mayo (2026-04-21 → 2026-05-29)

Movidos a `docs/archive/project-management/SPRINT-DONE-HISTORY-sprints-01-33.md`
el 2026-08-12. Los IDs siguen derivables: viven en `git log`.

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

---

## Ronda 2026-08-07 — Los quince huecos ASVS L1, cerrados

Branch `claude/asvs-l1-quince-huecos-kgk2qz`, **PR #584**, CI verde (12 de 13;
`api-tests-heavy` se salta, solo corre en push a `main`).

Dieciocho commits, uno por control, cada uno con suite propia y verificación por
mutación. `SEG-01` pasa de **15 huecos a 0**, y el tope de `check_asvs.py` de 15
a 0. Medición final: **116 CUMPLE · 8 NO APLICA · 3 ACEPTADO · 0 HUECO**.

| Control | Commit | Qué se hizo |
|---|---|---|
| `8.2.1` | `7f0c63b` | `Cache-Control: no-store` en todo `/api/` |
| `10.3.2` | `8235dae` | Tipos de letra self-hosted (`next/font`) + trinquete |
| `3.4.4` | `56e24da` | Cookie de sesión con prefijo `__Host-` |
| `2.1.12` | `bd8467a` | `PasswordInput` compartido en los 12 campos + trinquete |
| `2.1.7` | `80a8f69` | Conjunto de 37.970 contraseñas filtradas |
| `5.2.7` | `ff967d7` | Saneado de SVG por lista blanca |
| `11.1.4` | `c2702b3` | Presupuesto de 600 peticiones/min por cuenta |
| `2.2.3`+`2.5.5` | `ac57569` | Aviso en los seis sitios que tocan una credencial |
| `12.4.2` | `428bbe1` | Verificación de firma + enganche ClamAV |
| `3.2.3`+`8.2.2` | `60a220a` | Token de sesión a cookie `HttpOnly` (ADR-033) |
| `8.3.2` | `46caade` | Exportar + anonimizar (ADR-034) |
| `8.3.3` | `ea509e3` | Aviso de privacidad versionado con aceptación |
| `4.3.1` | `24dcedb` | Segundo factor por correo (ADR-035) |
| — | `b4793bf`, `ec965ca` | Ventana de equipo de confianza, 30 días |

### Lo que enseñó cerrarlos

**Tres controles no eran lo que su evidencia decía.** Es lo que más vale de
haber medido contra el texto del control y no contra el recuerdo:

1. **`10.3.2` decía «hoy no se cargan recursos externos». Cargaba tres** — la
   hoja de estilo de Google Fonts, sin `integrity`, decidiendo de dónde bajar
   los tipos. No se arregla con `integrity` (Google varía el CSS por
   `User-Agent`); se arregla dejando de pedírselo a un tercero.
2. **`2.1.7` no se cierra con «las 10.000 más usadas».** De las 59.186 de
   `rockyou-75`, las que pasan la política del producto son **ocho**. Una lista
   estándar habría sido un archivo grande, un control marcado y cero
   contraseñas detenidas.
3. **`12.4.2` tenía dos mitades y solo una necesita antivirus.** El tipo del
   archivo salía de la cabecera del navegador y del nombre — las dos escritas
   por quien sube—: un ejecutable renombrado a `.pdf` se guardaba y servía como
   PDF.

**Dos controles existían, pero no donde hacían falta.** `2.2.3`/`2.5.5` avisaban
en uno de los seis sitios que tocan una credencial —justo el único donde el
cambio lo hace el dueño de la cuenta, o sea donde el aviso no sirve—. `2.1.12`
estaba copiado a mano en dos pantallas y faltaba en las nueve donde se **elige**
contraseña nueva.

**Cerrar uno abrió otros cuatro.** El segundo factor de `4.3.1` hizo que
`2.2.2`, `2.7.2`, `2.7.3` y `2.7.4` dejaran de «no aplicar», con requisitos
concretos (diez minutos, un solo uso atado a su desafío, canal independiente), y
convirtió `2.7.1` en el tercer residual aceptado. **Un mapeo no es una lista que
solo encoge.**

### Un fallo propio que cazó una prueba ajena

Al partir el inicio de sesión en dos caminos para el segundo factor, el camino
directo perdió su registro `login_success`. Lo detectó la suite de exportación de
datos personales, que esperaba encontrarlo en la actividad del usuario.

### Migraciones

`0105` (consentimiento), `0106` (códigos OTP), `0107` (equipos de confianza).

### Trinquetes nuevos

`check_subrecursos.py` (ASVS 10.3.2) y `check_password_input.py` (ASVS 2.1.12),
los dos en el job `contexto-permanente`. Existen porque los dos fallos originales
no fueron técnicos sino de **evidencia escrita a mano que se quedó atrás**.

---

## Ronda 2026-08-19 — Bloque Reestructura-W1: la jerarquía cambia de eje

Doce commits en `claude/handoff-development-2awr5v`, PR **#594**. Las cinco USs
del bloque quedaron implementadas y pendientes de verificación del owner: los
issues **no** se cerraron.

**El cambio de fondo.** La jerarquía era `organización → unidad de negocio →
departamento → programa → proyecto`, y esos dos niveles del medio describían el
**organigrama** del cliente. La PMO no contesta preguntas de organigrama:
contesta qué se hace, con qué y qué se deja de hacer. El dato que lo cerró no
fue un argumento de diseño — el owner nunca usó BU/departamentos en producción
(2026-08-19): dos niveles con su CRUD, sus pantallas y sus columnas en cinco
tablas, con cero filas. Queda `organización → portafolio ⊃ programa → proyecto`
(**ADR-037**), y el veto de ADR-021 sobre la palabra «portafolio» se levanta
porque la entidad ya existe.

| US | Commit | Qué entró |
|---|---|---|
| **US-198** #588 | `27b6ae9` | Tabla `portfolios`, `programs.portfolio_id` NOT NULL, `projects.portfolio_id` nullable, regla de consistencia en `services/jerarquia.py`. Migración **0108** (aditiva, con backfill del «Portafolio General»). ADR-037 · DEC-030 |
| **US-199** #589 | `c529085` | CRUD `/portfolios` (8 rutas, papelera de dos pasos), retiro de los routers de BU/departamentos, migración **0109** que suelta 7 columnas FK |
| **US-202** #592 | `3253338` + `0f2d167` | Fases al español y `type` como enum, catálogo único en `app/dominio/proyecto.py`, 5 ventanas de compat, migración **0110**. ADR-038 (DEC-031 promovida) |
| **US-200** #590 | `f3f1063` | Acordeón Portafolio ⊃ Programa en el admin, árbol de 5 niveles con los cajones «Sin programa» y «Sin clasificar», selects anidados en los tres formularios |
| **US-201** #591 | `3c066f6` | Cascada org → portafolio → programa en las 7 superficies del tablero, las 5 vistas cross y `metric_snapshots` (scope `portfolio`); treemap de 4 niveles |

**Y una limpieza que el bloque hizo necesaria** (`ea5710b`, `c36d208`,
`399fe0f`, `0bdcf8c`, `92c9882`, `f155f40`):

- **ENH-190 retirada** (**DEC-032**, migración **0111**). El label configurable
  que renombraba «Organización» a «Portafolio» en la interfaz no quedó obsoleto:
  quedó **inválido**. Con el portafolio como entidad hija, ese inquilino vería
  «Portafolio → Portafolio → Programa». Se fue el mecanismo entero, y la
  migración cuenta cuántos inquilinos lo tenían para saber a quién avisar.
- Vocabulario duplicado en el frontend: cinco copias de la etiqueta de salud,
  cuatro del color, dos del tono de la insignia de fase y una de las fases de
  lección. Todas idénticas, todas a un cambio de desincronizarse.
- 675 líneas de componentes huérfanos y residuo en tests y configuración.
- **20 documentos** que describían como vigente lo retirado, incluido el
  glosario del dominio y un runbook cuyo procedimiento recomendado apuntaba a un
  campo que nunca existió.

**Los tres fallos silenciosos que el bloque cerró.** Los tres de la misma
familia — no fallan, devuelven un número equivocado:

1. `"closed"` estaba escrito a mano en 13 archivos. Al renombrar, la comparación
   que se olvide **no falla**: devuelve siempre falso, y un proyecto cerrado
   cuenta como activo. Centralizarlo hace que olvidarse sea un `NameError`.
2. Filtrar un portafolio por «los programas del portafolio» deja fuera
   exactamente a los proyectos que cuelgan de él sin programa. El KPI sale más
   chico y se lee como un dato.
3. `test_enh111_charter_logos.py` lleva `@pytest.mark.heavy`, así que solo corre
   al pushear a `main`. US-199 lo rompió —su doble del acta se quedó sin
   `portfolio_id`— y la suite normal nunca lo vio. Sin el arreglo, la primera CI
   de `main` tras el merge salía roja por un fallo sembrado tres commits antes.

**Verificación del bloque:** ruff · mypy --strict sin regresiones (línea base
apretada 1143 → 1142) · `tsc --noEmit` · `next build` · pytest 1826 passed +
3 skipped (`not heavy`) y 9 passed (`heavy`) · evaluación IA 52/52 ·
check_contexto / check_tokens / check_contraste / check_frescura ·
`generar_er.py --verificar`. Todo `exit 0`.

**Diferido a propósito:** las tablas `business_units` y `departments` siguen en
el esquema, sin lectores, y se dropean en **W8** — un `drop` es irreversible y no
se paga en la misma oleada que lo sustituye. Los campos de texto libre
`business_unit`/`department` de la solicitud **se quedan**: son las palabras del
solicitante, no la jerarquía (reetiquetados «Área que solicita» y «Equipo o
sub-área»).

