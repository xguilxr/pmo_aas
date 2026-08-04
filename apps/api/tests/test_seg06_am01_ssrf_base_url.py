"""B5 · MCS SEG-06, amenaza AM-01 — el inquilino elige el proveedor, no la red.

El modo BYO deja que un administrador de inquilino configure `base_url`. Antes
de esta suite el campo se validaba como `str | None` con `max_length=500`, y
`POST /api/v1/admin/ai/provider/test` lo usaba para hacer una petición **desde
dentro de la plataforma** devolviendo estado, 120 caracteres del cuerpo y la
latencia. Comprobado contra servidores locales: las respuestas de un puerto
abierto, uno cerrado y un nombre inexistente se distinguían entre sí, así que
servía para barrer la red privada de Railway y leer trozos de lo que hubiera.

Lo que esta suite fija:

1. Los destinos internos se rechazan por forma (§1) y por resolución (§2).
2. Los proveedores legítimos siguen funcionando (§3). Sin esto la defensa se
   quita en dos semanas, porque rompe el producto.
3. **No queda oráculo** (§4): todos los destinos rechazados producen la misma
   respuesta, así que ya no se puede deducir nada de la diferencia.
4. La defensa cubre las tres puertas (§5): escritura de configuración, prueba
   de conexión y ejecución real.

Lo que NO fija, porque la defensa no lo cierra: la reasignación de DNS. Entre la
comprobación y la petición hay dos resoluciones distintas. Está escrito en el
docstring de `app/core/url_externa.py` y en el modelo de amenazas.
"""
from __future__ import annotations

import socket

import pytest

from app.core.url_externa import (
    _resuelve_a_privada,
    asegurar_url_externa,
    motivo_url_insegura,
)

# ---------------------------------------------------------------------------
# §1 — Destinos que no pueden alcanzarse, juzgados sin resolver el nombre
# ---------------------------------------------------------------------------

INTERNOS = [
    ("bucle local", "https://127.0.0.1:8080/v1"),
    ("bucle local por nombre", "https://localhost/v1"),
    ("bucle local IPv6", "https://[::1]/v1"),
    ("privada 10/8", "https://10.0.0.5/v1"),
    ("privada 172.16/12", "https://172.16.4.9/v1"),
    ("privada 192.168/16", "https://192.168.1.10/v1"),
    ("metadatos de nube", "https://169.254.169.254/latest/meta-data/"),
    ("metadatos de Google", "https://metadata.google.internal/v1"),
    ("red privada de Railway", "https://redis.railway.internal:6379/v1"),
    ("sufijo .internal", "https://postgres.interno.internal/v1"),
    ("sufijo .local", "https://impresora.local/v1"),
    ("kubernetes", "https://api.svc.cluster.local/v1"),
    ("dirección sin especificar", "https://0.0.0.0/v1"),
    ("IPv4 mapeada en IPv6", "https://[::ffff:127.0.0.1]/v1"),
    ("punto final sobrante", "https://localhost./v1"),
    ("mayúsculas", "https://LOCALHOST/v1"),
]


@pytest.mark.parametrize("url", [u for _, u in INTERNOS], ids=[n for n, _ in INTERNOS])
def test_am01_los_destinos_internos_se_rechazan(url: str):
    assert motivo_url_insegura(url) is not None, (
        f"{url!r} llegaría a la red interna desde nuestra propia infraestructura"
    )


ESQUEMAS_MALOS = [
    "http://api.openai.com/v1",     # en claro: viajan minutas y RAID
    "file:///etc/passwd",
    "gopher://127.0.0.1:6379/_INFO",
    "ftp://interno/v1",
    "//api.openai.com/v1",          # sin esquema
    "api.openai.com/v1",
]


@pytest.mark.parametrize("url", ESQUEMAS_MALOS)
def test_am01_solo_se_admite_https(url: str):
    assert motivo_url_insegura(url) is not None


@pytest.mark.parametrize("url", [None, "", "   ", "https://", "https:///v1"])
def test_am01_las_urls_vacias_o_sin_host_se_rechazan(url):
    assert motivo_url_insegura(url) is not None


# ---------------------------------------------------------------------------
# §2 — Destinos que solo se ven al resolver el nombre
# ---------------------------------------------------------------------------


def _falsa_resolucion(direcciones: list[str]):
    def _fake(host, port, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (d, 0))
            for d in direcciones
        ]
    return _fake


def test_am01_un_nombre_publico_que_apunta_dentro_se_rechaza(monkeypatch):
    """El caso que la comprobación de forma no puede ver: un dominio que
    parece de un proveedor y tiene un registro A hacia 127.0.0.1."""
    monkeypatch.setattr(socket, "getaddrinfo", _falsa_resolucion(["127.0.0.1"]))
    assert _resuelve_a_privada("proveedor-que-parece-legitimo.example") is not None


def test_am01_basta_con_que_una_sola_direccion_sea_interna(monkeypatch):
    """Un nombre con un registro público y otro privado sirve para lo mismo
    que uno solo privado, así que se miran todas."""
    monkeypatch.setattr(
        socket, "getaddrinfo", _falsa_resolucion(["93.184.216.34", "10.1.2.3"])
    )
    assert _resuelve_a_privada("mixto.example") is not None


