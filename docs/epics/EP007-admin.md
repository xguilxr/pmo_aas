---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-29
revisar_cada: 90d
---

# EP007 — Panel de Administración

| Campo | Valor |
|---|---|
| **ID** | EP007 |
| **Prioridad** | Alta |
| **Dependencias** | EP001, EP002 |
| **Módulo** | `admin.*` |
| **Estado** | MVP |

## Objetivo de negocio

Un panel único centraliza la gestión de usuarios, roles, organizaciones y proyectos del tenant, con vistas optimizadas para operaciones rápidas (crear, editar, desactivar, resetear, etc.).

---

## US-037 — Panel de administración de usuarios

**Como** Administrador
**Quiero** una tabla completa de usuarios con acciones rápidas
**Para** onboardear y gestionar el equipo.

**Criterios de aceptación:**
- [ ] Columnas: nombre, username, email, roles (chips), estado (activo/bloqueado), último login, acciones.
- [ ] Acciones inline: editar, activar/desactivar, resetear password, desbloquear, impersonate (solo superadmin).
- [ ] Búsqueda fuzzy + filtros (rol, estado).
- [ ] Export CSV/XLSX con filtros aplicados.
- [ ] No se permite desactivar la cuenta propia.
- [ ] Bulk actions: asignar rol a varios seleccionados, desactivar masivo (con confirmación).

**Test Cases:**
- `TC-098` (integration) — Desactivar cuenta propia → 422 `BUSINESS_RULE`.
- `TC-099` (integration) — Bulk asignar rol a 10 users → todos afectados, audit log con 10 entradas.
- `TC-100` (E2E) — Export CSV descarga con headers correctos.

---

## US-038 — Panel de administración de roles ⛔ RETIRADA (DEC-024 / US-077)

> **Reemplazada por el modelo de capabilities.** El editor de rol con matriz
> de permisos vivió en `/admin/roles/*` (`admin_roles.py`) hasta que **US-077**
> lo borró junto con esa UI (DEC-024): los permisos pasaron a 5 capabilities
> estáticas en código (`tenant.manage`, `ai.configure`, `users.manage`,
> `organizations.delete`, `audit.read`). `Role.permissions` se ignora desde
> US-076; las tablas `roles`/`user_roles` quedan solo como compat (ver
> `apps/api/app/models/role.py`).
>
> **Lo que hay hoy:** `/admin/permissions` (US-078) — página **de solo
> lectura** que lista las 5 capabilities y si admin/user las tiene. La
> excepción puntual por tenant no se edita ahí: la crea el superadmin en
> `/superadmin/tenants/[id]/permissions` (DEC-021 / US-073), sobre la tabla
> `tenant_role_permission_overrides` (modelo `TenantRolePermissionOverride`).
>
> Los AC de abajo se conservan como registro de lo que se entregó y luego se retiró.

**Como** Administrador
**Quiero** definir roles con matriz de permisos (checkboxes por módulo × acción)
**Para** controlar acceso granular.

**Criterios de aceptación (histórico):**
- [ ] Tabla de roles con `name`, `description`, `user_count`, acciones.
- [ ] Editor de rol: matriz visual 12×8 (módulos × acciones) con checkboxes.
- [ ] Toggle "seleccionar todos" por fila y por columna.
- [ ] Preview "Este cambio afecta a N usuarios: …" antes de guardar.
- [ ] Roles sistema (`is_system=true`) muestran badge "Sistema" y deshabilitan borrar.
- [ ] Duplicar rol (as template).

**Test Cases:**
- `TC-101` (E2E) — Toggle "todos" marca fila completa.
- `TC-102` (E2E) — Preview muestra lista de afectados.
- `TC-103` (integration) — Duplicar rol → copia `permissions` pero `is_system=false`.

---

## US-039 — Panel de administración de organizaciones

**Como** Administrador
**Quiero** gestionar organizaciones desde un panel con métricas
**Para** ver impacto.

