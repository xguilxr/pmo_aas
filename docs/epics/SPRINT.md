# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
— Sin US activa —

**Estado al 2026-04-21 (owner):** productivo v1.0 corre en Railway con
tier superior; el costo marginal se cubre con licencias cobradas.
EP012 (migración a MySQL HostGator) CANCELADO por DEC-013. DEC-002 y
la parte "reabrir a v1.1" de DEC-012 quedan revocadas.

Bloque 13 (hotfixes operativos) cerrado el 2026-04-21:
- US-BUG-004 documentó el troubleshooting de redeploy en Railway.
- US-BUG-005 arregla el flash de TOP_NAV en primer paint del sidebar
  super admin.

Bloque 14 (EP016 v2 — Ollama local vía Tailscale) cerrado el
2026-04-21:
- US-NEW-046 reescribe docs/ai/local-ollama-setup.md para flujo
  Tailscale (Windows + MagicDNS + firewall por 100.64.0.0/10 +
  TS_AUTHKEY reusable/ephemeral con tag:railway-worker + cleanup del
  CF Tunnel previo).
- US-NEW-047 elimina los campos CF-Access del formulario
  OllamaLocalAiForm, del endpoint POST /api/v1/admin/ai/test-connection
  y del script ai_local_smoke.py. Schema reducido a {base_url, model,
  timeout_sec}. AI_SECRETS_FERNET_KEY queda DEPRECATED. Legacy
  secrets archivados en settings.ai.ollama.auth_legacy.*. Tests
  renombrados a test_usnew047_* con @pytest.mark.legacy para los de
  Fernet.
- US-NEW-048 agrega Dockerfile común api+worker con tailscaled,
  wrapper start-worker.sh (user-space networking → celery) y cierra
  el follow-up de EP016: OllamaProvider.generate consume
  {base_url, model, timeout_sec} del tenant; generate_with_cascade
  emite log estructurado ai_cascade_fallback con tags from/to para
  derivar la métrica Prometheus en el futuro.

Bloques 11 y 12 originales siguen cerrados; US-NEW-044/045 quedan
SUPERSEDED por el Bloque 14.

**Ruta directa a pruebas masivas (pendiente):**
  Bloque 15 — DNS productivo + landing (US-NEW-049/050)

Después de pruebas masivas (POST-MVP, no bloquean v1.0):
  Bloque 16 — EP011 Notificaciones in-app + email

Bloque 17 (EP012 MySQL HostGator): ❌ CANCELADO por DEC-013.

Follow-ups arrastrados:
- Harness Playwright no instalado: el test e2e superadmin-sidebar
  quedó fuera de US-BUG-005; reabrir cuando se introduzca el framework.
- Cleanup manual de CF Tunnel (tunnel pmoaas-ollama, CNAME ollama.*,
  Service Tokens): documentado en docs/ai/local-ollama-setup.md
  §10 "Rollback de CF Tunnel"; ejecuta el owner.
- Exportador Prometheus: el log estructurado ai_cascade_fallback
  está listo, falta el exporter que lo convierta en métrica
  `ai_cascade_fallback_total{from,to}`.
