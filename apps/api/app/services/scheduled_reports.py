"""Service helpers para ScheduledReport (US-056 + ENH-046).

ENH-046 (2026-05-05) extiende el cómputo de `next_run_at` para
permitir que el owner elija día de semana + hora para recurrentes y
fecha + hora puntual para uno-time. Convención de día de la semana:
0 = lunes, 6 = domingo (Python `weekday()`). Las horas viajan en UTC
por simplicidad — la tenant timezone-aware vendrá en una iteración
posterior si el owner lo pide.
"""
from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Literal

CADENCES: tuple[str, ...] = ("daily", "weekly", "monthly", "once")
REPORT_TYPES: tuple[str, ...] = ("avance", "seguimiento")

Cadence = Literal["daily", "weekly", "monthly", "once"]
ReportType = Literal["avance", "seguimiento"]


def compute_next_run(
    cadence: str,
    *,
    from_dt: datetime | None = None,
    day_of_week: int | None = None,
    hour_of_day: int | None = None,
    run_at: datetime | None = None,
) -> datetime:
    """Devuelve el próximo `next_run_at` aplicando la cadencia y los
    parámetros de día/hora si están presentes.

    - **once:** devuelve `run_at` directo. Si es None, error.
    - **daily:** próxima ocurrencia de `hour_of_day:00`. Si `hour_of_day`
      es None, mantiene el legacy (+1 día desde `from_dt`).
    - **weekly:** próxima ocurrencia de `day_of_week` a `hour_of_day:00`.
      Si ambos son None, legacy (+7 días).
    - **monthly:** legacy (+30 días). Mejorará si el owner pide día-clavado.
    """
    base = from_dt or datetime.now(UTC)
    if cadence == "once":
        if run_at is None:
            raise ValueError("cadence=once requiere run_at")
        # Asume tz-aware; si llega naive, asumimos UTC.
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=UTC)
        return run_at
    if cadence == "daily":
        if hour_of_day is None:
            return base + timedelta(days=1)
        target = base.replace(
            hour=hour_of_day, minute=0, second=0, microsecond=0
        )
        if target <= base:
            target += timedelta(days=1)
        return target
    if cadence == "weekly":
        if day_of_week is None or hour_of_day is None:
            return base + timedelta(days=7)
        # base.weekday(): 0=lunes … 6=domingo (igual convención que la API).
        days_ahead = (day_of_week - base.weekday()) % 7
        candidate = (base + timedelta(days=days_ahead)).replace(
            hour=hour_of_day, minute=0, second=0, microsecond=0
        )
        if candidate <= base:
            candidate += timedelta(days=7)
        return candidate
    if cadence == "monthly":
        return base + timedelta(days=30)
    raise ValueError(f"Cadencia inválida: {cadence}")


# Helpers usados por la API y tests para construir tiempos de demo.
def _today_at(hour: int) -> datetime:
    return datetime.now(UTC).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


def _at_time(hour: int) -> time:
    return time(hour=hour, tzinfo=UTC)
