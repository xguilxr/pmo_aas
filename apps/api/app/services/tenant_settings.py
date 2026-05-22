"""Tenant-level settings accessors (ENH-099).

Shape canónico de ``tenants.settings.report_builder``::

    {
      "report_builder": {
        "task_load_thresholds": {
            "green_max": int,  # tareas <= green_max  -> verde
            "amber_max": int,  # green_max < tareas <= amber_max -> ámbar
                               # tareas > amber_max  -> rojo
        }
      }
    }

Default cuando la clave no existe: ``{"green_max": 5, "amber_max": 10}``.

Este módulo expone helpers puros (sin DB) que consultan/escriben sobre
un objeto ``Tenant`` ya cargado. EP020 (Report Builder) consumirá
``get_task_load_thresholds`` para colorear la carga de tareas por
recurso al renderizar reportes.

Nota: el sibling worker ENH-098 también agrega claves bajo
``settings.report_builder``; cada PR usa una sub-clave independiente
(``progress_calculation_method`` vs ``task_load_thresholds``), por lo
que la segunda en mergear simplemente añade su función a este módulo.
"""

from __future__ import annotations

from typing import Any

from app.models.tenant import Tenant

# ---- task_load_thresholds (ENH-099) ----

DEFAULT_TASK_LOAD_THRESHOLDS: dict[str, int] = {"green_max": 5, "amber_max": 10}


def _report_builder_block(tenant: Tenant) -> dict[str, Any]:
    """Return the ``report_builder`` sub-dict (read-only view)."""
    settings = tenant.settings or {}
    rb = settings.get("report_builder")
    return rb if isinstance(rb, dict) else {}


def get_task_load_thresholds(tenant: Tenant) -> dict[str, int]:
    """Resolve per-tenant resource-load colorization thresholds.

    Reads ``tenant.settings["report_builder"]["task_load_thresholds"]``
    and returns a normalized ``{"green_max": int, "amber_max": int}``
    dict. Falls back to :data:`DEFAULT_TASK_LOAD_THRESHOLDS` when the
    block is absent or malformed. The returned dict is a fresh copy and
    safe for the caller to mutate.
    """
    rb = _report_builder_block(tenant)
    raw = rb.get("task_load_thresholds")
    if not isinstance(raw, dict):
        return dict(DEFAULT_TASK_LOAD_THRESHOLDS)
    try:
        green_max = int(raw.get("green_max", DEFAULT_TASK_LOAD_THRESHOLDS["green_max"]))
        amber_max = int(raw.get("amber_max", DEFAULT_TASK_LOAD_THRESHOLDS["amber_max"]))
    except (TypeError, ValueError):
        return dict(DEFAULT_TASK_LOAD_THRESHOLDS)
    return {"green_max": green_max, "amber_max": amber_max}


def validate_task_load_thresholds(green_max: int, amber_max: int) -> None:
    """Raise :class:`ValueError` if the threshold pair is invalid.

    Both values must be positive ints and ``green_max < amber_max``.
    """
    if isinstance(green_max, bool) or not isinstance(green_max, int):
        raise ValueError("green_max debe ser un entero")
    if isinstance(amber_max, bool) or not isinstance(amber_max, int):
        raise ValueError("amber_max debe ser un entero")
    if green_max <= 0 or amber_max <= 0:
        raise ValueError("Los umbrales deben ser positivos")
    if green_max >= amber_max:
        raise ValueError("green_max debe ser menor que amber_max")


def set_task_load_thresholds(
    tenant: Tenant, green_max: int, amber_max: int
) -> dict[str, Any]:
    """Persist task-load thresholds on the tenant settings dict.

    Validates the pair (positive ints with ``green_max < amber_max``) and
    returns the merged ``tenant.settings`` (also assigned on the model).
    Raises :class:`ValueError` on invalid input.
    """
    validate_task_load_thresholds(green_max, amber_max)
    merged = dict(tenant.settings or {})
    rb = dict(merged.get("report_builder") or {})
    rb["task_load_thresholds"] = {"green_max": green_max, "amber_max": amber_max}
    merged["report_builder"] = rb
    tenant.settings = merged
    return merged
