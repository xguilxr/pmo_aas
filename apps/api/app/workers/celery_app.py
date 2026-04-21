import logging
import os

from celery import Celery

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
    include=["app.workers.tasks.ai"],
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.broker_connection_retry_on_startup = True
