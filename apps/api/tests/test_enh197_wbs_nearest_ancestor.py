"""ENH-197 — jerarquía WBS por ancestro existente más cercano.

Feedback cliente 16-jul item 3: "todos los que inicien con 1.x deben
ser hijos de 1". Antes el rollup solo colgaba hijos de su padre
DIRECTO: '1.30.1' sin fila '1.30' quedaba como raíz suelta (avance de
'1' no la incluía y el promedio general se distorsionaba).
"""
from __future__ import annotations

from app.models.task import Task
from app.services.plan_metadata import (
    compute_plan_rollup_progress,
    compute_wbs_rollup,
    nearest_ancestor_wbs,
)


def _t(id_: str, wbs: str | None, progress: int = 0) -> Task:
    return Task(
        id=id_, tenant_id="t", project_id="p", name=id_, wbs=wbs,
        progress=progress, is_milestone=False, status="not_started",
    )


def test_nearest_ancestor():
    s = {"1", "1.30", "2"}
    assert nearest_ancestor_wbs("1.30.1", s) == "1.30"
    assert nearest_ancestor_wbs("1.29.5", s) == "1"  # sin '1.29' → sube a '1'
    assert nearest_ancestor_wbs("3.1", s) is None
    assert nearest_ancestor_wbs("1", s) is None
    assert nearest_ancestor_wbs(None, s) is None


def test_rollup_attaches_orphans_to_grandparent():
    """'1.30.1'/'1.30.2' sin fila '1.30' cuelgan de '1' — el avance de
    '1' es el promedio de TODO lo que empieza con 1.x."""
    tasks = [
        _t("a", "1"),
        _t("b", "1.30.1", 100),
        _t("c", "1.30.2", 50),
    ]
    rollup = compute_wbs_rollup(tasks)
    assert rollup["a"] == 75.0  # (100 + 50) / 2
    # Avance general: única raíz es '1'.
    assert compute_plan_rollup_progress(tasks) == 75.0


def test_rollup_direct_parent_still_wins():
    """Con el nivel intermedio presente, la jerarquía normal se
    mantiene (hijo → padre directo, no salta al abuelo)."""
    tasks = [
        _t("a", "1"),
        _t("m", "1.30"),
        _t("b", "1.30.1", 100),
        _t("c", "1.30.2", 0),
    ]
    rollup = compute_wbs_rollup(tasks)
    assert rollup["m"] == 50.0
    assert rollup["a"] == 50.0  # único hijo efectivo de '1' es '1.30'


def test_roots_without_any_ancestor():
    tasks = [_t("a", "1.1", 40), _t("b", "2.9", 80)]
    # Sin '1' ni '2': ambas son raíces.
    assert compute_plan_rollup_progress(tasks) == 60.0
