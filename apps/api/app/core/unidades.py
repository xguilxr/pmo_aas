"""DAT-04 y DAT-08 — las conversiones de unidad, con nombre y en un solo sitio.

> «La conversión de unidades DEBE ocurrir únicamente en fronteras explícitas y
> nombradas, nunca en la lógica de dominio.»

La auditoría del 2026-08-03 contó **6 sitios**; midiendo contra el árbol salen
**26**, que es la cifra que `DAT-08` ya anotaba como «constantes de conversión
en línea». Tres familias:

| Familia | Cómo estaba escrita | Cuántas |
|---|---|---|
| Fracción ↔ porcentaje | `* 100` · `/ 100` | 14 |
| Bytes ↔ mebibytes | `1024 * 1024` | 7 |
| Segundos → milisegundos | `* 1000` | 9 |

## Por qué importa más de lo que parece

Un `* 100` suelto no dice **de qué a qué**. En `project_health.py` conviven un
`ratio * 100` que produce porcentaje y un `progress / 100` que consume
porcentaje para producir fracción, a nueve líneas de distancia. Leerlo exige
reconstruir en la cabeza qué unidad lleva cada variable, y equivocarse no
produce un error: produce un número plausible.

Ya pasó en este producto. `xlsx_task_parser` multiplica por 100 porque Excel
guarda los porcentajes como fracción, y esa regla vivía solo en un comentario.

## Lo que este módulo NO es

**No es un sistema de tipos de magnitud.** Eso es `DAT-07` («sin tipos propios
para magnitudes»), sigue abierto, y es otra conversación: exige que
`porcentaje` y `fracción` sean tipos distintos que el verificador no deje
mezclar. Aquí solo se nombra la conversión, que es lo que `DAT-04` pide.

La diferencia práctica: esto impide escribir la conversión mal; no impide pasar
un porcentaje donde se espera una fracción.
"""
from __future__ import annotations

from decimal import Decimal

#: Un mebibyte. `MB` en la interfaz de usuario, `MiB` en la realidad — los
#: límites de subida se escribieron con 1024 desde el principio y renombrarlos
#: cambiaría el límite anunciado al cliente. Se nombra correcto aquí y se
#: mantiene el texto de cara al usuario.
BYTES_POR_MEBIBYTE = 1024 * 1024


def mebibytes(cantidad: float) -> int:
    """Bytes que ocupan `cantidad` mebibytes. Para declarar límites de tamaño."""
    return int(cantidad * BYTES_POR_MEBIBYTE)


def a_mebibytes(bytes_: int) -> float:
    """Mebibytes que ocupan `bytes_`. Para mostrárselo a una persona."""
    return bytes_ / BYTES_POR_MEBIBYTE


def fraccion_a_pct(fraccion: float, *, decimales: int = 1) -> float:
    """0,42 → 42,0. La dirección que produce el número que se presenta."""
    return round(fraccion * 100, decimales)


def pct_a_fraccion(pct: float) -> float:
    """42 → 0,42. La dirección que consume un porcentaje para volver a operar."""
    return pct / 100


def pct_a_fte(pct_acumulado: float, *, decimales: int = 1) -> float:
    """3860 → 38,6. Porcentajes de asignación sumados, en personas equivalentes.

    Es la misma aritmética que `pct_a_fraccion` y se nombra aparte porque dice
    otra cosa. Ahí «0,42» es una fracción de uno; aquí «38,6» son treinta y
    ocho personas y media, y el número se **presenta** con esa unidad
    («38,6 / 35,0 FTE»).

    Existe porque la alternativa era un `/ 100` suelto en el cálculo de
    capacidad, y un `/ 100` suelto no dice de qué a qué. En `capacity.py`
    conviven porcentajes por recurso, porcentajes sumados y FTE: leer cuál es
    cuál sin el nombre exige reconstruirlo, y equivocarse no da un error, da un
    número plausible — que es justo lo que DAT-04 existe para impedir.
    """
    return round(pct_a_fraccion(pct_acumulado), decimales)


def razon_a_pct(numerador: float, denominador: float, *, decimales: int = 1) -> float:
    """`numerador/denominador` en porcentaje, y **0,0 si el denominador es cero**.

    La guarda va aquí y no en cada sitio porque estaba en cada sitio: nueve
    variantes de `round(x * 100 / y, 1) if y else 0.0`, y basta que una se
    escriba sin el `if` para que un proyecto sin tareas tire una división por
    cero en el cálculo de salud.

    Cero **no** es lo mismo que «sin dato», y eso lo trata `DAT-12`: aquí el
    denominador cero significa que no hay nada que medir, y quien llame decide
    si eso se presenta como 0 % o como «—».
    """
    if not denominador:
        return 0.0
    return round(numerador * 100 / denominador, decimales)


def razon_a_pct_piso(numerador: int, denominador: int) -> int:
    """`numerador/denominador` en porcentaje entero, **truncando hacia abajo**.

    Existe aparte de `razon_a_pct` porque el redondeo no es un detalle de
    formato: es la diferencia entre decir «91 %» y «90 %» de un proyecto al que
    le falta un dato de once. Redondear hacia arriba insinúa que casi no le
    falta nada, y quien lea la columna no va a abrirla.

    Con `denominador` cero devuelve 100: la razón es que la única fuente de un
    cero ahí es «no hay requisitos que cumplir», y no cumplir ninguno de cero
    requisitos es estar completo. La otra opción —cero por ciento— diría que
    falta todo cuando no falta nada.
    """
    if not denominador:
        return 100
    return numerador * 100 // denominador


def razon_a_pct_decimal(numerador: Decimal, denominador: Decimal) -> Decimal:
    """La misma razón, en `Decimal`, para las cifras que van a informes.

    Existe aparte y no como un `isinstance` dentro de la anterior porque la
    diferencia no es de tipo, es de contrato: `IA-05` exige que las cifras de
    los informes ejecutivos no pasen por coma flotante. Fundirlas invitaría a
    llamar a la de `float` desde una ruta monetaria sin que nada avisara.
    """
    if not denominador:
        return Decimal("0.0")
    return (numerador / denominador * 100).quantize(Decimal("0.1"))


def segundos_a_ms(segundos: float) -> int:
    """Segundos → milisegundos, que es como se guardan las latencias.

    Entera a propósito: `duration_ms` es `INTEGER` en el modelo, y dejar que
    cada sitio decidiera si redondea o trunca producía latencias que no suman.
    """
    return int(segundos * 1000)
