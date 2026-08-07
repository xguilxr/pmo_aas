"""Tarea Celery de la copia de seguridad diaria (MCS INF-03).

Va en el worker y no en un cron de Railway por lo mismo que el resto de lo
programado: el worker ya tiene planificador, y una copia que dependa de un cron
configurado a mano en el panel es una copia que nadie sabe si sigue existiendo
cuando alguien recrea el servicio.

`autoretry_for` con `max_retries=2`: si `pg_dump` falla por una desconexión
pasajera, se reintenta. Si falla por algo real —no está el binario,
credenciales mal— reintentarlo tres veces no lo arregla y lo que hace falta es
que alguien se entere, que es lo que hace la captura de errores de OPS-02.

**El reintento tiene que estar declarado, no solo permitido.** La primera
versión llevaba `bind=True, max_retries=2` y ningún `self.retry()`: `max_retries`
es el tope de una política que nadie había activado, así que el primer fallo
era el último y la docstring de arriba describía algo que no ocurría. Lo
encontró `mypy --strict` tirando de un hilo distinto —`self` sin anotar—, que
es el motivo por el que la verificación de tipos gana su sitio.
"""
from __future__ import annotations

import logging

from app.services.respaldo import RespaldoError, respaldar
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


# `type: ignore[misc]`: el decorador de Celery no está anotado, y sin esto
# `mypy --strict` da por no verificada la función entera —que es peor que la
# molestia de la línea—. Mismo motivo que en el resto de tareas del worker.
@celery_app.task(  # type: ignore[misc]
    name="respaldo.diario",
    autoretry_for=(RespaldoError,),
    retry_backoff=60,
    max_retries=2,
)
def respaldo_diario() -> dict[str, object]:
    """Vuelca la base, la sube al almacenamiento de objetos y limpia lo viejo."""
    try:
        return respaldar()
    except RespaldoError as exc:
        # Se registra Y se relanza: el registro deja el rastro operativo y la
        # excepción llega a Sentry. Tragársela dejaría la copia sin hacer y el
        # trabajo marcado como correcto — la peor combinación.
        log.error("respaldo fallido: %s", exc)
        raise
