---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-29
revisar_cada: 90d
---

# EP001 — Login y Gestión de Usuarios

| Campo | Valor |
|---|---|
| **ID** | EP001 |
| **Prioridad** | Alta (fundacional) |
| **Dependencias** | — |
| **Módulo** | `auth`, `admin.users` |
| **Estado** | v1.5 (Sprint 6 — refactor capability-based) |
| **Versión objetivo** | v1.5 |

## Modelo actual (post-Sprint 6 / DEC-024)

> **Reescritura parcial 2026-04-25.** El modelo de permisos cambió de
> matriz `(role × module × action)` a **capability-based**. Las
> secciones "User Stories" e "Implementación" de abajo quedan como
> referencia histórica del diseño v1.0. El comportamiento productivo
> real lo define esta sección.

### Roles fijos (DEC-020 + DEC-024)

| `role_type` | Descripción |
|---|---|
| `admin` | Tiene 5 capabilities adicionales sobre `user`. |
| `pm_sr` | Equivalente a `admin` en capabilities vía `_ADMIN_EQUIVALENT_ROLES` (`core/permissions.py`); sin el constraint de unicidad que sí aplica a `admin`. |
| `user`  | Default. Hace casi todo en el tenant. |

`viewer` se **eliminó** en Sprint 6 (migración 0028). Los registros
residuales se normalizaron a `user`. Las tablas `roles` y
`user_roles` quedaron *deprecated*; su borrado físico es US-081
(Sprint 7).

### 5 capabilities del admin (DEC-024)

| Capability | Cubre |
|---|---|
| `tenant.manage`         | Branding, settings, configuración del tenant |
| `ai.configure`          | Proveedores y modos de IA |
| `users.manage`          | 10 acciones admin→user (alta/edición/reset/desactivación/asignación rol/membership orgs/auditoría/desbloqueo/soft-delete/forzar password) |
| `organizations.delete`  | Solo eliminar orgs. Crear/editar lo hace cualquier user |
| `audit.read`            | Ver audit log del tenant |

**Todo lo demás** (proyectos, tareas, riesgos, issues, change_requests,
documentos, minutas, lecciones, áreas, dashboard, IA generación,
project_requests, charters, reports, scheduled reports, importación
de planes, organizaciones crear/editar) es de cualquier user
autenticado del tenant. No hay granularidad CRUD por módulo.

### Flujo del gate

```
request → get_current_user → CurrentUser
                                  │
              role_type ∈ {admin,pm_sr,user} + is_superadmin
                                  │
                                  ▼
       require_capability("X")  →  cu.has_capability("X")
                                       │
                              ┌────────┴────────┐
                              ▼                 ▼
                        is_superadmin?    capability ∈
                              │           capabilities_for(role_type)?
                              │ + override de tenant (DEC-021)
                              ▼
                          True/False
```

Implementación: `app/core/permissions.py` (mapping estático),
`app/api/deps.py` (`CurrentUser.has_capability`, `require_capability`,
`require_authenticated`).

### Test de regresión (US-079)

`apps/api/tests/test_permission_matrix.py` clasifica cada APIRoute
en una de 8 categorías. Falla si aparece un endpoint con un gate no
reconocido. Esto previene la causa raíz de DEC-024 (strings huérfanos
en el mapping). El marker `pytest -m permissions` corre aislado.

### UI

- **`/admin/permissions`** — página informativa read-only con las
  5 capabilities. El footer remite al superadmin para overrides
  (DEC-021).
- **`/admin/users` + `/admin/users/[id]`** — CRUD de users con select
  `role_type`, sección "Acceso a organizaciones" (modelo opt-out,
  default todas marcadas) y los 10 botones de acciones admin→user.
- **`/admin/roles`** y `role-editor.tsx` **eliminados en Sprint 6**.
  Redirect 301 → `/admin/permissions`.

### Modelo de datos efectivo

- `users.role_type: VARCHAR(16)` ∈ {`admin`, `pm_sr`, `user`} — `pm_sr` es
  equivalente a `admin` para efectos de capacidades
  (`_ADMIN_EQUIVALENT_ROLES`, `core/permissions.py`).
- `tenant_role_permission_overrides` (US-073, DEC-021): vocabulario
  de overrides ahora es `capability` en `module` y `"grant"` en
  `action`. Solo el superadmin escribe aquí.
