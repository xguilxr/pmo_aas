# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-10 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Sprint 24 (v1.23) — Bloque 1+2+3+4 ENTREGADO 2026-05-09 (12 de 12, pendiente verif. owner):
  BUG-056 + ENH-092 + BUG-057 + ENH-093 + ENH-094 +
  ENH-095 + ENH-096 + BUG-058 +
  US-109 (rework) + US-111 (rework) + BUG-059 +
  BUG-060.
  Sin migración Alembic.
  Branch sesión: claude/fix-project-charter-issues-RFoAy

Sprint 18 (v1.17) — Bloque 1 ENTREGADO 2026-05-08 (3 issues — pendiente verif. owner):
  US-106 + ENH-081 + ENH-080. Migraciones 0055 + 0056 agregadas.
  Branch sesión: claude/review-start-next-sprint-R8JWc

Sprint 19 (v1.18) — Bloque 1 ENTREGADO 2026-05-09 (6 de 6, pendiente verif. owner):
  US-107 + ENH-082 + ENH-083 + ENH-088 + ENH-086 + ENH-087.
  Migración 0057 agregada.
  Branch sesión: claude/continue-sprint-tasks-jR3zt

Sprint 17 (v1.16) — Bloque 0 MERGED 2026-05-08 (PR #297, BUG-053).
Sprint 17 (v1.16) — Bloque 0.5 IN-PROGRESS 2026-05-08:
  US-104 #298 — módulo BYO: test-before-save + custom provider + retry
  Branch sesión: claude/setup-ai-module-8HYs1

Sprint 17 Bloque 1 (chat global #255-258) → POSTERGADO (ver sección Deferred).

Sprint 20 (v1.19) — Bloque 1 ENTREGADO 2026-05-09 (5 de 5, pendiente verif. owner):
  ENH-084 + US-108 + BUG-055 + ENH-090 + ENH-091.
  Migración 0058 agregada.
  Branch sesión: claude/continue-sprint-tasks-jR3zt

Sprint 21 (v1.20) — Bloque 1 ENTREGADO 2026-05-09 (4 de 4, pendiente verif. owner):
  ENH-085 + US-111 + US-109 + ENH-089.
  Migración 0059 agregada.
  Branch sesión: claude/continue-sprint-tasks-jR3zt

Sprint 22 (v1.21) — Bloque 1 ENTREGADO 2026-05-09 (2 de 2, pendiente verif. owner):
  US-112 + US-113. Migración 0060 agregada.

Sprint 23 (v1.22) — Bloque 1 ENTREGADO 2026-05-09 (1 de 1, pendiente verif. owner):
  US-110 — BYO universal (custom OpenAI-compat) + Azure OpenAI / Copilot M365.
  Sin migraciones (settings.ai.byo soporta dict flexible).
  Branch sesión: claude/continue-sprint-work-mcmzX

Sprints 12-15 — Bloques entregados, pendiente verificación owner.

Próximo libre: US-133, BUG-062, ENH-109.
(US-119 reservada para EP017 cleanup diferido; US-120 a US-132 reservadas EP020.
 BUG-061 + ENH-102 a ENH-108 reservados para Sprint 26 Bloque 0 Minutas v1.0.)
```

---

## 📥 INBOX / TRIAGE

> Issues creados con status:triage. Owner pasa a status:ready para arrancar.

```
Sprint 25 (v1.24) — EP017 Directorio de Proyecto — Bloque 1+2 ENTREGADO 2026-05-10 (5 de 5, pendiente verif. owner):
  US-114 #349 (6842344) — Schema additivo: project_participations + project_roles + actors enriquecido. Migración 0061.
  US-115 #350 (49ea588) — API: endpoints participations + project_roles + servicio derived_assignment.
  US-116 #351 (a24212f) — UI: tab Directorio en /pmo/projects/[id]/areas + DirectoryView + AddPersonModal + EditParticipationModal + cliente API.
  US-117 #352 (4236214) — eligible-actors endpoint + PersonPicker + lessons.owner_actor_id (migración 0062).
  US-118 #353 (2896787) — Fase 1 doble escritura project_members → project_participations (sync helper + cableado en POST /projects).
  Migraciones agregadas: 0061 + 0062.
  Branch sesión: claude/design-areas-resources-8DIfi
  Epic doc: docs/epics/EP017-project-directory.md
  Diferidos (sin issue, no bloqueantes):
    - /admin/areas rediseño completo (Toggle 2 con 5 sub-tabs).
    - Cableado de PersonPicker en cada formulario existente (TaskAssigneeDropdown, RiskOwnerDropdown, IssueOwnerDropdown, ChangeApproverPicker, LessonOwnerDropdown, ParticipantPicker minutas).
    - Filtros/agrupadores de Plan por dimensiones derivadas (depende de PersonPicker integrado + ENH-077).
    - US-118 Fases 2 (RBAC migra a leer participations) y 3 (drop project_members) — abrir US separadas con owner OK explícito por blast radius.
    - US-119 cleanup: drop legacy actors.team_id, actors.is_lead, teams.area_id, tasks/risks/issues.area_id (mantenidos hasta que el cableado de PersonPicker complete migración).
  Pendiente owner: crear label EP017 en GitHub UI y aplicar a #349-353; verificar fix; cerrar issues.

### EP008/EP014 — Minutas v1.0 — INBOX 2026-05-22 (Sprint 26 Bloque 0, antes que dependencias EP020)

> Frente minutas: estructura rígida + parser IA correcto + matching de participantes + suscripciones.
> Cierra deuda histórica + abre suscripciones equivalente a US-056 pero para minutas.
> Status sugerido: `status:triage` hasta que owner pase a `status:ready`.

**BUG-061 — Preview muestra RAID pero al guardar no persiste**
- Contexto: en el flow `/ai-minutes/new`, el preview muestra correctamente los items RAID sugeridos por el IA. Al hacer "Aceptar" / guardar, los items no se persisten en la minuta resultante (sí queda el texto pero los RAID quedan vacíos).
- AC:
  - [ ] Al guardar (`POST /ai-minutes/{id}/accept`), los items del preview RAID pasan a la tabla correspondiente (acciones, riesgos, decisiones, issues) ligados a la minuta.
  - [ ] Si el PM desmarcó algún sugerido en el preview, NO se crea.
  - [ ] TC verde con minuta de ejemplo de 5 items mixtos.
- Fix propuesto: revisar `apps/web/app/(app)/pmo/projects/[id]/ai-minutes/new/page.tsx` (preview) vs `apps/api/app/api/v1/endpoints/ai.py` (accept handler); el accept debe iterar sobre items confirmados y crear registros, no solo guardar texto.
- Epic: EP008.
- Sprint: 26 Bloque 0.

**ENH-102 — Parser RAID estricto (solo A/R/D/I, descartar lecciones/cambios) + opción crear items**
- Contexto: hoy el IA alucina y sugiere lecciones y cambios mezclados con RAID. La regla es estricta: solo Acciones, Riesgos, Decisiones, Issues. Además, cada sugerencia debe tener checkbox "crear como item del proyecto" (ya estaba — verificar que sigue funcionando tras BUG-061).
- AC:
  - [ ] Prompt schema ampliado solo permite tipos {action, risk, decision, issue}. Lecciones/cambios rechazados en validación post-IA.
  - [ ] Si el modelo emite item con tipo no permitido, descartar silenciosamente.
  - [ ] Cada item sugerido tiene checkbox individual "crear" (default sí); al aceptar la minuta solo se crean los marcados.
  - [ ] TC: prompt con transcript que menciona "lección aprendida" no produce item.
- Archivos: `apps/api/app/services/ai/prompts.py`, validador post-IA en `services/ai/validator.py` (nuevo si no existe).
- Epic: EP008.

**ENH-103 — Match participantes ↔ actores del proyecto (auto-link + crear faltantes)**
- Contexto: hoy los participantes de la minuta son strings libres. Necesitamos que se conecten con actores del proyecto (EP017 directorio). Si el participante existe → link; si no, crear actor on-the-fly con flag `unverified`.
- AC:
  - [ ] Al guardar minuta, cada participante se intenta matchear (case-insensitive, fuzzy match por nombre completo) contra `project_participations` del proyecto.
  - [ ] Match exitoso → link `minute_participants.actor_id` se asigna.
  - [ ] Sin match → crear `actor` con `auto_created=true` y `verified=false`; agregar al proyecto vía `project_participations` con rol "guest".
  - [ ] UI muestra los matcheados como chips verdes y los nuevos como chips amarillos.
- Archivos: `apps/api/app/services/minutes/participant_matcher.py` (nuevo), `apps/web/components/minute-raid-suggestions-editor.tsx`.
- Epic: EP008 + EP017.

**ENH-104 — Título auto desde nombre de archivo + prompt al guardar si vacío**
- Contexto: hoy el título default es "Minuta (IA)". El owner quiere: si el origen es un archivo importado, usar el nombre del archivo; si transcript IA o manual y queda vacío, abrir modal al guardar pidiendo título.
- AC:
  - [ ] Import file: `title = file.name` (sin extensión), editable.
  - [ ] Transcript IA / manual: `title = ""` por default; modal "Confirma el título" obligatorio al guardar si vacío.
  - [ ] Sin modal si el usuario ya editó el título.
- Archivos: flow `/ai-minutes/new`, modal nuevo en `apps/web/components/minute-save-modal.tsx`.
- Epic: EP008.

**ENH-105 — Estructura de minuta v1.0 (6 secciones fijas)**
- Contexto: cerrar la estructura rígida especificada por owner.
- AC:
  - [ ] Secciones: 1. Encabezado, 2. Participantes (asistentes + ausentes justificados + no justificados), 3. Agenda (resumen 2-3 oraciones), 4. Desarrollo por tema (bullet points), 5. RAID (A/R/D/I), 6. Notas libres (opcional).
  - [ ] No se admiten secciones extra ni reordenamiento.
  - [ ] Plantillas export (`.pdf`, `.docx`, `.md`, `.txt`) actualizadas con la nueva estructura.
  - [ ] Prompt IA actualizado para emitir JSON con esta estructura.
- Archivos: `apps/api/app/services/minutes_formatter.py`, plantillas `apps/api/app/templates/pdf/minutes/minute.html`, prompt EP008.
- Epic: EP008 + EP014.

**ENH-106 — Campo de auditoría `origin` en minuta (manual / transcript-IA / import)**
- Contexto: el origen no aparece en la minuta visible, pero debe quedar en BD para auditoría.
- AC:
  - [ ] `meeting_minutes.origin ENUM ('manual','transcript_ai','import_file','import_paste')` NOT NULL.
  - [ ] Backfill: registros existentes → `'manual'` o `'transcript_ai'` según `generated_by_ai`.
  - [ ] Visible en admin/audit log; NO renderizado en la minuta exportada.
- Migración Alembic.
- Epic: EP008.

**ENH-107 — Suscripciones programadas de minutas**
- Contexto: hoy reportes tienen `scheduled-reports` (US-056). Minutas no. Owner pide símil.
- AC:
  - [ ] Endpoint `POST /projects/{id}/scheduled-minutes` con cadence (weekly/monthly), destinatarios, plantilla de minuta opcional.
  - [ ] Worker beat: en el cron, busca la última minuta del proyecto en el periodo y la envía como PDF a la lista.
  - [ ] Si no hay minuta en el periodo → email con "Sin minuta registrada en este periodo".
  - [ ] Reusa motor Resend y patrón US-056.
- Archivos: `apps/api/app/services/scheduled_minutes.py` (nuevo), endpoints, worker tasks.
- Epic: EP014.

**ENH-108 — Copy-paste directo de transcript (sin file upload)**
- Contexto: hoy en `/ai-minutes/new` solo se sube archivo. Owner pide modal con textarea grande para pegar transcript directo.
- AC:
  - [ ] En `/ai-minutes/new`, dos tabs: "Subir archivo" (existente) | "Pegar transcript".
  - [ ] Tab paste: textarea ≥ 10 líneas visibles, sin límite duro de chars (warn al pasar 50k chars).
  - [ ] Mismo flow downstream que upload: crea AIJob, polling, preview, accept.
- Archivos: `apps/web/app/(app)/pmo/projects/[id]/ai-minutes/new/page.tsx`.
- Epic: EP008.

**Total Sprint 26 Bloque 0:** 1 BUG + 7 ENH = 8 items.

(antes: vacío — todos los issues nuevos están organizados en bloques de Sprint 13-16, ver abajo.)
```

### EP020 — Report Builder (Niveles 1, 2, 4) — INBOX 2026-05-22

> Epic doc: `docs/epics/EP020-report-builder.md`
> Catálogo detallado: `docs/epics/drafts/EP020-secciones-atomicas.md`
> Status sugerido para todos: `status:triage` hasta que owner pase a `status:ready` por bloque.

**Dependencias del sistema (Sprint 26 Bloque 1 — ENH a otros epics):**
- ENH-097 — EP006 Plan: `tasks.is_critical` boolean (reemplaza columna existente)
- ENH-098 — EP007 Admin: `progress_calculation_method` por tenant
- ENH-099 — EP007 Admin: `task_load_thresholds` por tenant
- ENH-100 — EP002 Org: `client_logo_url` + UI upload
- ENH-101 — EP005 Projects: `status_rag` declarativo del PM

**Backbone (Sprint 26 Bloque 2):**
- US-120 — Modelo y seed del catálogo de 22 secciones atómicas
- US-121 — Servicio cálculo % avance configurable por tenant
- US-122 — Modelo de plantillas + 4 plantillas seed (L3-Avance, L3-Seguimiento, L1-Portafolio, L2-Org)

**Motor de render + export (Sprint 27 Bloque 1):**
- US-123 — Engine de render con modos composición A (por sección) / B (por área)
- US-130 — Export PDF de reportes custom

**Canvas Nivel 4 (Sprint 27 Bloque 2):**
- US-124 — Canvas drag-and-drop + preview en vivo
- US-125 — Panel de parámetros transversales
- US-126 — Plantillas privadas + publicar al proyecto

**IA + Suscripciones (Sprint 28):**
- US-127 — Modo IA conversacional construyendo el reporte (tool calls)
- US-131 — Suscripciones de reportes custom (reusa US-056)

**Módulos UI Niveles 1/2 + Gantt (Sprint 29):**
- US-128 — Módulo UI Reportes Nivel 1 PMO (`/pmo/reports/portfolio`)
- US-129 — Módulo UI Reportes Nivel 2 Org/Programa (tab en organización)
- US-132 — Render headless del Gantt WBS-1 para S-19 (puppeteer/playwright)

**Fuera de scope v1.0 (postergado v2.0):**
- Snapshots históricos del semáforo y de KPIs (S-05 tendencia, sparklines, deltas vs anterior).
- S-07 Curva S (descartada — incompatible con flexibilidad del plan).
- S-10 Entregables formales (concepto no configurado en plataforma).

**Pendientes externos al owner:**
- Crear labels `EP020`, `EP020:catalog`, `EP020:builder`, `EP020:portfolio` en GitHub UI.
- Aprobar triage por bloque y pasar issues a `status:ready` antes de arrancar Sprint 26.

---

## ⏳ QUEUE

**Sprint 11 (v1.10) — Bloque 1 ENTREGADO 2026-05-06. Bloques 2+3 `status:ready` por owner 2026-05-06.**

### Sprint 11 — Bloque 1: Nav review (2 BUGs) ✅ ENTREGADO
- [x] BUG-042 #206 — Breadcrumb desde Programa → link Org va a PMO en lugar de Admin — `4591aee`
- [x] BUG-043 #207 — Panel de Programa en vista PMO Org no es clicable — `98822f7`
- [x] (pasada UI 2026-05-06 → 23 findings → 13 issues triagados → Bloques 2 + 3)

### Sprint 11 — Bloque 2: Nav cleanup (5 issues — cierra patrón BUG-042) ✅ ENTREGADO
- [x] BUG-044 #216 — Admin Org → tabla proyectos `?ctx=admin` + project detail ctx-aware — `0e1bd0e`
- [x] BUG-045 #217 — Admin Supervisión → links proyectos `?ctx=admin` — `63c5352`
- [x] ENH-057 #218 — Admin pages con Breadcrumb (4 pages) — `0aee75d`
- [x] ENH-058 #219 — `pmo/projects/new` + `pmo/requests/new` con Breadcrumb + BackLink — `de9dc0b`
- [x] ENH-059 #220 — `admin/users/[id]` migra a `<BackLink>` reutilizable — `9cc4fc6`

### Sprint 11 — Bloque 3: RAID polish (5 issues — correctness primero) ✅ ENTREGADO
- [x] BUG-046 #221 — Priority como badge color (P1=red, P2=warning, P3=info, P4+=neutral) — `e27d560`
- [x] BUG-047 #222 — closure_note vía Modal + Textarea (sin `window.prompt`) — `68e8d5b`
- [x] BUG-048 #223 — Title trim + min_length backend (TitleStr Annotated) + frontend submit guard — `213ad11`
- [x] ENH-060 #224 — Status dropdown spinner + check verde 1.5s — `55b615b`
- [x] ENH-061 #225 — Matriz P×I celdas clicables → filtran tabla con chip [×] — `a16699c`

### Backlog v2.0 — RAID polish diferidos (P3 de pasada UI 2026-05-06)
- Bulk actions multi-select RAID
- Empty states per-severity en lista RAID
- Preview modal "Abrir/Editar" link
- Keyboard shortcut (Ctrl+K) crear RAID item
- Type-change post-creación: confirmation modal
- Audit log UI por item RAID
- Date format inconsistency Issue table
- Closure prompt cancelar: estado inconsistente

---

## ⏳ Sprint 12 (v1.10/v1.11) — Bloques 1+2+3 ENTREGADOS 2026-05-06

### Sprint 12 — Bloque 1: Plan fixes + plantilla (5 issues) ✅ ENTREGADO
- [x] BUG-049 #230 — WBS natural sort (1.1 → 1.2 → 1.10) — `fb35a2e`
- [x] BUG-050 #231 — Outline level auto-calc en imports + backfill 0043 — `374e4cc`
- [x] BUG-051 #232 — Tareas delayed con marca visual roja — `99a481c`
- [x] US-095 #229 — Editar tarea (botón Pencil + modal pre-poblado) — `eab7849`
- [x] US-096 #227 — Plantilla XLSX con fórmulas + nuevos campos — `8889751`

### Sprint 12 — Bloque 2: Admin restructure (2 issues) ✅ ENTREGADO
- [x] US-094 #228 — Página `/admin` landing con 6 paneles — `41d617e`
- [x] ENH-062 #233 — Quitar "Gestión de" en labels admin — `8929a43`

### Sprint 12 — Bloque 3: Reportes refinamiento (2 issues) ✅ ENTREGADO
- [x] ENH-063 #234 — Filtro periodo (1d/1sem/2sem/1mes/3meses) — `7321e0f`
- [x] ENH-064 #235 — Default focus hitos/críticas/delayed — `f7db92c`

### Post-Sprint 12 — Reworks 2026-05-06 (branch claude/fix-issues-plan-sprints-2psWS)
- [x] #228 US-094 rework — sidebar `Admin` linkea a `/admin` — `4d82b4b` (cerrado por owner)
- [ ] #229 US-095 rework v2 — `cache:no-store` + optimistic update wins — `cf0283e` (v1 `204f2fd` no resolvió, owner revisar)

### Reworks Sprint 11 ya entregados (esperando verificación)
- [x] #204 ENH-054 fase 2 — `25ec5a0`
- [x] #205 US-091 fase 2 — `aa1a1ad`
- [x] #209 ENH-055 fase 2 — `682b06c`

---

## ⏳ Sprint 13 (v1.12) — Áreas + Plan — Bloque 1 ENTREGADO 2026-05-07
Branch sesión: `claude/fix-issues-plan-sprints-2psWS` (rama Sprint 13 reservada `claude/sprint-13-areas-plan` no se usó al ya estar la sesión activa).

- [x] US-097 #240 — Jerarquía Áreas → Equipos → Actores (CRUD 3 niveles + migración 0044) — `9d264cc`
- [x] US-098 #241 — Plan: asignar Área responsable (edit form + filtro + migración 0045) — `7fd939f`
- [x] ENH-067 #243 — Plan: toggles de nivel WBS (1/2/3/4/Manual) — `e36f937`
- [x] ENH-066 #242 — Plan: toggle "Agrupar por Área" (mutex con WBS) — `237374b`
- [x] ENH-068 + ENH-077 #244 #259 — Gantt sync con lista + composición chips × agrupador × nivel — `f6f349c`
- [x] US-099 #245 — Reasignación masiva de actores (bulk move tareas) — `632fdf9`

**Pendiente verificación owner:** cerrar #240-#245 + #259 tras smoke test.

**Migraciones Alembic agregadas:** 0044 (areas/teams/actors) + 0045 (tasks.area_id).

**Diferidos del bloque (no bloqueantes):**
- US-098 CA3: columna "Área" bajo MSP toggle — owner valida densidad MSP.
- ENH-066: colapsado de grupos por Área (chevrons como WBS) — owner valida si lo necesita.
- ENH-068 CA10: headers de grupo Área dentro del Gantt — Gantt es plano pero respeta el filtro.
- US-099 CA3: preview pre-operación con conteo — hoy se ve POST-operación.
- US-099 RAID/minutas: scopes adicionales cuando se valide modelo de actores en esos módulos.

**Migración Alembic prevista:** 1 — `areas`, `teams`, `actors` + `tasks.area_id`.

---

## ⏳ Sprint 14 (v1.13) — RAID detail redesign "Denso" — Bloque 1 ENTREGADO 2026-05-07
Branch sesión: `claude/fix-issues-plan-sprints-2psWS`

- [x] US-100 #246 — Rediseño detalle item RAID layout "Denso" (4 tipos) — `7b1bf5e`
- [x] ENH-069 #247 — Banner modo edición + Cancelar/Guardar transaccional — `7b1bf5e`
- [x] ENH-070 #248 — Card unificada Comentarios + Historial — `7b1bf5e`
- [x] BUG-052 #249 — Breadcrumb `RAID / Tipo / ID` + ← Volver preserva filtro — `6b5fa2e`

**Pendiente verificación owner:** cerrar #246-#249 tras smoke test.

**Sin cambios de schema, sin cambios de paleta.** Spec canónica: `docs/design-system/raid-detail-denso.md`.

**Diferidos del bloque (no bloqueantes):**
- US-100: P×I como cuadritos visuales explícitos del mock (hoy "3 × 3 = 9" inline).
- US-100/ENH-070: avatar/nombre del autor en comentarios — endpoints actuales no devuelven user mini en el shape de Comment.
- ENH-069 CA6: confirm "descartar cambios" al navegar fuera con dirty form.

---

## ⏳ Sprint 15 (v1.14) — Áreas refinement + Plan responsables — Bloque 1 ENTREGADO 2026-05-07
Branch sesión: `claude/define-area-roles-tYoXl`

### Bloque 1 (4 issues, commits separados)
- [x] BUG-054 #265 — Vista "Por Actor" empty state contextual — `5cd31eb`
- [x] US-103 #263 — Áreas catálogo compartido + assignments cascada (org/program/project/global) + PMO seed global + endpoints `/admin/areas/{id}/assignments` y `/admin/areas/by-project/{id}` — `0a7768d` (migración 0048)
- [x] ENH-078 #264 — Restructura Áreas + drop `project_areas`: 2 toggles, árbol jerárquico, 3 forms, líder=Actor con is_lead=true. Op A completa. — `b2bb881` (migración 0049)
- [x] ENH-079 #266 — Plan: responsable = Actor + sync PMO users → Actores. Backfill task/risks/issues por user_id match. — `db20f0e` (migración 0050)

**Pendiente verificación owner:** cerrar #263-#266 tras smoke test.

**Migraciones Alembic agregadas:** 0048 (area_assignments + repoint task/risks/issues + PMO seed) + 0049 (actors.is_lead + areas.lead_actor_id + DROP project_areas) + 0050 (assignee_actor_id + sync PMO).

**Decisiones owner 2026-05-07:**
- Opción A: `project_areas` deprecada y dropeada (0049). Catálogo tenant `areas/teams/actors` es fuente única.
- Líder del área = Actor con `is_lead=true`, creado primero antes del área.
- RAID owner = single-FK a actors (no polimórfico). PMO users → Actores en área "PMO" global.
- TC-5 (desasignar área con tareas): forzar reasignación (a implementar en endpoint que valide).

**Diferidos del bloque (no bloqueantes):**
- ENH-078: edit panel inline para gestionar equipos/recursos del área desde un solo modal; selector de actor existente como líder.
- ENH-078: cascade checkboxes UI en `/admin/areas/{id}` (backend listo, UI sigue pendiente).
- ENH-079: RAID create/edit dropdown owner sigue usando users (switch a Actores requiere RaidCreate/Update schema changes).
- ENH-079: DB trigger / hook para sync continuo PMO users → Actors al crear user nuevo (hoy 1-time backfill).
- US-103 TC-5: endpoint que bloquea desasignar con tareas activas (hoy permite + cascade NULL via FK).

**Migraciones Alembic previstas:** 2 (0046 area_assignments + PMO seed; 0047 actor fields + tasks.assignee_actor_id + raid_items owner polimórfico).

**Decisiones owner 2026-05-07:**
- Líder del área se persiste como Actor con flag `is_lead=true` (no campos sueltos en `areas`).
- Nuevo epic **EP017 (Áreas/Actores)** referenciado también desde EP004 (Admin) porque la página vive en `/admin/areas`.
- US-103 y ENH-078 quedan como issues separados pero entregados en el mismo bloque.

---

## ⏳ Sprint 16 (v1.14) — Reportes ✅ CERRADO 2026-05-07
4 issues (#250 ENH-071 + #251 ENH-072 + #252 ENH-073 + #253 US-101) entregados v1.14, todos `state:closed completed`. Detalle archivado en `SPRINT-DONE-HISTORY.md`.

---

## ⏳ Sprint 17 (v1.16) — IA conversacional global

### Bloque 0 (gate pre-arranque) ✅ ENTREGADO 2026-05-08
- [x] BUG-053 #254 — Cleanup residuos Ollama + cablear Groq (default) + BYO whitelist — `d6947d3`
  - **Decisión owner 2026-05-06:** provider de planta = **Groq**. BYO whitelist = `gemini, openai, anthropic, perplexity`.
  - **Migración Alembic 0053** agregada.

### Bloque 0.5 ⏳ IN-PROGRESS 2026-05-08
- [ ] US-104 #298 — Módulo BYO: test-before-save + custom provider + retry. Branch `claude/setup-ai-module-8HYs1`.

### Bloque 1 ⏸️ POSTERGADO 2026-05-08 (ver sección Deferred)

---

## ⏸️ Deferred — re-evaluación post Sprints 18-23

> Issues abiertos sin asignación de versión. Se retoman cuando owner decida.

### IA conversacional global (ex Sprint 17 Bloque 1)
- [ ] US-102 #255 — Side-panel chat IA en cada página (Ctrl+K + flotante)
- [ ] ENH-074 #256 — Context-awareness por página
- [ ] ENH-075 #257 — Tool-use (crear tarea / RAID / nav)
- [ ] ENH-076 #258 — Historial persistente + summary rolling

**Decisión owner 2026-05-08:** posterga el chat global. Primero ejecutar Sprints 18-23 (Documentos / RAID / Minutas / Reportes / Cambios / BYO universal). Volver a evaluar necesidad después.

### Pendiente redefinición Áreas/Recursos
- [ ] US-105 #311 — Import Plan: wizard matching responsables → Actor. Depende del shape final del catálogo Actores que salga de la redefinición. Se queda en `status:triage` hasta entonces.
- [ ] **Tab Organigrama de US-106** — placeholder UI en Sprint 18; el cableado funcional (lista de recursos asignados al proyecto) depende del mismo paquete.

**Decisión owner 2026-05-08:** la redefinición de Áreas/Recursos es el próximo paquete arquitectónico (sin issue creado todavía). Los items de arriba quedan congelados hasta que ese paquete se planee y entregue.

---

## ⏳ Sprint 18 (v1.17) — Documentos & Plan vivo — Bloque 1 ENTREGADO 2026-05-08
Branch sesión: `claude/review-start-next-sprint-R8JWc` (rama reservada `claude/sprint-18-documentos-plan` no se usó al ya estar la sesión activa).

### Bloque 1 (3 issues, commits separados)
- [x] US-106 #308 — Sistema de Artefactos por proyecto (Charter / Plan / RAID / Organigrama, whitelist) — `6e2f947`
- [x] ENH-081 #309 — Charter auto-creación + backfill + completeness banner — `0b43755`
- [x] ENH-080 #310 — Plan vivo: regeneradores xlsx/csv + fallback mpp — `13f51ed`

**Pendiente verificación owner:** cerrar #308-#310 tras smoke test.

**Migraciones Alembic agregadas:** 0055 (`project_artifacts` table) + 0056 (charter backfill data migration) — requieren `alembic upgrade head` en Railway api+worker.

**Diferidos del bloque (no bloqueantes):**
- US-106 CA6: permisos PM/admin para reemplazar artifacts — escritura cubierta hoy via endpoints nativos (charter PATCH, tasks/import); el endpoint genérico de upload de artefactos se cablea cuando lo pidan.
- US-106: subroute `/documents/legacy` (free-form upload) sigue accesible vía link; quitar cuando se migre la data al modelo de artefactos.
- ENH-080 CA3: roundtrip MPP write requiere MPXJ Pro / subprocess Java — fallback a XLSX devuelve header `X-Plan-Format-Fallback`. Diferido hasta que un usuario reporte el caso de uso real.
- ENH-080: storage del archivo original (preservar fórmulas/macros .mpp) — no necesario hoy: regen desde DB cumple los CA.
- ENH-081: lista `CHARTER_REQUIRED_FIELDS` per-tenant — diferido a cuando ≥3 tenants pidan customización.

**Decisiones:**
- DB es fuente de verdad del Plan; archivo se regenera on-demand en formato origen.
- Tab Organigrama = placeholder en Sprint 18; cableado real post-redefinición Áreas/Recursos.

**Migraciones Alembic previstas:** 2 — `project_artifacts`, charter backfill.

**Epic:** EP018 (Documentos / Artefactos) — nuevo, ver `docs/epics/EP018-documents-artifacts.md`.

---

## ⏳ Sprint 19 (v1.18) — RAID polish + vistas dedicadas — Bloque 1 ENTREGADO 2026-05-09
Branch sesión: `claude/review-start-next-sprint-R8JWc` (3 issues backend pesado) +
`claude/continue-sprint-tasks-jR3zt` (3 issues UI vistas dedicadas).

### Bloque 1 entregado (6 de 6)
- [x] US-107 #313 — Acciones de mitigación (multi-actor) + migración 0057 — `9d94fc9`
- [x] ENH-082 #312 — Export RAID Excel 4 sheets — `0c59aaa`
- [x] ENH-083 #314 — Render mitigación + acciones inline RAID detail — `5eb6b69`
- [x] ENH-088 #315 — Preview "tarjeta flotante" centrada + `openHref` (reemplaza side panel) — `e021a97`
- [x] ENH-086 #316 — Lecciones: página dedicada `/pmo/projects/[id]/lessons/[lessonId]` + GET/PATCH backend — `b3798d9`
- [x] ENH-087 #317 — Cambios: página dedicada `/pmo/projects/[id]/changes/[changeId]` + GET/PATCH backend — `4d91009`

**Pendiente verificación owner:** cerrar #312-#317 tras smoke test.

**Migración Alembic agregada:** 0057 (`risk_actions` + `risk_action_assignees` con CASCADE desde Risk). ENH-086/087/088 sin migración.

**Diferidos del bloque (no bloqueantes):**
- ENH-086/087: card "Comentarios & Historial" muestra placeholder hasta que existan endpoints `lessons/{id}/comments` y `change-requests/{id}/comments` (no priorizado).
- ENH-087 CA6: card "Aprobadores" hoy muestra approver único + nota EP019; el workflow multi-aprobador (US-112/US-113) llega con Sprint 22.

---

## ⏳ Sprint 20 (v1.19) — IA Minutas — Bloque 1 ENTREGADO 2026-05-09
Branch sesión: `claude/continue-sprint-tasks-jR3zt`.

### Bloque 1 (5 de 5)
- [x] ENH-084 #318 — IA Minutas: 4 secciones RAID estandarizadas (post-procesador determinístico) — `719fe50`
- [x] US-108 #319 — Sugerir RAIDs aprobables por PM (editor inline + bulk approve crea tickets reales) — `236990a` (migración 0058)
- [x] BUG-055 #320 — Botón Cancelar (cancela job + worker omite persist) y ← Volver — `eb9baa9`
- [x] ENH-090 #321 — Preview Minuta in-platform (HTML embebido + 4 secciones colapsables + editor RAID) — `a392350`
- [x] ENH-091 #322 — Botón Borrar minuta (header preview + kebab en lista + confirm modal) — `8188685`

**Pendiente verificación owner:** cerrar #318-#322 tras smoke test.

**Migración Alembic agregada:** 0058 (`meeting_minutes.raid_suggestions JSON`) — requiere `alembic upgrade head` en Railway api+worker.

**Diferidos del bloque (no bloqueantes):**
- ENH-090 CA4: botón "Pop-up" para ventana externa — render in-platform cubre el caso principal.
- BUG-055: AbortController para abortar el dispatch HTTP — el dispatch es 202 inmediato; cancelación cubre la parte que importa (worker no persiste).

---

## ⏳ Sprint 21 (v1.20) — Reportes redesign HTML — Bloque 1 ENTREGADO 2026-05-09
Branch sesión: `claude/continue-sprint-tasks-jR3zt`.

### Bloque 1 (4 de 4)
- [x] ENH-085 #325 — `report_templates` tenant-shared + endpoints CRUD + `reports.html_content` — `73bf661` (migración 0059)
- [x] US-111 #324 — Render HTML interactivo con KPIs + filtros vanilla JS embebidos (CA6 incluye Minutas) — `8c33cbd`
- [x] US-109 #323 — Panel 2 modos + tweaker IA HTML (sync endpoint) + historial N=10 + Save como plantilla — `69d1e84`
- [x] ENH-089 #326 — Export `/reports/{id}/export?format=html|pdf|txt` + Minutas con `format=html` + `html_to_pdf`/`html_to_text` helpers — `fdac553`

**Pendiente verificación owner:** cerrar #323-#326 tras smoke test.

**Migración Alembic agregada:** 0059 (`report_templates` table + `reports.html_content` column) — requiere `alembic upgrade head`.

**Diferidos del bloque (no bloqueantes):**
- ENH-089 CA5: selector visual de formato en la lista de reportes (los 3 endpoints están listos; cablear botón download dropdown en `reports/page.tsx` cuando se requiera reusar la página existente).
- US-109 streaming token-by-token (out-of-scope explícito).
- Diff visual entre versiones del HTML tweakeado (out-of-scope explícito).
- Cablear "Guardar como reporte" (`report_history`) en tweak page — hoy solo guarda como plantilla; el flujo completo de persistir un tweak como Report queda como follow-up cuando lo pidan.

---

## ⏳ Sprint 22 (v1.21) — Cambios / Approval workflow — Bloque 1 ENTREGADO 2026-05-09
Branch sesión: `claude/continue-sprint-tasks-jR3zt`.

### Bloque 1 (2 de 2)
- [x] US-112 #327 — Aprobadores multi-actor en Cambios (tabla + endpoints + guards de estado) — `e72b445`
- [x] US-113 #328 — Workflow email + token JWT firmado + landing pública `/approve/[token]` + re-trigger — `e44efdc`

**Pendiente verificación owner:** cerrar #327-#328 tras smoke test.

**Migración Alembic agregada:** 0060 (consolida ambas: `change_approvers` + `approval_tokens` en una sola revisión).

**Epic:** EP019 (Cambios / Approval workflow) — nuevo, ver `docs/epics/EP019-changes-approval.md`.

**Diferidos del bloque (no bloqueantes):**
- US-112 CA2: cableado de la card "Aprobadores" en `ENH-087` (página dedicada de Cambios) — backend listo; UI integration sigue como follow-up cuando el owner valide UX.
- US-113: integración real con proveedor de email (Resend / EP011) — hoy `_send_approval_email` cae a logger.info en dev. Cuando EP011 publique `app.services.notifications.send_email`, se conecta automático.

---

## ⏳ Sprint 23 (v1.22) — BYO universal + Copilot M365 — Bloque 1 ENTREGADO 2026-05-09
Branch sesión: `claude/continue-sprint-work-mcmzX` (rama reservada `claude/sprint-23-byo-universal` no se usó al ya estar la sesión activa).

### Bloque 1 (1 de 1)
- [x] US-110 #329 — BYO universal (`custom` OpenAI-compatible para Together/Mistral/vLLM/etc.) + Azure OpenAI / Microsoft Copilot M365 (provider `azure` con deployment_name + api_version) — `1c5674d`

**Pendiente verificación owner:** cerrar #329 tras smoke test.

**Sin migración Alembic.** El shape `tenants.settings.ai.byo` JSON ya admite los campos nuevos (`deployment_name`, `api_version`, `rate_limit_rpm`, `daily_token_limit`, `acknowledge_security`).

**Diferidos del bloque (no bloqueantes):**
- US-110 CA4 enforcement runtime: los límites `rate_limit_rpm` / `daily_token_limit` se almacenan y exponen al worker via `tenant_ai.load_tenant_ai`, pero el rate-limiter activo (cuenta de requests + cierre de circuito) llega cuando se reporten costos descontrolados.
- US-110 CA6 fase 2: auth via service principal Azure (hoy solo api-key del recurso).
- US-110: GitHub Copilot completion (out-of-scope explícito, no es API chat).
- US-110 CA8 spike Azure: documentación inline cubierta en docstring de `AzureProvider` + tooltips de la UI; ADR formal cuando lo pida el owner.

**Decisiones:**
- Azure usa API REST OpenAI-compatible (`{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=...`), header `api-key`. El campo `model` es informativo: el deployment es server-side.
- `custom` mantiene whitelist (heredada de US-104) pero ahora obliga `acknowledge_security=true` antes de guardar (CA3).
- Test-before-save US-104 cubre `azure` con POST mínimo a `/chat/completions`.

**Epic:** EP008 (IA / proveedores).

---

**Próximo libre:** US-114, BUG-061, ENH-097.

---

## ⏳ Sprint 24 (v1.23) — Feedback batch 2026-05-09 — Bloque 1 ENTREGADO 2026-05-09
Branch sesión: `claude/fix-project-charter-issues-RFoAy`.

Triage owner-aprobado para batch en una sesión: 10 issues nuevos +
2 reworks. 12 commits separados (1 por item).

### Bloque 1 — Documentos & Plan polish (5 items)
- [x] BUG-056 #336 — Cancelar edición Charter → `/documents` (no resumen) — `8807084`
- [x] ENH-092 #337 — Charter filename usa nombre de proyecto slugificado — `5591e8d`
- [x] BUG-057 #338 — Plan download `.bin` → plantilla XLSX (frontend fallback + `_plan_meta` reporta source_format) — `bd9b138`
- [x] ENH-093 #339 — RAID export filename usa nombre de proyecto slugificado — `772d01b`
- [x] ENH-094 #340 — Plan `duration_days > 21` = warning, no blocker — `834d02b`

### Bloque 2 — Minutas (4 items)
- [x] ENH-095 #341 — Editor estructurado por secciones en preview minuta (Participantes / Temas / Acuerdos) — `e3f5b44`
- [x] ENH-096 #342 — Minuta IA: bullets más detallados, 2-5 oraciones con contexto + responsables + fechas — `1705494`
- [x] BUG-058 #343 — Preview muestra RAIDs pero al guardar quedaba vacío (faltaba aceptar `raid_suggestions` en `MeetingMinuteCreate`) — `127ee97`

### Bloque 3 — Reportes (3 items, 1 = rework)
- [x] US-109 #323 (rework) — CTA visible para panel 2 modos (`/reports/tweak`) — `0c1304c`
- [x] US-111 #324 (rework) — Preview HTML interactivo (export?format=html&inline=true + botón en historial) — `7fd2343`
- [x] BUG-059 #344 — Preview reporte respeta `rep.html_content` (último tweak) en lugar de `sections["_html"]` (snapshot original) — `c365bf2`

### Bloque 4 — IA (1 item)
- [x] BUG-060 #345 — `mode=byo` ya no exige `body.byo` cuando hay config previa persistida — `3170581`

**Pendiente verificación owner:** cerrar #336-#345 + #323/#324 tras smoke test.

**Sin migraciones Alembic.** Solo cambios de código y prompt.

**Diferidos del bloque (no bloqueantes):**
- ENH-094 fase 2: warning visual en el form de edit/new task (modal) — hoy solo en la celda de la tabla.
- ENH-095 fase 2: edición de RAID-suggestions del editor inline ya existe (US-108); decisiones / next_steps / risks_blockers todavía read-only en el preview.
- US-111 rework: tweaker IA arrancando desde un reporte existente (hoy `/reports/tweak` carga render default o plantilla — no un `Report` ya guardado).

**Notas:**
- Los commit headers usan `refs #330..#339` (numeración estimada al momento del commit). El número real en GitHub es `+6` (issues creados después del último issue persistido en el repo). El mapping arriba (`BUG-056 #336` etc.) es la fuente de verdad.
- Branch única `claude/fix-project-charter-issues-RFoAy` para todo el batch (owner pidió "resolvamos esto", excepción al multi-branch reservado por bloque).

### Follow-ups identificados (Sprint 9+)
- US-081 — Borrar físicamente tablas `roles` + `user_roles` (migración 0037+) tras validación de Sprint 6 en producción.
- ENH futuro — Filtrado efectivo de queries por `organization_user_exclusions`.
- Cross-empresa nativo (post-ENH-043): si ≥3 grupos lo solicitan, abrir US con `program_organizations` + redesign listados.
- US-086 fase 2 — Cablear stakeholders FK en Charter (sponsor / business lead / technical lead) + migración data charters strings → stakeholders.
- US-084 fase 2 — Banner de divergencias cuando importadores MPP/XLSX detecten diferencia entre manual y calculado; botón "Resetear a calculado" en UI.
- US-087 fase 2 — Campos `Task.hours_estimated/hours_actual` para que `compute_kpis` exponga horas plan/real.
- Hard-delete User cuando hay `project_request.requested_by` (US-088 fase 2) — endpoint reasignación interactiva.

---

## ✅ DONE

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo (Sprints 1-10).**

| Sprint | Versión | Cerrado | Items |
|---|---|---|---|
| 1 | v1.0 MVP | 2026-04-21 | ~94 (22 bloques) |
| 2 | v1.1 | 2026-04-23 | 18 (4 bloques + hotfix) |
| 3 | v1.2 | 2026-04-24 | 5 (2 bloques) |
| 4 | v1.3 | 2026-04-24 | 14 (4 bloques) |
| 5 | v1.4 | 2026-04-24 | 10 (6 bloques + follow-up) |
| 6 | v1.5 | 2026-04-25 | 5 (5 bloques) |
| 7 | v1.6 | 2026-04-28 | 10 (6 bloques, 1 diferido v2.0) |
| 8 | v1.7 | 2026-04-29 | 13 (7 bloques, 1 not_planned) |
| 9 | v1.8 | 2026-05-05 | 6 (2 bloques + hotfix UX) |
| 10 | v1.9 | 2026-05-06 | 14 (6 bloques) |
| 16 | v1.14 | 2026-05-07 | 4 (1 bloque — Reportes) |

---

## 📋 Backlog v2.0 (post-v1.x)

> **Contexto (DEC-020):** plataforma definida como herramienta de apoyo/visualización
> sin aprobaciones jerárquicas. US-061 cancelada; US-059/US-060 entregadas en Sprint 4.

- [ ] ENH-035 #158 — Análisis profundo optimización CI tests pesados (post-MVP, diferido Sprint 7).
- [ ] (posibles items futuros: 2FA, SSO, magic-link login)

---

## Notas y cambios recientes

- **2026-05-10 (EP017 Directorio de Proyecto — diseño + triage):** owner pidió rediseño del módulo de Áreas/Recursos basado en feedback de modelo (separar área funcional / equipo operativo / rol proyecto / participación temporal). Decisión clave: `actors` sigue como catálogo tenant; nueva tabla `project_participations` (con `is_primary` por persona-proyecto) reemplaza la jerarquía `Area→Team→Actor`; `teams` queda plano sin FK a area; `project_roles` nuevo catálogo editable; en Plan se elimina FK directo a área (drop `tasks/risks/issues.area_id` con snapshot a `legacy_area_id`) — los filtros derivan vía join contra primary participation. 5 issues triaged en INBOX (US-114→US-118, `#349`-`#353`); epic doc creado en `docs/epics/EP017-project-directory.md`. Branch sesión: `claude/design-areas-resources-8DIfi`. Pendiente owner: crear label `EP017` en GitHub UI; aprobar `status:ready` para Bloque 1.
- **2026-05-09 (Sprint 24 — feedback batch entregado, 12 de 12):** owner pegó dump de 12 items mezclando BUGs / ENHs / reworks tras smoke test (Documentos, Plan, Minutas, Reportes, IA admin). Triage produjo 10 issues nuevos (`#336-#345`) + 2 reworks (`#323`, `#324`). 12 commits separados sobre branch `claude/fix-project-charter-issues-RFoAy`. **Sin migraciones Alembic.** Highlights: nuevo helper `app.services.filename_slug` con patrón canónico `{project-slug}-{kind}.{ext}` reusado por Charter / Plan / RAID; `MeetingMinuteCreate` ahora acepta `raid_suggestions`; `MeetingMinuteUpdate` extendido con `participants`/`topics`/`agreements` editables desde el preview; prompt MINUTE_SYSTEM mejorado para bullets de 2-5 oraciones; `ensure_duration_max_21` se vuelve no-op (warning visual en plan); `download_report_history` y `export_report?format=html` ahora respetan `rep.html_content` (último tweak) e `inline=true`; `update_provider_config` permite `body.byo=null` cuando hay config previa.
- **2026-05-09 (Sprint 23 Bloque 1 cerrado — 1 de 1):** entregado US-110 sobre branch `claude/continue-sprint-work-mcmzX`. 1 commit (`1c5674d`). Sin migración Alembic — el shape `tenants.settings.ai.byo` admite los campos nuevos como JSON. Cambios principales: `AzureProvider` agregado a `provider.py` (header `api-key`, no Bearer); `BYO_PROVIDERS` extendido con `"azure"`; `BYOConfigIn` nuevos campos `deployment_name`, `api_version`, `rate_limit_rpm`, `daily_token_limit`, `acknowledge_security`; `_ping_byo_provider` rama Azure que POSTea a `/openai/deployments/{deployment}/chat/completions?api-version=...`; UI wizard expone deployment + api_version cuando catálogo declara `requires_azure_fields`, y banner de seguridad + checkbox cuando `requires_security_ack` (custom). 12 tests nuevos (`test_us110_byo_universal.py`) + actualizado el test de catálogo en `test_us057_ai_multimode.py`. CA4 enforcement (rate-limiter activo) diferido hasta que se reporten costos descontrolados; los límites se persisten ya y `load_tenant_ai` los propaga al worker.
- **2026-05-09 (Sprint 22 Bloque 1 cerrado — 2 de 2):** entregados US-112 + US-113 sobre branch `claude/continue-sprint-tasks-jR3zt`. 2 commits (`e72b445` US-112 backend con migración 0060 consolidada — incluye ambas tablas `change_approvers` + `approval_tokens` para evitar revisiones intercaladas; `e44efdc` US-113 endpoints públicos + landing `/approve/[token]`). **1 migración Alembic** (0060) requiere `alembic upgrade head`. JWT HS256 firmado con `APPROVAL_TOKEN_SECRET` o `JWT_SECRET`; en DB queda solo el SHA256 hash. Re-trigger borra tokens previos (CA11) — los aprobadores readicionados quedan reset a pending. Email cae a `logger.info` cuando EP011 no expone `send_email`; integración real es follow-up sin bloqueo.
- **2026-05-09 (Sprint 21 Bloque 1 cerrado — 4 de 4):** entregados ENH-085 + US-111 + US-109 + ENH-089 sobre branch `claude/continue-sprint-tasks-jR3zt`. 4 commits separados (`73bf661` ENH-085 con migración 0059 + tabla `report_templates` + columna `reports.html_content`, `8c33cbd` US-111 con `html_report_renderer` reusable para reportes y minutas, `69d1e84` US-109 con tweaker UI + endpoint sync `/ai/reports/tweak-html`, `fdac553` ENH-089 con `/reports/{id}/export?format=html|pdf|txt` + helpers `html_to_pdf`/`html_to_text`). **1 migración Alembic** (0059). Reusa el patrón de `<details>` colapsables y filtros vanilla JS embebidos del template de US-111 para que el HTML descargado funcione offline (CA4). El tweaker es sync (out-of-scope: streaming) — historial N=10 in-memory + botón Deshacer.
- **2026-05-09 (Sprint 20 Bloque 1 cerrado — 5 de 5):** entregados ENH-084 + US-108 + BUG-055 + ENH-090 + ENH-091 sobre branch `claude/continue-sprint-tasks-jR3zt`. 5 commits separados (`719fe50` ENH-084 prompt + post-procesador con `_normalize_raid_block`, `236990a` US-108 con migración 0058 + endpoints CRUD minuta + bulk approve crea tickets reales, `eb9baa9` BUG-055 cancel endpoint + worker check, `a392350` ENH-090 preview page con 4 secciones colapsables + descargas + editor embebido, `8188685` ENH-091 confirm modal en lista). **1 migración Alembic** (0058) requiere `alembic upgrade head` en Railway api+worker. ENH-088 floating preview ya cableado en la lista de minutas con `openHref` → preview dedicado. CA5 de ENH-091 (tickets generados no se borran al borrar la minuta) garantizado por el modelo: `meeting_minutes` no tiene FK hacia los tickets RAID.
- **2026-05-09 (Sprint 19 Bloque 1 cerrado — 6 de 6):** entregados ENH-088 + ENH-086 + ENH-087 sobre branch `claude/continue-sprint-tasks-jR3zt` en 3 commits separados (`e021a97` ENH-088 floating preview, `b3798d9` ENH-086 lessons dedicated page, `4d91009` ENH-087 changes dedicated page). Backend extendido con GET/PATCH para lessons + change-requests (audit logs `lesson.update` y `change_request.update`); status de change requests sigue gobernado por approve/reject. Sin migraciones Alembic. Comentarios&Historial en cards `lesson` y `change` quedan como placeholder hasta que existan endpoints; card "Aprobadores" en cambios anuncia EP019.
- **2026-05-08 (Sprint 19 Bloque 1 parcial — 3 de 6):** owner pidió arrancar Sprint 19; se priorizó "backend pesado primero" (US-107 + ENH-082 + ENH-083). 3 commits sobre branch `claude/review-start-next-sprint-R8JWc`: `9d94fc9` US-107 (risk_actions + assignees N:N + endpoints), `0c59aaa` ENH-082 (export RAID 4 sheets con styling), `5eb6b69` ENH-083 (RiskActionsCard inline en raid-detail-page). **1 migración Alembic** (0057) requiere `alembic upgrade head`. Quedan ENH-088 (floating preview), ENH-086 (Lecciones page), ENH-087 (Cambios page) para siguiente sesión — son refactors de UI (raid-detail-page parametrizable + nuevo componente preview).
- **2026-05-08 (Sprint 18 Bloque 1 entregado):** 3 issues (#308-#310) entregados sobre branch `claude/review-start-next-sprint-R8JWc` en 3 commits separados (`6e2f947` US-106 + `0b43755` ENH-081 + `13f51ed` ENH-080). **2 migraciones Alembic** (0055 `project_artifacts` table + 0056 charter backfill data) requieren `alembic upgrade head` en Railway api+worker. Decisiones owner respetadas: DB es fuente de verdad del Plan, archivo se regenera on-demand; whitelist 4 tipos (charter/plan/raid/organigrama). MPP write fallback a XLSX por limitación MPXJ; tab Organigrama placeholder hasta redefinición Áreas/Recursos.
- **2026-05-08 (deferral US-105 + tab Organigrama):** owner postergó US-105 (#311) y el cableado funcional del tab Organigrama de US-106 (#308) hasta la redefinición del módulo de Áreas y Recursos (próximo paquete arquitectónico, sin issue aún). US-105 queda en `status:triage` sin versión; Sprint 18 Bloque 1 baja de 4 a 3 issues. Tab Organigrama existe como placeholder UI con empty state. Issues #308 y #311 actualizados con la nota; SPRINT.md y EP018 reflejan el cambio.
- **2026-05-08 (triage Sprints 18-23):** owner pegó dump de 22 ideas (Documentos/Artefactos, Plan vivo, RAID polish, IA Minutas, Reportes HTML, Cambios approval, BYO universal). Triage produjo 22 issues nuevos (#308-#329), 2 epics nuevos (EP018 Documentos, EP019 Cambios) y 6 sprints planeados (18-23). Decisiones owner: (a) DB es fuente de verdad del Plan; archivo se regenera preservando formato; (b) matching de Actores en imports = wizard posterior, por nombre, no bloquea; (c) BYO universal con OpenAI-compatible + caso especial Copilot M365 vía Azure OpenAI. Sprint 17 Bloque 1 (chat global #255-258) postergado a re-evaluación; label `v1.15` removido. Sprint 16 (Reportes #250-253) ya estaba 100% cerrado v1.14 — archivado a `SPRINT-DONE-HISTORY.md`.
- **2026-05-07 (Sprint 15 Bloque 1 entregado):** 4 issues entregados en branch `claude/define-area-roles-tYoXl`. 4 commits: `5cd31eb` BUG-054 + `0a7768d` US-103 + `b2bb881` ENH-078 + `db20f0e` ENH-079. **3 migraciones Alembic** (0048+0049+0050) requieren `alembic upgrade head` en Railway api+worker. Op A confirmada por owner: `project_areas` dropeado, catálogo tenant es fuente única. PMO seed global + sync PMO users → Actores. Plan responsable usa Actores; RAID dropdown switch diferido.
- **2026-05-07 (triage Sprint 15 — Áreas refinement):** owner pidió rediseño completo del módulo Áreas tras Sprint 13. Se crearon 4 issues (#263 US-103, #264 ENH-078, #265 BUG-054, #266 ENH-079) con `status:triage`. Sprint 15 (Reportes) → 16 y Sprint 16 (IA) → 17. Nuevo epic **EP017 (Áreas/Actores)** que referencia EP004 (Admin). Decisiones: líder del área se persiste como Actor con `is_lead=true` (no campos sueltos), creado primero antes del área; US-103 y ENH-078 quedan separados pero entregados en el mismo bloque.
- **2026-05-07 (Sprint 14 Bloque 1 entregado):** 4 issues (#246-#249) entregados sobre la misma branch `claude/fix-issues-plan-sprints-2psWS` en 2 commits (`7b1bf5e` US-100+ENH-069+ENH-070, `6b5fa2e` BUG-052). Rewrite completo de `apps/web/components/raid-detail-page.tsx` (188→765 líneas) siguiendo `docs/design-system/raid-detail-denso.md`. **Sin migraciones**, sin cambios de schema ni paleta. Owner planeaba 1 deploy combinando Sprint 13 + 14.
- **2026-05-07 (Sprint 13 Bloque 1 entregado):** 7 issues entregados sobre branch `claude/fix-issues-plan-sprints-2psWS`. 6 commits (`9d264cc`, `7fd939f`, `e36f937`, `237374b`, `f6f349c`, `632fdf9`). Migraciones Alembic 0044 (areas/teams/actors) + 0045 (tasks.area_id) requieren `alembic upgrade head` en Railway api+worker. US-095 #229 rework v2 también pusheado en commit `cf0283e` (cache:no-store + optimistic update post-refetch). Pendiente verificación owner: 7 issues Sprint 13 + #229.
- **2026-05-06 (post-Sprint 12 — reworks + planeación Sprints 13-16):** owner verificó Sprint 12 y reportó reworks: #228 US-094 (sidebar `Admin` no linkeaba a landing) → fix `4d82b4b`; #229 US-095 (edit no refresca tabla) → fix `204f2fd`. Owner aprobó scope de los próximos 4 sprints (Áreas+Plan, RAID detail redesign, Reportes, IA conversacional global). 19 issues creados (#240-#258) con `status:triage` distribuidos en 4 bloques. Sprint 16 incluye **Bloque 0** (BUG-053 cleanup Ollama) como gate pre-arranque. Branches reservadas: `claude/sprint-13-areas-plan`, `claude/sprint-14-raid-detail-redesign`, `claude/sprint-15-reportes-redesign`, `claude/sprint-16-ai-global`.
- **2026-05-06 (Sprint 12 Bloques 1-3 entregados):** 9 commits sobre branch `claude/sprint-12-bloques`, fast-forward desde `main` post-Sprint 11. Migración Alembic 0043 agregada (backfill de `tasks.outline_level`). Owner adelantó que el siguiente bloque será **redesign RAID + Area requirements** (no cubierto por #204/#205/#209/#221-225 ni US-091): scope se definirá al inicio de la próxima sesión sobre branch `claude/redesign-raid-area-requirements-EhZ3d`. ENH-065 #236 cerrado por owner pre-arranque.
- **2026-05-06 (Sprint 11 Bloque 1 entregado):** BUG-042 (breadcrumb context-aware via `?ctx=admin` query param) `4591aee` + BUG-043 (ProgramCard como `<Link>` con hover/focus) `98822f7`. Pendiente owner: verificar + cerrar issues #206 #207.
- **2026-05-06 (Sprint 11 arranque):** Sprint 10 cerrado y archivado a SPRINT-DONE-HISTORY.md (14 items, PR #215 mergeado a main `7e03332`). SPRINT.md queda con Sprint 11 Bloque 1 IN-PROGRESS — solo BUG-042 + BUG-043 pendientes (nav review).
- **2026-05-05 (Sprint 10 triage):** owner pidió planeación próximos 2 sprints + mejoras a página de reportes. 15 issues creados (#196-#207, #209-#212) en 6 bloques Sprint 10 + 1 bloque Sprint 11. Detalle histórico en SPRINT-DONE-HISTORY.md.
- **Notas históricas de Sprints 2-9:** ver `SPRINT-DONE-HISTORY.md` (incluye decisiones DEC-018/020/021/022, contexto reshuffles, naming conventions, runbooks Cloudflare R2, Tailscale).

---

## Instrucción para Claude Code

Al iniciar sesión, lee este archivo y los epics relevantes para las US en cola.
Trabaja el backlog en orden sin parar entre US. Por cada US:
1. Implementa la US completa.
2. Haz commit con el mensaje indicado antes de tocar la siguiente.
3. Mueve la US de IN-PROGRESS a DONE con fecha de hoy.
4. Mueve la primera US de QUEUE a IN-PROGRESS.
5. Arranca la siguiente US de inmediato.

Continúa hasta que no queden US en QUEUE o el contexto se agote.
Si el contexto se agota a mitad de una US, haz commit del avance con prefijo `wip:` y anota aquí dónde quedó.
