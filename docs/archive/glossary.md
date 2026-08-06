---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Glosario del dominio PMO-aaS

**ID:** `DOC-GLOSSARY`
**Uso:** referencia canónica para claves i18n, variables, nombres de tablas y documentación.

---

## Términos de negocio (ES → EN)

| Español | Inglés (clave i18n) | Definición |
|---|---|---|
| PMO | `pmo` | Project Management Office. Entidad que supervisa portafolio de proyectos. |
| Portafolio | `portfolio` | Conjunto de todos los programas y proyectos de un tenant. |
| Programa | `program` | Agrupación de proyectos con objetivos estratégicos comunes (opcional). |
| Proyecto | `project` | Esfuerzo temporal con alcance, tiempo y presupuesto definidos. |
| Solicitud de proyecto | `projectRequest` | Formulario previo a la aprobación que crea el proyecto. |
| Tenant | `tenant` | Cliente del SaaS. Aísla datos, usuarios, configuración. |
| Organización | `organization` | Entidad jurídica dentro de un tenant (matriz, filial, unidad). |
| Unidad de negocio | `businessUnit` | Segmento operativo de una organización (campo texto libre). |
| Folio | `folio` | Identificador legible auto-generado (`PRJ-2026-001`). |
| Fase | `phase` | Etapa del proyecto: Planificación, Ejecución, Soporte, Cerrado. |
| Riesgo | `risk` | Evento incierto que puede afectar objetivos. Tiene P×I = severidad. |
| Incidencia | `issue` | Hecho ocurrido que impacta el proyecto (AID). |
| AID | `aid` | Acción / Incidencia / Decisión — sub-tipo de incidencia. |
| Cambio | `changeRequest` | Solicitud formal de modificación de alcance/tiempo/costo/recurso. |
| Documento | `document` | Artefacto versionado del proyecto (PDF, XLSX, DOCX…). |
| Lección aprendida | `lesson` | Aprendizaje capitalizable cross-proyecto. |
| Minuta | `minute` | Registro estructurado de una reunión con acuerdos. |
| Patrocinador | `sponsor` | Persona que autoriza recursos y defiende el proyecto. |
| Responsable | `owner` | Persona accountable de un ítem (riesgo, tarea, doc). |
| Semáforo de salud | `healthStatus` | Indicador Verde/Amarillo/Rojo del estado del proyecto. |
| Avance | `progress` | % completado del proyecto o tarea. |
| Presupuesto | `budget` | Monto asignado en MXN. Se compara planeado vs real. |
| Plan vs Real | `planVsActual` | Comparativa de fecha/costo/avance planeado vs ejecutado. |
| Lineamiento estratégico | `strategicAlignment` | Vínculo del proyecto con objetivo corporativo. |
| Soft delete | `softDelete` | Borrado lógico (`is_active=false`, no DELETE físico). |
| Hard delete | `hardDelete` | Borrado físico permanente (sólo Super Admin, con confirmación). |

---

## Términos técnicos

| Término | Definición |
|---|---|
| JWT | JSON Web Token, portador de identidad y claims (sub, org_ids, is_superadmin). |
| Refresh token | Token de larga duración para renovar access tokens sin re-login. |
| RLS | Row-Level Security de PostgreSQL, aísla datos por `tenant_id`. |
| RBAC | Role-Based Access Control — permisos por rol y módulo. |
| RSC | React Server Components. |
| MPP | Formato binario propietario de Microsoft Project. |
| MPXJ | Librería Java para leer .mpp / .xml / .xlsx de MS Project. |
| Gantt | Diagrama de barras temporal que muestra tareas y dependencias. |
| WBS | Work Breakdown Structure — descomposición jerárquica de tareas. |
| FS/SS/FF/SF | Tipos de dependencia entre tareas (Finish-Start, Start-Start, etc.). |
| Ollama | Runtime local para modelos LLM con API REST compatible. |
| Tokens (IA) | Unidades en que el modelo procesa texto (~¾ de palabra en español). |
| Chunking | División de texto largo en fragmentos solapados para el LLM. |
| Tenant header | Header HTTP `X-Tenant-ID` que escopa las peticiones. |
| Audit log | Tabla `audit_log` que registra cada acción sensible. |
| Folio prefix | Prefijo por entidad: `SOL-`, `PRJ-`, `RIS-`, `INC-`, `CHG-`, `DOC-`, `LEC-`, `MIN-`. |

---

## Estados y enumeraciones

### Estados de solicitud (`project_requests.status`)
- `in_review` — En revisión
- `approved` — Aprobada
- `rejected` — Rechazada
- `needs_info` — Pendiente información

### Estados de proyecto (`projects.phase`)
- `planning` — En planificación
- `execution` — En ejecución
- `support` — En soporte
- `closed` — Cerrado

### Estados de riesgo (`risks.status`)
- `identified` — Identificado
- `analyzing` — En análisis
- `mitigating` — En mitigación
- `materialized` — Materializado
- `closed` — Cerrado

### Estados de incidencia (`issues.status`)
- `open`, `in_progress`, `resolved`, `closed`

### Tipos de cambio (`change_requests.type`)
- `scope`, `time`, `cost`, `resource`

### Estados de cambio (`change_requests.status`)
- `in_review`, `approved`, `rejected`, `implemented`

### Severidad de riesgo (calculada `probability × impact`)
- `1-5` → Verde (baja)
- `6-12` → Amarillo (media)
- `13-25` → Rojo (alta/crítica)

### Salud del proyecto (`projects.health_status`)
- `green` — Todo en orden
- `yellow` — Atención (desvío ≤ 10%)
- `red` — Crítico (desvío > 10% o riesgo alto activo)
