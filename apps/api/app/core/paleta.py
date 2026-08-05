"""ADR-023 — los colores de los gráficos, en un solo sitio.

Los informes se dibujan en el servidor (`services/reports/svg.py`,
`gantt_renderer.py`) y la web en el navegador, así que la misma paleta tiene que
existir en Python y en CSS. Este módulo es el origen; los tokens
`--chart-*` de `apps/web/app/globals.css` son su espejo, y
`tests/test_adr023_paleta_graficos.py` comprueba que no se separen.

**La regla, que es lo único que hay que recordar:** el semáforo se queda con el
arco cálido y el verde; los gráficos se quedan con el arco frío.

No es una preferencia estética con adorno. Antes, `#dc2626` marcaba «ruta
crítica» en el Gantt y `#16a34a` marcaba «lo real» en la curva-S, mientras el
semáforo de salud usaba esos mismos rojo y verde para «proyecto en problemas» y
«proyecto sano». El mismo color decía dos cosas en la misma página. Partiendo el
espectro, que una serie parezca un estado deja de ser posible por construcción.

**Cuatro ranuras, en orden fijo, sin reciclar.** El orden no es decorativo: es el
mecanismo de seguridad para daltonismo. Con estos mismos cuatro tonos en otro
orden, el teal y el rosa colapsan a ΔE 0,2 bajo deuteranopía —indistinguibles—;
en este orden el peor par adyacente queda en 13,3. Una quinta serie no se
inventa: se pliega en «Otros» o se parte en múltiplos pequeños.

Validado con el criterio de seis comprobaciones (banda de luminosidad, piso de
croma, separación CVD, piso de visión normal, contraste). Los pasos oscuros son
**propios**, no un volteo de los claros. Único aviso conocido: el morado oscuro
queda en 2,59:1 contra la superficie, lo que obliga a etiqueta visible o vista
de tabla — que es lo que los gráficos llevan de todos modos.
"""
from __future__ import annotations

#: Identidad: qué serie es cuál. Se asignan en orden y no se reciclan.
CATEGORICA_CLARO: tuple[str, ...] = ("#294c9f", "#008a9b", "#7c34a7", "#ca62a1")
CATEGORICA_OSCURO: tuple[str, ...] = ("#436ed1", "#00ab9e", "#8244ba", "#d368a2")

#: Secuencia: fase del proyecto, tamaño, tramo. Un solo tono —el azul de marca—
#: de claro a oscuro, porque cambiar el orden cambiaría el significado.
ORDINAL_CLARO: tuple[str, ...] = (
    "#c4d1ec", "#94abd8", "#6785c3", "#3c5fad", "#203d81",
)
ORDINAL_OSCURO: tuple[str, ...] = (
    "#2f4168", "#405c96", "#5277c7", "#6b95ee", "#9dbdff",
)

#: Lo que NO es una serie. Plan contra real, líneas de referencia, «sin dato».
NEUTRO = "#6F695A"
NEUTRO_SUAVE = "#A39C8B"

#: El acento de la plataforma. Es la serie por defecto cuando solo hay una, y el
#: lado «real» de la curva-S.
ACENTO = "#2A4DA0"

#: Reservados. Aquí solo para que el trinquete pueda comprobar que ninguna
#: ranura categórica los pisa — la salud los define en su propio sitio.
SEMAFORO = {"green": "#007A4C", "yellow": "#9F5900", "red": "#BD3528"}


def serie(indice: int, *, oscuro: bool = False) -> str:
    """Color de la serie `indice` (0-based), en el modo pedido.

    Lanza en vez de reciclar: una quinta serie con el color de la primera es un
    gráfico que miente sobre cuántas cosas distintas está mostrando. Quien
    llegue aquí tiene que decidir —«Otros», múltiplos pequeños— en vez de
    heredar una decisión que nadie tomó.
    """
    paleta = CATEGORICA_OSCURO if oscuro else CATEGORICA_CLARO
    if not 0 <= indice < len(paleta):
        raise ValueError(
            f"La paleta categórica tiene {len(paleta)} ranuras y se pidió la "
            f"{indice + 1}. No se recicla: pliega el resto en «Otros» o parte "
            f"el gráfico en múltiplos pequeños (ADR-023)."
        )
    return paleta[indice]


def escala(n: int, *, oscuro: bool = False) -> list[str]:
    """`n` pasos de la rampa ordinal, repartidos por los extremos.

    Con `n` menor que la rampa se toman pasos separados en vez de los primeros:
    tres tramos deben verse claro / medio / oscuro, no tres claros seguidos.
    """
    rampa = ORDINAL_OSCURO if oscuro else ORDINAL_CLARO
    if n <= 0:
        return []
    if n == 1:
        return [rampa[len(rampa) // 2]]
    paso = (len(rampa) - 1) / (n - 1)
    return [rampa[round(i * paso)] for i in range(n)]
