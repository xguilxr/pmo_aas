import logging
import os

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger("pmoaas.worker")

# El worker usa Redis como broker/backend. Aceptamos CELERY_BROKER_URL como
# override explícito; si no, caemos a REDIS_URL. Si ninguno está configurado
# (o viene vacío) fallamos ruidosamente — sin esto Celery usa su default
# amqp://guest@localhost:5672// y el worker se queda reintentando para siempre.
_broker = (os.getenv("CELERY_BROKER_URL") or settings.REDIS_URL or "").strip()
_backend = (os.getenv("CELERY_RESULT_BACKEND") or settings.REDIS_URL or "").strip()

if not _broker:
    raise RuntimeError(
        "Celery broker URL no está configurada. Define REDIS_URL "
        "(o CELERY_BROKER_URL) en el servicio worker."
    )

logger.info("celery broker configured: %s", _broker.split("@")[-1])

celery_app = Celery(
    "pmoaas",
    broker=_broker,
    backend=_backend or None,
    include=[
        "app.workers.tasks.ai",
        "app.workers.tasks.notifications",
        "app.workers.tasks.scheduled_minutes",
        "app.workers.tasks.scheduled_reports",
        "app.workers.tasks.snapshots",
    ],
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.broker_connection_retry_on_startup = True

# Beat schedule (US-056): dispatch de reportes programados cada 5 min.
# El beat process se lanza con `celery -A app.workers.celery_app beat`.
celery_app.conf.beat_schedule = {
    "scheduled-reports-dispatch-due": {
        "task": "scheduled_reports.dispatch_due",
        "schedule": 300.0,
    },
    # ENH-107: dispatch de minutas programadas cada 5 min.
    "scheduled-minutes-dispatch-due": {
        "task": "scheduled_minutes.dispatch_due",
        "schedule": 300.0,
    },
    # US-151: snapshot semanal de métricas (lunes 02:00 UTC) para las
    # tendencias de los dashboards N1/N2.
    "metric-snapshots-weekly": {
        "task": "metric_snapshots.weekly",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),
    },
}
