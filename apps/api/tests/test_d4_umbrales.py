"""D-4 — el semáforo mide contra el avance, y el amarillo deja de ser el default.

Decisión del owner, 2026-08-05. La revisión del glosario dejó D-4 con la forma
resuelta —un umbral por dimensión— y los valores pendientes. Al ir a calibrarlos
aparecieron dos cosas que ningún número arregla:

1. **El presupuesto no miraba el tiempo.** Comparaba `gastado / presupuesto` y
   coloreaba contra eso. Un proyecto con el 85 % del presupuesto gastado y el
   10 % de avance salía **verde**: va camino de costar ocho veces lo planeado y
   el semáforo callaba, porque 0,85 < 0,90.
2. **Casi todos los amarillos disparaban con el primer caso.** Cuatro de las
   cinco dimensiones ponían el piso en 0 o 1. En una cartera real eso es
   amarillo permanente, y un semáforo siempre amarillo dejó de informar.

Y una de estructura: la dimensión de recursos se configuraba en otra llave de
settings, con dos reglas escritas a fuego que nadie podía ajustar.
"""
from __future__ import annotations

import pytest

from app.services.project_health import (
    DEFAULT_HEALTH_THRESHOLDS,
    DIMENSION_LABELS,
    _budget_color,
    _decisions_color,
    _risks_color,
    _schedule_color,
    get_health_thresholds,
)

T = DEFAULT_HEALTH_THRESHOLDS


def _indice(gastado_pct: float, avance_pct: float) -> float:
    """El índice de consumo, como lo calcula `_budget_dimension`."""
    return (gastado_pct / 100) / (avance_pct / 100)


# ---------------------------------------------------------------------------
# El caso que antes salía verde
# ---------------------------------------------------------------------------


def test_gastar_casi_todo_sin_avanzar_ya_no_es_verde():
    """El caso que motivó el cambio: 85 % gastado, 10 % de avance.

    Con la regla vieja (`ratio >= 0.9` → amarillo) daba **verde**, porque 0,85
    se quedaba corto del umbral. El índice de consumo da 8,5.
    """
    indice = _indice(85, 10)

    assert indice == pytest.approx(8.5)
    assert _budget_color(T["budget"], indice) == "red"


def test_gastar_al_ritmo_que_se_avanza_es_verde():
    """La otra mitad: consumir el 90 % con el 90 % hecho no tiene nada de malo.

    Con la regla vieja esto era **amarillo** —0,90 alcanzaba el umbral— aunque
    el proyecto fuera exactamente según plan. El índice da 1,0.
    """
    assert _indice(90, 90) == pytest.approx(1.0)
    assert _budget_color(T["budget"], _indice(90, 90)) == "green"
    assert _budget_color(T["budget"], _indice(50, 50)) == "green"


@pytest.mark.parametrize(
    "gastado,avance,esperado",
    [
        (30, 30, "green"),    # al ritmo
        (55, 50, "green"),    # 1,10 — dentro de la tolerancia
        (60, 50, "yellow"),   # 1,20
        (70, 50, "red"),      # 1,40
        (20, 10, "red"),      # 2,00
    ],
)
def test_la_escala_del_indice_de_consumo(gastado, avance, esperado):
    assert _budget_color(T["budget"], _indice(gastado, avance)) == esperado


def test_el_ratio_crudo_ya_no_es_un_umbral():
    """Si volvieran, el caso de arriba vuelve a salir verde."""
    assert "yellow_ratio" not in T["budget"]
    assert "red_ratio" not in T["budget"]


# ---------------------------------------------------------------------------
# El amarillo deja de dispararse con el primer caso
# ---------------------------------------------------------------------------


def test_un_riesgo_severo_no_pinta_amarillo():
    """P×I ≥ 13 en un proyecto vivo es la operación normal, no una señal."""
    assert _risks_color(T["risks"], severe=1, open_issues=0) == "green"
    assert _risks_color(T["risks"], severe=2, open_issues=0) == "yellow"


def test_una_decision_estancada_no_pinta_amarillo():
    assert _decisions_color(T["decisions"], stale=1) == "green"
    assert _decisions_color(T["decisions"], stale=2) == "yellow"


def test_ningun_piso_de_amarillo_dispara_con_el_primer_caso():
    """La regla, no el caso: es lo que hacía inútil al semáforo.

    Se comprueban los pisos que cuentan **ocurrencias**. `yellow_overdue_pct`
    queda fuera porque es un porcentaje, y `yellow_overdue_milestones` también,
    a propósito: un hito perdido **sí** es señal, y ahí el owner mantuvo el 1.
    """
    pisos = {
        ("risks", "yellow_severe"): T["risks"]["yellow_severe"],
        ("decisions", "yellow_stale"): T["decisions"]["yellow_stale"],
        ("resources", "yellow_over"): T["resources"]["yellow_over"],
    }
    disparan_con_el_primero = {k: v for k, v in pisos.items() if v <= 1}

    assert not disparan_con_el_primero, (
        f"Estos pisos vuelven amarillo un proyecto con el primer caso: "
        f"{disparan_con_el_primero}. Es lo que dejaba la cartera entera en "
        f"amarillo permanente."
    )


def test_un_hito_perdido_sigue_siendo_amarillo():
    """La excepción deliberada: aquí el primer caso sí es señal."""
    assert _schedule_color(T["schedule"], overdue_pct=0, overdue_ms=1) == "yellow"


def test_dos_hitos_perdidos_ya_son_rojos():
    """3 → 2: tres hitos perdidos es enterarse tarde."""
    assert _schedule_color(T["schedule"], overdue_pct=0, overdue_ms=2) == "red"


# ---------------------------------------------------------------------------
# Que las cinco dimensiones se configuren en un solo sitio
# ---------------------------------------------------------------------------


def test_las_cinco_dimensiones_tienen_umbrales_declarados():
    """Recursos vivía en `capacity_thresholds`; era la única que no se podía
    ajustar desde donde se ajustan las demás."""
    assert set(T) == set(DIMENSION_LABELS)


def test_las_reglas_de_recursos_ya_no_estan_a_fuego():
    """Las dos cuentas —un recurso clave, tres en total— eran literales."""
    assert T["resources"]["red_key_overloaded"] == 1
    assert T["resources"]["yellow_overloaded_count"] == 3


def test_cualquier_dimension_se_puede_ajustar_por_inquilino():
    """Es lo que hace que la calibración no necesite tocar código."""

    class _Inquilino:
        settings = {"health_thresholds": {
            "budget": {"yellow_burn_index": 1.05},
            "resources": {"yellow_over": 20},
        }}

    t = get_health_thresholds(_Inquilino())

    assert t["budget"]["yellow_burn_index"] == 1.05
    assert t["resources"]["yellow_over"] == 20
    assert t["risks"]["yellow_severe"] == T["risks"]["yellow_severe"], "el resto no se toca"


def test_un_override_con_basura_no_rompe_el_semaforo():
    class _Inquilino:
        settings = {"health_thresholds": {
            "budget": {"yellow_burn_index": "mucho"},
            "inventada": {"x": 1},
            "resources": None,
        }}

    t = get_health_thresholds(_Inquilino())

    assert t["budget"]["yellow_burn_index"] == T["budget"]["yellow_burn_index"]
    assert "inventada" not in t
