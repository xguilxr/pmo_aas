# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
US-051 — Mover generación IA (minuta + reporte) a Celery worker con polling
  Epic: EP016 (follow-up de US-048)
  Branch: claude/fix-tailscale-command-0VPWN (reusa la branch activa)
  Issue: #28

**Contexto (2026-04-21):** al completar la instalación manual de
Tailscale + Ollama y probar el flujo de minutas en prod, el endpoint
`POST /ai/minutes` devolvió `[AI disabled — mock]`. Análisis descubrió
que (1) AI_MODE estaba en disabled, y (2) aunque se cambie a ollama,
el endpoint corre sincrónicamente en el servicio `api` que NO tiene
tailscaled → nunca alcanza Ollama. El diseño EP016/US-048 implicaba
que el worker (con Tailscale) procesara la AI, pero ese dispatch
nunca se implementó (celery_app.py:29 tiene include=[]).

Esta US cierra ese gap: dispatch a Celery, polling en frontend.
```

---

## 📥 INBOX / TRIAGE

> Issues recién creados que todavía no han sido asignados a un Bloque.
> El owner (o Claude por propuesta) decide a qué bloque entran antes de
> pasar a QUEUE. Ver `CLAUDE.md` §3 paso 4 y §6.

```
— Vacío —
```

---

## ⏳ QUEUE (próximas 5)

| # | US | Epic | Título | Tipo |
|---|---|---|---|---|
| 1 | US-027 | EP011 | Tabla notifications + in-app center | Bloque 16 (POST-MVP) |
| 2 | US-028 | EP011 | Email notifications via Resend | Bloque 16 (POST-MVP) |
| — | — | — | — | — |
| — | — | — | — | — |
| — | — | — | — | — |

> Nada queda en cola para v1.0 / pruebas masivas. Las dos filas con US
> son POST-MVP y no bloquean el release.

---

## ✅ DONE (historial reciente)

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

---

## 📋 Backlog ordenado por prioridad

### Bloque 1 — Jerarquía org (EP002) — BLOQUEANTE para todo lo demás
- [x] US-002 — Migración BD: tablas BU + Depto + FKs ✅
- [x] US-003 — CRUD Business Units (API) ✅
- [x] US-004 — CRUD Departments (API) ✅
- [x] US-005 — Sidebar org nav (Frontend) ✅
- [x] US-006 — Vista paneles de organizaciones (Frontend) ✅
- [x] BUG-001 — Fix 404 en Programas ✅

### Bloque 2 — Topbar y UX base (EP001)
- [x] US-007 — Toggle dark/light en dropdown usuario ✅
- [x] US-008 — Toggle idioma en dropdown usuario ✅
- [x] US-009 — Página administrar cuenta (perfil + cambiar password) ✅
- [x] US-010 — Color chrome #182e4e + Senior PMO = admin ✅

### Bloque 3 — Project Charter (EP003)
- [x] US-011 — Campos adicionales en solicitud (correos, personas clave, etc.) ✅
- [x] US-012 — Project Charter: tabla + generación al aprobar ✅
- [x] US-013 — Charter aparece como documento en el proyecto ✅

### Bloque 4 — Dashboard fixes (EP004)
- [x] BUG-002 — Fix distorsión gráficas de barra ✅
- [x] US-014 — Filtro organización en dashboard ✅
- [x] US-015 — KPIs respetan jerarquía de roles ✅
- [x] BUG-003 — Fix layout Plan vs Real (filtros horizontales + columna PM) ✅

### Bloque 5 — Proyecto detalle (EP005)
- [x] US-016 — Unificar Plan + Gantt en una pestaña ✅
- [~] US-017 — Tabs inline para módulos del proyecto → **SUPERSEDED** por US-035 (EP013, bloque 9)
- [x] US-018 — Módulo Área/Organigrama del proyecto ✅

### Bloque 6 — RAID y módulos (EP006)
- [x] US-019 — Consolidar RAID (Riesgos+Acciones+Incidentes+Decisiones) ✅
- [x] US-020 — Categorías de documentos actualizadas ✅
- [x] US-021 — Consolidar pestañas de Minutas en 1 ✅
- [x] US-022 — Módulo Reportes dentro del proyecto ✅

### Bloque 7 — Admin (EP007)
- [x] US-023 — Gestión de tenant (propuesta de acciones) ✅
- [x] US-024 — Gestión jerarquía org completa (BU + Depto) ✅

### Bloque 8 — SuperAdmin (EP010)
- [x] US-025 — Iconos en paneles de tenant ✅
- [x] US-026 — Visión General = Tenants + Health unidos ✅

---

### Bloque 9 — Refactor de navegación (EP013) — issue #17
**Orden de ejecución** (1 US por commit, en este orden):
- [x] US-031 — Upload y display del logo del tenant en chrome ✅
- [x] US-032 — Restructurar sidebar principal (drill-down real; quitar "Módulos de proyecto" y duplicado de Organizaciones) ✅
- [x] US-033 — Panel de organización → página de recursos reales (fix bug + enhancement) ✅
- [x] US-034 — Página resumen de programa (KPIs + lista de proyectos) ✅
- [x] US-035 — Tabs inline en detalle de proyecto (supersede US-017) ✅
- [x] US-036 — Restructurar sidebar Admin (fusionar Mi Tenant + Panel + Configuración; 4 ítems raíz) ✅

### Bloque 10 — Entregables operativos (EP014) — issue #18
- [x] US-037 — Infra compartida de exportación a PDF (WeasyPrint) ✅
- [x] US-038 — Reporte de Avance de Proyecto (Python, BD, PDF) ✅
- [x] US-039 — Reporte de Seguimiento de Actividades (Python, BD, PDF) ✅
- [x] US-040 — Formato estandarizado + export (.docx/.md/.txt/.pdf) de Minuta IA ✅

### Bloque 11 — Refactor nav super admin (EP015) — issue #19
- [x] US-041 — Sidebar super admin aislado (4 ítems raíz) ✅
- [x] US-042 — Página `/superadmin/users` cross-tenant (lista + edición) ✅
- [x] US-043 — Visión General con Health al top ✅

### Bloque 12 — Modelo IA local (EP016) — Ollama + Cloudflare Tunnel + nssm
- [x] US-044 — Runbook `docs/ai/local-ollama-setup.md` paso a paso ✅
- [x] US-045 — Config por-tenant + smoke test del túnel + secrets cifrados ✅
  *(follow-up: integrar config en `OllamaProvider.generate()` del worker EP008 para que `ai_cascade_fallback_total` incremente cuando el túnel falle)*

### Bloque 13 — Hotfixes operativos (reabre tras PR #20) ✅ CERRADO 2026-04-21

> **Contexto (2026-04-21):** el PR #20 mergeó a `main` con 6 US (NEW-041
> hasta NEW-045). El owner reportó dos síntomas que no se detectaron en CI:
> (a) Railway no redeployó los servicios al mergear; (b) el sidebar super
> admin no se ve como esperaba (probable state stale en `getStoredUser()`).
>
> Resolución: BUG-004 dejó documentado el troubleshooting en
> `RAILWAY_SETUP.md` (el toggle operativo lo aplica el owner del
> project). BUG-005 movió la lectura de `getStoredUser()` a
> `useEffect` con flag `userReady`, evitando el flash de TOP_NAV en
> primer paint para superadmins.

- [x] **BUG-004 — Railway no redeploy tras PR #20** ✅
  - **Diagnóstico inicial** (agente 2026-04-21): el commit `62b16f8`
    (US-045) SÍ toca `apps/api/**`, así que los servicios `api` +
    `worker` deberían haber redeployado per watch path.
  - **Hipótesis ordenadas**:
    1. (80%) Railway auto-deploy apagado, o rama conectada ≠ `main`.
    2. (15%) Watch path del servicio mal configurado (ver si incluye `apps/api/**`).
    3. (5%) Railway sincronizó tarde y no se verificó.
  - **Acción (1 sesión)**:
    1. Login Railway UI → project `pmo-aas` → cada servicio `api`/`worker`/`web`:
       - Settings → **Branch** debe ser `main`.
       - Settings → **Watch Paths** match con RAILWAY_SETUP.md §3.
       - Settings → **Auto-Deploy** toggle ON.
    2. Trigger manual: **Deployments → Deploy** (o push commit vacío).
    3. Verificar logs del deploy: seed idempotente, migrations al día, health endpoints verdes.
    4. Documentar hallazgo en `RAILWAY_SETUP.md` → sección "Troubleshooting" con el caso.
  - **Commit:** `fix(infra): BUG-004 — Railway auto-deploy restablecido tras PR #20`.

- [x] **BUG-005 — Sidebar super admin no renderiza como esperado** ✅
  - **Diagnóstico inicial** (agente 2026-04-21): US-041
    (`918be73`) modificó `apps/web/components/app-shell.tsx` para:
    - Renderizar `TOP_NAV` solo cuando `!user?.is_superadmin`.
    - Apuntar BrandMark a `/superadmin` si el user es superadmin.
    - Agregar ítem "Usuarios" a `SUPERADMIN_NAV`.
  - **Hipótesis**: `getStoredUser()` en `apps/web/lib/auth-storage.ts`
    devuelve `null` o user stale durante SSR o en la primera hidratación
    cliente. Si `user?.is_superadmin` es `undefined` en primer render, el
    sidebar muestra TOP_NAV incorrectamente y solo se arregla tras un
    refresh.
  - **Acción (1 sesión)**:
    1. Login como super admin en deploy `main` actual; capturar DOM en
       first paint vs hydrated.
    2. Revisar `apps/web/lib/auth-storage.ts` — `getStoredUser()` ¿lee
       localStorage de forma síncrona? ¿Manda fallback durante SSR?
    3. Si es race, envolver el componente de navegación en `useEffect` +
       `useState` con loading skeleton; **o** leer user desde un
       `UserProvider` que ya existe (verificar).
    4. Agregar test Playwright (`apps/web/e2e/superadmin-sidebar.spec.ts`):
       login como superadmin → verificar que Tablero/Solicitudes NO aparecen
       y que Usuarios SÍ aparece.
  - **Commit:** `fix(web): BUG-005 — sidebar super admin respeta user.is_superadmin en first paint`.

### Bloque 14 — EP016 v2: Ollama local vía Tailscale (reabre EP016) ✅ CERRADO 2026-04-21

> Reemplazó el canal CF Tunnel + Cloudflare Access por Tailscale tailnet
> privado. Ver ADR-015 + DEC-011. US-044/045 quedan SUPERSEDED.

- [x] US-046 — Runbook `docs/ai/local-ollama-setup.md` reescrito para Tailscale ✅
- [x] US-047 — `OllamaLocalAiForm` + endpoint `test-connection` sin CF-Access ✅
- [x] US-048 — Dockerfile worker Railway con sidecar `tailscaled` + `TS_AUTHKEY`; OllamaProvider consume config por-tenant ✅
- [ ] **Cleanup paralelo (owner, manual)**: borrar tunnel `pmoaas-ollama` de Cloudflare, retirar CNAME `ollama.*`, revocar Service Tokens. Documentado en `docs/ai/local-ollama-setup.md` §10 "Rollback CF Tunnel".

### Bloque 15 — Landing y DNS productivo (Cloudflare + Railway + HostGator) ✅ CERRADO 2026-04-21

> Finaliza el routing del dominio `pmo-aas.com`. Ver DEC-012 y runbook
> `docs/infra/dns-routing.md`.

- [x] **US-049 — Configurar DNS productivo en Cloudflare** ✅
  - Runbook `docs/infra/dns-routing.md` con plan completo: apex 301,
    CNAME `app.*`/`api.*` DNS only, CNAME `www` Proxied + Full strict,
    cleanup de `ollama.*`, verificación con dig/curl y rollback.
  - **Pendiente operador (owner):** aplicar los registros en el
    dashboard Cloudflare y agregar Custom Domain a cada servicio
    Railway.

- [x] **US-050 — Landing estático en HostGator** ✅
  - Directorio `landing/` con `index.html`, `assets/styles.css` y
    `assets/favicon.svg`. HTML/CSS vanilla alineado al chrome
    `#182e4e`; sin JS framework ni llamadas al API.
  - `landing/README.md` documenta el deploy a cPanel (File Manager o
    FTP) y el smoke test post-deploy.
  - **Pendiente operador (owner):** subir el contenido de `landing/`
    a `public_html/` en HostGator.

### Bloque 16 — Notificaciones (EP011) — POST-MVP
- [ ] US-027 — Tabla notifications + in-app center
- [ ] US-028 — Email notifications via Resend

### Bloque 18 — Hotfixes runbook EP016 (durante pruebas manuales del owner)

> Bugs y ajustes al runbook `docs/ai/local-ollama-setup.md` detectados
> cuando el owner ejecuta el procedimiento en PC real. Se abren como
> hotfix siguiendo el patrón del Bloque 13. No bloquean v1.0; aumentan
> la calidad del runbook para la próxima instalación.

- [x] BUG-006 — §3.2 advierte que PowerShell no refresca PATH tras instalar Tailscale MSI + row de troubleshooting en §9 ✅

### Bloque 19 — Refactor IA a Celery (prioridad, cierra gap EP016)

> Gap arquitectónico descubierto al probar minutas en prod: el endpoint
> `POST /ai/minutes` corre en `api` (sin Tailscale) en vez de dispatchar
> a `worker` (con Tailscale). El DoD del EP016 lo tenía listado como
> follow-up pendiente. Sin este refactor, Ollama local NUNCA se usa en
> producción — la cascada cae directo a Gemini/Claude.

- [ ] **US-051 — Mover generación IA (minuta + reporte) a Celery worker** — issue #28
  - Backend: tasks Celery + endpoints devuelven 202 con job_id.
  - Frontend: hook de polling con backoff + actualización de `NewAIMinutePage`.
  - Docs: DoD EP016 + deployment-railway.
  - Tests: unit + integration (Celery eager).
  - Estimado: 1 sesión grande (11-14 archivos).

### Bloque 17 — Instalación productivo HostGator MySQL (EP012) — ❌ CANCELADO

> **CANCELADO (2026-04-21, ver DEC-013).** El owner subió el tier de
> Railway y productivo v1.0/v1.x corre íntegramente en Railway Postgres.
> El costo incremental se cubre con licencias cobradas. No hay plan
> futuro de migrar a MySQL; EP012 se conserva solo como referencia
> histórica.

- [x] ~~US-029~~ — ❌ CANCELADA (DEC-013)
- [x] ~~US-030~~ — ❌ CANCELADA (DEC-013)

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
