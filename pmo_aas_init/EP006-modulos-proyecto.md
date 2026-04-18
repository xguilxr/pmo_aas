# EP-006: Módulos de Proyecto

**Prioridad:** Alta
**Módulo:** Sub-módulos del proyecto (dropdown en toolbar lateral)
**Dependencias:** EP-005 (Proyectos)

> Cada módulo se accede desde un dropdown en el toolbar lateral izquierdo del detalle de proyecto.
> Todos comparten el mismo patrón: botón de nuevo, filtros y matriz de resultados clickeables con página de detalle.

---

## US-017: Módulo de Riesgos

**Épica:** EP-006
**Prioridad:** Alta
**Estimación:** L

**Como** Project Manager
**Quiero** gestionar los riesgos asociados a mis proyectos
**Para** identificar, evaluar y mitigar amenazas al éxito del proyecto

### Campos del riesgo
| Campo                | Tipo         | Obligatorio |
|----------------------|--------------|-------------|
| Folio                | Auto         | Sí          |
| Título               | Text         | Sí          |
| Descripción          | Textarea     | Sí          |
| Proyecto             | Dropdown     | Sí          |
| Categoría            | Dropdown     | Sí          |
| Probabilidad         | Dropdown     | Sí (1-5)    |
| Impacto              | Dropdown     | Sí (1-5)    |
| Severidad            | Calculado    | Auto (P×I)  |
| Responsable          | Dropdown     | Sí          |
| Estrategia mitigación| Textarea     | Sí          |
| Fecha identificación | Date (auto)  | Sí          |
| Fecha límite         | Date         | No          |
| Estado               | Dropdown     | Sí          |
| Comentarios          | Textarea     | No          |

### Filtros
- Proyecto, Estado, Severidad, Responsable, Fecha (rango)
- Botones: Aplicar filtros, Limpiar filtros

### Matriz de resultados
- Folio, Título, Proyecto, Severidad (visual), Estado, Responsable, Fecha identificación
- Cada fila clickeable → detalle del riesgo con link al proyecto

### Criterios de aceptación
- [ ] Botón "+ Nuevo Riesgo" visible para usuarios con permiso
- [ ] Severidad se calcula automáticamente (Probabilidad × Impacto)
- [ ] Código de colores por severidad: 1-5 Verde, 6-12 Amarillo, 13-25 Rojo
- [ ] Detalle del riesgo incluye link al proyecto relacionado
- [ ] Historial de cambios del riesgo visible en el detalle
- [ ] Filtros combinables con AND lógico

### Casos de prueba
| ID      | Escenario                       | Pasos                                                              | Resultado esperado                                    |
|---------|----------------------------------|---------------------------------------------------------------------|-------------------------------------------------------|
| TC-089  | Crear nuevo riesgo              | 1. Click "+ Nuevo Riesgo" 2. Llenar campos 3. Guardar              | Riesgo creado con folio, severidad calculada           |
| TC-090  | Severidad calculada             | 1. Probabilidad: 4, Impacto: 5                                     | Severidad: 20 (Rojo/Crítico)                          |
| TC-091  | Filtrar por severidad           | 1. Filtro severidad: Alta 2. Aplicar                                | Solo riesgos con severidad >= 13                      |
| TC-092  | Click en riesgo                 | 1. Click en fila de riesgo en la matriz                             | Página de detalle con link al proyecto                |
| TC-093  | Editar riesgo                   | 1. En detalle, click "Editar" 2. Modificar estado 3. Guardar       | Cambio registrado en historial                        |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-018: Módulo de Incidencias

**Épica:** EP-006
**Prioridad:** Alta
**Estimación:** L

**Como** Project Manager
**Quiero** registrar y dar seguimiento a incidencias del proyecto
**Para** resolver problemas que afectan la ejecución del proyecto

### Campos de la incidencia
| Campo                | Tipo         | Obligatorio |
|----------------------|--------------|-------------|
| Folio                | Auto         | Sí          |
| Título               | Text         | Sí          |
| Descripción          | Textarea     | Sí          |
| Proyecto             | Dropdown     | Sí          |
| Tipo                 | Dropdown     | Sí (Acción/Incidencia/Decisión) |
| Prioridad            | Dropdown     | Sí (Alta/Media/Baja)            |
| Responsable          | Dropdown     | Sí          |
| Fecha reporte        | Date (auto)  | Sí          |
| Fecha compromiso     | Date         | Sí          |
| Estado               | Dropdown     | Sí (Abierto/En progreso/Resuelto/Cerrado) |
| Resolución           | Textarea     | No          |
| Comentarios          | Textarea     | No          |

### Filtros
- Proyecto, Tipo (AID), Estado, Prioridad, Responsable, Fecha (rango)

### Matriz
- Folio, Título, Proyecto, Tipo, Prioridad, Estado, Responsable, Fecha compromiso

