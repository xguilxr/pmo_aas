---
tipo: epica
responsable: propietario
estado: vigente
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
| **Estado** | **Decidido** — las cuatro preguntas contestadas por el owner el 2026-08-20 |
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

**Lo que hacía falta del owner no era aprobación, eran definiciones.** Abajo
están las cuatro preguntas con lo que se sabía del código y, bajo cada una, la
respuesta del owner del 2026-08-20. Las cuatro salieron en su forma acotada, así
que US-223 a US-226 quedan desbloqueadas y los workflows siguen fuera.

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

## Las cuatro preguntas, contestadas el 2026-08-20

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

**Respuesta del owner (2026-08-20): (b) y (c), nunca (a).**

No son excluyentes y por eso son dos US distintas: (b) es un bloque de contexto
que **se añade** al prompt del sistema —vocabulario, tono, nombres propios— y (c)
es un catálogo de variantes que trae el producto, de solo lectura con selección.
El contrato de salida lo sigue fijando el producto en los dos casos.

(a) queda descartada por lo que le hace al conjunto de evaluación, no por lo que
le hace al parser. Un inquilino reescribe la instrucción, el JSON de seis
secciones deja de pedirse, el parser se queda sin nada — y `evaluacion-ia` sigue
en verde, porque mide los prompts del producto y no el del inquilino. Un gate que
no puede ver el fallo que le toca ver es peor que no tener gate: da por
contenido lo que no lo está. Desbloquea **US-223** y **US-224**.
### 2. Qué es una «tool», y qué puede tocar

Una herramienta que el modelo puede invocar es, en la práctica, **una puerta
nueva a los datos** — y esta plataforma ya tiene dos amenazas registradas
alrededor de eso: AM-03 (instrucciones inyectadas en contenido subido) y AM-04
(la salida del modelo cruza al producto). Una herramienta que escriba convierte
una inyección en una escritura.

**Pregunta:** ¿las herramientas de este catálogo **leen** o también **escriben**?
Si escriben, esta epic arranca por el modelo de amenazas (§0.3) y no por el
esquema.

**Respuesta del owner (2026-08-20): solo leen.**

Una herramienta que escribe convierte AM-03 —instrucciones inyectadas en
contenido subido— en una escritura, y con eso el atacante deja de necesitar a una
persona en el medio. Las herramientas de lectura con la frontera de AM-04 delante
son **US-226** y se pueden construir con el modelo de amenazas que ya existe.

Las de escritura no son «lo mismo pero más»: son otra amenaza, y si algún día se
piden, esta epic arranca por `docs/architecture/modelo-amenazas.md` y no por el
esquema (§0.3).
### 3. Qué es un «workflow», y quién lo ejecuta

Un encadenado de pasos puede ser: una plantilla de secuencia que una persona
dispara y confirma paso a paso, o algo que corre solo con un disparador. La
diferencia no es de interfaz: lo segundo necesita cola, reintentos, límite de
gasto y una respuesta a «qué pasa si el paso 3 falla después de que el 2 escribió».

**Pregunta:** ¿asistido por una persona, o autónomo? Si es autónomo, ¿con qué
techo de gasto y sobre qué disparadores?

**Respuesta del owner (2026-08-20): asistido por una persona; lo autónomo se
difiere.**

Una plantilla de secuencia que alguien dispara y confirma paso a paso. La
ejecución autónoma necesita cola, reintentos, techo de gasto y una respuesta a
«qué pasa si el paso 3 falla después de que el 2 escribió» — eso es un subsistema,
no una variante de interfaz.

**Aun así, los workflows no entran en esta oleada.** Ni siquiera el asistido: no
hay US para ellos abajo y no se escribe esquema todavía. Es deliberado — la
pregunta 2 fija que las herramientas solo leen, y un encadenado de pasos que solo
lee tiene bastante menos que orquestar de lo que el artboard supone. Se replantea
cuando US-226 esté viva y se sepa qué encadenar.
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

## Lo que se va a construir

Las respuestas fueron las acotadas, así que esto deja de ser una propuesta.

Orden por lo que desbloquea, y cada bloque es una US:

| # | Qué | Depende de |
|---|---|---|
| **US-222** ✅ | Consumo de IA por inquilino: trabajos, tokens y reparto por modelo, seis meses. `GET /admin/ai/usage` + panel en `/admin/ai`. **Sin dinero, a propósito** (ver abajo) | Nada — `AIJob` ya lo tenía |
| **US-223** | Catálogo de **contexto** por inquilino: bloques de vocabulario que se añaden al prompt del sistema sin tocar el contrato de salida | ✅ P1 = (b) |
| **US-224** | Catálogo de **plantillas de operación** (las variantes que el producto trae), de solo lectura con selección | ✅ P1 = (c) |
| **US-225** | Roles de agente como **personalidad + techo**, actuando en nombre de una persona | ✅ P4 = en nombre de una persona (DEC-033) |
| **US-226** | Herramientas de **lectura** invocables, con la frontera de AM-04 delante | ✅ P2 = solo leen |

**Workflows sigue fuera a propósito**, ahora por una razón distinta: contestada
la pregunta 2, un encadenado que solo lee tiene mucho menos que orquestar de lo
que el artboard supone. Se replantea con US-226 viva, no antes.

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

## Lo que sigue sin hacerse, y ahora por decisión escrita

- Prompts de sistema editables como texto libre (pregunta 1a) sin resolver qué
  pasa con el contrato de salida y con el conjunto de evaluación.
- Herramientas que escriban (pregunta 2) sin pasar antes por el modelo de
  amenazas.
- Ejecución autónoma (pregunta 3) sin techo de gasto declarado.
- Un modelo de permisos separado del RBAC (pregunta 4) sin la amenaza escrita y
  su control.

Las cuatro tenían la misma forma: decisiones de producto o de seguridad
disfrazadas de trabajo de implementación. Ya están tomadas, y las cuatro se
tomaron por la opción acotada — así que esta lista deja de ser un bloqueo y pasa
a ser el límite del alcance. Reabrir cualquiera de ellas es trabajo nuevo con su
modelo de amenazas delante, no un ajuste.

## Notas

- **2026-08-20 — origen.** El plan de fase 2 (`reestructura-fase2-plan.md`)
  listaba US-220 como una US de la oleada 2C. Al implementarla se separó en esta
  epic: son cinco entregables y uno de ellos es un sistema de autorización.
  El resto de la oleada 2C quedó cerrado (US-210 a US-219, US-221).

**Respuesta del owner (2026-08-20): el agente actúa siempre en nombre de una
persona.**

Lleva las capacidades y el alcance de esa persona (`user_scope_assignments`,
AM-15). Lo «propio» del rol es la **personalidad** —tono, formato, qué mira— y un
**techo**; nunca un permiso que la persona no tenga. No hay segundo sistema: hay
un límite sobre el que ya existe, y un límite sobre un modelo de permisos se
puede razonar; dos modelos de permisos, no.

Lo que se evita es concreto: con dos sitios donde se decide «¿puede esto tocar
aquello?», el día que alguien tape un agujero en uno, el otro sigue abierto — y
nada en el código señala que había dos. Es **US-225**, y queda como **DEC-033**
porque es una decisión de arquitectura, no de alcance.
