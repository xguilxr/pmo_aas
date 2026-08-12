---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# Revisión del glosario — decisiones del owner

| Campo | Valor |
|---|---|
| Estado | **Cerrado.** Las nueve decididas y ejecutadas; D-4 calibrada el 2026-08-05 |
| Método | Cada término vetado del §6 del glosario, contrastado contra el código de hoy |
| Efecto | `02-GLOSARIO.md` deja de ser borrador |

---

## Por qué existe esta hoja

`02-GLOSARIO.md` §7 pedía «aprobación del owner, término por término». Son 282
líneas y la mayoría **no necesitaba decisión**: o ya estaba bien, o el cambio era
mecánico. Quedaron nueve puntos.

La tabla §6 del glosario había contado coincidencias de texto. Al mirar **dónde
caen** esas coincidencias cambió el cuadro. Una parte eran falsos positivos
—etiquetas de presentación en español, que el propio glosario permite—. El ítem
descrito como más barato resultó ser el más caro.

## Las decisiones

| # | Qué | Decisión | Cuesta |
|---|---|---|---|
| D-1 | `yellow` vs `amber` | **`yellow`** | Corregir el glosario + 3 restos |
| D-2 | `support` como fase | **Renombrar a `hypercare`** (2026-08-05) — ADR-019 | Migración + contrato + UI |
| D-3 | `tasks.wbs` | **Renombrar a `wbs_code`** — ADR-020, ronda propia | ✅ **hecha** 2026-08-05 — US-194, mig 0100 |
| D-4 | Umbral del semáforo | **Uno por dimensión** + calibrado — ✅ hecho 2026-08-05 (US-196) | Medio — el presupuesto cambió de fórmula |
| D-5 | Método de avance | **La propuesta del glosario** | Declararlo en la UI |
| D-6 | Línea base | **Al roadmap** | Épica propia |
| D-7 | Dos paletas de salud | **Unificar** — ✅ hecho 2026-08-05 | Bajo |
| D-8 | `portfolio_function` | **Renombrar a `discipline`** — ✅ hecho 2026-08-05 (ADR-021) | Medio — el parámetro es público |
| D-9 | `is_milestone ⟹ duración 0` | **Validar** — ✅ hecho 2026-08-05 | Bajo |

---

## D-1. `yellow` — el glosario lo tenía al revés

**Decisión: `yellow` es el valor canónico.**

El glosario decía «`amber` es el valor correcto; `yellow` es informal» (§2.4).
No lo es. `yellow` es **el contrato**, y se eligió a propósito:

| Evidencia | Qué demuestra |
|---|---|
| `apps/api/app/schemas/project.py:47,111,116` | `Literal["green","yellow","red"]` y el alias `RagColor` |
| `alembic/versions/20260708_0091_health_unified.py:37` | La migración **convierte `amber` → `yellow`** al unificar `status_rag` en `health_status` |
| `apps/api/app/services/analytics/snapshots.py:120` | Escribe la clave `health_yellow`. Los snapshots históricos ya la llevan |
| `apps/web/lib/api/projects.ts:5`, `analytics.ts:65,68`, `capacity.ts:5` | Los tipos del frontend replican los tres valores |

Adoptar `amber` habría sido cambiar el contrato público, revertir la 0091 sobre
datos productivos, migrar las claves de los snapshots y tocar el frontend. Se
queda `yellow`, y el glosario registra que **se aparta a conciencia del
vocabulario RAG de P3O/PRINCE2**. La UI ya dice «Amarillo», que es lo que ve el
cliente.

**Pendiente mecánico:** limpiar los tres restos de `amber` —
`charter_generator.py:52-53` mapea los dos, y `templates/pdf/sections/s-03.html:9`
usa `'amber'` por defecto. El `CHECK` de la migración 0065 es histórico.

**Merece ADR:** es el tipo de decisión que dentro de un año nadie recuerda por
qué se tomó.

