---
responsable: propietario
estado: vigente
revisado: 2026-08-03
revisar_cada: 90d
---

# Diagnóstico de brecha — dominio PMO

| Campo | Valor |
|---|---|
| Fecha | 2026-08-03 · commit `d79c31d` |
| Alcance | Semántica de gestión de proyectos del producto, contra el núcleo de §3 del rundown |
| Método | Modelos SQLAlchemy, tablas declaradas y literales en `apps/api/app/` |
| Qué **no** cubre | Calidad del código y arquitectura: eso es MCS, y está pendiente |

---

## 1. Resumen

El producto modela **más dominio PMO del que su documentación sugiere**. Hay 54 tablas, y
entre ellas están `project_charters`, `stakeholders`, `risks`, `issues`, `lessons`,
`risk_actions`, `change_requests`, `programs`, `task_dependencies` y
`project_health_evaluations`. Eso es un RAID completo, control de cambios y capa de
programa: bastante más que la mayoría de las herramientas de gama media.

**La brecha no es de cobertura. Es de definición.** Los conceptos existen como tablas pero
no como términos con significado único y regla de cálculo. Tres ejemplos medidos, no
impresiones:

1. Dos vocabularios simultáneos para las fases del ciclo de vida
2. Tres para el estado de salud, y dos paletas de color distintas para el mismo semáforo
3. Ninguna línea base, lo que deja sin sustento cualquier afirmación de desviación

Y una ausencia estructural: **cero anclaje a estándar**. Búsqueda sobre todo el repositorio
vivo de `PMBOK|PRINCE2|ISO 21500|ISO 21502|ISO 21504|P3O|P3M3|IPMA|ANSI/EIA-748`: **cero
coincidencias**. `EVM` aparece una vez, como `KPI-09 CV/CPI`, dentro de un borrador
(`docs/epics/drafts/EP020-secciones-atomicas.md:1002`) y condicionada a «solo si PPS activo».

---

## 2. Lo que ya está y está bien

Conviene decirlo antes de la lista de brechas, porque cambia qué tan caro es cerrarlas.

| Concepto | Evidencia | Comentario |
|---|---|---|
| RAID | tablas `risks`, `issues`, `lessons`, `risk_actions` | Separa riesgo de incidencia. Es la distinción que más se confunde y aquí está bien |
| Acta de constitución | `project_charters` | Entidad propia, no un campo de texto |
| Interesados | `stakeholders` | Entidad propia |
| Control de cambios | `change_requests`, `change_approvers`, `approval_tokens` | Con aprobadores y tokens: es control formal, no un campo de estado |
| Capa de programa | `programs`, `projects.program_id` | Existe el nivel intermedio |
| WBS y jerarquía | `tasks.wbs`, `parent_id`, `outline_level`, `position` | Estructura de descomposición real |
| Red de dependencias | `task_dependencies`, `predecessors`, `successors`, `is_critical` | Insumo suficiente para ruta crítica y para DCMA |
| Dinero en decimal | `projects.budget: Decimal`, `actual_budget: Decimal` | **Correcto.** No es coma flotante. Es el error más común y aquí no está |
| Trazabilidad | `audit_log`, `metric_snapshots`, `project_health_evaluations` | Hay historia, no solo estado actual |

---

## 3. Brechas, por gravedad

### B-1 · No existe línea base — **ALTA**

`grep -rli baseline apps/api/app/models/` → **0 modelos**. No hay `baselines`, ni
`baseline_start`, ni `baseline_end`, ni `baseline_cost`.

**Consecuencia.** Sin línea base no existe desviación. `tasks.start_date` / `end_date` son
las fechas *actuales*: cuando alguien mueve una tarea, la fecha original se pierde. El
producto no puede responder «¿esto se atrasó?» — solo «¿cuándo es ahora?». Toda variación
de cronograma, todo EVM y buena parte de un informe de estado dependen de esta pieza.

**Es la brecha keystone.** Las B-4 y B-5 no se pueden cerrar sin ella.

### B-2 · Las fases no corresponden a ningún ciclo de vida — **ALTA**

```
PHASES = ["planning", "execution", "support"]
```

Faltan inicio y cierre. `"support"` no es una fase de ciclo de vida en PMBOK, ISO 21502 ni
PRINCE2 — es operación, que por definición empieza **cuando el proyecto terminó**. Un
proyecto en fase `support` es un proyecto cerrado, y el modelo no puede distinguirlos.

Y conviven con literales sueltos en español:

