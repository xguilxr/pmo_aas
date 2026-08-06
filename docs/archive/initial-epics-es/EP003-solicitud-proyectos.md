---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# EP-003: Solicitud de Proyectos

**Prioridad:** Alta
**Módulo:** Formulario de solicitud para aprobación de proyectos
**Dependencias:** EP-001 (Usuarios), EP-002 (Jerarquía)

---

## US-009: Formulario de solicitud de proyecto

**Épica:** EP-003
**Prioridad:** Alta
**Estimación:** L

**Como** usuario de la plataforma
**Quiero** llenar un formulario de solicitud de proyecto con toda la información necesaria
**Para** someter una iniciativa al proceso de aprobación del PMO

### Campos del formulario
| Campo                              | Tipo                  | Obligatorio | Notas                                            |
|------------------------------------|-----------------------|-------------|--------------------------------------------------|
| Fecha de solicitud                 | Date (auto)           | Sí*         | Auto-rellenado con fecha actual                  |
| Nombre de solicitante              | Text (auto)           | Sí*         | Auto-rellenado con usuario en sesión             |
| Correo de solicitante              | Email (auto)          | Sí*         | Auto-rellenado con correo del usuario en sesión  |
| Título de la iniciativa            | Text                  | Sí          |                                                  |
| Descripción                        | Textarea              | Sí          |                                                  |
| Objetivo                           | Textarea              | Sí          |                                                  |
| Empresa                            | Dropdown              | Sí          | Organizaciones activas del sistema               |
| Unidad de Negocio                  | Dropdown/Text         | Sí          |                                                  |
| Departamento                       | Dropdown/Text         | Sí          |                                                  |
| Sub-departamento                   | Text                  | No          |                                                  |
| Dueño/Patrocinador/Sponsor        | Text                  | Sí          |                                                  |
| Correo Dueño/Patrocinador         | Email                 | Sí          |                                                  |
| Lineamiento Estratégico            | Dropdown/Text         | Sí          |                                                  |
| Beneficios/Justificación           | Textarea              | Sí          |                                                  |
| Presupuesto                        | Number (moneda)       | No          | Formato MXN con separador de miles               |
| ¿Qué sucede si no se hace?        | Textarea              | Sí          |                                                  |
| Personas clave involucradas        | Multi-input/Tags      | Sí          | Nombres + roles                                  |
| Entregables esperados/Alcance      | Textarea              | Sí          |                                                  |
| Otros documentos                   | File upload (múltiple)| No          | PDF, Excel, Word, PPT, imágenes                  |
| Observaciones/Comentarios          | Textarea              | No          |                                                  |

### Criterios de aceptación
- [ ] Todos los campos obligatorios (*) se validan antes de enviar
- [ ] Los campos auto-rellenables toman datos del usuario en sesión y la fecha del sistema
- [ ] El campo de presupuesto acepta formato numérico con separador de miles (MXN)
- [ ] El upload de documentos acepta: PDF, XLSX, XLS, DOCX, DOC, PPTX, PPT, PNG, JPG, JPEG
- [ ] Tamaño máximo por archivo: configurable (default 25MB)
- [ ] Al enviar, la solicitud queda en estado "En revisión"
- [ ] Se genera un folio único para la solicitud
- [ ] El solicitante recibe confirmación en pantalla con el número de folio
- [ ] La solicitud es visible en el dashboard del PMO Manager en "Solicitudes en revisión"
- [ ] Formulario disponible en español e inglés

### Casos de prueba
| ID      | Escenario                             | Pasos                                                                      | Resultado esperado                                    |
|---------|---------------------------------------|----------------------------------------------------------------------------|-------------------------------------------------------|
| TC-044  | Envío exitoso con todos los campos    | 1. Llenar todos los campos 2. Adjuntar documento 3. Enviar                 | Solicitud creada con folio, mensaje de confirmación   |
| TC-045  | Envío con solo campos obligatorios    | 1. Llenar solo campos obligatorios 2. Enviar                               | Solicitud creada correctamente                        |
| TC-046  | Campos auto-rellenados                | 1. Abrir formulario                                                        | Fecha, nombre y correo pre-llenados correctamente     |
| TC-047  | Validación de campos obligatorios     | 1. Dejar campos obligatorios vacíos 2. Enviar                              | Errores de validación en campos faltantes             |
| TC-048  | Upload de archivo válido              | 1. Adjuntar archivo PDF de 5MB                                             | Archivo cargado exitosamente                          |
| TC-049  | Upload de archivo muy grande          | 1. Adjuntar archivo de 30MB                                                | Error: "El archivo excede el tamaño máximo permitido" |
| TC-050  | Upload de tipo no permitido           | 1. Adjuntar archivo .exe                                                   | Error: "Tipo de archivo no permitido"                 |
| TC-051  | Formato de presupuesto               | 1. Ingresar 1500000 en presupuesto                                         | Se muestra como $1,500,000 MXN                        |
| TC-052  | Correo de patrocinador inválido      | 1. Ingresar correo inválido en campo de correo patrocinador                | Error de formato de correo                            |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-010: Revisión y aprobación de solicitudes

**Épica:** EP-003
**Prioridad:** Alta
**Estimación:** M

**Como** PMO Manager
**Quiero** revisar las solicitudes de proyecto pendientes y aprobarlas o rechazarlas
**Para** controlar qué iniciativas se convierten en proyectos formales

### Criterios de aceptación
- [ ] Las solicitudes en revisión se muestran en una lista filtrable
- [ ] El PMO Manager puede ver el detalle completo de cada solicitud
- [ ] Opciones: Aprobar, Rechazar, Solicitar más información
- [ ] Al aprobar, se puede iniciar la creación del proyecto directamente desde la solicitud (datos pre-cargados)
- [ ] Al rechazar, se debe ingresar un motivo de rechazo
- [ ] Al solicitar más información, el solicitante recibe una notificación
- [ ] Se registra quién aprobó/rechazó y cuándo

### Casos de prueba
| ID      | Escenario                         | Pasos                                                                | Resultado esperado                                    |
|---------|-----------------------------------|----------------------------------------------------------------------|-------------------------------------------------------|
| TC-053  | Aprobar solicitud                 | 1. Ver solicitud pendiente 2. Click "Aprobar"                        | Estado cambia a "Aprobada", opción de crear proyecto  |
| TC-054  | Rechazar solicitud                | 1. Ver solicitud 2. Click "Rechazar" 3. Ingresar motivo             | Estado cambia a "Rechazada", motivo registrado        |
| TC-055  | Solicitar más información         | 1. Ver solicitud 2. Click "Solicitar más info" 3. Escribir comentario| Notificación al solicitante, estado "Pendiente info"  |
| TC-056  | Crear proyecto desde solicitud    | 1. Aprobar solicitud 2. Click "Crear Proyecto"                      | Formulario de proyecto pre-cargado con datos de solicitud |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |
