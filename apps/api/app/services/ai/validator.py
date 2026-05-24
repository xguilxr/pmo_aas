"""ENH-102 — Post-IA validator for minute parsing.

The IA can hallucinate item types beyond the canonical RAID set
(Acciones, Riesgos, Decisiones, Issues). This module enforces the
strict A/R/D/I schema by silently discarding non-canonical items and
logging counters for observability.

Also normalizes the shape of a minute JSON to the 6-section structure
expected by ENH-105 downstream consumers.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_RAID_TYPES: frozenset[str] = frozenset({"A", "R", "D", "I"})
ALLOWED_STATUSES: frozenset[str] = frozenset({"Open", "In Progress", "Pending", "Closed"})

# Map verbose type names (legacy / IA hallucination) to canonical letters
# (only when the verbose name itself maps to a valid RAID type).
_TYPE_ALIASES: dict[str, str] = {
    "action": "A", "acción": "A", "accion": "A", "a": "A",
    "risk": "R", "riesgo": "R", "r": "R",
    "decision": "D", "decisión": "D", "d": "D",
    "issue": "I", "incident": "I", "i": "I",
    # Explicit DROP set — anything mapping here is silently discarded
    # ("lesson", "lección", "change", "cambio").
}

_DISCARD_TYPES: frozenset[str] = frozenset({
    "lesson", "lección", "leccion", "lessons_learned",
    "change", "cambio", "change_request",
    "l", "c",
})


def _coerce_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    key = value.strip().lower()
    if key in _DISCARD_TYPES:
        return None
    if key in _TYPE_ALIASES:
        return _TYPE_ALIASES[key]
    # Already-canonical uppercase letter
    upper = value.strip().upper()
    if upper in ALLOWED_RAID_TYPES:
        return upper
    return None


def validate_raid_items(items: list[Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Filter a RAID array to canonical A/R/D/I items.

    Returns ``(valid_items, metrics)`` where ``metrics`` is a counter
    dict (``kept``, ``dropped_lesson``, ``dropped_change``,
    ``dropped_unknown``, ``dropped_malformed``).
    """
    metrics = {
        "kept": 0,
        "dropped_lesson": 0,
        "dropped_change": 0,
        "dropped_unknown": 0,
        "dropped_malformed": 0,
    }
    valid: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return valid, metrics
    for raw in items:
        if not isinstance(raw, dict):
            metrics["dropped_malformed"] += 1
            continue
        raw_type = raw.get("type") or raw.get("kind") or ""
        canonical = _coerce_type(raw_type)
        if canonical is None:
            key = str(raw_type).strip().lower()
            if key in {"lesson", "lección", "leccion", "lessons_learned", "l"}:
                metrics["dropped_lesson"] += 1
            elif key in {"change", "cambio", "change_request", "c"}:
                metrics["dropped_change"] += 1
            else:
                metrics["dropped_unknown"] += 1
            continue
        description = (raw.get("description") or raw.get("short_desc") or "").strip()
        if not description:
            metrics["dropped_malformed"] += 1
            continue
        status = raw.get("status") or "Open"
        if status not in ALLOWED_STATUSES:
            status = "Open"
        valid.append({
            "type": canonical,
            "description": description,
            "responsible": (raw.get("responsible") or raw.get("owner") or "").strip() or None,
            "due_date": raw.get("due_date"),
            "status": status,
        })
        metrics["kept"] += 1

    dropped_total = (
        metrics["dropped_lesson"]
        + metrics["dropped_change"]
        + metrics["dropped_unknown"]
        + metrics["dropped_malformed"]
    )
    if dropped_total:
        logger.info(
            "minute.validator.raid_dropped",
            extra={
                "kept": metrics["kept"],
                "dropped_lesson": metrics["dropped_lesson"],
                "dropped_change": metrics["dropped_change"],
                "dropped_unknown": metrics["dropped_unknown"],
                "dropped_malformed": metrics["dropped_malformed"],
            },
        )
    return valid, metrics


def flatten_participants(payload: Any) -> list[dict[str, Any]]:
    """Aplana el dict de participantes del LLM a una lista plana de dicts.

    El prompt pide ``{attendees, absent_justified, absent_unjustified}`` pero
    la minuta persistida usa una lista plana. Cada item conserva
    ``name``/``role``/``area`` y se le agrega ``attendance`` con uno de
    ``attended``/``absent_justified``/``absent_unjustified``.

    Tolera:
    - ``dict`` con las 3 keys canónicas.
    - ``list`` directa (asume todos attendees).
    - ``None`` u otros tipos → retorna lista vacía.
    """
    if isinstance(payload, list):
        return [
            {**p, "attendance": p.get("attendance") or "attended"}
            for p in payload
            if isinstance(p, dict) and (p.get("name") or "").strip()
        ]
    if not isinstance(payload, dict):
        return []
    out: list[dict[str, Any]] = []
    for status_key in ("attendees", "absent_justified", "absent_unjustified"):
        bucket = payload.get(status_key) or []
        if not isinstance(bucket, list):
            continue
        attendance = "attended" if status_key == "attendees" else status_key
        for raw in bucket:
            if not isinstance(raw, dict):
                continue
            name = (raw.get("name") or "").strip()
            if not name:
                continue
            out.append({**raw, "attendance": attendance})
    return out


