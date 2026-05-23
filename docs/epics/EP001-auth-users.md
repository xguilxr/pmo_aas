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

> **Reescritura parcial 2026-04-25.** El modelo de permisos pasó de
> matriz `(role × module × action)` a **capability-based**. Las
> secciones "User Stories" e "Implementación" abajo conservan el
> diseño v1.0 como referencia histórica; el comportamiento real
> productivo lo manda esta sección.

### Roles fijos (DEC-020 + DEC-024)

| `role_type` | Descripción |
|---|---|
| `admin` | Tiene 5 capabilities adicionales sobre `user`. |
| `user`  | Default. Hace casi todo en el tenant. |

`viewer` fue **eliminado** en Sprint 6 (migración 0028). Cualquier
registro residual se normalizó a `user`. La tabla `roles` y
`user_roles` quedaron *deprecated* — borrado físico → US-081
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
de planes, organizaciones crear/editar) → cualquier user autenticado
del tenant. Sin granularidad CRUD por módulo.

### Flujo del gate

```
request → get_current_user → CurrentUser
                                  │
              role_type ∈ {admin,user} + is_superadmin
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
en una de 8 categorías y falla si aparece un endpoint con un gate no
reconocido. Esto previene la causa raíz de DEC-024 (strings huérfanos
en el mapping). Marker `pytest -m permissions` para correr aislado.

### UI

- **`/admin/permissions`** — página informativa read-only que lista
  las 5 capabilities. Footer apunta al superadmin para overrides
  (DEC-021).
- **`/admin/users` + `/admin/users/[id]`** — CRUD de users con select
  `role_type`, sección de "Acceso a organizaciones" (modelo opt-out,
  default todas marcadas), y los 10 botones de acciones admin→user.
- **`/admin/roles`** y `role-editor.tsx` **eliminados en Sprint 6**.
  Redirect 301 → `/admin/permissions`.

### Modelo de datos efectivo

- `users.role_type: VARCHAR(16)` ∈ {`admin`, `user`}.
- `tenant_role_permission_overrides` (US-073, DEC-021): vocabulario
  de overrides es ahora `capability` en `module` y `"grant"` en
  `action`. Solo el superadmin escribe aquí.
- `organization_user_exclusions` (US-078, opt-out membership): default
  vacío → user accede a todas las orgs del tenant.

---

## Objetivo de negocio (v1.0, histórico)

Permitir que usuarios del tenant se autentiquen de forma segura, gestionar roles con permisos granulares por módulo, y tener trazabilidad completa de quién hace qué.

## Roles involucrados

- **Super Admin** (platform-wide) — gestiona cuentas fundacionales.
- **Administrador** del tenant — CRUD de usuarios/roles del tenant.
- **Usuario final** — cualquier rol que se autentica.

---

## User Stories

### US-001 — Crear usuario

**Como** Administrador
**Quiero** crear un usuario con username único, email válido y rol(es)
**Para** que pueda acceder al sistema con las capacidades correctas.

**Criterios de aceptación:**
- [ ] Campos obligatorios: `full_name`, `username`, `email`, `password`, `role_ids[]`.
- [ ] `username` y `email` deben ser únicos por tenant (`citext`).
- [x] `password` cumple política (`core/security.py:validate_password_policy`): **min 8 chars**, 1 mayúscula, 1 dígito, 1 símbolo (set fijo). Sin requisito de lowercase ni blocklist de comunes (la política agresiva mencionada en docs viejos quedó como deuda).
- [ ] Hash `bcrypt rounds=12` al guardar.
- [ ] Response no expone `password_hash`.
- [ ] Crear registro `audit_log` con `action='user.create'`.
- [ ] Endpoint: `POST /api/v1/admin/users` (capability `users.manage`, ver DEC-024).
- [ ] Al crear, retorna `201 Created` con el `UserOut`.

**Test Cases:**
- `TC-001` (unit) — Política de password: cadenas débiles (`"password123"`, `"Aa1!"`) → `VALIDATION_ERROR`.
- `TC-002` (integration) — POST con email duplicado → `409 CONFLICT`.
- `TC-003` (integration) — Happy path → 201, hash correcto, audit log escrito.
- `TC-004` (E2E) — Admin crea user → user puede hacer login inmediato.

---

### US-002 — Login con username o email

**Como** usuario registrado
**Quiero** iniciar sesión con username o email + password
**Para** acceder a mi espacio de trabajo.

**Criterios de aceptación:**
- [ ] `POST /api/v1/auth/login` acepta `{identifier, password}` (identifier = username o email).
- [ ] Si credenciales ok: retorna `{access_token, refresh_token (cookie), user, tenants[]}`.
- [ ] Si credenciales mal: incrementa `failed_login_attempts`, audita, retorna `401 UNAUTHENTICATED`.
- [ ] Mensaje genérico "Credenciales inválidas" (no revela si user existe).
- [ ] JWT incluye `sub`, `tenant_ids[]`, `active_tenant_id`, `is_superadmin`, `roles[]`.
- [ ] Al éxito: `last_login = now()`, `failed_login_attempts = 0`.
- [ ] Audita `login_success` o `login_failed` con IP y user agent.

**Test Cases:**
- `TC-005` (integration) — Login con username ok → 200, JWT válido.
- `TC-006` (integration) — Login con email ok → 200.
- `TC-007` (integration) — Password mal → 401, `failed_login_attempts` +1.
- `TC-008` (integration) — User inactivo → 403 `FORBIDDEN`.
- `TC-009` (E2E) — Login desde UI, navegación persiste.

---

### US-003 — Bloqueo tras 5 intentos fallidos

**Como** Administrador de seguridad
**Quiero** bloquear la cuenta 15 min tras 5 fallos consecutivos
**Para** mitigar ataques de fuerza bruta.

**Criterios de aceptación:**
- [ ] 5º intento fallido: `locked_until = now() + 15min`.
- [ ] Login posterior (aun con pwd correcto) → `403 ACCOUNT_LOCKED` mientras `locked_until > now()`.
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
- [ ] Invalida todos los refresh tokens vigentes (forzando re-login en otros dispositivos).
- [ ] Audita `password_change`.

**Test Cases:**
- `TC-013` (integration) — Happy path → 204, refresh tokens viejos invalidados.
- `TC-014` (integration) — Password nueva = actual → 422 `BUSINESS_RULE`.
- `TC-015` (integration) — Password nueva débil → 400 `VALIDATION_ERROR`.

---

### US-005 — Reset de contraseña por Admin

**Como** Administrador
**Quiero** resetear la contraseña de cualquier user de mi tenant
**Para** desbloquear a usuarios que olvidaron.

**Criterios de aceptación:**
- [ ] `POST /admin/users/{id}/reset-password` → genera password temporal, la devuelve en claro una sola vez en la response.
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
- [ ] `permissions` = objeto `{module: [actions…]}`.
- [ ] Módulos válidos: `projects`, `risks`, `issues`, `change_requests`, `documents`, `lessons`, `minutes`, `admin.users`, `admin.roles`, `admin.organizations`, `admin.projects`, `ai.generate`.
- [ ] Acciones válidas: `read`, `create`, `update`, `delete`, `approve`, `upload`, `minute`, `report`.
- [ ] Roles sistema (`is_system=true`) no se pueden borrar.
- [ ] Al modificar permisos, aplica inmediatamente a los users con ese rol.
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
- [ ] Busqueda fuzzy (`pg_trgm`) en `full_name`, `username`, `email`.
- [ ] Filtro `is_active=true|false`.
- [ ] Paginación estándar.
- [ ] Response incluye: id, full_name, username, email, roles[], is_active, last_login.

**Test Cases:**
- `TC-021` (integration) — Busqueda parcial "juan" encuentra "Juan Pérez".
- `TC-022` (integration) — Filtro `is_active=false` solo lista desactivados.

---

### US-013 — Menú de usuario en el topbar

**Como** usuario autenticado
**Quiero** ver mi identidad y cerrar sesión desde cualquier pantalla
**Para** controlar mi sesión sin abandonar el contexto actual.

**Criterios de aceptación:**
- [ ] El chrome (sidebar + topbar) usa el azul marino `#0E164F` definido en
      `docs/design-system/style.md`.
