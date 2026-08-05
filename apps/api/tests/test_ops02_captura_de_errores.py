"""OPS-02 — la captura de errores cubre los DOS procesos, no solo la API.

La auditoría del 2026-08-03 lo dejó NO CONFORME y CRÍTICO: no había ninguna
captura, y un 500 en producción quedaba en los registros de Railway sin avisar a
nadie. La remediación cableó `sentry_sdk.init` en `main.py` y el requisito pasó a
PARCIAL, esperando solo la variable de entorno.

**Faltaba la otra mitad, y era la peor.** El servicio `worker` arranca `celery`
directo (`worker.railway.toml` → `startCommand`), así que en ese proceso
`main.py` **nunca se importa** y la inicialización nunca corría. Con `SENTRY_DSN`
puesta, la API reportaba y el worker no.

Y el worker es donde más caro sale: ahí corren la generación de minutas e
informes con IA, la importación de MS Project, los informes programados y los
snapshots semanales. Un fallo en la API produce un 500 que alguien ve; **un
fallo en una tarea de fondo no produce nada visible** — el informe no llega, y
el primero en enterarse es el cliente que lo esperaba.

Lo que esta suite defiende es justamente eso: que ningún punto de entrada quede
fuera, ni hoy ni cuando se agregue el siguiente.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.observabilidad import iniciar_captura_de_errores

RAIZ_API = Path(__file__).resolve().parents[1]

#: Todo proceso que Railway arranca por su cuenta. Cada uno necesita su propia
#: inicialización: no comparten intérprete.
PUNTOS_DE_ENTRADA = {
    "api": "app/main.py",
    "worker": "app/workers/celery_app.py",
}


# ---------------------------------------------------------------------------
# Que ningún punto de entrada quede fuera
# ---------------------------------------------------------------------------


def _llamadas_vivas(ruta: str) -> list[str]:
    """Las llamadas que se ejecutan, no las que aparecen en el archivo.

    Se excluyen las líneas comentadas a propósito: la primera versión de esta
    prueba buscaba el literal en el texto crudo y **pasaba con la llamada del
    worker comentada** — comprobaba que el texto estuviera escrito, no que el
    proceso reportara. Lo cazó la verificación por mutación, que es para lo que
    está.
    """
    fuente = (RAIZ_API / ruta).read_text(encoding="utf-8")
    codigo = "\n".join(
        linea for linea in fuente.splitlines() if not linea.lstrip().startswith("#")
    )
    return re.findall(r'iniciar_captura_de_errores\(\s*"([^"]+)"\s*\)', codigo)


@pytest.mark.parametrize("proceso,ruta", sorted(PUNTOS_DE_ENTRADA.items()))
def test_cada_punto_de_entrada_inicia_la_captura(proceso, ruta):
    """El worker se quedó fuera durante toda la remediación de OPS-02."""
    llamadas = _llamadas_vivas(ruta)

    assert proceso in llamadas, (
        f"`{ruta}` no inicia la captura de errores. Railway lo arranca como "
        f"proceso propio, así que no hereda la de nadie: un fallo ahí no se "
        f"reporta y —si es una tarea de fondo— tampoco se ve."
    )


def test_la_inicializacion_vive_en_un_solo_sitio():
    """Estaba dentro de `main.py`, y por eso el worker no podía reusarla.

    Un control que hay que reimplementar en cada punto de entrada es un control
    que se olvida en el siguiente.
    """
    fuentes = {
        ruta: (RAIZ_API / ruta).read_text(encoding="utf-8")
        for ruta in PUNTOS_DE_ENTRADA.values()
    }
    con_init_propio = [r for r, s in fuentes.items() if "sentry_sdk.init(" in s]

    assert not con_init_propio, (
        f"{con_init_propio} inicializa Sentry por su cuenta. Va por "
        f"`core/observabilidad.py`, que es el único sitio."
    )


# ---------------------------------------------------------------------------
# El comportamiento, que es lo que hace el requisito comprobable
# ---------------------------------------------------------------------------


def test_sin_dsn_queda_inerte_y_lo_dice(monkeypatch):
    """En local y en las pruebas no debe reportar nada — a propósito.

    Devuelve `False` en vez de no devolver nada: sin valor de retorno, la única
    forma de saber si el requisito está satisfecho en producción era leer los
    registros a mano.
    """
    monkeypatch.setattr("app.core.observabilidad.settings.SENTRY_DSN", "")

    assert iniciar_captura_de_errores("api") is False


def test_con_dsn_queda_activa_y_etiqueta_el_proceso(monkeypatch):
    """La etiqueta es lo que permite separar un fallo de la API de uno del
    worker sin adivinar por la traza."""
    llamadas: dict[str, object] = {}

    class _FalsoSentry:
        VERSION = "0"

        @staticmethod
        def init(**kwargs):
            llamadas["init"] = kwargs

        @staticmethod
        def set_tag(clave, valor):
            llamadas[clave] = valor

    monkeypatch.setattr(
        "app.core.observabilidad.settings.SENTRY_DSN", "https://x@example.test/1"
    )
    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", _FalsoSentry)

    assert iniciar_captura_de_errores("worker") is True
    assert llamadas["proceso"] == "worker"
    assert llamadas["init"]["dsn"] == "https://x@example.test/1"


def test_nunca_se_exportan_datos_personales(monkeypatch):
    """Este producto trata datos de proyecto de sus clientes; no hay motivo
    para mandarlos a un tercero junto con la traza."""
    llamadas: dict[str, object] = {}

    class _FalsoSentry:
        @staticmethod
        def init(**kwargs):
            llamadas.update(kwargs)

        @staticmethod
        def set_tag(*_):
            pass

    monkeypatch.setattr(
        "app.core.observabilidad.settings.SENTRY_DSN", "https://x@example.test/1"
    )
    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", _FalsoSentry)
    iniciar_captura_de_errores("api")

    assert llamadas["send_default_pii"] is False


def test_sin_la_biblioteca_no_revienta_el_arranque(monkeypatch):
    """Un fallo del reporte de errores no puede tumbar el proceso que reporta."""
    monkeypatch.setattr(
        "app.core.observabilidad.settings.SENTRY_DSN", "https://x@example.test/1"
    )
    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", None)

    assert iniciar_captura_de_errores("api") is False


def test_la_dependencia_esta_declarada():
    """Estaba: se comprueba para que un `pip uninstall` accidental no deje el
    requisito en verde sobre un `except ImportError` silencioso."""
    reqs = (RAIZ_API / "requirements.txt").read_text(encoding="utf-8")

    assert re.search(r"^sentry-sdk", reqs, re.MULTILINE)
