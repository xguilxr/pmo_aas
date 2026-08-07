---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 90d
---

# Glosario canónico del dominio PMO

| Campo | Valor |
|---|---|
| Estado | **Aprobado y completo.** Las nueve decisiones ejecutadas; el umbral del §2.4 quedó calibrado el 2026-08-05 (US-196). Evidencia en [`03-REVISION-GLOSARIO.md`](03-REVISION-GLOSARIO.md) |
| Fecha | 2026-08-03 · revisado 2026-08-04 |
| Alcance | El núcleo homogeneizable de `00-RUNDOWN-estandares.md` §3 |
| Árbitro propuesto | ISO 21506 (vocabulario), sin adoptar la familia |

---

## Cómo se lee

| Columna | Significado |
|---|---|
| **Término preferente** | El que se usa en código, UI, docs y ante el cliente |
| **Vetado** | Aparece hoy en el repositorio y **deja de usarse**. No es sinónimo: es error |
| **Definición** | Qué es, y qué lo distingue del término con el que se confunde |
| **Regla** | Cómo se calcula o valida. Sin regla, el término no está cerrado |

Un término sin regla es una etiqueta. La regla es lo que hace que dos personas obtengan el
mismo número.

---

## 1. Ciclo de vida

### 1.1 Fase

**Preferente:** `fase` · **En código:** `phase`

Etapa del ciclo de vida del proyecto, delimitada por una decisión de continuidad.

**Vocabulario vigente** — cuatro fases, en inglés en el código y español en la UI
(`apps/web/lib/api/projects.ts:3`):

| Código | UI | Qué la cierra |
|---|---|---|
| `planning` | Planeación | Línea base aprobada |
| `execution` | Ejecución | Entregables aceptados |
| `hypercare` | Hypercare | Fin del hypercare y aceptación formal |
| `closed` | Cierre | Cierre formal y lecciones registradas |

**`hypercare` es la fase, no una mesa de ayuda** (D-2). Es el período de garantía
posterior a la entrega y previo al cierre formal: **una forma de cierre**, no una fase de
operación. Se llamaba `support`, que se leía como servicio permanente — justo lo que la
fase no es.

**Renombrada el 2026-08-05** (ADR-019, migración 0098). El API **sigue aceptando
`support` a la entrada** durante una ventana de compatibilidad —un cliente que no se haya
actualizado no se rompe— pero devuelve siempre el nombre canónico, y en base ya no queda
ninguno.

**Decidido el 2026-08-05:** se añadirá **`cancelled`** —hoy una terminación anticipada es
indistinguible de un cierre cumplido.

**Vetado:** literales en español como *valor* dentro del código. Las etiquetas en español
de la capa de presentación son correctas y no cuentan como deuda. El único caso por
revisar es `plan_regenerator.py:37`.

### 1.2 Hito

**Preferente:** `hito` · **En código:** `milestone` · **Vetado:** `entregable` como sinónimo

Punto de control de **duración cero** que marca un evento significativo. No consume
recursos. Un entregable es un *producto*; un hito es una *fecha*. Un entregable puede tener
un hito asociado, pero no son lo mismo.

**Regla:** `is_milestone = true` ⟹ `duration_days = 0`. **Validada desde el 2026-08-05** (decisión D-9), en dos mitades: la duración la normaliza el modelo (`normalizar_hito` en `app/models/task.py`, evento de guardado, así que vale para el alta manual, los tres importadores, el regenerador de plan y la semilla); y marcar un hito con un rango de varios días se rechaza al crearlo. El caso que la incumplía no era raro: la duración se cuenta en días inclusivos, así que un hito con la misma fecha de inicio y fin daba 1.

---

## 2. Medición

### 2.1 Línea base

**Preferente:** `línea base` · **En código:** `baseline` · **Vetado:** `plan original`,
`fechas planeadas` usados sueltos

Versión **aprobada y congelada** del alcance, cronograma o costo, contra la que se mide la
desviación. Solo cambia por control de cambios aprobado.

**Regla:** toda línea base guarda quién la aprobó, cuándo, y la solicitud de cambio que la
modificó. Una línea base que se puede editar sin rastro no es una línea base.

> **Brecha B-1.** No existe en el modelo. Es el término que más falta: sin él, «desviación»,
> «retraso» y «sobrecosto» no tienen referente.

### 2.2 Desviación de cronograma

**Preferente:** `desviación de cronograma` · **Vetado:** `retraso` como término técnico

`fecha_actual − fecha_línea_base`, en días. Positivo es tarde.

*Retraso* sirve para hablar con un cliente; en el modelo y en los informes, el término es
desviación, porque puede ser negativa.

### 2.3 Avance

