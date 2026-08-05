"""OPS-01 — los registros salen estructurados y por la salida estándar.

La auditoría del 2026-08-03 lo dejó NO CONFORME con una frase que se puede
verificar sola: `structlog==24.4.0` está declarado en `requirements.txt` y no se
importa en ningún archivo de `apps/api/app/`. Una dependencia declarada y sin
usar es la forma más barata de aparentar un control.

Esta suite **no** comprueba que structlog esté importado. Comprueba la salida,
que es lo que el requisito pide y lo único que un cambio futuro puede romper sin
darse cuenta:

- que un `logging.getLogger(...)` **de los que ya existían** salga en JSON, no
  solo lo que se escriba de ahora en adelante con la API de structlog;
- que salga por `stdout` y no por `stderr`, que es el defecto de `logging`;
- que lleve los campos con los que se consulta un agregador —momento, nivel,
  registrador y proceso—;
- que una excepción llegue como campo y no como cuatro líneas sueltas;
- y que **ningún punto de entrada se quede fuera**, que es el fallo exacto por
  el que OPS-02 estuvo medio cableado durante meses.

El último invariante es el que más falta hacía y el más fácil de romper:
`worker_hijack_root_logger` viene en `True`, así que Celery reemplaza los
manejadores del raíz DESPUÉS de que este módulo los ponga. Sin desactivarlo, el
código se lee conforme y el worker emite texto plano en producción.
"""
from __future__ import annotations

import io
import json
import logging
import re
from pathlib import Path

import pytest
import structlog

from app.core.observabilidad import configurar_registro

RAIZ_API = Path(__file__).resolve().parents[1]

#: Los mismos que vigila `test_ops02_captura_de_errores`. Se repiten aquí a
#: propósito en vez de importarse: son dos requisitos distintos y que uno deje
#: de cubrir un proceso no debe poder apagar la comprobación del otro.
PUNTOS_DE_ENTRADA = {
    "api": "app/main.py",
    "worker": "app/workers/celery_app.py",
}