### Criterios de aceptación
- [ ] Botón "+ Nueva Incidencia"
- [ ] El tipo AID (Acción, Incidencia, Decisión) permite clasificar los registros
- [ ] Alerta visual cuando fecha compromiso está vencida y estado no es "Cerrado"
- [ ] Detalle con link al proyecto y historial de cambios
- [ ] Contador de AIDs abiertos alimenta el KPI del dashboard

### Casos de prueba
| ID      | Escenario                         | Pasos                                                              | Resultado esperado                                    |
|---------|-----------------------------------|---------------------------------------------------------------------|-------------------------------------------------------|
| TC-094  | Crear incidencia                  | 1. Click "+ Nueva Incidencia" 2. Llenar 3. Guardar                  | Incidencia creada con folio                           |
| TC-095  | Incidencia vencida                | 1. Crear incidencia con fecha compromiso pasada                     | Indicador visual de vencimiento                       |
| TC-096  | Filtrar por tipo AID              | 1. Filtro tipo: "Decisión" 2. Aplicar                               | Solo registros tipo Decisión                          |
| TC-097  | Cerrar incidencia                 | 1. Editar incidencia 2. Estado: "Cerrado" 3. Llenar resolución      | Estado actualizado, desaparece de AIDs abiertos       |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-019: Módulo de Cambios

**Épica:** EP-006
**Prioridad:** Alta
**Estimación:** M

**Como** Project Manager
**Quiero** gestionar solicitudes de cambio en el proyecto
**Para** controlar modificaciones al alcance, tiempo o costo del proyecto

### Campos del cambio
| Campo                | Tipo         | Obligatorio |
|----------------------|--------------|-------------|
| Folio                | Auto         | Sí          |
| Título               | Text         | Sí          |
| Descripción del cambio| Textarea    | Sí          |
| Proyecto             | Dropdown     | Sí          |
| Tipo de cambio       | Dropdown     | Sí (Alcance/Tiempo/Costo/Recurso) |
| Impacto              | Textarea     | Sí          |
| Solicitado por       | Text/Dropdown| Sí          |
| Fecha solicitud      | Date (auto)  | Sí          |
| Estado               | Dropdown     | Sí (En revisión/Aprobado/Rechazado/Implementado) |
| Aprobado por         | Dropdown     | No          |
| Fecha aprobación     | Date         | No          |
| Comentarios          | Textarea     | No          |

### Filtros
- Proyecto, Tipo de cambio, Estado, Fecha (rango)

### Matriz
- Folio, Título, Proyecto, Tipo, Estado, Solicitado por, Fecha solicitud

### Criterios de aceptación
- [ ] Botón "+ Nuevo Cambio"
- [ ] Flujo de aprobación: En revisión → Aprobado/Rechazado → Implementado
- [ ] Solo usuarios con permiso pueden aprobar/rechazar cambios
- [ ] Detalle con link al proyecto
- [ ] Contador de cambios en revisión alimenta el KPI del dashboard

### Casos de prueba
| ID      | Escenario                       | Pasos                                                               | Resultado esperado                                     |
|---------|----------------------------------|----------------------------------------------------------------------|--------------------------------------------------------|
| TC-098  | Crear solicitud de cambio       | 1. Click "+ Nuevo Cambio" 2. Llenar 3. Guardar                      | Cambio creado en estado "En revisión"                  |
| TC-099  | Aprobar cambio                  | 1. PM/PMO abre detalle 2. Click "Aprobar"                           | Estado: "Aprobado", registra aprobador y fecha         |
| TC-100  | Rechazar cambio                 | 1. PM/PMO abre detalle 2. Click "Rechazar" 3. Comentario            | Estado: "Rechazado" con motivo                         |
| TC-101  | Sin permiso de aprobación       | 1. Login como miembro 2. Intentar aprobar                            | Botón no visible o deshabilitado                       |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-020: Módulo de Documentos

**Épica:** EP-006
**Prioridad:** Media
**Estimación:** M

**Como** Project Manager
**Quiero** subir y organizar documentos asociados al proyecto
**Para** centralizar la información documental del proyecto

### Campos del documento
| Campo                | Tipo         | Obligatorio |
|----------------------|--------------|-------------|
| Folio                | Auto         | Sí          |
| Nombre               | Text         | Sí          |
| Descripción          | Text         | No          |
| Proyecto             | Dropdown     | Sí          |
| Categoría            | Dropdown     | Sí (Plan, Reporte, Contrato, Otro) |
| Archivo              | File upload  | Sí          |
| Versión              | Number (auto)| Sí          |
| Subido por           | Auto         | Sí          |
| Fecha                | Date (auto)  | Sí          |

### Filtros
- Proyecto, Categoría, Fecha (rango), Nombre (búsqueda)

### Matriz
- Folio, Nombre, Proyecto, Categoría, Versión, Subido por, Fecha, Acción (descargar)