| Literal | Ocurrencias |
|---|---|
| `"planning"` | 14 |
| `"execution"` | 13 |
| `"Inicio"` / `"inicio"` | 5 |
| `"Ejecución"` | 1 |
| `"Cierre"` | 1 |

Dos vocabularios, dos idiomas, y uno de ellos reconoce fases que el enum no admite.

### B-3 · El semáforo de salud tiene tres vocabularios y dos paletas — **ALTA**

| Vocabulario | Ocurrencias |
|---|---|
| `green` / `yellow` / `red` | 39 / 33 / 36 |
| `amber` | 3 |
| `Verde` / `Amarillo` / `Rojo` | 3 |

`amber` es el término correcto en RAG (*Red / Amber / Green*), el estándar en P3O y
PRINCE2; `yellow` es el informal. Hoy están mezclados.

Peor: **dos definiciones de color para el mismo concepto**, con valores distintos.

```
HEALTH_DONUT_COLOR = {"green": "#1F8A5B", "yellow": "#B26B12", "red": "#C0392B"}
HEALTH_HEX         = {"green": "#16a34a", "yellow": "#eab308", "red": "#dc2626"}
```

Un mismo proyecto en verde se ve de dos verdes distintos según el componente. Es
exactamente el patrón que la skill `auditar-deriva` persigue: el mismo concepto definido en
dos sitios.

**Y lo de fondo:** `health_status` es un campo almacenado con `health_source` y
`health_reason`. No encontré regla de derivación. Un semáforo sin fórmula es una opinión
con color — y es el número que más mira un patrocinador.

### B-4 · EVM no es posible con el modelo actual — **MEDIA**

`planned_value`, `earned_value`, `actual_cost` → **0 modelos**. El presupuesto vive solo a
nivel proyecto (`projects.budget`, `actual_budget`); **las tareas no tienen costo ni
esfuerzo**. Sin costo por tarea y sin línea base no hay PV, ni EV, ni AC, y por tanto no hay
CPI, SPI, EAC, ETC ni VAC.

El `KPI-09 CV/CPI` del borrador de EP020 no es implementable hoy. Conviene saberlo antes de
prometerlo en una demo.

**Gravedad media, no alta**, porque EVM puede no ser el camino: ver §4.

### B-5 · Avance sin definición — **MEDIA**

`tasks.progress: int` y `projects.progress: int`, sin declarar el método. Hay al menos
cuatro formas legítimas de calcularlo —por duración, por esfuerzo, por entregables
completados, o declarado por el responsable— y dan números distintos. Sin declarar cuál es,
el avance del proyecto no es reconciliable con el de sus tareas.

### B-6 · No hay capa de portafolio — **BAJA**

`portafolio` aparece como etiqueta de función de área (`portfolio_function`, constante
`PORTAFOLIO`), no como entidad. La jerarquía real es
`tenant → organization → business_unit → department → program → project`.

**No es necesariamente un defecto.** Esa jerarquía es organizacional y sirve. Solo conviene
no llamarle portafolio a un área, porque en ISO 21504 y MoP portafolio es *un conjunto de
componentes agrupado para gestión estratégica*, que no coincide con la estructura
organizativa.

### B-7 · Beneficios como texto libre — **BAJA**

`benefits` aparece en `project_charter` y `project_request` como campo. No hay entidad,
métrica ni seguimiento. La realización de beneficios es el eje de MSP y de la conversación
con un patrocinador, pero es la brecha más cara de cerrar y la menos urgente.

---

## 4. Recomendación

En orden de impacto sobre esfuerzo:

1. **Cerrar B-2 y B-3 con el glosario** (`02-GLOSARIO.md`). Son renombrados y una regla de
   derivación. Días, no semanas, y eliminan la ambigüedad más visible para el usuario.
2. **Unificar las dos paletas de salud** en una sola definición. Horas.
3. **Introducir línea base (B-1).** Es una migración y un cambio de escritura, no un módulo
   nuevo. Desbloquea todo lo demás.
4. **Elegir entre EVM y calidad de cronograma.** Mi recomendación es **calidad de
   cronograma tipo DCMA 14-point**: no exige costos por tarea, se alimenta de
   `task_dependencies`, `predecessors`, `successors` e `is_critical` —que ya tenés por el
   importador de MS Project— y es un diferenciador real. EVM exige antes B-1 y costo por
   tarea; es mucho más caro y no necesariamente más vendible.
5. **Beneficios y portafolio**, si un cliente los pide.

Nada de esto exige adoptar una familia de estándares. Todo es compatible con adoptarla
después.
