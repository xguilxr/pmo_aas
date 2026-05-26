"""US-158 — secciones de reporte S-05 (tendencia) y S-15 (matriz de riesgos)."""
from datetime import date
from types import SimpleNamespace

from app.services.reports.engine import (
    _build_s05_trends,
    _build_s15_risk_matrix,
    _RenderContext,
    get_section_builder,
)


def _ctx(**kw) -> _RenderContext:
    base = {
        "project": None,
        "organization_name": None,
        "program_name": None,
        "pm_name": None,
        "tenant_name": None,
    }
    base.update(kw)
    return _RenderContext(**base)


def _risk(p, i, status="identified"):
    return SimpleNamespace(probability=p, impact=i, status=status)


def _snap(day, avg, risks=0):
    return SimpleNamespace(
        snapshot_date=date(2026, 5, day), avg_progress=avg, open_risks=risks
    )


def test_sections_registered():
    assert get_section_builder("S-05") is _build_s05_trends
    assert get_section_builder("S-15") is _build_s15_risk_matrix


def test_s15_risk_matrix_counts_and_zones():
    ctx = _ctx(
        risks=[
            _risk(5, 4),
            _risk(5, 4),
            _risk(1, 1),
            _risk(3, 3, status="closed"),  # excluido
            _risk(None, 2),  # sin prob → no posicionado
        ]
    )
    out = _build_s15_risk_matrix(ctx, {}, None)
    assert out["total"] == 3
    row5 = next(r for r in out["matrix"] if r["probability"] == 5)
    c54 = next(c for c in row5["cells"] if c["impact"] == 4)
    assert c54["count"] == 2
    assert c54["zone"] == "high"  # sev 20 > 12
    row1 = next(r for r in out["matrix"] if r["probability"] == 1)
    c11 = next(c for c in row1["cells"] if c["impact"] == 1)
    assert c11["zone"] == "low"  # sev 1
    assert c11["count"] == 1


def test_s05_trends_series():
    ctx = _ctx(snapshots=[_snap(1, 10), _snap(8, 30), _snap(15, 55)])
    out = _build_s05_trends(ctx, {"metric": "avg_progress"}, None)
    assert out["empty"] is False
    assert len(out["points"]) == 3
    assert out["last"] == 55
    assert out["first"] == 10
    assert out["delta"] == 45
    assert out["svg"].startswith("<svg")
    assert out["metric_label"]


def test_s05_trends_empty():
    out = _build_s05_trends(_ctx(snapshots=[]), {}, None)
    assert out["empty"] is True
    assert out["svg"] == ""


def test_s05_trends_invalid_metric_falls_back():
    out = _build_s05_trends(_ctx(snapshots=[_snap(1, 10)]), {"metric": "bogus"}, None)
    assert out["metric"] == "avg_progress"