```

---

## ⏳ QUEUE (próximas 5)

| # | US | Epic | Título | Tipo |
|---|---|---|---|---|
| 1 | US-NEW-049 | infra | DNS productivo pmo-aas.com (Cloudflare + Railway + HostGator) | Bloque 15 |
| 2 | US-NEW-050 | infra | Landing estático www.pmo-aas.com en HostGator | Bloque 15 |
| 3 | US-NEW-027 | EP011 | Tabla notifications + in-app center | Bloque 16 (POST-MVP) |
| 4 | US-NEW-028 | EP011 | Email notifications via Resend | Bloque 16 (POST-MVP) |
| — | — | — | — | — |

> Backlog completo abajo, reordenado.

---

## ✅ DONE (historial reciente)

| US | Título | Commit | Fecha |
|---|---|---|---|
| US-NEW-001 | Setup inicial — análisis de gaps v1→v2 | `docs: gap analysis v2` | 2026-04-20 |
| US-NEW-002 | Tablas business_units + departments + FKs | `feat(org): US-NEW-002 — tablas BU y departments con FK` | 2026-04-20 |
| US-NEW-003 | CRUD Business Units API | `feat(org): US-NEW-003 — CRUD Business Units API` | 2026-04-20 |
| US-NEW-004 | CRUD Departments API | `feat(org): US-NEW-004 — CRUD Departments API` | 2026-04-20 |
| US-NEW-005 | Sidebar org tree nav (Frontend) | `feat(web): US-NEW-005 — sidebar org tree nav` | 2026-04-20 |
| US-NEW-006 | Vista paneles de organizaciones (cards + métricas) | `feat(web): US-NEW-006 — paneles de organizaciones` | 2026-04-20 |
| US-BUG-001 | Fix 404 en página de Programas | `fix(web): US-BUG-001 — crea /admin/programs` | 2026-04-20 |
| US-NEW-007 | Toggle dark/light mode en dropdown usuario | `feat(web): US-NEW-007 — toggle dark/light en user dropdown` | 2026-04-20 |
| US-NEW-008 | Toggle de idioma (ES/EN) en dropdown usuario | `feat(web): US-NEW-008 — toggle idioma en user dropdown` | 2026-04-20 |
| US-NEW-010 | Color chrome #182e4e + Senior PMO como admin | `feat(auth): US-NEW-010 — chrome #182e4e + Senior PMO admin` | 2026-04-20 |
| US-NEW-009 | Página /account (perfil + cambiar password) | `feat(web): US-NEW-009 — página /account perfil + password` | 2026-04-20 |
| US-NEW-011 | Campos adicionales en solicitud + FK BU/Depto | `feat(requests): US-NEW-011 — campos adicionales en solicitud` | 2026-04-20 |
| US-NEW-012 | Project Charter: tabla + generación al aprobar | `feat(requests): US-NEW-012 — project_charters + auto-gen` | 2026-04-20 |
| US-NEW-013 | Charter aparece como documento del proyecto | `feat(requests): US-NEW-013 — charter como documento` | 2026-04-20 |
| US-NEW-014 | Filtro de organización en dashboard | `feat(dashboard): US-NEW-014 — filtro organización` | 2026-04-20 |
| US-BUG-002 | Fix distorsión en gráficas de barra | `fix(dashboard): US-BUG-002 — distorsión gráficas barra` | 2026-04-20 |
| US-NEW-015 | KPIs respetan jerarquía de roles | `feat(dashboard): US-NEW-015 — KPIs respetan jerarquía roles` | 2026-04-20 |
| US-BUG-003 | Fix layout Plan vs Real + columna PM | `fix(dashboard): US-BUG-003 — layout Plan vs Real` | 2026-04-20 |
| US-NEW-016 | Unificar Plan + Gantt en una pestaña | `feat(projects): US-NEW-016 — unificar plan + gantt` | 2026-04-20 |
| US-NEW-018 | Módulo Áreas/Organigrama del proyecto | `feat(projects): US-NEW-018 — módulo áreas del proyecto` | 2026-04-20 |
| US-NEW-019 | Consolidar RAID (vista unificada) | `feat(projects): US-NEW-019 — consolidar RAID` | 2026-04-20 |
| US-NEW-020 | Categorías de documentos actualizadas | `feat(projects): US-NEW-020 — categorías de documentos` | 2026-04-20 |
| US-NEW-021 | Consolidar pestañas de Minutas | `feat(projects): US-NEW-021 — consolidar minutas` | 2026-04-20 |
| US-NEW-022 | Módulo Reportes dentro del proyecto | `feat(projects): US-NEW-022 — módulo reportes` | 2026-04-20 |
| US-NEW-023 | Gestión de Tenant (info + stats + editar) | `feat(admin): US-NEW-023 — gestión de tenant` | 2026-04-20 |
| US-NEW-024 | Gestión jerarquía org (BU + Depto) en Admin | `feat(admin): US-NEW-024 — jerarquía org en admin` | 2026-04-20 |
| US-NEW-025 | Iconos en paneles de tenant + jerarquía | `feat(superadmin): US-NEW-025 — iconos en paneles` | 2026-04-20 |
| US-NEW-026 | Visión General = Tenants + Health unificados | `feat(superadmin): US-NEW-026 — visión general unificada` | 2026-04-20 |
| US-NEW-031 | Upload y display del logo del tenant en chrome | `feat(branding): US-NEW-031 — upload y display del logo del tenant en chrome` | 2026-04-20 |
| US-NEW-032 | Restructurar sidebar principal (drill-down real) | `feat(web): US-NEW-032 — sidebar drill-down real; elimina duplicado y módulos de proyecto` | 2026-04-20 |
| US-NEW-033 | Panel de organización → página de recursos reales | `feat(web,api): US-NEW-033 — panel de organización con recursos reales` | 2026-04-20 |
| US-NEW-034 | Página resumen de programa | `feat(web,api): US-NEW-034 — página resumen de programa con KPIs y donut` | 2026-04-20 |
| US-NEW-035 | Tabs inline en detalle de proyecto (supersede US-NEW-017) | `feat(web): US-NEW-035 — tabs inline en detalle de proyecto (supersede US-NEW-017)` | 2026-04-20 |
| US-NEW-036 | Restructurar sidebar Admin (4 ítems raíz) | `feat(web): US-NEW-036 — sidebar admin con 4 ítems raíz y /admin/tenant tabbed` | 2026-04-20 |
| US-NEW-037 | Infra compartida de exportación a PDF (WeasyPrint) | `feat(api): US-NEW-037 — infra de exportación a PDF con WeasyPrint + Jinja2` | 2026-04-20 |
| US-NEW-038 | Reporte de Avance de Proyecto (Python, BD, PDF) | `feat(api,web): US-NEW-038 — reporte de avance ejecutable sin IA` | 2026-04-20 |
| US-NEW-039 | Reporte de Seguimiento de Actividades (Python, BD, PDF) | `feat(api,web): US-NEW-039 — reporte de seguimiento por responsable` | 2026-04-20 |
| US-NEW-040 | Formato estandarizado + export de Minuta IA (.pdf/.docx/.md/.txt) | `feat(api,web): US-NEW-040 — export estandarizado de minuta` | 2026-04-20 |
| US-NEW-041 | Sidebar super admin aislado (4 ítems raíz) | `feat(web): US-NEW-041 — sidebar super admin aislado (4 ítems raíz)` | 2026-04-20 |
| US-NEW-042 | Página `/superadmin/users` cross-tenant | `feat(api,web): US-NEW-042 — /superadmin/users cross-tenant` | 2026-04-20 |
| US-NEW-043 | Visión General con Health al top | `feat(web): US-NEW-043 — health al top en visión general del superadmin` | 2026-04-20 |
| US-NEW-044 | Runbook Ollama + Cloudflare Tunnel + nssm | `docs(ai): US-NEW-044 — runbook Ollama + Cloudflare Tunnel + nssm` | 2026-04-20 |
| US-NEW-045 | Config + smoke test del túnel + secrets cifrados | `feat(api,web): US-NEW-045 — config y smoke del modelo IA local (Cloudflare Tunnel)` | 2026-04-20 |
| US-BUG-004 | Railway no redeploy tras PR #20 — troubleshooting documentado | `fix(infra): US-BUG-004 — Railway auto-deploy troubleshooting tras PR #20` | 2026-04-21 |
| US-BUG-005 | Sidebar super admin respeta user.is_superadmin en first paint | `fix(web): US-BUG-005 — sidebar super admin respeta user.is_superadmin en first paint` | 2026-04-21 |
| US-NEW-046 | Runbook Ollama + Tailscale (reemplaza CF Tunnel) | `docs(ai): US-NEW-046 — runbook Ollama + Tailscale (reemplaza CF Tunnel)` | 2026-04-21 |
| US-NEW-047 | Refactor config Ollama a Tailscale (quita CF-Access) | `feat(api,web): US-NEW-047 — refactor config Ollama a Tailscale (quita CF-Access)` | 2026-04-21 |
| US-NEW-048 | Sidecar Tailscale en worker Railway + config por-tenant en OllamaProvider | `feat(worker): US-NEW-048 — sidecar Tailscale en worker Railway + config por-tenant en OllamaProvider` | 2026-04-21 |

