# EP-004: Dashboard - Panel del Project Manager

**Prioridad:** Alta
**Módulo:** Panel principal / Dashboard
**Dependencias:** EP-001 (Usuarios), EP-002 (Jerarquía), EP-005 (Proyectos)

---

## US-011: Tarjetas de KPIs principales

**Épica:** EP-004
**Prioridad:** Alta
**Estimación:** L

**Como** Project Manager o PMO Manager
**Quiero** ver tarjetas con indicadores clave (KPIs) en el dashboard
**Para** tener una visión rápida del estado general del portafolio

### KPIs requeridos (tarjetas con link al detalle)
| KPI                    | Descripción                                    | Link destino               |
|------------------------|------------------------------------------------|----------------------------|
| Proyectos Activos      | Cantidad de proyectos en ejecución             | Lista filtrada por activos |
| Solicitudes en Revisión| Solicitudes pendientes de aprobación           | Lista de solicitudes       |
| Riesgos Abiertos       | Total de riesgos con estado abierto            | Módulo de riesgos          |
| Cambios en Revisión    | Solicitudes de cambio pendientes               | Módulo de cambios          |
| Presupuesto Total      | Suma de presupuestos de proyectos activos      | Vista de presupuestos      |
| Avance Promedio        | Porcentaje promedio de avance de proyectos activos | Lista de proyectos     |
| Riesgos Severos        | Riesgos con severidad alta/crítica             | Riesgos filtrados          |
| AIDs Abiertos          | Acciones, Incidencias, Decisiones abiertas     | Módulo de incidencias      |

### Criterios de aceptación
- [ ] Cada tarjeta muestra el KPI con su valor numérico actualizado
- [ ] Cada tarjeta es clickeable y navega a la vista detallada correspondiente
- [ ] Los valores se calculan en tiempo real o con caché de máximo 5 minutos
- [ ] Las tarjetas respetan los permisos del usuario (solo datos de proyectos asignados)
- [ ] Diseño responsive: grid de 4 columnas en desktop, 2 en tablet
- [ ] Indicador visual de tendencia (subida/bajada) respecto al periodo anterior (futuro)

### Casos de prueba
| ID      | Escenario                         | Pasos                                                        | Resultado esperado                                    |
|---------|-----------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-057  | KPIs se muestran correctamente    | 1. Login 2. Ver dashboard                                    | Todas las tarjetas muestran valores numéricos         |
| TC-058  | Click en tarjeta KPI              | 1. Click en "Proyectos Activos"                              | Navega a lista de proyectos filtrada por activos      |
| TC-059  | Datos filtrados por permisos      | 1. Login como PM con 3 proyectos 2. Ver dashboard            | KPIs reflejan solo datos de sus 3 proyectos           |
| TC-060  | Dashboard sin proyectos           | 1. Login como usuario nuevo sin proyectos                    | Tarjetas muestran 0, mensaje de bienvenida            |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-012: Gráficos del dashboard

**Épica:** EP-004
**Prioridad:** Alta
**Estimación:** L

**Como** PMO Manager
**Quiero** ver gráficos visuales del estado del portafolio
**Para** analizar tendencias y tomar decisiones basadas en datos

### Gráficos requeridos
1. **Pie chart: Proyectos por fase** — Distribución de proyectos según su fase actual (Planificación, Ejecución, Soporte, Cerrado)
2. **Bar graph: Avance promedio por fase** — Barra por cada fase mostrando el % de avance promedio
3. **Bar graph: Presupuesto por tipo de proyecto** — Barra por tipo de proyecto con su presupuesto asignado
4. **Pie chart: Salud del portafolio** — Distribución de proyectos por estado de salud (Verde, Amarillo, Rojo)

### Criterios de aceptación
- [ ] Los 4 gráficos se renderizan correctamente con datos reales
- [ ] Tooltips al hover mostrando valores exactos
- [ ] Leyendas visibles y legibles
- [ ] Colores consistentes: Verde (sano), Amarillo (atención), Rojo (crítico)
- [ ] Gráficos se adaptan al tamaño de pantalla
- [ ] Con 0 datos, se muestra un placeholder en lugar de un gráfico vacío
- [ ] Datos filtrados según permisos del usuario

### Casos de prueba
| ID      | Escenario                         | Pasos                                                        | Resultado esperado                                    |
|---------|-----------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-061  | Gráficos con datos                | 1. Login como PMO Manager 2. Ver dashboard                   | 4 gráficos con datos correctos                        |
| TC-062  | Tooltip en gráfico                | 1. Hover sobre segmento de pie chart                         | Tooltip con valor numérico y porcentaje               |
| TC-063  | Sin datos                         | 1. Login sin proyectos asignados                             | Placeholders con mensaje "Sin datos disponibles"      |
| TC-064  | Consistencia de datos             | 1. Comparar valores de gráficos con KPIs                     | Los datos son consistentes entre gráficos y tarjetas  |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-013: Matriz Plan vs Real por proyecto

**Épica:** EP-004
**Prioridad:** Alta
**Estimación:** M

**Como** PMO Manager
**Quiero** ver una tabla comparativa de plan vs real para cada proyecto
**Para** identificar desviaciones en tiempo, costo y avance

### Columnas de la matriz
| Columna             | Tipo       | Descripción                                |
|---------------------|------------|--------------------------------------------|
| Proyecto            | Text/Link  | Nombre del proyecto (clickeable al detalle)|
| Inicio              | Date       | Fecha de inicio real                       |
| Fin                 | Date       | Fecha de fin planificada                   |
| Plan (MXN)          | Currency   | Presupuesto planificado                    |
| Real (MXN)          | Currency   | Gasto real a la fecha                      |
| Avance Planeado (%) | Percentage | Porcentaje de avance planeado              |
| Avance (%)          | Percentage | Porcentaje de avance real                  |
| Salud Proyecto      | Indicator  | Semáforo: Verde/Amarillo/Rojo              |

### Criterios de aceptación
- [ ] La matriz muestra todos los proyectos activos del usuario
- [ ] Nombre del proyecto es clickeable y navega al detalle
- [ ] Formato de moneda en MXN con separador de miles
- [ ] Indicador de salud como semáforo visual (ícono o color de fondo)
- [ ] Ordenamiento por cualquier columna (click en encabezado)
- [ ] Paginación si hay más de 10 proyectos
- [ ] Resaltado visual cuando Avance Real < Avance Planeado (desviación)

### Casos de prueba
| ID      | Escenario                         | Pasos                                                        | Resultado esperado                                    |
|---------|-----------------------------------|--------------------------------------------------------------|-------------------------------------------------------|
| TC-065  | Matriz con datos                  | 1. Ver dashboard con proyectos activos                       | Tabla con datos correctos, semáforos visibles          |
| TC-066  | Click en proyecto                 | 1. Click en nombre de proyecto en la matriz                  | Navega al detalle del proyecto                        |
| TC-067  | Ordenar por columna               | 1. Click en encabezado "Avance (%)"                          | Tabla ordenada por avance                             |
| TC-068  | Desviación visible                | 1. Proyecto con avance real < planeado                       | Fila resaltada en color de advertencia                |
| TC-069  | Formato de moneda                 | 1. Verificar columnas de presupuesto                         | Formato: $1,500,000 MXN                              |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |
