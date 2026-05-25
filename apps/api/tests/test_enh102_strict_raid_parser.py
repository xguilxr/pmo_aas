"""ENH-102 — Strict A/R/D/I RAID parser + post-IA validator.

TC-300..TC-309 derived from docs/epics/drafts/minute-gold-standard.md.

These are unit tests around the validator and prompt schema; they do
not call the LLM. They exercise the validator using the canonical
``highlander-eam-bnf-20260323.expected.json`` fixture and synthetic
hallucinations to prove that non-RAID items are dropped silently.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.ai.prompts import MINUTE_SYSTEM
from app.services.ai.validator import (
    ALLOWED_RAID_TYPES,
    ALLOWED_STATUSES,
    flatten_participants,
    validate_minute_payload,
    validate_raid_items,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "minutes"
TRANSCRIPT_FILE = FIXTURE_DIR / "highlander-eam-bnf-20260323.txt"
EXPECTED_FILE = FIXTURE_DIR / "highlander-eam-bnf-20260323.expected.json"


@pytest.fixture(scope="module")
def expected_payload() -> dict:
    return json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))


def test_fixture_files_exist() -> None:
    """The Highlander fixture (transcript + expected JSON) must ship in-repo."""
    assert TRANSCRIPT_FILE.exists(), TRANSCRIPT_FILE
    assert EXPECTED_FILE.exists(), EXPECTED_FILE
    assert TRANSCRIPT_FILE.stat().st_size > 500


def test_tc300_topics_at_least_eleven(expected_payload: dict) -> None:
    """TC-300 — parser ingiere transcript Highlander con ≥ 11 temas."""
    topics = expected_payload["topics"]
    assert isinstance(topics, list)
    assert len(topics) >= 11, f"Expected ≥ 11 topics, got {len(topics)}"
    for t in topics:
        assert t["title"]
        assert isinstance(t["bullets"], list)
        assert all(isinstance(b, str) and b for b in t["bullets"])


def test_tc301_raid_distribution(expected_payload: dict) -> None:
    """TC-301 — ≥ 7 Acciones, ≥ 4 Riesgos, ≥ 4 Decisiones, ≥ 1 Issue."""
    validated, metrics = validate_minute_payload(expected_payload)
    counts = {"A": 0, "R": 0, "D": 0, "I": 0}
    for item in validated["raid"]:
        counts[item["type"]] += 1
    assert counts["A"] >= 7, counts
    assert counts["R"] >= 4, counts
    assert counts["D"] >= 4, counts
    assert counts["I"] >= 1, counts
    assert metrics["kept"] == sum(counts.values())


def test_tc302_lessons_and_changes_dropped_silently() -> None:
    """TC-302 — lessons / changes silently discarded, no error raised."""
    raid_with_garbage = [
        {"type": "A", "description": "Real acción", "responsible": "X"},
        {"type": "Lección", "description": "Hallucinated lesson"},
        {"type": "lesson", "description": "another lesson"},
        {"type": "change", "description": "scope change request"},
        {"type": "Cambio", "description": "another change"},
        {"type": "R", "description": "Real riesgo"},
        {"type": "Unknown", "description": "garbage type"},
        {"description": "missing type"},
        "not a dict",
    ]
    valid, metrics = validate_raid_items(raid_with_garbage)
    types = [item["type"] for item in valid]
    assert types == ["A", "R"]
    assert metrics["kept"] == 2
    assert metrics["dropped_lesson"] == 2
    assert metrics["dropped_change"] == 2
    assert metrics["dropped_unknown"] == 2  # "Unknown" + missing-type (empty)
    assert metrics["dropped_malformed"] >= 1  # non-dict entry


def test_tc302b_type_alias_normalization() -> None:
    """Verbose RAID type names (action / Riesgo / Decisión) get normalized."""
    items = [
        {"type": "action", "description": "a1"},
        {"type": "Riesgo", "description": "r1"},
        {"type": "Decisión", "description": "d1"},
        {"type": "Issue", "description": "i1"},
        {"kind": "A", "description": "a2"},  # legacy field name
    ]
    valid, metrics = validate_raid_items(items)
    assert [v["type"] for v in valid] == ["A", "R", "D", "I", "A"]
    assert metrics["kept"] == 5


def test_validator_default_status_open_for_invalid_status() -> None:
    items = [{"type": "A", "description": "x", "status": "NotARealStatus"}]
    valid, _ = validate_raid_items(items)
    assert valid[0]["status"] == "Open"


def test_validator_preserves_allowed_status() -> None:
    for status in ALLOWED_STATUSES:
        items = [{"type": "D", "description": "d", "status": status}]
        valid, _ = validate_raid_items(items)
        assert valid[0]["status"] == status


def test_validator_handles_non_dict_payload() -> None:
    normalized, _ = validate_minute_payload("not a payload")  # type: ignore[arg-type]
    assert normalized["header"] == {}
    assert normalized["participants"]["attendees"] == []
    assert normalized["raid"] == []


def test_prompt_advertises_strict_schema() -> None:
    """Few-shot calibration: prompt explicitly enforces A/R/D/I only."""
    assert "A/R/D/I" in MINUTE_SYSTEM or 'A (Acción)' in MINUTE_SYSTEM
    assert "Lecciones" in MINUTE_SYSTEM
    assert "Cambios" in MINUTE_SYSTEM or "cambio" in MINUTE_SYSTEM.lower()
    assert "ENH-102" in MINUTE_SYSTEM
    assert "ENH-105" in MINUTE_SYSTEM
    # Schema mentions all 6 top-level sections
    for key in ("header", "participants", "summary", "topics", "raid", "free_notes"):
        assert key in MINUTE_SYSTEM


def test_validator_allowed_types_constant() -> None:
    assert ALLOWED_RAID_TYPES == frozenset({"A", "R", "D", "I"})


def test_fixture_payload_round_trips_through_validator(expected_payload: dict) -> None:
    normalized, metrics = validate_minute_payload(expected_payload)
    assert metrics["kept"] == len(expected_payload["raid"])
    assert metrics["dropped_lesson"] == 0
    assert metrics["dropped_change"] == 0
    # All items canonical
    for item in normalized["raid"]:
        assert item["type"] in ALLOWED_RAID_TYPES


# ===== BUG-063 — dedup + speakers-only en participants =====


def test_flatten_participants_dedups_by_normalized_name() -> None:
    """El LLM a veces repite el mismo speaker con/sin acento o mayúsculas.
    flatten_participants colapsa a una sola entrada por nombre normalizado.
    """
    payload = {
        "attendees": [
            {"name": "MARÍA López", "role": "PM"},
            {"name": "maria lopez"},
            {"name": "Juan Pérez", "area": "Finanzas"},
        ],
        "absent_justified": [],
        "absent_unjustified": [],
    }
    out = flatten_participants(payload)
    names = [p["name"] for p in out]
    assert names == ["MARÍA López", "Juan Pérez"]
    # El merge no-destructivo preserva el role del primero.
    assert out[0]["role"] == "PM"


def test_flatten_participants_merges_metadata_from_duplicate() -> None:
    """Si el primer item viene sin role/area pero el duplicado los trae,
    se completan sin pisar lo existente."""
    payload = {
        "attendees": [
            {"name": "Ana García"},
            {"name": "ana garcia", "role": "Sponsor", "area": "PMO"},
        ],
    }
    out = flatten_participants(payload)
    assert len(out) == 1
    assert out[0]["role"] == "Sponsor"
    assert out[0]["area"] == "PMO"


def test_flatten_participants_dedups_flat_list_input() -> None:
    out = flatten_participants(
        [
            {"name": "David Aguilar"},
            {"name": "DAVID AGUILAR"},
            {"name": "Martin Scalia"},
        ]
    )
    assert [p["name"] for p in out] == ["David Aguilar", "Martin Scalia"]


def test_validate_minute_payload_participants_flat_is_deduped() -> None:
    payload = {
        "participants": {
            "attendees": [
                {"name": "Eli Gómora"},
                {"name": "eli gomora"},
            ],
        },
        "raid": [],
    }
    normalized, _ = validate_minute_payload(payload)
    assert len(normalized["participants_flat"]) == 1


def test_prompt_enforces_speakers_only_participants() -> None:
    """El prompt instruye a no incluir mencionados ni duplicados."""
    assert "SIN DUPLICADOS" in MINUTE_SYSTEM
    assert "MENCIONADAS" in MINUTE_SYSTEM