## D-2. `support` es hypercare, y `closed` ya existe

**Decisión del owner:** *«`support` es un estado de hypercare antes del cierre
formal del proyecto. Pero es una forma de closing.»* Y la pregunta que vino con
ella —¿hay un `closed` para que se archiven?— tiene respuesta: **sí, ya existe.**

El vocabulario real de hoy son **cuatro fases**, no las tres que sugería el
glosario:

| Evidencia | Qué demuestra |
|---|---|
| `apps/web/lib/api/projects.ts:3` | `ProjectPhase = "planning" \| "execution" \| "support" \| "closed"` |
| `apps/web/app/(app)/pmo/projects/page.tsx:38,581` | La UI ofrece las cuatro como filtro |
| `apps/api/app/services/analytics/snapshots.py:28` | `ACTIVE_PHASES = ["planning","execution","support"]` — «activo» ya significa «no cerrado» |
| `apps/api/app/models/project.py:43` | `phase: String(32)`, sin enum de base de datos. Cambiar el vocabulario no exige migrar un tipo |
| `apps/api/app/services/lessons_export.py:38-42` | Las lecciones usan el mismo vocabulario de cuatro |

Así que el veto del glosario a `support` era **erróneo en el fondo**. El
concepto es legítimo —la transición a operaciones existe en los estándares—, pero lo
discutible es el nombre. `support` se lee como «mesa de ayuda»; `hypercare` es
lo que el owner describe.

**Renombrada a `hypercare` el 2026-08-05** (ADR-019, migración 0098). Va con
ventana de compatibilidad —el API sigue aceptando `support` a la entrada y
devuelve siempre el canónico—. Es la misma forma que se usó para `amber` → `yellow`
en la 0091.

De los dos huecos que la decisión no cubría, el owner resolvió el 2026-08-05:

- **`cancelled`: sí.** Hoy un proyecto cortado a mitad queda `closed`,
  indistinguible de uno que cumplió — ensucia cualquier métrica de éxito y las
  lecciones aprendidas. **Hecha el 2026-08-05** (ADR-022, US-195). Salió **sin
  migración**: `phase` es `String(32)` sin `CHECK`, así que añadir un valor no
  toca el esquema. De paso, `ACTIVE_PHASES` pasó a **derivarse** del vocabulario
  en vez de repetirlo. Era el sitio que en D-2 se quedó con el nombre viejo sin
  fallar.
- **`initiation`: no.** El proyecto nace en `planning` aunque el acta sea previa,
  y eso no ha causado ningún problema reportado.

**No verificado:** si un proyecto en `closed` queda de solo lectura. Lo único
comprobado es que sale de `ACTIVE_PHASES` y por tanto de los snapshots.

## D-3. `tasks.wbs` → `wbs_code`

**Decisión: renombrar.** El nombre correcto es `wbs_code`, porque el campo guarda
el *código* (`1.2.3`), no la estructura — esa vive en `parent_id` y
`outline_level`. El propio código ya lo sabe. `apps/api/app/models/task.py:90`
documenta «predecessors / successors como JSON array de **wbs_code**» mientras la
columna de la línea 29 se llama `wbs`.

Cuesta migración de columna + campo de la API + frontend + el parser de import.
Va con ADR y US propia.

**Hecha el 2026-08-05** — US-194, ADR-020, migración 0100. Lo que la ejecución
enseñó y la medición no anticipaba: la parte cara no fueron las 259 ocurrencias.
Un `sed` sobre el identificador resuelve casi todas. Fueron los **siete sitios
donde `wbs` no era nuestro campo**: la cabecera del Excel del usuario, los alias
del importador, los cinco códigos `WBS_*` de diagnóstico, el elemento `<WBS>` de
MS Project, la clave del JSON de MPXJ, la ruta `renumber-wbs` y la clave
`plan-wbs-level:<id>` de `localStorage`. Esta última era la única capaz de
romperse **en silencio**. Habría reseteado el nivel de agrupación guardado de
todos los usuarios sin producir un solo error.

