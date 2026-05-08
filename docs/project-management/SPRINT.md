# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.
>
> **Histórico:** Sprints 1-10 cerrados → ver `SPRINT-DONE-HISTORY.md`.

---

## 🔴 IN-PROGRESS

```
Sprint 18 (v1.17) — Bloque 1 ENTREGADO 2026-05-08 (3 issues — pendiente verif. owner):
  US-106 + ENH-081 + ENH-080. Migraciones 0055 + 0056 agregadas.
  Branch sesión: claude/review-start-next-sprint-R8JWc

Sprint 17 (v1.16) — Bloque 0 MERGED 2026-05-08 (PR #297, BUG-053).
Sprint 17 (v1.16) — Bloque 0.5 IN-PROGRESS 2026-05-08:
  US-104 #298 — módulo BYO: test-before-save + custom provider + retry
  Branch sesión: claude/setup-ai-module-8HYs1

Sprint 17 Bloque 1 (chat global #255-258) → POSTERGADO (ver sección Deferred).

Sprints 19-23 PLANEADOS 2026-05-08 (status:triage):
  Sprint 19 (v1.18) — RAID polish + vistas dedicadas (6 issues, 1 migración)
  Sprint 20 (v1.19) — IA Minutas (5 issues)
  Sprint 21 (v1.20) — Reportes redesign HTML (4 issues, 1 migración)
  Sprint 22 (v1.21) — Cambios approval workflow (2 issues, 2 migraciones)
  Sprint 23 (v1.22) — BYO universal + Copilot M365 (1 issue)
  Branch sesión actual: claude/plan-hierarchy-restructure-sdQOm

Sprints 12-15 — Bloques entregados, pendiente verificación owner.

Próximo libre: US-114, BUG-056, ENH-092.
```

---

## 📥 INBOX / TRIAGE

> Issues creados con status:triage. Owner pasa a status:ready para arrancar.

```
(vacío — todos los issues nuevos están organizados en bloques de Sprint 13-16, ver abajo.)
```

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

## ⏳ Sprint 19 (v1.18) — RAID polish + vistas dedicadas (PLANEADO 2026-05-08)
Branch reservada: `claude/sprint-19-raid-polish`

### Bloque 1 (6 issues — orden recomendado)
- [ ] ENH-082 #312 — Export RAID Excel "bonito" 4 sheets dedicados con todas las propiedades
- [ ] US-107 #313 — Riesgo: entidad "Acción de mitigación" linked (multi-responsable, status, fecha)
- [ ] ENH-083 #314 — Riesgo: render mitigación + lista Acciones inline en ticket
- [ ] ENH-088 #315 — Preview "tarjeta flotante" sobre página actual (reemplaza side panel) — RAID/Lecciones/Cambios
- [ ] ENH-086 #316 — Lecciones: página dedicada in-platform (extiende RAID Denso)
- [ ] ENH-087 #317 — Cambios: página dedicada in-platform (extiende RAID Denso)

**Migración Alembic prevista:** 1 — `risk_actions` + `risk_action_assignees`.

---

## ⏳ Sprint 20 (v1.19) — IA Minutas (PLANEADO 2026-05-08)
Branch reservada: `claude/sprint-20-ia-minutas`

### Bloque 1 (5 issues)
- [ ] ENH-084 #318 — IA Minutas: 4 secciones RAID estandarizadas independiente del modelo (post-procesado JSON-schema)
- [ ] US-108 #319 — IA Minutas → sugerir RAIDs aprobables por PM (PM revisa/edita/aprueba/crea)
- [ ] BUG-055 #320 — Generación minuta: botón Cancelar/Volver (UI faltante)
- [ ] ENH-090 #321 — Preview Minuta in-platform (HTML viewer embebido)
- [ ] ENH-091 #322 — Botón Borrar minuta

**Sin migraciones previstas.**

---

## ⏳ Sprint 21 (v1.20) — Reportes redesign HTML (PLANEADO 2026-05-08)
Branch reservada: `claude/sprint-21-reportes-html`

### Bloque 1 (4 issues — orden recomendado)
- [ ] US-111 #324 — Render HTML interactivo con filtros + KPIs (ref `docs/archive/Reporte de Seguimiento.html`) — base que consumen los demás
- [ ] US-109 #323 — Panel creación 2 modos (Nuevo / Plantilla) + render HTML inicial + tweaker IA edita HTML
- [ ] ENH-085 #325 — Guardar como Reporte / Guardar como Plantilla (catálogo tenant)
- [ ] ENH-089 #326 — Export Reportes/Minutas: HTML primario + adecuaciones PDF/TXT

**Migración Alembic prevista:** 1 — `report_templates`.

---

## ⏳ Sprint 22 (v1.21) — Cambios / Approval workflow (PLANEADO 2026-05-08)
Branch reservada: `claude/sprint-22-cambios-approval`

### Bloque 1 (2 issues)
- [ ] US-112 #327 — Cambios: registrar responsables de aprobación (multi-actor)
- [ ] US-113 #328 — Workflow email: token JWT firmado + landing pública aprobar/rechazar + re-trigger en rechazo

**Migraciones Alembic previstas:** 2 — `change_approvers`, `approval_tokens`.

**Epic:** EP019 (Cambios / Approval workflow) — nuevo, ver `docs/epics/EP019-changes-approval.md`.

---

## ⏳ Sprint 23 (v1.22) — BYO universal + Copilot M365 (PLANEADO 2026-05-08)
Branch reservada: `claude/sprint-23-byo-universal`

### Bloque 1 (1 issue)
- [ ] US-110 #329 — BYO universal (cualquier API válida vía OpenAI-compatible) + soporte Microsoft Copilot M365 vía Azure OpenAI

**Sin migraciones previstas.**

---

**Próximo libre:** US-114, BUG-056, ENH-092.

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