- `organization_user_exclusions` (US-078, opt-out membership): vacío
  por default: user accede a todas las orgs del tenant.

---

## Objetivo de negocio (v1.0, histórico)

Los usuarios del tenant se autentican de forma segura. Los roles
tienen permisos granulares por módulo. Cada acción queda trazada: se
sabe quién hizo qué.

## Roles involucrados

- **Super Admin** (platform-wide) — gestiona cuentas fundacionales.
- **Administrador** del tenant — CRUD de usuarios/roles del tenant.
- **Usuario final** — cualquier rol que se autentica.

---

## User Stories

### US-001 — Crear usuario

**Como** Administrador
**Quiero** crear un usuario con username único, email válido y rol(es)
**Para** que acceda al sistema con las capacidades correctas.

**Criterios de aceptación:**
- [ ] Campos obligatorios: `full_name`, `username`, `email`, `password`, `role_ids[]`.
- [ ] `username` y `email` son únicos por tenant (`citext`).
- [x] `password` cumple política (`core/security.py:validate_password_policy`): **min 8 chars**, 1 mayúscula, 1 dígito, 1 símbolo (set fijo), y no está en la blocklist de contraseñas filtradas (~23,000 entradas vía `esta_filtrada`, ASVS 2.1.7). Sin requisito de lowercase.
- [ ] Hash `bcrypt rounds=12` al guardar.
- [ ] La response no expone `password_hash`.
- [ ] Crea registro `audit_log` con `action='user.create'`.
- [ ] Endpoint: `POST /api/v1/admin/users` (capability `users.manage`, ver DEC-024).
- [ ] Al crear, retorna `201 Created` con el `UserOut`.

**Test Cases:**
- `TC-001` (unit) — Política de password: cadenas débiles (`"password123"`, `"Aa1!"`) → `VALIDATION_ERROR`.
- `TC-002` (integration) — POST con email duplicado → `409 CONFLICT`.
- `TC-003` (integration) — Happy path → 201, hash correcto, audit log escrito.
- `TC-004` (E2E) — Admin crea user → user hace login inmediato.

---

### US-002 — Login con username o email

**Como** usuario registrado
**Quiero** iniciar sesión con username o email + password
**Para** acceder a mi espacio de trabajo.

**Criterios de aceptación:**
- [ ] `POST /api/v1/auth/login` acepta `{identifier, password}` (identifier = username o email).
- [ ] Credenciales válidas: retorna `{access_token, refresh_token (cookie), user, tenants[]}`.
- [ ] Credenciales inválidas: incrementa `failed_login_attempts`, audita y retorna `401 UNAUTHENTICATED`.
- [ ] Mensaje genérico "Credenciales inválidas" (no revela si user existe).
- [ ] JWT incluye `sub`, `tenant_ids[]`, `active_tenant_id`, `is_superadmin`, `roles[]`.
- [ ] Al éxito: `last_login = now()`, `failed_login_attempts = 0`.
- [ ] Audita `login_success` o `login_failed` con IP y user agent.

**Test Cases:**
- `TC-005` (integration) — Login con username ok → 200, JWT válido.
- `TC-006` (integration) — Login con email ok → 200.
- `TC-007` (integration) — Password mal → 401, `failed_login_attempts` +1.
- `TC-008` (integration) — User inactivo → 403 `FORBIDDEN`.
- `TC-009` (E2E) — Login desde UI, la navegación persiste.

---

### US-003 — Bloqueo tras 5 intentos fallidos

**Como** Administrador de seguridad
**Quiero** bloquear la cuenta 15 min tras 5 fallos consecutivos
**Para** mitigar ataques de fuerza bruta.

**Criterios de aceptación:**
- [ ] 5º intento fallido: `locked_until = now() + 15min`.
- [ ] Login posterior (aun con pwd correcto) da `403 ACCOUNT_LOCKED` mientras `locked_until > now()`.
- [ ] Al expirar bloqueo, user puede intentar nuevamente.
- [ ] Login exitoso resetea `failed_login_attempts = 0` y `locked_until = null`.
- [ ] Audita `account_locked` con detalle.
- [ ] Admin puede desbloquear manualmente: `POST /admin/users/{id}/unlock`.

