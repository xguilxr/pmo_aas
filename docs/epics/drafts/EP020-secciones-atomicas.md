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

## Modos de composición de reporte (template-level)

Concepto que vive en el nivel **template**, no en el de sección.
Define cómo se orquestan las secciones cuando el reporte se renderiza.

### Modo A — Por sección (matriz "sección × área")
Cada sección es un bloque discreto en el orden que el PM la puso en el canvas.
Dentro de cada sección, los items se ordenan por:
**área asc → fecha de finalización asc**.

Aplicación: **Reporte de Avance** (existente, US-038).
Ejemplo:
```
1. Hitos
     · Área Compras  | 22-may  · …
     · Área TI       | 28-may  · …
2. Acciones
     · Área Compras  | 23-may  · …
     · Área TI       | 24-may  · …
```

### Modo B — Por área (matriz invertida "área × sección")
La agrupación externa es **área**; dentro de cada área se renderizan las
secciones secuencialmente. Cada área es su propio "mini-reporte".

Aplicación: **Reporte de Seguimiento** (existente, US-039).
Ejemplo:
```
Área Compras
  ├ Hitos:    · 22-may …
  ├ Acciones: · 23-may …
  └ Riesgos:  · alto …
Área TI
  ├ Hitos:    · 28-may …
  ├ Acciones: · 24-may …
  └ Riesgos:  · medio …
```

### Implicaciones para el catálogo de secciones
- Toda sección debe ser capaz de filtrarse por una sola área (para que
  el Modo B la pueda repetir N veces).
- Toda sección debe exponer su data en un shape que permita ambos modos
  (la diferencia es de **render**, no de query).
- El template del reporte declara `composition_mode: "by_section" | "by_area"`.

---

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

#### S-16 Críticos — SPEC CERRADO
```
Categoría: PLN
Propósito: tareas críticas del proyecto — las que NO pueden retrasarse
           sin impactar fecha fin u otro hito clave.

Fuente: tasks WHERE is_critical = true
  Criterio único: flag manual del PM marcado en form de edición de tarea,
  símil al checkbox "Hito".

Estados (mismos 4 que S-09):
  CUMPLIDO / PRÓXIMO / CRÍTICO (≤3d) / VENCIDO
  Mismas ventanas (cumplidos 14d default, vencidos TODOS hasta hoy).

Visual default: (δ) Tabla compacta priorizada
  Columnas: Tarea | Fecha plan fin | Estado (chip color) | Responsable | Área
  Orden default: fecha plan fin asc

No mostrar: predecesoras / dependencias (los reportes deben ser ligeros;
            el detalle se consulta en el plan).

Filtros: aplica filtro por área del bloque de parámetros transversales.
         Sin filtro de área = todas las críticas del proyecto.

Soporta IA: no (sección directa, sin narrativa).
Niveles: 3, 4.

DEPENDENCIA DEL SISTEMA (ENH a EP006 Plan — se abre como issue separado):
  - REEMPLAZAR la columna `critical` existente por BOOLEAN NOT NULL DEFAULT FALSE.
    (Hoy existe una columna `critical` con otra lógica; se elimina para no
    mantener dos columnas similares con semánticas distintas → riesgo de confusión.)
  - Migración Alembic: convertir valores existentes (lo que sea TRUTHY → true,
    el resto false) y dropear la columna vieja.
  - Plantilla import (Excel/CSV): columna "Crítica" (Sí/No)
  - Form edición tarea: checkbox "Crítica" hermano del checkbox "Hito"
  - Mapping desde MS Project import: si el archivo trae una columna "Critical"
    (o equivalente), mapearla al BOOLEAN.
```

