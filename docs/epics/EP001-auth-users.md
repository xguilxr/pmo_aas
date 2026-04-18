# EP001 — Login y Gestión de Usuarios

| Campo | Valor |
|---|---|
| **ID** | EP001 |
| **Prioridad** | Alta (fundacional) |
| **Dependencias** | — |
| **Módulo** | `auth`, `admin.users`, `admin.roles` |
| **Estado** | MVP |
| **Versión objetivo** | v1.0 |

## Objetivo de negocio

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
- [ ] `password` cumple política: min 12 chars, 1 mayúscula, 1 número, 1 símbolo.
- [ ] Hash `bcrypt rounds=12` al guardar.
- [ ] Response no expone `password_hash`.
- [ ] Crear registro `audit_log` con `action='user.create'`.
- [ ] Endpoint: `POST /api/v1/admin/users` (permiso `admin.users:create`).
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
