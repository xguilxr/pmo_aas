"""ENH-109 — Rollup jerárquico de avance por WBS.

El avance de una tarea con hijos es el promedio del avance de sus hijos
(recursivo por nivel). El avance general del proyecto es el promedio de
los WBS de nivel más alto. Estos tests son puros (sin DB) y verifican el
ejemplo exacto que dio el owner, donde el general da ~26%.
"""
from app.models.task import Task
from app.services.plan_metadata import (
    compute_plan_rollup_progress,
    compute_wbs_rollup,
    parent_wbs,
    round_half_up,
)


def _t(wbs: str, progress: int) -> Task:
    """Task en memoria. `progress` de los padres se pone en 0 a propósito
    para demostrar que el rollup lo sobrescribe."""
    return Task(id=wbs, wbs=wbs, progress=progress, name=f"T{wbs}")


# Ejemplo literal del owner (los padres llevan progress=0 almacenado; el
# rollup debe recalcularlos).
OWNER_EXAMPLE = [
    _t("0", 100),
    _t("1", 0),
    _t("1.1", 0),
    _t("1.1.1", 85),
    _t("1.1.3", 100),
    _t("1.1.4", 0),
    _t("1.2", 0),
    _t("1.2.1", 100),
    _t("1.2.2", 85),
    _t("1.3", 0),
    _t("1.3.1", 0),
    _t("1.3.2", 0),
    _t("1.3.3", 0),
    _t("1.4", 0),
    _t("2", 0),
    _t("2.1", 100),
    _t("2.2", 100),
    _t("2.3", 80),
    _t("2.4", 50),
    _t("2.5", 0),
    _t("3", 0),
    _t("3.1", 0), _t("3.2", 0), _t("3.3", 0), _t("3.4", 0), _t("3.5", 0),
    _t("4", 0),
    _t("4.1", 0), _t("4.2", 0), _t("4.3", 0), _t("4.4", 0), _t("4.5", 0),
    _t("5", 0),
    _t("5.1", 0), _t("5.2", 0), _t("5.3", 0), _t("5.4", 0),
    _t("6", 0),
    _t("6.1", 0), _t("6.2", 0), _t("6.3", 0), _t("6.4", 0),
    _t("6.5", 0), _t("6.6", 0), _t("6.7", 0), _t("6.8", 0),
    _t("7", 0),
    _t("7.1", 0), _t("7.2", 0), _t("7.3", 0),
    _t("7.4", 0), _t("7.5", 0), _t("7.6", 0),
]


def test_parent_wbs():
    assert parent_wbs("1.2.3") == "1.2"
    assert parent_wbs("1.2") == "1"
    assert parent_wbs("1") is None
    assert parent_wbs(None) is None
    assert parent_wbs("") is None


def test_round_half_up():
    # banker's rounding daría 92 para 92.5; nosotros queremos 93.
    assert round_half_up(92.5) == 93
    assert round_half_up(61.67) == 62
    assert round_half_up(25.59) == 26
    assert round_half_up(50.0) == 50
    assert round_half_up(0.0) == 0


def test_rollup_matches_owner_example():
    roll = compute_wbs_rollup(OWNER_EXAMPLE)

    # Hojas conservan su valor.
    assert roll["1.1.1"] == 85.0
    assert roll["1.4"] == 0.0
    assert roll["0"] == 100.0

    # Padres = promedio de hijos directos.
    assert round_half_up(roll["1.1"]) == 62  # (85+100+0)/3 = 61.67
    assert round_half_up(roll["1.2"]) == 93  # (100+85)/2 = 92.5
    assert round_half_up(roll["1.3"]) == 0
    assert round_half_up(roll["2"]) == 66  # (100+100+80+50+0)/5 = 66

    # Nivel 1 recursivo: (61.67 + 92.5 + 0 + 0)/4 = 38.54 → 39.
    assert round_half_up(roll["1"]) == 39


def test_general_progress_is_26():
    general = compute_plan_rollup_progress(OWNER_EXAMPLE)
    assert general is not None
    # promedio de las 8 raíces (0..7): (100 + 38.54 + 66 + 0*5)/8 = 25.6.
    assert round_half_up(general) == 26


def test_empty_plan_returns_none():
    assert compute_plan_rollup_progress([]) is None


def test_task_without_wbs_is_root_leaf():
    tasks = [_t("1", 0), _t("1.1", 40), _t("1.2", 60)]
    no_wbs = Task(id="x", wbs=None, progress=20, name="suelta")
    tasks.append(no_wbs)
    roll = compute_wbs_rollup(tasks)
    assert round_half_up(roll["1"]) == 50  # (40+60)/2
    assert roll["x"] == 20.0  # hoja sin wbs conserva su valor
    # raíces = "1" (rollup 50) + "x" (20) → general (50+20)/2 = 35.
    assert round_half_up(compute_plan_rollup_progress(tasks)) == 35


def test_orphan_wbs_treated_as_root():
    # "2.3" existe pero no su padre "2.3"->"2": es huérfano → raíz.
    tasks = [_t("1", 0), _t("1.1", 80), _t("5.3", 100)]
    roll = compute_wbs_rollup(tasks)
    assert round_half_up(roll["1"]) == 80
    assert roll["5.3"] == 100.0
    # raíces: "1" (80) y "5.3" (100, huérfano) → (80+100)/2 = 90.
    assert round_half_up(compute_plan_rollup_progress(tasks)) == 90
