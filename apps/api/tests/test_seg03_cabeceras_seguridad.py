"""SEG-03 — cabeceras de seguridad en toda respuesta.

Auditoría MCS 2026-08-03: la aplicación solo montaba `CORSMiddleware`. Estas
pruebas existen para que la ausencia de las cabeceras vuelva a fallar si alguien
retira el middleware, no para documentar que un día estuvieron.
"""
import pytest


@pytest.mark.asyncio
async def test_seg03_cabeceras_presentes_en_respuesta_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in r.headers["Permissions-Policy"]


@pytest.mark.asyncio
async def test_seg03_csp_bloquea_enmarcado_y_scripts(client):
    r = await client.get("/health")
    csp = r.headers["Content-Security-Policy"]
    # Es un API: no sirve HTML propio, así que puede negarlo todo por defecto.
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


@pytest.mark.asyncio
async def test_seg03_cabeceras_tambien_en_respuestas_de_error(client):
    """Un 404 sigue siendo una respuesta que el navegador procesa."""
    r = await client.get("/api/v1/__no_existe__")
    assert r.status_code == 404
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
async def test_seg03_docs_sin_csp_restrictiva(client):
    """Swagger carga JS y CSS de CDN: con `default-src 'none'` no renderiza.

    Se excluye a propósito. Si alguien endurece la CSP sin contemplar `/docs`,
    esta prueba lo avisa antes de que el owner descubra la página en blanco.
    """
    r = await client.get("/docs")
    assert r.status_code == 200
    assert "Content-Security-Policy" not in r.headers
    # Las demás cabeceras sí aplican.
    assert r.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.asyncio
async def test_seg03_hsts_ausente_en_desarrollo(client):
    """En local se sirve por HTTP; HSTS dejaría el navegador fijado a HTTPS
    para `localhost` y es engorroso de revertir. En producción sí se emite."""
    r = await client.get("/health")
    assert "Strict-Transport-Security" not in r.headers
