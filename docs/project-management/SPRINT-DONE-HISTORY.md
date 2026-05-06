# SPRINT-DONE-HISTORY.md — Histórico de bloques completados (Sprint 1 v1.0 MVP)

> **Propósito:** Archivo de referencia histórica. Los bloques completados se mueven aquí desde SPRINT.md cuando se cierra un sprint. Permite que SPRINT.md mantenga solo lo pendiente para el sprint activo.

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