**Test Cases:**
- `TC-010` (integration) — 5 fails consecutivos → 6º intento 403 aun con pwd bueno.
- `TC-011` (integration) — Tras 15 min (mock clock), login permite nuevamente.
- `TC-012` (integration) — Admin unlock → `locked_until = null`.

---

### US-004 — Cambio de contraseña propia

**Como** usuario autenticado
**Quiero** cambiar mi contraseña
**Para** mantener seguridad.

**Criterios de aceptación:**
- [ ] `POST /api/v1/auth/change-password` con `{current_password, new_password}`.
- [ ] Verifica `current_password`; si mal → `401`.
- [ ] `new_password` distinto al actual, cumple política.
- [ ] Invalida todos los refresh tokens vigentes (fuerza re-login en otros dispositivos).
- [ ] Audita `password_change`.

**Test Cases:**
- `TC-013` (integration) — Happy path → 204, refresh tokens viejos invalidados.
- `TC-014` (integration) — Password nueva = actual → 422 `BUSINESS_RULE`.
- `TC-015` (integration) — Password nueva débil → 400 `VALIDATION_ERROR`.

---

### US-005 — Reset de contraseña por Admin

**Como** Administrador
**Quiero** resetear la contraseña de cualquier user de mi tenant
**Para** desbloquear a usuarios que la olvidaron.

**Criterios de aceptación:**
- [ ] `POST /admin/users/{id}/reset-password` genera password temporal y la devuelve en claro una sola vez en la response.
- [ ] Marca `must_change_password = true` en el user.
- [ ] En el próximo login, redirige a pantalla forzada de cambio.
- [ ] Admin de tenant A no puede resetear user de tenant B (`TC-MT-005`).
- [ ] Superadmin puede resetear de cualquier tenant.
- [ ] Audita `password_reset_by_admin`.

**Test Cases:**
- `TC-016` (integration) — Admin resetea → password temp devuelta, user debe cambiarla.
- `TC-MT-005` (integration) — Admin A resetea user B → `403 FORBIDDEN`.

---

### US-006 — Asignar roles y permisos

**Como** Administrador
**Quiero** crear roles con matriz de permisos por módulo
**Para** controlar qué puede hacer cada perfil.

**Criterios de aceptación:**
- [ ] `POST /api/v1/admin/roles` con `{name, description, permissions}`.
- [ ] `permissions` es objeto `{module: [actions…]}`.
- [ ] Módulos válidos: `projects`, `risks`, `issues`, `change_requests`, `documents`, `lessons`, `minutes`, `admin.users`, `admin.roles`, `admin.organizations`, `admin.projects`, `ai.generate`.
- [ ] Acciones válidas: `read`, `create`, `update`, `delete`, `approve`, `upload`, `minute`, `report`.
- [ ] Roles sistema (`is_system=true`) no se pueden borrar.
- [ ] Al modificar permisos, el cambio aplica de inmediato a los users con ese rol.
- [ ] UI muestra preview "¿A quiénes afecta?" antes de guardar.

**Test Cases:**
- `TC-017` (unit) — Validar módulos/acciones permitidas.
- `TC-018` (integration) — Borrar rol `is_system` → 403.
- `TC-019` (integration) — Modificar rol → user activo ve permisos nuevos en próxima request.
- `TC-020` (E2E) — Matriz de checkboxes en UI guarda JSON correcto.

---

### US-007 — Listar y buscar usuarios

**Como** Administrador
**Quiero** ver lista de usuarios con búsqueda y filtros
**Para** gestionar mi equipo.

**Criterios de aceptación:**
- [ ] `GET /api/v1/admin/users?q=&role_id=&is_active=&page=&limit=`.
- [ ] Búsqueda fuzzy (`pg_trgm`) en `full_name`, `username`, `email`.
- [ ] Filtro `is_active=true|false`.
- [ ] Paginación estándar.
- [ ] Response incluye: id, full_name, username, email, roles[], is_active, last_login.

**Test Cases:**
- `TC-021` (integration) — Búsqueda parcial "juan" encuentra "Juan Pérez".
- `TC-022` (integration) — Filtro `is_active=false` solo lista desactivados.

---

### US-013 — Menú de usuario en el topbar

