"""DAT-09 — cada indicador se define una sola vez.

«Cada indicador DEBE definirse una sola vez en el código. NO DEBE
reimplementarse por consumidor».

La auditoría dejó medida la mitad: «la salud se calcula en
`services/project_health.py`, una sola vez ✓. Otros indicadores no auditados».
Auditados los demás contra `07-FICHAS-INDICADORES.md`, salieron cuatro
reimplementaciones — y una ya había producido el fallo exacto que el requisito
existe para evitar.

## El que estaba roto

La ficha, firmada por el owner el 2026-08-06, dice: «Sin proyectos → `null`,
que se pinta «—». Cero proyectos no es cero por ciento». Se corrigió en
`dashboard.py`. `analytics/snapshots.py` calculaba **el mismo indicador** con
su propia división y su propio `else 0`, y se quedó fuera.

Resultado: el tablero decía «—» y la instantánea de ese día guardaba `0`. La
gráfica de tendencia de los informes lee instantáneas, así que dibujaba una
caída a cero en carteras recién creadas. Dos consumidores, dos fórmulas, y la
corrección alcanzó a uno.

Lo que se comprueba aquí no es solo que ahora haya una sola definición: es que
**las dos superficies dan la misma respuesta**, que es lo que un usuario nota.
"""
from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path

import pytest

from app.services.indicadores import (
    avance_de_cartera,
    dias_de_retraso,
    porcentaje_a_tiempo,
    promedio_de_avance,
)

API = Path(__file__).resolve().parents[1]
FUENTE = API / "app"
INDICADORES = FUENTE / "services" / "indicadores.py"
SALUD = FUENTE / "services" / "project_health.py"


# --------------------------------------------------------------------------
# La definición, y que sea una
# --------------------------------------------------------------------------


def test_sin_proyectos_no_es_cero_por_ciento() -> None:
    """La regla firmada, en el único sitio donde vive."""
    assert avance_de_cartera([]) is None, (
        "Cartera vacía devuelve un número. La ficha dice «—», y un tablero "
        "recién estrenado no es una cartera parada en seco."
    )
    assert avance_de_cartera([0.0]) == 0.0, (
        "Un proyecto al 0 % SÍ es cero por ciento. Confundir las dos "
        "direcciones es la otra mitad de DAT-12."
    )
    assert avance_de_cartera([50.0, 100.0]) == 75.0


def test_las_dos_superficies_del_avance_de_cartera_coinciden() -> None:
    """Lo que un usuario nota: el tablero y la instantánea, de acuerdo.

    Se comprueba sobre el ÁRBOL: los dos consumidores llaman a la misma
    función, así que coincidir es consecuencia y no coincidencia. Lo que esta
    prueba vigila es que ninguno vuelva a calcularlo por su cuenta.
    """
    consumidores = {
        "api/v1/endpoints/dashboard.py": "avance_de_cartera",
        "services/analytics/snapshots.py": "avance_de_cartera",
        "services/reports/gantt_renderer.py": "promedio_de_avance",
        "services/reports/engine.py": "promedio_de_avance",
        "services/operational_reports.py": "dias_de_retraso",
        "api/v1/endpoints/reports.py": "porcentaje_a_tiempo",
    }
    for ruta, funcion in consumidores.items():
        fuente = (FUENTE / ruta).read_text(encoding="utf-8")
        assert f"import {funcion}" in fuente or f", {funcion}" in fuente, (
            f"`{ruta}` dejó de importar `{funcion}`. O lo dejó de usar, o lo "
            f"volvió a calcular por su cuenta — que es DAT-09 otra vez."
        )
        assert f"{funcion}(" in fuente


def test_la_division_no_se_reescribe_fuera_del_modulo() -> None:
    """El trinquete: nadie vuelve a escribir la fórmula en su archivo.

    Se busca la FORMA de la reimplementación —una división entre un contador
    con guarda de cero— dentro de las funciones que producen indicadores, y no
    la palabra «promedio»: lo que reaparece es la aritmética, no el nombre.

    Se recorre el árbol y no el texto para no confundir un comentario que
    describe la fórmula con la fórmula. Ya pasó cinco veces en este
    repositorio: un control validándose contra su propia documentación.
    """
    sospechosas: list[str] = []
    patron_suma = re.compile(r"progress_sum|prog_values|sum\(eff")

    for archivo in sorted(FUENTE.rglob("*.py")):
        if archivo == INDICADORES:
            continue
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not (isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Div)):
                continue
            texto = ast.unparse(nodo)
            if patron_suma.search(texto):
                sospechosas.append(f"{archivo.relative_to(FUENTE)}: {texto}")

    assert not sospechosas, (
        "Estas divisiones recalculan un promedio de avance fuera de "
        "`indicadores.py`:\n  " + "\n  ".join(sospechosas)
    )


