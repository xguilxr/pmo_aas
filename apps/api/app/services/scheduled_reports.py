"""Service helpers para ScheduledReport (US-056).

Cálculo del siguiente `next_run_at` según la cadencia y envío del PDF
por email vía Resend. El dispatch del worker vive en
`app.workers.tasks.scheduled_reports`.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

CADENCES: tuple[str, ...] = ("daily", "weekly", "monthly")
REPORT_TYPES: tuple[str, ...] = ("avance", "seguimiento")

Cadence = Literal["daily", "weekly", "monthly"]
ReportType = Literal["avance", "seguimiento"]


def compute_next_run(cadence: str, *, from_dt: datetime | None = None) -> datetime:
    """Devuelve el siguiente `next_run_at` a partir de `from_dt` (default: ahora).

    - daily: +1 día
    - weekly: +7 días
    - monthly: +30 días (aproximación — suficiente para un MVP; TODO: día
      calendario exacto si el owner pide la fecha-clavada mensual).
    """
    base = from_dt or datetime.now(UTC)
    if cadence == "daily":
        return base + timedelta(days=1)
    if cadence == "weekly":
        return base + timedelta(days=7)
    if cadence == "monthly":
        return base + timedelta(days=30)
    raise ValueError(f"Cadencia inválida: {cadence}")