**Como** usuario autenticado
**Quiero** ver mi identidad y cerrar sesión desde cualquier pantalla
**Para** controlar mi sesión sin abandonar el contexto actual.

**Criterios de aceptación:**
- [ ] El chrome (sidebar + topbar) usa el azul marino `#0E164F` definido en
      `docs/design-system/style.md`.
- [ ] El sidebar **no** tiene footer con datos del usuario; su única
      función es navegación.
- [ ] En la esquina superior derecha del topbar vive un componente
      `UserMenu`:
  - **Trigger**: avatar (iniciales derivadas de `full_name` / `username` /
    `email`) + nombre truncado + chevron. Altura 36 px, radius `md`.
  - **Dropdown** (256 px de ancho): avatar 36 px, nombre completo, email,
    chips con roles visibles o badge "Super admin" cuando aplica, separador
    y botón `Cerrar sesión`.
- [ ] Cerrar sesión invoca `POST /api/v1/auth/logout`, limpia `localStorage`
      (`access_token`, `user`, `active_tenant_id`) y redirige a `/login`.
- [ ] El dropdown se cierra con click fuera, tecla `Esc` o al seleccionar
      una opción.
- [ ] Accesibilidad: `aria-haspopup="menu"`, `aria-expanded`, `role="menu"`
      y `role="menuitem"` en las opciones; focus visible.

**Test Cases:**
- `TC-023` (E2E) — Click en avatar abre dropdown con nombre/email/roles.
- `TC-024` (E2E) — Click en "Cerrar sesión" limpia token y redirige a `/login`.
- `TC-025` (E2E) — `Esc` cierra el dropdown; click afuera lo cierra.
- `TC-026` (unit) — Las iniciales se calculan de `full_name` (primeras
  dos palabras, en mayúsculas).

---

### Bloqueo por inactividad (ENH-160)

**Como** usuario autenticado
**Quiero** que tras un período de inactividad la app se bloquee y pida
re-iniciar sesión, en vez de cerrarla y mandarme a `/login`
**Para** no perder el contexto ni el progreso del trabajo en curso.

**Comportamiento:**
- Tras **15 min sin actividad** (`mousedown`, `keydown`, `scroll`,
  `touchstart`) en cualquier ruta autenticada, la app entra en estado
  **bloqueado**.
- El contenido autenticado se muestra con **blur** y queda no interactivo
  (`pointer-events: none` + `inert`). Se monta un overlay **no descartable**
  (sin `Esc`, sin click-fuera, sin botón de cierre) que pide re-autenticar.
- El overlay **pre-rellena** la cuenta (email/username) de la sesión actual en
  modo solo-lectura; el usuario solo ingresa su **contraseña**.
- Al re-autenticar correctamente, el overlay se cierra y el usuario sigue
  en **la misma ruta y con el mismo estado en memoria**. No hay redirect ni
  reload, así que no se pierde progreso (p. ej. formularios sin guardar).
- El **tenant activo** se preserva a través del re-login: si el contexto tenía
  un tenant distinto al default del usuario y sigue siendo válido, se restaura.
- Escape hatch: botón **"Cerrar sesión"** dentro del overlay que invoca
  `POST /api/v1/auth/logout`, limpia `localStorage` y redirige a `/login`.
- Mientras está bloqueado, la actividad del usuario **no** re-arma el timer; el
  desbloqueo es exclusivamente vía re-login. Tras desbloquear, el timer de 15
  min se re-arma.

**Implementación:** `apps/web/hooks/use-inactivity-lock.ts` (timer + estado
`locked`) + `apps/web/components/inactivity-lock.tsx` (blur + overlay de
re-login), cableado en `components/require-auth.tsx`. Reemplaza al anterior
`use-inactivity-logout.ts` (logout duro + redirect).

**Test Cases:**
- `TC-027` (E2E) — Tras 15 min idle, el contenido se ve con blur y aparece el
  overlay de re-login (no hay redirect a `/login`).
- `TC-028` (E2E) — Re-login correcto cierra el overlay sin cambiar de ruta ni
  recargar.
- `TC-029` (manual) — El tenant activo se conserva tras el re-login.

_Actualizado 2026-06-25 (ENH-160)._

---

## Notas técnicas