---

## 📋 Backlog ordenado por prioridad

### Bloque 1 — Jerarquía org (EP002) — BLOQUEANTE para todo lo demás
- [x] US-NEW-002 — Migración BD: tablas BU + Depto + FKs ✅
- [x] US-NEW-003 — CRUD Business Units (API) ✅
- [x] US-NEW-004 — CRUD Departments (API) ✅
- [x] US-NEW-005 — Sidebar org nav (Frontend) ✅
- [x] US-NEW-006 — Vista paneles de organizaciones (Frontend) ✅
- [x] US-BUG-001 — Fix 404 en Programas ✅

### Bloque 2 — Topbar y UX base (EP001)
- [x] US-NEW-007 — Toggle dark/light en dropdown usuario ✅
- [x] US-NEW-008 — Toggle idioma en dropdown usuario ✅
- [x] US-NEW-009 — Página administrar cuenta (perfil + cambiar password) ✅
- [x] US-NEW-010 — Color chrome #182e4e + Senior PMO = admin ✅

### Bloque 3 — Project Charter (EP003)
- [x] US-NEW-011 — Campos adicionales en solicitud (correos, personas clave, etc.) ✅
- [x] US-NEW-012 — Project Charter: tabla + generación al aprobar ✅
- [x] US-NEW-013 — Charter aparece como documento en el proyecto ✅

