---
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# EP-005: Proyectos

**Prioridad:** Alta
**Módulo:** Gestión de proyectos
**Dependencias:** EP-001 (Usuarios), EP-002 (Jerarquía), EP-003 (Solicitudes)

---

## US-014: Matriz de proyectos con filtros

**Épica:** EP-005
**Prioridad:** Alta
**Estimación:** L

**Como** Project Manager
**Quiero** ver una lista de proyectos con filtros avanzados
**Para** encontrar y gestionar rápidamente los proyectos que necesito

### Filtros requeridos
| Filtro          | Tipo                      | Notas                                                      |
|-----------------|---------------------------|-------------------------------------------------------------|
| Status          | Botones en fila (toggle)  | Todos (default), En planificación, En ejecución, En soporte, Cerrados |
| Empresa         | Dropdown                  | Organizaciones activas del sistema                          |
| Folio           | Input text                | Búsqueda por folio de proyecto                              |
| Nombre          | Input text                | Búsqueda parcial por nombre                                 |
| Tipo            | Dropdown                  | Tipos de proyecto configurados                              |
| Prioridad       | Dropdown                  | Alta, Media, Baja                                           |
| Fecha inicio    | DateRange (desde - hasta) | Rango de fecha de inicio                                    |
| Fecha final     | Date                      | Fecha fin planificada                                       |
| Aplicar filtros | Botón                     | Ejecuta la búsqueda con los filtros seleccionados           |
| Limpiar filtros | Botón                     | Restablece todos los filtros a su valor por defecto         |

### Columnas de la matriz
| Columna      | Tipo       | Notas                                |
|--------------|------------|--------------------------------------|
| Folio        | Text       | Identificador único                  |
| Nombre       | Text/Link  | Clickeable → detalle del proyecto    |
| Tipo / Prioridad | Badge  | Tipo y prioridad en badges de color  |
| Empresa      | Text       | Nombre de la organización            |
| Fase         | Badge      | Fase actual del proyecto             |
| Avance (%)   | Progress   | Barra de progreso + porcentaje       |
| Presupuesto  | Currency   | Formato MXN                          |

### Criterios de aceptación
- [ ] La vista por defecto muestra "Todos" los proyectos accesibles al usuario
- [ ] Los botones de status funcionan como toggle (solo uno activo a la vez)
- [ ] Los filtros se combinan con AND lógico
- [ ] La búsqueda por nombre es parcial (contiene)
- [ ] Cada fila es clickeable y navega al detalle del proyecto
- [ ] Paginación con 15 registros por página (configurable)
- [ ] Ordenamiento por click en encabezados de columna
- [ ] Indicador de cantidad de resultados encontrados
- [ ] "Limpiar filtros" restablece todo y muestra todos los registros

### Casos de prueba
| ID      | Escenario                            | Pasos                                                              | Resultado esperado                                     |
|---------|--------------------------------------|---------------------------------------------------------------------|--------------------------------------------------------|
| TC-070  | Vista por defecto                    | 1. Ir a Proyectos                                                   | Todos los proyectos accesibles, botón "Todos" activo   |
| TC-071  | Filtrar por status                   | 1. Click en "En ejecución"                                          | Solo proyectos en ejecución                            |
| TC-072  | Filtrar por empresa                  | 1. Seleccionar empresa del dropdown                                  | Solo proyectos de esa empresa                          |
| TC-073  | Búsqueda por nombre parcial          | 1. Escribir "migra" en campo nombre 2. Aplicar filtros               | Proyectos cuyo nombre contiene "migra"                 |
| TC-074  | Combinación de filtros               | 1. Status: "En ejecución" + Prioridad: "Alta" 2. Aplicar            | Solo proyectos activos con prioridad alta              |
| TC-075  | Limpiar filtros                      | 1. Aplicar varios filtros 2. Click "Limpiar filtros"                 | Todos los filtros reseteados, vista completa           |
| TC-076  | Click en proyecto                    | 1. Click en fila de proyecto                                         | Navega a página de detalle del proyecto                |
| TC-077  | Sin resultados                       | 1. Filtros que no coinciden con ningún proyecto                       | Mensaje "No se encontraron proyectos" + sugerencia     |
| TC-078  | Paginación                           | 1. Tener más de 15 proyectos 2. Click en página 2                    | Siguiente set de resultados                            |
| TC-079  | Rango de fechas                      | 1. Seleccionar fecha inicio desde/hasta 2. Aplicar                   | Solo proyectos dentro del rango                        |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-015: Creación de nuevo proyecto