## D-4. Umbral del semáforo — forma y valores

**La duda original del owner era si había uno o varios.** Resuelta el
2026-08-05: **uno por dimensión**.

Encaja con lo que el producto ya hace. US-191 evalúa la salud en **cinco
dimensiones** —cronograma, presupuesto, riesgos, decisiones, recursos— más la
global, y `project_health_evaluations` ya las guarda por separado. Un umbral
único tendría que promediarlas para volver a partirlas después; uno por
dimensión se apoya en la estructura que existe.

Y responde a la intuición que dio origen a la duda: **no es lo mismo el umbral
de cronograma que el de costo**. Un 10 % de desviación en presupuesto y un 10 %
en fechas no significan lo mismo para nadie.

**Calibrada el 2026-08-05** (US-196). Al ir a poner los valores aparecieron dos
cosas que ningún número arreglaba:

1. **El presupuesto no miraba el tiempo.** Comparaba `gastado / presupuesto` sin
   avance ni fecha. Un proyecto con el **85 % del presupuesto gastado y
   el 10 % de avance salía verde**. Ahora usa un **índice de consumo**
   —`(gastado/presupuesto) ÷ (avance/100)`, el inverso del CPI—, que en ese caso
   da 8,5. Sin avance la dimensión queda sin color, no en rojo.
2. **Casi todos los amarillos disparaban con el primer caso.** Cuatro de las
   cinco dimensiones tenían el piso en 0 o 1 —un riesgo severo, una decisión
   estancada, cualquier sobreasignación—. En cartera real, eso es amarillo
   permanente. Un semáforo siempre amarillo dejó de informar.

Más una de estructura: recursos se configuraba en `capacity_thresholds`, otra
llave, con dos reglas escritas a fuego. Las cinco dimensiones se ajustan ahora
desde `health_thresholds`.

**Los valores son razonados, no medidos** — no había cartera real contra la cual
contrastarlos. Por eso lo que importa es que sean settings por inquilino:
calibrar de verdad no necesita tocar código.

Mientras tanto, `health_source = 'manual'` con `health_reason` obligatoria sigue
siendo la salida honesta: el semáforo es un juicio declarado, no un cálculo.

**Lo que falta para cerrarla del todo:** un proyecto con historia suficiente, y
entonces cinco números. No antes.

## D-5. Método de avance

**Decisión: la propuesta del glosario.** Avance de tarea **declarado**; avance de
proyecto **ponderado por duración** de sus tareas hoja. Se declara en la UI junto
al número, y debe ser reproducible desde las tareas: si no cuadra, es defecto.

## D-6. Línea base — al roadmap

Es la brecha B-1 y bloquea «desviación», «retraso» y «sobrecosto»: sin línea
base esas tres palabras no tienen referente. También bloquea el DCMA 14-point del
diagnóstico. Entra como épica propia.

## D-7, D-8, D-9 — aprobadas, mecánicas

| # | Qué | Dónde |
|---|---|---|
| D-7 | Unificar las dos paletas de salud | ✅ **Hecha el 2026-08-05.** Ver abajo |
| D-8 | `portfolio_function` no es portafolio | ✅ **Hecha el 2026-08-05** (ADR-021, migración 0099). `discipline` porque «función» y «rol» ya significan otras cosas aquí. Ventana en dos puertas —cuerpo y parámetro de consulta— porque el nombre era público; `by_function` pasó a `by_discipline` para no reabrir el mismo desajuste |
| D-9 | Validar `is_milestone ⟹ duration_days = 0` | ✅ **Hecha el 2026-08-05.** Normalización en el modelo (vale para los seis caminos de escritura) + rechazo del rango de varios días al crear. Resultó menos mecánica de lo previsto: la duración es un valor **derivado** —el endpoint ignora el que manda el cliente— así que un 422 sobre ella habría dejado al usuario sin forma de arreglarlo |