class _Registro:
    """Arranca el registro contra un `stdout` de mentira y lee lo que salió.

    Se sustituye `sys.stdout` en vez de mirar el manejador ya montado
    precisamente para probar lo que el requisito dice: que el destino es la
    salida estándar. Si alguien lo cambia a `stderr`, aquí no llega nada y
    todas las pruebas de la suite caen a la vez.

    El cambio se hace **dentro de la llamada** y no en la preparación de la
    prueba: pytest reasigna `sys.stdout` al empezar cada fase, así que un
    parche puesto en el `fixture` queda pisado antes de que corra el cuerpo.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._monkeypatch = monkeypatch
        self._salida = io.StringIO()

    def configurar(self, proceso: str) -> None:
        self._monkeypatch.setattr("sys.stdout", self._salida)
        configurar_registro(proceso)

    def lineas(self) -> list[dict]:
        return [json.loads(x) for x in self._salida.getvalue().splitlines() if x.strip()]


@pytest.fixture
def registro(monkeypatch: pytest.MonkeyPatch):
    anteriores = logging.getLogger().handlers[:]
    nivel_anterior = logging.getLogger().level
    structlog.reset_defaults()
    try:
        yield _Registro(monkeypatch)
    finally:
        logging.getLogger().handlers = anteriores
        logging.getLogger().setLevel(nivel_anterior)
        structlog.reset_defaults()


def test_un_logging_getlogger_heredado_sale_en_json(registro: _Registro) -> None:
    """El caso que decide si el requisito se cumple o solo lo parece.

    Hay 31 sitios en `app/` que ya llamaban `logging.getLogger(...)`, más
    uvicorn, celery y sqlalchemy, que no son nuestros. Si structlog se hubiera
    cableado como registrador paralelo, todos ellos seguirían en texto plano y
    lo estructurado sería solo lo que se escriba a partir de hoy — es decir, la
    minoría, y encima la que menos falla.
    """
    registro.configurar("api")
    logging.getLogger("pmoaas.heredado").warning("presupuesto excedido")

    (evento,) = registro.lineas()
    assert evento["event"] == "presupuesto excedido"
    assert evento["level"] == "warning"
    assert evento["logger"] == "pmoaas.heredado"


def test_lleva_los_campos_con_los_que_se_consulta(registro: _Registro) -> None:
    """Sin estos cuatro, «estructurado» es un JSON con una frase dentro.

    `proceso` es el que no se puede deducir de nada más: la API y el worker
    comparten casi todo el código, así que comparten los nombres de registrador.
    """
    registro.configurar("worker")
    logging.getLogger("pmoaas.worker").info("informe programado enviado")

    (evento,) = registro.lineas()
    assert evento["proceso"] == "worker"
    assert evento["logger"] == "pmoaas.worker"
    assert evento["level"] == "info"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", evento["timestamp"]), (
        f"El momento tiene que ser ISO-8601 y ordenable: {evento.get('timestamp')!r}"
    )


def test_la_excepcion_viaja_como_campo(registro: _Registro) -> None:
    """Una traza partida en líneas sueltas se pierde en cualquier agregador.

    Es además el caso que más importa: el registro que se va a leer de verdad
    es el del fallo, no el del arranque.
    """
    registro.configurar("api")
    try:
        raise ValueError("el inquilino no tiene presupuesto declarado")
    except ValueError:
        logging.getLogger("pmoaas.api").exception("fallo al calcular la salud")

    (evento,) = registro.lineas()
    assert "ValueError" in evento["exception"]
    assert "el inquilino no tiene presupuesto declarado" in evento["exception"]
    assert evento["event"] == "fallo al calcular la salud"


def test_los_argumentos_posicionales_se_interpolan(registro: _Registro) -> None:
    """`logger.info("x=%s", v)` es como está escrito el código que ya existe.

    Las **dos** rutas, y la segunda es la que de verdad se rompe. Un registro
    nacido en `logging` ya llega interpolado por `record.getMessage()`, así que
    comprobar solo esa deja pasar la ausencia de
    `PositionalArgumentsFormatter`: la primera versión de esta prueba lo hacía,
    y la mutación que quitaba el procesador sobrevivió.

    Por la ruta nativa de structlog no hay nadie más que interpole: sin el
    procesador el evento sale con los `%s` crudos y los valores perdidos en un
    campo `positional_args`.
    """
    registro.configurar("api")
    logging.getLogger("pmoaas.api").info("captura activa proceso=%s env=%s", "api", "production")
    structlog.get_logger("pmoaas.api").info("captura activa proceso=%s env=%s", "api", "production")

    heredado, nativo = registro.lineas()
    esperado = "captura activa proceso=api env=production"
    assert heredado["event"] == esperado
    assert nativo["event"] == esperado, (
        "La ruta nativa de structlog no interpoló: falta "
        "`PositionalArgumentsFormatter` en la cadena de `structlog.configure`."
    )


def test_structlog_y_logging_producen_la_misma_forma(registro: _Registro) -> None:
    """Si divergen, quien consulta los registros necesita dos preguntas.

    Es lo que pasa cuando la cadena de procesadores se duplica en dos sitios y
    uno se actualiza sin el otro.
    """
    registro.configurar("api")
    logging.getLogger("pmoaas.viejo").info("por la biblioteca estándar")
    structlog.get_logger("pmoaas.nuevo").info("por structlog")

    viejo, nuevo = registro.lineas()
    assert set(viejo) == set(nuevo), (
        "Los dos caminos tienen que emitir los mismos campos. Diferencia: "
        f"{set(viejo) ^ set(nuevo)}"
    )


def test_no_acumula_manejadores_al_reconfigurar(registro: _Registro) -> None:
    """Dos llamadas no deben duplicar cada línea.

    Ocurre solo en desarrollo con recarga en caliente, y por eso se cuela: en
    producción el proceso arranca una vez y nadie lo ve hasta que un día
    alguien llama a la función desde un tercer sitio.
    """
    registro.configurar("api")
    registro.configurar("api")
    logging.getLogger("pmoaas.api").info("una sola vez")

    assert len(registro.lineas()) == 1
    assert len(logging.getLogger().handlers) == 1


def test_en_produccion_el_formato_de_consola_no_puede_ganar(
    registro: _Registro, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`LOG_FORMAT` es una variable de entorno, y una mal puesta en Railway no
    debe poder desactivar un requisito del marco.

    `consola` existe para leer con los ojos en local. En producción se ignora.
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOG_FORMAT", "consola")
    monkeypatch.setattr(settings, "PYTHON_ENV", "production")
    registro.configurar("api")
    logging.getLogger("pmoaas.api").info("sigue siendo json")

    (evento,) = registro.lineas()
    assert evento["event"] == "sigue siendo json"


def test_todo_punto_de_entrada_configura_su_registro() -> None:
    """El fallo por el que OPS-02 estuvo medio cableado durante meses.

    Los dos procesos no comparten intérprete: el servicio `worker` arranca
    `celery` directo y nunca importa `main.py`. Lo que se configure en uno, en
    el otro no existe.
    """
    faltan = [
        proceso
        for proceso, ruta in PUNTOS_DE_ENTRADA.items()
        if not re.search(
            rf"configurar_registro\(\s*[\"']{proceso}[\"']\s*\)",
            (RAIZ_API / ruta).read_text(encoding="utf-8"),
        )
    ]
    assert not faltan, (
        f"Puntos de entrada sin `configurar_registro`: {faltan}. Cada proceso "
        "que Railway arranca por su cuenta necesita la suya."
    )


def test_ningun_punto_de_entrada_reconfigura_por_su_cuenta() -> None:
    """`logging.basicConfig` no falla ni avisa: no hace nada si ya hay
    manejadores, y lo deshace todo si corre antes.

    Aquí había uno, con formato de texto plano, y era la razón por la que el
    requisito estaba abierto. Que no vuelva por la puerta de atrás.

    Se busca la **llamada**, no la cadena: los comentarios de los dos puntos de
    entrada nombran la función para explicar por qué se fue, y una búsqueda
    literal los tomaría por la infracción que documentan.
    """
    llamada = re.compile(r"^\s*logging\.basicConfig\s*\(", re.M)
    culpables = [
        ruta
        for ruta in PUNTOS_DE_ENTRADA.values()
        if llamada.search((RAIZ_API / ruta).read_text(encoding="utf-8"))
    ]
    assert not culpables, f"`logging.basicConfig` reaparecido en: {culpables}"


def test_celery_no_secuestra_el_registrador_raiz() -> None:
    """El invariante que se rompe sin tocar este archivo.

    `worker_hijack_root_logger` viene en `True`. Celery reemplaza los
    manejadores del raíz al levantar el worker, o sea DESPUÉS de que
    `configurar_registro` los ponga al importar el módulo. Sin desactivarlo el
    código se lee conforme y producción emite texto plano — que es exactamente
    la clase de fallo que este expediente lleva dos sesiones cazando.
    """
    from app.workers.celery_app import celery_app

    assert celery_app.conf.worker_hijack_root_logger is False, (
        "Celery va a reemplazar el manejador estructurado por el suyo de texto "
        "plano en cuanto arranque el worker."
    )