**Criterios de aceptación:**
- [ ] Cards con métricas por org: `project_count_active`, `budget_total`, `user_count`.
- [ ] Link rápido a "Ver proyectos de esta org".
- [ ] Upload logo inline con preview + crop 1:1.
- [ ] Soft delete con confirmación y advertencia de proyectos afectados.

**Test Cases:**
- `TC-104` (integration) — Métricas por org coinciden con queries directas.
- `TC-105` (E2E) — Upload logo con crop → guardado correcto.

---

## US-040 — Panel del Tenant (supervisión global de proyectos)

**Como** Administrador
**Quiero** ver **todos** los proyectos del tenant sin filtro de miembro
**Para** supervisión global.

**Criterios de aceptación:**
- [ ] Ruta `/admin/supervision` (label en sidebar: **"Panel del Tenant"**, bajo el dropdown _Admin_).
- [ ] Endpoint especial `GET /api/v1/admin/projects` — bypass filtro `is_member`.
- [ ] Solo accesible con permiso `admin.projects:read`.
- [ ] Métricas globales: total, por estado, por organización, desviaciones.
- [ ] Acciones: cambiar PM, forzar cierre (con comentario).

**Test Cases:**
- `TC-106` (integration) — User sin `admin.projects:read` → 403.
- `TC-107` (integration) — Admin ve todos los proyectos incluidos los de orgs inactivas.

---

## US-041 — Configuración del tenant

**Como** Administrador
**Quiero** configurar preferencias del tenant
**Para** personalizar.

**Criterios de aceptación:**
- [ ] Sección "Configuración" con:
  - Idioma default (`es-MX` / `en-US`).
  - Moneda default (`MXN`, `USD`, `EUR`).
  - Formato de fecha.
  - Timezone.
  - Logo corporativo + color primario (para PDFs exportados).
  - Modo IA (`platform` / `byo` / `disabled`). El modo se configura en
    `/admin/ai` (no en este panel). Ver `EP008-ai.md`. El catálogo BYO
    incluye OpenAI / Claude / Gemini / Perplexity / Azure Copilot M365 /
    Custom / Groq. Ollama fue eliminado (BUG-053).
- [ ] Se guarda en `tenants.settings` (JSONB).
- [ ] Cambio de idioma default no afecta preferencia individual de users.

**Test Cases:**
- `TC-108` (integration) — Actualizar `settings.locale` → próximo login muestra UI en ese idioma.
- `TC-109` (integration) — Color primario se refleja en PDF exportado.

---

## US-042 — Logs de auditoría (visible para Admin del tenant)

**Como** Administrador
**Quiero** consultar quién hizo qué cuándo
**Para** forensía y compliance.

**Criterios de aceptación:**
- [ ] `GET /api/v1/admin/audit-logs?action=&user_id=&entity_type=&date_from=&date_to=&cursor=`.
- [ ] Solo ve eventos del **tenant propio** (filtro `tenant_id` en la query; no hay RLS Postgres, ver `architecture/security-multitenant.md`).
- [ ] Incluye `action`, `module`, `entity_type`, `entity_id`, `details`, `ip_address`, `occurred_at`, `user_display`.
- [ ] Export CSV para período.

**Test Cases:**
- `TC-110` (integration) — Admin A no ve eventos de tenant B (TC-MT-006).
- `TC-111` (integration) — Filtros combinados devuelven exacto.

---

## US-043 — Navegación jerárquica del sidebar (SUPERSEDED)

