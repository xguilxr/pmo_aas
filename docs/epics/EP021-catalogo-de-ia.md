---
tipo: epica
responsable: propietario
estado: borrador
revisado: 2026-08-20
revisar_cada: 30d
---

# EP021 — Catálogo de IA y roles de agente (US-220)

| Campo | Valor |
|---|---|
| **ID** | EP021 |
| **Prioridad** | P1 (el artboard la marca así) |
| **Dependencias** | EP008 (IA viva en producción), EP007 (admin), modelo de amenazas AM-03/AM-04 |
| **Módulo** | `apps/api/app/services/ai/`, `/admin/ai` |
| **Estado** | **BORRADOR — necesita decisión del owner antes de implementar** |
| **Origen** | Artboard «Admin — IA» de los mockups aprobados el 2026-08-19 |

## Por qué esto es una epic y no la US-220

El plan de fase 2 la listaba como una US. Al ir a implementarla, lo que el
artboard pide son **cinco cosas** y una de ellas es un sistema de autorización
nuevo:

```
Provider BYOK (provider, modelo, API key, límites)   ← existe (EP008)
Consumo / alertas                                    ← parcial (AIJob tiene tokens)
Catálogo: skills · tools · prompts · workflows       ← NUEVO, cuatro conceptos
Roles de agente (personalidad + permisos propios)    ← NUEVO, «separado del RBAC»
```

Una US es una instrucción técnica puntual (CLAUDE.md §0.2). Esto son cuatro
catálogos con su modelo de datos, más un segundo modelo de permisos. Escribirlo
en un commit sería inventar el producto, y quedaría como si alguien lo hubiera
decidido.

**Lo que hace falta del owner no es aprobación, son definiciones.** Abajo están
las preguntas, cada una con lo que ya se sabe del código, para que contestarlas
sea corto.

## Lo que ya existe, y por eso no hay que rehacerlo

Verificado contra el código el 2026-08-20:

| Pieza | Dónde | Estado |
|---|---|---|
| Proveedor BYOK por inquilino | `endpoints/admin_ai.py` (`/provider`, `/provider/test`) | Vivo |
| Modelo y clave cifrada (Fernet) | `services/ai/tenant_ai.py` | Vivo |
| Registro de trabajos con tokens | `models/ai.py::AIJob` (`tokens_in`, `tokens_out`, `model_used`) | Vivo |
| Frontera de la salida del modelo | `services/ai/frontera.py`, `untrusted.py` | Vivo (AM-03, AM-04) |
| Conjunto de evaluación | `apps/api/evaluacion/` + job `evaluacion-ia` | Vivo, umbral eliminatorio |
| Prompts de sistema | `services/ai/prompts.py`, constantes de Python | Vivo |

**El consumo ya se puede contar** — `AIJob` tiene los tokens y el modelo — así que
la fila «Consumo / alertas» del artboard es trabajo pequeño y **no** depende de
las decisiones de abajo. Puede salir sola.

## Las cuatro preguntas que bloquean

### 1. Un «prompt» editable choca con el contrato de salida

`prompts.py` no guarda texto libre: guarda **contratos**. `MINUTE_SYSTEM` declara
un JSON de seis secciones con claves fijas, enums estrictos y orden. El código que
consume esa respuesta espera exactamente esa forma, y el conjunto de evaluación
mide **estas** instrucciones, no las que un inquilino escriba después.

Así que «catálogo de prompts» puede querer decir tres cosas muy distintas:

- **(a) Texto libre editable.** El inquilino reescribe la instrucción. Es lo que
  la palabra sugiere y es lo que rompe la funcionalidad: una instrucción que ya
  no pide el JSON de seis secciones deja al parser sin nada que parsear, y el
  conjunto de evaluación seguiría verde porque mide otra cosa.
- **(b) Un bloque de contexto que se **añade** al prompt del sistema.** El
  contrato de salida lo sigue fijando el producto; el inquilino aporta
  vocabulario, tono, nombres propios. Esto ya existe a medias como
  `ai-context` del proyecto, y ampliarlo es acotado.
