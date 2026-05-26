"""Celery task para snapshots semanales de métricas (US-151).

`capture_weekly_snapshots`: beat-triggered (lunes 02:00 UTC). Recorre los
tenants activos y persiste una fila por scope (tenant/org/programa/proyecto)
en `metric_snapshots`, habilitando las tendencias de los dashboards N1/N2.
"""
from __future__ import annotations

import logging
from datetime import date

from app.services.analytics.snapshots import snapshot_all_tenants
from app.workers.celery_app import celery_app
from app.workers.db import db_session, run_async

log = logging.getLogger(__name__)


@celery_app.task(name="metric_snapshots.weekly", bind=True, max_retries=1)
def capture_weekly_snapshots(self) -> dict:
    return run_async(_capture())


async def _capture() -> dict:
    today = date.today()
    async with db_session() as db:
        written = await snapshot_all_tenants(db, today)
    log.info("metric_snapshots: %d filas escritas para %s", written, today)
    return {"date": today.isoformat(), "rows": written}
