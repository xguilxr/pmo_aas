"""MCS SEG-01 · ASVS 8.2.1 — los datos del inquilino no se quedan en el disco.

«Verify the application sets sufficient anti-caching headers so that sensitive
data is not cached in modern browsers.»

Antes de esto el API no emitía **ninguna** cabecera de caché. Sin `Cache-Control`
ni `Expires`, la norma del navegador no es «no guardes»: es heurística, y una
respuesta `200` a un `GET` puede acabar en el caché de disco. La consecuencia
concreta —no la teórica— es que la cartera de proyectos de un inquilino sigue
en el perfil del navegador después de cerrar sesión, y en un equipo compartido
la lee el siguiente que se siente.

Esta suite fija las tres cosas que hacen falta para que el control siga
cumpliéndose mañana:

1. Que la cabecera esté (§1), también en las respuestas de error, que llevan
   igual el motivo del fallo y a veces el identificador que lo produjo.
2. Que **no** se aplique fuera del API (§2): `/health` lo consulta el
   comprobador de Railway y no lleva dato de nadie.
3. Que el endpoint que se sale de la norma lo siga haciendo a propósito (§3).
   `setdefault` deja que un endpoint gane, y eso es una puerta: si mañana
   alguien pone `max-age` en un listado, esta prueba no lo ve. Lo que sí ve es
   que el **único** que hoy se sale siga siendo el que se documentó.
"""
from __future__ import annotations

import pytest

from app.main import app

# ---------------------------------------------------------------------------
# §1 — Está en las respuestas del API, incluidas las de error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs821_no_store_en_respuesta_del_api(client):
    """Un 401 es una respuesta del API como cualquier otra."""
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.headers["Cache-Control"] == "no-store"


@pytest.mark.asyncio
async def test_asvs821_no_store_tambien_en_404(client):
    r = await client.get("/api/v1/__no_existe__")
    assert r.status_code == 404
    assert r.headers["Cache-Control"] == "no-store"


# ---------------------------------------------------------------------------
# §2 — Fuera del API no se toca
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs821_health_sin_no_store(client):
    """`/health` no devuelve dato de ningún inquilino y lo consulta el
    comprobador de Railway. Marcarlo `no-store` no protegería nada."""
    r = await client.get("/health")
    assert r.status_code == 200
    assert "Cache-Control" not in r.headers


# ---------------------------------------------------------------------------
# §3 — La única excepción sigue siendo una, y sigue siendo la misma
# ---------------------------------------------------------------------------


def test_asvs821_solo_un_endpoint_declara_su_propia_cache():
    """El logo del inquilino se cachea 60 s en el navegador y solo ahí.

    Es deliberado: lo pide cada pantalla, no es dato sensible, y `private`
    impide que lo guarde un intermediario. Lo que esta prueba impide es que la
    lista crezca sin que nadie lo note — `setdefault` deja ganar al endpoint,
    así que un `max-age` puesto en un listado pasaría en silencio.
    """
    import inspect
    import re

    from app.api.v1.endpoints import branding

    fuentes = {}
    for modulo in _modulos_de_endpoints():
        texto = inspect.getsource(modulo)
        for linea in re.findall(r'.*Cache-Control.*', texto):
            fuentes.setdefault(modulo.__name__, []).append(linea.strip())

    assert fuentes == {
        branding.__name__: ['headers={"Cache-Control": "private, max-age=60"},'],
    }, (
        f"Cambió quién declara su propia caché: {fuentes}. Si es a propósito, "
        f"documenta por qué ese dato puede quedarse en el navegador y actualiza "
        f"esta prueba; si no lo es, quita la cabecera y deja que el middleware "
        f"ponga `no-store`."
    )


def _modulos_de_endpoints():
    """Todos los módulos de `app.api.v1.endpoints`, importados."""
    import importlib
    import pkgutil

    from app.api.v1 import endpoints

    for info in pkgutil.iter_modules(endpoints.__path__):
        yield importlib.import_module(f"{endpoints.__name__}.{info.name}")


def test_asvs821_el_middleware_sigue_montado():
    """Sin esto, borrar el middleware entero dejaría §1 en verde solo si
    además alguien borra las pruebas. Se comprueba que sigue registrado."""
    nombres = [
        getattr(m, "__name__", "") or getattr(getattr(m, "func", None), "__name__", "")
        for m in _middlewares_http(app)
    ]
    assert "cabeceras_de_seguridad" in nombres, (
        f"El middleware de cabeceras no está montado. Encontrados: {nombres}"
    )


def _middlewares_http(aplicacion):
    for middleware in aplicacion.user_middleware:
        for valor in (*middleware.args, *middleware.kwargs.values()):
            if callable(valor):
                yield valor
