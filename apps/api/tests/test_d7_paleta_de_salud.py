"""D-7 — el semáforo de salud tiene un solo juego de colores.

Decisión del glosario (`docs/dominio/03-REVISION-GLOSARIO.md`, D-7): unificar
las dos paletas de salud. Había dos en el mismo archivo —`_HEALTH_DONUT_COLOR`
con los colores de marca y `_HEALTH_HEX` con los de Tailwind— y otras dos
repartidas por las plantillas PDF. El mismo proyecto en rojo salía `#C0392B` en
el donut y `#dc2626` en el mapa de árbol de al lado.

Y va atada a **MCS DIS-02**: unificar sin mirar el contraste habría consolidado
el verde que no llegaba a AA, que era justo el del semáforo. Por eso la suite
comprueba las dos cosas —una sola paleta, y que sea la que pasa AA— en vez de
solo contar copias.

Lo que **no** comprueba: que ningún archivo del repositorio vuelva a escribir un
verde a mano. Eso exigiría barrer cada hex de cada plantilla y se pondría rojo
con cualquier color decorativo. Se vigilan los sitios que pintan salud, que son
los que la decisión nombra.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.reports.scoped_status import (
    _HEALTH_DONUT_COLOR,
    _HEALTH_HEX,
    HEALTH_COLOR,
    _worst_health_color,
)

RAIZ_API = Path(__file__).resolve().parents[1]
GLOBALS_CSS = RAIZ_API.parents[0] / "web" / "app" / "globals.css"

#: Los colores que dejó de usar el semáforo. Los tres primeros son la paleta de
#: marca anterior a DIS-02; los tres siguientes, la de Tailwind que convivía
#: con ella.
RETIRADOS = ["#1F8A5B", "#B26B12", "#C0392B", "#16a34a", "#eab308", "#dc2626"]

#: Los sitios que pintan salud. Si aparece uno nuevo, se añade aquí.
PINTAN_SALUD = [
    "app/services/reports/scoped_status.py",
    "app/services/html_report_renderer.py",
    "app/templates/pdf/base.html",
    "app/templates/pdf/reports/scope_status.html",
    # Añadido el 2026-08-05 (DAT-05). Faltaba, y con él se escapó un quinto
    # juego de colores: `_RAG_RGB` pintaba el punto de salud del acta en .docx
    # con `#16a34a` y `#dc2626`, dos de los RETIRADOS de arriba. D-7 unificó
    # cuatro sitios, el registro dio DAT-05 por CONFORME, y el documento que
    # más se imprime y se firma seguía saliendo con la paleta anterior a
    # DIS-02 — la del verde que no llegaba a AA.
    #
    # La lección no es que faltara un archivo: es que una lista escrita a mano
    # no puede probar «una sola paleta». Por eso se añade además
    # `test_ningun_sitio_de_salud_copia_la_paleta`, que deriva los sitios del
    # código en vez de enumerarlos.
    "app/services/charter_generator.py",
]

#: **Fuera de D-7, y declarado en vez de silenciado.** Estos símbolos comparten
#: hex con la paleta retirada pero no pintan salud: son la paleta de *gráficos*
#: —líneas de tendencia, barras del Gantt, curva-S—, que arrastra los mismos
#: colores de Tailwind y también convendría unificar.
#:
#: No se toca aquí porque elegir si la línea de «avance promedio» debe llevar
#: el verde del semáforo es una decisión de diseño, no la que D-7 tomó. Queda
#: nombrada para que sea trabajo y no descuido: además de esta línea, están
#: `reports/gantt_renderer.py` y el `actual_color` de `reports/svg.py`.
AJENOS_A_SALUD = ("_TREND_COLOR",)


def test_los_dos_nombres_apuntan_a_la_misma_paleta():
    assert _HEALTH_DONUT_COLOR is HEALTH_COLOR
    assert _HEALTH_HEX is HEALTH_COLOR


def test_la_paleta_cubre_los_tres_estados():
    assert set(HEALTH_COLOR) == {"green", "yellow", "red"}


@pytest.mark.parametrize(
    "fila,esperado",
    [
        ({"red": 1, "yellow": 1, "green": 1}, "red"),
        ({"red": 0, "yellow": 2, "green": 1}, "yellow"),
        ({"red": 0, "yellow": 0, "green": 3}, "green"),
    ],
)
def test_el_peor_estado_manda(fila, esperado):
    assert _worst_health_color(fila) == HEALTH_COLOR[esperado]


@pytest.mark.parametrize("estado,token", [
    ("green", "success-fg"),
    ("yellow", "warning-fg"),
    ("red", "danger-fg"),
])
def test_la_paleta_es_la_de_globals_css(estado, token):
    """El backend no puede tener su propia idea del verde (DIS-02 + D-7).

    Se lee el CSS en vez de repetir el hex aquí: si alguien retoca el token por
    contraste y no toca el backend, el semáforo del informe se queda con el
    valor viejo — y esa desincronización es exactamente lo que D-7 corrige.
    """
    declarado = re.search(rf"--color-{token}:\s*(#[0-9A-Fa-f]{{6}})", GLOBALS_CSS.read_text(encoding="utf-8"))

    assert declarado, f"`--color-{token}` ya no está en globals.css como hex"
    assert HEALTH_COLOR[estado].lower() == declarado.group(1).lower()


@pytest.mark.parametrize("ruta", PINTAN_SALUD)
@pytest.mark.parametrize("retirado", RETIRADOS)
def test_no_queda_ninguna_copia_de_las_paletas_viejas(ruta, retirado):
    """Un hex retirado en un archivo que pinta salud es una paleta que revive."""
    texto = (RAIZ_API / ruta).read_text(encoding="utf-8")
    # Las menciones en comentarios son historia, no color: documentan de qué se
    # viene. Se descartan las líneas que empiezan por marca de comentario, y
    # las de la paleta de gráficos, que está declarada arriba.
    vivas = [
        n
        for n, linea in enumerate(texto.splitlines(), start=1)
        if retirado.lower() in linea.lower()
        and not linea.lstrip().startswith(("#", "//", "*", "<!--"))
        and not any(simbolo in linea for simbolo in AJENOS_A_SALUD)
    ]

    assert not vivas, (
        f"{ruta} sigue usando {retirado} en las líneas {vivas}. D-7 dejó una "
        f"sola paleta: `HEALTH_COLOR` en `scoped_status.py`."
    )


# ---------------------------------------------------------------------------
# DAT-05 (2026-08-05) — la comprobación que no depende de una lista escrita
# ---------------------------------------------------------------------------

#: Fondos suaves de distintivo. **No son un segundo semáforo**: son la forma
#: del `pill` —texto oscuro sobre fondo claro del mismo tono—, y el texto sí
#: sale de la paleta única. Se declaran con su razón en vez de silenciarse.
FONDOS_DE_DISTINTIVO = {
    "#dcfce7": "fondo suave del pill verde en los PDF",
    "#fef9c3": "fondo suave del pill amarillo en los PDF",
    "#fee2e2": "fondo suave del pill rojo en los PDF",
}

#: Un color en la misma línea que una clave de salud.
_CLAVE_DE_SALUD = re.compile(r"""(?:['".])(green|yellow|red)(?:['"]|\b)""")
_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def test_ningun_sitio_de_salud_copia_la_paleta() -> None:
    """Deriva los sitios del código en vez de enumerarlos.

    `PINTAN_SALUD` es una lista escrita a mano, y una lista escrita a mano no
    puede probar «una sola paleta»: prueba «una sola paleta entre los que me
    acordé de listar». Lo demostró `charter_generator.py`, que pintaba el punto
    de salud del acta con dos de los colores RETIRADOS y no estaba en la lista.
    D-7 unificó cuatro sitios, el registro dio DAT-05 por CONFORME, y el
    documento que más se imprime seguía saliendo con la paleta anterior.

    Esta comprobación invierte el defecto: **todo** archivo entra, y lo que se
    declara son las excepciones, con su razón.
    """
    canonicos = {v.lower() for v in HEALTH_COLOR.values()}
    permitidos = canonicos | {k.lower() for k in FONDOS_DE_DISTINTIVO} | {"#fff", "#ffffff"}

    intrusos = []
    for patron in ("*.py", "*.html"):
        for archivo in (RAIZ_API / "app").rglob(patron):
            for n, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
                if not _CLAVE_DE_SALUD.search(linea):
                    continue
                for color in _HEX.findall(linea):
                    if color.lower() not in permitidos:
                        intrusos.append(
                            f"{archivo.relative_to(RAIZ_API)}:{n}: {color} — {linea.strip()[:70]}"
                        )

    assert not intrusos, (
        "Colores de salud fuera de la paleta única. El origen es "
        "`HEALTH_COLOR`; si de verdad hace falta otro valor, va a "
        "`FONDOS_DE_DISTINTIVO` con su razón.\n" + "\n".join(intrusos)
    )


def test_el_acta_en_docx_usa_la_paleta_unica() -> None:
    """El caso concreto que se escapó, con el valor comprobado y no el texto.

    `_RAG_RGB` se deriva de `HEALTH_COLOR` en vez de copiarlo — una copia es lo
    que produjo las cinco paletas—, y esto lo comprueba mirando los bytes que
    acaban en el documento.
    """
    from app.services.charter_generator import _RAG_RGB

    for estado, esperado in HEALTH_COLOR.items():
        assert str(_RAG_RGB[estado]) == esperado.lstrip("#").upper(), (
            f"El punto de salud «{estado}» del acta en .docx sale {_RAG_RGB[estado]} "
            f"y la paleta única dice {esperado}."
        )
