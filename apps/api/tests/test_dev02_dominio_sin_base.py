"""DEV-02 — la lógica de dominio se verifica sin tocar la base.

«La lógica de dominio DEBE ser verificable sin acceso a base de datos».

La auditoría lo dejó PARCIAL con el motivo escrito: «las pruebas usan SQLite en
memoria (`tests/conftest.py`): rápido, pero la lógica de dominio **sí** necesita
base de datos».

**Este archivo es la demostración, y su forma es la prueba.** No usa ninguna
fixture, no abre sesión y no importa `app.models`: si algún día la lógica
necesitara la base, este archivo dejaría de poder ejecutarse. No hace falta que
nadie lo vigile — dejaría de pasar.

El trinquete de abajo lo sostiene por el otro lado: `app/dominio/` no puede
importar SQLAlchemy ni los modelos, comprobado sobre el árbol.

## Qué es dominio y qué no

Contar cuántos hitos van vencidos es **acceso a datos**: hace falta la base.
Decidir de qué color sale un proyecto con tres hitos vencidos es **dominio**: le
bastan los números. La separación es esa, y por eso `project_health.py` sigue
existiendo con sus consultas mientras las reglas se fueron a `app/dominio`.
"""
from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.core.magnitudes import CATALOGO
from app.core.unidades import (
    a_mebibytes,
    fraccion_a_pct,
    pct_a_fraccion,
    razon_a_pct,
    razon_a_pct_decimal,
    segundos_a_ms,
)
from app.dominio.salud import (
    DEFAULT_HEALTH_THRESHOLDS,
    color_de_cronograma,
    color_de_decisiones,
    color_de_presupuesto,
    color_de_riesgos,
    peor_color,
    umbrales_efectivos,
)
from app.services.ai.corpus import RAID
from app.services.ai.frontera import fuera_de_alcance
from app.services.indicadores import (
    avance_de_cartera,
    dias_de_retraso,
    porcentaje_a_tiempo,
    promedio_de_avance,
)

API = Path(__file__).resolve().parents[1]
DOMINIO = API / "app" / "dominio"

UMBRALES = DEFAULT_HEALTH_THRESHOLDS


# --------------------------------------------------------------------------
# El trinquete: el dominio no puede aprender a consultar
# --------------------------------------------------------------------------


