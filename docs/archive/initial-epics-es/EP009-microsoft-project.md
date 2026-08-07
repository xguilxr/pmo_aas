---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# EP-009: Integración con Microsoft Project

**Prioridad:** Alta
**Módulo:** Gestión de tareas / Integración
**Dependencias:** EP-005 (Proyectos)

> Los proyectos deben poder importar archivos de Microsoft Project (.mpp, .xml, .xlsx)
> para visualizar tareas, dependencias y cronogramas dentro de la plataforma.

---

## Decisión técnica: Lectura de archivos MS Project

### Formatos soportados
| Formato      | Descripción                        | Librería de lectura                    | Complejidad |
|-------------|-------------------------------------|----------------------------------------|-------------|
| **.xml**     | MS Project XML export              | `xml.etree` (Python nativo)            | Baja        |
| **.mpp**     | Formato nativo MS Project          | `mpxj` (Java bridge) o `MPXJ` via subprocess | Media  |
| **.xlsx**    | Export a Excel desde MS Project    | `openpyxl` (Python)                    | Baja        |

### Estrategia recomendada
1. **Prioridad 1:** Soporte para .xml (MS Project XML) — es el más limpio y no requiere dependencias pesadas
2. **Prioridad 2:** Soporte para .xlsx con plantilla estándar de importación
3. **Prioridad 3:** Soporte para .mpp nativo usando **MPXJ** (librería Java con wrapper Python `mpxj`)

### Librería principal: MPXJ
- Open source, lee .mpp, .xml, .xlsx, .mpt y más
- Wrapper Python disponible: `pip install mpxj`
- Extrae: tareas, duraciones, dependencias, recursos, fechas, % completado, WBS
- Requiere Java Runtime (JRE) en el servidor

### Visualización: Gantt Chart
- **React:** `dhtmlx-gantt` (free/pro), `frappe-gantt`, `react-gantt-chart`
- Recomendación: `frappe-gantt` (open source, ligero, buen look) o `dhtmlx-gantt` (más completo)

---

## US-030: Importar archivo de Microsoft Project

**Épica:** EP-009
**Prioridad:** Alta
**Estimación:** XL

**Como** Project Manager
**Quiero** importar un archivo de Microsoft Project (.mpp, .xml o .xlsx) a un proyecto de la plataforma
**Para** migrar mi cronograma existente sin tener que recrear todas las tareas manualmente

### Flujo del usuario
1. En detalle de proyecto → Sección "Cronograma/Tareas" → "Importar desde MS Project"
2. Seleccionar archivo (.mpp, .xml o .xlsx)
3. El sistema parsea el archivo y muestra una **vista previa** de las tareas detectadas
4. El usuario revisa, puede excluir tareas o ajustar datos
5. Confirmar importación
6. Las tareas se crean en el proyecto con sus dependencias y fechas

### Datos extraídos del archivo
| Campo MS Project     | Campo en plataforma     | Notas                              |
|---------------------|--------------------------|-------------------------------------|
| Task Name           | Nombre de tarea          |                                     |
| WBS                 | Código WBS               | Estructura jerárquica               |
| Duration            | Duración                 | En días                             |
| Start               | Fecha inicio             |                                     |
| Finish              | Fecha fin                |                                     |
| % Complete          | Avance (%)               |                                     |
| Predecessors        | Dependencias             | FS, SS, FF, SF                      |
| Resource Names      | Recursos asignados       | Mapeo a usuarios del sistema        |
| Milestone           | Es hito                  | Boolean                             |
| Notes               | Notas                    |                                     |
| Outline Level       | Nivel de jerarquía       | Para tareas padre/hijo              |

### Criterios de aceptación
- [ ] Acepta archivos .mpp, .xml (MS Project XML) y .xlsx
- [ ] Vista previa de tareas antes de confirmar importación
- [ ] Preserva la jerarquía de tareas (tareas padre/subtareas) vía WBS
- [ ] Importa dependencias entre tareas (Fin-Inicio, Inicio-Inicio, etc.)
- [ ] Importa fechas de inicio, fin, duración y % de avance
- [ ] Detecta hitos (milestones)
- [ ] Si hay recursos, intenta mapearlos a usuarios del sistema (matching por nombre)
- [ ] Tamaño máximo de archivo: 50MB
- [ ] Manejo de errores: archivos corruptos, formato incorrecto, etc.
- [ ] Log de importación: tareas importadas, ignoradas, errores
- [ ] Se puede re-importar (actualizar tareas existentes o crear nuevas)

### Casos de prueba
| ID      | Escenario                                | Pasos                                                                 | Resultado esperado                                       |
|---------|------------------------------------------|-----------------------------------------------------------------------|----------------------------------------------------------|
| TC-143  | Importar .xml exitosamente               | 1. "Importar MS Project" 2. Subir .xml 3. Vista previa 4. Confirmar  | Tareas creadas con jerarquía y dependencias              |
| TC-144  | Importar .mpp exitosamente               | 1. Subir archivo .mpp 2. Vista previa 3. Confirmar                    | Tareas importadas correctamente                          |
| TC-145  | Importar .xlsx                           | 1. Subir .xlsx exportado de MS Project 2. Confirmar                   | Tareas importadas (sin dependencias complejas)           |
| TC-146  | Vista previa y exclusión                 | 1. Importar archivo 2. Desmarcar 3 tareas 3. Confirmar               | Solo tareas seleccionadas importadas                     |
| TC-147  | Archivo corrupto                         | 1. Subir archivo .mpp dañado                                         | Error: "No se pudo leer el archivo"                      |
| TC-148  | Dependencias importadas                  | 1. Importar archivo con dependencias FS                               | Dependencias visibles en Gantt                           |
| TC-149  | Re-importación                           | 1. Importar archivo 2. Modificar .mpp 3. Re-importar                 | Opción: actualizar existentes o crear nuevas             |
| TC-150  | Mapeo de recursos                        | 1. Importar archivo con recursos 2. Revisar mapeo                    | Sugerencia de mapeo a usuarios del sistema               |
| TC-151  | Archivo muy grande (>50MB)               | 1. Subir archivo de 60MB                                             | Error: "El archivo excede el tamaño máximo"              |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-031: Visualización Gantt de tareas del proyecto

