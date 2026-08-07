"""Tarea Celery de la copia de seguridad diaria (MCS INF-03).

Va en el worker y no en un cron de Railway por lo mismo que el resto de lo
programado: el worker ya tiene planificador, y una copia que dependa de un cron
configurado a mano en el panel es una copia que nadie sabe si sigue existiendo
cuando alguien recrea el servicio.

`max_retries=2`: si `pg_dump` falla por una desconexión pasajera, se reintenta.
Si falla por algo real —no está el binario, credenciales mal— reintentarlo tres
veces no lo arregla y lo que hace falta es que alguien se entere, que es lo que
hace la captura de errores de OPS-02.
"""
from __future__ import annotations

import logging

from app.services.respaldo import RespaldoError, respaldar
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="respaldo.diario", bind=True, max_retries=2)
def respaldo_diario(self) -> dict:
    """Vuelca la base, la sube al almacenamiento de objetos y limpia lo viejo."""
    try:
        return respaldar()
    except RespaldoError as exc:
        # Se registra Y se relanza: el registro deja el rastro operativo y la
        # excepción llega a Sentry. Tragársela dejaría la copia sin hacer y el
        # trabajo marcado como correcto — la peor combinación.
        log.error("respaldo fallido: %s", exc)
        raise