- **(c) Elegir entre variantes que el producto trae.** Un catálogo de solo
  lectura con selección, sin edición.

**Pregunta:** ¿(a), (b) o (c)? Si es (a), hace falta además decidir qué pasa con
el conjunto de evaluación —¿se evalúa el prompt del inquilino al guardarlo?— y qué
se le muestra cuando su prompt rompe la salida.

### 2. Qué es una «tool», y qué puede tocar

Una herramienta que el modelo puede invocar es, en la práctica, **una puerta
nueva a los datos** — y esta plataforma ya tiene dos amenazas registradas
alrededor de eso: AM-03 (instrucciones inyectadas en contenido subido) y AM-04
(la salida del modelo cruza al producto). Una herramienta que escriba convierte
una inyección en una escritura.

**Pregunta:** ¿las herramientas de este catálogo **leen** o también **escriben**?
Si escriben, esta epic arranca por el modelo de amenazas (§0.3) y no por el
esquema.

### 3. Qué es un «workflow», y quién lo ejecuta

Un encadenado de pasos puede ser: una plantilla de secuencia que una persona
dispara y confirma paso a paso, o algo que corre solo con un disparador. La
diferencia no es de interfaz: lo segundo necesita cola, reintentos, límite de
gasto y una respuesta a «qué pasa si el paso 3 falla después de que el 2 escribió».

**Pregunta:** ¿asistido por una persona, o autónomo? Si es autónomo, ¿con qué
techo de gasto y sobre qué disparadores?

### 4. «Roles de agente, separado del RBAC» es un segundo sistema de permisos

Es la decisión más cara del artboard, en una frase de cinco palabras. Hoy hay un
modelo: capacidades por rol más alcance por asignación
(`user_scope_assignments`, AM-15). Un agente con «permisos propios» significa que
una petición podría estar autorizada por un camino que el primer modelo no
conoce, y entonces hay dos respuestas posibles a «¿puede esto tocar aquello?».

Dos formas de hacerlo, y solo la segunda es barata:

- **Un sistema aparte.** Es lo que la frase dice. Duplica el punto donde se
  decide, y el día que alguien arregle un agujero en uno, el otro sigue abierto.
- **Un agente actúa siempre *en nombre de* una persona**, con sus capacidades y
  su alcance, y lo «propio» del rol es la **personalidad** —tono, formato,
  qué mira— y un techo, nunca un permiso extra. Con esto no hay segundo sistema:
  hay un límite sobre el que ya existe.

**Pregunta:** ¿la segunda forma cubre lo que el artboard quiere? Si de verdad hace
falta la primera, el modelo de amenazas va antes del código y esta epic crece.

## Lo que se propone construir, si las respuestas son las acotadas

Orden por lo que desbloquea, y cada bloque es una US:

| # | Qué | Depende de |
|---|---|---|
| **US-222** ✅ | Consumo de IA por inquilino: trabajos, tokens y reparto por modelo, seis meses. `GET /admin/ai/usage` + panel en `/admin/ai`. **Sin dinero, a propósito** (ver abajo) | Nada — `AIJob` ya lo tenía |
| **US-223** | Catálogo de **contexto** por inquilino: bloques de vocabulario que se añaden al prompt del sistema sin tocar el contrato de salida | Respuesta (b) a la pregunta 1 |
| **US-224** | Catálogo de **plantillas de operación** (las variantes que el producto trae), de solo lectura con selección | Respuesta (c) a la pregunta 1 |
| **US-225** | Roles de agente como **personalidad + techo**, actuando en nombre de una persona | Respuesta 2 a la pregunta 4 |
| **US-226** | Herramientas de **lectura** invocables, con la frontera de AM-04 delante | Respuesta «solo leen» a la pregunta 2 |

**Workflows queda fuera de esta propuesta a propósito.** Con las preguntas 2 y 3
sin contestar, cualquier esquema que se escriba hoy se va a rehacer.

### US-222 — entregada el 2026-08-20

