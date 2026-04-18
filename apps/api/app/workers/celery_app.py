from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "pmoaas",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[],
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
