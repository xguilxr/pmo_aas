"""US-224 (EP021) — catálogo de plantillas de operación, de solo lectura.

## Qué es esto, y qué deliberadamente no es

El artboard «Admin — IA» pedía un «catálogo de prompts». La palabra admite tres
lecturas y el owner eligió dos de las tres el 2026-08-20 (EP021, pregunta 1):

- **(a) texto libre editable por el inquilino — DESCARTADA.** No por el parser,
  sino por el conjunto de evaluación: si un inquilino reescribe la instrucción y
  el JSON deja de pedirse, `evaluacion-ia` sigue en verde porque mide los
  prompts del producto, no el suyo. Un gate que no puede ver el fallo que le
  toca ver es peor que no tener gate.
- **(b) un bloque de contexto que se AÑADE** al prompt del sistema — ya existe
  como `tenants.settings.ai.instructions_md`, y lo aplica `prompt_builder.py`.
- **(c) elegir entre variantes que trae el producto** — es este archivo.

Así que aquí viven **plantillas**, no prompts editables. Cada una declara su
propósito, qué datos necesita, en qué modo de IA corre y —lo que la hace
utilizable— **el contrato exacto de su salida**: las claves del JSON que el
producto va a leer. El contrato lo fija el producto en los dos casos, (b) y (c).

## Por qué la API no devuelve el texto del prompt

`plantilla_publica()` omite `sistema` a propósito. Un prompt renderizado en una
pantalla de administración se lee como un campo, y un campo invita a editarlo;
la primera petición después de mostrarlo sería «déjenme cambiar esta línea», que
es exactamente la opción (a) que se descartó. Se expone lo que sirve para
elegir —propósito, entradas, contrato, modo— y nada que sugiera edición.

## Por qué las plantillas solo leen

EP021 pregunta 2: las herramientas del catálogo **solo leen**. Una plantilla
recibe datos y devuelve texto estructurado que una persona confirma; ninguna
escribe en la base. Con AM-03 vivo —instrucciones inyectadas en contenido
subido— una plantilla que escribiera convertiría una inyección en una escritura
y el atacante dejaría de necesitar a alguien en el medio. Las salidas de aquí
son **propuestas**: el flujo minuta→RAID que ya existe es el patrón, y la
confirmación humana es parte del control, no una cortesía de interfaz.

## Versionado

`version` sube cuando cambia `sistema` o `claves_salida`. Cambiar un prompt en
producción tiene blast radius alto —cambia la salida que el usuario edita— y va
por PR como cualquier código (política de `docs/ai/prompts-catalog.md`). El
número viaja en la respuesta de la API para que un cliente que cachea sepa que
lo que tiene envejeció.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Modos de IA del inquilino en los que una plantilla puede correr.
#
# `platform` (Groq gestionado) se limita a minutas por DEC-017, así que toda
# plantilla que redacte narrativa ejecutiva exige `byo`. Declararlo aquí evita
# el 409 sorpresa: la pantalla puede ocultar lo que este inquilino no puede
# usar en vez de ofrecerlo y fallar al pulsar.
MODO_PLATAFORMA = "platform"
MODO_BYO = "byo"

CATEGORIAS = (
    "proyecto",
    "cartera",
    "gobernanza",
    "plan",
    "calidad",
)


@dataclass(frozen=True)
class Plantilla:
    """Una operación de IA que el producto ofrece, con su contrato de salida.

    `entradas` nombra los datos que el llamador debe aportar; se valida antes
    de gastar una llamada al proveedor. `claves_salida` son las claves exactas
    que el JSON de respuesta debe traer, y se valida después: entre las dos, un
    fallo del modelo se detecta aquí y no tres capas más arriba, donde ya se
    parece a un bug del producto.
    """

    id: str
    nombre: str
    proposito: str
    categoria: str
    modo_minimo: str
    entradas: tuple[str, ...]
    claves_salida: tuple[str, ...]
    version: int
    sistema: str


# --------------------------------------------------------------------------
# Fragmentos compartidos
#
# Se repiten literalmente en cada plantilla que los necesita en vez de vivir en
# un bucle: un trinquete que lee el fuente no ve tras una indirección, y este
# repositorio ya tropezó dos veces con eso (LESSONS, 2026-08-19).
# --------------------------------------------------------------------------
_SOLO_JSON = (
    "Devuelves SIEMPRE y ÚNICAMENTE un objeto JSON válido, sin texto antes ni "
    "después, sin bloques de código y sin claves además de las pedidas."
)

_SIN_INVENTAR = (
    "No inventas datos. Si un dato que necesitas no está en la entrada, lo "
    "dices con el texto «sin dato» en el campo correspondiente; nunca lo "
    "estimas ni lo rellenas con un valor plausible."
)

_ESPANOL = "Escribes en español neutro, claro y breve, en voz activa."


CATALOGO: dict[str, Plantilla] = {}


def _registrar(p: Plantilla) -> Plantilla:
    if p.id in CATALOGO:
        raise ValueError(f"plantilla duplicada: {p.id}")
    if p.categoria not in CATEGORIAS:
        raise ValueError(f"categoría desconocida en {p.id}: {p.categoria}")
    if p.modo_minimo not in (MODO_PLATAFORMA, MODO_BYO):
        raise ValueError(f"modo desconocido en {p.id}: {p.modo_minimo}")
    if not p.claves_salida:
        raise ValueError(f"{p.id} no declara contrato de salida")
    CATALOGO[p.id] = p
    return p


# --------------------------------------------------------------------------
# Proyecto
# --------------------------------------------------------------------------
_registrar(
    Plantilla(
        id="resumen-ejecutivo-proyecto",
        nombre="Resumen ejecutivo del proyecto",
        proposito=(
            "Convierte el estado de un proyecto en el párrafo que un director "
            "leería antes de una reunión de comité."
        ),
        categoria="proyecto",
        modo_minimo=MODO_BYO,
        entradas=("proyecto",),
        claves_salida=("resumen", "puntos_clave", "que_decidir"),
        version=1,
        sistema=f"""Eres el analista de una PMO. Recibes el estado de un proyecto \
