"""MCS DES-03 — la comprobación de salud tiene que comprobar algo.

> «Las verificaciones de salud DEBEN condicionar la aceptación de un despliegue.»

La mitad buena ya estaba: `apps/api/railway.toml` declara
`healthcheckPath = "/health"` y Railway no promueve un despliegue cuyo
healthcheck no responde. La mitad mala la encontró la auditoría R1: el endpoint
devolvía una constante. Atrapaba «el proceso no arrancó» y ningún otro caso —una
API desplegada contra una base inalcanzable respondía `ok` y se promovía igual.

Estas pruebas cubren las tres cosas que hacen que la condición sirva:

1. Con la base sana, sigue devolviendo 200 (si no, ningún despliegue promueve).
2. Con la base caída, devuelve un código que Railway rechaza.
3. La base **se toca de verdad**. Es el caso que distingue esta suite de una que
   solo lee el cuerpo de la respuesta: si mañana alguien devuelve
   `{"checks": {"database": "ok"}}` a mano, el punto 3 falla y los otros no.
"""
from __future__ import annotations

import asyncio

import pytest

from app.main import HEALTH_DB_TIMEOUT_SECONDS, _base_de_datos_responde


@pytest.mark.asyncio
async def test_con_la_base_sana_responde_200(client):
    resp = await client.get("/health")

    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["status"] == "ok"
    assert cuerpo["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_la_comprobacion_ejecuta_una_consulta(client, monkeypatch):
    """Sin esto, un `checks` escrito a mano pasaría por comprobación."""
    from app.db import session as db_session

    ejecutadas: list[str] = []
    fabrica_real = db_session.SessionLocal

    class SesionQueAnota:
        def __init__(self):
            self._sesion = fabrica_real()

        async def __aenter__(self):
            interna = await self._sesion.__aenter__()

            async def execute(consulta, *args, **kwargs):
                ejecutadas.append(str(consulta))
                return await type(interna).execute(interna, consulta, *args, **kwargs)

            monkeypatch.setattr(interna, "execute", execute, raising=False)
            return interna

        async def __aexit__(self, *args):
            return await self._sesion.__aexit__(*args)

    monkeypatch.setattr(db_session, "SessionLocal", lambda: SesionQueAnota())

    resp = await client.get("/health")

    assert resp.status_code == 200
    assert ejecutadas == ["SELECT 1"], (
        "`/health` no ejecutó `SELECT 1` contra la base. Devolver `checks` "
        "constante deja DES-03 tal y como la auditoría R1 lo encontró."
    )


@pytest.mark.asyncio
async def test_con_la_base_caida_el_despliegue_no_se_acepta(client, monkeypatch):
    """503 es lo que hace que Railway rechace la promoción del despliegue."""
    from app.db import session as db_session

    def cae(*args, **kwargs):
        raise OSError("no se pudo conectar con la base")

    monkeypatch.setattr(db_session, "SessionLocal", cae)

    resp = await client.get("/health")

    assert resp.status_code == 503
    cuerpo = resp.json()
    assert cuerpo["status"] == "degraded"
    assert cuerpo["checks"]["database"] == "unreachable"


@pytest.mark.asyncio
async def test_la_base_lenta_cuenta_como_caida(monkeypatch):
    """Colgarse agota la ventana de Railway y deja además la conexión ocupada.

    Se comprueba sobre el ayudante y no sobre el endpoint para no gastar el
    tiempo límite real en cada corrida de la suite.
    """
    from app.db import session as db_session

    monkeypatch.setattr("app.main.HEALTH_DB_TIMEOUT_SECONDS", 0.05)

    class SesionQueNuncaContesta:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def execute(self, *args, **kwargs):
            await asyncio.sleep(10)

    monkeypatch.setattr(db_session, "SessionLocal", lambda: SesionQueNuncaContesta())

    assert await _base_de_datos_responde() is False


def test_el_tiempo_limite_cabe_en_la_ventana_de_railway():
    """El límite propio tiene que dejar margen al `healthcheckTimeout` externo.

    Si creciera por encima, `/health` dejaría de responder «mal» a tiempo y
    volvería a ser indistinguible de un proceso colgado — que es el estado del
    que DES-03 quiere salir.
    """
    import re
    from pathlib import Path

    railway = Path(__file__).resolve().parents[1] / "railway.toml"
    declarado = re.search(r"healthcheckTimeout\s*=\s*(\d+)", railway.read_text())

    assert declarado, "railway.toml ya no declara healthcheckTimeout"
    assert HEALTH_DB_TIMEOUT_SECONDS < int(declarado.group(1))
