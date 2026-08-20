"""US-221 — El plan de suscripción: qué límites tiene un inquilino y cuánto usa.

Del artboard «Admin — Plan (suscripción)»: «Plan actual: Free / Pro /
Enterprise», «Límites y consumo (organizaciones 1/1 · proyectos 3/3 · usuarios ·
IA)», y una línea que manda sobre todo lo demás: **«Solo lectura — sin paywall ni
billing en esta fase»**.

## Lo que este módulo hace y lo que deliberadamente no

Contesta «¿cuánto de mi plan estoy usando?». **No bloquea nada.** Un límite
excedido se muestra y se sigue trabajando: el artboard lo dice, y convertirlo en
un bloqueo sería cambiar el producto por cuenta propia — un cliente al que le
crece la cartera se quedaría fuera de su propia plataforma un viernes por la
tarde.

Cuando el bloqueo llegue, este módulo ya tiene la respuesta y solo hará falta
decidir **qué** hacer con ella. Esa decisión no es técnica.

## Por qué los límites viven en el inquilino y no en el tier

Los tres nombres —`free`, `pro`, `enterprise`— salen del artboard aprobado. Los
**números** de cada uno no: son información comercial que no está en ningún
documento de este repositorio. Escribir «pro = 10 organizaciones» aquí sería
inventar el catálogo de precios en un módulo de dominio, y quedaría como si
alguien lo hubiera decidido.

Así que el tier es una **etiqueta** y los límites son **datos del inquilino**. El
día que exista un catálogo, se rellenan desde él y este módulo no cambia. La
diferencia práctica: hoy un inquilino en `pro` sin límites capturados muestra
«sin límite declarado», que es la verdad, en vez de un número inventado.

## Un límite ausente no es un límite de cero

Es MCS DAT-12 otra vez, y aquí importa más que en otros sitios: un cero diría
«no puedes crear ni una organización», que es lo contrario de «no hay tope». Los
dos estados se nombran distinto y se pintan distinto.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.unidades import razon_a_pct_piso

#: Los tres del artboard. Es una etiqueta comercial, no un conjunto de reglas:
#: las reglas son los límites, y esos van por inquilino.
Tier = Literal["free", "pro", "enterprise"]

TIERS: tuple[Tier, ...] = ("free", "pro", "enterprise")

ETIQUETAS: dict[str, str] = {
    "free": "Free",
    "pro": "Pro",
    "enterprise": "Enterprise",
}

#: El tier de quien no tiene ninguno declarado. `free` y no `enterprise` porque
#: equivocarse hacia abajo se ve —el inquilino pregunta— y equivocarse hacia
#: arriba no: nadie reporta que le sobran permisos.
TIER_POR_DEFECTO: Tier = "free"


@dataclass(frozen=True)
class Recurso:
    """Algo que se cuenta contra un límite."""

    clave: str
    etiqueta: str
    #: Qué se ve al pasar del tope. Sin esto, «excedido» no dice qué hacer.
    consecuencia: str


#: Los cuatro que el artboard enumera. El orden es el de la pantalla.
RECURSOS: tuple[Recurso, ...] = (
    Recurso(
        "organizations",
        "Organizaciones",
        "Las que ya existen siguen funcionando; crear otra queda fuera del plan.",
    ),
    Recurso(
        "projects",
        "Proyectos",
        "Los que ya existen siguen funcionando; crear otro queda fuera del plan.",
    ),
    Recurso(
        "users",
        "Usuarios activos",
        "Las cuentas activas cuentan; desactivar una libera su lugar.",
    ),
    Recurso(
        "ai_jobs_month",
        "Trabajos de IA este mes",
        "Se cuenta por mes calendario y vuelve a cero el día 1.",
    ),
)

CLAVES: tuple[str, ...] = tuple(r.clave for r in RECURSOS)

#: Qué le pasa a un recurso frente a su límite.
Estado = Literal["sin_limite", "dentro", "al_limite", "excedido"]

ETIQUETAS_DE_ESTADO: dict[str, str] = {
    "sin_limite": "Sin límite declarado",
    "dentro": "Dentro del plan",
    "al_limite": "En el tope",
    "excedido": "Por encima del plan",
}


@dataclass(frozen=True)
class Uso:
    clave: str
    etiqueta: str
    consumo: int
    #: `None` = no hay tope declarado. **No es cero** (MCS DAT-12): un cero diría
    #: «no puedes crear ninguna», que es lo contrario de «no hay tope».
    limite: int | None
    estado: Estado
    #: Porcentaje del tope, o `None` sin tope. No se calcula contra un tope
    #: inventado: sin denominador no hay porcentaje.
    porcentaje: int | None


def evaluar_uno(clave: str, etiqueta: str, consumo: int, limite: int | None) -> Uso:
    if limite is None:
        return Uso(clave, etiqueta, consumo, None, "sin_limite", None)
    # Un tope de cero es un tope válido —«este plan no incluye esto»— y hay que
    # tratarlo sin dividir por él.
    if limite <= 0:
        estado: Estado = "excedido" if consumo > 0 else "al_limite"
        return Uso(clave, etiqueta, consumo, limite, estado, 100 if consumo else 0)
    if consumo > limite:
        estado = "excedido"
    elif consumo == limite:
        estado = "al_limite"
    else:
        estado = "dentro"
    # `razon_a_pct_piso` y no una división en línea (MCS DAT-04). Trunca hacia
    # abajo a propósito: 99,6 % del tope no debe leerse «100 %», que es la
    # diferencia entre «te queda margen» y «ya llegaste». El caso de denominador
    # cero no llega aquí —la rama de arriba lo atajó—, así que su regla propia
    # (devolver 100) no se aplica por accidente.
    return Uso(clave, etiqueta, consumo, limite, estado, razon_a_pct_piso(consumo, limite))


def evaluar(
    consumo: dict[str, int], limites: dict[str, int | None]
) -> list[Uso]:
    """Un `Uso` por recurso declarado, en el orden de la pantalla.

    Se recorren los `RECURSOS` y no las claves del consumo: así, un recurso nuevo
    aparece en la pantalla en cuanto se declara aquí, y un límite guardado con una
    clave que ya no existe se ignora en vez de pintar una fila sin nombre.
    """
    return [
        evaluar_uno(r.clave, r.etiqueta, consumo.get(r.clave, 0), limites.get(r.clave))
        for r in RECURSOS
    ]


def hay_algo_fuera(usos: list[Uso]) -> bool:
    """Si algún recurso pasó su tope.

    Se devuelve aparte del detalle porque es lo que decide si la pantalla lleva un
    aviso arriba. Recorrer cuatro filas para descubrirlo es trabajo que quien
    consume no tiene por qué hacer.
    """
    return any(u.estado == "excedido" for u in usos)


def normalizar_tier(crudo: object) -> Tier:
    """El tier guardado, o el por defecto si no es uno de los tres.

    Un valor desconocido cae al default en vez de propagarse: `settings` lo edita
    una persona, y una errata no debe dejar la pantalla del plan sin nada que
    decir. Es el mismo criterio que `moneda.resolver` con un código inválido.
    """
    return crudo if crudo in TIERS else TIER_POR_DEFECTO  # type: ignore[return-value]


def normalizar_limites(crudo: object) -> dict[str, int | None]:
    """Los límites guardados, quedándose solo con lo utilizable.

    Un valor no entero o negativo se descarta —queda como «sin límite declarado»,
    que es la verdad: no hay un tope legible— en vez de caer a cero, que diría
    «ninguno permitido». Las claves desconocidas se ignoran.
    """
    salida: dict[str, int | None] = {}
    if not isinstance(crudo, dict):
        return salida
    for clave in CLAVES:
        valor = crudo.get(clave)
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            continue
        entero = int(valor)
        if entero < 0:
            continue
        salida[clave] = entero
    return salida