> ⚠️ **Esta US está superseded por US-138** (sidebar capability-based
> con TOP_NAV / ADMIN_NAV / SUPERADMIN_NAV separados; ver
> `components/app-shell.tsx`). El árbol "Organizaciones → Solicitudes /
> Programas / Proyectos → Módulos" se reemplazó por:
>
> - `OrgTreeNav` (drill-down vivo orgs → programas → proyectos), a su vez
>   retirado en US-205: la organización vive en el header.
> - Tabs dentro de `/pmo/projects/[id]/*` (US-035) para los módulos.
> - Items planos en TOP_NAV para Requests, Projects, RAID, Cambios, etc.
> - Las rutas `/admin/projects`, `/admin/programs`, `/admin/raid`, etc.
>   ahora son redirects 301 a `/pmo/*` (US-075 / DEC-022).
> - `/admin/settings` y `/admin/supervision` → redirects a
>   `/admin/tenant?tab={config|stats}` (US-036).
> - `/admin/roles` → redirect a `/admin/permissions`.
>
> El árbol descrito abajo refleja el diseño original. Queda como
> contexto histórico.

**Como** usuario autenticado (cualquier rol)
**Quiero** un sidebar organizado en grupos colapsables con dropdowns anidados
**Para** escanear rápido las áreas de la app y reducir la fricción de navegación.

**Criterios de aceptación:**
- [ ] El sidebar expone **tres grupos top-level** en este orden:
  1. **Tablero** — link directo a `/dashboard`.
  2. **Organizaciones** (dropdown; el label navega a `/admin/organizations`):
     - Solicitudes → `/admin/requests`.
     - Programas → `/admin/programs`.
     - Proyectos (sub-dropdown; label navega a `/admin/projects`):
       - **Módulos de Proyectos** (sub-grupo expandible) con: Riesgos, AIDs, Cambios, Documentos, Lecciones, Minutas, Tareas, Gantt, Minuta IA, Reporte IA.
  3. **Admin** (dropdown):
     - **Panel del Tenant** → `/admin/supervision` (reemplaza el label "Supervisión").
     - Usuarios → `/admin/users`.
     - Roles → `/admin/roles`.
     - Auditoría → `/admin/audit-logs`.
     - Configuración → `/admin/settings`.
- [ ] Los grupos con `href` + `children` actúan como **link + toggle**: clic en el label navega, clic en el chevron (lado derecho) expande/colapsa.
- [ ] **Auto-expand**: al montar el shell o al cambiar `pathname`, las ramas que contienen la ruta activa se expanden automáticamente.
- [ ] Los ítems bajo _Módulos de Proyectos_ resuelven su `href` contra el proyecto en curso cuando la URL calza `/admin/projects/:id/...`; en caso contrario caen al listado `/admin/projects`.
- [ ] El estado activo usa pill de fondo (`--chrome-active`) sin border; cada nivel de anidación agrega `0.75rem` de indent.
- [ ] La sección **Super admin** (Visión general, Tenants, Logs platform, Health) sólo se renderiza si `user.is_superadmin === true` y queda por fuera del árbol principal.
- [ ] Los chevrones tienen `aria-expanded` y labels `aria-label="Expandir/Colapsar <grupo>"`.

**Test Cases:**
- `TC-112` (e2e) — Al entrar a `/admin/users`, el grupo _Admin_ aparece expandido y _Usuarios_ activo; el resto colapsado.
- `TC-113` (e2e) — Al entrar a `/admin/projects/:id/risks`, quedan abiertos _Organizaciones → Proyectos → Módulos de Proyectos_ con _Riesgos_ activo.
- `TC-114` (e2e) — Clic en el label "Organizaciones" navega a `/admin/organizations` **y** expande el grupo; clic en el chevron sólo expande.
- `TC-115` (unit) — `buildNav(pathname)` devuelve hrefs de módulos apuntando al proyecto en curso cuando `pathname` incluye `/admin/projects/:id`.
- `TC-116` (a11y) — Navegación completa con teclado (Tab + Enter sobre chevron) respeta focus ring y `aria-expanded` cambia de estado.

---

## US-221 — Plan de suscripción: límites y consumo ✅ (2026-08-20)

Del artboard «Admin — Plan (suscripción)» de los mockups aprobados el
2026-08-19: «Plan actual: Free / Pro / Enterprise», «Límites y consumo
(organizaciones 1/1 · proyectos 3/3 · usuarios · IA)», y la línea que manda
sobre todo lo demás: **«Solo lectura — sin paywall ni billing en esta fase»**.

