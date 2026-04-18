# EP-007: Administración

**Prioridad:** Alta
**Módulo:** Panel de administración del sistema
**Dependencias:** EP-001 (Usuarios/Roles), EP-002 (Jerarquía)

---

## US-023: Panel de administración de usuarios

**Épica:** EP-007
**Prioridad:** Alta
**Estimación:** M

**Como** administrador del sistema
**Quiero** una vista centralizada para gestionar todos los usuarios
**Para** administrar accesos, roles y estado de las cuentas

### Criterios de aceptación
- [ ] Lista de usuarios con: nombre, usuario, correo, rol(es), estado (activo/inactivo), último acceso
- [ ] Búsqueda por nombre, usuario o correo
- [ ] Filtros por rol y estado
- [ ] Acciones: crear, editar, activar/desactivar, resetear contraseña
- [ ] No se puede desactivar la propia cuenta
- [ ] Paginación
- [ ] Exportar lista a CSV/Excel (futuro)

### Casos de prueba
| ID      | Escenario                         | Pasos                                                        | Resultado esperado                                    |
|---------|-----------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-111  | Ver lista de usuarios             | 1. Admin > Usuarios                                          | Lista completa con datos y acciones                   |
| TC-112  | Buscar usuario                    | 1. Escribir en campo de búsqueda                             | Lista filtrada por coincidencia                       |
| TC-113  | Desactivar usuario                | 1. Click "Desactivar" en usuario                             | Usuario marcado como inactivo, no puede hacer login   |
| TC-114  | Resetear contraseña               | 1. Click "Reset contraseña" 2. Confirmar                     | Contraseña temporal generada                          |
| TC-115  | Intentar desactivarse a sí mismo  | 1. Click "Desactivar" en propia cuenta                       | Error: "No puede desactivar su propia cuenta"         |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-024: Panel de administración de roles

**Épica:** EP-007
**Prioridad:** Alta
**Estimación:** M

**Como** administrador del sistema
**Quiero** una vista para crear y gestionar roles con sus permisos
**Para** definir qué puede hacer cada tipo de usuario en la plataforma

### Criterios de aceptación
- [ ] Lista de roles con: nombre, descripción, cantidad de usuarios asignados
- [ ] Detalle de rol con matriz de permisos (checkboxes por módulo × acción)
- [ ] CRUD de roles (excepto eliminar roles del sistema)
- [ ] Al modificar permisos, los cambios aplican a todos los usuarios con ese rol
- [ ] Vista previa de "¿A quiénes afecta este cambio?" antes de guardar

### Casos de prueba
| ID      | Escenario                         | Pasos                                                        | Resultado esperado                                    |
|---------|-----------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-116  | Ver lista de roles                | 1. Admin > Roles                                             | Lista de roles con conteo de usuarios                 |
| TC-117  | Crear nuevo rol                   | 1. "+ Nuevo Rol" 2. Nombre + permisos 3. Guardar             | Rol creado, disponible para asignar                   |
| TC-118  | Editar permisos                   | 1. Click en rol 2. Cambiar checkboxes 3. Guardar             | Permisos actualizados, preview de afectados           |
| TC-119  | Eliminar rol con usuarios         | 1. Intentar eliminar rol asignado a usuarios                 | Error: "Reasigne usuarios antes de eliminar el rol"   |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-025: Panel de administración de organizaciones

**Épica:** EP-007
**Prioridad:** Media
**Estimación:** S

**Como** administrador del sistema
**Quiero** gestionar las organizaciones registradas desde el panel de administración
**Para** mantener actualizado el catálogo de clientes/empresas

### Criterios de aceptación
- [ ] Reutiliza las funcionalidades de US-006 (CRUD de organizaciones)
- [ ] Vista integrada en el panel de administración
- [ ] Indicador de proyectos activos por organización
- [ ] Link rápido a proyectos de cada organización

### Casos de prueba
| ID      | Escenario                            | Pasos                                                  | Resultado esperado                                    |
|---------|--------------------------------------|--------------------------------------------------------|-------------------------------------------------------|
| TC-120  | Ver organizaciones desde admin       | 1. Admin > Organizaciones                              | Lista con indicador de proyectos activos              |
| TC-121  | Navegar a proyectos de organización  | 1. Click en conteo de proyectos                        | Vista de proyectos filtrada por organización           |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-026: Panel de administración de proyectos

**Épica:** EP-007
**Prioridad:** Media
**Estimación:** S

**Como** administrador del sistema
**Quiero** tener una vista administrativa de todos los proyectos del sistema
**Para** supervisar y gestionar el portafolio completo sin restricción de permisos

### Criterios de aceptación
- [ ] Vista de todos los proyectos del sistema (sin filtro de permisos)
- [ ] Acciones masivas: cambiar estado, reasignar PM (futuro)
- [ ] Indicadores: total de proyectos, por estado, por organización
- [ ] Acceso exclusivo para rol Administrador

### Casos de prueba
| ID      | Escenario                            | Pasos                                                  | Resultado esperado                                    |
|---------|--------------------------------------|--------------------------------------------------------|-------------------------------------------------------|
| TC-122  | Ver todos los proyectos como admin   | 1. Admin > Proyectos                                   | Todos los proyectos del sistema, sin restricción       |
| TC-123  | Acceso como no-admin                 | 1. Login como PM 2. Intentar acceder a Admin > Proyectos | Acceso denegado                                       |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |
