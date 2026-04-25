# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
2026-04-25 — Sprint 7 v1.6 ✅ EJECUTADO EN BLOQUE.
Branch sesión actual: claude/review-and-triage-issues-EUsvX

Owner pidió "ejecuta TODO de golpe para hacer un solo PR" tras triage.
9 items entregados en commits limpios (1 por item) según regla
sagrada CLAUDE.md §7. ENH-035 (#158) queda diferido a v2.0
(post-MVP, marcado por el owner).

Items entregados (en orden de implementación):
  · ENH-037 #167 → c5798bf  feat(web) — botón Nuevo Programa en /pmo/orgs/[id]
  · BUG-035  #163 → 7766281  fix(api,web) — RAID comments con nombre del autor
  · BUG-033  #160 → 3ad5e9a  fix(api,web) — UI superadmin dropdown role inline
  · BUG-032  #159 → 2f86f38  fix(api,web) — SA /me email change con take-over
  · ENH-036  #162 → a48aa2b  feat(web) — RAID detail edit form
  · BUG-034  #161 → 49358e8  fix(api,web) — documents download via presigned URL
  · BUG-036  #166 → e441a07  fix(api,web,infra) — scheduled reports (beat embed + run-now)
  · US-083   #165 → c740a59  feat(api,web) — charter universal + descarga DOCX/PDF
  · US-082   #164 → 3533d21  feat(api,web) — tickets de permisos tenant→SA

Migraciones agregadas (auto-aplican al deploy via Dockerfile CMD):
- 0030 charter_for_legacy_projects (data — backfill rows vacías)
- 0031 permission_change_requests

Pendiente owner:
- Revisar PR (1 solo PR con todos los commits).
- En Railway: confirmar que el redeploy del worker aplica el cambio
  del worker.railway.toml (--beat embedded para BUG-036).
- BUG-032: probar el flow de take-over de email si hay clash al
  cambiar a daguilar1601@gmail.com.
- BUG-036: validar que el botón "Enviar ahora" dispara el correo
  end-to-end.

Naming convention nueva (próxima sesión):
- Per instrucción del owner 2026-04-25, las próximas branches
  seguirán el formato: sprint{N}-{ddmmyy}-{merge_order}-{code}
  (ej. sprint8-280426-1-cleanup).

--- contexto Sprint 7 triage ---
Triage 2026-04-25:
- 9 issues needs-rework analizados (#50, #78, #105, #111, #113, #125,
  #126, #127, #130).
- 9 cerrados como `completed` (scope original cumplido en cada uno;
  gaps reportados se separan en issues nuevos).
- 10 issues nuevos creados (Sprint 7):
  · #158 ENH-035 — Análisis profundo CI tests (post-MVP, v2.0).
  · #159 BUG-032 — SuperAdmin /me no permite cambiar email.
  · #160 BUG-033 — UI gestión users sin opción modificar rol.
  · #161 BUG-034 — Documents R2: link "Abrir" da 404 (presigned URL).
  · #162 ENH-036 — RAID página detalle sin opción editar.
  · #163 BUG-035 — RAID comments muestran user ID en vez de nombre.
  · #164 US-082 — Tenant admin: ticket cambio permisos → SuperAdmin.
  · #165 US-083 — Charter universal: migración legacy + descarga DOCX/PDF.
  · #166 BUG-036 — Reportes calendarizados no envían correo (Resend/beat).
  · #167 ENH-037 — /pmo/organizations/[id]: botón "Nuevo Programa".

Decisiones owner (vía AskUserQuestion 2026-04-25):
- PR #156 (Sprint 6) está mergeado y deployed → bugs de #125/#127/#113
  son reales, no cache stale.
- Charter legacy: migración data Alembic (no lazy on-demand).
- US-082: tabla + flujo nuevos, no se reutiliza Solicitudes EP005.
- ENH-036 alcance: solo página detalle dedicada (no preview panel).

Pendiente owner para arrancar Sprint 7:
- Revisar los 10 issues nuevos (#158-#167).
- Asignar `status:ready` a los que apruebe (mínimo recomendado:
  Bloque 0 hotfix → BUG-032 + BUG-033).
- Confirmar orden de bloques (default: 0 → 1 → 2 → 3 → 4 → 5).

--- contexto Sprint 6 cerrado ---
Sprint 6 v1.5 ✅ COMPLETO. Branch: claude/debug-admin-permissions-n3Yop
PR #156 mergeado a main (confirmado por owner 2026-04-25).

5/5 items entregados (US-076 a US-080). Suite 339 pass / 1 skip.

PRs / commits:
- US-076 (#151) → fabf8c3  feat(api) — capability model + migración 0028
- US-077 (#152) → fc93bb3  feat(web,api) — borra /admin/roles legacy
- US-079 (#154) → 2a0315a  test(api) — matriz role × endpoint
- US-078 (#153) → 1fc8ad8  feat(api,web) — UI users + exclusions + migración 0029
- US-080 (#155) → consolidación de docs

Migraciones aplican automáticamente al deploy (CMD del Dockerfile).
```

---

## 📥 INBOX / TRIAGE

> Issues recién creados que todavía no han sido asignados a un Bloque.
> El owner (o Claude por propuesta) decide a qué bloque entran antes de
> pasar a QUEUE. Ver `CLAUDE.md` §3 paso 4 y §6.

```
— Vacío — (los 10 issues nuevos del 2026-04-25 ya están en Bloques de Sprint 7)
```

---

## ⏳ QUEUE

**Sprint 7 (v1.6) — Reworks post-Sprint 6 + charter universal + tickets de permisos. 10 items en 6 bloques.**

> Triage completo 2026-04-25. Esperando `status:ready` del owner por
> issue (mínimo recomendado: Bloque 0 hotfix antes que el resto).

### Bloque 0 — Hotfix verificación post-Sprint 6 (2 items) ✅
- [x] BUG-032 — SuperAdmin /me email change con take-over — #159 ✅ 2f86f38
- [x] BUG-033 — UI superadmin dropdown role inline — #160 ✅ 3ad5e9a

### Bloque 1 — Charter universal + downloads (2 items) ✅
- [x] BUG-034 — Documents download via presigned URL R2 — #161 ✅ 49358e8
- [x] US-083 — Charter universal + descarga DOCX/PDF — #165 ✅ c740a59

### Bloque 2 — RAID polish (2 items) ✅
- [x] ENH-036 — RAID detail page edit form — #162 ✅ a48aa2b
- [x] BUG-035 — RAID comments con nombre del autor — #163 ✅ 7766281

### Bloque 3 — Reportes Resend funcional (1 item) ✅
- [x] BUG-036 — Scheduled reports beat + run-now — #166 ✅ e441a07

### Bloque 4 — Tenant ↔ SuperAdmin permission tickets (1 item) ✅
- [x] US-082 — Tickets de permisos con notif email — #164 ✅ 3533d21

### Bloque 5 — UX programas (1 item) ✅
- [x] ENH-037 — Botón Nuevo Programa /pmo/orgs/[id] — #167 ✅ c5798bf

### Follow-ups identificados (Sprint 8+)
- US-081 — Borrar físicamente tablas `roles` + `user_roles` (migración 0030+) tras validación de Sprint 6 en producción.
- ENH-035 — Análisis profundo optimización CI tests pesados (post-MVP / v2.0) — #158.
- ENH futuro — Filtrado efectivo de queries por `organization_user_exclusions`.

---

## 🗂️ Sprint 6 (v1.5) — CERRADO

**5 items en 5 bloques. PR #156 mergeado a main 2026-04-25.**

### Bloque 1 — Refactor backend del modelo de permisos (1 item) ✅
- [x] US-076 — Modelo capability-based + migración 0028 + barrido endpoints — #151 ✅ fabf8c3

### Bloque 2 — Eliminar UI/endpoints legacy de roles (1 item) ✅
- [x] US-077 — Borrar `/admin/roles/*`, `role-editor.tsx`, `admin_roles.py`, limpiar `admin.ts` — #152 ✅ fc93bb3

### Bloque 3 — UI nueva gestión users + capabilities + org membership (1 item) ✅
- [x] US-078 — `/admin/users/[id]` (10 acciones) + `/admin/permissions` + migración 0029 (exclusions) — #153 ✅ 1fc8ad8

### Bloque 4 — Tests de matriz role × endpoint (1 item) ✅
- [x] US-079 — `test_permission_matrix.py` con clasificación estática + fail-on-unknown — #154 ✅ 2a0315a

### Bloque 5 — Cierre: actualización de documentación (1 item) ✅
- [x] US-080 — Consolidar EP001, DECISIONS (anotaciones DEC-020/021), DB-CHANGES, CLAUDE.md §2, SPRINT.md — #155 ✅

---

## 🗂️ Sprint 5 (v1.4) — CERRADO

**10 items en 6 bloques + 1 follow-up. Todos mergeados a main.**

### Bloque 0 — Hotfix admin lockout (1 item) ✅ MERGEADO
- [x] BUG-031 — Admin lockout post-US-059/060 — #121 ✅ PR #129

### Bloque 0.5 — Infra CI (3 items) ✅ COMPLETO
- [x] ENH-030 — Acelerar suite de tests + CI (Fase 1/2/3) — #130 ✅ PR #131
- [x] ENH-032 + ENH-033 — Ruff cleanup + path filters + concurrency cancel — #133/#138 ✅ PR #139 (consolidados)
- [x] ENH-031 — Engine session-scoped + clean tables per test — #132 ✅ PR #141 (a5cfab1)

### Bloque 1 — SuperAdmin safety net (3 items) ✅ COMPLETO
- [x] US-072 — SuperAdmin: editar `role_type` de usuarios — #125 ✅ PR #134
- [x] US-073 — SuperAdmin: overrides permisos por tenant (DEC-021) — #126 ✅ PR #140 (migración 0027)
- [x] US-074 — SuperAdmin: cambiar email + password — #127 ✅ PR #134

### Bloque 2 — Import inteligente de planes (3 items) ✅ COMPLETO
- [x] US-069 — Import MPP nativo vía MPXJ (OpenJDK 21 + MPXJ 13.7.0) — #122 ✅ PR #143
- [x] US-070 — Wizard de mapeo de columnas Excel/CSV/MPP — #123
  - [x] Sub-bloque A: backend `/preview` + `/confirm` + Redis + CSV parser (PR #146)
  - [x] Sub-bloque B: frontend `import-wizard.tsx` + plan/page.tsx wired
- [x] US-071 — Plantilla vacía descargable del plan — #124 ✅ PR #135

### Bloque 3 — Refactor navegación TO-BE (1 item — mega-US completa) ✅
- [x] US-075 — Recursos de proyecto bajo `/pmo/*` (DEC-022) — #128
  - [x] Sub-bloque A: mover rutas + redirects 301 (33b0c7a)
  - [x] Sub-bloque C: sidebar OrgTreeNav + ADMIN_NAV gate (33b0c7a)
  - [x] Sub-bloque B: páginas informativas (`/pmo/programs/*` cards +
        KPIs en `/pmo/organizations/[id]`)

### Follow-ups detectados durante ejecución
- [x] ENH-034 — Diagnosticar bottleneck 38s en 9 tests (cierra CA2 <60s de ENH-031) — #142 ✅ fix-committed (causa: Celery .delay() esperaba broker Redis ausente)

---

## ✅ DONE

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo de Sprint 1 (v1.0 MVP, 94 items) y Sprint 2 (v1.1, 18 items).**

Sprint 2 v1.1 cerrado 2026-04-23. 4 bloques completos + hotfix Railway.

Sprint 3 v1.2 cerrado 2026-04-24 — 2 bloques:
- Bloque 1 (2 items): ENH-021 #96 + US-063 #95.
- Bloque 2 (3 items): BUG-027 #100 + ENH-022 #102 + ENH-023 #103.

---

## 📋 Backlog Sprint 2 (v1.1 — CERRADO)

### Bloque 1 — Sprint 2 Setup: navegación + bugs + permisos (7 items) ✅ COMPLETO
- [x] BUG-026 — Auth: timeout de inactividad a 15 minutos — #87 ✅ 77dc093
- [x] US-055 — Export tareas (CSV/Excel) — Opción A: botón descarga instantánea — #71 ✅ 023a99c
- [x] ENH-012 — Sidebar: reorganizar con módulo "Módulos de Proyecto" — #72 ✅ e2e420f
- [x] ENH-013 — Botón "Nuevo Programa" abre modal en Organizaciones — #73 ✅ b47f19a
- [x] BUG-023 — Project Charter: link a editor cuando no hay archivo (404) — #74 ✅ d81d036
- [x] BUG-024 — Lógica de uploads no configurada — #75 ✅ 3cd997d
- [x] BUG-025 — Rol "Reportes" sin módulo de permisos — #76 ✅ b1954c7

### Bloque 2 — Sprint 2 Reportes + Dashboard (5 items) ✅ COMPLETO
- [x] ENH-014 — Reportes: renombrar archivo con datetime + preview PDF — #77 ✅ 02cfaa6
- [x] US-056 — Calendarizar envío automático de reportes vía Resend — #78 ✅ 51947ef
- [x] ENH-015 — Dashboard: expandir barra de navegación — #80 ✅ 55956f9
- [x] ENH-017 — RAID: filtros en línea horizontal — #82 ✅ 6832199
- [x] ENH-016 — Solicitudes: permitir reabrir si proyecto no existe — #81 ✅ ade6ee7

### Bloque 3 — Sprint 2 RAID + Áreas (5 items) ✅ COMPLETO
- [x] ENH-019 — RAID: filtros avanzados (status + severidad/prioridad) — #85 ✅ fe3b001
- [x] ENH-018 — RAID: agregar toggle Kanban — #84 ✅ c894f12
- [x] US-058 — RAID: preview panel editable con comentarios (parcial — ver issue) — #83 ✅ e239caa
- [x] ENH-020 — Áreas: permitir múltiples recursos/contactos — #86 ✅ 009c0f2
- [x] US-062 — Áreas/Recursos: Area Leader + recursos asignados (moved from v1.2) — #91 ✅ 009c0f2

### Bloque 4 — Sprint 2 IA multi-modo (1 item) ✅ COMPLETO
- [x] US-057 — IA multi-modo por tenant: disabled / platform (Groq) / byo — #79 ✅ (9 commits, 8e4c385…be2a2ac; hotfix 40c4176)

---

## 📋 Backlog Sprint 3 (v1.2 — CERRADO)

### Bloque 1 — Sprint 3 Limpieza post-v1.1 + Auth self-service (2 items) ✅ COMPLETO
- [x] ENH-021 — Superadmin AI: quitar defaults editables de Ollama — #96 ✅ b70c887
- [x] US-063 — Recuperación y cambio de contraseña con envío por correo — #95 ✅ (6 commits, af4c9c3…7222dac)

### Bloque 2 — Sprint 3 Cleanup IA legacy post-DEC-017 (3 items) ✅ COMPLETO (pending merge)
- [x] BUG-027 — /admin/tenant config: retirar dropdown "Modo IA" + form Ollama Tailscale + endpoint backend + runbooks archivados + runbook BYO nuevo — #100 ✅ 1b62045
- [x] ENH-022 — Housekeeping docs/ai/ (4 archivos legacy a archive) + archivar EP016 + actualizar refs cruzadas — #102 ✅ 6315d19
- [x] ENH-023 — Retirar sidecar Tailscale del worker (start-worker.sh + Dockerfile custom + env vars TS_AUTHKEY/HOSTNAME + tailscale-setup.md archivado) — #103 ✅ f541171

---

## 📋 Backlog Sprint 4 (v1.3 — ACTIVO)

> Sprint arranca 2026-04-24 tras cerrar el review post-Sprint 2/3 con
> el owner. Scope: **reworks del review + infra + RAID robusto + import
> project/excel + página PMO de organización**. Los 3 items de v2.0
> (US-059/060/061) siguen diferidos por DEC-018.
>
> **Reshuffle 2026-04-24:** BUG-028 movido a Bloque 2 (depende de
> US-066 + BUG-029). #40 y #50 reintegrados. US-068 creada para sub-B
> de #50. Total 14 items.

### Bloque 1 — Reworks del review (8 items)
- [x] BUG-015 — Dashboard: botón "Exportar CSV" en 2 líneas (rework) — #40 ✅ d3523bb
- [x] BUG-029 — Upload de Excel falla + botón "Choose file" sin styling — #105 ✅ 3f6ac90
- [x] ENH-003 — Modal directo "Nuevo programa" en `/admin/organizations` y `/admin/programs` (sub-A) — #50 ✅ b47f19a (ya resuelto por ENH-013 Sprint 2; owner re-valida en deploy actual)
- [x] ENH-024 — Reporte: filename correcto al descargar — #106 ✅ 33c043c
- [x] ENH-025 — Filtros RAID siguen apilados (rework definitivo horizontales) — #107 ✅ ca9dc1d
- [x] ENH-026 — Consolidar "Panel de Gestión Avanzada" RAID en `/admin/raid` — #108 ✅ 8d69623
- [x] ENH-027 — Panel editable RAID (US-058) debe funcionar en `/admin/projects/[id]/raid` — #109 ✅ 3001959
- [x] ENH-028 — Export tareas: Excel MPP-like + naming PLAN-{Proyecto}-{Fecha} + CSV BOM UTF-8 — #110 ✅ f1db32a

### Bloque 2 — Infra + RAID robusto + charter + PMO (5 items) ✅ COMPLETO

- [x] US-066 — Uploads: object storage S3-compatible (Cloudflare R2) + runbook — #113 ✅ e0f9c2e (runbook ca5dd0c)
- [x] BUG-028 — Charter .docx real en bucket + editable desde documents — #104 ✅ 342e2b3
- [x] US-064 — RAID: área obligatoria + responsable + fechas + ordenamiento — #111 ✅ 798c89f
- [x] US-065 — RAID: página dedicada por ítem + historial — #112 ✅ 76277ac
- [x] US-068 — Página PMO de organización separada de admin — #116 ✅ 8f78d9b

### Bloque 3 — Import Project/Excel (1 item) ✅ COMPLETO
- [x] US-067 — Import XLSX → tareas (MPP follow-up documentado) — #114 ✅ e9ef28b

### Bloque 4 — Auth simplificada post-DEC-020 (2 items) ✅ COMPLETO
- [x] US-059 — Roles Admin/User/Viewer + backend gate — #88 ✅ 13eca87
- [x] US-060 — Hook useMyPermissions + gate UI — #89 ✅ 4fd19ca

---

## 📋 Backlog v2.0 (post-v1.3)

> **Contexto (DEC-020, 2026-04-24):** los 3 items originales de v2.0
> fueron recuperados o cancelados tras la decisión de no implementar
> aprobaciones jerárquicas. US-059 (#88) + US-060 (#89) bajaron a
> Sprint 4 v1.3 Bloque 4 con scope simplificado. US-061 (#90) está
> cancelada.

- [ ] (posibles items futuros: 2FA, SSO, magic-link login)

---

## Notas y cambios

- **2026-04-25 (Sprint 7 triage post-Sprint 6):** owner revisa los 9
  items con `status:needs-rework` y deja comments. Triage:
  - **9 cerrados como `completed`** (#50, #78, #105, #111, #113, #125,
    #126, #127, #130). Scope original cumplido en cada uno; los gaps
    se separan en issues nuevos.
  - **10 issues nuevos creados:** #158 ENH-035, #159 BUG-032, #160
    BUG-033, #161 BUG-034, #162 ENH-036, #163 BUG-035, #164 US-082,
    #165 US-083, #166 BUG-036, #167 ENH-037.
  - **Sprint 7 v1.6 organizado en 6 bloques** (Bloque 0 hotfix
    SuperAdmin → Bloque 1 charter+downloads → Bloque 2 RAID polish →
    Bloque 3 reportes Resend → Bloque 4 permission tickets → Bloque 5
    UX programas).
  - Decisiones owner (vía AskUserQuestion):
    1. PR #156 (Sprint 6) está mergeado y deployed → bugs reportados
       son reales, no cache stale.
    2. Charter legacy: **migración data Alembic** autogenera row vacía
       en `project_charters` para todo project sin charter (no lazy).
    3. US-082: **tabla + flujo nuevos** (`permission_change_requests`),
       no se reutiliza el módulo de Solicitudes (EP005).
    4. ENH-036: alcance solo página detalle dedicada (no preview panel).
  - Override CLAUDE.md: ENH-030 (#130) cerrado como `completed` aunque
    no llega a CA2 <60s — owner acepta el resultado actual ~3min para
    v1.x; análisis profundo se difiere a #158 (post-MVP / v2.0).
- **2026-04-24 (Sprint 5 sesión US-069):** entregada US-069 Import
  MPP nativo (commit `5ef2677`, branch `claude/sprint-pending-tasks-YhSdj`).
  Decisiones clave:
  - MPXJ 13.7.0 pinned en build-stage del Dockerfile (no hay
    `apps/worker/` separado — imagen compartida con api).
  - Wrapper Java propio (`MpxjCli.java`) en vez de CLI de terceros
    porque MPXJ no ships uno que emita el shape `ParsedTask`.
  - JRE 21 headless copiado desde `eclipse-temurin:21-jre-jammy`
    porque Debian Bookworm (base de python:3.12-slim) no trae
    openjdk-21 en repos default.
  - Tamaño incremental: ~225 MB (JRE 180 + MPXJ 45).
  - Tests mockean `subprocess.run` (sin fixture binario .mpp en repo).
  - Contrato `parse_mpp(data) -> XlsxParseResult` matchea el shape
    del parser XLSX — reutiliza `_TaskShim` del endpoint sin
    duplicar lógica de persistencia.
  Orden confirmado con owner para próximas sesiones: US-075 refactor
  `/pmo/*` → US-070 wizard (para que el wizard aterrice directo en
  `/pmo/projects/[id]/plan`).
- **2026-04-24 (Sprint 5 sesión ejecución):** entregados 7 items en
  ~8h (5 nuevos en sesión + BUG-031 + ENH-030 que venían). Branches
  recomendadas para mergear (orden por dependencia):
  1. PR #131 `claude/optimize-ci-tests-ac3u8` (ENH-030 — infra CI).
  2. `claude/sprint-5-cleanup-ruff` (ENH-032 — limpieza cosmética).
  3. `claude/sprint-5-superadmin-block` (US-072 + US-074).
  4. `claude/sprint-5-superadmin-overrides` (US-073 — incluye
     migración 0027 + cambio en `CurrentUser.has()`).
  5. `claude/sprint-5-import-block` (US-071 — plantilla vacía,
     independiente).
  Conflictos esperados: `apps/web/lib/api/superadmin.ts` se toca
  en branches 3 y 4 (anexos al final, fácil resolver). `SPRINT.md`
  se toca en varias branches (el último merge gana). `apps/api/app/
  api/v1/endpoints/superadmin.py` también — conflicto trivial
  porque cada branch agrega bloques distintos al final del archivo.
  Migraciones a aplicar en Railway: **0024, 0025, 0026, 0027**.
- **2026-04-24 (Sprint 5 kickoff):** owner reporta BUG crítico de
  admin lockout post-Sprint 4 (todas las rutas `/admin/*` devuelven
  "Falta permiso admin.X:read"). Diagnóstico: US-059 introdujo
  mapping estático sin prefijo `admin.*` pero los endpoints siguen
  exigiendo `"admin.users"`, `"admin.roles"`, etc. BUG-031 creado
  con `status:ready` directo (hotfix P0).
- **2026-04-24 (Sprint 5 triage):** owner aprobó 8 items para el
  sprint distribuidos en 4 bloques:
  - Bloque 0: BUG-031 hotfix (#121).
  - Bloque 1 SuperAdmin safety net: US-072 (#125), US-073 (#126),
    US-074 (#127). DEC-021 registrada (overrides permisos por tenant).
  - Bloque 2 Import inteligente: US-069 MPP (#122), US-070 wizard de
    mapeo (#123), US-071 plantilla vacía (#124).
  - Bloque 3 Refactor navegación: US-075 `/pmo/*` namespace (#128).
    DEC-022 registrada (namespaces `/pmo` negocio vs `/admin`
    sistema). Evaluación DEC-023 (`/{tenant_slug}` prefix) queda
    como follow-up ADR. ENH-029 absorbido por US-075.
- **2026-04-24 (reshuffle #2 — US-066 promovida):** owner reporta que
  los docs de Railway Volume (`SETUP.md` §4.1, `DEPLOYMENT.md` §4)
  están incorrectos — Railway no permite compartir volumes entre
  servicios. Sin storage persistente los uploads se pierden en cada
  redeploy, bloqueando el resto del testing. **US-066 (#113)
  promovida a prioridad inmediata** antes de seguir el Bloque 1.
  Nueva estrategia: **object storage S3-compatible (Cloudflare R2)**,
  cero egress fees + free tier 10 GB. Runbook completo entregado en
  `docs/runbooks/infra/uploads-storage.md` con 12 secciones
  (bucket + token + env vars + smoke + código + backup + rollback +
  troubleshooting). SETUP.md y DEPLOYMENT.md corregidos.
- **2026-04-24 (DEC-020 mid-Sprint 4):** owner redefine la plataforma
  como herramienta de apoyo/visualización — sin aprobaciones
  jerárquicas. Consecuencia: US-059 (#88) + US-060 (#89) bajan de v2.0
  al Bloque 4 del Sprint 4 v1.3 con scope reducido (3 roles fijos:
  Admin/User/Viewer + permisos estáticos por rol). US-061 (#90)
  cancelada. El permiso `reports` pendiente de BUG-025 se absorbe en
  US-060 como parte del rol `User`. Total Sprint 4: 16 items (8+5+1+2).
- **2026-04-24 (Sprint 4 reshuffle):** owner revisa el plan inicial
  y pide considerar #40, #50, #103 + mover BUG-028 al Bloque 2 por
  dependencia con US-066 + BUG-029 (charter real requiere storage
  persistente + upload funcional). Acciones:
  - BUG-015 #40 y ENH-003 #50 reintegrados al Bloque 1 con scope
    clarificado en comentarios.
  - BUG-028 #104 re-scoped a "generar PDF real del charter" + movido
    a Bloque 2 después de US-066.
  - Nueva US-068 #116 para sub-problema B de #50 (página PMO de
    organización separada de admin) en Bloque 2.
  - #103 identificado como pending-merge (no requiere issue nuevo;
    documentado en comentario).
  - US-060 (#89) y US-061 (#90) documentados con contexto DEC-018
    para que owner pueda cerrarlos con `not_planned`.
  - Introducido label `status:ready` en CLAUDE.md §5 como gate de
    arranque: Claude espera `status:ready` antes de tocar código.
  - Total Sprint 4: 14 items (8+5+1).
- **2026-04-24 (Sprint 4 kickoff):** owner revisa Sprint 2/3 y reporta
  7 items con `needs-rework` + pide RAID robusto (área obligatoria,
  fechas, página dedicada, ordenamiento) + import XLSX/MPP. Se crean
  11 issues (#104-#114) en 3 bloques. Scope completo confirmado por
  owner (ningún corte). Import MPP requiere Java 21 + MPXJ en worker
  (flag de riesgo dentro del issue US-067).
- **2026-04-23 (post-v1.1):** owner define scope de Sprint 3 v1.2:
  solo limpieza Ollama + password reset (ENH-021 + US-063). Los 3
  items originales de v1.2 (#88/#89/#90) pasan a v2.0 por ser un
  major overhaul de Auth/Roles/Aprobaciones. Ver **DEC-018**.
- **2026-04-22 (Sprint 2 intake):** 21 issues clasificados en 4
  bloques v1.1 + 3 items v1.2 (luego reclasificados a v2.0 el
  2026-04-23).

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
