"""CON-02 — el conocimiento del dominio, versionado, no dictado al modelo.

> «El conocimiento del dominio DEBE residir en artefactos versionados. NO DEBE
> implementarse **únicamente** mediante instrucciones de rol dirigidas a un
> modelo».

## Qué se midió y qué salió

`06-COMPETENCIA.md` §5 dejó escrito el trabajo: «comprobar que lo que se le
dice al modelo no contiene reglas de dominio que no existan en ningún otro
sitio». Contrastadas las cuatro instrucciones de sistema contra el glosario,
los modelos y los ADR, la mayor parte del texto es **formato** —qué claves
devolver, en qué orden, sin bloques de código— y eso no es conocimiento de
dominio: es contrato de salida.

Quedaron dos cosas que sí lo eran:

1. **La taxonomía RAID.** Vive en el código (`validator.ALLOWED_RAID_TYPES`,
   `minutes_formatter.RAID_TYPE_LABELS`), así que versionada estaba. Lo que
   **no** cuadraba era el glosario: su §3 definía riesgo, incidencia, acción y
   lección aprendida, y **no mencionaba la decisión**, que es una de las cuatro
   categorías que el producto implementa. El artefacto de dominio y la
   implementación decían cosas distintas.

2. **El mapa de señales.** «se acordó» → Decisión, «preocupación» → Riesgo.
   Eso es criterio de dominio puro —la parte que un director de proyecto
   discutiría—, y existía **solo dentro de la cadena del prompt**. Es
   exactamente el caso que el requisito nombra.

## Qué hace este módulo

Es la fuente de las dos cosas. El glosario §3 las declara para las personas;
esto las declara para el código, y `prompts.py` **ensambla** su instrucción a
partir de aquí en vez de llevarla escrita. Cambiar una señal es cambiar un dato
versionado con su historia en `git log`, no editar prosa dentro de una cadena
de 180 líneas.

Una prueba mantiene los tres unidos —glosario, este módulo y el validador—,
porque tres copias del mismo hecho divergen; ya divergieron una vez, y así es
como se descubrió.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoriaRaid:
    """Una de las cuatro categorías del RAID, con lo que la distingue.

    `senales` es criterio de dominio, no de formato: son las expresiones que en
    una sesión de proyecto indican que lo dicho pertenece a esta categoría.
    """

    letra: str
    nombre: str
    definicion: str
    senales: tuple[str, ...]


#: Las cuatro. El orden es el de `minutes_formatter.RAID_TYPE_ORDER`, que es el
#: que ve quien lee la minuta.
RAID: tuple[CategoriaRaid, ...] = (
    CategoriaRaid(
        letra="A",
        nombre="Acción",
        definicion=(
            "Tarea de respuesta con responsable y fecha comprometida. No es "
            "una tarea del cronograma: vive en el RAID."
        ),
        senales=(
            "X va a hacer Y",
            "se contactará",
            "se agendará",
            "tomar el",
            "lo tomamos",
            "agregar al backlog",
        ),
    ),
    CategoriaRaid(
        letra="R",
        nombre="Riesgo",
        definicion=(
            "Evento futuro e incierto que, de ocurrir, afecta un objetivo. "
            "Tiene probabilidad e impacto. Un riesgo materializado deja de ser "
            "riesgo y pasa a incidencia."
        ),
        senales=(
            "preocupación",
            "podría",
            "puede ser más costoso",
            "riesgo",
            "no alineado",
            "se podrían retrasar",
        ),
    ),
    CategoriaRaid(
        letra="D",
        nombre="Decisión",
        definicion=(
            "Elección tomada en la sesión que fija un curso de acción y cierra "
            "una alternativa. Lo que la distingue de la acción es que no queda "
            "trabajo por hacer: queda un rumbo elegido."
        ),
        senales=(
            "se acordó",
            "se decidió",
            "se confirma",
            "decidimos",
            "queda pendiente decisión",
            "definición final",
        ),
    ),
    CategoriaRaid(
        letra="I",
        nombre="Incidencia",
        definicion=(
            "Evento que ya ocurrió y afecta un objetivo. No tiene "
            "probabilidad: tiene impacto y responsable."
        ),
        senales=(
            "problema",
            "falta claridad",
            "no resuelto",
            "sigue abierto",
            "issue",
        ),
    ),
)

#: Lo que el RAID de una minuta **no** admite, y por qué. Va en la instrucción
#: porque sin decirlo el modelo las emite y el validador las tira en silencio —
#: y un descarte silencioso parece una minuta incompleta.
FUERA_DEL_RAID: tuple[tuple[str, str], ...] = (
    (
        "Lecciones aprendidas",
        "tienen registro propio (`lessons`) y se capturan durante el proyecto, "
        "no al vuelo en una sesión",
    ),
    (
        "Solicitudes de cambio",
        "tienen flujo de aprobación propio (`change_requests`); meterlas en el "
        "RAID las sacaría de él",
    ),
)


def bloque_raid() -> str:
    """El fragmento de instrucción que describe el RAID, generado desde arriba.

    Se genera y no se escribe para que la instrucción no pueda decir algo que
    el dominio no diga. Es la diferencia práctica que pide CON-02: editar una
    señal es cambiar un dato versionado, no prosa dentro de una cadena.
    """
    letras = ", ".join(f"{c.letra} ({c.nombre})" for c in RAID)
    lineas = [f"- Cada item es exclusivamente {letras}.", "- Qué es cada una:"]
    for c in RAID:
        lineas.append(f"  - {c.letra} ({c.nombre}): {c.definicion}")

    excluidas = " ni ".join(n for n, _ in FUERA_DEL_RAID)
    motivos = "; ".join(f"{n.lower()}: {porque}" for n, porque in FUERA_DEL_RAID)
    lineas.append(
        f"- **NO emitas {excluidas}** — si aparecen en el transcript, "
        f"descártalas silenciosamente ({motivos})."
    )

    lineas.append("- Señales del transcript que indican cada tipo:")
    for c in RAID:
        senales = ", ".join(f'"{s}"' for s in c.senales)
        lineas.append(f"  - {senales} → {c.letra} ({c.nombre}).")
    return "\n".join(lineas)