**Preferente:** `avance` · **En código:** `progress` · **Vetado:** `% completado` sin
calificar

Porcentaje de trabajo completado. **Carece de significado sin declarar el método**, porque
los cuatro métodos dan números distintos:

| Método | Cómo |
|---|---|
| Por duración | Tiempo transcurrido sobre duración total |
| Por esfuerzo | Horas consumidas sobre horas estimadas |
| Por entregables | Entregables aceptados sobre total |
| Declarado | Lo que dice el responsable |

**Regla adoptada** (D-5, 2026-08-04): avance de tarea **declarado**; avance de proyecto
**ponderado por duración** de sus tareas hoja. Debe declararse en la UI, junto al número.

**Regla de reconciliación:** el avance del proyecto debe ser reproducible a partir de sus
tareas. Si no cuadra, es defecto.

> **Brecha B-5.** Hoy `progress: int` en tarea y proyecto, sin método declarado.

### 2.4 Estado de salud (RAG)

**Preferente:** `estado de salud` · **En código:** `health_status`
**Valores:** `red` · `yellow` · `green`
**Vetado:** `amber` como valor — **0 restos desde el 2026-08-06** (DAT-06, ADR-030); `status_rag` (absorbido en la migración 0091)

RAG —*Red, Amber, Green*— es el término de P3O y PRINCE2, y este producto **se aparta de él
a conciencia** (D-1, 2026-08-04). `yellow` es el contrato de la API
(`schemas/project.py:116`), la migración 0091 convirtió `amber` → `yellow` a propósito, y
los snapshots históricos ya guardan la clave `health_yellow`. La UI dice «Amarillo», que es
lo que ve el cliente. Volver a `amber` costaría contrato, datos e históricos; no lo vale.

> **Cerrado el 2026-08-05 (DAT-06).** Los restos eran cuatro, no tres, y ninguno estaba
> donde se busca. `reports/engine.py` **traducía `yellow` → `amber`** para hablarle a la
> plantilla: mientras esa tabla existiera, retirar el término del dominio no lo retiraba
> del producto, solo lo movía al borde. Y el PDF que se le manda al cliente decía
> **«Ámbar»** en la etiqueta visible. Los otros dos —una clase CSS y una clave alias en
> el generador DOCX— eran alias que nadie usaba, que es justo por donde el término vuelve
> cuando alguien copia el diccionario. Trinquete: `tests/test_dat06_vocabulario.py`, que
> mira el árbol y no una lista de sitios conocidos.
>
> **El quinto cerró el 2026-08-06** (ADR-030). `task_load_thresholds.amber_max` era una
> llave guardada en `tenant.settings` de inquilinos reales, así que fue con el molde de
> `wbs` → `wbs_code`: migración 0101 sobre los datos existentes y ventana de
> compatibilidad a la entrada **y a la lectura**. La etiqueta del formulario de ajustes
> también decía «Ámbar»; el sinónimo no estaba solo en una variable.

**Regla — la pieza que falta.** Un semáforo sin fórmula es una opinión con color. Propuesta,
a validar:

| Estado | Criterio |
|---|---|
| `green` | Sin desviación material y sin riesgos altos abiertos |
| `yellow` | Desviación dentro del umbral, o riesgo alto con plan de respuesta |
| `red` | Desviación fuera del umbral, o riesgo alto sin plan, o incidencia crítica abierta |

> **Umbral: uno por dimensión** (D-4, decidido el 2026-08-05). No uno global: el producto
> ya evalúa la salud en cinco dimensiones —cronograma, presupuesto, riesgos, decisiones,
> recursos— y no es lo mismo un 10 % de desviación en costo que en fechas.
>
> **Los valores siguen pendientes, y a propósito.** Se calibran contra un proyecto real con
> desviación medible; antes de eso cualquier número sería inventado. Mientras tanto,
> `health_source = 'manual'` con `health_reason` obligatoria es la salida honesta: el
> semáforo es un juicio declarado, no un cálculo.

`health_source` distingue **derivado** de **anulado manualmente**; si es manual,
`health_reason` es obligatorio. Ese campo ya existe y hoy no se aprovecha.

**Regla de color:** una sola definición de paleta.

> **Brecha B-3.** Hoy hay dos: `HEALTH_DONUT_COLOR` (verde `#1F8A5B`) y `HEALTH_HEX`
> (verde `#16a34a`). Mismo concepto, dos valores.

---

## 3. RAID

El producto ya lo separa bien. Aquí se fija el vocabulario para que siga así.

### 3.1 Riesgo

**Preferente:** `riesgo` · **En código:** `risk`

Evento **futuro e incierto** que, de ocurrir, afecta un objetivo. Tiene probabilidad e
impacto.