y escribes el resumen que su patrocinador leería en dos minutos.

{_SOLO_JSON}
{{
  "resumen": "<3 a 5 oraciones: dónde está el proyecto, contra qué se compara \
y qué lo mueve>",
  "puntos_clave": ["<hecho con su cifra>", "..."],
  "que_decidir": ["<decisión que le corresponde al comité, no al PM>", "..."]
}}

Reglas:
- `puntos_clave`: entre 3 y 5, cada uno con el dato que lo sostiene. Un punto \
sin cifra ni fecha no es un punto clave, es una opinión.
- `que_decidir` lista solo lo que el comité puede resolver y el equipo no. Si \
no hay nada, devuelve [] — un comité al que se le lleva una lista inventada \
deja de leer las verdaderas.
- No repitas en `puntos_clave` lo que ya dijiste en `resumen`.
- Nunca califiques el proyecto de «exitoso» o «fracasado»: describe la \
desviación y deja el juicio a quien lee.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)

_registrar(
    Plantilla(
        id="explicacion-de-salud",
        nombre="Por qué el semáforo está en ese color",
        proposito=(
            "Traduce la evaluación de salud de 5+1 dimensiones a una "
            "explicación que el equipo pueda accionar."
        ),
        categoria="proyecto",
        modo_minimo=MODO_BYO,
        entradas=("evaluacion_salud",),
        claves_salida=("veredicto", "causas", "acciones_sugeridas"),
        version=1,
        sistema=f"""Eres el analista de salud de una PMO. Recibes la evaluación \
por dimensiones de un proyecto —cada una con su color y sus cifras— y explicas \
qué la produjo.

{_SOLO_JSON}
{{
  "veredicto": "<1 o 2 oraciones: qué color y qué dimensión lo determina>",
  "causas": [
    {{"dimension": "<nombre exacto de la dimensión recibida>",
      "color": "verde|amarillo|rojo",
      "porque": "<la cifra que la puso en ese color>"}}
  ],
  "acciones_sugeridas": ["<acción concreta con responsable sugerido>", "..."]
}}

Reglas:
- El color global lo determina la PEOR dimensión. Dilo explícitamente en \
`veredicto`, nombrando esa dimensión.
- `causas` incluye SOLO las dimensiones en amarillo o rojo. Las verdes no \
explican nada y alargan la lectura.
- Cada `porque` cita la cifra recibida. «El avance va retrasado» no sirve; \
«el avance real es 42% contra 61% esperado» sí.
- `acciones_sugeridas`: máximo 4, cada una ejecutable esta semana. Son \
propuestas para que una persona las confirme, no instrucciones.
- Si todas las dimensiones están en verde, `causas` es [] y `acciones_sugeridas` \
también: no hay nada que arreglar y decir lo contrario entrena a ignorarte.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)

_registrar(
    Plantilla(
        id="preguntas-de-seguimiento",
        nombre="Preguntas para la próxima reunión de estatus",
        proposito=(
            "Genera las preguntas que el PM debería hacer, a partir de las "
            "desviaciones y del RAID abierto."
        ),
        categoria="proyecto",
        modo_minimo=MODO_BYO,
        entradas=("proyecto", "raid_abierto"),
        claves_salida=("preguntas",),
        version=1,
        sistema=f"""Eres un PMO senior preparando la reunión de estatus de un \
proyecto. Recibes su avance y su RAID abierto, y escribes las preguntas que \
harías.

{_SOLO_JSON}
{{
  "preguntas": [
    {{"pregunta": "<pregunta directa, en segunda persona>",
      "porque": "<el dato que la motiva>",
      "a_quien": "<rol: PM, patrocinador, responsable del riesgo, ...>"}}
  ]
}}

Reglas:
- Entre 4 y 8 preguntas, ordenadas por lo que más mueve la aguja.
- Cada pregunta nace de un dato de la entrada. Si no puedes citar el dato en \
`porque`, no hagas la pregunta.
- Preguntas abiertas que exijan un dato o una fecha, no preguntas de sí/no: \
«¿para cuándo se cierra el riesgo R-12?» y no «¿va bien el riesgo R-12?».
- Prioriza lo vencido y lo que no tiene responsable sobre lo que va en fecha.
- Nada de preguntas de cortesía ni de resumen general.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)


# --------------------------------------------------------------------------
# Cartera
# --------------------------------------------------------------------------
_registrar(
    Plantilla(
        id="resumen-de-cartera",
        nombre="Narrativa de la cartera",
        proposito=(
            "Convierte los KPI de un portafolio o programa en la narrativa "
            "del reporte de dirección."
        ),
        categoria="cartera",
        modo_minimo=MODO_BYO,
        entradas=("kpis", "alcance"),
        claves_salida=("titular", "narrativa", "atencion_inmediata"),
        version=1,
        sistema=f"""Eres el analista de una PMO que escribe el reporte de \
cartera para la dirección. Recibes los KPI agregados de un alcance \
(organización, portafolio o programa) y su composición.

{_SOLO_JSON}
{{
  "titular": "<una oración: lo más importante que pasó en este corte>",
  "narrativa": "<2 a 4 párrafos cortos separados por \\n\\n>",
  "atencion_inmediata": [
    {{"proyecto": "<nombre>", "motivo": "<la cifra que lo pone aquí>"}}
  ]
}}

Reglas:
- Los importes van SIEMPRE con su moneda y NUNCA se suman entre monedas \
distintas. Si la entrada trae varias, se reportan por separado.
- Un porcentaje sin su base engaña: «30% de avance» se escribe «30% de avance \
sobre 42 proyectos activos».
- Si un KPI viene nulo, se dice «sin dato». Cero y «sin dato» son cosas \
distintas: cero proyectos no es cero por ciento.
- `atencion_inmediata`: máximo 5, y solo proyectos cuyo dato lo justifique.
- No compares contra periodos que no estén en la entrada.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)

_registrar(
    Plantilla(
        id="explicacion-de-indicador",
        nombre="Explicar un indicador a quien no lo calculó",
        proposito=(
            "Explica qué mide un indicador, qué incluye y qué no, a partir de "
            "su ficha, sin recalcularlo."
        ),
        categoria="cartera",
        modo_minimo=MODO_PLATAFORMA,
        entradas=("ficha_indicador", "valor_actual"),
        claves_salida=("que_mide", "como_leerlo", "que_no_dice"),
        version=1,
        sistema=f"""Eres quien explica los números de una PMO a alguien que no \
los calculó. Recibes la ficha de un indicador —fórmula, grano, inclusiones, \
exclusiones, tratamiento de nulos— y su valor actual.

{_SOLO_JSON}
{{
  "que_mide": "<1 o 2 oraciones, sin fórmula>",
  "como_leerlo": "<qué significa el valor actual, en concreto>",
  "que_no_dice": ["<una exclusión de la ficha, en lenguaje llano>", "..."]
}}

Reglas:
- `que_no_dice` sale de las EXCLUSIONES de la ficha, no de tu criterio. Es la \
parte más útil de la explicación y la que más se omite.
- No recalcules el indicador ni propongas una fórmula alternativa: la ficha \
está firmada y tu trabajo es traducirla, no revisarla.
- Si la ficha dice que el nulo se pinta «—», explica que el vacío es un dato y \
no un cero.
- Nada de analogías: el lector quiere el dato, no una metáfora.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)


# --------------------------------------------------------------------------
# Gobernanza
# --------------------------------------------------------------------------
_registrar(
    Plantilla(
        id="borrador-de-acta",
        nombre="Borrador del acta de constitución",
        proposito=(
            "Propone las secciones del acta a partir de una solicitud "
            "aprobada, para que el PM las edite."
        ),
        categoria="gobernanza",
        modo_minimo=MODO_BYO,
        entradas=("solicitud",),
        claves_salida=(
            "justificacion",
            "objetivos",
            "alcance_incluido",
            "alcance_excluido",
            "supuestos",
            "riesgos_iniciales",
        ),
        version=1,
        sistema=f"""Eres un PMO redactando el borrador del acta de constitución \
de un proyecto a partir de su solicitud aprobada. El acta la firma una persona: \
tu salida es un borrador para editar, no un documento final.

{_SOLO_JSON}
{{
  "justificacion": "<por qué existe este proyecto, 2 o 3 oraciones>",
  "objetivos": ["<objetivo medible con su criterio de éxito>", "..."],
  "alcance_incluido": ["<entregable o frente>", "..."],
  "alcance_excluido": ["<lo que explícitamente NO entra>", "..."],
  "supuestos": ["<supuesto cuya caída cambiaría el plan>", "..."],
  "riesgos_iniciales": [
    {{"riesgo": "<enunciado causa-evento-efecto>", "mitigacion": "<acción>"}}
  ]
}}

Reglas:
- `alcance_excluido` es obligatorio y no puede quedar vacío: un acta que no \
dice qué queda fuera no acota nada. Si la solicitud no lo menciona, propón lo \
que razonablemente se confundiría con este proyecto y márcalo como propuesta.
- Los objetivos llevan criterio de éxito verificable. «Mejorar el proceso» no \
es un objetivo; «reducir el tiempo de cierre de 5 a 3 días» sí.
- Los riesgos se enuncian como causa → evento → efecto, no como problemas ya \
ocurridos (eso sería una incidencia).
- Entre 2 y 5 elementos por lista. Un acta con veinte objetivos no tiene \
ninguno.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)

_registrar(
    Plantilla(
        id="redaccion-de-cambio",
        nombre="Formalizar una solicitud de cambio",
        proposito=(
            "Convierte la descripción informal de un cambio en la solicitud "
            "que un comité puede aprobar o rechazar."
        ),
        categoria="gobernanza",
        modo_minimo=MODO_BYO,
        entradas=("descripcion_libre", "proyecto"),
        claves_salida=(
            "titulo",
            "descripcion",
            "justificacion",
            "impacto",
            "alternativas",
        ),
        version=1,
        sistema=f"""Eres un PMO que convierte una petición informal en una \
solicitud de cambio formal. Recibes lo que alguien escribió y el contexto del \
proyecto.

{_SOLO_JSON}
{{
  "titulo": "<máximo 90 caracteres, empieza por un verbo>",
  "descripcion": "<qué cambia, en concreto>",
  "justificacion": "<por qué es necesario ahora>",
  "impacto": {{
    "alcance": "<qué se mueve, o «sin impacto»>",
    "cronograma": "<días o «sin dato»>",
    "presupuesto": "<importe con moneda, o «sin dato»>",
    "riesgos": "<riesgos que introduce o retira>"
  }},
  "alternativas": ["<alternativa considerada y por qué no se eligió>", "..."]
}}

Reglas:
- Los cuatro campos de `impacto` van siempre. «Sin dato» es una respuesta \
válida y honesta; omitir el campo no lo es, porque un comité que no ve la línea \
del presupuesto asume que no lo hay.
- Nunca estimes un importe ni un número de días que no venga en la entrada.
- `alternativas`: al menos una, y «no hacer nada» cuenta como alternativa \
legítima — casi siempre es la que falta.
- El título no repite el nombre del proyecto: ya se sabe dónde está.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)

_registrar(
    Plantilla(
        id="leccion-aprendida",
        nombre="Estructurar una lección aprendida",
        proposito=(
            "Convierte una nota de cierre en una lección reutilizable por "
            "otro proyecto."
        ),
        categoria="gobernanza",
        modo_minimo=MODO_PLATAFORMA,
        entradas=("nota_libre",),
        claves_salida=("titulo", "situacion", "leccion", "recomendacion", "fase"),
        version=1,
        sistema=f"""Eres el archivista de lecciones de una PMO. Recibes una nota \
de cierre y la conviertes en una lección que sirva a un proyecto que aún no \
existe.

{_SOLO_JSON}
{{
  "titulo": "<la lección en una línea, sin nombres propios>",
  "situacion": "<qué pasó, en pasado y sin culpables>",
  "leccion": "<qué se aprendió, generalizado>",
  "recomendacion": "<qué hacer distinto la próxima vez, en imperativo>",
  "fase": "preparacion|ejecucion|hypercare|cierre"
}}

Reglas:
- `fase` toma exactamente uno de esos cuatro valores. La fase de cierre se \
dice «cierre», no «cerrado».
- Sin nombres de personas. Una lección que señala a alguien deja de \
registrarse la próxima vez, y el registro vale más que el señalamiento.
- `leccion` tiene que ser cierta fuera de este proyecto. Si no se puede \
generalizar, no es una lección: es una anécdota, y lo dices en `leccion`.
- `recomendacion` en imperativo y accionable por alguien que no vivió el caso.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)


# --------------------------------------------------------------------------
# Plan
# --------------------------------------------------------------------------
_registrar(
    Plantilla(
        id="revision-de-plan",
        nombre="Revisión de calidad del plan",
        proposito=(
            "Señala los defectos estructurales de un plan importado: tareas "
            "sin responsable, hitos con duración, cadenas sin dependencia."
        ),
        categoria="plan",
        modo_minimo=MODO_BYO,
        entradas=("tareas",),
        claves_salida=("hallazgos", "resumen"),
        version=1,
        sistema=f"""Eres un planificador senior revisando el plan de un proyecto. \
Recibes su lista de tareas con código EDT, fechas, responsable, dependencias y \
marca de hito.

{_SOLO_JSON}
{{
  "hallazgos": [
    {{"tipo": "sin_responsable|hito_con_duracion|sin_dependencia|\
fecha_incoherente|nombre_ambiguo|duracion_excesiva",
      "wbs": "<código EDT de la tarea>",
      "detalle": "<qué está mal, con el dato>",
      "gravedad": "alta|media|baja"}}
  ],
  "resumen": "<1 o 2 oraciones: el patrón dominante de los hallazgos>"
}}

Reglas:
- `tipo` toma exactamente uno de los seis valores listados. Si un defecto no \
cae en ninguno, no lo reportes: un catálogo abierto deja de ser filtrable.
- Un hito con duración mayor que cero es siempre un hallazgo: un hito es un \
instante.
- `duracion_excesiva` solo si la tarea pasa de 20 días hábiles y no es un \
resumen (no tiene hijos).
- `nombre_ambiguo`: nombres como «Fase 1», «Varios» o «Pendiente», que no \
dicen qué se entrega.
- Ordena `hallazgos` por gravedad descendente. Máximo 30; si hay más, quédate \
con los 30 más graves y dilo en `resumen`.
- No propongas fechas ni reestructures el plan: señalas, no reescribes.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)


# --------------------------------------------------------------------------
# Calidad
# --------------------------------------------------------------------------
_registrar(
    Plantilla(
        id="riesgos-desde-texto",
        nombre="Riesgos e incidencias desde texto libre",
        proposito=(
            "Extrae candidatos a riesgo, incidencia, acción o decisión desde "
            "un texto, para que una persona los confirme."
        ),
        categoria="calidad",
        modo_minimo=MODO_PLATAFORMA,
        entradas=("texto",),
        claves_salida=("candidatos",),
        version=1,
        sistema=f"""Eres un PMO leyendo un texto de proyecto —un correo, una \
nota, un fragmento de minuta— y extrayendo lo que debería entrar al RAID.

{_SOLO_JSON}
{{
  "candidatos": [
    {{"tipo": "R|I|A|D",
      "descripcion": "<enunciado en una oración>",
      "responsable": "<nombre mencionado, o null>",
      "fecha": "<fecha mencionada en AAAA-MM-DD, o null>",
      "confianza": "alta|media|baja"}}
  ]
}}

Reglas:
- Los cuatro tipos y nada más: R riesgo (aún no ocurrió), I incidencia (ya \
ocurrió), A acción (alguien hace algo), D decisión (algo quedó resuelto). Una \
lección aprendida o una solicitud de cambio NO son RAID: se descartan.
- `responsable` y `fecha` van a null si el texto no los dice. No los deduzcas \
del contexto ni del remitente.
- `confianza` baja significa «esto quizá no es un ítem RAID»; inclúyelo igual \
y deja que la persona decida. Es la mitad del valor: un extractor que solo \
reporta lo obvio no aporta sobre leer el texto.
- Un riesgo se enuncia con su efecto: «si X, entonces Y».
- Si el texto no contiene nada del RAID, `candidatos` es []. Devolver algo \
para no volver vacío es el peor fallo posible aquí.
{_SIN_INVENTAR}
{_ESPANOL}""",
    )
)


# --------------------------------------------------------------------------
# Acceso
# --------------------------------------------------------------------------
def listar(*, modo_tenant: str | None = None) -> list[Plantilla]:
    """Las plantillas del catálogo, opcionalmente filtradas por modo de IA.

    Un inquilino en `platform` no ve las que exigen `byo`: ofrecérselas para
    que fallen con 409 al pulsar convierte una limitación conocida en un
    incidente de soporte.
    """
    plantillas = sorted(CATALOGO.values(), key=lambda p: (p.categoria, p.id))
    if modo_tenant == MODO_PLATAFORMA:
        return [p for p in plantillas if p.modo_minimo == MODO_PLATAFORMA]
    if modo_tenant in (None, MODO_BYO):
        return plantillas
    # `disabled` u otro modo: el catálogo existe pero nada corre.
    return []


def obtener(plantilla_id: str) -> Plantilla | None:
    return CATALOGO.get(plantilla_id)


def plantilla_publica(p: Plantilla) -> dict[str, Any]:
    """La vista que sale por la API. **Sin `sistema`** — ver el encabezado."""
    return {
        "id": p.id,
        "nombre": p.nombre,
        "proposito": p.proposito,
        "categoria": p.categoria,
        "modo_minimo": p.modo_minimo,
        "entradas": list(p.entradas),
        "claves_salida": list(p.claves_salida),
        "version": p.version,
    }


def validar_entradas(p: Plantilla, datos: dict[str, Any]) -> list[str]:
    """Qué entradas declaradas faltan. Lista vacía = se puede llamar al modelo."""
    return [
        campo
        for campo in p.entradas
        if campo not in datos or datos[campo] in (None, "", [], {})
    ]


def validar_salida(p: Plantilla, salida: dict[str, Any] | None) -> list[str]:
    """Qué claves del contrato faltan en la respuesta del modelo.

    Se comprueba la presencia, no el tipo: el contrato dice qué claves lee el
    producto, y una clave presente con la forma equivocada la detecta el
    consumidor, que sabe qué esperaba. Validar aquí el tipo duplicaría esa
    regla en dos sitios, que es como se desincronizan.
    """
    if salida is None:
        return list(p.claves_salida)
    return [clave for clave in p.claves_salida if clave not in salida]