def test_am01_un_nombre_publico_de_verdad_pasa(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _falsa_resolucion(["93.184.216.34"]))
    assert _resuelve_a_privada("publico.example") is None


def test_am01_un_fallo_de_resolucion_no_es_un_rechazo(monkeypatch):
    """Si el nombre no resuelve, la petición tampoco va a llegar a ninguna
    parte. Rechazar aquí convertiría cualquier hipo del DNS en un error de
    configuración que el administrador no puede explicarse."""
    def _falla(*a, **k):
        raise OSError("getaddrinfo failed")

    monkeypatch.setattr(socket, "getaddrinfo", _falla)
    assert _resuelve_a_privada("no-resuelve.example") is None


# ---------------------------------------------------------------------------
# §3 — Control negativo: los proveedores legítimos siguen funcionando
# ---------------------------------------------------------------------------

LEGITIMOS = [
    "https://api.openai.com/v1",
    "https://api.together.xyz/v1",
    "https://my-resource.openai.azure.com",
    "https://api.example.com/v1",
    "https://llm.midominio.com:8443/v1",
    "https://93.184.216.34/v1",          # IP pública literal: válida
]


@pytest.mark.parametrize("url", LEGITIMOS)
def test_am01_los_proveedores_legitimos_no_se_rompen(url: str):
    """Una defensa que rechaza todo se quita en dos semanas, y entonces no
    defiende nada. Aquí entran los mismos valores que usan las suites de
    US-104 y US-110."""
    assert motivo_url_insegura(url) is None, f"{url!r} es un destino legítimo"


@pytest.mark.asyncio
async def test_am01_asegurar_deja_pasar_un_destino_publico(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _falsa_resolucion(["93.184.216.34"]))
    await asegurar_url_externa("https://api.example.com/v1")  # no lanza


@pytest.mark.asyncio
async def test_am01_asegurar_lanza_ante_un_destino_interno():
    with pytest.raises(ValueError, match="base_url rechazada"):
        await asegurar_url_externa("https://169.254.169.254/latest/meta-data/")


# ---------------------------------------------------------------------------
# §4 — Ya no queda oráculo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_am01_los_destinos_rechazados_son_indistinguibles():
    """Lo que hacía peligroso a este endpoint no era una respuesta concreta
    sino la DIFERENCIA entre ellas: puerto abierto, puerto cerrado y nombre
    inexistente contestaban cosas distintas, y esa diferencia es el escaneo.

    Ahora los tres se cortan antes de tocar la red y contestan lo mismo salvo
    el nombre del host, así que no hay nada que deducir.
    """
    from app.api.v1.endpoints.admin_ai import _ping_byo_provider

    destinos = [
        "https://127.0.0.1:8080",      # habría estado abierto
        "https://127.0.0.1:1",         # habría estado cerrado
        "https://no-existe.internal",  # no habría resuelto
        "https://10.0.0.5",
    ]
    resultados = [
        await _ping_byo_provider("custom", "k", "m", d) for d in destinos
    ]
    assert all(r.ok is False for r in resultados)
    assert {r.code for r in resultados} == {"BASE_URL_NO_PERMITIDA"}
    # Ninguna respuesta lleva latencia: no se llegó a abrir conexión, así que
    # tampoco se puede cronometrar la diferencia.
    assert all(r.latency_ms is None for r in resultados)


# ---------------------------------------------------------------------------
# §5 — Las tres puertas
# ---------------------------------------------------------------------------


def test_am01_la_escritura_de_configuracion_rechaza(monkeypatch):
    """Puerta 1: guardar la configuración."""
    from pydantic import ValidationError

    from app.api.v1.endpoints.admin_ai import BYOConfigIn

    with pytest.raises(ValidationError):
        BYOConfigIn(
            provider="custom", api_key="k", model="m",
            base_url="https://169.254.169.254/v1",
        )


def test_am01_la_escritura_admite_un_destino_legitimo():
    from app.api.v1.endpoints.admin_ai import BYOConfigIn

    cfg = BYOConfigIn(
        provider="custom", api_key="k", model="m",
        base_url="https://api.together.xyz/v1",
    )
    assert cfg.base_url == "https://api.together.xyz/v1"


@pytest.mark.asyncio
async def test_am01_la_ejecucion_real_tambien_rechaza():
    """Puerta 3, y es la que protege a quien ya tuviera guardada una
    `base_url` interna ANTES de que existiera la comprobación de escritura.
    Sin esto la defensa solo cubriría configuraciones nuevas."""
    from app.services.ai.provider import generate_for_tenant

    with pytest.raises(ValueError, match="base_url rechazada"):
        await generate_for_tenant(
            "hola",
            tenant_ai_mode="byo",
            byo_config={
                "provider": "custom",
                "api_key": "k",
                "base_url": "https://10.0.0.5/v1",
            },
        )


@pytest.mark.asyncio
async def test_am01_el_modo_plataforma_no_se_toca():
    """Control negativo: el modo `platform` no lleva `base_url` del inquilino,
    así que la defensa no debe entrometerse en su camino."""
    from app.services.ai.provider import generate_for_tenant

    res = await generate_for_tenant("hola", tenant_ai_mode="disabled")
    assert res.model == "stub"
