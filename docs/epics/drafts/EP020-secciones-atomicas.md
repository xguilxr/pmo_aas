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
| **AVN** | Avance | % avance, curva S, snapshot Gantt WBS-1, entregables |
| **PLN** | Plan / Cronograma | **Hitos, críticos y retrasadas** (NO el detalle completo) |
| **RAID** | RAID — orden **A → R → D → I** | Acuerdos, Riesgos, Decisiones, Issues |
| **EQP** | Equipo / Recursos | Composición, carga, cambios |
| **PPS** | Presupuesto / Costo | Resumen, variaciones, gasto por categoría |
| **QCH** | Calidad / Cambios | Solicitudes de cambio, lecciones |
| **NAR** | Narrativa / IA | Texto libre, logros, próximos pasos |
| **KPI** | KPIs / Indicadores | Tiles configurables, tablas, avances clave |
| **PRT** | Portafolio (cross-proyecto) | Solo Niveles 1/2 |

---

## Parámetros transversales (aplican a casi toda sección operativa)

Estos parámetros viven **en el contenedor de sección** y se ofrecen
automáticamente cuando la sección expone data tabular o temporal.
No hay que repetirlos en cada spec.

| Param | Valores | Default | Aplica a |
|---|---|---|---|
| **Área / segmento** | "todas" \| `area_id[]` | todas | PLN, RAID, EQP, AVN, KPI |
| **Ventana temporal** | corte único \| rango (desde→hasta) \| "periodo del reporte" | periodo del reporte | PLN, RAID, AVN, EQP, QCH |
| **Solo items con fecha dentro de la ventana** | sí / no | sí | PLN (hitos, críticos, próximas), RAID acciones |
| **Top N** | 5 / 10 / 20 / todos | 10 | RAID riesgos/issues, PLN delayed |
| **Modo** | resumen \| detalle | resumen | PLN delayed, RAID issues |
| **Ordenamiento** | fecha plan fin asc \| severidad desc \| área | fecha plan fin asc | PLN, RAID |
| **Agrupación** | ninguna \| por área \| por responsable \| por tipo | ninguna | PLN, RAID, EQP |

**Regla:** "modo resumen" = una línea por item con totales; "modo detalle" = expansión con campos completos. Default siempre resumen para
no inflar reportes de planes grandes.

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
- **S-10** Entregables del periodo — tabla
- **S-19** Snapshot Gantt WBS-1 — imagen renderizada del Gantt a primer nivel de WBS (no detalle)

### PLN — Plan / Cronograma (orientado a Hitos + Críticos + Delayed)
> Filosofía: en planes de 100-1000+ tareas el detalle completo es contraproducente.
> Estas 4 secciones cubren lo esencial. Si el PM necesita más detalle, lo pide
> agregando otra sección o configurando el modo en "detalle".

#### S-09 Hitos — SPEC CERRADO
```
Categoría: PLN
Propósito: hitos del proyecto agrupados por estado, visualmente digeribles.

Fuente: tasks WHERE is_milestone = true

Estados (4):
  CUMPLIDO  verde   completed_at dentro de ventana_cumplidos
  PRÓXIMO   azul    fecha_plan en (hoy, hoy+lookahead]
  CRÍTICO   ámbar   fecha_plan en (hoy, hoy+3d]   (regla operativa, no configurable)
  VENCIDO   rojo    fecha_plan < hoy AND completed_at IS NULL

Ventanas:
  cumplidos:  últimas 2 semanas (configurable, default 14d)
  próximos:   amarrado a la ventana del reporte
  vencidos:   TODOS hasta hoy (sin filtro de ventana — deuda viva)
  críticos:   próximos 3 días (fijo)

Visual default: (β) Tarjetones agrupados por estado
  - 4 columnas: Cumplidos | Próximos | Críticos | Vencidos
  - cada hito = mini-card con: título, fecha plan, fecha real/proyectada,
    variación días, responsable, área
  - color de borde por estado

Variantes seleccionables (toggle en panel parámetros):
  (α) Timeline horizontal con tarjetas sobre eje temporal
  (γ) Mini-Gantt WBS-1 con rombos de hitos

Parámetros específicos (extra a transversales):
  lookahead_próximos:        14 / 30 / 60 días (default 30, sobreescribe ventana si menor)
  ventana_cumplidos:         7 / 14 / 30 días (default 14)
  mostrar_variación_días:    sí/no (default sí, aplica a cumplidos y vencidos)
  columnas_opcionales:       responsable, área, WBS path

Soporta IA: opcional — narrativa corta por hito vencido o crítico
            ("vencido 5d por dependencia con X")

Niveles: 3 (Proyecto), 4 (Custom).
         Nivel 2 versión agregada del programa (X cumplidos / Y planificados).
```

### RAID — orden **A → R → D → I**
Cada subsección con los mismos parámetros transversales (área, ventana, top N, ordenamiento, agrupación).
- **S-14** **Acuerdos / Acciones (A)** — primero. Pendientes con responsable y fecha compromiso
- **S-11** **Riesgos (R)** — top N por severidad, con dueño y mitigación
- **S-13** **Decisiones (D)** — del periodo, con sponsor que decide
- **S-12** **Issues / Incidentes (I)** — abiertos, default modo resumen
- **S-15** Matriz probabilidad × impacto — heatmap 5×5 (visualización complementaria de Riesgos)

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
