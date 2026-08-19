"""Tenant-level settings accessors (ENH-098 + ENH-099).

Shape canónico de ``tenants.settings.report_builder``::

    {
      "report_builder": {
        "progress_calculation_method":
            "by_task_count" | "by_duration" | "by_effort",
        "task_load_thresholds": {
            "green_max": int,  # tareas <= green_max  -> verde
            "yellow_max": int,  # green_max < tareas <= yellow_max -> amarillo
                                # tareas > yellow_max  -> rojo
        }
      }
    }

Defaults cuando la clave no existe:
- ``progress_calculation_method`` → ``"by_task_count"``
- ``task_load_thresholds`` → ``{"green_max": 5, "yellow_max": 10}``

ENH-190 vivía aquí: ``tenants.settings.org_label`` permitía renombrar
"Organización" a "Portafolio" en la interfaz. Se retiró en DEC-032 —
Portafolio pasó a ser una entidad **hija** de la organización (ADR-037) y el
label dejaba dos niveles adyacentes con el mismo nombre. La migración 0111
borra la clave.

Este módulo expone helpers puros (sin DB) que consultan/escriben sobre
un objeto ``Tenant`` ya cargado. EP020 (Report Builder) consumirá estos
accessors al renderizar reportes.
"""
from __future__ import annotations

from typing import Any

from app.core.compatibilidad import registrar_uso
from app.models.tenant import Tenant

# ---- progress_calculation_method (ENH-098) ----

PROGRESS_CALC_METHODS: tuple[str, ...] = (
    "by_task_count",
    "by_duration",
    "by_effort",
)
DEFAULT_PROGRESS_CALC_METHOD: str = "by_task_count"

# ---- task_load_thresholds (ENH-099) ----

# DAT-06 / ADR-030 (2026-08-06): la llave se llama `yellow_max`. El semáforo
# habla `green`/`yellow`/`red` desde D-1 y la migración 0091; tener el valor en
# `yellow` y su umbral en `amber_max` obligaba a traducir mentalmente cada vez
# que se leía el código de colorización, que es como se cuelan los errores de
# asignación de color. La migración 0101 reescribió los datos; la entrada sigue
# aceptando el nombre viejo durante la ventana de compatibilidad.
DEFAULT_TASK_LOAD_THRESHOLDS: dict[str, int] = {"green_max": 5, "yellow_max": 10}


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
    and returns a normalized ``{"green_max": int, "yellow_max": int}``
    dict. Falls back to :data:`DEFAULT_TASK_LOAD_THRESHOLDS` when the
    block is absent or malformed. The returned dict is a fresh copy and
    safe for the caller to mutate.

    DAT-06: acepta el nombre retirado ``amber_max`` a la LECTURA además de a la
    entrada. La migración 0101 reescribió los datos, pero un inquilino que se
    restaure de una copia anterior al despliegue lo traería, y perder su umbral
    silenciosamente sería peor que aceptarlo con rastro.
    """
    rb = _report_builder_block(tenant)
    raw = rb.get("task_load_thresholds")
    if not isinstance(raw, dict):
        return dict(DEFAULT_TASK_LOAD_THRESHOLDS)
    if "yellow_max" not in raw and "amber_max" in raw:
        registrar_uso("amber_max", donde="settings del inquilino")
    try:
        green_max = int(raw.get("green_max", DEFAULT_TASK_LOAD_THRESHOLDS["green_max"]))
        yellow_max = int(
            raw.get(
                "yellow_max",
                raw.get("amber_max", DEFAULT_TASK_LOAD_THRESHOLDS["yellow_max"]),
            )
        )
    except (TypeError, ValueError):
        return dict(DEFAULT_TASK_LOAD_THRESHOLDS)
    return {"green_max": green_max, "yellow_max": yellow_max}


def validate_task_load_thresholds(green_max: int, yellow_max: int) -> None:
    """Raise :class:`ValueError` if the threshold pair is invalid.

    Both values must be positive ints and ``green_max < yellow_max``.
    """
    if isinstance(green_max, bool) or not isinstance(green_max, int):
        raise ValueError("green_max debe ser un entero")
    if isinstance(yellow_max, bool) or not isinstance(yellow_max, int):
        raise ValueError("yellow_max debe ser un entero")
    if green_max <= 0 or yellow_max <= 0:
        raise ValueError("Los umbrales deben ser positivos")
    if green_max >= yellow_max:
        raise ValueError("green_max debe ser menor que yellow_max")


def set_task_load_thresholds(
    tenant: Tenant, green_max: int, yellow_max: int
) -> dict[str, Any]:
    """Persist task-load thresholds on the tenant settings dict.

    Validates the pair (positive ints with ``green_max < yellow_max``) and
    returns the merged ``tenant.settings`` (also assigned on the model).
    Raises :class:`ValueError` on invalid input.
    """
    validate_task_load_thresholds(green_max, yellow_max)
    merged = dict(tenant.settings or {})
    rb = dict(merged.get("report_builder") or {})
    rb["task_load_thresholds"] = {"green_max": green_max, "yellow_max": yellow_max}
    merged["report_builder"] = rb
    tenant.settings = merged
    return merged