**Regla:** un riesgo materializado **deja de ser riesgo y se convierte en incidencia**, con
trazabilidad al riesgo origen. Un riesgo con probabilidad 100 % es una incidencia mal
clasificada.

### 3.2 Incidencia

**Preferente:** `incidencia` · **En código:** `issue` · **Vetado:** `problema`, `bug`

Evento que **ya ocurrió** y afecta un objetivo. No tiene probabilidad: tiene impacto y
responsable.

> `bug` se reserva para defectos de software del propio producto. No es vocabulario de
> dominio del cliente.

### 3.3 Acción

**Preferente:** `acción` · **En código:** `risk_action`

Tarea de respuesta ante un riesgo o incidencia, con responsable y fecha comprometida. No es
una tarea del cronograma: vive en el RAID.

### 3.4 Lección aprendida

**Preferente:** `lección aprendida` · **En código:** `lesson`

Conocimiento registrado para proyectos futuros. **Regla:** se captura durante el proyecto,
no solo al cierre. Una lección registrada únicamente al cierre casi nunca se escribe.

---

## 4. Gobernanza

### 4.1 Acta de constitución

**Preferente:** `acta de constitución` · **En código:** `charter`
**Vetado:** `carta del proyecto` (calco), `project charter` en la UI en español

Documento que **autoriza formalmente** el proyecto y designa al director. Sin autorización
registrada, es un borrador.

### 4.2 Solicitud de cambio

**Preferente:** `solicitud de cambio` · **En código:** `change_request`

Propuesta formal de modificar alcance, cronograma, costo o línea base.

**Regla:** todo cambio de línea base exige una solicitud aprobada. Es lo que hace que la
línea base signifique algo.

### 4.3 Interesado

**Preferente:** `interesado` · **En código:** `stakeholder`
**Vetado:** `involucrado`, `parte interesada` mezclado con los anteriores

Persona u organización que afecta, se ve afectada, o se percibe afectada por el proyecto.
Las tres condiciones cuentan: la percepción basta.

### 4.4 Patrocinador

**Preferente:** `patrocinador` · **En código:** `sponsor`

Interesado que provee recursos y respaldo, y **rinde cuentas** por los beneficios. Es un rol
único: si hay dos patrocinadores, no hay ninguno.

---

## 5. Estructura

### 5.1 EDT / WBS

**Preferente:** `EDT` en español, `WBS` en código
**Vetado:** usar «WBS» para referirse al *código* de la tarea

Descomposición jerárquica del alcance total en paquetes de trabajo.

**Regla del 100 %** (ISO 21511 / PMI): la suma de los hijos es exactamente el alcance del
padre. Ni más, ni menos.

> **Ambigüedad actual.** `tasks.wbs` guarda el *código* (`1.2.3`), no la estructura. La
> estructura vive en `parent_id` y `outline_level`. Conviene renombrar el campo a
> `wbs_code`, que es lo que es.

### 5.2 Programa

**Preferente:** `programa` · **En código:** `program`

Conjunto de proyectos gestionados de forma coordinada para obtener beneficios que **no se
obtendrían gestionándolos por separado**. Esa última cláusula es la que lo distingue de una
simple carpeta.

### 5.3 Portafolio

**Preferente:** `portafolio` · **En código:** `portfolio`
**Vetado:** usar «portafolio» para un área organizativa

Conjunto de proyectos, programas y operaciones agrupados **para facilitar la gestión
estratégica**. No coincide con la estructura organizativa.

> **Brecha B-6.** Hoy `PORTAFOLIO` y `portfolio_function` son etiquetas de función de área.
> Mientras no exista la entidad, conviene no usar la palabra.

---

## 6. Términos vetados — resumen accionable

> Revisado el 2026-08-04 contra el código. Dos filas se cayeron por falsas y una cambió de
> dirección; la evidencia por línea está en `03-REVISION-GLOSARIO.md`.

| Vetado | Preferente | Ocurrencias hoy | Dónde |
|---|---|---|---|
| `amber` como valor | `yellow` | **0** (2026-08-06) | cerrado entero: código, datos (migración 0101) e interfaz. Ventana abierta en `compatibilidad.py` |
| Dos paletas de salud | una definición única | 2 mapas | `scoped_status.py:30,33` |
| `wbs` para el código de tarea | `wbs_code` | 1 campo | `tasks.wbs` |
| `portafolio` para un área | `discipline` — ✅ hecho 2026-08-05 | 0 | ADR-021, migración 0099 |
| `problema` / `bug` para incidencia de proyecto | `incidencia` | por revisar | — |
| «Inicio» como nombre de fase generado | `planning` | 1 | `plan_regenerator.py:37` |

---

## 7. Magnitudes y unidades canónicas

Cierra **DAT-01** («cada magnitud del dominio DEBE tener una unidad canónica
declarada en el glosario»). Un término del §1 al §6 dice *qué* es una cosa;
esta tabla dice *en qué se mide*, que es la otra mitad de que dos personas
obtengan el mismo número.

**Esta tabla es la declaración normativa.** `apps/api/app/core/magnitudes.py`
la refleja para que el código pueda citarla, y una prueba falla si las dos se
separan: un catálogo que puede desincronizarse de su declaración no es un
catálogo.

| Magnitud | Unidad canónica | Rango | Cómo se reconoce en el código |
|---|---|---|---|
| **Importe** | peso mexicano (MXN) | ≥ 0, dos decimales | `Mapped[Importe]` · `Numeric(14, 2)` |
| **Porcentaje** | por ciento | 0 a 100, hasta dos decimales | sufijo `_pct`, o `Mapped[Porcentaje]` |
| **Fracción** | parte de uno | 0 a 1 | solo variable interna; **nunca** una columna |
| **Días** | día natural | entero; negativo en los desfases | sufijo `_days` |
| **Milisegundos** | milisegundo | entero ≥ 0 | sufijo `_ms` |
| **Bytes** | byte | entero ≥ 0 | sufijo `_bytes` |
| **Conteo** | la cosa contada, y va en el nombre | entero ≥ 0 | `projects_total`, `tokens_in`, `open_risks` |
| **Escala** | punto de escala ordinal | 1 a 5 | `probability`, `impact`, `priority` · `Mapped[Escala]` |
| **Severidad** | punto de severidad (probabilidad por impacto) | 1 a 25 | `severity` · `Mapped[Severidad]` |
| **Ordinal** | posición dentro de un orden | entero; el origen se documenta en cada campo | `position`, `level`, `outline_level`, `version` |
| **Calendario** | coordenada de calendario, en la zona del inquilino | día 0 a 6 · hora 0 a 23 · día del mes 1 a 31 | `day_of_week`, `hour_of_day`, `day_of_month` |

### 7.1 Las tres que más se confunden

**Porcentaje y fracción.** En `project_health.py` conviven un `ratio * 100` que
produce porcentaje y un `progress / 100` que lo consume, a nueve líneas de
distancia. Equivocarse no produce un error: produce un número plausible cien
veces mayor o menor. La conversión tiene nombre (`unidades.fraccion_a_pct`) y
la unidad, ahora, tipo.

**Escala y severidad.** Un 4 de impacto no es el doble de un 2 — son juicios
ordenados, no medidas —, y la severidad es su producto, así que **su rango no
es 1 a 5 sino 1 a 25**. Leerla con la misma vara que sus factores es el error
disponible.

**Ordinal y conteo.** `outline_level` y `open_risks` son los dos enteros y no
se parecen en nada: el primero ordena y el segundo mide. Promediar niveles no
significa nada, y declararlo evita que alguien saque «el nivel medio».

### 7.2 La moneda, declarada como está y no como se promete

La unidad canónica del importe es **MXN**, y se declara así porque es lo que el
producto hace: las superficies que muestran dinero la traen escrita. El ajuste
`settings.currency` ofrece USD y EUR y ningún sitio de presentación lo lee, así
que hoy un inquilino en dólares vería sus importes rotulados en pesos.

Se declara la realidad y no la intención. **El disparador que invalida esta
declaración** es que la moneda del inquilino llegue a la presentación: ese día
la unidad canónica pasa a ser «la moneda del inquilino» y esta fila cambia.


## 8. Qué falta para cerrar este glosario

1. ~~Aprobación del owner, término por término.~~ **Hecha el 2026-08-04.**
2. ~~Decidir la **forma** del umbral de RAG de §2.4.~~ **Uno por dimensión, 2026-08-05.**
   ~~Calibrar los valores.~~ **Hecho el 2026-08-05** (US-196). Al calibrarlos apareció que
   el presupuesto no miraba el tiempo: 85 % gastado con 10 % de avance salía verde.
3. ~~Confirmar el método de avance de §2.3.~~ **Adoptado.**
4. ~~Decidir el **nombre** de la fase de hypercare.~~ **`hypercare`, hecho el 2026-08-05**
   (ADR-019, migración 0098). **`cancelled` añadida** (ADR-022); `initiation` no.

El plan de remediación ya puede escribirse; el orden sugerido está al final de
`03-REVISION-GLOSARIO.md`. Los tres cambios que tocan contrato —`wbs_code`,
`portfolio_function` y el nombre de la fase— van con ADR y US propia, uno por uno.
