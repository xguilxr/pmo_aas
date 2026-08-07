---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# US001 — Autenticación y gestión de sesión

Épica origen: [EP001 — Login usuarios](../../epics/EP001-login-usuarios.md)

## US001-A — Login exitoso

**Como** usuario registrado
**quiero** iniciar sesión con mi username/email + password
**para** acceder a mi tenant.

### Criterios de aceptación
- POST `/api/auth/login` con credenciales válidas → 200 con `access_token`,
  `user_id`, `full_name`, `roles`, `organizations`, `is_superadmin`.
- `user.last_login` se actualiza a `datetime.now(timezone.utc)`.
- `user.failed_login_attempts` se resetea a 0.
- Se escribe una fila en `audit_log` por org del usuario con
  `action='login_success'`, `module='auth'`.
- JWT incluye `sub`, `org_ids`, `is_superadmin`.

**Test:** `TC-001` → `backend/tests/api/test_tc001_login_success.py`

## US001-B — Login fallido registra intento

**Como** admin de seguridad
**quiero** ver en el audit log los intentos fallidos
**para** detectar ataques de fuerza bruta.

### Criterios de aceptación
- POST `/auth/login` con password mala → 401 `"Credenciales incorrectas"`.
- `user.failed_login_attempts` incrementa en 1.
- Fila en `audit_log` con `action='login_failed'`,
  `details={"attempts": N, "reason": "bad_password"}`.
- Usuario inexistente → 401, fila con `user_id=NULL`,
  `details={"username_or_email": "...", "reason": "unknown_user"}`.

**Test:** `TC-002`

## US001-C — Bloqueo tras 5 intentos fallidos

**Como** usuario legítimo
**quiero** que mi cuenta se bloquee 15min tras 5 intentos malos
**para** que un atacante no pueda seguir probando passwords.

### Criterios de aceptación
- Al 5º intento fallido, `user.locked_until = now() + 15min`.
- Login posterior (aun con password correcta) → 403 `"Cuenta bloqueada temporalmente"`.
- Se escribe fila `action='login_blocked'` en audit_log.
- Tras 15min se permite login de nuevo y se resetea `locked_until`.

**Test:** `TC-003`

## US001-D — Cambio de contraseña propia

**Como** usuario autenticado
**quiero** cambiar mi contraseña desde `/settings/password`
**para** mantener la seguridad de mi cuenta.

### Criterios de aceptación
- POST `/auth/change-password` con `current_password` correcta + `new_password`
  que pasa la policy (mínimo 12 chars, mayúscula, número, símbolo) → 200.
- `current_password` incorrecta → 400.
- `new_password == current_password` → 400.
- `new_password` débil → 400 con detalle de la regla violada.

**Test:** `TC-004`

## US001-E — Reset admin (superadmin o admin de tenant)

**Como** admin
**quiero** resetear la password de un usuario a un valor aleatorio
**para** desbloquearle acceso sin conocer su password.

### Criterios de aceptación
- POST `/auth/users/{id}/reset-password` → 200 con `new_password` en claro **una sola vez**.
- Admin de tenant solo puede resetear usuarios de SU tenant; a otros → 404.
- Admin de tenant **no** puede resetear a un superadmin → 403.
- Superadmin puede resetear a cualquiera.

**Test:** `TC-005` (pendiente de crear)