**Como** administrador de un inquilino
**Quiero** ver qué límites tiene mi plan y cuánto llevo usado
**Para** saber si me estoy quedando corto antes de que sea un problema.

**Nada de esto bloquea nada, y es el criterio central.** Un límite excedido se
muestra y el inquilino sigue trabajando. El artboard lo dice; convertirlo en un
bloqueo sería cambiar el producto por cuenta propia y dejaría a un cliente cuya
cartera creció fuera de su propia plataforma un viernes por la tarde. Cuando el
bloqueo llegue, la respuesta ya está calculada y solo hará falta decidir **qué**
hacer con ella — que no es una decisión técnica. `enforced: false` viaja en la
respuesta para que quien consuma la API no tenga que leer esto para saberlo.

**Los tres tiers son del artboard; los números no.** `free`, `pro` y
`enterprise` están en el mockup aprobado. Los **topes** de cada uno no aparecen
en ningún documento de este repositorio, así que escribir «pro = 10
organizaciones» habría sido inventar el catálogo comercial en un módulo de
dominio, y habría quedado como si alguien lo hubiera decidido. El tier es una
**etiqueta** y los topes son **datos del inquilino**, que fija el
superadministrador. El día que exista un catálogo, se rellenan desde él y nada
de esto cambia.

**Sin tope declarado no es un tope de cero.** Es MCS DAT-12, y aquí importa más
que en otros sitios: un cero diría «no puedes crear ni una organización», que es
lo contrario de «no hay tope». Se nombran distinto, se pintan distinto, y donde
no hay denominador no se dibuja barra — una barra contra un tope inventado
convierte «no se sabe» en «vas bien».

**El consumo se cuenta, no se guarda.** Un contador almacenado se desincroniza el
día que alguien borra un proyecto por un camino que se olvidó de decrementarlo, y
entonces el plan dice que el inquilino está en el tope cuando no lo está. Misma
razón que la completitud (US-210) y el costo (US-215).

**Sin migración.** Los topes viven en `tenants.settings.plan`, donde ya viven la
moneda preferida, el modo de IA y la cadencia de reporte. Cuatro columnas para lo
mismo obligarían a una migración por cada límite que se añada, y los límites de un
plan comercial son justo lo que cambia.

**Criterios de aceptación:**
- [x] `GET /admin/plan` — el tier, los cuatro recursos con su consumo y su tope,
  y `enforced: false`. Trae los rótulos junto a los datos porque el vocabulario
  vive en el dominio: escribirlos en el frontend los deja divergiendo en cuanto se
  añade un recurso.
- [x] `PUT /superadmin/tenants/{id}/plan` fija tier y topes; `GET
  /superadmin/plan-catalog` sirve el vocabulario del formulario. **Ver es del
  inquilino, escribir del superadministrador**: uno que pudiera subirse el propio
  tope tendría un plan decorativo.
- [x] Un tope se puede **quitar** (`null`), volviendo a «sin límite declarado».
  Sin marcha atrás, un plan mal capturado obligaría a editar el JSON a mano.
- [x] Un tope de **cero** es válido —«este plan no incluye esto»— y se trata sin
  dividir por él.
- [x] Un valor negativo, no numérico o con clave desconocida se **descarta** y
  queda como «sin declarar», que es la verdad, en vez de caer a cero.
- [x] Un tier desconocido cae al por defecto en vez de propagarse: `settings` lo
  edita una persona y una errata no debe dejar la pantalla sin nada que decir. El
  por defecto es `free`, el más bajo — equivocarse hacia abajo se ve porque el
  inquilino pregunta, y hacia arriba no, porque nadie reporta que le sobran
  permisos.
- [x] El consumo de IA se cuenta por **mes calendario** y no por ventana móvil: es
  lo que dice el artboard y lo que espera quien lee una factura. Una ventana daría
  un número que baja sin que nadie haya hecho nada.
