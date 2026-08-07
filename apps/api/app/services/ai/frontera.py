"""CON-05 — lo que excede la competencia declarada se deriva, no se contesta.

> «El sistema DEBE derivar a persona profesional cualificada toda consulta que
> exceda la frontera de competencia declarada».

La frontera la declara [`docs/dominio/06-COMPETENCIA.md`](../../../../../docs/dominio/06-COMPETENCIA.md)
§3, y su §4 dejó escrito el estado: **no implementado**. En sus palabras, «nada
impide que alguien le pregunte al asistente si puede despedir a un colaborador
por bajo desempeño, y nada garantiza que la respuesta derive en vez de opinar».
Y nombró los tres pasos que faltaban:

1. Que la instrucción del asistente **declare la frontera** del documento.
2. Que ante una consulta fuera de alcance **derive explícitamente**.
3. Que la derivación esté en el conjunto de evaluación, «o no hay forma de
   saber si sigue funcionando tras cambiar el modelo».

Este módulo es la fuente de los tres.

## Por qué la comprobación no la hace el modelo

El paso 1 —decírselo en la instrucción— es necesario y **no es suficiente**, y
el propio documento lo dice: «una frontera que solo vive en el texto de un
prompt se erosiona con cada cambio de modelo y nadie se entera». Un prompt es
una petición, no una garantía; ninguna defensa de prompt sobrevive a un modelo
que decide otra cosa.

Por eso la derivación se aplica **después**, sobre la consulta de quien
pregunta, y no depende de que el modelo colabore: si la pregunta cruza la
frontera, el aviso se antepone a la respuesta pase lo que pase.

## Lo que este control NO consigue, dicho antes de que lo pregunten

Detecta por **señales léxicas**, así que tiene falsos negativos: una consulta
jurídica formulada sin ninguna de las palabras declaradas pasa de largo. No se
puede afirmar «detecta todas las consultas fuera de alcance» y no se afirma.

Lo que sí se afirma, y es lo que CON-05 pide de un sistema: cuando la consulta
cruza la frontera de forma reconocible, **la derivación ocurre por
construcción** y no por buena voluntad del modelo. Es la misma postura que
`ruta_interna_segura`: lista blanca de forma, y el residual escrito.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Exclusion:
    """Una fila de la tabla «fuera de competencia» de `06-COMPETENCIA.md` §3.

    `derivar_a` no tiene valor por defecto a propósito. Derivar sin decir a
    quién es la forma educada de no derivar: quien pregunta se queda igual, y
    el requisito pide «persona profesional cualificada», no «alguien».
    """

    titulo: str
    porque: str
    derivar_a: str
    senales: tuple[str, ...]


#: Las seis del documento, en su orden. **El documento manda**; esto lo refleja
#: para que el código pueda citarlo, y una prueba falla si se separan.
EXCLUSIONES: tuple[Exclusion, ...] = (
    Exclusion(
        titulo="Consejo jurídico o fiscal",
        porque="No es su materia y no hay jurisdicción declarada",
        derivar_a="un abogado o un contador con la jurisdicción que aplique",
        senales=(
            "legal",
            "juridic",
            "abogad",
            "demanda",
            "contrato laboral",
            "clausula",
            "fiscal",
            "impuesto",
            "sat ",
            "deduc",
            "factura fiscal",
        ),
    ),
    Exclusion(
        titulo="Decidir cancelar, aprobar o continuar un proyecto",
        porque=(
            "Es una decisión de gobierno. El producto informa; decide la "
            "persona"
        ),
        derivar_a="el comité o la persona con autoridad de gobierno del proyecto",
        senales=(
            "debo cancelar",
            "debería cancelar",
            "cancelo el proyecto",
            "conviene cancelar",
            "apruebo el proyecto",
            "debo aprobar",
            "debería aprobar",
            "hay que matar el proyecto",
            "seguimos o no",
            "vale la pena continuar",
        ),
    ),
    Exclusion(
        titulo="Certificar cumplimiento de marcos",
        porque="Usar su vocabulario no es certificar conformidad",
        derivar_a=(
            "un organismo certificador, o la persona responsable de calidad de "
            "la organización"
        ),
        senales=(
            "certifica",
            "certificacion",
            "somos compatibles con pmbok",
            "cumplimos pmbok",
            "cumplimos prince2",
            "cumplimos iso",
            "conformidad con iso",
            "acredita",
        ),
    ),
    Exclusion(
        titulo="Valorar el desempeño de personas",
        porque=(
            "Los datos de carga miden asignación, no rendimiento. Usarlos para "
            "evaluar personas es un uso que el producto no respalda"
        ),
        derivar_a="el área de personas de la organización",
        senales=(
            "despedir",
            "despido",
            "bajo desempeño",
            "mal desempeño",
            "evaluar a ",
            "evaluacion de desempeño",
            "quien rinde",
            "quien trabaja mejor",
            "es productivo",
            "amonestar",
            "ascender a ",
        ),
    ),
    Exclusion(
        titulo="Predecir resultados",
        porque="Lo que se muestra es cálculo sobre lo introducido, no pronóstico",
        derivar_a=(
            "quien dirige el proyecto, con los supuestos sobre la mesa: la "
            "proyección la firma una persona"
        ),
        senales=(
            "va a terminar",
            "vamos a terminar",
            "prediccion",
            "predice",
            "pronostico",
            "probabilidad de exito",
            "cuando terminara",
            "llegaremos a tiempo",
            "se va a retrasar",
        ),
    ),
    Exclusion(
        titulo="Sustituir criterio profesional de dirección de proyectos",
        porque="Es herramienta, no asesor",
        derivar_a="quien dirige el proyecto",
        senales=(
            "que debo hacer",
            "que deberia hacer",
            "que harias tu",
            "que me recomiendas",
            "dame tu opinion",
            "decide por mi",
        ),
    ),
)


def _plano(texto: str) -> str:
    """Minúsculas, sin tildes y con los espacios normalizados.

    Sin esto, «jurídico» y «juridico» serían consultas distintas y media
    frontera se cruzaría sin querer, escribiendo rápido y sin acentos — que es
    justo como se teclea en un widget de chat.
    """
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_tildes)


def fuera_de_alcance(consulta: str) -> Exclusion | None:
    """La exclusión que cruza la consulta, o `None`.

    Devuelve la **primera** en el orden del documento. Cuando una consulta toca
    dos —«¿puedo despedirlo legalmente?»—, ese orden decide, y es el del
    documento a propósito: así la respuesta no depende de cómo esté escrito el
    diccionario.
    """
    plano = _plano(consulta)
    for exclusion in EXCLUSIONES:
        # La señal se normaliza TAMBIÉN, y no es simetría estética: la primera
        # versión solo normalizaba la consulta, así que «bajo desempeño»,
        # «mal desempeño» y «evaluacion de desempeño» no podían casar nunca
        # —la consulta llegaba como «desempeno» y la señal seguía con la eñe—.
        # Tres señales muertas y ninguna forma de notarlo: la exclusión seguía
        # disparando por «despedir», que es otra señal de la misma fila.
        if any(_plano(senal) in plano for senal in exclusion.senales):
            return exclusion
    return None


def aviso_de_derivacion(exclusion: Exclusion) -> str:
    """El texto que se antepone. Dice qué, por qué y a quién."""
    return (
        f"⚠️ **Esto excede lo que esta herramienta cubre.** "
        f"{exclusion.titulo} queda fuera de su alcance: {exclusion.porque.lower()}. "
        f"Conviene consultarlo con {exclusion.derivar_a}.\n\n"
        f"Lo que sí puedo hacer es mostrarte la información del proyecto que "
        f"tenga registrada."
    )


def aplicar_frontera(mensaje: str, consulta: str) -> str:
    """Antepone la derivación si la consulta cruza la frontera.

    Se aplica sobre la respuesta ya formada y **no se le pide permiso al
    modelo**: si el modelo se saltó la instrucción y opinó igualmente, el aviso
    va delante de su opinión. Un control que depende de que el modelo coopere
    no es un control.
    """
    exclusion = fuera_de_alcance(consulta)
    if exclusion is None:
        return mensaje
    return f"{aviso_de_derivacion(exclusion)}\n\n---\n\n{mensaje}".strip()


def bloque_para_prompt() -> str:
    """La frontera, generada para la instrucción del asistente.

    Generada y no escrita por lo mismo que el corpus de CON-02: si se teclea,
    la instrucción puede acabar diciendo algo que el documento no diga.
    """
    lineas = [
        "FRONTERA DE COMPETENCIA (docs/dominio/06-COMPETENCIA.md §3).",
        "Estas consultas EXCEDEN lo que este producto cubre. Ante cualquiera de",
        "ellas NO opines ni recomiendes: di que excede el alcance y deriva a",
        "quien corresponde.",
    ]
    for e in EXCLUSIONES:
        lineas.append(f"- {e.titulo} — {e.porque}. Deriva a: {e.derivar_a}.")
    lineas.append(
        "Lo que sí haces: mostrar, estructurar y calcular sobre la información "
        "que el inquilino ya introdujo."
    )
    return "\n".join(lineas)