### Modelos de BD involucrados

- `users`, `roles`, `user_roles`
- `audit_log`

Detalle en [`../architecture/database.md`](../architecture/database.md).

### Endpoints

```
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/change-password
POST   /api/v1/auth/switch-tenant

GET    /api/v1/admin/users
POST   /api/v1/admin/users
GET    /api/v1/admin/users/{id}
PATCH  /api/v1/admin/users/{id}
DELETE /api/v1/admin/users/{id}                      (soft)
POST   /api/v1/admin/users/{id}/reset-password
POST   /api/v1/admin/users/{id}/unlock
```

### Dependencias de librerías

- `python-jose[cryptography]` — JWT.
- `passlib[bcrypt]` — hashing.
- `pydantic[email]` — validación email.
- Frontend: `next-auth` + provider custom que habla con nuestro `/auth/login`.

---

## Definition of Done

- [ ] Todas las US cubiertas por tests.
- [ ] TC-MT-001, TC-MT-005, TC-MT-006 verdes.
- [ ] Endpoints documentados en OpenAPI.
- [ ] Cliente TS generado en `packages/sdk`.
- [ ] UI accesible (WCAG AA en formularios login/admin).
- [ ] Audit log cubre las 7 acciones anteriores.
- [ ] Seed inicial crea roles sistema: `Administrador`, `PMO Manager`, `Project Manager`, `Viewer`.
- [ ] Runbook "crear primer superadmin" en `docs/` interno.

---

## # PENDING — User Stories nuevas

### US-007 — Toggle dark/light mode en dropdown de usuario

**Como** usuario autenticado
**Quiero** cambiar entre modo oscuro y claro desde el menú de usuario
**Para** elegir mi preferencia visual.

**Criterios de aceptación:**
- [x] Dropdown de usuario incluye radio group con 3 opciones (Claro / Oscuro / Sistema) + iconos Sun/Moon/Monitor.
- [x] Default: `prefers-color-scheme` del sistema.
- [x] Preferencia guardada en `users.preferences JSON → { "theme": "dark"|"light"|"system" }`.
- [x] Cambio aplica de inmediato, sin reload, sin FOUT (script inline en `<head>`).
- [x] `GET /api/v1/users/me/preferences` y `PATCH /api/v1/users/me/preferences`.
- [x] Cliente TS en `lib/api/users.ts` + `ThemeProvider`.

**Test Cases:**
- `TC-NEW-013` (integration) — Preferencia persiste entre sesiones ✅
- `TC-NEW-013b` (integration) — theme inválido → 422 ✅

**Estado de integración:** DONE (US-007).

---

### US-008 — Toggle de idioma en dropdown de usuario

**Como** usuario autenticado
**Quiero** cambiar el idioma de la interfaz entre Español y English
**Para** operar en mi idioma preferido.

**Criterios de aceptación:**
- [x] Dropdown de usuario incluye selector de idioma con banderas 🇲🇽/🇺🇸.
- [x] Preferencia guardada en `users.preferences.locale` (reutiliza `PATCH /users/me/preferences`).
- [x] Cambio actualiza `<html lang>` y persiste en `localStorage`.
- [x] También escribe `users.locale` para compatibilidad con código existente.
- [x] Cliente: `LocaleProvider` con hook `useLocale()`.

**Notas:**
- La traducción visible del UI (strings) queda fuera del alcance de esta US.
  Esta US solo persiste la preferencia y la expone globalmente. El i18n
  routing completo (Next.js `[locale]` segments) es post-MVP.

**Estado de integración:** DONE (US-008).

---

### US-009 — Página administrar cuenta (perfil + cambiar password)

**Como** usuario autenticado
**Quiero** editar mis datos personales y cambiar mi contraseña
**Para** mantener mi perfil actualizado.

**Criterios de aceptación:**
- [x] Opción "Administrar cuenta" en dropdown de usuario → navega a `/account`.
- [x] Página con dos secciones:
  - **Detalles personales**: `full_name` editable, `email` readonly (cambio requiere verificación, post-MVP).
  - **Cambiar contraseña**: current + new + confirm (mismos criterios que US-004).
