"""US-190 — revisión de calidad del plan (linter).

Checks del feedback 16-jul item 4: estructura WBS, cierre de sección
con hito, actividades críticas, duraciones < 21d, fechas/responsables.
"""
from __future__ import annotations

from datetime import date

from app.models.task import Task
from app.services.plan_quality import plan_quality_score, review_plan

TODAY = date(2026, 7, 18)


def _t(id_: str, wbs_code: str | None, **kw) -> Task:
    base = {
        "id": id_, "tenant_id": "t", "project_id": "p", "name": f"Tarea {id_}",
        "wbs_code": wbs_code, "progress": 0, "is_milestone": False,
        "status": "not_started", "is_critical": False,
    }
    base.update(kw)
    return Task(**base)


def _codes(obs: list[dict]) -> set[str]:
    return {o["code"] for o in obs}


def test_empty_plan():
    obs = review_plan([], today=TODAY)
    assert _codes(obs) == {"PLAN_EMPTY"}
    assert plan_quality_score(obs) == 85


def test_healthy_plan_no_observations():
    tasks = [
        _t("a", "1", is_critical=True),
        _t("b", "1.1", start_date=date(2026, 8, 1), end_date=date(2026, 8, 10),
           duration_days=10, area_id="ar"),
        _t("m", "1.2", is_milestone=True, start_date=date(2026, 8, 11),
           end_date=date(2026, 8, 11)),
    ]
    obs = review_plan(tasks, today=TODAY)
    assert obs == []
    assert plan_quality_score(obs) == 100


def test_structure_checks():
    tasks = [
        _t("a", "1"),
        _t("b", "1.1", start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
           duration_days=5, area_id="ar"),
        _t("dup", "1.1", start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
           duration_days=5, area_id="ar"),
        _t("orph", "1.5.2", start_date=date(2026, 8, 1),
           end_date=date(2026, 8, 5), duration_days=5, area_id="ar"),
        _t("nowbs", None, start_date=date(2026, 8, 1),
           end_date=date(2026, 8, 5), duration_days=5, area_id="ar"),
        _t("m", "1.2", is_milestone=True),
    ]
    obs = review_plan(tasks, today=TODAY)
    codes = _codes(obs)
    assert "WBS_DUPLICATED" in codes
    assert "WBS_ORPHAN_LEVELS" in codes
    assert "WBS_MISSING" in codes
    assert "WBS_GAPS" in codes  # 1.5.2 implica hueco (1.3, 1.4 y 1.5.1)
    dup = next(o for o in obs if o["code"] == "WBS_DUPLICATED")
    assert dup["items"] == ["1.1"]
    assert dup["severity"] == "error"


def test_milestone_and_critical_checks():
    tasks = [
        _t("a", "1"),
        _t("b", "1.1", start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
           duration_days=5, area_id="ar"),
        _t("c", "2"),
        _t("d", "2.1", start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
           duration_days=5, area_id="ar"),
        _t("m", "1.2", is_milestone=True),
    ]
    obs = review_plan(tasks, today=TODAY)
    codes = _codes(obs)
    # Sección '2' no cierra con hito; la '1' sí.
    sec = next(o for o in obs if o["code"] == "SECTION_NO_MILESTONE")
    assert sec["items"] == ["2"]
    assert "NO_CRITICAL_TASKS" in codes
    assert "NO_MILESTONES" not in codes


def test_duration_dates_and_stale():
    tasks = [
        _t("long", "1", duration_days=45, start_date=date(2026, 8, 1),
           end_date=date(2026, 9, 15), area_id="ar", is_critical=True),
        _t("nodates", "2", area_id="ar"),
        _t("noowner", "3", start_date=date(2026, 8, 1),
           end_date=date(2026, 8, 5), duration_days=5),
        _t("stale", "4", start_date=date(2026, 6, 1), end_date=date(2026, 6, 5),
           duration_days=5, area_id="ar"),
        _t("m", "5", is_milestone=True),
    ]
    obs = review_plan(tasks, today=TODAY)
    codes = _codes(obs)
    assert {"LONG_TASKS", "MISSING_DATES", "NO_OWNER",
            "OVERDUE_NOT_STARTED"} <= codes
    long_o = next(o for o in obs if o["code"] == "LONG_TASKS")
    assert long_o["count"] == 1


def test_parent_summary_tasks_not_flagged_for_dates():
    """Los padres (resumen) no se flaggean por fechas/duración — solo
    las hojas operativas."""
    tasks = [
        _t("a", "1", duration_days=120),  # padre macro: no flag
        _t("b", "1.1", start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
           duration_days=5, area_id="ar", is_critical=True),
        _t("m", "1.2", is_milestone=True),
    ]
    obs = review_plan(tasks, today=TODAY)
    assert "LONG_TASKS" not in _codes(obs)