#### S-17 Delayed — SPEC CERRADO
```
Categoría: PLN
Propósito: lista operativa de tareas retrasadas, optimizada para
           "cobrar" a áreas (o personas) que no están cumpliendo.

Fuente:
  tasks WHERE fecha_plan_fin < hoy
        AND completed_at IS NULL
  Exclusiones dinámicas (calculadas en tiempo de render del reporte):
    - is_milestone = true  → excluir SI S-09 está en el mismo reporte
    - is_critical  = true  → excluir SI S-16 está en el mismo reporte
  Si S-09 o S-16 no están en el reporte, S-17 los incluye.

Visual default: tabla compacta agrupada por ÁREA (collapsable)
  Cabecera área:   Área X    [12 retrasadas · prom. 8d]
  Filas:           Tarea | Fecha plan | Días retraso (chip color) | Responsable
  Orden default dentro de cada área: días de retraso desc.

Bandas de retraso (chips de color):
  1-7d    amarillo claro
  8-14d   ámbar
  15-21d  naranja
  >21d    rojo intenso

Modos:
  resumen (default): contador por área + promedio días + top 10 por área
  detalle:           listado completo por área

Parámetros específicos:
  agrupación:    área (default) | responsable | sin agrupar
  top_n_resumen: 10 (default)
  bandas_color:  sí/no (default sí)

Soporta IA: opcional — narrativa por área ("área X acumula 12 tareas con
            promedio 8d retraso; 3 superan 21d y requieren escalación")

Niveles: 3, 4.
```

#### S-18 Próximas (En curso + Arranca) — SPEC CERRADO
```
Categoría: PLN
Propósito: visión operativa de qué se está trabajando AHORA + qué arranca
           en el periodo que viene. Complementa lo que YA se cierra
           (cubierto por S-09 hitos próximos y S-16 críticos próximos).

Estructura: la sección tiene DOS sub-bloques visuales.

  ───────────────────────────────────────────────
  BLOQUE A — EN CURSO
  ───────────────────────────────────────────────
  Fuente:
    tasks WHERE fecha_plan_inicio < hoy
          AND fecha_plan_fin   >= hoy
          AND completed_at IS NULL
    Excluye:
      - is_milestone = true  → SI S-09 está en el reporte
      - is_critical  = true  → SI S-16 está en el reporte
      - retrasadas (fecha_plan_fin < hoy ya no aplica acá; van a S-17)

  Visual: tabla agrupada por ÁREA
    Cabecera: Área X    [4 en curso]
    Columnas: Tarea | Fecha plan fin | Días restantes | Responsable
    Orden: fecha plan fin asc (las que cierran antes primero)

  ───────────────────────────────────────────────
  BLOQUE B — ARRANCA (próximos 21 días)
  ───────────────────────────────────────────────
  Fuente:
    tasks WHERE fecha_plan_inicio >= hoy
          AND fecha_plan_inicio <= hoy + lookahead
          AND completed_at IS NULL
    Mismas exclusiones dinámicas que Bloque A.

  Visual: tabla agrupada por SEMANA → luego por ÁREA dentro de cada semana
    Semana 22-may a 28-may   [8 tareas]
      └ Área X   [3]
          Tarea | Inicio | Fin | Responsable
      └ Área Y   [5]
          Tarea | Inicio | Fin | Responsable
    Orden dentro de área: fecha plan inicio asc.

Lookahead default: 21 días (configurable 7 / 14 / 21 / 30 / 60).
                   Alineado con la banda mayor de S-17 (>21d).

Modos:
  resumen (default): título + fechas + responsable + área
  detalle:           agrega WBS path, duración estimada, predecesoras

Parámetros específicos:
  lookahead:           7 / 14 / 21 / 30 / 60 días (default 21)
  mostrar_en_curso:    sí/no (default sí — Bloque A visible)
  mostrar_arranca:     sí/no (default sí — Bloque B visible)
  agrupación_arranca:  semana→área (default) | semana | área | sin agrupar
  agrupación_curso:    área (default) | responsable | sin agrupar

Soporta IA: opcional — resumen ejecutivo de carga próxima por área
            ("equipo X concentrará 60% de la carga arrancante; área Y
            cierra 5 entregables esta semana").

Niveles: 3, 4.
```

### RAID — orden **A → R → D → I**
Cada subsección con los mismos parámetros transversales (área, ventana, top N, ordenamiento, agrupación).

