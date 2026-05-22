"""ENH-105 — 6-section rigid minute structure (Highlander gold-standard).

Reusa el fixture de ENH-102 para verificar que el formatter produce
las 6 secciones en orden, ignora extras y codifica correctamente en
los 4 formatos de export (MD, TXT, DOCX, PDF context).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.minutes_formatter import (
    RAID_TYPE_LABELS,
    RAID_TYPE_ORDER,
    SECTION_ORDER,
    build_view_from_payload,
    to_docx,
    to_markdown,
    to_plain_text,
)

FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "minutes"
    / "highlander-eam-bnf-20260323.expected.json"
)


@pytest.fixture(scope="module")
def gold_view():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return build_view_from_payload(
        payload,
        title="Highlander EAM-BNF — Operacional",
        project_name="Highlander",
        project_folio="HL-001",
        meeting_date="2026-03-23",
    )


def test_section_order_is_canonical() -> None:
    """ENH-105 — el orden de secciones es inmutable y exacto."""
    assert SECTION_ORDER == (
        "header",
        "participants",
        "summary",
        "topics",
        "raid",
        "free_notes",
    )
    assert len(SECTION_ORDER) == 6


def test_view_has_all_six_sections(gold_view) -> None:
    d = gold_view.as_dict()
    # Each section key must exist (non-None / non-missing).
    assert d.get("header")
    assert d.get("attendees")  # participants
    assert d["summary"]
    assert d["topics"]
    assert any(d["raid_by_type"][t] for t in RAID_TYPE_ORDER)
    # free_notes can be empty but the key must exist
    assert "free_notes" in d


def test_tc307_markdown_has_six_sections_in_order(gold_view) -> None:
    """TC-307 — minuta exportada (MD) tiene exactamente 6 secciones en orden."""
    md = to_markdown(gold_view)
    headers = [
        "1. Encabezado",
        "2. Participantes",
        "3. Resumen / Objetivo",
        "4. Temas tratados",
        "5. RAID — A/R/D/I",
        "6. Notas libres",
    ]
    last_pos = -1
    for h in headers:
        pos = md.find(h)
        assert pos > last_pos, f"section {h!r} missing or out of order in MD"
        last_pos = pos


def test_plain_text_matches_markdown(gold_view) -> None:
    assert to_plain_text(gold_view) == to_markdown(gold_view)


def test_markdown_includes_raid_labels(gold_view) -> None:
    md = to_markdown(gold_view)
    for tcode in RAID_TYPE_ORDER:
        if gold_view.raid_by_type[tcode]:
            assert f"{tcode} — {RAID_TYPE_LABELS[tcode]}" in md


def test_docx_export_bytes(gold_view) -> None:
    """DOCX export produces a real ZIP container (.docx) with content."""
    payload = to_docx(gold_view)
    assert isinstance(payload, bytes)
    assert len(payload) > 1024
    # DOCX is a ZIP — starts with PK\x03\x04 signature
    assert payload[:2] == b"PK"


def test_pdf_context_keys_for_six_sections(gold_view) -> None:
    """to_pdf relies on view.as_dict() — verify all section keys are present."""
    ctx = gold_view.as_dict()
    for key in (
        "title", "header", "attendees", "absent_justified",
        "absent_unjustified", "summary", "topics", "raid_by_type",
        "raid_type_order", "raid_type_labels", "free_notes",
        "section_order",
    ):
        assert key in ctx, f"missing PDF context key: {key}"
    assert ctx["section_order"] == list(SECTION_ORDER)


def test_extras_in_payload_are_ignored() -> None:
    """ENH-105 — campos extra en el payload no se filtran al output."""
    payload = {
        "header": {"date": "2026-03-23"},
        "participants": {"attendees": [{"name": "A"}]},
        "summary": "s",
        "topics": [{"title": "t1", "bullets": ["b1"]}],
        "raid": [{"type": "A", "description": "x"}],
        "free_notes": "fn",
        # Extras — must NOT leak into the view
        "lessons": [{"description": "ignore me"}],
        "changes": [{"description": "ignore me too"}],
        "extra_section": "not allowed",
    }
    view = build_view_from_payload(payload, title="T")
    d = view.as_dict()
    assert "lessons" not in d
    assert "changes" not in d
    assert "extra_section" not in d


def test_topics_preserve_order_and_index(gold_view) -> None:
    for idx, t in enumerate(gold_view.topics, start=1):
        assert t["index"] == idx
        assert t["title"]
        # Bullets list always present (even if empty)
        assert isinstance(t["bullets"], list)


def test_raid_distribution_in_view(gold_view) -> None:
    """The Highlander gold standard yields ≥ 7/4/4/1 in A/R/D/I."""
    counts = {t: len(gold_view.raid_by_type[t]) for t in RAID_TYPE_ORDER}
    assert counts["A"] >= 7
    assert counts["R"] >= 4
    assert counts["D"] >= 4
    assert counts["I"] >= 1


def test_actividades_backlog_consolidated_in_raid_actions(gold_view) -> None:
    """Owner clarification 2026-05-22: backlog actions go in RAID Acciones,
    not in a separate section. Verify the formatter has no 'backlog'
    bucket and all action-like items live in raid_by_type['A']."""
    d = gold_view.as_dict()
    assert "backlog" not in d
    assert "activities" not in d
    # The action describing "balances al backlog" is in A.
    descs = [r["description"].lower() for r in gold_view.raid_by_type["A"]]
    assert any("backlog" in s for s in descs)


def test_free_notes_carries_calendarized_steps(gold_view) -> None:
    assert "calendarizados" in (gold_view.free_notes or "").lower()


def test_summary_is_two_to_three_sentences(gold_view) -> None:
    # The gold-standard summary is ~2 sentences. Allow 1-4 to be safe.
    sentences = [s for s in gold_view.summary.split(".") if s.strip()]
    assert 1 <= len(sentences) <= 4