- [x] Las organizaciones inactivas, los proyectos borrados y las cuentas
  desactivadas **no cuentan**: cobrar por algo que no se puede usar es un defecto,
  y desactivar una cuenta libera su lugar, que es lo que espera quien la desactiva
  para dar de alta a otra persona.
- [x] `undeclared_limits` viaja con el resto. «Todo dentro del plan» con cuatro
  topes sin declarar no significa nada, y quien lo lee tiene que poder distinguir
  las dos situaciones.
- [x] Cada recurso nombra la **consecuencia** de pasarse. «Excedido» sin decir qué
  pasa no es accionable.

**Tests (`tests/test_us221_plan_suscripcion.py`, 19):**
- `TC-221.1` — La regla sin base de datos (MCS DEV-02, 10 casos): los tres tiers,
  tier desconocido al default, sin tope ≠ cero, los tres estados frente a un tope,
  tope de cero sin división, límites negativos o no numéricos descartados, clave
  desconocida ignorada, se recorren los recursos y no el consumo, `hay_algo_fuera`,
  el mes calendario.
- `TC-221.2` — Contra la API (9 casos): un inquilino sin plan lo dice; el consumo
  se cuenta de lo que hay; borrar un proyecto lo baja; el superadministrador fija
  tier y topes; un tope se puede quitar; **pasarse del tope se muestra y no
  bloquea** —tres proyectos con tope de uno, los tres se crean—; un administrador
  de inquilino no puede fijar su propio plan (403); el catálogo lo sirve el
  backend; un tier inválido se rechaza en la frontera (422).

**Lo que queda fuera, dicho a propósito:** el formulario del superadministrador
para fijar el plan desde la interfaz. El endpoint existe y el catálogo también; la
pantalla de plataforma es trabajo de `superadmin_panel` y no de esta US, que era
la vista del inquilino. Y el paywall, que el artboard excluye explícitamente.

**Estado de integración:** DONE (US-221).

---

## Notas técnicas

- Panel admin es una ruta protegida `/admin` en Next.js con `middleware.ts` que verifica permiso.
- Bulk actions usan endpoints que aceptan arrays, con validación de tamaño máx (100).
- Logs de auditoría usan cursor pagination por performance (tabla grande).

### Endpoints

> Corregido 2026-08-29: `admin_users.py` no tiene `bulk` ni `impersonate` (no
> hay impersonate en ningún endpoint de `admin`). Los bulk reales viven en
> `admin_panel.py`. `GET`/`POST /admin/roles` (CRUD) no existen — se borraron
> en US-077 (ver US-038) —; `duplicate`/`impact` siguen en el backend pero sin
> UI que los llame.

```
GET    /api/v1/admin/users
POST   /api/v1/admin/users/bulk/assign-role      (admin_panel.py, ~línea 42)
POST   /api/v1/admin/users/bulk/deactivate       (admin_panel.py, ~línea 86)

POST   /api/v1/admin/roles/{id}/duplicate        (admin_panel.py; sin UI que lo llame)
GET    /api/v1/admin/roles/{id}/impact           (ídem; preview de afectados)

GET    /api/v1/admin/organizations
GET    /api/v1/admin/projects                    (bypass member filter)

GET    /api/v1/admin/settings
PATCH  /api/v1/admin/settings
POST   /api/v1/admin/settings/logo

GET    /api/v1/admin/audit-logs
GET    /api/v1/admin/audit-logs/export.csv

GET    /api/v1/admin/plan                        (US-221, solo lectura)
PUT    /api/v1/superadmin/tenants/{id}/plan      (US-221, fija tier y topes)
GET    /api/v1/superadmin/plan-catalog           (US-221, vocabulario)
```

---

## Definition of Done

