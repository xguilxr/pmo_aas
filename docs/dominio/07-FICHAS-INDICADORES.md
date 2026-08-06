---
tipo: referencia
responsable: propietario
estado: borrador
revisado: 2026-08-06
revisar_cada: 90d
---

# Fichas de indicador

Trabaja **MCS DAT-10**: «cada indicador DEBE disponer de ficha versionada con
fórmula, grano, inclusiones, exclusiones, zona horaria, tratamiento de nulos y
responsable».

> **Estado: borrador.** Las fórmulas se **derivaron del código**, no se
> inventaron, y cada ficha dice de qué función sale. Lo que necesita tu palabra
> está marcado **[owner]**. Mientras queden marcas, esto no cierra `DAT-10`:
> una ficha con un hueco es una ficha que alguien rellenará suponiendo.

**Zona horaria — regla general.** Todo lo que se guarda con marca temporal usa
`DateTime(timezone=True)` y se almacena en **UTC**. Los cortes por fecha
(`date.today()`, ventanas) se evalúan en la **zona del servidor**, no en la del
inquilino. **[owner]** Con inquilinos en husos distintos, «las tareas vencidas
hoy» cambia según dónde corra el proceso. Hace falta decidir si el corte es UTC,
la zona del inquilino, o la de quien mira.

---

## Lo primero: `avg_progress` y `progress_avg` **no son lo mismo**

Preguntaste por ellas y la respuesta importa más que las dos fichas juntas.

| | `avg_progress` | `progress_avg` |
|---|---|---|
| **Grano** | **Un proyecto** | **Cartera** (conjunto de proyectos activos) |
| **Qué mide** | Avance del proyecto según su plan | Promedio de los avances de los proyectos |
| **De dónde sale** | `operational_reports.py:166` | `dashboard.py:210` |
| **Redondeo** | Entero (`round_half_up`) | Sin redondear |

**La raíz de cálculo sí es única**, y eso es lo que salva a `DAT-09`: las dos
terminan en `compute_plan_rollup_progress` (`plan_metadata.py:233`), la del
tablero a través de `effective_progress_map` → `plan_rollup_map`. No hay dos
implementaciones del avance de un proyecto.

**Lo que sí está mal son los nombres.** `avg_progress` y `progress_avg` son casi
anagramas y designan cosas de grano distinto. Cualquiera que lea las dos en un
mismo informe asumirá que son la misma cifra en dos sitios.

**[owner] Propuesta de renombrado:** `avance_proyecto_pct` y
`avance_cartera_pct`. Cruza API y web, así que va con ADR, migración de contrato
y ventana de compatibilidad, igual que `wbs` → `wbs_code`.

---

## Familia: avance

### `avg_progress` — avance del proyecto

| Campo | Valor |
|---|---|
| **Fórmula** | Promedio simple del avance efectivo de las **raíces WBS**. Cada padre es el promedio recursivo de sus hijos. `sum(rollup[raíz]) / nº raíces` |
| **Grano** | Proyecto |
| **Unidad** | Porcentaje 0-100, entero |
| **Incluye** | Todas las tareas del proyecto. Raíz = tarea sin ningún ancestro WBS existente (ENH-197) |
| **Excluye** | Nada por estado: una tarea cancelada sigue pesando **[owner] ¿debería?** |
| **Nulos** | Sin tareas → `None`, y el llamador cae al `Project.progress` manual. **Cero tareas no es cero por ciento** |
| **Ponderación** | **Ninguna**: promedio simple de raíces. Una raíz con 40 tareas pesa lo mismo que una con 1 **[owner] ¿ponderar por duración o esfuerzo?** |
| **Firma** | **[owner]** |

> El promedio simple de raíces es decisión del owner registrada en el docstring
> de `compute_plan_rollup_progress`, no un accidente.

### `progress_avg` — avance de la cartera

| Campo | Valor |
|---|---|
| **Fórmula** | `sum(avance_efectivo) / nº proyectos activos` |
| **Grano** | Cartera, filtrada por organización y por alcance de quien mira |
| **Incluye** | Proyectos **activos**, no borrados (`deleted_at IS NULL`) |
| **Excluye** | Proyectos fuera del alcance del usuario (SEG-04). **Dos personas ven cifras distintas del mismo inquilino, y es correcto** |
| **Nulos** | Sin proyectos → `0`. **[owner] Debería ser «—»:** cero proyectos no es cero por ciento (DAT-12) |
| **Firma** | **[owner]** |

### `on_time_pct` · `overdue_pct` · `overdue_days` · `delayed_count`

**[owner]** Pendientes de derivar. Necesitan una decisión previa que las
atraviesa: **¿tarde respecto de qué?** Sin línea base (D-6, sin abrir), «retraso»
solo puede medirse contra la fecha planeada *actual*, que se mueve cada vez que
alguien la cambia — con lo que un proyecto puede no llegar nunca tarde.