**Épica:** EP-009
**Prioridad:** Alta
**Estimación:** L

**Como** Project Manager
**Quiero** ver las tareas del proyecto en un diagrama de Gantt interactivo
**Para** visualizar el cronograma, dependencias y avance de forma gráfica

### Criterios de aceptación
- [ ] Vista Gantt accesible desde el detalle del proyecto (pestaña "Cronograma" o "Gantt")
- [ ] Muestra tareas como barras horizontales en línea de tiempo
- [ ] Barras coloreadas por estado: en progreso (azul), completada (verde), retrasada (rojo), hito (diamante)
- [ ] Dependencias visuales con flechas entre tareas
- [ ] Jerarquía visible: tareas padre colapsables/expandibles
- [ ] Barra de avance dentro de cada tarea (% completado)
- [ ] Zoom: día, semana, mes, trimestre
- [ ] Línea de "hoy" marcada en el cronograma
- [ ] Tooltip al hover con detalle de la tarea
- [ ] Click en tarea abre su detalle/edición
- [ ] Drag & drop para mover tareas en el tiempo (futuro)
- [ ] Scroll horizontal suave para navegar el timeline

### Casos de prueba
| ID      | Escenario                          | Pasos                                                        | Resultado esperado                                    |
|---------|-------------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-152  | Ver Gantt con tareas               | 1. Ir a proyecto con tareas 2. Pestaña "Gantt"               | Diagrama con barras, dependencias y avance             |
| TC-153  | Zoom a semana                      | 1. Click en botón "Semana"                                   | Timeline ajustado a vista semanal                     |
| TC-154  | Colapsar tarea padre               | 1. Click en flecha de tarea padre                             | Subtareas se ocultan, barra padre permanece           |
| TC-155  | Hover en tarea                     | 1. Hover sobre barra de tarea                                 | Tooltip con: nombre, fechas, avance, responsable      |
| TC-156  | Click en tarea                     | 1. Click en barra de tarea                                    | Panel lateral o modal con detalle editable            |
| TC-157  | Tarea retrasada                    | 1. Tarea con fecha fin pasada y avance < 100%                 | Barra en rojo, indicador visual de retraso            |
| TC-158  | Proyecto sin tareas                | 1. Proyecto vacío, pestaña "Gantt"                            | Mensaje "Sin tareas" + botón "Importar MS Project"    |
| TC-159  | Línea de hoy                       | 1. Ver Gantt                                                  | Línea vertical en la fecha actual                     |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-032: Gestión manual de tareas

**Épica:** EP-009
**Prioridad:** Media
**Estimación:** L

**Como** Project Manager
**Quiero** crear, editar y organizar tareas manualmente dentro del proyecto
**Para** gestionar el cronograma sin depender de un archivo de MS Project

### Campos de tarea
| Campo               | Tipo         | Obligatorio |
|---------------------|--------------|-------------|
| Nombre              | Text         | Sí          |
| Descripción         | Textarea     | No          |
| Fecha inicio        | Date         | Sí          |
| Fecha fin           | Date         | Sí          |
| Duración (días)     | Number (auto)| Calculado   |
| Avance (%)          | Slider/Number| Sí          |
| Responsable         | Dropdown     | No          |
| Dependencias        | Multi-select | No          |
| Es hito             | Checkbox     | No          |
| Tarea padre         | Dropdown     | No          |
| Estado              | Dropdown     | Sí          |
| Prioridad           | Dropdown     | No          |

### Criterios de aceptación
- [ ] CRUD completo de tareas dentro de un proyecto
- [ ] Crear subtareas (jerarquía)
- [ ] Definir dependencias entre tareas
- [ ] Actualizar avance (%) individual y que se recalcule el avance del padre
- [ ] Las tareas se reflejan automáticamente en el Gantt
- [ ] Ordenamiento por WBS, fecha, o prioridad

### Casos de prueba
| ID      | Escenario                       | Pasos                                                        | Resultado esperado                                    |
|---------|----------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-160  | Crear tarea manualmente         | 1. "+ Nueva Tarea" 2. Llenar datos 3. Guardar                | Tarea creada, visible en lista y Gantt                |
| TC-161  | Crear subtarea                  | 1. En tarea padre, "+ Subtarea" 2. Llenar 3. Guardar         | Subtarea creada bajo la tarea padre                   |
| TC-162  | Definir dependencia             | 1. Editar tarea 2. Agregar dependencia 3. Guardar            | Flecha de dependencia visible en Gantt                |
| TC-163  | Actualizar avance               | 1. Cambiar avance de subtareas 2. Ver tarea padre            | Avance del padre recalculado automáticamente          |
| TC-164  | Eliminar tarea con dependencias | 1. Eliminar tarea que tiene dependientes                      | Confirmación + dependencias removidas                 |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |
