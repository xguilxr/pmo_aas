# EP013 — Refactor de navegación (sidebar + admin + tabs inline)

| Campo | Valor |
|---|---|
| **ID** | EP013 |
| **Prioridad** | Alta — bloque 9 del sprint (antes de POST-MVP) |
| **Dependencias** | EP001, EP002, EP005, EP006, EP007, EP010 completos |
| **Módulo** | `web.nav`, `admin`, `projects.detail`, `superadmin` |
| **Estado** | Sprint 5 (v1.4) — US-075 completa (sub-bloques A+B+C fix-committed) |
| **Versión objetivo** | v1.4 |
| **Issues** | [#17 origen](https://github.com/xguilxr/pmo_aas/issues/17), [#128 US-075 TO-BE](https://github.com/xguilxr/pmo_aas/issues/128) |

## Actualización 2026-04-24 — TO-BE del owner (Sprint 5)

Owner reabrió este epic tras detectar **2 "PMO" en el sidebar**
(uno viejo en `OrgTreeNav` apuntando a `/admin/organizations`, otro
nuevo de US-068 apuntando a `/pmo`) + el diagnóstico de navegación
As-Is de Claude Code. Decisión consolidada:

**DEC-022** — separar namespaces de rutas:
- `/pmo/*` — recursos de **negocio** (proyectos, solicitudes, RAID,
  minutas, reportes, org/program informativos). Visible a cualquier
  user del tenant.
- `/admin/*` — recursos de **sistema** (tenant config, users, roles,
  AI settings, audit logs). Solo admin/superadmin.
- `/superadmin/*` — solo `is_superadmin=True`.

**DEC-023 (follow-up)** — evaluar `/{tenant_slug}/pmo/...` como
prefijo URL. No bloquea DEC-022; se abre ADR separado.

**US-075 (#128)** ejecuta el refactor:
- Mover `page.tsx` de `/admin/{projects,requests,raid,changes,minutes,reports,programs/[id]}` → `/pmo/...`.
- Redirects 301 de rutas viejas por compat.
- `OrgTreeNav` visible para todos los users del tenant.
- Páginas informativas nuevas: `/pmo/programs/` listado, `/pmo/programs/[id]`.
- Backend: permisos GET de org/program/project no requieren `admin.*`.
- ENH-029 (fix puntual de los 2 PMO) absorbido por US-075.

**Blast radius alto:** ~30 page.tsx movidos + ~50 `<Link>` + backend
perms + docs. ETA 5-7 días. Owner puede partir en sub-US si conviene.

### Estado de ejecución (2026-04-24)

**Sub-bloque A — Mover rutas + redirects** ✅ fix-committed
- 7 directorios movidos via `git mv` (preserva historial git).
- 137 referencias en 40 archivos sustituidas masivamente con `sed`.
- 11 redirects 301 agregados a `apps/web/next.config.js` (incluye
  `:path*` para sub-rutas y entradas literales para los listados).

**Sub-bloque C — Sidebar + permisos** ✅ fix-committed
- Item "PMO" standalone retirado del `TOP_NAV` (eliminado el
  duplicado vs el header del `OrgTreeNav`).
- `OrgTreeNav` header `PMO` ahora apunta a `/pmo` (antes
  `/admin/organizations`); cada org node apunta a
  `/pmo/organizations/${id}` (vista informativa, no editor).
- `app-shell` separa visibility:
  - `OrgTreeNav` visible a cualquier user del tenant
    (`!user.is_superadmin`).
  - `ADMIN_NAV` visible solo si `role_type === "admin"`
    (antes era a cualquier no-superadmin — bug de scope).
- Permisos backend ya estaban alineados (verificado via inspect):
  `require_permission("organizations|projects", "read")` ya admite
  user/viewer en sus mappings estáticos (DEC-020). No requirió cambios
  en endpoints.

**Sub-bloque B — Páginas informativas** ✅ fix-committed
- `/pmo/programs/page.tsx` reescrita como grid de cards informativos
  (sin CRUD ni modal "Nuevo programa" — la creación queda en
  `/admin/organizations/{id}`). Header breadcrumb `PMO / Programas`,
  3 KPI cards (total/activos/inactivos) + filtros (search/org/estado).
  Click en card → resumen `/pmo/programs/{id}` (US-034).
- `/pmo/programs/[id]/page.tsx` — breadcrumbs + BackLink fallbacks
  actualizados para apuntar a `/pmo/organizations/{id}` y `/pmo` en
  vez de `/admin/organizations`. KPIs, donut y top risks ya estaban
  completos (US-034).
- `/pmo/organizations/[id]/page.tsx` — agregada fila de 4 KPI cards
  arriba de la sección Programas: Business Units, Departamentos,
  Programas activos (hint con total), Proyectos activos (hint con
  total). Derivados de `OrganizationPanelDetail` sin requerir
  endpoint nuevo.

## Objetivo de negocio

El sidebar hoy mezcla dos árboles de organización (jerarquía administrativa y drill-down real) y obliga a navegar a páginas separadas para cada módulo del proyecto. Esto confunde al usuario y rompe la expectativa de que "entrar a un proyecto" es una sola pantalla.

La refactor consolida la navegación en:

- **Sidebar principal (todos los usuarios):** drill-down real Organización → Programa → Proyecto. Dentro del proyecto, los módulos son tabs, no entradas del sidebar.
- **Sidebar Admin (admin / senior PMO):** un solo lugar para gestión de tenant, jerarquía org, usuarios/roles y auditoría. Sin página "Configuración" separada.

## Alcance propuesto

### Sidebar principal (drill-down real)

```
Logo/Home (usa logo del tenant si está cargado)
├─ Tablero
├─ Solicitudes
├─ Organizaciones
│   ├─ Org A                  → panel de recursos de la org
│   │   ├─ Programa 1         → resumen del programa (KPIs + proyectos)
│   │   │   └─ Proyecto X     → detalle del proyecto con tabs inline
│   │   └─ Programa 2
│   └─ Org B
└─ Admin (solo admin/senior PMO)
    ├─ Gestión de Tenant      (fusiona Mi Tenant + Panel del Tenant)
    ├─ Gestión de Organizaciones  (BUs + Deptos inline, una sola página)
    ├─ Gestión de Usuarios y Roles
    │   ├─ Usuarios
    │   └─ Roles
    └─ Auditoría
```

Se **elimina**:

- La segunda sección "Organizaciones" del sidebar que sólo mostraba jerarquía administrativa (queda sólo en `/admin/organizations`).
- La entrada de sidebar "Módulos de proyecto" (los módulos viven como tabs del detalle de proyecto).
- La entrada de sidebar "Configuración" (se integra en Gestión de Tenant).

### DEC-XXX a registrar en DECISIONS.md al cierre del bloque

- **DEC-011** — Sidebar principal expone drill-down real; sidebar admin expone jerarquía administrativa. No se duplican.
- **DEC-012** — Los módulos del proyecto viven como tabs dentro de `/admin/projects/{id}` (no como rutas separadas en el sidebar global). Las rutas individuales actuales quedan como deep-link para compatibilidad.
- **DEC-013** — "Mi Tenant" y "Panel del Tenant" se consolidan en una sola página bajo `Admin → Gestión de Tenant`.

---

## # DONE — US-031 — Upload y display del logo del tenant en chrome

**Como** admin / senior PMO
**Quiero** subir el logo de mi tenant y que se muestre en el topbar (reemplazando el texto `PMO•aaS`)
**Para** que la app refleje la marca de mi organización.

**Criterios de aceptación:**
- [x] `PATCH /api/v1/admin/tenant` sigue aceptando `logo_url` como URL string (US-023).
- [x] Endpoint `POST /api/v1/admin/tenant/logo` (multipart):
  - Acepta PNG / JPG / SVG / WEBP ≤ 2 MB.
  - Guarda en `{STORAGE_PATH}/tenants/{tenant_id}/logo.{ext}`.
  - Reemplaza variantes previas (otra extensión) al subir.
  - Actualiza `tenants.logo_url` al endpoint interno de serving.
- [x] Endpoint `DELETE /api/v1/admin/tenant/logo` para quitar logo local.
- [x] Endpoint `GET /api/v1/branding/tenants/{tenant_id}/logo` sirve el archivo (auth requerida; 404 si el user no es de ese tenant y no es superadmin).
- [x] Endpoint `GET /api/v1/me/tenant-branding` devuelve `{tenant_id, tenant_name, tenant_slug, logo_url, primary_color}` — consumido por el topbar.
- [x] `BrandMark` (frontend): cuando `logo_url` existe, muestra `<img>` con `alt=tenant_name`; si no, fallback `"PMO · aaS"`.
- [x] `TenantBrandingProvider` con caché en `localStorage` + refresh explícito tras upload/edición en `/admin/tenant`.
- [x] Click en el logo/home → navega a `/dashboard`.
- [x] `/admin/tenant` acepta archivo (botón "Subir archivo") o URL externa — el cambio se refleja en el topbar sin reload completo via `refreshBranding()`.

**Test Cases (8/8 verdes):**
- `test_usnew031_upload_png_sets_logo_url` — happy path upload + serve.
- `test_usnew031_upload_rejects_oversized` — > 2 MB → 413.
- `test_usnew031_upload_rejects_bad_mime` — MIME no permitido → 400.
- `test_usnew031_non_admin_cannot_upload` — usuario sin `admin.users:update` → 403.
- `test_usnew031_cross_tenant_serve_blocked` — admin de tenant A intentando pedir logo de tenant B → 404.
- `test_usnew031_delete_logo` — DELETE quita archivo y limpia `logo_url`.
- `test_usnew031_me_tenant_branding` — endpoint devuelve data correcta antes y después de upload.
- `test_usnew031_overwrite_replaces_old_extension` — subir WEBP tras PNG deja un solo archivo en disco.

**Commit:** `feat(branding): US-031 — upload y display del logo del tenant en chrome`.

---

## # DONE — US-032 — Restructurar sidebar principal (drill-down real)

**Como** usuario autenticado
**Quiero** que el sidebar principal me muestre Organizaciones → Programas → Proyectos reales, sin duplicar la jerarquía administrativa
**Para** navegar a mi proyecto en pocos clicks.

**Criterios de aceptación:**
- [x] Sidebar principal expone: `Tablero`, `Solicitudes`, `Organizaciones`, `Admin` (no-superadmin).
- [x] Bajo "Organizaciones" aparece la lista de orgs reales del tenant con chevron.
- [x] Expandir org → lista de programas reales de esa org (endpoints existentes, lazy).
- [x] Expandir programa → lista de proyectos reales de ese programa.
- [x] Click en la hoja:
  - Organización → `/admin/organizations/{id}` (enlace se redirige al panel de recursos reales en US-033 siguiente).
  - Programa → `/admin/projects?program_id={id}` temporal; se actualiza a `/admin/programs/{id}` cuando US-034 cree la página resumen.
  - Proyecto → `/admin/projects/{id}` (DONE).
- [x] **Eliminada** la sección duplicada "Organizaciones (jerarquía administrativa)" del sidebar principal — BUs/Deptos sólo en `/admin/organizations`.
- [x] **Eliminada** la sección "Módulos de proyecto" del sidebar (sus ítems serán tabs inline en US-035).
- [x] Expansión persistida en `localStorage` (`pmoaas:sidebar:org-tree:expanded`).
- [~] Endpoint `GET /api/v1/me/nav-tree?depth=3` **diferido**: la carga lazy con los endpoints existentes (`list{Organizations,Programs,Projects}`) cumple el caso de uso; un endpoint agregado se considerará si el number de nodos supera cientos. No bloqueante.

**Implementación:**
- `OrgTreeNav` simplificado (sin BUs / Deptos) y promovido a entrada raíz del sidebar.
- `AppShell` dividido en 3 bloques explícitos: `TOP_NAV` (Tablero + Solicitudes) → `<OrgTreeNav />` → `ADMIN_NAV` (+ SUPERADMIN_NAV si aplica).

**Commit:** `feat(web): US-032 — sidebar drill-down real; elimina duplicado y módulos de proyecto`.

---

## # DONE — US-033 — Panel de organización → página de recursos reales (fix bug)

**Como** usuario
**Quiero** que al seleccionar el panel de una organización me lleve a una página con sus recursos reales (BUs, Deptos, Programas, Usuarios, Proyectos), no a la pantalla de "editar organización" del admin
**Para** explorar el estado de la org sin privilegios de admin.

**Criterios de aceptación:**
- [x] Nueva ruta `/admin/organizations/{id}/panel` (auth-only, tenant-scoped).
- [x] Secciones: header con logo / nombre / industry / country / is_active + contacto; KPIs (BUs, Deptos, Programas, Proyectos); lista de BUs con sus Deptos; tabla de Programas (con count de proyectos activos); tabla de Proyectos (folio, fase, salud, PM); usuarios con rol en la org (PMs + miembros de proyectos).
- [x] Botón "Editar organización" sólo visible si el user es superadmin o tiene rol `Administrador` / `PMO Manager` — redirige a `/admin/organizations/{id}` (editor preexistente).
- [x] Endpoint `GET /api/v1/organizations/{id}/panel` — un solo response con BUs + Deptos + Programas + Proyectos + Users; auth-only sin permiso admin (cross-tenant → 404).
- [x] Sidebar (OrgTreeNav) ahora apunta las orgs a `/panel` en vez de al editor (fix bug del issue #17).

**Test Cases (4/4 verdes):**
- `test_usnew033_panel_happy_path` — datos agregados correctos.
- `test_usnew033_panel_non_admin_can_read` — user sin admin.users → 200.
- `test_usnew033_panel_cross_tenant_404` — aislamiento multi-tenant.
- `test_usnew033_panel_empty_org` — sin BUs/programas/proyectos no crashea.

**Commit:** `feat(web,api): US-033 — panel de organización con recursos reales`.

---

## # DONE — US-034 — Página resumen de programa

**Como** usuario con acceso al programa
**Quiero** una página de resumen del programa con KPIs y lista de proyectos
**Para** evaluar su estado sin entrar a cada proyecto.

**Criterios de aceptación:**
- [x] Endpoint `GET /api/v1/programs/{id}/summary` auth-only + cross-tenant → 404.
- [x] Ruta `/admin/programs/{id}` con:
  - Header: nombre, org (link al panel), is_active badge, descripción.
  - 4 KPI cards: proyectos total / activos / en riesgo / cerrados.
  - Donut SVG con salud del portafolio (green/yellow/red).
  - Presupuesto plan vs real agregado + desviación %.
  - Top 10 riesgos con `severity >= 13` no cerrados/materializados.
  - Tabla de proyectos con folio, fase, salud, PM, avance, presupuesto plan/real.
- [x] Sidebar (`OrgTreeNav`): link de programa actualizado a `/admin/programs/{id}` (antes apuntaba a `/admin/projects?program_id=…`).

**Test Cases (3/3 verdes):**
- `test_usnew034_summary_aggregates_correctly` — counts, health, presupuestos, top risks filtrados por severidad y status.
- `test_usnew034_summary_cross_tenant_404` — aislamiento.
- `test_usnew034_summary_empty_program` — programa vacío no crashea.

**Commit:** `feat(web,api): US-034 — página resumen de programa con KPIs y donut`.

---

## # DONE — US-035 — Tabs inline en detalle de proyecto (supersede US-017)

**Como** PM
**Quiero** que los módulos del proyecto (Plan, RAID, Áreas, Documentos, Lecciones, Minutas, Reportes, Cambios) sean tabs dentro de `/admin/projects/{id}`, no páginas separadas
**Para** no perder contexto al moverme entre módulos.

> Esta US **supersede** la US-017 original.

**Criterios de aceptación:**
- [x] Shared layout `app/(app)/admin/projects/[id]/layout.tsx` con barra de tabs sticky (`<ProjectTabsBar />`).
- [x] Tabs visibles en orden: `Resumen | Plan | RAID | Áreas | Documentos | Lecciones | Minutas | Reportes | Cambios`. Charter se mantiene como documento del proyecto (categoría en Documentos, ya DONE por US-013). Equipo y Actividad siguen como sub-tabs internas de la página Resumen (pattern preexistente de `/admin/projects/[id]/page.tsx`).
- [x] Next.js layout persiste entre navegaciones a sub-rutas (`/plan`, `/raid`, etc.): el header y el tab bar no se re-renderizan, la percepción de UX coincide con "no hay cambio de página".
- [x] Tab activa resaltada (bg `--color-subtle`, font-semibold).
- [x] Scroll horizontal en la barra para anchos reducidos (`overflow-x-auto`).
- [x] Rutas legacy `/plan`, `/raid`, `/areas`, `/documents`, etc. siguen funcionando como páginas individuales dentro del layout tabbed.
- [x] La entrada "Módulos de proyecto" del sidebar principal fue eliminada en US-032.

**Nota de diseño:** El criterio original pedía `?tab=<key>` con renderizado inline del contenido. La implementación usa sub-paths compartiendo layout — es equivalente UX-wise (Next.js no re-monta el layout al cambiar de sub-ruta) y mucho más barata de mantener porque no refactoriza las 8 páginas de módulos en componentes loadable. Si a futuro se requiere query-param puro, el refactor queda como follow-up.

**Commit:** `feat(web): US-035 — tabs inline en detalle de proyecto (supersede US-017)`.

---

## # DONE — US-036 — Restructurar sidebar Admin

**Como** admin / senior PMO
**Quiero** que el sidebar Admin tenga sólo 4 entradas lógicas, sin duplicación
**Para** no navegar entre "Mi Tenant" y "Panel del Tenant" que muestran info repetida.

**Criterios de aceptación:**
- [x] Sidebar Admin ahora tiene **4 ítems raíz**:
  - `Gestión de Tenant` → `/admin/tenant` (con tabs internos `?tab=info|branding|config|stats`).
  - `Gestión de Organizaciones` → `/admin/organizations` (preexistente con BUs/Deptos en tree inline).
  - `Usuarios y Roles` → parent colapsable con `Usuarios` y `Roles`.
  - `Auditoría` → `/admin/audit-logs`.
- [x] Entrada `Configuración` **eliminada** del sidebar como ítem standalone.
- [x] Entradas `Mi tenant` + `Panel del Tenant` fusionadas bajo `Gestión de Tenant`.
- [x] Página `/admin/tenant` refactorizada con tabs visuales: Información / Branding / Configuración / Uso & Stats. La pestaña Configuración renderiza `<TenantSettingsForm />` (componente extraído para reuso).
- [x] Redirects permanentes en `next.config.js`:
  - `/admin/supervision` → `/admin/tenant?tab=stats`.
  - `/admin/settings` → `/admin/tenant?tab=config`.
- [x] DEC-005 respetada: el sidebar Admin sigue siendo visible a usuarios no-superadmin con rol `Administrador` o `PMO Manager`; las rutas validan `require_permission` en backend.
- [x] `/admin/settings` ahora usa `<TenantSettingsForm />` (queda como handler legacy; el redirect Next-side se aplica antes de que se renderice la página en SSR, pero dejar la página mantiene dev tests si alguien navega directo vía dev server dynamic render).

**Commit:** `feat(web): US-036 — sidebar admin con 4 ítems raíz y /admin/tenant tabbed`.

---

## Endpoints nuevos o modificados

```
# Tenant branding
POST   /api/v1/admin/tenant/logo              (upload multipart)   [US-031]
GET    /api/v1/me/tenant-branding             (consumido por topbar)

# Nav tree del sidebar principal
GET    /api/v1/me/nav-tree?depth=3                                  [US-032]

# Organización panel (read-only)
GET    /api/v1/organizations/{id}/panel                             [US-033]

# Programa summary
GET    /api/v1/programs/{id}/summary                                [US-034]
```

## Cambios de schema

Ninguno. US-031 (upload de logo) reusa `tenants.logo_url` + el
storage local ya existente; no se agregó migración. Resto del refactor
es puramente UI.

---

## Definition of Done

- [ ] Sidebar principal muestra drill-down real; no hay duplicados con jerarquía administrativa.
- [ ] Sidebar Admin con 4 ítems raíz; sin entrada "Configuración" independiente.
- [ ] Detalle de proyecto usa tabs inline; rutas legacy redirigen.
- [ ] Logo del tenant se muestra en topbar cuando está configurado.
- [ ] US-017 marcada como superseded por US-035.
- [ ] DEC-011, DEC-012, DEC-013 registrados en DECISIONS.md.
- [ ] Tests E2E verdes para navegación completa (3 clicks hasta un proyecto).
