# Super Admin — guía funcional y técnica

Este documento describe la experiencia y la arquitectura de la vista
**Super Admin** de PMOAAS, que permite operar la plataforma por encima de los
tenants (multi-tenant vertical).

La vista solo está disponible para usuarios con `users.is_superadmin = 1` y
toda la API vive bajo `GET /api/superadmin/*` (guardada por
`get_superadmin_user`).

---

## 1. Mapa de navegación

El sidebar se redibuja cuando el usuario autenticado es super admin
(`services/auth.ts → isSuperAdmin`). Enlaces:

| Ruta                             | Página                         | Para qué                                  |
|----------------------------------|--------------------------------|-------------------------------------------|
| `/superadmin`                    | `SuperadminOverviewPage`       | Landing: resumen de tenants + métricas    |
| `/superadmin/tenants`            | `SuperadminTenantsPage`        | CRUD completo de tenants                  |
| `/superadmin/tenants/:id`        | `SuperadminTenantDetailPage`   | Detalle de un tenant concreto             |
| `/superadmin/dashboard`          | `SuperadminDashboardPage`      | Insights globales (tendencias de logins, actividad por módulo, top usuarios) |
| `/superadmin/users`              | `SuperadminUsersPage`          | Lista cruzada de todos los usuarios       |
| `/superadmin/roles`              | `SuperadminRolesPage`          | Roles de plataforma (compartidos)         |
| `/superadmin/logs/access`        | `SuperadminAccessLogsPage`     | Logins, logouts y cambios de contraseña   |
| `/superadmin/logs/activity`      | `SuperadminActivityLogsPage`   | Actividad en negocio (CRUD de entidades)  |

Todas las rutas están envueltas en `<SuperAdminGuard>`
(`components/superadmin/SuperAdminGuard.tsx`) que redirige a `/login` si no
hay sesión y a `/` si la sesión existe pero no es super admin.

---

## 2. Panel Super Admin (`/superadmin`)

Landing operativa. Consume `GET /superadmin/overview` y muestra:

- 7 KPIs: tenants totales/activos/inactivos, usuarios, super admins,
  proyectos, programas, logins/fallos de las últimas 24 h.
- Tarjeta "Tenants recientes" con los 5 últimos creados.
- Grid de tenants con dos acciones rápidas por tarjeta:
  - **Toggle activo/inactivo** → `PATCH /superadmin/tenants/{id}/active`.
  - **Actuar como admin** → `POST /superadmin/tenants/{id}/join-as-admin`,
    luego setea `X-Tenant-ID` y navega a `/admin/users` dentro del tenant.

---

## 3. Gestión de Tenants (`/superadmin/tenants`)

La prioridad del cliente: administrar tenants sin entrar en ellos. Opera sobre
`GET /superadmin/tenants` y ofrece:

- Buscador + filtro activo/inactivo.
- **Crear tenant** (`POST /superadmin/tenants`) — incluye datos iniciales del
  admin del tenant. Si no se pasan, el backend auto-genera usuario y
  contraseña y los devuelve **una sola vez** en el modal de credenciales.
- **Editar** (`PATCH /superadmin/tenants/{id}`) — nombre, slug, industria,
  contacto, branding.
- **Soft-delete** (`DELETE /superadmin/tenants/{id}`) — marca
  `deleted_at` y desactiva. Recuperable por soporte.
- **Hard-delete** permanente (`DELETE /superadmin/tenants/{id}/permanent?confirm_slug=…`)
  — sólo para tenants ya inactivos. Confirmación al estilo GitHub escribiendo
  el slug.
- **Actuar como admin** — mismo helper `enterTenantAsAdmin` que el overview.
  Es idempotente: si el super admin ya está en el tenant con rol
  `Administrador` no duplica nada.

### Flujo "hacerse admin"
1. Frontend llama `POST /superadmin/tenants/{id}/join-as-admin`.
2. Backend garantiza pertenencia al tenant y asigna el rol `Administrador`
   (si no existe, no falla — queda sin rol y se registra).
3. Frontend guarda `localStorage['pmo_tenant_id'] = id` y mutabiliza el blob
   `pmo_user.organizations` para que el sidebar detecte la organización
   activa sin recargar.
4. Al navegar a `/admin/users` (o cualquier ruta tenant-scoped) el endpoint
   recibe `X-Tenant-ID` y `get_current_tenant` lo acepta porque
   `current_user.is_superadmin` corto-circuita la validación de pertenencia.

---

## 4. Dashboard General (`/superadmin/dashboard`)

Vista "zoom out" con insights de plataforma. Hace 3 llamadas:

- `GET /superadmin/overview` — KPIs.
- `GET /superadmin/access-logs?days=7` — para dibujar tendencia de logins
  de los últimos 7 días.
- `GET /superadmin/activity-logs?days=7` — para ranking de módulos más
  activos, top 5 usuarios por actividad y feed reciente.

No guarda estado propio, refresca al recargar.

---

## 5. Usuarios (`/superadmin/users`)

Lista cruzada de todos los usuarios de la plataforma
(`GET /superadmin/users`). Filtros server-side:

- `search` — por username/email/nombre.
- `tenant_id` — restringe a miembros de un tenant.
- `role` — por nombre de rol.
- `only_active` / `include_superadmins`.

Acciones:

- **Crear** (`POST /superadmin/users`) — permite asignar cualquier
  combinación de tenants y roles, marcar como super admin y fijar password
  inicial (política ≥12 caracteres + mayúscula + dígito, igual que el resto
  de la app).
- **Editar** (`PATCH /superadmin/users/{id}`) — reemplaza asignaciones.
  Guard-rail: si el usuario es el propio super admin logueado, no se permite
  quitarle `is_superadmin` (para no auto-lockout).
- **Resetear contraseña** (`POST /superadmin/users/{id}/reset-password`) —
  genera una contraseña nueva, escribe un `AuditLog` de
  `password_reset_platform` y la muestra **una sola vez**.
- **Eliminar** (`DELETE /superadmin/users/{id}`) — soft delete.
  No se puede eliminar a sí mismo.

---

## 6. Roles (`/superadmin/roles`)

Roles compartidos por todos los tenants. `GET /superadmin/roles` devuelve
`is_system` y `user_count` para que la UI pueda:

- Proteger roles del sistema (Administrador, PMO, etc.) de renombrado y
  eliminación.
- Avisar con `window.confirm` si se intenta eliminar un rol que tiene
  usuarios asignados.

El modal agrupa permisos por módulo (`GET /superadmin/permissions`) con un
botón "Todos/Ninguno" por módulo y chips toggleables para permisos
individuales. El toggle de módulo es idempotente: si hay alguno
desmarcado los marca todos, si todos están marcados los quita.

---

## 7. Logs

### 7.1 Logs de acceso (`/superadmin/logs/access`)

`GET /superadmin/access-logs` filtra `AuditLog.action` a un set cerrado:

```
login_success, login_failed, login_blocked, logout,
password_change, password_reset, password_reset_platform,
password_reset_request
```

**Deduplicación**: cada login escribe una fila con `organization_id = NULL`
(nivel plataforma) y además una fila por tenant al que pertenece el usuario.
Por defecto el endpoint devuelve solo las filas con `organization_id IS NULL`
para no duplicar. Pasar `tenant_id=<id>` fuerza a ver las filas scoped a un
tenant específico.

Rango por defecto: 30 días. Filtros UI: acción, tenant, rango (1/7/30/90/365
días), búsqueda en memoria por usuario/tenant/IP/detalles.

### 7.2 Logs de actividad (`/superadmin/logs/activity`)

`GET /superadmin/activity-logs` es el complemento: todo lo que **no** es
autenticación (`AuditLog.action NOT IN <access set>` y
`AuditLog.module != "auth"`). Cubre CRUD sobre organizaciones, programas,
proyectos, RAID, minutas, documentos, usuarios, roles, etc.

Rango por defecto: 7 días. Filtros UI: módulo (poblado con los módulos que
aparecen en la respuesta), acción (campo libre, ej. `create`, `update`,
`delete`, `deactivate`), tenant, rango y búsqueda en memoria.

---

## 8. Hooks de auditoría nuevos

Para que los logs sean completos, se añadieron llamadas a `log_action` en:

| Endpoint                                   | Acción emitida (plataforma + tenant)        |
|--------------------------------------------|---------------------------------------------|
| `POST /auth/change-password`               | `password_change`                           |
| `POST /admin/users/{id}/reset-password`    | `password_reset` (tenant) + plataforma     |
| `POST /superadmin/users/{id}/reset-password` | `password_reset_platform`                |
| `POST /superadmin/tenants/{id}/join-as-admin` | `superadmin.join_as_admin`              |
| `PATCH /superadmin/tenants/{id}/active`    | `tenant.activate` / `tenant.deactivate`    |

Login exitoso/fallido/bloqueado, creación y desactivación de tenant, CRUD
de usuario/rol, etc. ya estaban registrados antes.

---

## 9. Invariantes de seguridad

1. **`get_superadmin_user` en todas las rutas `/api/superadmin/*`**. Ningún
   endpoint depende solo de `get_current_user`.
2. **`get_current_tenant`** sigue filtrando por `is_active=True` para
   usuarios normales. Super admin bypass via check explícito
   (`current_user.is_superadmin or org_id in user_org_ids`), por eso puede
   manipular tenants inactivos con los endpoints `/superadmin/tenants/*`
   que no pasan por `get_current_tenant`.
3. **No se puede auto-lockout**: el backend rechaza que un super admin
   elimine su propia cuenta o le quite el flag `is_superadmin` a sí mismo.
4. **Contraseñas nuevas se muestran una sola vez**. Los endpoints
   `createUser`, `createTenant` y `resetUserPassword` devuelven la clave en
   claro en la respuesta; después queda solo el hash bcrypt.
5. **Hard delete de tenant** requiere que el tenant esté inactivo y que el
   query param `confirm_slug` coincida exactamente con el slug actual.

---

## 10. Cómo añadir una nueva vista super admin

1. Crear endpoint en `backend/app/api/superadmin.py` con
   `_admin: User = Depends(get_superadmin_user)`.
2. Añadir el typed client en `frontend/src/services/superadmin.ts`.
3. Crear la página en `frontend/src/pages/superadmin/…`.
4. Registrar la ruta dentro de `<SuperAdminGuard>` en `App.tsx`.
5. Añadir el link al sidebar super admin en
   `components/layout/Sidebar.tsx` (bloque `superAdmin ? … :`).
6. Actualizar este documento.
