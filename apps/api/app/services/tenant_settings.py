"""Tenant-level settings accessors (ENH-098 + ENH-099).

Shape canónico de ``tenants.settings.report_builder``::

    {
      "report_builder": {
        "progress_calculation_method":
            "by_task_count" | "by_duration" | "by_effort",
        "task_load_thresholds": {
            "green_max": int,  # tareas <= green_max  -> verde
            "amber_max": int,  # green_max < tareas <= amber_max -> ámbar
                               # tareas > amber_max  -> rojo
        }
      }
    }

Defaults cuando la clave no existe:
- ``progress_calculation_method`` → ``"by_task_count"``
- ``task_load_thresholds`` → ``{"green_max": 5, "amber_max": 10}``

Además, ``tenants.settings.org_label`` (top-level, ENH-190) controla el
label de UI para "Organización/Organizaciones": ``"organizations"``
(default) o ``"portfolios"``. Es puramente cosmético — no cambia
schema, rutas ni tipos de entidad.

Este módulo expone helpers puros (sin DB) que consultan/escriben sobre
un objeto ``Tenant`` ya cargado. EP020 (Report Builder) consumirá estos
accessors al renderizar reportes.
"""
from __future__ import annotations

from typing import Any

from app.models.tenant import Tenant

# ---- progress_calculation_method (ENH-098) ----

PROGRESS_CALC_METHODS: tuple[str, ...] = (
    "by_task_count",
    "by_duration",
    "by_effort",
)
DEFAULT_PROGRESS_CALC_METHOD: str = "by_task_count"

# ---- task_load_thresholds (ENH-099) ----

DEFAULT_TASK_LOAD_THRESHOLDS: dict[str, int] = {"green_max": 5, "amber_max": 10}


def _report_builder_block(tenant: Tenant) -> dict[str, Any]:
    """Return the ``report_builder`` sub-dict (read-only view)."""
    settings = tenant.settings or {}
    rb = settings.get("report_builder")
    return rb if isinstance(rb, dict) else {}


def get_progress_calculation_method(tenant: Tenant) -> str:
    """Resolve the per-tenant progress calculation method.

    Returns the configured value if it is one of
    :data:`PROGRESS_CALC_METHODS`; otherwise returns
    :data:`DEFAULT_PROGRESS_CALC_METHOD`.
    """
    rb = _report_builder_block(tenant)
    val = rb.get("progress_calculation_method")
    if isinstance(val, str) and val in PROGRESS_CALC_METHODS:
        return val
    return DEFAULT_PROGRESS_CALC_METHOD


def set_progress_calculation_method(tenant: Tenant, value: str) -> dict[str, Any]:
    """Persist the progress calculation method on the tenant settings dict.

    Returns the merged ``tenant.settings`` (also assigned on the model).
    Raises :class:`ValueError` if ``value`` is not in
    :data:`PROGRESS_CALC_METHODS`.
    """
    if value not in PROGRESS_CALC_METHODS:
        raise ValueError(
            f"invalid progress_calculation_method: {value!r}; "
            f"expected one of {PROGRESS_CALC_METHODS}"
        )
    merged = dict(tenant.settings or {})
    rb = dict(merged.get("report_builder") or {})
    rb["progress_calculation_method"] = value
    merged["report_builder"] = rb
    tenant.settings = merged
    return merged


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


# ---- org_label (ENH-190) ----
#
# Shape canónico: ``tenants.settings.org_label`` (top-level, no anidado
# bajo ``report_builder`` — es un label de UI, no una config del Report
# Builder). Solo afecta textos visibles en el frontend; cero cambios de
# schema/rutas/APIs (las entidades siguen siendo "organizations" en DB
# y URLs).
ORG_LABEL_VALUES: tuple[str, ...] = ("organizations", "portfolios")
DEFAULT_ORG_LABEL: str = "organizations"


def get_org_label(tenant: Tenant) -> str:
    """Resolve the per-tenant UI label for "Organización/Organizaciones".

    Returns the configured value if it is one of :data:`ORG_LABEL_VALUES`
    ("organizations" | "portfolios"); otherwise returns
    :data:`DEFAULT_ORG_LABEL`.
    """
    settings = tenant.settings or {}
    val = settings.get("org_label")
    if isinstance(val, str) and val in ORG_LABEL_VALUES:
        return val
    return DEFAULT_ORG_LABEL


def set_org_label(tenant: Tenant, value: str) -> dict[str, Any]:
    """Persist the org_label on the tenant settings dict.

    Returns the merged ``tenant.settings`` (also assigned on the model).
    Raises :class:`ValueError` if ``value`` is not in
    :data:`ORG_LABEL_VALUES`.
    """
    if value not in ORG_LABEL_VALUES:
        raise ValueError(
            f"invalid org_label: {value!r}; expected one of {ORG_LABEL_VALUES}"
        )
    merged = dict(tenant.settings or {})
    merged["org_label"] = value
    tenant.settings = merged
    return merged