### Bloque 4 — Dashboard fixes (EP004)
- [x] US-BUG-002 — Fix distorsión gráficas de barra ✅
- [x] US-NEW-014 — Filtro organización en dashboard ✅
- [x] US-NEW-015 — KPIs respetan jerarquía de roles ✅
- [x] US-BUG-003 — Fix layout Plan vs Real (filtros horizontales + columna PM) ✅

### Bloque 5 — Proyecto detalle (EP005)
- [x] US-NEW-016 — Unificar Plan + Gantt en una pestaña ✅
- [~] US-NEW-017 — Tabs inline para módulos del proyecto → **SUPERSEDED** por US-NEW-035 (EP013, bloque 9)
- [x] US-NEW-018 — Módulo Área/Organigrama del proyecto ✅

### Bloque 6 — RAID y módulos (EP006)
- [x] US-NEW-019 — Consolidar RAID (Riesgos+Acciones+Incidentes+Decisiones) ✅
- [x] US-NEW-020 — Categorías de documentos actualizadas ✅
- [x] US-NEW-021 — Consolidar pestañas de Minutas en 1 ✅
- [x] US-NEW-022 — Módulo Reportes dentro del proyecto ✅

### Bloque 7 — Admin (EP007)
- [x] US-NEW-023 — Gestión de tenant (propuesta de acciones) ✅
- [x] US-NEW-024 — Gestión jerarquía org completa (BU + Depto) ✅

### Bloque 8 — SuperAdmin (EP010)
- [x] US-NEW-025 — Iconos en paneles de tenant ✅
- [x] US-NEW-026 — Visión General = Tenants + Health unidos ✅

---

### Bloque 9 — Refactor de navegación (EP013) — issue #17
**Orden de ejecución** (1 US por commit, en este orden):
- [x] US-NEW-031 — Upload y display del logo del tenant en chrome ✅
- [x] US-NEW-032 — Restructurar sidebar principal (drill-down real; quitar "Módulos de proyecto" y duplicado de Organizaciones) ✅
- [x] US-NEW-033 — Panel de organización → página de recursos reales (fix bug + enhancement) ✅
- [x] US-NEW-034 — Página resumen de programa (KPIs + lista de proyectos) ✅
- [x] US-NEW-035 — Tabs inline en detalle de proyecto (supersede US-NEW-017) ✅
- [x] US-NEW-036 — Restructurar sidebar Admin (fusionar Mi Tenant + Panel + Configuración; 4 ítems raíz) ✅

### Bloque 10 — Entregables operativos (EP014) — issue #18
- [x] US-NEW-037 — Infra compartida de exportación a PDF (WeasyPrint) ✅
- [x] US-NEW-038 — Reporte de Avance de Proyecto (Python, BD, PDF) ✅
- [x] US-NEW-039 — Reporte de Seguimiento de Actividades (Python, BD, PDF) ✅
- [x] US-NEW-040 — Formato estandarizado + export (.docx/.md/.txt/.pdf) de Minuta IA ✅

### Bloque 11 — Refactor nav super admin (EP015) — issue #19
- [x] US-NEW-041 — Sidebar super admin aislado (4 ítems raíz) ✅
- [x] US-NEW-042 — Página `/superadmin/users` cross-tenant (lista + edición) ✅
- [x] US-NEW-043 — Visión General con Health al top ✅

### Bloque 12 — Modelo IA local (EP016) — Ollama + Cloudflare Tunnel + nssm
- [x] US-NEW-044 — Runbook `docs/ai/local-ollama-setup.md` paso a paso ✅
- [x] US-NEW-045 — Config por-tenant + smoke test del túnel + secrets cifrados ✅
  *(follow-up: integrar config en `OllamaProvider.generate()` del worker EP008 para que `ai_cascade_fallback_total` incremente cuando el túnel falle)*

### Bloque 13 — Hotfixes operativos (reabre tras PR #20) ✅ CERRADO 2026-04-21