> **Nomenclatura de la plataforma:**
> - **A = Acciones** (no "Acuerdos"). Los Acuerdos de minutas se ven más como Decisiones (D).
>   Las Acciones se crean directo en el tab RAID o desde sugerencias de minutas.
> - **R = Riesgos**
> - **D = Decisiones** (incluye acuerdos de minuta convertidos)
> - **I = Issues** (incidentes)

- **S-14** **Acciones (A)** — pendientes con responsable y fecha compromiso
- **S-11** **Riesgos (R)** — top N por severidad, con dueño y mitigación
- **S-13** **Decisiones (D)** — del periodo, con sponsor que decide
- **S-12** **Issues (I)** — abiertos, default modo resumen
- **S-15** Matriz probabilidad × impacto — heatmap 5×5 (visualización complementaria de Riesgos)

#### S-14 Acciones (A) — SPEC CERRADO
```
Categoría: RAID (primero en orden A→R→D→I)
Propósito: lista de acciones pendientes del proyecto. Origen: tab RAID
           directo o sugerencias convertidas desde minutas.

Fuente: action_items (tabla unificada)
  Columna `origin`: "raid_direct" | "minute_<id>"
  (en reportes se muestra como "Manual" o "Minuta YYYY-MM-DD")

Estados:
  PENDIENTE   azul    completed_at IS NULL AND fecha_compromiso > hoy+3d
  PRÓXIMO     ámbar   fecha_compromiso en (hoy, hoy+3d]
  VENCIDO     rojo    fecha_compromiso < hoy AND completed_at IS NULL
  CUMPLIDO    verde   completed_at dentro de ventana_cumplidos

Visual default: (δ) Tabla compacta priorizada
  Columnas: Acción | Compromiso | Estado (chip) | Responsable | Área | Origen
  Orden default: ÁREA asc → FECHA COMPROMISO asc
  (sin agrupar — el ordenamiento por área ya da bloques visuales claros)

Modos:
  resumen (default): solo pendientes + próximos + vencidos
  detalle:           agrega cumplidos del periodo + descripción larga

Parámetros específicos:
  ventana_cumplidos: 7 / 14 / 30 días (default 14)
  mostrar_cumplidos: sí/no (default no en resumen, sí en detalle)

Soporta IA: opcional — narrativa de seguimiento de compromisos vencidos
            por área ("área X tiene 3 acciones vencidas, la más antigua
            de 12-may sin avance").

Niveles: 3, 4.
```

#### S-11 Riesgos (R) — SPEC CERRADO
```
Categoría: RAID (segundo en A→R→D→I)
Propósito: panorama de riesgos del proyecto, priorizados por severidad.
           Audiencia: sponsor / dirección.

Fuente: risks
  Sub-bloque ABIERTOS:  status IN ('open', 'mitigating', 'monitoring')
  Sub-bloque MITIGADOS: status = 'mitigated' AND closed_at dentro de ventana

Severidad: probabilidad (1-5) × impacto (1-5) → score 1-25
Buckets:
  CRÍTICO (rojo)     score >= 15
  ALTO    (naranja)  score 9-14
  MEDIO   (amarillo) score 4-8
  BAJO    (verde)    score 1-3

Visual default: (δ) Tabla compacta priorizada — DOS sub-tablas

  ──── Riesgos abiertos ────
  Columnas: Riesgo | Severidad (chip) | Prob×Imp | Estado | Dueño | Área
  Orden default: severidad desc → área asc → fecha_identificación asc

  ──── Riesgos mitigados (ventana) ────
  Columnas: Riesgo | Severidad al mitigar | Fecha mitigación | Dueño | Área
  Orden: fecha_mitigación desc

NOTA: NO incluir columna "Mitigación corta" (densidad innecesaria).
      El plan de mitigación se consulta en el módulo Riesgos directo.

Modo Avance (composición A): orden severidad → área → fecha
Modo Seguimiento (composición B): filtrar por área del bloque, orden
                                   severidad desc → fecha asc

Modos:
  resumen (default): top N abiertos + mitigados de la ventana
  detalle:           todos los abiertos sin top N

Parámetros específicos:
  top_n_abiertos:    5 / 10 / 20 / todos (default 10)
  incluir_buckets:   multi-select (default crítico+alto+medio)
  ventana_mitigados: 7 / 14 / 30 días (default 14)
  mostrar_mitigados: sí/no (default sí)

Soporta IA: opcional — narrativa de top 3 críticos
            ("riesgo X concentra impacto en hito Y").

Niveles: 3, 4.
         Nivel 1/2: vista cross-proyecto agregada en S-34.
```