- [ ] El sidebar **no** contiene footer con datos del usuario; su única
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
- `TC-026` (unit) — Iniciales se calculan a partir de `full_name` (primeras
  dos palabras, en mayúsculas).

---

## Notas técnicas

### Modelos de BD involucrados

- `users`, `roles`, `user_roles`
- `audit_log`

Detalle en [`../architecture/database.md`](../architecture/database.md).

### Endpoints

```
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
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

GET    /api/v1/admin/roles
POST   /api/v1/admin/roles
GET    /api/v1/admin/roles/{id}
PATCH  /api/v1/admin/roles/{id}
DELETE /api/v1/admin/roles/{id}                      (si no is_system)
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
- [x] Cambio aplica inmediatamente sin reload, sin FOUT (script inline en `<head>`).
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
- La traducción visible del UI (strings) queda fuera del alcance de esta US;
  esta US solo persiste la preferencia y la expone globalmente. El i18n
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
- [x] `GET /api/v1/users/me` — obtener perfil.
- [x] `PATCH /api/v1/users/me` — actualizar `full_name` (audit log).
- [x] Al guardar, actualiza `StoredUser` en localStorage → topbar muestra nuevo nombre sin reload.
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
  cambios — Senior PMO pasa por tener los permisos `admin.*` en su rol.

**Test Cases:**
- `TC-NEW-017` (E2E) — Chrome #182e4e visible en light y dark mode ✅ (CSS).
- `TC-NEW-018` (integration) — Senior PMO accede a `/admin/users` ✅.
- `is_admin_equivalent` helper cubierto por test unitario ✅.

**Estado de integración:** DONE (US-010).
