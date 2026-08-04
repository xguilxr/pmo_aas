# Revisión del glosario — hoja de decisiones del owner

| Campo | Valor |
|---|---|
| Estado | Pendiente de decisión. Nada de esto se implementa antes de aprobarse |
| Fecha | 2026-08-04 |
| Sustituye a | Leer `02-GLOSARIO.md` entero término por término |
| Método | Cada término vetado del §6 del glosario, contrastado contra el código de hoy |

---

## Por qué existe esta hoja

`02-GLOSARIO.md` §7 pide «aprobación del owner, término por término». Son 282
líneas y la mayoría **no necesita decisión**: o ya está bien, o el cambio es
mecánico. Lo que sí la necesita son **nueve puntos**, y tres de ellos cuestan
mucho más de lo que el glosario sugiere.

La tabla §6 del glosario contó coincidencias de texto. Al mirar dónde caen esas
coincidencias, cambia el cuadro: **una parte son falsos positivos** —etiquetas de
presentación en español, que el propio glosario permite— y **el más barato de la
lista resulta ser el más caro**.

---

## Bloque 1 — decisiones que cuestan un contrato, no un renombrado

### D-1. `yellow` vs `amber` — el glosario tiene esto al revés

**Qué dice el glosario:** «`amber` es el valor correcto; `yellow` es informal y
hoy convive con él» (§2.4), 33 ocurrencias.

**Qué dice el código:** `yellow` no es informal. Es **el valor canónico del
contrato**, y se eligió a propósito:

| Evidencia | Qué demuestra |
|---|---|
| `apps/api/app/schemas/project.py:47,111,116` | `Literal["green","yellow","red"]` y el alias `RagColor`. Es el contrato público de la API |
| `apps/api/alembic/versions/20260708_0091_health_unified.py:37` | La migración **convierte `amber` → `yellow`** al unificar `status_rag` en `health_status`. El `downgrade` (:58) lo revierte |
| `apps/api/app/services/analytics/snapshots.py:120` | Escribe la clave `health_yellow` en los snapshots de métricas. Los históricos ya guardados llevan ese nombre |
| `apps/web/lib/api/projects.ts:5`, `analytics.ts:65,68`, `capacity.ts:5` | Los tipos del frontend replican `"green" \| "yellow" \| "red"` |

Adoptar `amber` no es renombrar 33 líneas: es **cambiar el contrato de la API,
migrar los datos revirtiendo la 0091, migrar las claves de los snapshots
históricos y tocar los tipos del frontend**. Adoptar `yellow` es corregir el
glosario y limpiar tres restos de `amber`
(`charter_generator.py:52-53` mapea los dos; `templates/pdf/sections/s-03.html:9`
usa `'amber'` por defecto; el `CHECK` de la migración 0065 es histórico).

**Recomendación:** adoptar **`yellow`** como valor canónico y registrar en el
glosario que se aparta a conciencia del vocabulario RAG de P3O/PRINCE2, con el
motivo. La UI ya dice «Amarillo», que es lo que ve el cliente. Merece un ADR:
es exactamente el tipo de decisión que dentro de un año nadie recordará por qué
se tomó.

- [ ] Adoptar `yellow` (recomendado) — [ ] Adoptar `amber` (asumiendo el costo)

### D-2. `support` como fase

**En el código hay una sola ocurrencia**, y no es el enum del proyecto:
`apps/api/app/services/analytics/snapshots.py:28` →
`ACTIVE_PHASES = ["planning","execution","support"]`.

El campo real es `apps/api/app/models/project.py:43` — `String(32)`, sin enum de
base de datos, por defecto `planning`. Eso abarata mucho el cambio: **no hay tipo
enum que migrar**, solo filas existentes y las opciones que ofrezca la UI.

El glosario propone cinco fases (`initiation`, `planning`, `execution`,
`closing`, `cancelled`). La decisión de fondo: **¿qué pasa con los proyectos que
hoy están en `support`?** Son operación, no proyecto.