> **Contexto (2026-04-21):** el PR #20 mergeó a `main` con 6 US (NEW-041
> hasta NEW-045). El owner reportó dos síntomas que no se detectaron en CI:
> (a) Railway no redeployó los servicios al mergear; (b) el sidebar super
> admin no se ve como esperaba (probable state stale en `getStoredUser()`).
>
> Resolución: US-BUG-004 dejó documentado el troubleshooting en
> `RAILWAY_SETUP.md` (el toggle operativo lo aplica el owner del
> project). US-BUG-005 movió la lectura de `getStoredUser()` a
> `useEffect` con flag `userReady`, evitando el flash de TOP_NAV en
> primer paint para superadmins.

- [x] **US-BUG-004 — Railway no redeploy tras PR #20** ✅
  - **Diagnóstico inicial** (agente 2026-04-21): el commit `62b16f8`
    (US-NEW-045) SÍ toca `apps/api/**`, así que los servicios `api` +
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
  - **Commit:** `fix(infra): US-BUG-004 — Railway auto-deploy restablecido tras PR #20`.

- [x] **US-BUG-005 — Sidebar super admin no renderiza como esperado** ✅
  - **Diagnóstico inicial** (agente 2026-04-21): US-NEW-041
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
  - **Commit:** `fix(web): US-BUG-005 — sidebar super admin respeta user.is_superadmin en first paint`.

### Bloque 14 — EP016 v2: Ollama local vía Tailscale (reabre EP016) ✅ CERRADO 2026-04-21

> Reemplazó el canal CF Tunnel + Cloudflare Access por Tailscale tailnet
> privado. Ver ADR-015 + DEC-011. US-NEW-044/045 quedan SUPERSEDED.

- [x] US-NEW-046 — Runbook `docs/ai/local-ollama-setup.md` reescrito para Tailscale ✅
- [x] US-NEW-047 — `OllamaLocalAiForm` + endpoint `test-connection` sin CF-Access ✅
- [x] US-NEW-048 — Dockerfile worker Railway con sidecar `tailscaled` + `TS_AUTHKEY`; OllamaProvider consume config por-tenant ✅
- [ ] **Cleanup paralelo (owner, manual)**: borrar tunnel `pmoaas-ollama` de Cloudflare, retirar CNAME `ollama.*`, revocar Service Tokens. Documentado en `docs/ai/local-ollama-setup.md` §10 "Rollback CF Tunnel".

### Bloque 15 — Landing y DNS productivo (Cloudflare + Railway + HostGator)

> Finalizar el routing del dominio `pmo-aas.com` antes de release v1.0.
> Separado de EP016 porque no toca Ollama. Ver DEC-012.

- [ ] **US-NEW-049 — Configurar DNS productivo en Cloudflare**
  - Apex `pmo-aas.com` → redirect 301 a `app.pmo-aas.com` (page rule o CNAME flattening).
  - `app.pmo-aas.com` → CNAME al Railway web service (DNS only, nube gris).
  - `api.pmo-aas.com` → CNAME al Railway api service (DNS only, nube gris).
  - `www.pmo-aas.com` → A/CNAME a HostGator IP (proxied, nube naranja, Full SSL).
  - Verificar TLS Railway auto-provisiona cert para `app.*` y `api.*`.
  - Documentar en nuevo `docs/infra/dns-routing.md`.
  - **Commit:** `docs(infra): US-NEW-049 — DNS routing pmo-aas.com (Railway + HostGator)`.

- [ ] **US-NEW-050 — Landing estático en HostGator**
  - Subir HTML/CSS mínimo a `public_html/` de HostGator vía FTP/cPanel.
  - Contenido: marca PMO-aaS, 1-liner, CTA a `app.pmo-aas.com/login`.
  - Sin conexión a BD — es solo marketing.
  - Verificar `https://www.pmo-aas.com` sirve con TLS Cloudflare Full.
  - **Commit:** `feat(landing): US-NEW-050 — landing estático www.pmo-aas.com en HostGator`.

### Bloque 16 — Notificaciones (EP011) — POST-MVP
- [ ] US-NEW-027 — Tabla notifications + in-app center
- [ ] US-NEW-028 — Email notifications via Resend

### Bloque 17 — Instalación productivo HostGator MySQL (EP012) — ❌ CANCELADO

> **CANCELADO (2026-04-21, ver DEC-013).** El owner subió el tier de
> Railway y productivo v1.0/v1.x corre íntegramente en Railway Postgres.
> El costo incremental se cubre con licencias cobradas. No hay plan
> futuro de migrar a MySQL; EP012 se conserva solo como referencia
> histórica.

- [x] ~~US-NEW-029~~ — ❌ CANCELADA (DEC-013)
- [x] ~~US-NEW-030~~ — ❌ CANCELADA (DEC-013)

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
