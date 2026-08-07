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

import functools
import inspect
import logging
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, ParamSpec, TypeVar, cast

import structlog

from app.core.config import settings
from app.core.unidades import segundos_a_ms

logger = logging.getLogger("pmoaas.observabilidad")

#: Registro aparte para la medición. Se separa de `pmoaas.observabilidad` para
#: que se pueda subir o bajar su nivel sin tocar el de los errores.
medidor = logging.getLogger("pmoaas.medicion")

#: Para que `medido` conserve la firma de lo que decora. Sin esto el decorador
#: devuelve `Any` y apaga la comprobación de tipos de todo el que llama a la
#: función decorada — en silencio.
_P = ParamSpec("_P")
_R = TypeVar("_R")

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


@contextmanager
def medir(operacion: str, **etiquetas: Any) -> Iterator[dict[str, Any]]:
    """Mide cuánto tarda un bloque y lo reporta a Sentry y al registro.

    Existe por MCS REQ-02: «DEBEN definirse al menos cuatro escenarios de
    calidad con medida de respuesta numérica». Hoy hay **cero**, y no por
    descuido: no se puede declarar «un informe se genera en menos de N
    segundos» sin saber cuánto tarda. Inventar el número sería exactamente el
    error que este expediente lleva cinco recuentos evitando.

    Así que primero se mide y después se declara el escenario, con el
    percentil 95 real de producción.

    **Funciona sin Sentry.** En local y en las pruebas no hay DSN, y aun así la
    duración sale por el registro estructurado —que desde OPS-01 es JSON a la
    salida estándar—. Una medición que solo existe en producción no se puede
    probar.

    **Nunca cambia el resultado ni traga un error.** Si el bloque revienta, se
    mide igual, se marca `exito=False` y la excepción sigue subiendo: una
    instrumentación que se coma un fallo es peor que no tenerla.

    El diccionario que entrega permite añadir etiquetas que solo se conocen
    dentro del bloque (páginas, filas, tamaño), y que se emiten al cerrar:

        with medir("informe.html", tipo="semanal") as m:
            html = render(...)
            m["bytes"] = len(html)
    """
    extra: dict[str, Any] = dict(etiquetas)
    comienzo = time.perf_counter()
    exito = True

    span = None
    try:  # pragma: no cover - depende de que sentry esté instalado y activo
        import sentry_sdk

        if sentry_sdk.get_client().is_active():
            span = sentry_sdk.start_span(op="generacion", name=operacion)
            span.__enter__()
    except Exception:
        span = None

    try:
        yield extra
    except Exception:
        exito = False
        raise
    finally:
        ms = segundos_a_ms(time.perf_counter() - comienzo)
        if span is not None:  # pragma: no cover
            try:
                for clave, valor in {**extra, "exito": exito}.items():
                    span.set_data(clave, valor)
                span.__exit__(None, None, None)
            except Exception:
                pass
        medidor.info(
            "generacion",
            extra={
                "operacion": operacion,
                "duracion_ms": ms,
                "exito": exito,
                **extra,
            },
        )


def medido(
    operacion: str, **etiquetas: Any
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Decorador para medir una función entera. Sirve para `async` y para `def`.

    `medir` como gestor de contexto obliga a tocar el cuerpo de la función; en
    los puntos de generación, que son largos y con varios `return`, eso es
    invitar a que una rama se quede sin medir. El decorador mide la función
    completa por construcción.

    Se elige por firma, no por bandera: envolver una corrutina con el envoltorio
    síncrono devolvería la corrutina sin esperarla y mediría **cero
    milisegundos siempre** — un fallo que se lee como un informe instantáneo y
    no como un error.

    **Tipado con `ParamSpec`, y no es cosmética.** La primera versión devolvía
    `Any`, y mypy avisó de lo que eso significa: «untyped decorator makes
    function untyped». Las cuatro funciones decoradas **perdieron su firma**, y
    con ella la comprobación de tipos de todo el que las llama.

    Se vio en el propio gate: al enchufarlo desaparecieron **cinco huellas de
    la línea base** de `reports.py` —errores reales de tipo que mypy dejó de
    ver porque ya no sabía qué recibía `render_report_html`—. Un decorador sin
    tipar no es un detalle de estilo: apaga el análisis aguas abajo y lo hace
    en silencio.
    """

    def envolver(funcion: Callable[_P, _R]) -> Callable[_P, _R]:
        if inspect.iscoroutinefunction(funcion):

            @functools.wraps(funcion)
            async def asincrona(*args: _P.args, **kwargs: _P.kwargs) -> Any:
                with medir(operacion, **etiquetas):
                    return await funcion(*args, **kwargs)

            # `cast` porque el envoltorio asíncrono devuelve la corrutina ya
            # esperada: para quien llama, la firma es la misma.
            return cast(Callable[_P, _R], asincrona)

        @functools.wraps(funcion)
        def sincrona(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            with medir(operacion, **etiquetas):
                return funcion(*args, **kwargs)

        return sincrona

    return envolver