---

## Familia: carga y capacidad

Esta familia **ya tiene sus reglas escritas** en el encabezado de
`services/capacity.py` (decisiones del owner, 2026-07-08). Las fichas las
formalizan sin cambiarlas.

### `allocation_pct` — asignación de un recurso a un proyecto

| Campo | Valor |
|---|---|
| **Fórmula** | Valor declarado en `project_participations.allocation_pct`. No se calcula |
| **Grano** | Par recurso-proyecto |
| **Incluye** | Participaciones con `status='activa'` cuyo rango `[start_date, end_date]` **intersecta** la ventana. Rango nulo = abierto |
| **Excluye** | Tentativas (se reportan aparte) y vencidas |
| **Nulos** | **Explícito y bien resuelto:** `NULL` = asignación sin cuantificar. **No suma**, pero se cuenta en `unquantified_count` para que se vea la cobertura del dato |
| **Firma** | **[owner]** |

### `capacity_pct` / `over_pct` — saturación

| Campo | Valor |
|---|---|
| **Fórmula** | `demanda = Σ allocation_pct` de activas en ventana. Se compara contra `actors.project_capacity_pct`, **nunca contra 100** |
| **Grano** | Recurso, con agregación por función de portafolio, área y sub-área |
| **Unidad** | La sobreasignación va en **puntos porcentuales**, no en porcentaje del porcentaje |
| **Ventana** | `today` (0 d), `week` (7), `3weeks` (21), `month` (30), hacia adelante desde hoy |
| **Umbrales** | Por inquilino en `settings.capacity_thresholds`: `over > red_over` (10) → rojo; `over > yellow_over` (0) → amarillo |
| **Nulos** | Igual que arriba: no suman, se reportan |
| **Firma** | **[owner]** |

> **Comparar contra `project_capacity_pct` y no contra 100 es la decisión más
> importante de esta familia.** Un recurso que dedica el 60 % a proyectos y el
> resto a operación se satura al 60, no al 100.

---

## Familia: presupuesto

### `budget_plan` · `budget_actual` · `burn_index`

| Campo | Valor |
|---|---|
| **Fórmula** | `burn_index = budget_actual / budget_plan` **[owner] confirmar** |
| **Unidad** | **Sin declarar, y es el hueco de `DAT-01`.** La unidad del dinero es la moneda, y hoy solo existe como `tenant.settings.currency` |
| **Nulos** | **[owner]** ¿Un proyecto sin presupuesto planeado tiene índice infinito, cero, o «—»? |
| **Firma** | **[owner]** |

> **Esta familia no cierra sin decidir la moneda** y sin el renombrado de
> `DAT-02` (`budget_plan` → `budget_plan_mxn` o con moneda en el tipo).
> Sumar presupuestos de dos inquilinos con monedas distintas hoy no está
> impedido por nada.

---

## Familia: salud

### `health_green` · `health_yellow` · `health_red`

| Campo | Valor |
|---|---|
| **Fórmula** | Conteo de proyectos por estado de salud |
| **Origen del valor** | Automático o manual: `health_source` distingue `auto` de intervención humana, y `health_reason` guarda el motivo |
| **Vocabulario** | `green` / `yellow` / `red`. **`amber` está retirado** (D-1, migración 0091, ADR-030) |
| **Nulos** | **[owner]** ¿Un proyecto sin evaluar cuenta como verde o queda fuera del total? Hoy la respuesta la da el código; debería darla la ficha |
| **Firma** | **[owner]** |

---

## Familia: volumen

`project_count` · `task_count` · `program_count` · `organization_count` ·
`business_unit_count` · `department_count` · `users_total` · `tenants_total`

| Campo | Valor |
|---|---|
| **Fórmula** | Conteo simple |
| **Incluye** | Filas con `deleted_at IS NULL` |
| **Excluye** | Lo borrado lógicamente, y lo que quede fuera del alcance de quien mira |
| **Nulos** | No aplica: un conteo sin filas **es** cero, y aquí sí se muestra `0` |
| **Firma** | **[owner]** |

> Es la única familia donde `0` es un valor legítimo y no un hueco disfrazado.

---

## Qué falta para cerrar `DAT-10`

1. Resolver las marcas **[owner]** de arriba, empezando por las cuatro que
   cambian números en pantalla: ponderación del avance, nulos de `progress_avg`,
   moneda, y salud sin evaluar.
2. Derivar las fichas de la familia de cumplimiento, que depende de la línea
   base (D-6).
3. Firmar cada una. **Un indicador sin responsable no tiene a quién preguntarle
   cuando dos informes no cuadran**, que es exactamente cuando se necesita.
