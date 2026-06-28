"""BUG-079 — un 500 NO manejado debe salir CON headers CORS.

Las excepciones no manejadas las atrapa `ServerErrorMiddleware` (la capa más
externa, por ENCIMA de `CORSMiddleware`), así que su respuesta no pasa por
CORS y sale sin `Access-Control-Allow-Origin`. El browser la bloquea y el
front muestra "No se pudo conectar con el servidor" en vez del error real.
El handler global de `main.py` reinyecta los headers CORS.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

_BOOM_PATH = "/api/v1/_bug079_boom"


@pytest.mark.asyncio
async def test_bug079_unhandled_500_carries_cors_headers():
    from app.main import app

    async def _boom():
        raise RuntimeError("kaboom")

    # Ruta de prueba que revienta con una excepción que NO es HTTPException,
    # forzando el camino de ServerErrorMiddleware. Idempotente entre tests.
    if not any(getattr(r, "path", None) == _BOOM_PATH for r in app.router.routes):
        app.add_api_route(_BOOM_PATH, _boom, methods=["GET"])

    # raise_app_exceptions=False → httpx devuelve la respuesta 500 que el
    # handler envió (ServerErrorMiddleware re-lanza la excepción para que el
    # server la loguee, pero la respuesta ya salió con los headers CORS).
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        r = await c.get(_BOOM_PATH, headers={"Origin": "http://testclient"})

    assert r.status_code == 500
    # ALLOWED_ORIGINS de tests = "http://testclient" (ver conftest).
    assert r.headers.get("access-control-allow-origin") == "http://testclient"
    assert r.headers.get("access-control-allow-credentials") == "true"
    body = r.json()
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert "fields" in body


@pytest.mark.asyncio
async def test_bug079_no_origin_no_cors_headers():
    """Sin header Origin (no es request de browser cross-origin) no
    reinyectamos nada — el comportamiento default no cambia."""
    from app.main import app

    async def _boom():
        raise RuntimeError("kaboom")

    if not any(getattr(r, "path", None) == _BOOM_PATH for r in app.router.routes):
        app.add_api_route(_BOOM_PATH, _boom, methods=["GET"])

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        r = await c.get(_BOOM_PATH)

    assert r.status_code == 500
    assert "access-control-allow-origin" not in r.headers
