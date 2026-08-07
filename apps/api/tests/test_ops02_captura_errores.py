"""OPS-02 — la captura de errores se anuncia, encendida y apagada.

«DEBE existir captura y notificación automática de errores en producción».

El cableado estaba desde la Ola 2. Lo que faltaba lo reportó el owner el
2026-08-06 mirando Railway: **veía los registros estructurados de OPS-01 y
ninguna línea sobre Sentry**, y no había manera de distinguir «apagado» de
«encendido y callado».

La causa era un defecto pequeño y caro: sin `SENTRY_DSN`, la función devolvía
`False` **en silencio** — mientras su propio docstring afirmaba «sin
`SENTRY_DSN` no hace nada *y lo dice*». La documentación describía un
comportamiento que el código no tenía.

Un control que no se puede observar no se puede verificar, y eso es justo lo
que el requisito pide. Ahora se anuncia por registro **y** se publica en
`/health`, que se puede vigilar desde fuera sin acceso a los registros.
"""
from __future__ import annotations

import logging

import pytest

from app.core.observabilidad import (
    captura_de_errores_activa,
    iniciar_captura_de_errores,
)


def test_sin_dsn_lo_dice_en_vez_de_callarse(caplog: pytest.LogCaptureFixture) -> None:
    """El defecto que reportó el owner, como caso.

    Sin esto, «no veo nada sobre Sentry en los registros» sigue teniendo dos
    explicaciones posibles y ninguna forma de distinguirlas.
    """
    from app.core.config import settings

    assert not settings.SENTRY_DSN, "Este caso mide el camino SIN DSN."

    with caplog.at_level(logging.WARNING, logger="pmoaas.observabilidad"):
        activa = iniciar_captura_de_errores("api")

    assert activa is False
    (registro,) = (r for r in caplog.records if "captura de errores" in r.getMessage())
    assert "DESACTIVADA" in registro.getMessage()
    assert "SENTRY_DSN" in registro.getMessage(), (
        "El aviso no nombra la variable que falta. Quien lo lea en Railway "
        "tiene que saber qué poner sin ir al código."
    )
    assert registro.levelno >= logging.WARNING, (
        "Va como aviso, no como informativo: que la captura de errores esté "
        "apagada en producción es una condición que alguien debe atender."
    )


def test_el_estado_se_puede_consultar_sin_leer_registros() -> None:
    """`captura_de_errores_activa()` es lo que `/health` publica.

    Leer registros para saber si un control está encendido obliga a tener
    acceso y a saber qué buscar. Una respuesta JSON la mira cualquiera — y la
    puede vigilar un supervisor externo, que es lo que convierte esto en
    verificable de forma continua y no una vez.
    """
    iniciar_captura_de_errores("api")
    assert captura_de_errores_activa() is False  # sin DSN en la suite


@pytest.mark.asyncio
async def test_health_publica_el_estado_de_la_captura(client) -> None:
    """De extremo a extremo: la ruta que se vigila desde fuera.

    Sin este caso, la función podría existir y no llegar nunca a la respuesta
    —la forma de fallo de la 0098: la verificación fabricándose su sujeto—.
    """
    r = await client.get("/health")
    assert r.status_code in (200, 503)
    checks = r.json()["checks"]
    assert "error_capture" in checks, (
        "`/health` dejó de publicar el estado de la captura de errores. Sin "
        "eso, OPS-02 vuelve a comprobarse leyendo registros a mano."
    )
    assert checks["error_capture"] in ("ok", "disabled")


def test_los_dos_procesos_inician_la_captura() -> None:
    """El worker sobrescribe el CMD y nunca importa `main.py`.

    Es el fallo original de OPS-02 y el que más caro sale: un error en una
    tarea de fondo no produce un 500 que alguien vea — el informe simplemente
    no llega.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1]
    for entrada in ("app/main.py", "app/workers/celery_app.py"):
        fuente = (raiz / entrada).read_text(encoding="utf-8")
        assert "iniciar_captura_de_errores(" in fuente, (
            f"`{entrada}` dejó de iniciar la captura de errores."
        )
