"""BUG-079 — un 500 NO manejado debe salir CON headers CORS.

Las excepciones no manejadas las atrapa `ServerErrorMiddleware` (la capa más
externa, por ENCIMA de `CORSMiddleware`), así que su respuesta no pasa por
CORS y sale sin `Access-Control-Allow-Origin`. El browser la bloquea y el
front muestra "No se pudo conectar con el servidor" en vez del error real.
El handler global de `main.py` reinyecta los headers CORS.

Importante: construimos un app AISLADO que reusa el handler real de
`app.main` (`unhandled_exception_handler`) en lugar de añadir una ruta al app
global. Añadir una ruta al app global la dejaba registrada para toda la sesión
de pytest y `test_permission_matrix` la marcaba como endpoint sin gate.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import unhandled_exception_handler


def _build_isolated_app() -> FastAPI:
    app = FastAPI()
    # Mismo CORS que producción (app.main).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # El handler REAL de app.main.
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/boom")
    async def _boom():
        raise RuntimeError("kaboom")

    return app


@pytest.mark.asyncio
async def test_bug079_unhandled_500_carries_cors_headers():
    # raise_app_exceptions=False → httpx devuelve la respuesta 500 que el
    # handler envió (ServerErrorMiddleware re-lanza la excepción para que el
    # server la loguee, pero la respuesta ya salió con los headers CORS).
    transport = ASGITransport(app=_build_isolated_app(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        r = await c.get("/boom", headers={"Origin": "http://testclient"})

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
    transport = ASGITransport(app=_build_isolated_app(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        r = await c.get("/boom")

    assert r.status_code == 500
    assert "access-control-allow-origin" not in r.headers