- [x] `GET /api/v1/users/me` — obtiene perfil.
- [x] `PATCH /api/v1/users/me` — actualiza `full_name` (audit log).
- [x] Al guardar, actualiza `StoredUser` en localStorage; topbar muestra nuevo nombre sin reload.
- [ ] Upload de avatar (PNG/JPG ≤ 2 MB): pospuesto a iteración siguiente (requiere infra de upload).
- [ ] `phone` opcional: pospuesto (agregar columna a users).

**Test Cases:**
- `TC-NEW-015` (integration) — PATCH /users/me actualiza full_name ✅
- `TC-NEW-015b` (integration) — full_name < 2 chars → 422 ✅

**Estado de integración:** DONE (US-009), con avatar/phone como trabajo
de seguimiento.

### US-010 — Color chrome #182e4e + Senior PMO como admin

**Como** desarrollador
**Quiero** el color de chrome correcto y Senior PMO con capacidades admin
**Para** cumplir DEC-005 y DEC-006.

**Criterios de aceptación:**
- [x] Variable CSS `--chrome-bg` = `#182e4e` en `globals.css` (DEC-006).
- [x] Variables derivadas (`--chrome-border`, `--chrome-hover`, `--chrome-active`)
  recalibradas al nuevo matiz.
- [x] `docs/design-system/style.md` actualizado al nuevo color.
- [x] Rol `PMO Manager` en seed incluye todos los permisos `admin.*` que
  tiene `Administrador` (DEC-005).
- [x] `CurrentUser.is_admin_equivalent` disponible como helper.
- [x] Middleware existente (`require_permission`) sigue funcionando sin
  cambios — Senior PMO tiene los permisos `admin.*` en su rol.

**Test Cases:**
- `TC-NEW-017` (E2E) — Chrome #182e4e visible en light y dark mode ✅ (CSS).
- `TC-NEW-018` (integration) — Senior PMO accede a `/admin/users` ✅.
- `is_admin_equivalent` helper cubierto por test unitario ✅.

**Estado de integración:** DONE (US-010).

---

### US-214 / AM-16 — Membresía multi-inquilino y selector de inquilino ✅ (2026-08-20)

Del artboard «Header — contexto tenant/org» de los mockups aprobados el
2026-08-19: «Switcher de tenant — visible solo con más de una membresía. Cambiar
re-emite la sesión y recarga la aplicación en el tenant elegido.»

**Como** consultor que trabaja para dos clientes
**Quiero** cambiar de inquilino sin cerrar sesión
**Para** no tener dos cuentas y dos contraseñas para el mismo trabajo.

**Esta US es un cambio de seguridad antes que de modelo, y por eso el análisis de
amenazas se escribió primero** (CLAUDE.md §0.3). Está en el modelo como **AM-16**.

**El defecto que cierra.** Hasta aquí el cambio de inquilino se autorizaba contra
el claim `tenant_ids` del JWT: `switch_tenant` comprobaba
`body.tenant_id in cu.tenant_ids`, y esa lista sale de `payload.get("tenant_ids")`.
Con un inquilino por usuario la lista era de un elemento y el defecto no tenía
consecuencia. Con dos, **revocar una membresía no surte efecto hasta que el token
caduca** — una hora—. El caso concreto: un consultor externo termina con un
cliente, el administrador le quita la membresía, y sigue viendo su cartera durante
sesenta minutos.

**Los dos controles, y los dos van contra la tabla:**

1. `POST /auth/switch-tenant` resuelve la membresía en la base antes de emitir el
   token nuevo, y **rearma los claims desde la tabla** en vez de copiarlos del
   token viejo.
2. `get_current_user` comprueba en **cada petición** que el inquilino activo sigue
   siendo una membresía viva. Sin esto, el punto 1 solo cubre el instante del
   cambio.

El precio del segundo es una consulta por petición autenticada, por un índice
compuesto. Es el precio de que revocar signifique revocar: sin ella la ventana de
una hora existe por diseño y no hay control que la cierre.

**La membresía de origen se crea con el usuario, desde el modelo.** Los usuarios
se crean por cinco caminos —alta de administrador, alta de inquilino del
superadministrador, dos siembras y las factorías de prueba— y la comprobación de
cada petición deja fuera a quien no tenga membresía. Una regla que hay que
recordar en cinco sitios se olvida en el sexto, así que vive en un
`after_insert` del modelo, igual que `normalizar_hito` vive en el modelo de
tareas y por la misma razón.