- [ ] Panel accesible en `/admin` con sidebar de dropdowns anidados (ver US-043): _Admin_ agrupa Panel del Tenant, Usuarios, Roles, Auditoría, Configuración; _Organizaciones_ agrupa Solicitudes, Programas y Proyectos → Módulos.
- [ ] Bulk actions probadas con 100 elementos sin degradar performance.
- [ ] TC-MT-005 (admin A no gestiona B) y TC-MT-006 (logs aislados) verdes.
- [ ] UI elegante con tablas densas estilo macOS Finder (ver design system).

---

## # PENDING — User Stories nuevas

### US-023 — Gestión de Tenant (acciones propuestas)

**Como** Admin / Senior PMO
**Quiero** un panel para ver y editar la información de mi tenant
**Para** mantener identidad y conocer uso sin depender de super admin.

**Criterios de aceptación:**
- [x] `GET /api/v1/admin/tenant` devuelve: id, slug, name, logo_url,
  is_active, plan, settings y stats (active_users, total_users,
  total_organizations, total_projects, storage_bytes).
- [x] `PATCH /api/v1/admin/tenant` permite actualizar `name` y `logo_url`.
  Rechaza nombres < 2 caracteres. Ignora `slug` silenciosamente
  (solo super admin lo cambia).
- [x] Página `/admin/tenant`:
  - Tarjeta con logo, nombre (editable), slug (readonly).
  - Tarjeta de plan actual con link "Contactar soporte".
  - Stats: usuarios activos, organizaciones, proyectos, storage humano.
  - Link a `/admin/settings` para idioma, moneda, timezone, IA.
- [x] Storage calculado sumando `documents.size_bytes` current.
- [x] Entrada "Mi tenant" agregada al nodo Admin del sidebar.

**Test Cases:**
- `test_usnew023_get_tenant_info_with_stats` ✅
- `test_usnew023_patch_tenant_name_and_logo` ✅
- `test_usnew023_patch_ignores_slug` ✅
- `test_usnew023_patch_name_too_short` → 422 ✅

**Estado de integración:** DONE (US-023).

---

### US-024 — Gestión jerarquía org completa (BU + Depto) en Admin ⛔ RETIRADA (ADR-037)

> **Entregada el 2026-05, retirada el 2026-08-19.** La pantalla existió y
> funcionaba; lo que se retiró son los dos niveles que administraba. ADR-037
> reemplazó unidad de negocio y departamento —que modelaban el organigrama del
> cliente— por el portafolio, que agrupa por decisión de inversión. Los endpoints
> que esta US reutilizaba (US-003/004) responden 404 desde US-199.
>
> **Lo que hace hoy esa pantalla:** la sección de jerarquía es
> `org-hierarchy-section.tsx`, un acordeón **Portafolio ⊃ Programa** con alta,
> edición, archivado con cascada opcional y papelera de dos pasos en los dos
> niveles (**US-200**, ver EP002).
>
> Los AC de abajo se conservan como registro de lo que se entregó.

**Criterios de aceptación (histórico):**
- [x] En `/admin/organizations/{id}`, debajo del formulario de edición
  de la org, se muestra sección "Jerarquía: unidades de negocio y
  departamentos" con tree expandible.
- [x] Tree Org → BUs → Deptos con acciones inline por fila:
  - "Nuevo departamento" (solo en filas de BU).
  - "Editar" (abre modal de nombre + descripción).
  - "Desactivar" (modal con toggle `force` para cascada).
- [x] Botón "Nueva BU" en el header de la sección.
- [x] Botón "Ver proyectos" en el header de la sección → filtra
  `/admin/projects?organization_id={id}`.
- [x] Deptos se cargan lazy al expandir la BU.
- [x] Reutiliza los endpoints existentes (US-003/004); sin cambios
  de backend.

**Notas:**
- Modal de desactivar muestra el mensaje `BU_HAS_ACTIVE_DEPARTMENTS` o
  `DEPT_HAS_ACTIVE_CHILDREN` cuando aplica, y sugiere el toggle force.

**Estado de integración:** DONE (US-024) y luego RETIRADA (ADR-037 / US-199); la sustituye US-200.
