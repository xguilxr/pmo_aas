"""US-215 — El costo de una asignación, con la tarifa congelada.

El catálogo (`actors.fte_cost_rate`) guarda la tarifa **de hoy**. Si en marzo
alguien sube la tarifa de un consultor, el costo del trabajo de enero cambiaría
solo, y el gasto acumulado de un proyecto se reescribiría hacia atrás. Es el
mismo defecto que la línea base resuelve para las fechas (US-212): la historia
no se puede mover.

La tarifa se **congela en la participación** al crearla, y no se recalcula. Lo
que el catálogo cambie a partir de entonces afecta a las asignaciones nuevas y a
ninguna vieja.

## Por qué el periodo de la tarifa es un dato y no una convención

`fte_cost_rate` es un número sin unidad de tiempo. «Tarifa de un FTE» puede ser
por hora, por día o por mes, y las tres son ciframientos legítimos según el
contrato. Multiplicar por los días de la asignación asumiendo una de ellas da un
número que **parece** autoritativo y es arbitrario — el error más caro de este
módulo sería inventar la unidad.

Así que el periodo se declara junto a la tarifa (`cost_rate_period`), se congela
con ella, y sin él no hay costo: `None`, no un cero ni una estimación.

## Por qué no hay un total en una sola moneda

Es la regla de `dominio/moneda.py` y aquí aplica igual: dos personas facturadas
en monedas distintas no tienen un costo total. Convertir exigiría un tipo de
cambio con fecha, que es una estimación y no un dato. `costo_por_moneda`
devuelve un importe por moneda, nunca uno solo.

## Un mes son 21 días laborables, y eso es una convención declarada

No 30 ni 30,44. Es la que el propio plan ya usa —`ensure_duration_max_21` en
`services/plan_metadata.py` trata 21 días como el mes de trabajo— y usar dos
convenciones distintas para el mismo mes en el mismo producto es peor que
elegir la imperfecta. Vive como constante con nombre para que se pueda cambiar
en un sitio y para que nadie tenga que adivinar de dónde salió el 21.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.dominio.moneda import es_valida

#: La unidad de tiempo de una tarifa. Sin esto, `fte_cost_rate` es un número sin
#: significado y cualquier costo derivado de él es inventado.
Periodo = Literal["hora", "dia", "mes"]

PERIODOS: tuple[Periodo, ...] = ("hora", "dia", "mes")

ETIQUETAS: dict[str, str] = {
    "hora": "por hora",
    "dia": "por día laborable",
    "mes": "por mes",
}

#: Días laborables de un mes. Misma convención que `ensure_duration_max_21`.
DIAS_LABORABLES_POR_MES = 21

#: Horas de una jornada. Se declara para que la conversión hora→día no quede
#: escrita dentro de una fórmula (MCS DAT-04).
HORAS_POR_DIA = 8


def dias_laborables(desde: date, hasta: date) -> int:
    """Días de lunes a viernes entre las dos fechas, ambas incluidas.

    Inclusivas porque el resto del plan cuenta así (`compute_duration_days`), y
    una asignación de un solo día es un día de costo, no cero.

    No conoce los feriados. Es una imprecisión declarada: el calendario laboral
    por país o por inquilino es un frente propio, y descontar los feriados de
    México a un equipo en Polonia sería peor que no descontar ninguno.
    """
    if hasta < desde:
        return 0
    total = 0
    dia = desde
    while dia <= hasta:
        if dia.weekday() < 5:
            total += 1
        dia = date.fromordinal(dia.toordinal() + 1)
    return total


def tarifa_diaria(tarifa: Decimal, periodo: str) -> Decimal | None:
    """La tarifa llevada a día laborable, la unidad de cálculo de este módulo.

    Es la única frontera de conversión de tiempo del costo (MCS DAT-04): el resto
    del módulo trabaja en días y no vuelve a dividir por nada.

    Un periodo desconocido devuelve `None` en lugar de caer en un default. Un
    costo calculado con la unidad equivocada es un número creíble y falso, que es
    la peor clase de error que este módulo puede producir.
    """
    if periodo == "dia":
        return tarifa
    if periodo == "mes":
        return tarifa / Decimal(DIAS_LABORABLES_POR_MES)
    if periodo == "hora":
        return tarifa * Decimal(HORAS_POR_DIA)
    return None


def costo_de_asignacion(
    *,
    tarifa: Decimal | None,
    periodo: str | None,
    allocation_pct: Decimal | None,
    desde: date | None,
    hasta: date | None,
) -> Decimal | None:
    """Lo que cuesta una asignación, o `None` si falta cualquier dato.

    `None` y no cero. Una asignación sin tarifa congelada no cuesta cero: se
    desconoce su costo, y un cero se sumaría al total del proyecto haciéndolo
    parecer completo (MCS DAT-12). Los cinco datos hacen falta:

    - **tarifa** — sin ella no hay número.
    - **periodo** — sin él la tarifa no tiene unidad.
    - **allocation_pct** — sin él no se sabe qué fracción de la persona es. No se
      supone 100 %: la mayoría de las asignaciones compartidas no lo son, y
      suponerlo infla el costo de todo el portafolio.
    - **desde / hasta** — sin fechas no hay duración. Una asignación sin plazo
      cuenta como vigente para la *capacidad* (US-208), y ahí es correcto; para
      el costo no, porque habría que elegir arbitrariamente cuándo termina.
    """
    if tarifa is None or periodo is None or allocation_pct is None:
        return None
    if desde is None or hasta is None:
        return None
    diaria = tarifa_diaria(Decimal(tarifa), periodo)
    if diaria is None:
        return None
    dias = dias_laborables(desde, hasta)
    if dias == 0:
        return Decimal("0.00")
    bruto = diaria * Decimal(dias) * (Decimal(allocation_pct) / Decimal(100))
    return bruto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def costo_por_moneda(
    asignaciones: list[tuple[str | None, Decimal | None]],
) -> dict[str, Decimal]:
    """Suma los costos **por moneda**. Nunca devuelve un total único.

    Misma regla y misma razón que `moneda.agregar`: dos personas facturadas en
    monedas distintas no tienen un costo total, y escribirlo inventaría un
    número que no existe en ninguna parte. Un `None` no suma y tampoco cuenta
    como cero; una moneda cuyos costos son todos desconocidos no aparece.

    Una moneda inválida se descarta en vez de caer en la de por defecto. En
    `moneda.agregar` el default es correcto porque el importe existe y hay que
    rotularlo con algo; aquí el costo es **derivado**, y derivarlo con una
    moneda adivinada lo convierte en un dato sin procedencia.
    """
    por_moneda: dict[str, Decimal] = {}
    for codigo, costo in asignaciones:
        if costo is None or not es_valida(codigo):
            continue
        clave = str(codigo)
        por_moneda[clave] = por_moneda.get(clave, Decimal(0)) + costo
    return por_moneda


def sin_tarifa(asignaciones: list[tuple[str | None, Decimal | None]]) -> int:
    """Cuántas asignaciones quedaron sin costo calculable.

    Se devuelve junto al total porque un total sin este número miente por
    omisión: «$400.000 en recursos» con doce asignaciones sin tarifa es un
    presupuesto a medias presentado como completo. Es la misma pareja que
    `unquantified_resources` en la carga semanal (US-208).
    """
    return sum(1 for _, costo in asignaciones if costo is None)