`GET /admin/ai/usage` y el panel al pie de `/admin/ai`: trabajos y tokens por mes
(seis meses), reparto por modelo del mes en curso, y los fallidos del mes.

**No devuelve dinero, y la pantalla dice por qué.** La propuesta original de esta
tabla decía «costo estimado». Al implementarla quedó claro que no se puede: la
tarifa de cada modelo la fija su proveedor, cambia cuando él la cambia y **no la
controlamos**. Un importe calculado con una tarifa de hace seis meses se leería
como el gasto, no lo sería, y nadie volvería a comprobarlo. Se cuentan tokens, que
es el dato que sí es nuestro, y quien tenga la tarifa multiplica con información
fresca. Es el mismo criterio que `dominio/moneda.py` con la conversión entre
monedas: sin un tipo de cambio con fecha, el resultado deja de ser un dato.

**La alerta contra el tope del plan queda para cuando US-221 y esto se junten.**
El tope de `ai_jobs_month` ya existe (US-221) y el consumo ya se cuenta aquí; lo
que falta es decidir **cómo** se avisa —correo, notificación en la aplicación,
solo el color de la pantalla— y a quién. Es una decisión de producto de una línea,
y esta epic ya tiene cuatro esperando.

**Decisiones que quedaron en el código:**
- **Un mes sin trabajos aparece con ceros**, no se omite. Un hueco en una serie se
  lee como continuidad, y ahí el cero es un dato: nadie usó la IA ese mes.
- **El reparto es por modelo, no por proveedor.** Dos modelos del mismo proveedor
  cuestan distinto, y el que se cambia cuando el gasto molesta es el modelo. El
  proveedor viaja al lado para no obligar a adivinarlo.
- **Los fallidos van junto al total.** «120 trabajos este mes» con treinta
  fallidos se lee como éxito. Misma pareja que el costo con «sin tarifa» (US-215)
  y la importación con «quedaron fuera» (US-216).
- **Un trabajo sin tokens cuenta como trabajo.** Falló antes de consumir, pero
  ocurrió; descartarlo haría que el conteo de trabajos y el de tokens hablaran de
  conjuntos distintos.
- **Un modelo `null` se nombra** («falló antes de elegirlo») en vez de
  descartarse.
- **La agrupación por mes se hace en Python**, no con `strftime`/`to_char`. La
  suite corre sobre SQLite y producción sobre Postgres: una rama por motor deja
  la mitad de producción sin probar. El precio es traer tres columnas de los
  trabajos de seis meses de un inquilino, que es acotado.

**Tests (`tests/test_us222_consumo_ia.py`, 12):** la ventana de meses en orden y
cruzando el año; un mes sin trabajos con ceros; suma por mes; un trabajo sin
tokens; el reparto por modelo ordenado y acotado al mes en curso; un modelo nulo;
los fallidos junto al total; **que la respuesta no contenga dinero**; aislamiento
por inquilino; lo anterior a la ventana no entra.

## Lo que NO se va a hacer sin decisión escrita

- Prompts de sistema editables como texto libre (pregunta 1a) sin resolver qué
  pasa con el contrato de salida y con el conjunto de evaluación.
- Herramientas que escriban (pregunta 2) sin pasar antes por el modelo de
  amenazas.
- Ejecución autónoma (pregunta 3) sin techo de gasto declarado.
- Un modelo de permisos separado del RBAC (pregunta 4) sin la amenaza escrita y
  su control.

Las cuatro tienen la misma forma: son decisiones de producto o de seguridad
disfrazadas de trabajo de implementación. Tomarlas desde el código las deja sin
que nadie las haya tomado.

## Notas

- **2026-08-20 — origen.** El plan de fase 2 (`reestructura-fase2-plan.md`)
  listaba US-220 como una US de la oleada 2C. Al implementarla se separó en esta
  epic: son cinco entregables y uno de ellos es un sistema de autorización.
  El resto de la oleada 2C quedó cerrado (US-210 a US-219, US-221).