**Conceder membresía es del superadministrador (FC-4), no del administrador de
inquilino.** El inquilino es la frontera de aislamiento del producto; un
administrador que pudiera añadir a alguien a otro inquilino podría concederse a sí
mismo acceso a los datos de otro cliente, que es exactamente lo que la frontera
existe para impedir.

**`users.tenant_id` no desaparece.** Sigue siendo el inquilino de origen: dónde se
creó la cuenta y quién la administra. Retirarlo obligaría a reescribir toda
consulta que hoy lo use para resolver el inquilino por defecto, y a decidir qué
pasa con un usuario cuya única membresía se revoca. La membresía **añade**
inquilinos.

**Criterios de aceptación:**
- [x] Tabla `user_tenant_memberships` con unicidad `(user_id, tenant_id)` sin
  importar el estado: dos filas para la misma pareja obligarían a decidir cuál
  manda cada vez que se lee. Migración `0115`, que **siembra** el inquilino de
  origen de cada usuario existente.
- [x] Revocar **marca** `revoked_at`, no borra la fila. «¿Quién tuvo acceso a este
  cliente y cuándo se le quitó?» no se contesta con una fila borrada, y es la
  pregunta de una auditoría.
- [x] Conceder sobre una membresía revocada la **reactiva** en vez de crear otra
  fila.
- [x] `GET /auth/my-tenants` — la lista para el selector, de la tabla, con el
  conteo de organizaciones que el artboard pinta en cada fila.
- [x] `POST /superadmin/memberships` y `DELETE /superadmin/memberships` para
  conceder y revocar; `GET /superadmin/users/{id}/tenants` para ver las de una
  persona. Las dos escrituras quedan en la auditoría.
- [x] **No se puede revocar el inquilino de origen**: dejaría la cuenta sin
  ningún sitio donde entrar, que es una baja disfrazada de cambio de permiso. Para
  dar de baja está `is_active`, que dice lo que hace.
- [x] **A un superadministrador no se le conceden membresías**: le darían el mismo
  acceso que «entrar como administrador» sin el rastro de auditoría que esa
  operación deja (AM-06).
- [x] El selector se pinta **solo con más de una membresía**. Un desplegable de un
  elemento es un control que no hace nada, en el sitio más caro de la pantalla.
- [x] Cambiar de inquilino **recarga la aplicación**. A diferencia del selector de
  organización —que solo cambia un filtro—, cambiar de inquilino cambia las
  organizaciones, los proyectos, el catálogo de personas, la marca, la moneda y
  los permisos. Re-consultar pantalla por pantalla dejaría media interfaz con
  datos del inquilino anterior, y esa mezcla es peor que una recarga.
- [x] La recarga aterriza en `/dashboard` y no en la ruta actual: la actual puede
  ser el detalle de un proyecto que en el inquilino nuevo no existe, y un 404 tras
  cambiar de cliente se lee como que el cambio falló.
- [x] El selector va **antes** del de organización: leídos de izquierda a derecha
  dicen «este cliente, esta organización suya».

**Tests (`tests/test_us214_multi_tenant.py`, 15):**
- `TC-214.1` — La membresía de origen nace con el usuario; un superadministrador
  no gana ninguna inventada.
- `TC-214.2` — Conceder, listar ordenado, conceder dos veces sin duplicar,
  revocar y reactivar reusando la fila, una revocada no aparece en el selector.
- `TC-214.3` — El login trae los dos inquilinos y aterriza en el de origen; el
  cambio funciona; sin membresía da 403; **revocar surte efecto en la siguiente
  petición con el mismo token** —el test que justifica la consulta por
  petición—; y el claim del token no autoriza por sí mismo.
- `TC-214.4` — Un administrador de inquilino no puede conceder (403); el
  superadministrador concede, lista y revoca; el inquilino de origen no se puede
  revocar; a un superadministrador no se le conceden membresías.

**Lo que queda del artboard:** la etiqueta de plan («Plan Pro · 3
organizaciones») que el mockup pinta junto a cada inquilino. El conteo de
organizaciones ya va; el plan es US-221 y no se inventa aquí.

**Estado de integración:** DONE (US-214).

