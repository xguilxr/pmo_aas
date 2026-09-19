"""US-273 — el reporte de participaciones cruzadas, sin base de datos delante.

El script `scripts/diagnostico_participaciones_cruzadas.py` necesita Postgres
para consultar, pero lo que decide si el reporte sirve —cómo agrupa y qué
imprime— es puro. Se prueba aquí: agrupar mal deja al owner sin saber a qué
organización pertenece el recurso que tiene que limpiar, y eso no lo
detectaría ninguna prueba de la consulta.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
RUTA = RAIZ / "scripts" / "diagnostico_participaciones_cruzadas.py"


def _cargar():
    spec = importlib.util.spec_from_file_location("dpc", RUTA)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _fila(**kwargs):
    base = {
        "tenant_slug": "acme",
        "participation_id": "pp1",
        "actor_id": "a1",
        "actor_name": "Ana",
        "actor_org": "Org A",
        "folio": "P-1",
        "project_name": "Proyecto Uno",
        "phase": "ejecucion",
        "project_org": "Org B",
    }
    base.update(kwargs)
    return base


def test_us273_agrupa_por_la_organizacion_del_actor():
    """El corte es por el dueño del recurso, no por el proyecto ajeno.

    Quien lee el reporte está limpiando su catálogo: necesita saber cuántos de
    **los suyos** tienen una asignación de más, no en cuántas organizaciones
    ajenas aparecen.
    """
    dpc = _cargar()
    filas = [
        _fila(actor_org="Org A", project_org="Org B"),
        _fila(actor_org="Org A", project_org="Org C", participation_id="pp2"),
        _fila(actor_org="Org D", project_org="Org B", actor_id="a2", participation_id="pp3"),
    ]
    grupos = dpc.agrupar(filas)
    assert set(grupos) == {("acme", "Org A"), ("acme", "Org D")}
    assert len(grupos[("acme", "Org A")]) == 2


def test_us273_agrupa_por_inquilino_ademas_de_organizacion():
    """Dos inquilinos no se mezclan aunque la organización se llame igual."""
    dpc = _cargar()
    grupos = dpc.agrupar(
        [_fila(tenant_slug="acme"), _fila(tenant_slug="globex", participation_id="pp2")]
    )
    assert set(grupos) == {("acme", "Org A"), ("globex", "Org A")}


def test_us273_el_actor_sin_organizacion_se_nombra_y_no_se_pierde():
    """Un nulo inesperado sale en el reporte en vez de desaparecer de él.

    La consulta ya excluye al recurso global, así que esta fila no debería
    existir. Si aparece, verla es lo que permite corregirla.
    """
    dpc = _cargar()
    grupos = dpc.agrupar([_fila(actor_org=None)])
    assert set(grupos) == {("acme", "sin organización")}


def test_us273_el_reporte_nombra_recurso_proyecto_y_organizacion_ajena():
    """Sin los tres datos no se puede decidir qué quitar sin abrir la base."""
    dpc = _cargar()
    lineas = dpc.formatear(dpc.agrupar([_fila()]))
    cabecera, detalle = lineas[0], lineas[1]
    assert "[acme] Org A" in cabecera
    assert "1 participación(es) cruzada(s) en 1 recurso(s)" in cabecera
    assert "Ana" in detalle
    assert "P-1 Proyecto Uno" in detalle
    assert "Org B" in detalle
    assert "ejecucion" in detalle


def test_us273_cuenta_recursos_distintos_no_participaciones():
    """Dos asignaciones del mismo recurso son un recurso, no dos."""
    dpc = _cargar()
    lineas = dpc.formatear(
        dpc.agrupar(
            [_fila(), _fila(participation_id="pp2", project_name="Proyecto Dos")]
        )
    )
    assert "2 participación(es) cruzada(s) en 1 recurso(s)" in lineas[0]


@pytest.mark.parametrize("nombre", ["agrupar", "formatear", "SQL", "main"])
def test_us273_el_script_expone_lo_que_el_runbook_promete(nombre: str):
    """Renombrar una de estas funciones rompe el reporte sin avisar."""
    assert hasattr(_cargar(), nombre)
