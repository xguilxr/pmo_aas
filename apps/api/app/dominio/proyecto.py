"""El vocabulario del proyecto: en qué fase está y de qué tipo es.

> **Reestructura de plataforma, US-202 / ADR-038.** Las fases del proyecto se
> llamaban `planning | execution | hypercare | closed | cancelled` y el tipo era
> texto libre. Pasan a `preparacion | ejecucion | hypercare | cerrado |
> cancelado` y a un enum de cuatro tipos.

## Por qué en español

No es cosmética. El glosario del producto está en español, la interfaz está en
español y las personas que usan la plataforma hablan español. Un valor guardado
en inglés obliga a una tabla de traducción en cada superficie que lo muestre —y
había cuatro, cada una con su propio diccionario: `lessons_export.py`,
`status_display.py`, los badges del frontend y los `<option>` de los formularios.
Cuatro copias del mismo mapeo es cuatro sitios donde se desincroniza.

`hypercare` se queda como está, y a propósito: no tiene traducción que no sea
peor («acompañamiento», «post-arranque»), es el término que usa la operación, y
ya lo renombró ADR-019 hace dos semanas. Renombrarlo otra vez sería gastar una
segunda ventana de compatibilidad para empeorar el nombre.

## Por qué un módulo y no literales sueltos

Antes de US-202, `"closed"` aparecía escrito a mano en 13 archivos: cinco
`if p.phase == "closed"`, cuatro `Project.phase != "closed"`, una lista de fases
activas en el dashboard y otra en el panel de administración. Ninguna estaba mal,
y ahí está el problema: al renombrar, la que se olvide **no falla** — sigue
comparando contra un valor que ya no existe y devuelve siempre falso. Un proyecto
cerrado contaría como activo, y nadie vería un error.

Con las constantes aquí, olvidarse es un `NameError` en el arranque.

## Fases: qué son y qué no

Cinco, y ninguna es «solicitud»: una solicitud todavía no es un proyecto, vive en
`project_requests.status` y el proyecto **nace** en preparación. Meterla como
fase obligaría a que todo proyecto pasara por ella, incluido el que se captura
directo o el que entra por importación masiva.

`cerrado` y `cancelado` son los dos finales, y son distintos: hasta ADR-022 un
proyecto cortado a mitad terminaba en `closed`, indistinguible de uno que
cumplió. Contaba como entregado en cualquier métrica de éxito y sus lecciones se
mezclaban con las de los que llegaron al final.

## Tipos: por qué enum y no texto libre

`projects.type` era `String(50)` sin validar. El cliente de 23 proyectos pidió
poder responder «cuánto de mi cartera es transformación y cuánto es mantener las
luces encendidas», y eso no se puede contestar sobre texto libre: `BAU`, `bau`,
`Bau` y `Business as usual` son cuatro categorías distintas para un `GROUP BY`.

Cuatro valores, no más: el que necesita un quinto está describiendo un atributo
distinto (una disciplina, un programa), no un tipo de proyecto.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Fases
# ---------------------------------------------------------------------------

PREPARACION = "preparacion"
EJECUCION = "ejecucion"
#: Sin traducir a propósito — ver el encabezado.
HYPERCARE = "hypercare"
CERRADO = "cerrado"
CANCELADO = "cancelado"

#: En orden del ciclo de vida. El orden importa: lo consumen los desplegables y
#: los ejes de los gráficos por fase, que sin él saldrían alfabéticos.
FASES: tuple[str, ...] = (PREPARACION, EJECUCION, HYPERCARE, CERRADO, CANCELADO)

#: Los dos finales. Ninguno admite transición de salida y ninguno cuenta como
#: activo.
FASES_TERMINALES: frozenset[str] = frozenset({CERRADO, CANCELADO})

#: Lo que cuenta como «en marcha» en KPIs, capacidad y snapshots.
FASES_ACTIVAS: tuple[str, ...] = tuple(f for f in FASES if f not in FASES_TERMINALES)

#: El ciclo de vida, como grafo. `cancelado` se alcanza desde cualquier fase
#: viva: un proyecto se cancela cuando se cancela, no cuando le toca.
TRANSICIONES: dict[str, frozenset[str]] = {
    PREPARACION: frozenset({EJECUCION, CERRADO, CANCELADO}),
    EJECUCION: frozenset({HYPERCARE, CERRADO, CANCELADO}),
    HYPERCARE: frozenset({CERRADO, CANCELADO}),
    CERRADO: frozenset(),
    CANCELADO: frozenset(),
}

#: Ventana de compatibilidad (ADR-038). El nombre viejo se acepta a la entrada y
#: se guarda ya como el canónico. `support` viene de la ventana anterior
#: (ADR-019) y sigue aquí: cerrarla es una decisión con su propio contador.
FASES_RENOMBRADAS: dict[str, str] = {
    "planning": PREPARACION,
    "execution": EJECUCION,
    "support": HYPERCARE,
    "closed": CERRADO,
    "cancelled": CANCELADO,
}

#: Quién registra cada nombre retirado en el contador de compat vive en
#: `schemas/project.py::_AVISAR_FASE`, con la clave escrita literal para que el
#: trinquete de `test_ventanas_compatibilidad.py` la encuentre.

#: Para reportes y exportables. Una sola copia: había cuatro diccionarios con
#: este mapeo y ninguno igual a otro.
ETIQUETAS_FASE: dict[str, str] = {
    PREPARACION: "Preparación",
    EJECUCION: "Ejecución",
    HYPERCARE: "Hypercare",
    CERRADO: "Cerrado",
    CANCELADO: "Cancelado",
}


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

TRANSFORMACION = "transformacion"
OPERACION = "operacion"
INNOVACION = "innovacion"
#: «Business as usual»: mantener las luces encendidas. Se queda en la sigla
#: porque es como lo dice quien lo pide; traducirlo a «operación continua» lo
#: haría indistinguible de `operacion`.
BAU = "bau"

TIPOS: tuple[str, ...] = (TRANSFORMACION, OPERACION, INNOVACION, BAU)

#: Los nombres en inglés que estuvieron en el enum de la API hasta US-202.
TIPOS_RENOMBRADOS: dict[str, str] = {
    "transformation": TRANSFORMACION,
    "operation": OPERACION,
    "innovation": INNOVACION,
}

ETIQUETAS_TIPO: dict[str, str] = {
    TRANSFORMACION: "Transformación",
    OPERACION: "Operación",
    INNOVACION: "Innovación",
    BAU: "BAU (operación continua)",
}


#: La misma fase, dicha desde la lección. Un proyecto **está** cerrado —es un
#: estado—; una lección se aprendió **en el cierre** —es una etapa—. Es la única
#: palabra que cambia, y se deriva del catálogo para que añadir una fase no
#: obligue a recordar esta segunda copia.
ETIQUETAS_FASE_LECCION: dict[str, str] = {**ETIQUETAS_FASE, CERRADO: "Cierre"}


def etiqueta_fase(valor: object) -> str:
    """La fase en palabras, o el valor crudo si no la conoce.

    Devuelve el crudo en vez de «—» o de lanzar: en un reporte, un valor que no
    está en el catálogo es un dato que hay que **ver** para poder corregirlo, no
    uno que convenga esconder.
    """
    clave = str(valor or "").strip().lower()
    if not clave:
        return "—"
    return ETIQUETAS_FASE.get(clave, str(valor))


def etiqueta_tipo(valor: object) -> str:
    """El tipo en palabras, o el valor crudo. Mismo criterio que las fases —y
    aquí importa más, porque los tipos libres de antes de US-202 salen así."""
    clave = str(valor or "").strip().lower()
    if not clave:
        return "—"
    return ETIQUETAS_TIPO.get(clave, str(valor))
