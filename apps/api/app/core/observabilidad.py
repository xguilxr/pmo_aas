"""Captura de errores en producción (MCS OPS-02), para los DOS procesos.

La auditoría del 2026-08-03 encontró que no había ninguna: un 500 en producción
quedaba en los registros de Railway y nadie se enteraba salvo que un usuario lo
reportase. La remediación cableó `sentry_sdk.init` en `main.py`.

**Que era la mitad del problema.** `main.py` es el punto de entrada de la API;
el servicio `worker` sobrescribe el CMD con un `celery` directo
(`worker.railway.toml` → `startCommand`), así que en ese proceso `main.py`
**nunca se importa** y la inicialización nunca corre. Con `SENTRY_DSN` puesta,
la API reportaba y el worker no.

Y el worker es justo donde más caro sale: ahí corren la generación de minutas y
de informes con IA, la importación de MS Project, los informes programados y los
snapshots semanales. Un fallo en la API produce un 500 que alguien ve; **un
fallo en una tarea de fondo no produce nada** — el informe simplemente no llega,
y el primero en enterarse es el cliente que lo esperaba.

Por eso esto vive aquí y no en ninguno de los dos: un control que hay que
acordarse de llamar en cada punto de entrada es un control que se olvida en el
siguiente.
"""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("pmoaas.observabilidad")


def iniciar_captura_de_errores(proceso: str) -> bool:
    """Arranca la captura de errores para `proceso` («api» o «worker»).

    Devuelve si quedó activa, que es lo que hace comprobable el requisito: sin
    valor de retorno, la única forma de saberlo era leer los registros.

    Sin `SENTRY_DSN` no hace nada y lo dice: en local y en las pruebas queda
    inerte a propósito. `send_default_pii=False` porque este producto trata
    datos de proyecto de sus clientes y no hay motivo para exportarlos a un
    tercero junto con la traza.

    `proceso` va como etiqueta para poder separar en Sentry un fallo de la API
    de uno del worker sin adivinar por la traza.
    """
    if not settings.SENTRY_DSN:
        return False
    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN definido pero sentry-sdk no está instalado")
        return False

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.PYTHON_ENV,
        release=settings.VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )
    sentry_sdk.set_tag("proceso", proceso)
    logger.info(
        "captura de errores activa proceso=%s env=%s", proceso, settings.PYTHON_ENV
    )
    return True
