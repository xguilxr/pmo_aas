"""Observabilidad de los DOS procesos: registros (OPS-01) y errores (OPS-02).

Los dos requisitos comparten módulo por la misma razón, y esa razón es un fallo
real: lo que se cablea en un solo punto de entrada deja la otra mitad de
producción a oscuras. `main.py` arranca la API; el servicio `worker`
sobrescribe el CMD con un `celery` directo (`worker.railway.toml` →
`startCommand`) y **nunca importa `main.py`**. Cualquier cosa que se configure
allí, en el worker no existe.

---

## Captura de errores en producción (MCS OPS-02), para los DOS procesos.

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

---

## Registros estructurados a la salida estándar (MCS OPS-01)

La auditoría lo dejó NO CONFORME con una frase exacta: `structlog==24.4.0` está
en `requirements.txt` y **no se importa en ningún archivo** de `apps/api/app/`.
Lo que sí había era un `logging.basicConfig` con formato de texto plano en
`main.py`, y nada en el worker.

Dos consecuencias, y ninguna es cosmética. En Railway los registros se buscan
por texto: sin campos, `nivel=ERROR AND inquilino=X` no se puede preguntar, y
lo que se hace en su lugar es leer con los ojos. Y en el worker no había ni
siquiera configuración propia — quedaba a merced de la de Celery, que además
**secuestra el registrador raíz** por defecto.

`configurar_registro` cablea `structlog` como formateador del `logging` de la
biblioteca estándar, no como un registrador paralelo. La diferencia importa:
los **31 sitios** que ya llaman `logging.getLogger(...)` pasan a emitir JSON
sin tocar una línea, y con ellos `uvicorn`, `celery` y `sqlalchemy`, que no son
nuestros y nunca iban a migrar. Un cableado que exigiera reescribir cada sitio
habría dejado estructurado lo nuevo y en texto plano lo que ya había, que es la
peor de las dos mitades.

**Salida estándar y no de error**, explícitamente: `logging` manda a `stderr`
por defecto, y ahí un `INFO` se lee como un fallo en cualquier agregador que
separe los dos flujos.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings

logger = logging.getLogger("pmoaas.observabilidad")

#: Nombre del proceso, fijado por `configurar_registro`. Se emite en cada
#: registro para poder separar la API del worker sin adivinar por el módulo:
#: los dos comparten casi todo el código y casi todos los nombres de registrador.
_PROCESO = "desconocido"


def _anotar_proceso(_logger: Any, _metodo: str, evento: dict[str, Any]) -> dict[str, Any]:
    evento.setdefault("proceso", _PROCESO)
    return evento


def _cadena_comun() -> list[Any]:
    """Procesadores que se aplican venga el registro de donde venga.

    Se comparten entre `structlog.configure` y el `foreign_pre_chain` del
    formateador a propósito: si divergen, un `logging.getLogger(...)` y un
    `structlog.get_logger()` producen dos formas distintas del mismo evento y
    el que consulta los registros no puede escribir una sola pregunta.
    """
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _anotar_proceso,
    ]


def _renderizador() -> Any:
    """JSON salvo que se pida consola Y no estemos en producción.

    El `and` no es defensivo de más: `LOG_FORMAT` es una variable de entorno, y
    una variable de entorno mal puesta en Railway no debe poder desactivar un
    requisito del marco.
    """
    if settings.LOG_FORMAT == "consola" and settings.PYTHON_ENV != "production":
        return structlog.dev.ConsoleRenderer(colors=False)
    return structlog.processors.JSONRenderer(ensure_ascii=False, sort_keys=True)


def configurar_registro(proceso: str) -> None:
    """Deja el registro de `proceso` estructurado y saliendo por `stdout`.

    Idempotente: los dos puntos de entrada pueden llamarla y una recarga en
    desarrollo no acumula manejadores. Reemplaza los del registrador raíz en
    vez de añadirse, que es lo que produce la línea duplicada.
    """
    global _PROCESO
    _PROCESO = proceso

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *_cadena_comun(),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formateador = structlog.stdlib.ProcessorFormatter(
        # Lo que le pasa a un registro que NO nació en structlog: los 31 sitios
        # de `logging.getLogger(...)` que ya existen, más uvicorn y celery.
        foreign_pre_chain=[structlog.stdlib.ExtraAdder(), *_cadena_comun()],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            _renderizador(),
        ],
    )

    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(formateador)

    raiz = logging.getLogger()
    raiz.handlers = [manejador]
    raiz.setLevel(settings.LOG_LEVEL)


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
