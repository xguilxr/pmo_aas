# Revisión del glosario — decisiones del owner

| Campo | Valor |
|---|---|
| Estado | **Resuelto el 2026-08-04.** Ocho decisiones tomadas, una abierta (D-4) |
| Método | Cada término vetado del §6 del glosario, contrastado contra el código de hoy |
| Efecto | `02-GLOSARIO.md` deja de ser borrador salvo en el umbral del semáforo |

---

## Por qué existe esta hoja

`02-GLOSARIO.md` §7 pedía «aprobación del owner, término por término». Son 282
líneas y la mayoría **no necesitaba decisión**: o ya estaba bien, o el cambio era
mecánico. Quedaron nueve puntos.

La tabla §6 del glosario había contado coincidencias de texto. Al mirar **dónde
caen** esas coincidencias cambió el cuadro: una parte eran falsos positivos
—etiquetas de presentación en español, que el propio glosario permite— y el ítem
descrito como más barato resultó ser el más caro.

## Las decisiones

| # | Qué | Decisión | Cuesta |
|---|---|---|---|
| D-1 | `yellow` vs `amber` | **`yellow`** | Corregir el glosario + 3 restos |
| D-2 | `support` como fase | **Es hypercare, y es cierre**. Queda | Documentar + nombre a decidir |
| D-3 | `tasks.wbs` | **Renombrar a `wbs_code`** | Migración + contrato + frontend |
| D-4 | Umbral del semáforo | **Abierta** — ni siquiera está claro si es uno o varios | — |
| D-5 | Método de avance | **La propuesta del glosario** | Declararlo en la UI |
| D-6 | Línea base | **Al roadmap** | Épica propia |
| D-7 | Dos paletas de salud | **Unificar** | Bajo |
| D-8 | `portfolio_function` | **Renombrar** | Medio — el parámetro es público |
| D-9 | `is_milestone ⟹ duración 0` | **Validar** | Bajo |

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
vocabulario RAG de P3O/PRINCE2**: la UI ya dice «Amarillo», que es lo que ve el
cliente.

**Pendiente mecánico:** limpiar los tres restos de `amber` —
`charter_generator.py:52-53` mapea los dos, `templates/pdf/sections/s-03.html:9`
usa `'amber'` por defecto, y el `CHECK` de la migración 0065 es histórico.

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

Así que el veto del glosario a `support` era **erróneo en el fondo**: el
concepto es legítimo —la transición a operaciones existe en los estándares—, lo
discutible es el nombre. `support` se lee como «mesa de ayuda»; `hypercare` es
lo que el owner describe.

**Lo que falta decidir es solo el nombre**, y dos huecos:

- [ ] Renombrar `support` → `hypercare` (claro, cuesta migración de datos + tipos + UI)
      · o dejar `support` y documentarlo como hypercare (gratis)
- [ ] ¿Hace falta `initiation`? Hoy un proyecto nace en `planning`, aunque el acta
      de constitución sea previa
- [ ] ¿Hace falta `cancelled`? Un proyecto terminado anticipadamente hoy solo puede
      quedar `closed`, indistinguible de uno que cumplió

**No verificado:** si un proyecto en `closed` queda de solo lectura. Lo único
comprobado es que sale de `ACTIVE_PHASES` y por tanto de los snapshots.

## D-3. `tasks.wbs` → `wbs_code`

**Decisión: renombrar.** El nombre correcto es `wbs_code`, porque el campo guarda
el *código* (`1.2.3`), no la estructura — esa vive en `parent_id` y
`outline_level`. El propio código ya lo sabe: `apps/api/app/models/task.py:90`
documenta «predecessors / successors como JSON array de **wbs_code**» mientras la
columna de la línea 29 se llama `wbs`.

Cuesta migración de columna + campo de la API + frontend + el parser de import.
Va con ADR y US propia.

## D-4. Umbral del semáforo — abierta

**Decisión del owner:** no se define hoy, y con razón: *«no sé si hay un solo
umbral o deben haber más»*. Casi seguro son varios —no es lo mismo el umbral de
un proyecto de tres meses que el de uno de dos años, ni el de cronograma que el
de costo.

Es el único punto que deja `02-GLOSARIO.md` en borrador, y el único que ningún
estándar resuelve. Mientras tanto, `health_source = 'manual'` con
`health_reason` obligatoria es la salida honesta: el semáforo es un juicio
declarado, no un cálculo.

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
| D-7 | Unificar las dos paletas de salud | `apps/api/app/services/reports/scoped_status.py:30,33` — `_HEALTH_DONUT_COLOR` verde `#1F8A5B` vs `_HEALTH_HEX` verde `#16a34a` |
| D-8 | `portfolio_function` no es portafolio | `apps/api/app/models/area.py:233`, `endpoints/areas.py:675-689`, `L1-PORTAFOLIO` en `report_builder_template.py:11` |
| D-9 | Validar `is_milestone ⟹ duration_days = 0` | Regla del §1.2, hoy sin validar |

---

## Lo que el glosario marcó y **no** hay que tocar

Contarlos como deuda infla la lista y hace que la revisión pese más de lo que es.

- **`Verde` / `Amarillo` / `Rojo`** en `scoped_status.py:340-341`,
  `pmo/page.tsx:116`, `programs/[id]/page.tsx:82`,
  `health-evaluation-modal.tsx:93` son **etiquetas de presentación**, y el
  glosario §1.1 permite explícitamente español en esa capa. No son valores.
- **`"Inicio"` / `"Ejecución"` / `"Cierre"`**: de las ocurrencias en `apps/api`,
  `lessons_export.py:38-42` es un mapa de traducción, `charter_generator.py:247`
  es la etiqueta de una fila de tabla y `xlsx_task_parser.py:6` son alias de
  encabezado para leer archivos del usuario — los tres son legítimos. **El único
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