# Mapping de tipos A/R/D/I canónicos al bucket persistible. Usamos los
# 4 nombres canónicos del RAID en lugar del legacy
# ``{risks, issues, lessons, changes}``: A→actions, R→risks, D→decisions,
# I→issues. Lecciones y cambios fueron descartados del modelo (owner
# 2026-05-22) — si el LLM los emite los filtra el validator.
RAID_TYPE_TO_BUCKET: dict[str, str] = {
    "A": "actions",
    "R": "risks",
    "D": "decisions",
    "I": "issues",
}


def raid_suggestions_from_flat(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Convierte la lista flat A/R/D/I del LLM al shape de buckets
    persistible en ``MeetingMinute.raid_suggestions``.

    Cada item del LLM ``{type, description, responsible, due_date, status}``
    se mapea al shape de sugerencia
    ``{short_desc, suggested_owner_name, suggested_due_date, raw_quote,
    status: "pending", ticket_id: null, ticket_type: null}``.

    Los items sin ``description`` se descartan. ``status`` de la sugerencia
    siempre es ``pending`` hasta que el PM la apruebe/descarte.
    """
    out: dict[str, list[dict[str, Any]]] = {
        "actions": [], "risks": [], "decisions": [], "issues": [],
    }
    for raw in items:
        if not isinstance(raw, dict):
            continue
        type_letter = (raw.get("type") or "").strip().upper()
        bucket = RAID_TYPE_TO_BUCKET.get(type_letter)
        if not bucket:
            continue
        desc = (raw.get("description") or "").strip()
        if not desc:
            continue
        out[bucket].append({
            "short_desc": desc,
            "suggested_owner_name": (raw.get("responsible") or None) or None,
            "suggested_due_date": raw.get("due_date") or None,
            "suggested_priority": None,
            "raw_quote": raw.get("raw_quote") or None,
            "status": "pending",
            "ticket_id": None,
            "ticket_type": None,
        })
    return out


def validate_minute_payload(payload: Any) -> tuple[dict[str, Any], dict[str, int]]:
    """Coerce a minute JSON payload to the canonical 6-section shape.

    Missing sections are filled with empty defaults. RAID items are
    filtered via :func:`validate_raid_items`. The returned payload es
    safe to feed to the formatter (ENH-105).

    Output shape:
        - ``header``: dict (raw del LLM).
        - ``participants``: dict ``{attendees, absent_justified,
          absent_unjustified}`` (raw del LLM normalizado).
        - ``participants_flat``: list plana de ``{name, role?, area?,
          attendance}`` lista para persistir en ``MeetingMinute.participants``.
        - ``summary``, ``topics``, ``free_notes``: pass-through.
        - ``raid``: list plana ``[{type:A|R|D|I, description, ...}]``
          (validada).
        - ``raid_suggestions``: dict ``{actions, risks, decisions,
          issues}`` listo para ``MeetingMinute.raid_suggestions``.
    """
    if not isinstance(payload, dict):
        payload = {}
    header = payload.get("header") if isinstance(payload.get("header"), dict) else {}
    participants_raw = payload.get("participants")
    if isinstance(participants_raw, dict):
        participants = {
            "attendees": participants_raw.get("attendees") or [],
            "absent_justified": participants_raw.get("absent_justified") or [],
            "absent_unjustified": participants_raw.get("absent_unjustified") or [],
        }
    elif isinstance(participants_raw, list):
        participants = {
            "attendees": participants_raw,
            "absent_justified": [],
            "absent_unjustified": [],
        }
    else:
        participants = {"attendees": [], "absent_justified": [], "absent_unjustified": []}

    topics = payload.get("topics") if isinstance(payload.get("topics"), list) else []
    raid_items, metrics = validate_raid_items(payload.get("raid") or [])
    summary = payload.get("summary") or ""
    free_notes = payload.get("free_notes")

    normalized = {
        "header": header,
        "participants": participants,
        "participants_flat": flatten_participants(participants_raw),
        "summary": summary,
        "topics": topics,
        "raid": raid_items,
        "raid_suggestions": raid_suggestions_from_flat(raid_items),
        "free_notes": free_notes,
    }
    return normalized, metrics
