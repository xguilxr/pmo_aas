"""ADR-023 — el semáforo se queda el arco cálido; los gráficos, el frío.

Antes convivían dos sistemas y ninguno decidido. Los gráficos de la web ofrecían
`success`, `warning` y `danger` como colores de **serie**, y los informes del
servidor llevaban hexes de Tailwind escritos a mano. El resultado concreto:
`#dc2626` marcaba «ruta crítica» en el Gantt y `#16a34a` marcaba «lo real» en la
curva-S, mientras el semáforo de salud usaba esos mismos rojo y verde para
«proyecto en problemas» y «proyecto sano». El mismo color decía dos cosas en la
misma página.

Partir el espectro no es una preferencia con adorno: hace **imposible por
construcción** que una serie parezca un estado.

Lo que esta suite defiende:

1. **Que ninguna ranura categórica pise el semáforo.** Es la regla entera.
2. **Que las dos copias de la paleta no se separen.** Los informes se dibujan en
   Python y la web en CSS; una paleta que vive en dos sitios se desincroniza el
   día que alguien toca uno.
3. **Que la quinta serie no se recicle en silencio**, que es como un gráfico
   acaba mintiendo sobre cuántas cosas distintas muestra.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.paleta import (
    ACENTO,
    CATEGORICA_CLARO,
    CATEGORICA_OSCURO,
    ORDINAL_CLARO,
    ORDINAL_OSCURO,
    SEMAFORO,
    escala,
    serie,
)

RAIZ = Path(__file__).resolve().parents[3]
GLOBALS_CSS = RAIZ / "apps" / "web" / "app" / "globals.css"


def _hex_a_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _distancia(a: str, b: str) -> float:
    ra, rb = _hex_a_rgb(a), _hex_a_rgb(b)
    return sum((x - y) ** 2 for x, y in zip(ra, rb, strict=True)) ** 0.5


# ---------------------------------------------------------------------------
# La regla: ninguna serie puede parecer un estado
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("paleta", [CATEGORICA_CLARO, CATEGORICA_OSCURO])
def test_ninguna_ranura_categorica_es_un_color_del_semaforo(paleta):
    choque = set(paleta) & set(SEMAFORO.values())
    assert not choque, f"Estas ranuras son colores de estado: {choque}"


@pytest.mark.parametrize("paleta", [CATEGORICA_CLARO, CATEGORICA_OSCURO])
def test_ninguna_ranura_se_parece_a_un_color_del_semaforo(paleta):
    """No basta con que no sean iguales: un rojo casi igual engaña lo mismo."""
    cerca = [
        (c, nombre, round(_distancia(c, s)))
        for c in paleta
        for nombre, s in SEMAFORO.items()
        if _distancia(c, s) < 60
    ]
    assert not cerca, f"Demasiado cerca de un estado: {cerca}"


def test_los_informes_ya_no_usan_los_hexes_de_tailwind():
    """Los seis que estaban escritos a mano en los dos renderizadores."""
    api = Path(__file__).resolve().parents[1]
    sospechosos = ("#2563eb", "#dc2626", "#7c3aed", "#16a34a", "#6b7280", "#9ca3af")
    encontrados: dict[str, list[str]] = {}
    for ruta in (api / "app" / "services" / "reports").rglob("*.py"):
        texto = ruta.read_text(encoding="utf-8")
        vivos = [
            h for h in sospechosos
            if any(
                h in linea and not linea.lstrip().startswith("#")
                for linea in texto.splitlines()
            )
        ]
        if vivos:
            encontrados[ruta.name] = vivos

    assert not encontrados, (
        f"Colores de Tailwind sueltos en los informes: {encontrados}. "
        f"Salen de `app/core/paleta.py` (ADR-023)."
    )


# ---------------------------------------------------------------------------
# Que las dos copias no se separen
# ---------------------------------------------------------------------------


def _tokens_css(bloque: str, prefijo: str) -> list[str]:
    return re.findall(rf"--chart-{prefijo}-\d+:\s*(#[0-9a-fA-F]{{6}})", bloque)


def _bloques() -> tuple[str, str]:
    css = GLOBALS_CSS.read_text(encoding="utf-8")
    corte = css.index('[data-theme="dark"]')
    return css[:corte], css[corte:]


@pytest.mark.parametrize(
    "indice,prefijo,esperado",
    [(0, "cat", CATEGORICA_CLARO), (0, "ord", ORDINAL_CLARO),
     (1, "cat", CATEGORICA_OSCURO), (1, "ord", ORDINAL_OSCURO)],
)
def test_los_tokens_css_espejan_el_modulo_de_python(indice, prefijo, esperado):
    """Una paleta que vive en dos sitios se desincroniza sola.

    Los informes se dibujan en el servidor y la web en el navegador, así que las
    dos copias son inevitables. Lo que no es inevitable es que se separen.
    """
    encontrados = _tokens_css(_bloques()[indice], prefijo)

    assert [c.lower() for c in encontrados] == [c.lower() for c in esperado]


def test_el_tema_oscuro_tiene_pasos_propios():
    """No es un volteo del claro: la banda válida sobre fondo oscuro es más
    estrecha y los pasos claros se caen de ella."""
    assert CATEGORICA_CLARO != CATEGORICA_OSCURO
    assert ORDINAL_CLARO != ORDINAL_OSCURO


def test_la_rampa_ordinal_es_de_un_solo_tono():
    """Si fuera de varios tonos dejaría de leerse como una secuencia.

    Se comprueba por la propiedad que importa: la luminosidad avanza en una sola
    dirección, sin repetir. Una rampa que sube y baja no ordena nada.
    """
    for rampa in (ORDINAL_CLARO, ORDINAL_OSCURO):
        luces = [sum(_hex_a_rgb(c)) for c in rampa]
        assert luces == sorted(luces) or luces == sorted(luces, reverse=True)
        assert len(set(luces)) == len(luces)


# ---------------------------------------------------------------------------
# Que la quinta serie no se recicle en silencio
# ---------------------------------------------------------------------------


def test_las_cuatro_ranuras_se_asignan_en_orden():
    assert [serie(i) for i in range(4)] == list(CATEGORICA_CLARO)
    assert [serie(i, oscuro=True) for i in range(4)] == list(CATEGORICA_OSCURO)


def test_pedir_una_quinta_serie_falla_en_vez_de_reciclar():
    """Reciclar es como un gráfico acaba mintiendo sobre cuántas cosas muestra.

    Fallar obliga a decidir —«Otros», múltiplos pequeños— en vez de heredar una
    decisión que nadie tomó.
    """
    with pytest.raises(ValueError, match="no se recicla|No se recicla"):
        serie(4)


def test_la_escala_reparte_por_los_extremos():
    """Tres tramos deben verse claro / medio / oscuro, no tres claros seguidos."""
    tres = escala(3)

    assert tres == [ORDINAL_CLARO[0], ORDINAL_CLARO[2], ORDINAL_CLARO[4]]
    assert escala(5) == list(ORDINAL_CLARO)
    assert escala(1) == [ORDINAL_CLARO[2]]
    assert escala(0) == []


def test_el_acento_es_el_de_la_plataforma():
    """La serie única y el lado «real» de la curva-S usan el acento de marca,
    no un azul propio de los gráficos."""
    assert ACENTO == "#2A4DA0"
