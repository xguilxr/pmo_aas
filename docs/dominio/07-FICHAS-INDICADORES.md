---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 90d
---

# Fichas de indicador

Trabaja **MCS DAT-10**: «cada indicador DEBE disponer de ficha versionada con
fórmula, grano, inclusiones, exclusiones, zona horaria, tratamiento de nulos y
responsable».

> **Firmadas por el owner el 2026-08-06.** Las fórmulas se **derivaron del
> código**, no se inventaron, y cada ficha dice de qué función sale. Las
> decisiones del owner van marcadas **[owner 2026-08-06]** con su razón cuando
> la dio; donde no hubo nota, la ficha quedó aprobada tal como estaba.
>
> Tres respuestas **cambiaron código**, no solo este documento. Están señaladas.

**Zona horaria — regla general.** Todo lo que se guarda con marca temporal usa
`DateTime(timezone=True)` y se almacena en **UTC**. Los cortes por fecha
(`date.today()`, ventanas) se evalúan en la **zona del servidor**.
**Sigue abierto:** con inquilinos en husos distintos, «las tareas vencidas hoy»
cambia según dónde corra el proceso. Es el único hueco de este documento que no
tiene respuesta, y no bloquea las fichas porque afecta al corte, no a la
fórmula. **Responsable: owner.**

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

**Propuesta de renombrado, sin resolver:** `avance_proyecto_pct` y
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
| **Excluye** | Nada por estado: una tarea cancelada sigue pesando |
| **Nulos** | Sin tareas → `None`, y el llamador cae al `Project.progress` manual. **Cero tareas no es cero por ciento** |
| **Ponderación** | **Simple, confirmada [owner 2026-08-06]**: «la tarea raíz ya hace un promedio de las subtareas, por lo que ya las toma en consideración». La profundidad del árbol es la que pondera |
| **Firma** | owner · 2026-08-06 |

> El promedio simple de raíces es decisión del owner registrada en el docstring
> de `compute_plan_rollup_progress`, no un accidente.

### `progress_avg` — avance de la cartera

| Campo | Valor |
|---|---|
| **Fórmula** | `sum(avance_efectivo) / nº proyectos activos` |
| **Grano** | Cartera, filtrada por organización y por alcance de quien mira |
| **Incluye** | Proyectos **activos**, no borrados (`deleted_at IS NULL`) |
| **Excluye** | Proyectos fuera del alcance del usuario (SEG-04). **Dos personas ven cifras distintas del mismo inquilino, y es correcto** |
| **Nulos** | Sin proyectos → **`null`, que se pinta «—» [owner 2026-08-06]**. Cero proyectos no es cero por ciento. **Cambió el código**: `dashboard.py` devolvía `0` |
| **Firma** | owner · 2026-08-06 |

### `on_time_pct` · `overdue_pct` · `overdue_days` · `delayed_count`

| Campo | Valor |
|---|---|
| **Referencia del retraso** | **La fecha planeada ACTUAL [owner 2026-08-06]**, no una línea base |
| **Firma** | owner · 2026-08-06 |

**Razón del owner, y conviene leerla entera porque explica el producto:** «esta
plataforma no es para *enforzar* como tal, sino para poder gestionar las
actividades con flexibilidad; en cambios deberían registrar cambios de fechas
planeadas».

Es decir: **la consecuencia conocida se acepta a propósito.** Medir contra la
fecha actual significa que mover la fecha borra el retraso, y por tanto que un
proyecto puede no llegar nunca tarde. Eso sería un defecto en una herramienta de
control y es el comportamiento buscado en una de gestión.

**Lo que sostiene la decisión es la trazabilidad, no la métrica**: el rastro de
que la fecha se movió vive en el control de cambios. Si ese registro no captura
los cambios de fecha planeada, el retraso deja de ser auditable por ninguna vía
— y ahí sí habría un hueco. **Queda como verificación pendiente.**

La línea base (D-6) sigue sin abrir y no bloquea estas fichas: daría una segunda
lectura —«tarde contra lo comprometido»—, que es información distinta y
complementaria, no un arreglo de esta.

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
| **Firma** | owner · 2026-08-06, sin cambios |

### `capacity_pct` / `over_pct` — saturación

| Campo | Valor |
|---|---|
| **Fórmula** | `demanda = Σ allocation_pct` de activas en ventana. Se compara contra `actors.project_capacity_pct`, **nunca contra 100** |
| **Grano** | Recurso, con agregación por función de portafolio, área y sub-área |
| **Unidad** | La sobreasignación va en **puntos porcentuales**, no en porcentaje del porcentaje |
| **Ventana** | `today` (0 d), `week` (7), `3weeks` (21), `month` (30), hacia adelante desde hoy |
| **Umbrales** | Por inquilino en `settings.capacity_thresholds`: `over > red_over` (10) → rojo; `over > yellow_over` (0) → amarillo |
| **Nulos** | Igual que arriba: no suman, se reportan |
| **Firma** | owner · 2026-08-06, sin cambios |

