"""DAT-04 — las conversiones de unidad tienen nombre y viven en un solo sitio.

> «La conversión de unidades DEBE ocurrir únicamente en fronteras explícitas y
> nombradas, nunca en la lógica de dominio.»

La auditoría contó **6 sitios**. Midiendo contra el árbol salían **26**, que es
la cifra que `DAT-08` ya anotaba por su cuenta como «constantes de conversión en
línea»: los dos requisitos estaban mirando el mismo hecho desde lados distintos.
Tres familias — fracción↔porcentaje, bytes↔mebibytes y segundos→milisegundos.

## Por qué no es cosmético

Un `* 100` suelto no dice **de qué a qué**. En `project_health.py` convivían un
`ratio * 100` que produce porcentaje y un `progress / 100` que consume
porcentaje, a nueve líneas de distancia. Equivocarse ahí no da un error: da un
número plausible que va a un informe ejecutivo.

Y había una guarda repetida nueve veces: `round(x * 100 / y, 1) if y else 0.0`.
Nueve copias de la misma protección contra la división por cero, y basta que la
décima se escriba sin el `if` para que un proyecto sin tareas tumbe el cálculo
de salud. Ahora la guarda vive en `razon_a_pct` y no se puede olvidar.

## Lo que el trinquete mira

El **árbol**, no una lista de sitios. Una prueba que enumerara los 26 quedaría
verde el día que aparezca el 27, que es exactamente cómo llegaron a ser 26.

Lo que **no** cubre: que alguien pase un porcentaje donde se espera una
fracción. Eso pide tipos propios de magnitud y es `DAT-07`, que sigue abierto.
Se dice para que sea trabajo pendiente y no un descuido.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.unidades import (
    BYTES_POR_MEBIBYTE,
    a_mebibytes,
    fraccion_a_pct,
    mebibytes,
    pct_a_fraccion,
    razon_a_pct,
    razon_a_pct_decimal,
    segundos_a_ms,
)

RAIZ_API = Path(__file__).resolve().parents[1]
UNIDADES = RAIZ_API / "app" / "core" / "unidades.py"

#: Las tres formas en que estaban escritas. `100` con multiplicación o
#: división, el mebibyte, y el millar de los milisegundos.
CONVERSIONES = re.compile(
    r"""
    (?:\*|/)\s*100(?:\.0)?\b        # fracción ↔ porcentaje
  | \b100\s*/                       # ídem, con el 100 delante
  | \b1024\s*\*\s*1024\b            # bytes ↔ mebibytes
  | (?:\*|/)\s*1000\b               # segundos ↔ milisegundos
""",
    re.X,
)


def _sin_comentarios(codigo: str) -> str:
    """Explicar una conversión no es hacerla.

    El módulo de fronteras documenta `0,42 → 42,0` en sus docstrings, y varios
    comentarios del dominio explican por qué la unidad es la que es. Contarlos
    como infracción empuja a borrar la explicación, que es el incentivo
    contrario al que interesa.
    """
    sin_docstrings = re.sub(r'"""(?:.|\n)*?"""|\'\'\'(?:.|\n)*?\'\'\'', "", codigo)
    return re.sub(r"#[^\n]*", "", sin_docstrings)


def test_ninguna_conversion_quedo_suelta_en_el_codigo() -> None:
    """Mira el árbol entero, que es lo que distingue esto de un `sed`."""
    culpables = []
    for archivo in sorted((RAIZ_API / "app").rglob("*.py")):
        if archivo == UNIDADES:
            continue  # es la frontera: aquí es donde deben estar
        cuerpo = _sin_comentarios(archivo.read_text(encoding="utf-8"))
        for n, linea in enumerate(cuerpo.splitlines(), 1):
            if CONVERSIONES.search(linea):
                culpables.append(f"{archivo.relative_to(RAIZ_API)}:{n}: {linea.strip()[:80]}")
    assert not culpables, (
        "Conversión de unidad escrita en línea. Las fronteras nombradas están "
        "en `app/core/unidades.py`; si hace falta una nueva, se añade ahí.\n"
        + "\n".join(culpables)
    )


def test_la_frontera_esta_en_un_solo_modulo() -> None:
    """Dos módulos de conversión son dos vocabularios de conversión.

    Es el mismo fallo que produjo cinco paletas de salud, aplicado a la
    aritmética.
    """
    otros = [
        x.relative_to(RAIZ_API).as_posix()
        for x in (RAIZ_API / "app").rglob("*.py")
        if x != UNIDADES and re.search(r"unidad|conversion|unit_conv", x.name)
    ]
    assert not otros, f"Aparecieron más módulos de conversión: {otros}"


@pytest.mark.parametrize(
    ("fraccion", "esperado"), [(0.42, 42.0), (0.0, 0.0), (1.0, 100.0), (0.12345, 12.3)]
)
def test_fraccion_a_pct(fraccion: float, esperado: float) -> None:
    assert fraccion_a_pct(fraccion) == esperado


@pytest.mark.parametrize(("pct", "esperado"), [(42, 0.42), (0, 0.0), (100, 1.0)])
def test_pct_a_fraccion(pct: float, esperado: float) -> None:
    assert pct_a_fraccion(pct) == pytest.approx(esperado)


def test_las_dos_direcciones_son_inversas() -> None:
    """El invariante que hace que nombrarlas sirva de algo.

    Si una redondeara y la otra no, ir y volver movería el número — y el
    índice de consumo del semáforo hace exactamente eso.
    """
    for pct in (0, 1, 33, 50, 99, 100):
        assert fraccion_a_pct(pct_a_fraccion(pct)) == pytest.approx(pct)


def test_la_razon_protege_del_denominador_cero() -> None:
    """La guarda que estaba copiada nueve veces.

    Un proyecto sin tareas abiertas es normal —recién creado, o terminado— y
    antes cada sitio tenía que acordarse de su `if`.
    """
    assert razon_a_pct(5, 0) == 0.0
    assert razon_a_pct(0, 0) == 0.0
    assert razon_a_pct(3, 4) == 75.0


def test_la_razon_en_decimal_no_pasa_por_coma_flotante() -> None:
    """IA-05: las cifras de los informes ejecutivos no se calculan en `float`.

    Existe aparte de la de `float` a propósito: fundirlas invitaría a llamar a
    la equivocada desde una ruta monetaria sin que nada avisara.
    """
    from decimal import Decimal

    resultado = razon_a_pct_decimal(Decimal("1"), Decimal("3"))
    assert isinstance(resultado, Decimal)
    assert str(resultado) == "33.3"
    assert razon_a_pct_decimal(Decimal("5"), Decimal("0")) == Decimal("0.0")


def test_los_mebibytes_van_y_vuelven() -> None:
    assert mebibytes(1) == BYTES_POR_MEBIBYTE == 1_048_576
    assert a_mebibytes(mebibytes(25)) == 25.0


def test_los_milisegundos_son_enteros() -> None:
    """`duration_ms` es `INTEGER` en el modelo.

    Dejar que cada sitio decidiera si redondea o trunca producía latencias que
    no suman con las que se guardan.
    """
    assert segundos_a_ms(1.2345) == 1234
    assert isinstance(segundos_a_ms(0.5), int)


def test_el_trinquete_reconoce_las_tres_familias() -> None:
    """Que la expresión no se quede corta sin que nadie lo note.

    Si dejara de reconocer una familia, la comprobación de arriba seguiría en
    verde mientras esa familia vuelve al dominio.
    """
    for muestra in (
        "pct = ratio * 100",
        "frac = pct / 100",
        "x = 100 / total",
        "LIMITE = 5 * 1024 * 1024",
        "ms = segundos * 1000",
    ):
        assert CONVERSIONES.search(muestra), f"dejó de reconocer: {muestra!r}"