**Épica:** EP-005
**Prioridad:** Alta
**Estimación:** L

**Como** PMO Manager o Project Manager
**Quiero** crear un nuevo proyecto ya sea desde una solicitud aprobada o llenando un formulario nuevo
**Para** formalizar una iniciativa y comenzar su gestión

### Criterios de aceptación
- [ ] Botón "+ Nuevo Proyecto" visible en la vista de proyectos
- [ ] Al crear desde solicitud aprobada, los campos se pre-cargan con datos de la solicitud
- [ ] Al crear manualmente, se llena un formulario completo
- [ ] Campos mínimos: folio (autogenerado), nombre, descripción, tipo, prioridad, empresa, fase, responsable (PM), fecha inicio, fecha fin planificada, presupuesto
- [ ] Se asigna automáticamente al usuario creador como parte del equipo
- [ ] El proyecto aparece inmediatamente en la matriz de proyectos
- [ ] Se registra en el log de auditoría

### Casos de prueba
| ID      | Escenario                         | Pasos                                                                | Resultado esperado                                    |
|---------|-----------------------------------|----------------------------------------------------------------------|-------------------------------------------------------|
| TC-080  | Crear proyecto nuevo               | 1. Click "+ Nuevo Proyecto" 2. Llenar formulario 3. Guardar          | Proyecto creado con folio, visible en matriz           |
| TC-081  | Crear desde solicitud              | 1. Aprobar solicitud 2. "Crear Proyecto" 3. Revisar datos pre-cargados 4. Guardar | Proyecto creado con datos de solicitud                |
| TC-082  | Folio autogenerado                 | 1. Crear proyecto                                                    | Folio único generado automáticamente (ej: PRJ-2026-001)|
| TC-083  | Campos obligatorios vacíos         | 1. Dejar campos requeridos vacíos 2. Guardar                         | Validación con errores en campos faltantes            |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-016: Detalle de proyecto

**Épica:** EP-005
**Prioridad:** Alta
**Estimación:** L

**Como** Project Manager
**Quiero** ver una página de detalle completa del proyecto
**Para** gestionar toda la información, equipo y módulos asociados al proyecto

### Criterios de aceptación
- [ ] Página de detalle accesible al hacer click en cualquier proyecto de la matriz
- [ ] Muestra toda la información del proyecto organizada en secciones
- [ ] Secciones: Información general, Equipo, Avance, Presupuesto, Timeline
- [ ] Toolbar lateral izquierdo con acceso a módulos del proyecto (Riesgos, Incidencias, Cambios, Documentos, Lecciones, Minutas)
- [ ] Breadcrumb de navegación: PMO > Organización > Programa > Proyecto
- [ ] Botones de acción: Editar, Cambiar fase, Exportar
- [ ] Solo usuarios con permisos pueden editar

### Casos de prueba
| ID      | Escenario                           | Pasos                                                        | Resultado esperado                                    |
|---------|-------------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-084  | Ver detalle de proyecto             | 1. Click en proyecto desde la matriz                         | Página de detalle con toda la información             |
| TC-085  | Navegar por breadcrumb              | 1. Click en "Organización" en breadcrumb                     | Navega a detalle de la organización                   |
| TC-086  | Acceder a módulo desde toolbar      | 1. Click en "Riesgos" en toolbar lateral                     | Vista de riesgos filtrada por este proyecto            |
| TC-087  | Editar proyecto                     | 1. Click "Editar" 2. Modificar campos 3. Guardar             | Datos actualizados, registro en auditoría             |
| TC-088  | Sin permisos de edición             | 1. Login como Viewer 2. Ver detalle de proyecto              | Botón "Editar" no visible o deshabilitado             |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |
