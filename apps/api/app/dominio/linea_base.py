"""US-212 — Línea base del plan: contra qué se mide una desviación.

Es la brecha B-1 del diagnóstico y la decisión D-6 del glosario. Sin línea base,
tres palabras que la plataforma ya usa no tienen referente: «desviación»,
«retraso» y «sobrecosto». Un Gantt que se mueve solo no está atrasado respecto de
nada — está atrasado respecto de lo que alguien prometió, y eso hay que haberlo
guardado.

## Qué es una línea base aquí

Una **foto fechada** del plan: por cada tarea, su inicio, su fin y si era hito, en
el momento de capturarla. No es una versión editable del plan ni una rama: se
captura, se compara y se archiva. Editar una línea base es lo mismo que
falsificar la promesa contra la que se mide.

## Por qué se emparejan las tareas por identificador y no por código EDT

El código EDT (`1.2.3`) parece la clave natural, y no lo es: el propio plan tiene
un botón que lo renumera (`POST /projects/{id}/tasks/renumber-wbs`). Emparejar por
código haría que una renumeración —que no mueve ninguna fecha— apareciera como
«todas las tareas retiradas y otras tantas nuevas». Se empareja por `task_id`, que
no cambia nunca, y el código se guarda solo para poder leer la fila.

## Por qué la deriva puede no existir

Una tarea sin fecha de fin no tiene deriva. Decir que su deriva es 0 la contaría
como «en fecha», que es la lectura opuesta a la verdad: no se sabe (MCS DAT-12,
la ausencia no es un cero). La deriva es `None` y la interfaz tiene que decir
«sin fecha», no «0 días».

## Las cuatro cosas que pueden pasarle a una tarea

- **Estaba y sigue** — hay deriva, positiva (se corrió), negativa (se adelantó) o
  cero.
- **No estaba y está** (`nueva`) — alcance agregado después de la promesa. No es
  un atraso, y mezclarlo con los atrasos es cómo se pierde la conversación sobre
  el alcance: un proyecto puede tener cero tareas atrasadas y treinta nuevas.
- **Estaba y ya no** (`retirada`) — alcance quitado. Tampoco es un adelanto.
- La **deriva real** de una tarea cerrada (`closed_at` contra el fin de la base)
  es distinta de la deriva del plan: el plan se puede reescribir para que la
  desviación desaparezca, la fecha de cierre no. Se devuelven las dos.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

#: Qué le pasó a una tarea entre la línea base y el plan de hoy.
Estado = Literal["sin_cambio", "corrida", "adelantada", "nueva", "retirada"]

ETIQUETAS: dict[str, str] = {
    "sin_cambio": "En fecha base",
    "corrida": "Corrida",
    "adelantada": "Adelantada",
    "nueva": "Nueva (no estaba en la base)",
    "retirada": "Retirada del plan",
}

#: El orden en que se leen: primero lo que duele.
ORDEN: tuple[str, ...] = ("corrida", "nueva", "retirada", "adelantada", "sin_cambio")


@dataclass(frozen=True)
class Fila:
    """Una tarea, en la línea base o en el plan vivo. La misma forma en las dos.

    Que sea la misma forma es lo que permite compararlas sin traducir: la
    captura copia el plan tal cual, y la comparación no tiene que saber de qué
    lado vino cada fila.
    """

    task_id: str
    wbs_code: str | None
    nombre: str
    inicio: date | None
    fin: date | None
    es_hito: bool = False
    #: Solo en el plan vivo. La base no guarda avance: es una promesa de fechas,
    #: no una foto del progreso, y comparar el avance de hoy con el de la captura
    #: contestaría una pregunta que nadie hace.
    progreso: int | None = None
    cerrada_el: date | None = None


@dataclass(frozen=True)
class Comparacion:
    task_id: str
    wbs_code: str | None
    nombre: str
    base_inicio: date | None
    base_fin: date | None
    plan_inicio: date | None
    plan_fin: date | None
    #: Días entre el fin del plan y el fin de la base. Positivo = se corrió.
    #: `None` cuando falta cualquiera de las dos fechas.
    deriva_dias: int | None
    #: Días entre el cierre real y el fin de la base. Lo que ya no se puede
    #: reescribir. `None` si no está cerrada o la base no tenía fin.
    deriva_real_dias: int | None
    progreso: int | None
    es_hito: bool
    estado: Estado


@dataclass(frozen=True)
class Resumen:
    total_base: int
    total_plan: int
    corridas: int
    adelantadas: int
    sin_cambio: int
    nuevas: int
    retiradas: int
    #: Deriva del proyecto: el fin más tardío del plan contra el de la base.
    #: `None` si alguno de los dos lados no tiene ninguna fecha de fin.
    deriva_proyecto_dias: int | None
    fin_base: date | None
    fin_plan: date | None
    #: La deriva más grande de una sola tarea, y de cuál. Se devuelve porque el
    #: promedio de las derivas no sirve para decidir nada: veinte tareas en fecha
    #: y una corrida cuatro meses dan un promedio tranquilizador.
    peor_deriva_dias: int | None
    peor_deriva_task_id: str | None


def _deriva(base_fin: date | None, otro_fin: date | None) -> int | None:
    if base_fin is None or otro_fin is None:
        return None
    return (otro_fin - base_fin).days


def _estado(deriva: int | None) -> Estado:
    # Sin deriva calculable el estado es «sin_cambio» y no «corrida»: no se sabe
    # que se movió, y afirmar que se movió es peor que no afirmar nada.
    if deriva is None or deriva == 0:
        return "sin_cambio"
    return "corrida" if deriva > 0 else "adelantada"


def comparar(base: Sequence[Fila], plan: Sequence[Fila]) -> list[Comparacion]:
    """Empareja las dos fotos por `task_id` y describe cada diferencia.

    Devuelve una fila por tarea que aparezca en cualquiera de los dos lados. El
    orden es el del plan vivo primero —es el que el usuario está mirando— y las
    retiradas al final, porque ya no tienen sitio en la tabla.
    """
    por_id_base = {f.task_id: f for f in base}
    salida: list[Comparacion] = []

    for viva in plan:
        b = por_id_base.get(viva.task_id)
        if b is None:
            salida.append(
                Comparacion(
                    task_id=viva.task_id,
                    wbs_code=viva.wbs_code,
                    nombre=viva.nombre,
                    base_inicio=None,
                    base_fin=None,
                    plan_inicio=viva.inicio,
                    plan_fin=viva.fin,
                    deriva_dias=None,
                    deriva_real_dias=None,
                    progreso=viva.progreso,
                    es_hito=viva.es_hito,
                    estado="nueva",
                )
            )
            continue
        deriva = _deriva(b.fin, viva.fin)
        salida.append(
            Comparacion(
                task_id=viva.task_id,
                wbs_code=viva.wbs_code,
                nombre=viva.nombre,
                base_inicio=b.inicio,
                base_fin=b.fin,
                plan_inicio=viva.inicio,
                plan_fin=viva.fin,
                deriva_dias=deriva,
                deriva_real_dias=_deriva(b.fin, viva.cerrada_el),
                progreso=viva.progreso,
                es_hito=viva.es_hito,
                estado=_estado(deriva),
            )
        )

    vivos = {f.task_id for f in plan}
    for b in base:
        if b.task_id in vivos:
            continue
        salida.append(
            Comparacion(
                task_id=b.task_id,
                # El nombre y el código son los de la captura: la tarea ya no
                # existe, y esta fila es lo único que queda de ella.
                wbs_code=b.wbs_code,
                nombre=b.nombre,
                base_inicio=b.inicio,
                base_fin=b.fin,
                plan_inicio=None,
                plan_fin=None,
                deriva_dias=None,
                deriva_real_dias=None,
                progreso=None,
                es_hito=b.es_hito,
                estado="retirada",
            )
        )
    return salida


def resumir(base: Sequence[Fila], plan: Sequence[Fila], comparaciones: Sequence[Comparacion]) -> Resumen:
    """Los totales que van arriba de la tabla."""
    fines_base = [f.fin for f in base if f.fin is not None]
    fines_plan = [f.fin for f in plan if f.fin is not None]
    fin_base = max(fines_base) if fines_base else None
    fin_plan = max(fines_plan) if fines_plan else None

    corridas_reales = [c for c in comparaciones if (c.deriva_dias or 0) > 0]
    # Sin ninguna tarea corrida no hay «peor»: devolver la menos adelantada bajo
    # ese nombre haría leer un adelanto como un atraso.
    peor = max(corridas_reales, key=lambda c: c.deriva_dias or 0) if corridas_reales else None

    def cuantas(estado: str) -> int:
        return sum(1 for c in comparaciones if c.estado == estado)

    return Resumen(
        total_base=len(base),
        total_plan=len(plan),
        corridas=cuantas("corrida"),
        adelantadas=cuantas("adelantada"),
        sin_cambio=cuantas("sin_cambio"),
        nuevas=cuantas("nueva"),
        retiradas=cuantas("retirada"),
        deriva_proyecto_dias=_deriva(fin_base, fin_plan),
        fin_base=fin_base,
        fin_plan=fin_plan,
        peor_deriva_dias=peor.deriva_dias if peor else None,
        peor_deriva_task_id=peor.task_id if peor else None,
    )
