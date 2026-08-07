"""La moneda de un importe: del proyecto, con la del inquilino como preferida.

> **Decisión del owner, 2026-08-07 (BUG-092).** «Habrá una moneda preferida,
> pero la moneda irá sobre el proyecto y deben poder escoger la que necesite el
> proyecto. Debe reflejar la correspondiente.»

## Qué había antes

`tenant.settings.currency` ofrecía MXN, USD y EUR, y **el formulario que la
guardaba era el único sitio que la leía**. Las diez superficies que muestran
dinero traían `currency: "MXN"` escrito a mano, así que un inquilino en dólares
—el propio sembrado crea uno— veía sus importes **rotulados en pesos**. No es
que el número estuviera mal: es que la unidad era mentira, que en un importe es
lo mismo que estar mal.

Salió midiendo DAT-02, y DAT-01 lo dejó declarado con su disparador: «la unidad
canónica del importe pasa a ser la moneda del inquilino el día que llegue a la
presentación». El owner movió el grano un escalón más abajo, al proyecto, que es
donde de verdad vive un presupuesto.

## La parte que no es evidente: agregar

Un portafolio con un proyecto en pesos y otro en euros **no tiene un
presupuesto total**. Sumar 1.000 MXN y 1.000 EUR y escribir «2.000» es inventar
un número que no existe en ninguna parte, y es el error que este módulo existe
para hacer imposible: `agregar` devuelve **un importe por moneda**, nunca uno
solo.

Convertir tampoco es la salida: haría falta un tipo de cambio con fecha, y en
ese momento el número deja de ser un dato para ser una estimación — con todo lo
que eso arrastra (qué fuente, de qué día, quién la firma). Es un frente propio
y no se abre aquí.
"""
from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

#: Las tres que el formulario de ajustes ya ofrecía. Se declaran aquí para que
#: el desplegable y la validación del servidor no puedan divergir — que es
#: exactamente lo que pasó con la moneda y la presentación.
MONEDAS: tuple[str, ...] = ("MXN", "USD", "EUR")

#: Lo que se aplica cuando ni el proyecto ni el inquilino dicen nada. Es la que
#: el producto venía usando de facto, así que ningún importe existente cambia de
#: rótulo al desplegar esto.
POR_DEFECTO = "MXN"


def es_valida(codigo: str | None) -> bool:
    return codigo in MONEDAS


def resolver(del_proyecto: str | None, preferida: str | None) -> str:
    """La moneda que se le aplica a un importe, en orden de especificidad.

    Proyecto → preferida del inquilino → `POR_DEFECTO`. El nulo del proyecto
    significa «la que diga el inquilino», no «ninguna»: así, cambiar la
    preferida arrastra a los proyectos que no eligieron, que es lo que espera
    quien la cambia.

    Un código desconocido se ignora en lugar de propagarse. `settings` lo edita
    una persona desde un formulario, y un importe sin rótulo por una errata es
    peor que uno con el rótulo por defecto.
    """
    if es_valida(del_proyecto):
        return str(del_proyecto)
    if es_valida(preferida):
        return str(preferida)
    return POR_DEFECTO


def agregar(importes: Iterable[tuple[str, Decimal | None]]) -> dict[str, Decimal]:
    """Suma importes **por moneda**. Nunca devuelve un total único.

    La firma es la mitad del control: no hay forma de llamar a esto y obtener un
    número solo. Un portafolio con un proyecto en pesos y otro en euros no tiene
    un presupuesto total, y escribir «2.000» donde hay 1.000 MXN y 1.000 EUR es
    inventar un número que no existe.

    Los nulos no suman y tampoco cuentan como cero: un proyecto sin presupuesto
    cargado no es un proyecto de presupuesto cero (DAT-12). Una moneda cuyos
    importes son todos nulos **no aparece** en el resultado.
    """
    por_moneda: dict[str, Decimal] = {}
    for codigo, importe in importes:
        if importe is None:
            continue
        moneda = codigo if es_valida(codigo) else POR_DEFECTO
        por_moneda[moneda] = por_moneda.get(moneda, Decimal(0)) + Decimal(importe)
    return por_moneda


def unica(por_moneda: dict[str, Decimal]) -> str | None:
    """El código si todos los importes están en la misma moneda, o `None`.

    Sirve para decidir la presentación: con una sola se pinta un número; con
    varias hay que pintarlas todas, y con ninguna no hay nada que pintar. Los
    tres casos son distintos y el llamador tiene que verlos distintos.
    """
    return next(iter(por_moneda)) if len(por_moneda) == 1 else None