- [ ] Adoptar las cinco fases y migrar `support` → ___________
- [ ] Dejarlo como está por ahora

### D-3. `tasks.wbs` → `wbs_code`

`apps/api/app/models/task.py:29` — `wbs: Mapped[str | None]`. El propio código ya
sabe que el nombre está mal: el comentario de la línea 90 dice «predecessors /
successors como JSON array de **wbs_code**».

Cuesta migración de columna + campo de la API + frontend + el parser de import.
Es correcto, pero es un renombrado que se ve en el contrato.

- [ ] Renombrar — [ ] Aceptar la ambigüedad y documentarla

---

## Bloque 2 — decisiones de negocio, no de estándar

Estas tres no las resuelve ningún marco: dependen de cómo querés que el producto
mida.

### D-4. Umbral del semáforo (§2.4)

Sin fórmula, el estado de salud es «una opinión con color». El glosario propone
verde / ámbar / rojo por desviación y riesgos. Falta **el número**: ¿qué es
«desviación material»? ¿5 % del cronograma? ¿10 días?

- [ ] Umbral propuesto: ______________________

### D-5. Método de avance (§2.3)

Hoy `progress: int` sin método declarado. Los cuatro métodos dan números
distintos y el cliente los va a comparar.

- [ ] Tarea declarado + proyecto ponderado por duración (propuesta del glosario)
- [ ] Otro: ______________________

### D-6. Línea base (§2.1)

No existe en el modelo. Es la brecha B-1 y bloquea «desviación», «retraso» y
«sobrecosto»: sin línea base, esas tres palabras no tienen referente. También
bloquea el DCMA 14-point del diagnóstico.

- [ ] Entra al roadmap — [ ] Se difiere, y se retiran esos términos de los informes

---

## Bloque 3 — mecánico, sin decisión de fondo

Confirmá que estás de acuerdo y se ejecutan sin más discusión.

| # | Qué | Dónde | Costo |
|---|---|---|---|
| D-7 | Unificar las dos paletas de salud en una | `apps/api/app/services/reports/scoped_status.py:30,33` — `_HEALTH_DONUT_COLOR` verde `#1F8A5B` vs `_HEALTH_HEX` verde `#16a34a` | Bajo |
| D-8 | `portfolio_function` no es portafolio | `apps/api/app/models/area.py:233`, `endpoints/areas.py:675-689`, `L1-PORTAFOLIO` en `report_builder_template.py:11` | Medio — el parámetro es público |
| D-9 | Validar `is_milestone ⟹ duration_days = 0` | Regla del §1.2, hoy sin validar | Bajo |

---

## Lo que el glosario marcó y **no** hay que tocar

Contarlos como deuda infla la lista y hace que la revisión pese más de lo que es.

- **`Verde` / `Amarillo` / `Rojo`** en `scoped_status.py:340-341`,
  `pmo/page.tsx:116`, `programs/[id]/page.tsx:82`,
  `health-evaluation-modal.tsx:93` son **etiquetas de presentación**, y el
  glosario §1.1 permite explícitamente español en la capa de presentación. No son
  valores.
- **`"Inicio"` / `"Ejecución"` / `"Cierre"`**: de las ocurrencias en `apps/api`,
  `lessons_export.py:40,42` es un mapa de traducción, `charter_generator.py:247`
  es la etiqueta de una fila de tabla y `xlsx_task_parser.py:6` son alias de
  encabezado para leer archivos del usuario — los tres son legítimos. **El único
  que amerita mirar es `plan_regenerator.py:37`**, donde «Inicio» parece un
  nombre de fase generado.

---

## Cómo se sigue

1. Marcás las casillas de D-1 a D-9 (o las anotás al margen).
2. Con eso se cierra `02-GLOSARIO.md` §7 puntos 1-3 y deja de estar en borrador.
3. Recién entonces se escribe el plan de remediación, que el glosario condiciona
   a su propia aprobación.

D-1, D-2 y D-3 tocan contrato: si alguna se aprueba, va con ADR y por su propia
US, no dentro de otro batch.
