"""US-211 — Si un proyecto está reportado al día, y cuál es su próximo hito.

Dos columnas del artboard «Portafolio — Vista maestra»: «Próx. hito» («UAT
integral · 28 ago») y «Reporte» («al día» / «por vencer» / «vencido»). El
Portfolio Board del artboard «Boards» agrupa por la segunda.

## Por qué el estatus de reporte es un dato y no un adjetivo

«¿Está reportado?» es la primera pregunta de una reunión de portafolio y la que
nadie puede contestar mirando la lista de reportes: hay que abrir cada proyecto,
ver la fecha del último y compararla con la cadencia acordada. Veintitrés veces.

Convertirlo en un valor consultable es lo que permite ordenar la tabla por él y
agrupar el board con él. Y hace visible el caso que se pierde: el proyecto que
**nunca** se reportó, que no está «vencido» —no venció nada— sino sin empezar.

## MCS DEV-02 — aquí no entra la base de datos

Recibe fechas y devuelve el veredicto. Quién busca el último reporte y el
próximo hito es la capa de datos.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

#: Los cuatro estados. `sin_reporte` no es «vencido»: un proyecto que nunca se
#: reportó no incumplió una fecha, es que no ha empezado a reportar. Meterlos en
#: el mismo cubo esconde el caso que más hay que mirar en un onboarding.
EstadoDeReporte = Literal["al_dia", "por_vencer", "vencido", "sin_reporte"]

ETIQUETAS: dict[str, str] = {
    "al_dia": "al día",
    "por_vencer": "por vencer",
    "vencido": "vencido",
    "sin_reporte": "sin reporte",
}

#: Cada cuántos días se espera un reporte, si el inquilino no dice otra cosa.
#: Catorce porque los mockups piden cadencia **bi-semanal**; US-213 la vuelve
#: configurable de verdad y esto será su default.
CADENCIA_POR_DEFECTO_DIAS = 14


@dataclass(frozen=True)
class Reporte:
    estado: EstadoDeReporte
    #: Cuándo vence el siguiente, o `None` si nunca se reportó: sin un último
    #: no hay de dónde contar. Inventar «hoy + cadencia» daría una fecha que
    #: nadie acordó.
    vence: date | None
    #: Días de retraso. Positivo solo cuando está vencido; nunca negativo, que
    #: se leería como «adelantado» y reportar antes no adelanta nada.
    dias_de_retraso: int

    @property
    def etiqueta(self) -> str:
        return ETIQUETAS[self.estado]


def _ventana_de_aviso(cadencia_dias: int) -> int:
    """Cuántos días antes del vencimiento se avisa.

    Un quinto del periodo, mínimo uno. Se deriva de la cadencia y no es un
    número fijo porque «tres días» significa cosas distintas en un ciclo
    semanal y en uno mensual: en el semanal ya es casi la mitad del periodo, y
    la mitad de los proyectos saldrían «por vencer» permanentemente.
    """
    return max(1, cadencia_dias // 5)


def evaluar_reporte(
    ultimo: date | None,
    *,
    hoy: date,
    cadencia_dias: int = CADENCIA_POR_DEFECTO_DIAS,
) -> Reporte:
    """El estatus de reporte de un proyecto.

    `cadencia_dias <= 0` se trata como la cadencia por defecto: una cadencia de
    cero días haría que todo esté vencido siempre, lo que no es una
    configuración, es un error de captura.
    """
    if cadencia_dias <= 0:
        cadencia_dias = CADENCIA_POR_DEFECTO_DIAS
    if ultimo is None:
        return Reporte("sin_reporte", None, 0)

    vence = date.fromordinal(ultimo.toordinal() + cadencia_dias)
    if hoy > vence:
        return Reporte("vencido", vence, (hoy - vence).days)
    if (vence - hoy).days <= _ventana_de_aviso(cadencia_dias):
        return Reporte("por_vencer", vence, 0)
    return Reporte("al_dia", vence, 0)


@dataclass(frozen=True)
class Hito:
    """El próximo hito del proyecto: qué y cuándo."""

    nombre: str
    fecha: date
    #: `True` si la fecha ya pasó y el hito sigue abierto. La columna lo pinta
    #: distinto: «UAT · 28 ago» en un proyecto donde hoy es 5 de septiembre no
    #: es información de calendario, es una alerta.
    vencido: bool


def proximo_hito(
    hitos: list[tuple[str, date]], *, hoy: date
) -> Hito | None:
    """El hito abierto que toca primero.

    Recibe `(nombre, fecha)` de los hitos **no completados** y devuelve el más
    próximo. Si el primero ya pasó, se devuelve ese y marcado como vencido: la
    alternativa —saltar a la siguiente fecha futura— esconde el hito que se
    incumplió, que es justo el que hay que mirar.

    Empate de fechas: gana el nombre alfabéticamente, para que dos cargas
    seguidas no devuelvan hitos distintos. Una columna que cambia sola entre dos
    refrescos parece un dato que se mueve.
    """
    if not hitos:
        return None
    nombre, fecha = min(hitos, key=lambda h: (h[1], h[0]))
    return Hito(nombre=nombre, fecha=fecha, vencido=fecha < hoy)