#### S-13 Decisiones (D) — SPEC CERRADO
```
Categoría: RAID (tercero en A→R→D→I)
Propósito: registro de decisiones tomadas + propuestas pendientes.
           Las decisiones generadas desde minutas son el MISMO registro
           (no sub-tipo separado), solo difieren en el origen.

Fuente: decisions (módulo separado de Changes)
  Campo `origin`: "raid_direct" | "minute_<id>"
  Mismo registro, solo distinto punto de creación.

Estados:
  TOMADA      verde   decision_date IS NOT NULL
  PROPUESTA   azul    decision_date IS NULL

  (estado "escalada" queda como follow-up del modelo; hoy los
   escalamientos se hacen ad-hoc como comentarios en el item.)

Visual default: (δ) Tabla compacta — DOS sub-tablas

  ──── Tomadas (en ventana) ────
  Columnas: Decisión | Fecha | Tomada por | Impacto | Origen | Área
  Orden: ÁREA asc → FECHA decisión desc

  ──── Pendientes / Propuestas (deuda activa, sin filtro de ventana) ────
  Columnas: Decisión | Propuesta por | Impacto | Origen | Área
  Orden: ÁREA asc → fecha_creación asc (más antiguas primero)

Campo Impacto: se toma directo del registro (no se calcula).
Origen en reporte: "Manual" si raid_direct, "Minuta YYYY-MM-DD" si minute_<id>.

Modo Avance: orden área → fecha
Modo Seguimiento (composición B): filtrar por área del bloque

Modos:
  resumen (default): tomadas (ventana) + propuestas (todas)
  detalle:           agrega contexto largo + alternativas si existen

Parámetros específicos:
  ventana_tomadas:    ventana del reporte (default)
  mostrar_propuestas: sí/no (default sí)

Soporta IA: opcional — síntesis de decisiones clave del periodo.

Niveles: 3, 4.
```

#### S-12 Issues (I) — SPEC CERRADO
```
Categoría: RAID (cuarto y último en A→R→D→I)
Propósito: incidencias / issues del proyecto. Mismo patrón que decisiones:
           los issues generados desde minutas son el MISMO registro que
           los creados en RAID directo.

Fuente: issues
  Campo `origin`: "raid_direct" | "minute_<id>"
  Campo `severity`: viene tal como esté declarado en el registro
                    (la sección no calcula, solo presenta)
  Campo `status`: viene del registro (debe tener su propio estado)

Visual default: (δ) Tabla compacta — DOS sub-tablas

  ──── Abiertos / En curso (sin filtro de ventana, deuda viva) ────
  Columnas: Issue | Severidad (chip) | Estado | Días abierto |
            Dueño | Origen | Área
  Orden: severidad desc → ÁREA asc → días_abierto desc
  ("días abierto" señala issues envejecidos sin atención)

  ──── Resueltos (en ventana del reporte) ────
  Columnas: Issue | Severidad | Fecha resolución | Dueño | Área
  Orden: fecha_resolución desc

Modo Avance: orden severidad → área → días/fecha
Modo Seguimiento (composición B): filtrar por área del bloque

Modos:
  resumen (default): top N abiertos + resueltos de la ventana
  detalle:           todos los abiertos sin top N + descripción larga

Parámetros específicos:
  top_n_abiertos:    5 / 10 / 20 / todos (default 10)
  ventana_resueltos: 7 / 14 / 30 días (default 14)
  mostrar_resueltos: sí/no (default sí)

Soporta IA: opcional — narrativa de top issues envejecidos.
            ("issue X lleva 18d abierto sin actividad reciente").

Niveles: 3, 4.
         Nivel 1/2: agregado cross-proyecto en S-34.
```