> **Comparar contra `project_capacity_pct` y no contra 100 es la decisión más
> importante de esta familia.** Un recurso que dedica el 60 % a proyectos y el
> resto a operación se satura al 60, no al 100.

---

## Familia: presupuesto

### `budget_plan` · `budget_actual` · `burn_index`

| Campo | Valor |
|---|---|
| **Fórmula** | `burn_index = (actual / budget) / (avance / 100)`, es decir consumo relativo sobre avance relativo |
| **Unidad** | **Sin declarar todavía.** La unidad del dinero es la moneda, y hoy solo existe como `tenant.settings.currency` |
| **Nulos** | **Sin presupuesto → «—» [owner 2026-08-06]**, no cero ni infinito. **Ya se cumplía** en `project_health.py`: devuelve `color: None` con «Sin presupuesto configurado». Lo mismo para avance cero: dividir por cero no es rojo, es «todavía no se puede decir» |
| **Firma** | owner · 2026-08-06 |

> **Cambió el código en el tablero, no aquí:** `budget_total` llegaba como `0.0`
> con cero proyectos porque la consulta traía `coalesce(sum(budget), 0)`. El
> `coalesce` convertía el hueco en cero **dentro del SQL**, una capa más abajo
> de donde se suele buscar — y la anotación de Python ya decía `Decimal | None`.
> Ahora llega `null`.

> **La moneda sigue abierta, y es un frente de producto declarado
> [owner 2026-08-06]:** «vamos a dar un diseño de gestión de recursos y
> presupuesto para poder trabajar con esto y registrar budget y monedas».
> Hasta entonces nada impide sumar presupuestos de dos inquilinos con monedas
> distintas. Es lo que mantiene abierto `DAT-01`, y con él el renombrado de
> `DAT-02`.

---

## Familia: salud

### `health_green` · `health_yellow` · `health_red`

| Campo | Valor |
|---|---|
| **Fórmula** | Conteo de proyectos por estado de salud |
| **Origen del valor** | Automático o manual: `health_source` distingue `auto` de intervención humana, y `health_reason` guarda el motivo |
| **Vocabulario** | `green` / `yellow` / `red`. **`amber` está retirado** (D-1, migración 0091, ADR-030) |
| **Nulos** | **No los hay, y se incluyen todos [owner 2026-08-06]**: «los proyectos deberían tener evaluación automática; manual es bajo necesidad, por lo que no debería haber proyectos sin evaluar, y se deben incluir» |
| **Firma** | owner · 2026-08-06 |

**Verificado contra el código, y la decisión ya se cumple.** `health_status` es
`nullable=False` con `default="green"`, así que ningún proyecto queda fuera del
conteo. La evaluación automática corre de verdad —`refresh_health_bulk` en el
tablero y en los snapshots, `apply_auto_health` en el detalle— y `health_source`
respeta la intervención manual sin sobrescribirla.

**El matiz que conviene tener presente:** el color se recalcula **cuando alguien
mira**. Un proyecto que nadie abre conserva el valor por defecto hasta que una
carga de tablero o un snapshot lo toque, y ese valor por defecto es `green` — el
optimista. No es un fallo hoy, porque el refresco masivo del tablero cubre los
proyectos del alcance; sí lo sería si el tablero dejara de recalcular.

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
| **Firma** | owner · 2026-08-06, sin cambios |

> Es la única familia donde `0` es un valor legítimo y no un hueco disfrazado.

---

## Lo que queda abierto

Las fichas están firmadas y `DAT-10` cierra con ellas. Lo de abajo **no las
bloquea**: son frentes propios que las tocarán cuando se resuelvan.

| Qué | Por qué sigue abierto | Bloquea |
|---|---|---|
| **Moneda del dinero** | Frente de producto declarado: diseño de gestión de recursos y presupuesto | `DAT-01`, y con él `DAT-02` |
| **Zona horaria del corte** | Con inquilinos en husos distintos, «vencidas hoy» depende de dónde corra el proceso | Nada hoy; sale a la superficie con el primer inquilino en otro huso |
| **Renombrar `avg_progress` / `progress_avg`** | Cruza API y web: ADR + migración de contrato + ventana | Nada; es deuda de legibilidad |
| **Verificar que el control de cambios registre los cambios de fecha planeada** | Es lo que sostiene la decisión de medir el retraso contra la fecha actual | La auditabilidad del retraso |
| **Línea base (D-6)** | Épica propia, sin abrir | Nada; añadiría una segunda lectura del retraso |

**Lo que cambió de verdad al firmar estas fichas** —y es la parte que no se ve
en el documento— son tres correcciones en el producto: `progress_avg` y
`budget_total` dejan de decir «cero» cuando quieren decir «nada», y el
`coalesce` que lo causaba en SQL desapareció.
