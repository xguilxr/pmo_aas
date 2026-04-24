# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
2026-04-24 — Sprint 5 en curso. Branch: claude/sprint-pending-tasks-YhSdj

US-075 (#128) Refactor navegación /pmo/* — sub-bloques A+C
fix-committed (33b0c7a). Sub-bloque B (páginas informativas
con KPIs) pendiente próxima sesión.

PRs mergeados a main:
- BUG-031 (#121)  PR #129
- ENH-030 (#130)  PR #131
- US-072  (#125)  PR #134
- US-074  (#127)  PR #134
- US-071  (#124)  PR #135
- ENH-032 (#133)  PR #139 (consolidado con ENH-033)
- ENH-033 (#138)  PR #139
- US-073  (#126)  PR #140 (+ fixes CI dual runs + permissions)
- ENH-031 (#132)  PR #141 (a5cfab1 — session engine + clean tables)
- Docs Sprint 5   PR #137 (b6fc650)
- US-069  (#122)  PR #143 (5ef2677 + cleanup ruff + alembic doc)

Branch activa pendiente de PR:
- US-075 (#128) sub-bloques A+C — commit 33b0c7a en
  claude/sprint-pending-tasks-YhSdj. Esperando review + merge.

Pendientes siguientes sesiones:
- US-075 (#128) sub-bloque B — páginas informativas /pmo/programs/*
  y /pmo/organizations/[id] con KPIs (~1-2 días).
- US-070 (#123) Wizard de mapeo de columnas — tras cerrar US-075
  (mega 4-6 días).
- ENH-034 (#142) Diagnosticar bottleneck 38s en 9 tests
  (status:triage — pendiente label ready del owner).

Pendiente owner:
- Revisar PR de US-075. Cambios: 28 page.tsx renombrados (preserva
  historial git), 137 refs sustituidas en 40 archivos, 11 redirects
  301 nuevos, scope de ADMIN_NAV ahora correcto (solo role_type=admin).
- En el primer deploy: cache de Next.js se invalida por las rutas
  nuevas. Verificar que un user con role_type=user (no admin) ya
  NO ve el menú "Admin" (este PR cierra un bug de scope no reportado).

Nota: las migraciones Alembic son automáticas al mergear (CMD del
Dockerfile corre `alembic upgrade head` antes de uvicorn). No hay
acción manual con la DB.
```

---

## 📥 INBOX / TRIAGE

> Issues recién creados que todavía no han sido asignados a un Bloque.
> El owner (o Claude por propuesta) decide a qué bloque entran antes de
> pasar a QUEUE. Ver `CLAUDE.md` §3 paso 4 y §6.

```
— Vacío — (todos los nuevos issues ya en Bloques del Sprint 5)
```

---

## ⏳ QUEUE

**Sprint 5 (v1.4) — 10 items en 6 bloques + 1 follow-up. 9/10 mergeados a main, US-069 fix-committed (PR pendiente).**

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

### Bloque 2 — Import inteligente de planes (3 items) — 2/3 fix-committed
- [x] US-069 — Import MPP nativo vía MPXJ (OpenJDK 21 + MPXJ 13.7.0) — #122 ✅ 5ef2677 (fix-committed, esperando PR/merge)
- [ ] US-070 — Wizard de mapeo de columnas Excel/CSV/MPP — #123 `status:ready` (mega 4-6 días, arranca tras US-075)
- [x] US-071 — Plantilla vacía descargable del plan — #124 ✅ PR #135

### Bloque 3 — Refactor navegación TO-BE (1 item — mega-US, partido en sub-bloques)
- [~] US-075 — Recursos de proyecto bajo `/pmo/*` (DEC-022) — #128
  - [x] Sub-bloque A: mover rutas + redirects 301 (33b0c7a)
  - [x] Sub-bloque C: sidebar OrgTreeNav + ADMIN_NAV gate (33b0c7a)
  - [ ] Sub-bloque B: páginas informativas con KPIs (próxima sesión)

### Follow-ups detectados durante ejecución
- [ ] ENH-034 — Diagnosticar bottleneck 38s en 9 tests (cierra CA2 <60s de ENH-031) — #142 `status:triage`

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