def test_el_dominio_no_importa_la_base() -> None:
    """Lo que hace que DEV-02 siga siendo verdad mañana.

    Se recorre el árbol y no el texto: un módulo puede **mencionar**
    SQLAlchemy en su docstring —el de `salud.py` lo hace, explicando de dónde
    vino— y eso no es importarlo. Buscar la palabra habría prohibido explicar
    la decisión, que es el modo de fallo de un control validándose contra su
    propia documentación.
    """
    prohibidos = ("sqlalchemy", "app.models", "app.db")
    infractores: list[str] = []

    for archivo in sorted(DOMINIO.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            modulos: list[str] = []
            if isinstance(nodo, ast.Import):
                modulos = [a.name for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos = [nodo.module]
            for modulo in modulos:
                if any(modulo.startswith(p) for p in prohibidos):
                    infractores.append(f"{archivo.name}: importa {modulo}")

    assert not infractores, (
        "El dominio empezó a depender de la base:\n  " + "\n  ".join(infractores)
        + "\n\nContar filas es acceso a datos y su sitio es `app/services`. Lo "
        "que vive aquí recibe los números ya contados."
    )


def test_las_reglas_no_reciben_una_sesion() -> None:
    """La otra forma de colar la base: pedirla por parámetro.

    Un `db` en la firma haría fallar el trinquete de arriba solo si además se
    importara el tipo. Esto lo caza por el nombre del argumento, que es lo que
    de verdad ata la función a una sesión.
    """
    sospechosas: list[str] = []
    for archivo in sorted(DOMINIO.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            nombres = {a.arg for a in nodo.args.args} | {
                a.arg for a in nodo.args.kwonlyargs
            }
            if nombres & {"db", "session", "sesion", "conn"}:
                sospechosas.append(f"{archivo.name}::{nodo.name}")
            if isinstance(nodo, ast.AsyncFunctionDef):
                sospechosas.append(
                    f"{archivo.name}::{nodo.name} es asíncrona — en el dominio "
                    f"no hay nada que esperar salvo E/S"
                )
    assert not sospechosas, "\n  ".join(sospechosas)


# --------------------------------------------------------------------------
# El semáforo: la parte del producto que más se mira
# --------------------------------------------------------------------------


def test_el_peor_color_manda() -> None:
    """Verde < amarillo < rojo, por rango y no por orden alfabético.

    Comparar los textos pondría el rojo en medio («green» < «red» < «yellow»),
    y un proyecto en rojo saldría amarillo.
    """
    assert peor_color(["green", "yellow", "red"]) == "red"
    assert peor_color(["green", "yellow"]) == "yellow"
    assert peor_color(["green"]) == "green"
    assert peor_color([]) == "green", "Sin dimensiones evaluadas no hay alarma."
    assert peor_color([None, "inventado"]) == "green", (
        "Un color desconocido se ignora en vez de tumbar el cálculo. Lo que "
        "llega aquí puede venir de `tenant.settings`, que edita una persona."
    )


@pytest.mark.parametrize(
    "vencidos_pct,hitos,esperado",
    [
        (0, 0, "green"),
        (9, 0, "green"),
        (10, 0, "yellow"),
        (24, 0, "yellow"),
        (25, 0, "red"),
        (0, 1, "yellow"),
        (0, 2, "red"),
        (30, 0, "red"),
        (5, 2, "red"),
    ],
)
def test_el_cronograma_evalua_el_rojo_primero(
    vencidos_pct: float, hitos: int, esperado: str
) -> None:
    """Nueve combinaciones en milisegundos. Con una base de por medio serían
    nueve inserciones, y por eso nadie las escribía.

    El caso `(5, 2)` es el que importa: poco porcentaje vencido y dos hitos
    perdidos. Con el amarillo evaluado antes que el rojo saldría amarillo.
    """
    assert color_de_cronograma(UMBRALES["schedule"], vencidos_pct, hitos) == esperado


@pytest.mark.parametrize(
    "indice,esperado",
    [(0.0, "green"), (1.0, "green"), (1.14, "green"), (1.15, "yellow"), (1.29, "yellow"), (1.30, "red"), (3.0, "red")],
)
def test_el_presupuesto_se_mide_contra_el_avance(indice: float, esperado: str) -> None:
    """El índice de quemado, no el gasto absoluto.

    Es la corrección de US-196: «85 % gastado con 10 % de avance salía verde»
    cuando el presupuesto se medía contra sí mismo.
    """
    assert color_de_presupuesto(UMBRALES["budget"], indice) == esperado


@pytest.mark.parametrize(
    "severos,incidencias,esperado",
    [(0, 0, "green"), (1, 0, "green"), (2, 0, "yellow"), (3, 0, "red"), (0, 8, "yellow"), (0, 15, "red"), (1, 15, "red")],
)
def test_los_riesgos_no_saltan_con_el_primero(
    severos: int, incidencias: int, esperado: str
) -> None:
    """Un riesgo severo es la operación normal de un proyecto vivo.

    El piso estaba en 1 y dejaba casi toda la cartera en amarillo permanente.
    Un semáforo que siempre está amarillo dejó de informar.
    """
    assert color_de_riesgos(UMBRALES["risks"], severos, incidencias) == esperado


@pytest.mark.parametrize(
    "estancadas,esperado", [(0, "green"), (1, "green"), (2, "yellow"), (3, "red"), (9, "red")]
)
def test_las_decisiones_estancadas(estancadas: int, esperado: str) -> None:
    assert color_de_decisiones(UMBRALES["decisions"], estancadas) == esperado


def test_los_umbrales_del_inquilino_se_mezclan_sin_romperse() -> None:
    """El diccionario lo edita una persona desde un formulario.

    Una llave mal escrita o un texto donde va un número **no puede** dejar el
    semáforo sin pintar: se ignora y se usa el valor por defecto. Un tablero en
    blanco por una errata es peor que uno con los umbrales de fábrica.
    """
    base = umbrales_efectivos(None)
    assert base == DEFAULT_HEALTH_THRESHOLDS

    ajustado = umbrales_efectivos(
        {
            "health_thresholds": {
                "budget": {"yellow_burn_index": 1.05},
                "dimension_inventada": {"x": 1},
                "risks": {"yellow_severe": "muchos", "red_severe": 4},
            }
        }
    )
    assert ajustado["budget"]["yellow_burn_index"] == 1.05
    assert ajustado["budget"]["red_burn_index"] == 1.30, "Lo no tocado no cambia."
    assert "dimension_inventada" not in ajustado
    assert ajustado["risks"]["yellow_severe"] == 2, "El texto se ignora."
    assert ajustado["risks"]["red_severe"] == 4

    assert umbrales_efectivos({}) == DEFAULT_HEALTH_THRESHOLDS
    assert umbrales_efectivos({"health_thresholds": None}) == DEFAULT_HEALTH_THRESHOLDS
    assert umbrales_efectivos({"health_thresholds": {"budget": {"yellow_burn_index": True}}})[
        "budget"
    ]["yellow_burn_index"] == 1.15, (
        "`True` es un `int` en Python y valdría 1 como umbral, dejando todo en "
        "amarillo. Se excluye explícitamente."
    )


# --------------------------------------------------------------------------
# El resto del dominio: indicadores, unidades, magnitudes, corpus, frontera
# --------------------------------------------------------------------------


def test_los_indicadores_se_calculan_con_numeros_sueltos() -> None:
    assert avance_de_cartera([]) is None
    assert avance_de_cartera([50.0, 100.0]) == 75.0
    assert promedio_de_avance(150.0, 4) == 37.5
    assert dias_de_retraso(date(2026, 8, 1), date(2026, 8, 6)) == 5
    assert dias_de_retraso(None, date(2026, 8, 6)) == 0
    assert porcentaje_a_tiempo(10, 15) == 0


def test_las_conversiones_de_unidad_son_puras() -> None:
    assert fraccion_a_pct(0.42) == 42.0
    assert pct_a_fraccion(42) == 0.42
    assert razon_a_pct(1, 4) == 25.0
    assert razon_a_pct(1, 0) == 0.0, "Un proyecto sin tareas no divide por cero."
    assert razon_a_pct_decimal(Decimal(1), Decimal(4)) == Decimal("25.0")
    assert segundos_a_ms(1.5) == 1500
    assert a_mebibytes(1024 * 1024) == 1.0


def test_el_catalogo_y_el_corpus_se_leen_sin_sesion() -> None:
    """Las declaraciones de DAT-01 y CON-02 también son dominio."""
    assert CATALOGO["importe"].unidad
    assert {c.letra for c in RAID} == {"A", "R", "D", "I"}
    assert fuera_de_alcance("¿puedo despedirlo por bajo desempeño?") is not None
    assert fuera_de_alcance("¿cuántos riesgos abiertos hay?") is None


def test_este_archivo_no_usa_ninguna_fixture_de_base() -> None:
    """La prueba de la prueba.

    Si alguien añade aquí un caso que pide `db` o `client`, DEV-02 deja de
    estar demostrado y este archivo pasa a ser decorativo. Se comprueba sobre
    su propio árbol.
    """
    propio = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    prohibidas = {"db", "client", "session", "async_session", "tenant", "app"}
    con_fixture = [
        n.name
        for n in ast.walk(propio)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("test_")
        and ({a.arg for a in n.args.args} & prohibidas)
    ]
    assert not con_fixture, (
        f"Estos casos piden una fixture de base: {con_fixture}. Este archivo "
        f"existe para demostrar que el dominio no la necesita."
    )