#### S-15 Matriz Probabilidad × Impacto — SPEC CERRADO
```
Categoría: RAID (complemento visual opcional de Riesgos)
Propósito: heatmap 5×5 que distribuye los riesgos abiertos por
           probabilidad × impacto. Es una vista visual bonita,
           NO obligatoria.

IMPORTANTE — Inclusión:
  Esta sección NO se incluye por default en los reportes base (Avance /
  Seguimiento). Solo aparece en reportes especializados de Riesgos, o
  cuando el PM la agrega manualmente en Nivel 4.
  Función: complemento o reemplazo de S-11 en esos casos.

Fuente: risks WHERE status IN ('open', 'mitigating', 'monitoring')

Visual default: matriz 5×5 numérica
  Eje Y: Impacto      (1 abajo → 5 arriba)
  Eje X: Probabilidad (1 izquierda → 5 derecha)
  Color de celda según bucket: CRÍTICO / ALTO / MEDIO / BAJO
  Contenido de celda: número de riesgos en esa combinación (badge)

  Si el reporte incluye S-11 también, la tabla complementaria con IDs
  y títulos ya se muestra naturalmente desde S-11; no se duplica acá.

Tamaño canvas: 1/2

Escala: 5×5 (decisión: mantener 5×5 por ahora; reducción a 3×3
        requeriría cambio de plataforma + migración de items, fuera
        de alcance de este epic).

Modo Avance: todos los riesgos abiertos del proyecto
Modo Seguimiento (composición B): filtrar por área del bloque.
                                  Si la matriz queda VACÍA en esa
                                  área → OCULTAR la sección para
                                  esa área (no renderizar el cuadro).

Variantes:
  (a) matriz numérica  → default
  (b) matriz con IDs   → opcional, denso
  (c) matriz antes/después → DESCARTADA (requería snapshots y
                              no aporta vs alternativas más simples)

Parámetros específicos:
  variante:          a / b (default a)
  incluir_mitigados: sí/no (default no — vista de "qué amenaza HOY")

Soporta IA: no (vista visual pura).

Niveles: 3, 4 (siempre opcional, nunca default).
```

#### S-06 % Avance plan vs real — SPEC CERRADO
```
Categoría: AVN
Propósito: KPI más visible del reporte — qué % del plan se ha ejecutado
           a la fecha de corte vs qué % debía estar ejecutado.

Fuente: tasks (todas las del proyecto, status != cancelled)

Método de cálculo del % real: CONFIGURABLE por tenant
  Setting del admin del tenant: `progress_calculation_method` enum,
  con 3 opciones más comunes:

    (a) "weighted_duration"   — DEFAULT recomendado
         % = Σ(progress_i × duración_planificada_i) / Σ(duración_planificada_i)
         Cada tarea pesa según cuánto tiempo planeado abarca.

    (b) "weighted_effort"
         % = Σ(progress_i × horas_estimadas_i) / Σ(horas_estimadas_i)
         Cada tarea pesa según esfuerzo planeado en horas.
         Requiere que las tareas tengan horas_estimadas pobladas.

    (c) "simple_count"
         % = tareas_terminadas / total_tareas
         Sin ponderación. Útil cuando todas las tareas son comparables
         en tamaño, o cuando no hay duración/horas confiables.

  El reporte consulta el setting y aplica el método correspondiente.
  Si el setting no existe, default = "weighted_duration".

Método del % planeado a fecha de corte:
  Default: lineal por duración planificada acumulada
  (curva S configurada por proyecto queda como follow-up)

Desviación: % real − % planeado (en puntos porcentuales)

Visual default: (a) card con gauge semicircular
  Centro:    % real (número grande)
  Subtítulo: "vs N% planeado"
  Delta:     ±N pp con color

  Color del % real según desviación:
    verde      ≥ −2 pp     (en o sobre plan)
    amarillo   −2 a −10 pp (ligero retraso)
    rojo       < −10 pp    (retraso material)
  (umbrales recomendados, configurables a futuro)

Variantes seleccionables:
  (a) card con gauge semicircular — default
  (b) barra horizontal plan vs real
  (c) tile minimalista solo número

Tamaño canvas: 1/3 (card individual)

Modo Avance: KPI agregado de todo el proyecto
Modo Seguimiento (composición B): se recalcula con tasks del área del
                                   bloque, mostrando avance de esa área

Parámetros específicos:
  variante:          a / b / c (default a)
  mostrar_delta_pp:  sí/no (default sí)
  mostrar_sparkline: sí/no (default no)

Soporta IA: opcional — interpretación corta.

Niveles: 3, 4.
         Nivel 1/2: se reusa como tile dentro de S-35 (avance promedio
         portafolio).

DEPENDENCIA DEL SISTEMA (ENH a EP007 Admin / EP001 Tenants):
  - tenants.progress_calculation_method ENUM
      ('weighted_duration', 'weighted_effort', 'simple_count')
      DEFAULT 'weighted_duration'
  - UI en admin del tenant para seleccionar método (radio buttons +
    explicación corta de cada opción).
  - Validación: si selecciona 'weighted_effort' y hay tareas sin
    horas_estimadas, mostrar warning ("X tareas sin horas estimadas
    se contarán con peso 0").
  - Migración Alembic.
```

