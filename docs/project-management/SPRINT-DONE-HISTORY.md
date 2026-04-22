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

**Última actualización:** 2026-04-22 (intake Sprint 2)