def test_la_resta_del_retraso_no_se_reescribe() -> None:
    """La misma idea sobre `dias_de_retraso`, que estaba escrita dos veces.

    A diecisiete líneas de distancia, en el mismo archivo: una para tareas y
    otra para acciones. Dos copias de la misma resta divergen en cuanto una
    aprende algo —un calendario laboral, un huso— y la otra no.
    """
    copias: list[str] = []
    for archivo in sorted(FUENTE.rglob("*.py")):
        if archivo == INDICADORES:
            continue
        for numero, linea in enumerate(
            archivo.read_text(encoding="utf-8").splitlines(), 1
        ):
            if re.search(r"\(\s*cut_off_date\s*-\s*\w+\s*\)\.days", linea):
                copias.append(f"{archivo.relative_to(FUENTE)}:{numero}")
    assert not copias, (
        "Estas líneas recalculan los días de retraso:\n  " + "\n  ".join(copias)
    )


# --------------------------------------------------------------------------
# Lo que NO se toca, y por qué se dice
# --------------------------------------------------------------------------


def test_la_salud_sigue_teniendo_su_propia_casa() -> None:
    """DAT-09 pide una definición por indicador, no un archivo que las junte.

    La salud ya era única. Traerla aquí la alejaría de su rúbrica y de los
    umbrales por dimensión que el owner calibró (US-196), sin ganar nada.
    """
    assert SALUD.exists()
    fuente = SALUD.read_text(encoding="utf-8")
    assert "def evaluate" in fuente or "def compute" in fuente or "_budget_color" in fuente
    assert "from app.services.indicadores import" not in fuente, (
        "La salud empezó a depender del módulo de indicadores. Si es porque "
        "comparte un cálculo, ese cálculo es el que hay que unificar; si es "
        "por orden, no lo hagas."
    )


# --------------------------------------------------------------------------
# Las definiciones, una por una
# --------------------------------------------------------------------------


def test_el_promedio_por_cubo_no_es_el_de_cartera() -> None:
    """Se llaman distinto porque son distintos, y la ficha lo advierte.

    Distinto denominador (elementos del cubo vs proyectos) y distinto trato
    del vacío: el cubo vacío es un error de quien llama; la cartera vacía es
    una cartera vacía.
    """
    assert promedio_de_avance(0.0, 0) == 0.0
    assert avance_de_cartera([]) is None
    assert promedio_de_avance(150.0, 4) == 37.5


@pytest.mark.parametrize(
    "compromiso,esperado",
    [
        (date(2026, 8, 1), 5),
        (date(2026, 8, 6), 0),
        (date(2026, 8, 20), 0),
        (None, 0),
    ],
)
def test_los_dias_de_retraso_nunca_son_negativos(
    compromiso: date | None, esperado: int
) -> None:
    """Una fecha futura no adelanta el reloj: son cero días de retraso."""
    assert dias_de_retraso(compromiso, date(2026, 8, 6)) == esperado


def test_el_porcentaje_a_tiempo_se_recorta() -> None:
    """El recorte es parte de la definición, y por eso vive con ella.

    `delayed` puede venir de un conteo con otro filtro que `total` —ya pasó,
    ENH-146— y sin recorte el indicador sale negativo o por encima de cien.
    """
    assert porcentaje_a_tiempo(10, 0) == 100
    assert porcentaje_a_tiempo(10, 10) == 0
    assert porcentaje_a_tiempo(10, 15) == 0, "Sin recorte saldría -50."
    assert porcentaje_a_tiempo(0, 0) == 0, "Sin plan no hay porcentaje que dar."
    assert porcentaje_a_tiempo(4, 1) == 75


def test_la_instantanea_puede_guardar_la_ausencia() -> None:
    """Sin esto, la definición única sería verdad y el dato seguiría mintiendo.

    La columna era `NOT NULL DEFAULT 0`, así que el recolector no tenía dónde
    escribir «no hay nada que promediar» aunque la función se lo devolviera.
    """
    from app.models.metric_snapshot import MetricSnapshot

    columna = MetricSnapshot.__table__.columns["avg_progress"]
    assert columna.nullable, (
        "`metric_snapshots.avg_progress` volvió a ser NOT NULL. La "
        "instantánea no puede distinguir «cartera al 0 %» de «no hay "
        "proyectos», y la gráfica de tendencia dibuja una caída a cero."
    )
