# EP013 — Refactor de navegación (sidebar + admin + tabs inline)

| Campo | Valor |
|---|---|
| **ID** | EP013 |
| **Prioridad** | Alta — bloque 9 del sprint (antes de POST-MVP) |
| **Dependencias** | EP001, EP002, EP005, EP006, EP007, EP010 completos |
| **Módulo** | `web.nav`, `admin`, `projects.detail`, `superadmin` |
| **Estado** | # PENDING |
| **Versión objetivo** | v1.1 |
| **Issue origen** | [#17 — Mejora de barra de navegación de tenants](https://github.com/xguilxr/pmo_aas/issues/17) |

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

## # DONE — US-NEW-031 — Upload y display del logo del tenant en chrome

**Como** admin / senior PMO
**Quiero** subir el logo de mi tenant y que se muestre en el topbar (reemplazando el texto `PMO•aaS`)
**Para** que la app refleje la marca de mi organización.

**Criterios de aceptación:**
- [x] `PATCH /api/v1/admin/tenant` sigue aceptando `logo_url` como URL string (US-NEW-023).
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

**Commit:** `feat(branding): US-NEW-031 — upload y display del logo del tenant en chrome`.

---

## # DONE — US-NEW-032 — Restructurar sidebar principal (drill-down real)

**Como** usuario autenticado
**Quiero** que el sidebar principal me muestre Organizaciones → Programas → Proyectos reales, sin duplicar la jerarquía administrativa
**Para** navegar a mi proyecto en pocos clicks.

**Criterios de aceptación:**
- [x] Sidebar principal expone: `Tablero`, `Solicitudes`, `Organizaciones`, `Admin` (no-superadmin).
- [x] Bajo "Organizaciones" aparece la lista de orgs reales del tenant con chevron.
- [x] Expandir org → lista de programas reales de esa org (endpoints existentes, lazy).
- [x] Expandir programa → lista de proyectos reales de ese programa.
- [x] Click en la hoja:
  - Organización → `/admin/organizations/{id}` (enlace se redirige al panel de recursos reales en US-NEW-033 siguiente).
  - Programa → `/admin/projects?program_id={id}` temporal; se actualiza a `/admin/programs/{id}` cuando US-NEW-034 cree la página resumen.
  - Proyecto → `/admin/projects/{id}` (DONE).
- [x] **Eliminada** la sección duplicada "Organizaciones (jerarquía administrativa)" del sidebar principal — BUs/Deptos sólo en `/admin/organizations`.
- [x] **Eliminada** la sección "Módulos de proyecto" del sidebar (sus ítems serán tabs inline en US-NEW-035).
- [x] Expansión persistida en `localStorage` (`pmoaas:sidebar:org-tree:expanded`).
- [~] Endpoint `GET /api/v1/me/nav-tree?depth=3` **diferido**: la carga lazy con los endpoints existentes (`list{Organizations,Programs,Projects}`) cumple el caso de uso; un endpoint agregado se considerará si el number de nodos supera cientos. No bloqueante.

**Implementación:**
- `OrgTreeNav` simplificado (sin BUs / Deptos) y promovido a entrada raíz del sidebar.
- `AppShell` dividido en 3 bloques explícitos: `TOP_NAV` (Tablero + Solicitudes) → `<OrgTreeNav />` → `ADMIN_NAV` (+ SUPERADMIN_NAV si aplica).

**Commit:** `feat(web): US-NEW-032 — sidebar drill-down real; elimina duplicado y módulos de proyecto`.

---

## # DONE — US-NEW-033 — Panel de organización → página de recursos reales (fix bug)

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

**Commit:** `feat(web,api): US-NEW-033 — panel de organización con recursos reales`.

---

## # PENDING — US-NEW-034 — Página resumen de programa

**Como** usuario con acceso al programa
**Quiero** una página de resumen del programa con KPIs y lista de proyectos
**Para** evaluar su estado sin entrar a cada proyecto.

**Criterios de aceptación:**
- [ ] Ruta `/admin/programs/{id}` con:
  - Header: nombre, org, PM del programa (si aplica), fase agregada, salud agregada.
  - KPIs: #proyectos totales, #activos, #en riesgo (health ≠ green), #cerrados, presupuesto plan vs real agregado.
  - Gráfica de status de proyectos (donut: green/yellow/red).
  - Lista de riesgos top (severidad ≥ 13) a través de todos los proyectos del programa.
  - Tabla de proyectos del programa (mismo formato que US-024, sin filtro de programa).
- [ ] Endpoint `GET /api/v1/programs/{id}/summary` con agregados.
- [ ] Permiso `programs:read` — cualquier usuario con acceso al programa.
- [ ] Enlazada desde sidebar (US-NEW-032).

**Test Cases:**
- `TC-NEW-034-1` (integration) — Summary agrega counts correctos con 5 proyectos seed.
- `TC-NEW-034-2` (integration) — Presupuesto plan/real suma presupuestos de proyectos activos.
- `TC-NEW-034-3` (E2E) — Click en fila de proyecto abre su detalle.

---

## # PENDING — US-NEW-035 — Tabs inline en detalle de proyecto (supersede US-NEW-017)

**Como** PM
**Quiero** que los módulos del proyecto (Charter, Plan, RAID, Áreas, Documentos, Lecciones, Minutas, Reportes, Cambios) sean tabs dentro de `/admin/projects/{id}`, no páginas separadas
**Para** no perder contexto al moverme entre módulos.

> Esta US **supersede** la US-NEW-017 original (que queda marcada como obsoleta).

**Criterios de aceptación:**
- [ ] Detalle del proyecto `/admin/projects/{id}` renderiza una barra de tabs con el orden:
  `Resumen | Equipo | Charter | Plan | RAID | Áreas | Documentos | Lecciones | Minutas | Reportes | Cambios | Actividad`.
- [ ] Tab activa persistida como `?tab=<key>` en la URL (deep-linkable).
- [ ] Click en tab cambia panel inferior sin navegar a otra página.
- [ ] Tab activa resaltada visualmente (estilo design system).
- [ ] Si el ancho es insuficiente: scroll horizontal en la barra (o dropdown "más" al final).
- [ ] Las rutas legacy `/admin/projects/{id}/plan`, `/raid`, `/areas`, `/minutes`, `/reports`, etc. **siguen funcionando** como redirect permanente a `/admin/projects/{id}?tab=<key>`.
- [ ] La entrada de sidebar "Módulos de proyecto" queda eliminada (ver US-NEW-032).

**Test Cases:**
- `TC-NEW-035-1` (E2E) — Todas las tabs cargan su contenido sin recarga completa.
- `TC-NEW-035-2` (E2E) — Deep-link `?tab=raid` abre la tab RAID activa.
- `TC-NEW-035-3` (E2E) — `/admin/projects/{id}/plan` redirige a `/admin/projects/{id}?tab=plan`.

---

## # PENDING — US-NEW-036 — Restructurar sidebar Admin

**Como** admin / senior PMO
**Quiero** que el sidebar Admin tenga sólo 4 entradas lógicas, sin duplicación
**Para** no navegar entre "Mi Tenant" y "Panel del Tenant" que muestran info repetida.

**Criterios de aceptación:**
- [ ] Sidebar Admin:
  - `Gestión de Tenant` (fusiona "Mi Tenant" + "Panel del Tenant" + "Configuración"). Una sola página con tabs internos: `Información | Branding | Configuración | Uso & Stats`.
  - `Gestión de Organizaciones` (BUs, Deptos y programas en una sola página con selector de org; no sub-páginas — ver criterio US-NEW-024 ya implementado, ampliar si hace falta).
  - `Gestión de Usuarios y Roles`
    - `Usuarios`
    - `Roles`
  - `Auditoría`
- [ ] Se **elimina** del sidebar la entrada "Configuración" como ítem independiente.
- [ ] Se **elimina** la entrada duplicada "Mi Tenant" o "Panel del Tenant" (queda sólo "Gestión de Tenant").
- [ ] Ruta consolidada: `/admin/tenant` con tabs internos. Rutas legacy `/admin/my-tenant`, `/admin/tenant/panel`, `/admin/settings` redirigen a `/admin/tenant?tab=<info|branding|config|stats>`.
- [ ] La validación de acceso sigue la regla DEC-005 (admin + senior PMO).

**Test Cases:**
- `TC-NEW-036-1` (integration) — `/admin/settings` → 301 a `/admin/tenant?tab=config`.
- `TC-NEW-036-2` (E2E) — Sidebar admin muestra exactamente 4 ítems raíz.
- `TC-NEW-036-3` (E2E) — Usuario con rol "Project Manager" (no senior) no ve el sidebar Admin.

---

## Endpoints nuevos o modificados

```
# Tenant branding
POST   /api/v1/admin/tenant/logo              (upload multipart)   [US-NEW-031]
GET    /api/v1/me/tenant-branding             (consumido por topbar)

# Nav tree del sidebar principal
GET    /api/v1/me/nav-tree?depth=3                                  [US-NEW-032]

# Organización panel (read-only)
GET    /api/v1/organizations/{id}/panel                             [US-NEW-033]

# Programa summary
GET    /api/v1/programs/{id}/summary                                [US-NEW-034]
```

## Cambios de schema

Ninguno nuevo. `tenants.logo_url` ya existe (US-NEW-023). Si falta el campo de upload físico, añadirlo como parte de US-NEW-031 con su propia migración.

---

## Definition of Done

- [ ] Sidebar principal muestra drill-down real; no hay duplicados con jerarquía administrativa.
- [ ] Sidebar Admin con 4 ítems raíz; sin entrada "Configuración" independiente.
- [ ] Detalle de proyecto usa tabs inline; rutas legacy redirigen.
- [ ] Logo del tenant se muestra en topbar cuando está configurado.
- [ ] US-NEW-017 marcada como superseded por US-NEW-035.
- [ ] DEC-011, DEC-012, DEC-013 registrados en DECISIONS.md.
- [ ] Tests E2E verdes para navegación completa (3 clicks hasta un proyecto).