### Criterios de aceptación
- [ ] Botón "+ Nuevo Documento"
- [ ] Soporte para múltiples versiones del mismo documento
- [ ] Tipos de archivo permitidos: PDF, XLSX, DOCX, PPTX, PNG, JPG
- [ ] Tamaño máximo configurable (default 25MB)
- [ ] Descarga directa desde la matriz
- [ ] Preview de documentos PDF e imágenes (futuro)

### Casos de prueba
| ID      | Escenario                       | Pasos                                                              | Resultado esperado                                    |
|---------|----------------------------------|--------------------------------------------------------------------|-------------------------------------------------------|
| TC-102  | Subir documento                 | 1. Click "+ Nuevo Documento" 2. Llenar datos 3. Subir archivo      | Documento registrado, versión 1                       |
| TC-103  | Subir nueva versión             | 1. En detalle de documento 2. "Nueva versión" 3. Subir archivo     | Versión incrementada, historial visible               |
| TC-104  | Descargar documento             | 1. Click en ícono de descarga en la matriz                         | Archivo descargado                                    |
| TC-105  | Archivo no permitido            | 1. Intentar subir .exe                                             | Error: "Tipo de archivo no permitido"                 |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-021: Módulo de Lecciones Aprendidas

**Épica:** EP-006
**Prioridad:** Media
**Estimación:** S

**Como** Project Manager
**Quiero** registrar lecciones aprendidas durante el proyecto
**Para** generar conocimiento reutilizable para futuros proyectos

### Campos
| Campo                | Tipo         | Obligatorio |
|----------------------|--------------|-------------|
| Folio                | Auto         | Sí          |
| Título               | Text         | Sí          |
| Descripción          | Textarea     | Sí          |
| Proyecto             | Dropdown     | Sí          |
| Categoría            | Dropdown     | Sí (Éxito/Mejora/Error) |
| Fase del proyecto    | Dropdown     | Sí          |
| Recomendación        | Textarea     | Sí          |
| Registrado por       | Auto         | Sí          |
| Fecha                | Date (auto)  | Sí          |

### Filtros
- Proyecto, Categoría, Fase, Fecha (rango)

### Matriz
- Folio, Título, Proyecto, Categoría, Fase, Registrado por, Fecha

### Criterios de aceptación
- [ ] Botón "+ Nueva Lección"
- [ ] Lecciones consultables cross-proyecto (con permisos)
- [ ] Búsqueda por texto en título y descripción

### Casos de prueba
| ID      | Escenario                       | Pasos                                                        | Resultado esperado                                    |
|---------|----------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-106  | Registrar lección               | 1. Click "+ Nueva Lección" 2. Llenar 3. Guardar              | Lección registrada con folio                          |
| TC-107  | Buscar lección cross-proyecto   | 1. Buscar lección por texto desde otro proyecto              | Resultados de múltiples proyectos (con permisos)      |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-022: Módulo de Minutas

**Épica:** EP-006
**Prioridad:** Media
**Estimación:** M

**Como** Project Manager
**Quiero** registrar minutas de reuniones del proyecto
**Para** documentar acuerdos, compromisos y seguimiento de reuniones

### Campos
| Campo                | Tipo              | Obligatorio |
|----------------------|-------------------|-------------|
| Folio                | Auto              | Sí          |
| Título de la reunión | Text              | Sí          |
| Proyecto             | Dropdown          | Sí          |
| Fecha de reunión     | Date              | Sí          |
| Participantes        | Multi-select      | Sí          |
| Temas tratados       | Textarea          | Sí          |
| Acuerdos/Compromisos | Textarea/Lista    | Sí          |
| Próxima reunión      | Date              | No          |
| Documentos adjuntos  | File upload       | No          |
| Registrado por       | Auto              | Sí          |

### Filtros
- Proyecto, Fecha (rango), Participante

### Matriz
- Folio, Título, Proyecto, Fecha, Participantes (#), Registrado por

### Criterios de aceptación
- [ ] Botón "+ Nueva Minuta"
- [ ] Los acuerdos/compromisos pueden generar incidencias tipo "Acción" automáticamente (futuro)
- [ ] Minutas exportables a PDF (futuro)
- [ ] Detalle con link al proyecto

### Casos de prueba
| ID      | Escenario                       | Pasos                                                        | Resultado esperado                                    |
|---------|----------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-108  | Crear minuta                    | 1. Click "+ Nueva Minuta" 2. Llenar 3. Guardar               | Minuta registrada con folio                           |
| TC-109  | Ver detalle de minuta           | 1. Click en minuta en la matriz                               | Detalle completo con participantes y acuerdos         |
| TC-110  | Filtrar por fecha               | 1. Seleccionar rango de fechas 2. Aplicar                     | Solo minutas en ese rango                             |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |
