# Glosario canónico del dominio PMO

| Campo | Valor |
|---|---|
| Estado | **Borrador.** Ningún término está adoptado hasta que el owner lo apruebe |
| Fecha | 2026-08-03 |
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

**Vocabulario propuesto** — cinco fases, alineadas con ISO 21502 y PMBOK, en inglés en el
código y español en la UI:

| Código | UI | Qué la cierra |
|---|---|---|
| `initiation` | Inicio | Acta de constitución autorizada |
| `planning` | Planeación | Línea base aprobada |
| `execution` | Ejecución | Entregables aceptados |
| `closing` | Cierre | Cierre formal y lecciones registradas |
| `cancelled` | Cancelado | Decisión de terminación anticipada |

**Vetado:** `support` / `Soporte` como fase. Operación no es fase de proyecto: empieza
cuando el proyecto terminó. Si hay que representarlo, va como **estado posterior al cierre**
o como servicio, no como fase.

**Vetado:** literales en español dentro del código (`"Inicio"`, `"Ejecución"`, `"Cierre"`).
El código va en inglés; la traducción vive en la capa de presentación.

> **Brecha B-2.** Hoy: `PHASES = ["planning", "execution", "support"]`, más cinco
> ocurrencias de `"Inicio"`/`"inicio"` y una de `"Ejecución"` y `"Cierre"` sueltas.

### 1.2 Hito

**Preferente:** `hito` · **En código:** `milestone` · **Vetado:** `entregable` como sinónimo

Punto de control de **duración cero** que marca un evento significativo. No consume
recursos. Un entregable es un *producto*; un hito es una *fecha*. Un entregable puede tener
un hito asociado, pero no son lo mismo.

**Regla:** `is_milestone = true` ⟹ `duration_days = 0`. Hoy no está validado.

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

**Regla propuesta:** avance de tarea **declarado**; avance de proyecto **ponderado por
duración** de sus tareas hoja. Debe declararse en la UI, junto al número.

**Regla de reconciliación:** el avance del proyecto debe ser reproducible a partir de sus
tareas. Si no cuadra, es defecto.

> **Brecha B-5.** Hoy `progress: int` en tarea y proyecto, sin método declarado.

### 2.4 Estado de salud (RAG)

**Preferente:** `estado de salud` · **En código:** `health_status`
**Valores:** `red` · `amber` · `green`
**Vetado:** `yellow` (3 usos), `Verde`/`Amarillo`/`Rojo` (3 usos)

RAG —*Red, Amber, Green*— es el término de P3O y PRINCE2. `amber` es el valor correcto;
`yellow` es informal y hoy convive con él.

**Regla — la pieza que falta.** Un semáforo sin fórmula es una opinión con color. Propuesta,
a validar:

| Estado | Criterio |
|---|---|
| `green` | Sin desviación material y sin riesgos altos abiertos |
| `amber` | Desviación dentro del umbral, o riesgo alto con plan de respuesta |
| `red` | Desviación fuera del umbral, o riesgo alto sin plan, o incidencia crítica abierta |

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

| Vetado | Preferente | Ocurrencias hoy | Dónde |
|---|---|---|---|
| `support` como fase | estado posterior al cierre | 1 enum | `PHASES` |
| `"Inicio"`, `"Ejecución"`, `"Cierre"` en código | `initiation`, `execution`, `closing` | 7 | `apps/api/app/` |
| `yellow` | `amber` | 33 + 3 | transversal |
| `Verde`/`Amarillo`/`Rojo` en código | `green`/`amber`/`red` | 3 | transversal |
| Dos paletas de salud | una definición única | 2 mapas | `HEALTH_DONUT_COLOR`, `HEALTH_HEX` |
| `wbs` para el código de tarea | `wbs_code` | 1 campo | `tasks.wbs` |
| `portafolio` para un área | — | 4 | `area.py` y otros |
| `problema` / `bug` para incidencia de proyecto | `incidencia` | por revisar | — |

---

## 7. Qué falta para cerrar este glosario

1. **Aprobación del owner**, término por término. Nada de esto está adoptado.
2. **Decidir el umbral de RAG** de §2.4. Es la única regla que exige criterio de negocio, no
   de estándar.
3. **Confirmar el método de avance** de §2.3.
4. Recién entonces: plan de remediación con los renombrados, la migración de `phase`, la
   unificación de paletas y la introducción de línea base.

El plan de remediación **no se escribe hasta que este documento esté aprobado**. Escribirlo
antes sería planificar sobre vocabulario que todavía puede cambiar.