### D-7, cerrada — y no eran dos paletas, eran cuatro

La decisión nombraba dos, ambas en `scoped_status.py`: `_HEALTH_DONUT_COLOR`
con los colores de marca y `_HEALTH_HEX` con los de Tailwind. Al ir a
unificarlas aparecieron **otras dos** en las plantillas PDF —`base.html` y
`reports/scope_status.html`—, cada una con su mezcla de las anteriores. El mismo
proyecto en rojo salía `#C0392B` en el donut y `#dc2626` en el mapa de árbol de
la página siguiente.

Hoy hay una sola, `HEALTH_COLOR` en `scoped_status.py`:

| Estado | Color | Token de `globals.css` |
|---|---|---|
| `green` | `#007A4C` | `--color-success-fg` |
| `yellow` | `#9F5900` | `--color-warning-fg` |
| `red` | `#BD3528` | `--color-danger-fg` |

**Los valores no son los que la decisión suponía**. Ahí está lo que hizo que
esto no fuera mecánico: el verde de marca `#1F8A5B` no alcanzaba WCAG 2.2 AA
(MCS DIS-02). Unificar sin mirar el contraste habría consolidado el que no pasa,
que era justo el del semáforo. Las dos decisiones se resolvieron juntas y el
mismo día.

De regalo cerró un defecto que nadie había reportado: el mapa de árbol del PDF
pintaba texto blanco sobre `#eab308`, alrededor de 1.9:1 — ilegible.

`tests/test_d7_paleta_de_salud.py` lee el hex de `globals.css` y lo compara con
el del backend. Así, la próxima vez que un token se retoque por contraste, el
semáforo no se queda atrás en silencio.

**Lo que queda fuera, dicho a propósito:** la paleta de *gráficos* —líneas de
tendencia, barras del Gantt, `actual_color` de la curva-S—. Arrastra los mismos
colores de Tailwind, y también convendría unificarla. No se tocó porque decidir si
la línea de «avance promedio» lleva el verde del semáforo es una decisión de
diseño. No es la que D-7 tomó. Está nombrada en el propio test para que sea trabajo
y no descuido.

---

## Lo que el glosario marcó y **no** hay que tocar

Contarlos como deuda infla la lista y hace que la revisión pese más de lo que es.

- **`Verde` / `Amarillo` / `Rojo`** en `scoped_status.py:340-341`,
  `pmo/page.tsx:116`, `programs/[id]/page.tsx:82`,
  `health-evaluation-modal.tsx:93` son **etiquetas de presentación**, y el
  glosario §1.1 permite explícitamente español en esa capa. No son valores.
- **`"Inicio"` / `"Ejecución"` / `"Cierre"`**: de las ocurrencias en `apps/api`,
  `lessons_export.py:38-42` es un mapa de traducción. `charter_generator.py:247`
  es la etiqueta de una fila de tabla. `xlsx_task_parser.py:6` son alias de
  encabezado para leer archivos del usuario. Los tres son legítimos. **El único
  que amerita mirar es `plan_regenerator.py:37`**, donde «Inicio» parece un
  nombre de fase generado.

---

## Qué sigue

El plan de remediación ya se puede escribir: el glosario estaba condicionado a
esta aprobación. Orden sugerido, de menor a mayor riesgo:

1. **Gratis y hoy** — corregir `02-GLOSARIO.md` (D-1, D-2, D-5) y limpiar los
   tres restos de `amber`.
2. **Mecánico** — D-7 y D-9.
3. **Con ADR y US propia, una por una** — D-3 (`wbs_code`), D-8
   (`portfolio_function`), y el nombre de `support` si se decide renombrar.
   Las tres tocan contrato.
4. **Épica** — D-6, línea base.

D-4 se retoma cuando haya un proyecto real con desviación medible contra el que
calibrar. Antes de eso, cualquier umbral sería inventado.
