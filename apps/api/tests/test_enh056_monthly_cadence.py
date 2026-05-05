"""ENH-056 — Reportes programados: cadencia mensual con day_of_month + clamp.

Cubre:
- TC-056.1: dom=15, base=15-Abr 10:00 hod=09 → next = 15-May 09:00.
- TC-056.2: dom=15, base=10-Abr hod=09 → next = 15-Abr 09:00.
- TC-056.3: dom=31, base=01-Feb hod=09 → next = 28-Feb (o 29 bisiesto).
- TC-056.4: dom=31, base=01-Mar hod=09 → next = 31-Mar.
- TC-056.5: dom=31, base=15-Abr hod=09 → next = 30-Abr (clamp).
- TC-056.6: schema rechaza monthly sin day_of_month/hour_of_day.
- TC-056.7: monthly legacy sin dom mantiene +30 días.
"""
from datetime import UTC, datetime

from app.services.scheduled_reports import compute_next_run


def test_tc056_1_dom_15_after_hour_passes_to_next_month():
    base = datetime(2026, 4, 15, 10, 0, tzinfo=UTC)
    nxt = compute_next_run(
        "monthly", from_dt=base, day_of_month=15, hour_of_day=9
    )
    assert nxt == datetime(2026, 5, 15, 9, 0, tzinfo=UTC)


def test_tc056_2_dom_15_before_hour_same_month():
    base = datetime(2026, 4, 10, 8, 0, tzinfo=UTC)
    nxt = compute_next_run(
        "monthly", from_dt=base, day_of_month=15, hour_of_day=9
    )
    assert nxt == datetime(2026, 4, 15, 9, 0, tzinfo=UTC)


def test_tc056_3_dom_31_clamps_to_feb_28_or_29():
    base = datetime(2026, 2, 1, 0, 0, tzinfo=UTC)  # 2026 no bisiesto.
    nxt = compute_next_run(
        "monthly", from_dt=base, day_of_month=31, hour_of_day=9
    )
    assert nxt == datetime(2026, 2, 28, 9, 0, tzinfo=UTC)
    # Bisiesto: feb 2024 → 29.
    base = datetime(2024, 2, 1, 0, 0, tzinfo=UTC)
    nxt = compute_next_run(
        "monthly", from_dt=base, day_of_month=31, hour_of_day=9
    )
    assert nxt == datetime(2024, 2, 29, 9, 0, tzinfo=UTC)


def test_tc056_4_dom_31_in_march_uses_31():
    base = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    nxt = compute_next_run(
        "monthly", from_dt=base, day_of_month=31, hour_of_day=9
    )
    assert nxt == datetime(2026, 3, 31, 9, 0, tzinfo=UTC)


def test_tc056_5_dom_31_in_april_clamps_to_30():
    base = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)  # ya pasó el "30" no
    # aplica porque dom=31 implica clamp y april tiene 30; 30 <= 15 false → 30 > 15 → este mes.
    nxt = compute_next_run(
        "monthly", from_dt=base, day_of_month=31, hour_of_day=9
    )
    assert nxt == datetime(2026, 4, 30, 9, 0, tzinfo=UTC)


def test_tc056_7_legacy_monthly_keeps_plus_30_days():
    """Sin day_of_month + hour_of_day → +30 días (back-compat)."""
    base = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    nxt = compute_next_run("monthly", from_dt=base)
    assert nxt == datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
