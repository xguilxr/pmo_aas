"""Service helpers para ScheduledReport (US-056 + ENH-046).

ENH-046 (2026-05-05) extiende el cómputo de `next_run_at` para
permitir que el owner elija día de semana + hora para recurrentes y
fecha + hora puntual para uno-time. Convención de día de la semana:
0 = lunes, 6 = domingo (Python `weekday()`). Las horas viajan en UTC
por simplicidad — la tenant timezone-aware vendrá en una iteración
posterior si el owner lo pide.
"""
from __future__ import annotations

import calendar
from datetime import UTC, datetime, time, timedelta
from typing import Literal

CADENCES: tuple[str, ...] = ("daily", "weekly", "monthly", "once")
REPORT_TYPES: tuple[str, ...] = ("avance", "seguimiento")

Cadence = Literal["daily", "weekly", "monthly", "once"]
ReportType = Literal["avance", "seguimiento"]


def _last_day_of_month(year: int, month: int) -> int:
    """ENH-056: 28/29/30/31 según corresponda. Reusa `calendar.monthrange`."""
    return calendar.monthrange(year, month)[1]


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def compute_next_run(
    cadence: str,
    *,
    from_dt: datetime | None = None,
    day_of_week: int | None = None,
    hour_of_day: int | None = None,
    day_of_month: int | None = None,
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
        # ENH-056: si tenemos day_of_month + hour_of_day, calculamos
        # próxima ocurrencia "fija" con clamp al último día del mes
        # destino. Sin estos campos, mantenemos legacy `+30 días`.
        if day_of_month is None or hour_of_day is None:
            return base + timedelta(days=30)
        # Candidato 1: este mes en day_of_month (clampeado).
        last = _last_day_of_month(base.year, base.month)
        target_day = min(day_of_month, last)
        candidate = base.replace(
            day=target_day, hour=hour_of_day, minute=0, second=0, microsecond=0
        )
        if candidate > base:
            return candidate
        # Sino: siguiente mes con clamp.
        ny, nm = _next_month(base.year, base.month)
        last_next = _last_day_of_month(ny, nm)
        target_day = min(day_of_month, last_next)
        return base.replace(
            year=ny, month=nm, day=target_day,
            hour=hour_of_day, minute=0, second=0, microsecond=0,
        )
    raise ValueError(f"Cadencia inválida: {cadence}")


# Helpers usados por la API y tests para construir tiempos de demo.
def _today_at(hour: int) -> datetime:
    return datetime.now(UTC).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


def _at_time(hour: int) -> time:
    return time(hour=hour, tzinfo=UTC)
