"""US-217 — RACI: quién hace, quién responde, a quién se consulta y a quién se informa.

El artboard «Proyecto — Recursos» pide «RACI / stakeholders clave», marcado como
nuevo. Es la matriz clásica de asignación de responsabilidades, y su valor no
está en las cuatro letras: está en que **una sola persona sea la A** de cada
cosa. Un proyecto con dos «responsables últimos» no tiene ninguno.

## Por qué es un campo de la participación y no una tabla nueva

Una participación ya dice «esta persona está en este proyecto con este rol y
este % de FTE». El RACI dice, de esa misma participación, **de qué tipo** es la
responsabilidad. Una tabla aparte obligaría a mantener dos listas de las mismas
personas y a decidir qué hacer cuando una está en un sitio y no en el otro.

## Por qué la A es única y la R no

- **A (accountable)** — responde por el resultado. Es el único papel que no se
  puede repartir: si dos personas responden, ninguna lo hace. El sistema lo
  impide en la frontera.
- **R (responsible)** — hace el trabajo. Varias personas pueden hacer partes de
  lo mismo, y eso es normal.
- **C (consulted)** y **I (informed)** — se les pregunta, o se les cuenta.
  Cuantas más, mejor; no hay nada que limitar.

Se valida a nivel de **proyecto** y no de tarea porque las participaciones son
del proyecto. Un RACI por tarea es otra cosa y otra US.
"""
from __future__ import annotations

from typing import Literal

#: Las cuatro letras, en el orden en que se leen.
Papel = Literal["A", "R", "C", "I"]

PAPELES: tuple[Papel, ...] = ("A", "R", "C", "I")

ETIQUETAS: dict[str, str] = {
    "A": "Responsable último (A)",
    "R": "Ejecuta (R)",
    "C": "Consultado (C)",
    "I": "Informado (I)",
}

#: Qué significa cada letra, para la interfaz. Sin esto, «A» y «R» se confunden
#: en cada conversación: las dos palabras españolas empiezan por «responsable».
DESCRIPCIONES: dict[str, str] = {
    "A": "Responde por el resultado ante el sponsor. Solo puede haber una persona.",
    "R": "Hace el trabajo. Puede haber varias.",
    "C": "Se le pregunta antes de decidir.",
    "I": "Se le informa de lo decidido.",
}

#: El papel que no se puede repartir.
UNICO: Papel = "A"


def es_papel(valor: str | None) -> bool:
    return valor in PAPELES


def conflicto_de_unicidad(
    papeles_actuales: dict[str, str | None],
    *,
    participacion: str,
    nuevo: str | None,
) -> str | None:
    """El identificador de la participación que ya tiene la A, si hay conflicto.

    `papeles_actuales` es `participation_id → papel` del proyecto entero,
    **incluida** la que se está cambiando. Devuelve `None` si no hay conflicto.

    Se devuelve el identificador y no un booleano porque el mensaje de error
    tiene que poder decir **quién** la tiene: «Ana ya es la A» es accionable y
    «ya hay una A» obliga a ir a buscarla.

    Poner la A a quien ya la tiene no es conflicto: es idempotente. Y quitarla
    tampoco —dejar un proyecto sin A es un estado incompleto, no inválido: así
    es como está antes de que alguien lo asigne, y rechazarlo impediría corregir
    una A puesta a la persona equivocada.
    """
    if nuevo != UNICO:
        return None
    for otra, papel in papeles_actuales.items():
        if otra != participacion and papel == UNICO:
            return otra
    return None
