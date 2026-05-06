"""BUG-049 — WBS natural sort (1.2 < 1.10)."""
from app.services.plan_metadata import wbs_sort_key


def test_natural_order_two_levels():
    items = ["1.10", "1.1", "1.2", "1.9", "1.20"]
    assert sorted(items, key=wbs_sort_key) == ["1.1", "1.2", "1.9", "1.10", "1.20"]


def test_top_level_and_nested():
    items = ["10", "2", "1.10", "1.2", "1"]
    assert sorted(items, key=wbs_sort_key) == ["1", "1.2", "1.10", "2", "10"]


def test_non_numeric_segments_go_after_numeric():
    items = ["1.2", "1.2.A", "1.2.1", "1.2.B"]
    out = sorted(items, key=wbs_sort_key)
    # Padre primero; entre hermanos del mismo prefijo, numéricos antes que alfabéticos.
    assert out[0] == "1.2"
    assert out[1] == "1.2.1"
    assert out[2:] == ["1.2.A", "1.2.B"]


def test_none_and_empty_go_last():
    items = ["1.2", "", None, "1.1"]
    out = sorted(items, key=wbs_sort_key)
    assert out[:2] == ["1.1", "1.2"]
    assert set(out[2:]) == {"", None}