#### S-07 Curva S — DESCARTADA
```
Estado: NO se implementa.
Razón: requiere rigidez del plan (snapshots históricos consistentes,
       re-baselining controlado, granularidad fija) que esta plataforma
       no impone. La flexibilidad del plan haría que la curva sea
       engañosa más que útil.
Acción: se elimina del catálogo. Si en el futuro se rigidiza el plan,
        re-evaluar.
```

#### S-08 Avance por WBS-1 / Área — SPEC CERRADO
```
Categoría: AVN
Propósito: barras horizontales con el % de avance de cada rama de
           WBS-1 (default) o área. Identifica rezagados de un vistazo.

Fuente: tasks agrupadas por WBS-1 (default) o por área
  Filtro de inclusión del grupo:
    Solo se incluyen grupos que tengan al menos una task con fecha
    plan inicio o fin DENTRO de la ventana del reporte.
    Grupos sin actividad en el periodo se omiten (no inflar reporte).

  Por cada grupo incluido:
    % avance = mismo cálculo que S-06 (respeta método del tenant)
    % planeado = lineal por duración a fecha de corte
    delta_pp = real − planeado

Visual default: barras horizontales con plan vs real
  Una fila por grupo:
    Grupo X   [██████████░░░░░░░░░░] 52%  vs 60% plan   −8 pp
  - Fondo gris (0-100%)
  - Relleno coloreado según delta (mismos umbrales S-06)
  - Chip a la derecha con delta pp

Orden default: % avance ASC (rezagados arriba — llaman atención primero)

Tamaño canvas: full

Modo Avance: todos los grupos con actividad en el periodo (sin top N)
Modo Seguimiento (composición B): SE OMITE (sería redundante con
                                   la composición por área)

Variantes seleccionables:
  (a) barras plan vs real (default)
  (b) solo barras de real
  (c) barras + contador tareas terminadas / total

Agrupación:
  por_WBS_1: default
  por_área:  alternativa

Parámetros específicos:
  agrupación: WBS-1 (default) / área
  variante:   a / b / c (default a)
  orden:      avance_asc (default)

Soporta IA: opcional — narrativa de grupos críticos.

Niveles: 3, 4.
         Nivel 1/2: vista por proyecto del portafolio → S-35.
```

#### S-10 Entregables del periodo — DIFERIDA v2.0
```
Estado: NO se implementa en v1.0.
Razón: el concepto de "entregable" formal no está configurado en la
       plataforma todavía. Requiere primero definir modelo de datos
       (módulo separado o flag sobre tasks/documents).
Acción: re-evaluar cuando se introduzca el concepto en plataforma.
        Mientras tanto, S-09 Hitos cubre parcialmente la función
        (los hitos suelen representar entregables clave).
Label issue: post-mvp, v2.0
```

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
