---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# EP-001: Login y Manejo de Usuarios

**Prioridad:** Alta
**Módulo:** Autenticación y gestión de usuarios
**Dependencias:** Ninguna (épica fundacional)

---

## US-001: Creación de usuarios

**Épica:** EP-001
**Prioridad:** Alta
**Estimación:** M

**Como** administrador del sistema
**Quiero** crear nuevos usuarios con sus datos básicos
**Para** que puedan acceder a la plataforma PMO

### Criterios de aceptación
- [ ] El formulario solicita: nombre completo, correo electrónico, nombre de usuario, contraseña, rol inicial
- [ ] El correo electrónico debe ser único en el sistema
- [ ] El nombre de usuario debe ser único en el sistema
- [ ] La contraseña debe cumplir política mínima: 8 caracteres, 1 mayúscula, 1 número, 1 carácter especial
- [ ] Al crear el usuario se envía una notificación (en pantalla o por correo) con sus credenciales
- [ ] El usuario creado aparece en la lista de usuarios de administración
- [ ] Se registra la acción en el log de auditoría

### Casos de prueba
| ID      | Escenario                          | Pasos                                                              | Resultado esperado                                    |
|---------|------------------------------------|--------------------------------------------------------------------|-------------------------------------------------------|
| TC-001  | Creación exitosa                   | 1. Ir a Admin > Usuarios 2. Click "Nuevo Usuario" 3. Llenar campos válidos 4. Guardar | Usuario creado, aparece en lista, mensaje de éxito    |
| TC-002  | Correo duplicado                   | 1. Intentar crear usuario con correo ya existente                  | Error: "El correo electrónico ya está registrado"     |
| TC-003  | Username duplicado                 | 1. Intentar crear usuario con username ya existente                | Error: "El nombre de usuario ya está en uso"          |
| TC-004  | Contraseña débil                   | 1. Ingresar contraseña "1234"                                      | Error: "La contraseña no cumple los requisitos mínimos" |
| TC-005  | Campos obligatorios vacíos         | 1. Dejar campos requeridos vacíos 2. Guardar                       | Error indicando campos faltantes                      |
| TC-006  | Correo con formato inválido        | 1. Ingresar "usuario@" como correo                                 | Error: "Formato de correo electrónico inválido"       |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-002: Inicio de sesión con usuario o correo

**Épica:** EP-001
**Prioridad:** Alta
**Estimación:** M

**Como** usuario registrado
**Quiero** iniciar sesión con mi nombre de usuario o correo electrónico junto con mi contraseña
**Para** acceder a la plataforma y sus funcionalidades

### Criterios de aceptación
- [ ] El formulario de login acepta usuario o correo en un solo campo + contraseña
- [ ] Al autenticar correctamente, se genera un token JWT y se redirige al dashboard
- [ ] Al fallar la autenticación, se muestra un mensaje genérico: "Credenciales incorrectas"
- [ ] Después de 5 intentos fallidos consecutivos, la cuenta se bloquea temporalmente (15 min)
- [ ] La sesión tiene un tiempo de expiración configurable (default: 24 horas)
- [ ] Se registra cada intento de login (exitoso o fallido) en el log de auditoría
- [ ] La interfaz está disponible en español (default) e inglés

### Casos de prueba
| ID      | Escenario                           | Pasos                                                        | Resultado esperado                                         |
|---------|-------------------------------------|--------------------------------------------------------------|------------------------------------------------------------|
| TC-007  | Login exitoso con username          | 1. Ingresar username válido 2. Ingresar contraseña 3. Click Login | Redirección al dashboard, token generado                   |
| TC-008  | Login exitoso con correo            | 1. Ingresar correo válido 2. Ingresar contraseña 3. Click Login   | Redirección al dashboard, token generado                   |
| TC-009  | Contraseña incorrecta               | 1. Ingresar usuario válido 2. Ingresar contraseña incorrecta     | Error: "Credenciales incorrectas"                          |
| TC-010  | Usuario inexistente                 | 1. Ingresar usuario que no existe 2. Contraseña cualquiera       | Error: "Credenciales incorrectas" (mismo mensaje genérico) |
| TC-011  | Bloqueo por intentos fallidos       | 1. Ingresar contraseña incorrecta 5 veces consecutivas           | Cuenta bloqueada, mensaje de bloqueo temporal              |
| TC-012  | Login después de bloqueo temporal   | 1. Esperar 15 min después de bloqueo 2. Login con datos válidos  | Login exitoso                                              |
| TC-013  | Sesión expirada                     | 1. Esperar a que expire el token 2. Intentar navegar             | Redirección a pantalla de login                            |
| TC-014  | Cambio de idioma en login           | 1. En pantalla de login, cambiar idioma a inglés                 | Toda la interfaz cambia a inglés                           |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-003: Recuperación de contraseña

**Épica:** EP-001
**Prioridad:** Alta
**Estimación:** M

**Como** usuario que olvidó su contraseña
**Quiero** poder recuperar/restablecer mi contraseña desde una pantalla en la plataforma
**Para** volver a acceder al sistema sin depender de un administrador

### Criterios de aceptación
- [ ] Existe un enlace "¿Olvidaste tu contraseña?" en la pantalla de login
- [ ] El flujo de recuperación se realiza en una pantalla dentro de la plataforma (sin link por correo)
- [ ] El usuario debe identificarse con su correo electrónico o nombre de usuario
- [ ] Se valida la identidad con una pregunta de seguridad o código enviado por correo
- [ ] La nueva contraseña debe cumplir la misma política de seguridad que al crear cuenta
- [ ] No se puede reutilizar las últimas 3 contraseñas
- [ ] Se registra el cambio de contraseña en el log de auditoría

