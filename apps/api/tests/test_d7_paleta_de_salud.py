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
