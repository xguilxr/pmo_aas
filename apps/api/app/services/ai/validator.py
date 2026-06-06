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


def _coerce_text(value: Any) -> str:
    """Coerce a free-text field to a plain string.

    The IA occasionally returns ``summary`` as a nested object
    (``{"text": "..."}``, ``{"overview": "...", ...}``) or a list of
    fragments instead of a plain string. Downstream consumers join this
    field with ``str.join`` (minute merge across chunks in
    :mod:`app.workers.tasks.ai`), which raises ``TypeError: sequence item
    0: expected str instance, dict found`` on a dict/list. This flattens
    any such shape to a string, returning ``""`` when there's nothing
    usable.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Only keys that unambiguously mean "the whole text" short-circuit;
        # anything else (overview + detail, bilingual, etc.) is concatenated
        # so no content is dropped.
        for key in ("text", "summary", "content", "body"):
            inner = value.get(key)
            if isinstance(inner, str) and inner.strip():
                return inner
        parts = [_coerce_text(v) for v in value.values()]
        return "\n\n".join(p for p in parts if p.strip())
    if isinstance(value, (list, tuple)):
        parts = [_coerce_text(v) for v in value]
        return "\n\n".join(p for p in parts if p.strip())
    return str(value)


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
        # ENH-147 — amplía las claves aceptadas para no descartar items que
        # el modelo nombró con title/text/detail/summary en vez de description.
        description = (
            raw.get("description")
            or raw.get("short_desc")
            or raw.get("text")
            or raw.get("title")
            or raw.get("detail")
            or raw.get("summary")
            or ""
        ).strip()
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


def _normalize_name(name: str | None) -> str:
    """Lowercase + trim + strip diacritics para deduplicar nombres que
    difieren solo en acentos/mayúsculas ("MARÍA López" == "maria lopez")."""
    import unicodedata

    raw = (name or "").strip().lower()
    nfd = unicodedata.normalize("NFD", raw)
    return "".join(ch for ch in nfd if not unicodedata.combining(ch))


# BUG-068: el LLM puede devolver header.date en cualquier formato
# ("01/06/2026", "1 de junio", "2026-06-01"). El frontend hace
# new Date(`${date}T12:00:00`).toISOString(), que crashea con
# RangeError si el string no es ISO. Normalizamos aquí a YYYY-MM-DD
# o null cuando no es parseable.
_DATE_FORMATS_TRIED = (
    "%Y-%m-%d",
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%Y/%m/%d",
    "%d/%m/%y", "%d-%m-%y",
)


def _normalize_iso_date(value: Any) -> str | None:
    """Devuelve fecha en formato `YYYY-MM-DD` o `None` si no se puede
    interpretar. Acepta strings ISO, formatos comunes es-MX/en-US, y
    cualquier prefijo `YYYY-MM-DD` (e.g. timestamps ISO completos).
    Nombres de mes en lenguaje natural devuelven `None` (mejor que
    adivinar)."""
    from datetime import date, datetime

    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    # Caso fast-path: ISO completo o prefijo ISO.
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS_TRIED:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def merge_topics(items: list[Any]) -> list[dict[str, Any]]:
    """Fusiona topics con el mismo título normalizado preservando orden.
    Los `bullets` de las repeticiones se concatenan al primero,
    descartando duplicados textuales (lowercase + strip).

    BUG-070: cuando el transcript se divide en chunks con overlap, el
    mismo tema puede ser extraído por varios chunks (ej. "Alcance del
    Proyecto" aparece 3 veces). Aquí los unificamos en un único topic
    con bullets combinados.
    """
    import unicodedata

    def _key(title: Any) -> str:
        raw = str(title or "").strip().lower()
        nfd = unicodedata.normalize("NFD", raw)
        return "".join(ch for ch in nfd if not unicodedata.combining(ch))

    out: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for raw in items:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        if not title:
            continue
        key = _key(title)
        bullets_raw = raw.get("bullets") if isinstance(raw.get("bullets"), list) else []
        bullets = [str(b).strip() for b in bullets_raw if str(b).strip()]
        if key in seen:
            target = out[seen[key]]
            existing_norm = {b.strip().lower() for b in target["bullets"]}
            for b in bullets:
                if b.strip().lower() not in existing_norm:
                    target["bullets"].append(b)
                    existing_norm.add(b.strip().lower())
            continue
        seen[key] = len(out)
        out.append({"title": title, "bullets": list(bullets)})
    return out


def dedupe_participants(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedup por nombre normalizado preservando orden de aparición. Si
    una repetición trae role/area/email no vacíos y el primero los tenía
    vacíos, se completan (merge no destructivo).

    BUG-069: usado tanto por `flatten_participants` (dentro de un chunk)
    como por el merge cross-chunk del worker, donde cada chunk del
    transcript puede mencionar al mismo participante.
    """
    out: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = _normalize_name(item.get("name"))
        if not key:
            continue
        if key in seen:
            existing = out[seen[key]]
            for field in ("role", "area", "email"):
                if not (existing.get(field) or "").strip() and (item.get(field) or "").strip():
                    existing[field] = item[field]
            continue
        seen[key] = len(out)
        out.append(dict(item))
    return out


def flatten_participants(payload: Any) -> list[dict[str, Any]]:
    """Aplana el dict de participantes del LLM a una lista plana de dicts,
    **deduplicada por nombre normalizado**.

    El prompt pide ``{attendees, absent_justified, absent_unjustified}`` pero
    la minuta persistida usa una lista plana. Cada item conserva
    ``name``/``role``/``area`` y se le agrega ``attendance`` con uno de
    ``attended``/``absent_justified``/``absent_unjustified``.

    BUG-063 (feedback owner): el LLM a veces lista el mismo participante
    dos veces (con/sin acento, alias) o agrega personas solo mencionadas.
    Aquí garantizamos una sola entrada por nombre normalizado — la primera
    aparición gana, y si una repetición trae más metadata (role/area) se
    fusiona sin pisar lo ya capturado.

    Tolera:
    - ``dict`` con las 3 keys canónicas.
    - ``list`` directa (asume todos attendees).
    - ``None`` u otros tipos → retorna lista vacía.
    """
    raw_items: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for p in payload:
            if isinstance(p, dict) and (p.get("name") or "").strip():
                raw_items.append({**p, "attendance": p.get("attendance") or "attended"})
    elif isinstance(payload, dict):
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
                raw_items.append({**raw, "attendance": attendance})

    return dedupe_participants(raw_items)


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
    # BUG-068: normaliza header.date a YYYY-MM-DD para que el frontend
    # pueda hacer new Date(...).toISOString() sin crashear. Si el LLM
    # devolvió algo no parseable (ej. "1 de junio"), queda None y el
    # frontend cae a "hoy" por default.
    if header:
        header = {**header, "date": _normalize_iso_date(header.get("date"))}
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
    # BUG-073 — la IA a veces devuelve summary como dict/list; coercionar a
    # str para que el merge cross-chunk (str.join) no reviente.
    summary = _coerce_text(payload.get("summary"))
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
