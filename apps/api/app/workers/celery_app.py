import logging

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
from app.core.observabilidad import configurar_registro, iniciar_captura_de_errores

# MCS OPS-01 — el worker no configuraba el registro en absoluto: heredaba lo
# que Celery decidiera. Se llama ANTES del primer `logger.info` de este módulo,
# que es el del broker, para que ese también salga estructurado.
configurar_registro("worker")

logger = logging.getLogger("pmoaas.worker")

# El worker usa Redis como broker/backend. Aceptamos CELERY_BROKER_URL como
# override explícito; si no, caemos a REDIS_URL. Si ninguno está configurado
# (o viene vacío) fallamos ruidosamente — sin esto Celery usa su default
# amqp://guest@localhost:5672// y el worker se queda reintentando para siempre.
_broker = (settings.CELERY_BROKER_URL or settings.REDIS_URL or "").strip()
_backend = (settings.CELERY_RESULT_BACKEND or settings.REDIS_URL or "").strip()

if not _broker:
    raise RuntimeError(
        "Celery broker URL no está configurada. Define REDIS_URL "
        "(o CELERY_BROKER_URL) en el servicio worker."
    )

logger.info("celery broker configured: %s", _broker.split("@")[-1])

# MCS OPS-02 — el worker reporta igual que la API. Antes no: la
# inicialización vivía en `main.py`, que este proceso nunca importa porque
# su servicio arranca `celery` directo. Un fallo aquí no produce un 500 que
# alguien vea; el informe simplemente no llega.
iniciar_captura_de_errores("worker")

celery_app = Celery(
    "pmoaas",
    broker=_broker,
    backend=_backend or None,
    include=[
        "app.workers.tasks.ai",
        "app.workers.tasks.notifications",
        "app.workers.tasks.respaldo",
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

# MCS OPS-01 — sin esto el cableado de arriba no sobrevive al arranque.
#
# Celery reemplaza los manejadores del registrador raíz al levantar el worker
# (`worker_hijack_root_logger`, por defecto `True`) y los sustituye por los
# suyos, de texto plano. `configurar_registro` corre al importar el módulo, o
# sea ANTES: el secuestro ocurre después y se lo lleva por delante. El resultado
# sería el peor de los posibles — el requisito parece cumplido leyendo el
# código, y en producción el worker sigue emitiendo texto.
celery_app.conf.worker_hijack_root_logger = False

# Y esto es el resto del mismo problema: Celery redirige `stdout`/`stderr` de
# las tareas a un registrador propio con `WARNING` como nivel, así que un
# `print` de depuración aparecía como advertencia. Con el registro ya
# estructurado, se deja de redirigir y lo que se imprime va a `stdout` tal cual.
celery_app.conf.worker_redirect_stdouts = False

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
    # MCS INF-03 — copia de seguridad diaria, 03:30 UTC.
    #
    # Media hora después del snapshot semanal para no solaparse con él los
    # lunes: los dos leen la base entera y competir por E/S alarga los dos.
    "respaldo-diario": {
        "task": "respaldo.diario",
        "schedule": crontab(hour=3, minute=30),
    },
}
