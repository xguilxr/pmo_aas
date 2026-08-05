"""ADR-022 — cancelar un proyecto y cerrarlo son dos finales distintos.

Hasta hoy sólo había uno. Un proyecto cortado a mitad —porque se quedó sin
presupuesto, porque cambió la prioridad, porque el patrocinador se fue—
terminaba en `closed`, **exactamente igual que uno que llegó al final y
entregó**. La consecuencia no es cosmética:

- cualquier métrica de éxito cuenta el cancelado como entregado;
- sus lecciones aprendidas se mezclan con las de los que sí cumplieron, que es
  justo donde más importa distinguirlos;
- y no hay forma de responder «cuántos proyectos cancelamos este año», que es
  una pregunta que una PMO se hace.

Lo que estas pruebas defienden, en orden de importancia:

1. **Que `cancelled` no cuente como activo.** Es la propiedad que se rompe sin
   hacer ruido: un proyecto cancelado que siguiera entrando en los snapshots
   inflaría el portafolio vivo para siempre, y nadie lo vería en una pantalla.
2. **Que se llegue desde cualquier fase viva.** Cancelar no es un paso del
   ciclo, es interrumpirlo; no depende de dónde estaba el proyecto.
3. **Que sea terminal**, como `closed`.
4. **Que `closed` no lleve a `cancelled`.** Un proyecto que llegó al final ya
   tuvo su final; permitirlo sería reescribir la historia.
"""
from __future__ import annotations

from typing import get_args

import pytest

from app.api.v1.endpoints.projects import VALID_TRANSITIONS
from app.schemas.project import FASES_TERMINALES, PhaseChange, ProjectPhase
from app.services.analytics.snapshots import ACTIVE_PHASES

FASES_VIVAS = ("planning", "execution", "hypercare")


# ---------------------------------------------------------------------------
# El vocabulario
# ---------------------------------------------------------------------------


def test_cancelled_es_parte_del_vocabulario_canonico():
    assert set(get_args(ProjectPhase)) == {
        "planning", "execution", "hypercare", "closed", "cancelled",
    }


def test_los_dos_finales_estan_declarados():
    assert FASES_TERMINALES == {"closed", "cancelled"}


def test_el_esquema_acepta_cancelled_como_destino():
    assert PhaseChange(new_phase="cancelled").new_phase == "cancelled"


def test_el_esquema_rechaza_una_fase_inventada():
    with pytest.raises(ValueError):
        PhaseChange(new_phase="abandonado")


# ---------------------------------------------------------------------------
# Lo que se rompe en silencio: contar un cancelado como vivo
# ---------------------------------------------------------------------------


def test_cancelled_no_cuenta_como_fase_activa():
    """La propiedad que no avisa al romperse.

    Un cancelado dentro de `ACTIVE_PHASES` seguiría sumando al portafolio vivo
    en cada snapshot semanal, sin error y sin pantalla que lo delate.
    """
    assert "cancelled" not in ACTIVE_PHASES


def test_ninguna_fase_terminal_cuenta_como_activa():
    assert not (set(ACTIVE_PHASES) & FASES_TERMINALES)


def test_las_activas_son_exactamente_las_no_terminales():
    """`ACTIVE_PHASES` se deriva; si volviera a escribirse a mano, esto lo caza.

    Es el error que D-2 cometió: la lista se quedó con el nombre viejo de la
    fase y los proyectos en hypercare habrían salido de los snapshots sin que
    nada fallara. Derivarla cierra la clase entera.
    """
    assert set(ACTIVE_PHASES) == set(get_args(ProjectPhase)) - FASES_TERMINALES


# ---------------------------------------------------------------------------
# Las transiciones
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fase", FASES_VIVAS)
def test_se_cancela_desde_cualquier_fase_viva(fase):
    """Cancelar interrumpe el ciclo; no depende de dónde estaba el proyecto."""
    assert "cancelled" in VALID_TRANSITIONS[fase]


def test_cancelled_es_terminal():
    assert VALID_TRANSITIONS["cancelled"] == set()


def test_un_proyecto_cerrado_no_se_puede_cancelar():
    """Ya tuvo su final. Permitirlo sería reescribir la historia."""
    assert "cancelled" not in VALID_TRANSITIONS["closed"]


def test_toda_fase_del_vocabulario_tiene_transiciones_declaradas():
    """Una fase sin fila cae en el `.get(p.phase, set())` del endpoint y queda
    atrapada: sin salidas y sin que nadie lo haya decidido."""
    assert set(VALID_TRANSITIONS) == set(get_args(ProjectPhase))


def test_ninguna_transicion_apunta_fuera_del_vocabulario():
    for origen, destinos in VALID_TRANSITIONS.items():
        fuera = set(destinos) - set(get_args(ProjectPhase))
        assert not fuera, f"`{origen}` apunta a {fuera}, que no son fases"


def test_las_terminales_no_tienen_salida():
    for fase in FASES_TERMINALES:
        assert VALID_TRANSITIONS[fase] == set(), f"`{fase}` debería ser terminal"
