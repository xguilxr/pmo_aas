# EP020 — Catálogo de Secciones Atómicas (DRAFT / WIP)

> **Estado:** Draft de diseño. NO es epic oficial todavía. Vive en
> `docs/epics/drafts/` mientras lo iteramos. Se promueve a
> `docs/epics/EP020-report-builder.md` cuando el catálogo cierre.
>
> **Propósito:** definir el conjunto base de "secciones atómicas" que
> el Report Builder Nivel 4 ofrece en su canvas drag-and-drop. Estas
> mismas secciones son la unidad de composición de los reportes Nivel
> 1/2/3 también (un solo motor, no dos).
>
> **Owner:** xguilxr · **Editor:** Claude · **Última actualización:** 2026-05-21

---

## Convenciones

Cada sección se identifica con `S-XX` (2 dígitos, secuencial dentro del
catálogo). Los IDs **no se reusan** aunque una sección se elimine.

Template de spec completo (a aplicar sección por sección en lote
posterior):

```
### S-XX — <nombre>
Categoría: <una de la tabla de categorías>
Propósito: <1 línea>
Fuente de datos: <tablas / endpoints / servicios>
Parámetros configurables: <ej. periodo, top N, filtro por área, agrupación>
Variantes visuales: <tabla | card | barra | donut | timeline | semáforo | texto | gauge>
Tamaño en canvas: <1/3 | 1/2 | 2/3 | full>
Soporta IA: <sí/no — si sí: qué prompt y qué genera>
Dependencias de datos: <qué módulos deben tener data>
Disponible en niveles: <1 PMO | 2 Org | 3 Proyecto | 4 Custom>
```

## Categorías

| Cat | Nombre | Descripción |
|---|---|---|
| **HDR** | Identidad / Header | Portada, info del proyecto, branding |
| **EST** | Estado / Semáforo | RAG global, resumen ejecutivo, tendencia |
| **AVN** | Avance | % avance, curva S, hitos, entregables |
| **RAID** | RAID | Riesgos, issues, acuerdos, decisiones |
| **PLN** | Plan / Cronograma | Tareas críticas, vencidas, próximas, Gantt |
| **EQP** | Equipo / Recursos | Composición, carga, cambios |
| **PPS** | Presupuesto / Costo | Resumen, variaciones, gasto por categoría |
| **QCH** | Calidad / Cambios | Solicitudes de cambio, lecciones |
| **NAR** | Narrativa / IA | Texto libre, logros, próximos pasos |
| **KPI** | KPIs custom | Tiles configurables, tablas |
| **PRT** | Portafolio (cross-proyecto) | Solo Niveles 1/2 |

---

## Lista seed (~36 candidatos para podar/ajustar)

### HDR — Identidad / Header
- **S-01** Portada (cover) — título, periodo, logo cliente
- **S-02** Información del proyecto — código, sponsor, PM, fecha de corte, periodo

### EST — Estado / Semáforo
- **S-03** Semáforo global RAG — alcance / tiempo / costo / calidad
- **S-04** Resumen ejecutivo — texto IA o manual
- **S-05** Tendencia de estado — últimos N periodos (mini-timeline)

### AVN — Avance
- **S-06** % Avance plan vs real — gauge / card grande
- **S-07** Curva S — planificado vs real acumulado
- **S-08** Avance por área/WBS — barras horizontales
- **S-09** Hitos próximos y cumplidos — timeline
- **S-10** Entregables del periodo — tabla

### RAID
- **S-11** Top N riesgos por severidad — tabla con dueño y mitigación
- **S-12** Top N issues abiertos
- **S-13** Decisiones del periodo
- **S-14** Acciones / acuerdos pendientes — con responsable y fecha
- **S-15** Matriz probabilidad × impacto — heatmap 5x5

### PLN — Plan / Cronograma
- **S-16** Tareas en camino crítico
- **S-17** Tareas vencidas
- **S-18** Próximas 2 semanas — agenda
- **S-19** Snapshot Gantt — imagen renderizada del Gantt

### EQP — Equipo / Recursos
- **S-20** Composición del equipo / actores activos
- **S-21** Carga por responsable — horas/tareas
- **S-22** Cambios de equipo en el periodo

### PPS — Presupuesto / Costo
- **S-23** Resumen presupuesto — planificado / ejecutado / comprometido / disponible
- **S-24** Variación de costo — CV / CPI
- **S-25** Gasto por concepto / categoría — pie o tabla

### QCH — Calidad / Cambios
- **S-26** Solicitudes de cambio del periodo
- **S-27** Lecciones aprendidas del periodo

### NAR — Narrativa / IA
- **S-28** Bloque narrativo libre — rich text editable
- **S-29** Logros destacados — IA
- **S-30** Próximos pasos / foco siguiente periodo — IA

### KPI — KPIs custom
- **S-31** KPI tile — valor + delta vs periodo anterior + sparkline
- **S-32** Tabla de KPIs configurable

### PRT — Portafolio (Niveles 1 PMO / 2 Org)
- **S-33** Mapa de proyectos por estado — grid o treemap
- **S-34** Top riesgos del portafolio
- **S-35** Avance promedio del portafolio — barras
- **S-36** Proyectos en alerta — lista con razón

---

## Iteración

- **Ronda actual:** seed list (este doc).
- **Siguiente:** owner poda / agrega / renombra. Luego pasamos al spec
  completo en lotes de 4-5 secciones por ronda.
- **Cierre:** catálogo final → promover a `EP020-report-builder.md`,
  crear US-110 con AC/TC, abrir issue en GitHub.