### Casos de prueba
| ID      | Escenario                            | Pasos                                                                | Resultado esperado                                     |
|---------|--------------------------------------|----------------------------------------------------------------------|--------------------------------------------------------|
| TC-015  | Recuperación exitosa                 | 1. Click "¿Olvidaste tu contraseña?" 2. Ingresar correo 3. Validar identidad 4. Ingresar nueva contraseña | Contraseña actualizada, redirección a login            |
| TC-016  | Correo no registrado                 | 1. Ingresar correo que no existe en el sistema                       | Mensaje genérico (no revelar si existe o no)           |
| TC-017  | Nueva contraseña no cumple política  | 1. Ingresar nueva contraseña débil                                   | Error con requisitos de contraseña                     |
| TC-018  | Reutilización de contraseña anterior | 1. Ingresar una de las últimas 3 contraseñas como nueva              | Error: "No puede reutilizar contraseñas recientes"     |
| TC-019  | Validación de identidad fallida      | 1. Responder incorrectamente la pregunta de seguridad                | Error: no se permite el cambio                         |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-004: Gestión de roles y permisos

**Épica:** EP-001
**Prioridad:** Alta
**Estimación:** L

**Como** administrador del sistema
**Quiero** crear roles, definir permisos mediante checkboxes editables y asignar roles a usuarios
**Para** controlar el acceso a las diferentes funcionalidades de la plataforma

### Criterios de aceptación
- [ ] Se pueden crear nuevos roles con nombre y descripción
- [ ] Cada rol tiene una matriz de permisos con checkboxes editables
- [ ] Los permisos se agrupan por módulo (Proyectos, Riesgos, Incidencias, Cambios, Documentos, Lecciones, Minutas, Admin)
- [ ] Cada módulo tiene permisos granulares: Ver, Crear, Editar, Eliminar
- [ ] Se pueden asignar uno o más roles a un usuario
- [ ] Los cambios de rol/permisos se aplican inmediatamente (o al siguiente login)
- [ ] Roles por defecto: Administrador, PMO Manager, Project Manager, Viewer
- [ ] No se puede eliminar el rol de Administrador ni dejar el sistema sin al menos un administrador
- [ ] Se registran los cambios de roles en el log de auditoría

### Casos de prueba
| ID      | Escenario                               | Pasos                                                                  | Resultado esperado                                    |
|---------|-----------------------------------------|------------------------------------------------------------------------|-------------------------------------------------------|
| TC-020  | Crear rol nuevo                         | 1. Ir a Admin > Roles 2. Click "Nuevo Rol" 3. Llenar nombre y permisos 4. Guardar | Rol creado, aparece en lista                          |
| TC-021  | Editar permisos de rol                  | 1. Seleccionar rol existente 2. Modificar checkboxes 3. Guardar        | Permisos actualizados                                 |
| TC-022  | Asignar rol a usuario                   | 1. Ir a edición de usuario 2. Seleccionar rol 3. Guardar               | Usuario con nuevo rol, accesos actualizados           |
| TC-023  | Validar restricción de permisos         | 1. Login con usuario de rol "Viewer" 2. Intentar crear proyecto        | Acción bloqueada, mensaje de permisos insuficientes   |
| TC-024  | Intentar eliminar rol Administrador     | 1. Intentar eliminar rol de Administrador                              | Error: "No se puede eliminar el rol de Administrador" |
| TC-025  | Último administrador                    | 1. Intentar cambiar rol del único admin a otro rol                     | Error: "Debe existir al menos un administrador"       |
| TC-026  | Rol con nombre duplicado               | 1. Crear rol con nombre ya existente                                   | Error: "Ya existe un rol con ese nombre"              |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-005: Asignación de proyectos a usuarios

**Épica:** EP-001
**Prioridad:** Media
**Estimación:** M

**Como** administrador o PMO Manager
**Quiero** asignar usuarios a proyectos específicos
**Para** que cada usuario solo vea y gestione los proyectos que le corresponden

### Criterios de aceptación
- [ ] Desde el perfil de usuario o desde el proyecto, se pueden vincular usuarios
- [ ] Un usuario puede estar asignado a múltiples proyectos
- [ ] Un proyecto puede tener múltiples usuarios asignados
- [ ] Se puede definir el rol del usuario dentro del proyecto (PM, miembro, stakeholder)
- [ ] Los usuarios solo ven proyectos a los que están asignados (excepto admin/PMO Manager)
- [ ] Se registra la asignación en el log de auditoría

### Casos de prueba
| ID      | Escenario                             | Pasos                                                                | Resultado esperado                                     |
|---------|---------------------------------------|----------------------------------------------------------------------|--------------------------------------------------------|
| TC-027  | Asignar usuario a proyecto            | 1. Ir a detalle de proyecto 2. Sección "Equipo" 3. Agregar usuario   | Usuario aparece en equipo del proyecto                 |
| TC-028  | Usuario ve solo sus proyectos         | 1. Login con usuario asignado a 2 proyectos 2. Ver lista de proyectos | Solo se muestran 2 proyectos                          |
| TC-029  | Admin ve todos los proyectos          | 1. Login como admin 2. Ver lista de proyectos                        | Se muestran todos los proyectos del sistema            |
| TC-030  | Remover usuario de proyecto           | 1. Ir a equipo del proyecto 2. Remover usuario                       | Usuario ya no tiene acceso al proyecto                 |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |
