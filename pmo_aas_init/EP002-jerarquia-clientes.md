# EP-002: Jerarquía de Clientes/Proyectos

**Prioridad:** Alta
**Módulo:** Estructura organizacional
**Dependencias:** EP-001 (Usuarios y roles)

---

## US-006: Gestión de organizaciones/empresas

**Épica:** EP-002
**Prioridad:** Alta
**Estimación:** M

**Como** administrador del sistema
**Quiero** registrar y gestionar las organizaciones (compañías/clientes)
**Para** establecer la base de la jerarquía PMO → Cliente → Programa/Proyecto

### Criterios de aceptación
- [ ] CRUD completo de organizaciones: crear, ver, editar, desactivar
- [ ] Campos: nombre, razón social, industria, país, contacto principal, correo, teléfono, logo (opcional)
- [ ] El nombre de la organización debe ser único
- [ ] Se puede activar/desactivar una organización (soft delete)
- [ ] Al desactivar una organización, sus proyectos no se eliminan pero se marcan como inactivos
- [ ] Lista de organizaciones con búsqueda y paginación

### Casos de prueba
| ID      | Escenario                          | Pasos                                                                | Resultado esperado                                      |
|---------|-------------------------------------|----------------------------------------------------------------------|---------------------------------------------------------|
| TC-031  | Crear organización exitosamente    | 1. Admin > Organizaciones 2. "Nueva Organización" 3. Llenar campos 4. Guardar | Organización creada, visible en lista                   |
| TC-032  | Nombre duplicado                   | 1. Crear organización con nombre ya existente                        | Error: "Ya existe una organización con ese nombre"      |
| TC-033  | Desactivar organización            | 1. Seleccionar org 2. Click "Desactivar"                             | Organización inactiva, proyectos marcados como inactivos|
| TC-034  | Editar organización                | 1. Click en organización 2. Modificar datos 3. Guardar               | Datos actualizados correctamente                        |
| TC-035  | Buscar organización                | 1. Escribir en campo de búsqueda                                     | Lista filtrada por nombre/razón social                  |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-007: Gestión de programas

**Épica:** EP-002
**Prioridad:** Media
**Estimación:** M

**Como** PMO Manager
**Quiero** crear programas dentro de una organización para agrupar proyectos relacionados
**Para** tener una visión consolidada de iniciativas que comparten objetivos estratégicos

### Criterios de aceptación
- [ ] Un programa pertenece a una organización
- [ ] Campos: nombre, descripción, organización (dropdown), responsable, fecha inicio, fecha fin estimada, estado
- [ ] Un programa puede contener múltiples proyectos
- [ ] Vista de programa muestra sus proyectos asociados con resumen de avance
- [ ] Se pueden crear programas sin proyectos inicialmente

### Casos de prueba
| ID      | Escenario                         | Pasos                                                              | Resultado esperado                                    |
|---------|------------------------------------|--------------------------------------------------------------------|-------------------------------------------------------|
| TC-036  | Crear programa                    | 1. Seleccionar organización 2. "Nuevo Programa" 3. Llenar datos 4. Guardar | Programa creado bajo la organización seleccionada     |
| TC-037  | Asociar proyecto a programa       | 1. En detalle de programa 2. "Agregar Proyecto" 3. Seleccionar     | Proyecto vinculado, aparece en lista del programa     |
| TC-038  | Ver resumen de programa           | 1. Click en programa                                               | Vista con proyectos, avance consolidado               |
| TC-039  | Programa sin organización         | 1. Intentar crear programa sin seleccionar organización            | Error: campo organización es obligatorio              |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-008: Jerarquía PMO → Organización → Programa → Proyecto

**Épica:** EP-002
**Prioridad:** Alta
**Estimación:** L

**Como** PMO Manager
**Quiero** visualizar y navegar la jerarquía completa PMO → Organización → Programa → Proyecto
**Para** tener una vista estructurada de todo el portafolio

### Criterios de aceptación
- [ ] Vista tipo árbol o breadcrumb que muestre la jerarquía completa
- [ ] Navegación: al hacer click en cualquier nivel se accede a su detalle
- [ ] Filtros por organización y programa en la vista de proyectos
- [ ] Un proyecto siempre pertenece a una organización (obligatorio) y opcionalmente a un programa
- [ ] Los usuarios solo ven la jerarquía de las organizaciones/proyectos a los que tienen acceso
- [ ] Breadcrumb visible en todas las pantallas de detalle: PMO > [Organización] > [Programa] > [Proyecto]

### Casos de prueba
| ID      | Escenario                                 | Pasos                                                          | Resultado esperado                                    |
|---------|-------------------------------------------|----------------------------------------------------------------|-------------------------------------------------------|
| TC-040  | Navegar jerarquía completa                | 1. Desde dashboard, click en organización 2. Click en programa 3. Click en proyecto | Navegación fluida, breadcrumb correcto en cada nivel  |
| TC-041  | Proyecto sin programa                     | 1. Crear proyecto solo con organización (sin programa)         | Proyecto creado, breadcrumb: PMO > Org > Proyecto     |
| TC-042  | Filtrar proyectos por organización        | 1. En vista de proyectos, filtrar por organización             | Solo proyectos de esa organización                    |
| TC-043  | Acceso restringido a jerarquía            | 1. Login como usuario con acceso a 1 organización              | Solo ve la jerarquía de su organización               |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |
