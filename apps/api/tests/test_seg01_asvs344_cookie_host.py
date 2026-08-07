"""MCS SEG-01 · ASVS 3.4.4 — la cookie de sesión lleva prefijo `__Host-`.

«Verify that cookie-based session tokens use the "__Host-" prefix so cookies are
only sent to the host that initially set the cookie.»

## Qué compra el prefijo, que no es obvio

`__Host-` no lo comprueba el servidor: lo impone el **navegador**, que rechaza
la cookie si le falta cualquiera de las tres condiciones —`Secure`, sin
`Domain`, `Path=/`—. Y por eso cierra un ataque que ninguna validación nuestra
alcanza: sin el prefijo, **un subdominio puede sobrescribir la cookie del
dominio padre**. Un blog o el panel de un proveedor colgados de
`*.pmo-aas.com` bastan para plantarle a alguien una cookie de sesión ajena, y
la que llega al API es sintácticamente perfecta — no hay nada que detectar.

## Lo que fija esta suite

1. Que en producción la cookie salga con el nombre, el `Path` y los atributos
   que el prefijo exige (§1). Los tres, porque **dos de tres no valen**: el
   navegador tira la cookie entera y el síntoma es «no puedo iniciar sesión»,
   sin más pista.
2. Que fuera de producción NO lleve el prefijo (§2). Ahí se sirve por HTTP, no
   se puede emitir `Secure`, y una cookie `__Host-` no se guardaría.
3. Que la ventana de compatibilidad funcione en las dos direcciones (§3): se
   acepta la cookie vieja al leer, y al cerrar sesión se borran **todas** sus
   formas. Una cookie de refresco que sobrevive a «cerrar sesión» es lo que
   este cambio existe para impedir, y solo se borra desde el `Path` con que se
   creó.
"""
from __future__ import annotations

import logging

import pytest

from app.core import cookies


class _RespuestaFalsa:
    """Recoge lo que se le pasa a `set_cookie`/`delete_cookie`.

    Se usa un doble y no la respuesta real porque lo que se comprueba son los
    **atributos** de la cookie, y `Response` los serializa a una cabecera
    `Set-Cookie` que habría que volver a parsear para afirmar sobre ellos.
    """

    def __init__(self) -> None:
        self.fijadas: list[tuple[str, str, dict]] = []
        self.borradas: list[tuple[str, dict]] = []

    def set_cookie(self, clave, valor, **kw):
        self.fijadas.append((clave, valor, kw))

    def delete_cookie(self, clave, **kw):
        self.borradas.append((clave, kw))


class _PeticionFalsa:
    def __init__(self, galletas: dict[str, str]) -> None:
        self.cookies = galletas


@pytest.fixture
def en_produccion(monkeypatch):
    monkeypatch.setattr(cookies.settings, "PYTHON_ENV", "production")


# ---------------------------------------------------------------------------
# §1 — En producción, las tres condiciones del prefijo, juntas
# ---------------------------------------------------------------------------


def test_asvs344_la_cookie_lleva_prefijo_y_sus_tres_condiciones(en_produccion):
    resp = _RespuestaFalsa()
    cookies.fijar(resp, cookies.REFRESCO, "abc", max_age=60)

    assert len(resp.fijadas) == 1
    clave, valor, kw = resp.fijadas[0]

    assert clave == "__Host-refresh_token"
    assert valor == "abc"
    # Las tres condiciones que el navegador exige para aceptar el prefijo.
    assert kw["secure"] is True, "`__Host-` sin `Secure` lo rechaza el navegador"
    assert kw["path"] == "/", "`__Host-` exige `Path=/`"
    assert "domain" not in kw, "`__Host-` no admite `Domain`"
    # Y las que no son del prefijo pero sí de una cookie de sesión.
    assert kw["httponly"] is True
    assert kw["samesite"] == "strict"


@pytest.mark.parametrize("entorno", ["development", "test", "production"])
def test_asvs344_el_prefijo_y_secure_van_siempre_juntos(entorno, monkeypatch):
    """El invariante que hace que §1 no se pueda romper a medias.

    Si alguien desacopla el nombre de `Secure`, saldría una cookie llamada
    `__Host-…` que el navegador tira sin avisar: sesión imposible y ni un error
    que lo explique. Se comprueba en los tres entornos, no solo en el que
    interesa, porque el fallo aparece justo en el que no se estaba mirando.
    """
    monkeypatch.setattr(cookies.settings, "PYTHON_ENV", entorno)
    resp = _RespuestaFalsa()
    cookies.fijar(resp, cookies.REFRESCO, "v", max_age=60)

    clave, _, kw = resp.fijadas[0]
    assert clave.startswith("__Host-") == kw["secure"], (
        f"En {entorno!r} el prefijo y `Secure` no van juntos: "
        f"{clave!r}, secure={kw['secure']}"
    )


# ---------------------------------------------------------------------------
# §2 — Fuera de producción, sin prefijo, porque no hay HTTPS
# ---------------------------------------------------------------------------


def test_asvs344_en_desarrollo_sin_prefijo(monkeypatch):
    monkeypatch.setattr(cookies.settings, "PYTHON_ENV", "development")
    resp = _RespuestaFalsa()
    cookies.fijar(resp, cookies.REFRESCO, "abc", max_age=60)

    clave, _, kw = resp.fijadas[0]
    assert clave == "refresh_token"
    assert kw["secure"] is False
    # El `Path` sí se unifica en todos los entornos: que dev y producción
    # difieran en algo más que el nombre es cómo se cuela un fallo que solo
    # aparece al desplegar.
    assert kw["path"] == "/"


# ---------------------------------------------------------------------------
# §3 — La ventana: se lee la vieja, y se borran todas las formas
# ---------------------------------------------------------------------------


def test_asvs344_se_lee_la_cookie_nueva_primero(en_produccion, caplog):
    peticion = _PeticionFalsa(
        {"__Host-refresh_token": "nueva", "refresh_token": "vieja"}
    )
    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        assert cookies.leer(peticion, cookies.REFRESCO) == "nueva"
    assert not caplog.records, "La nueva no debe contar como uso de la ventana"


def test_asvs344_se_acepta_la_cookie_vieja_y_deja_rastro(en_produccion, caplog):
    """Quien inició sesión antes del despliegue tiene que poder cerrarla."""
    peticion = _PeticionFalsa({"refresh_token": "vieja"})
    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        assert cookies.leer(peticion, cookies.REFRESCO) == "vieja"

    # `campo=` lleva `Ventana.viejo` —el nombre que llegó—, no la clave del
    # registro. Es lo que se busca en Sentry para contar quién sigue trayéndola.
    assert any(
        "compat.nombre_viejo" in r.getMessage()
        and "campo=refresh_token" in r.getMessage()
        and "nuevo=__Host-refresh_token" in r.getMessage()
        and "adr=ADR-033" in r.getMessage()
        for r in caplog.records
    ), f"Sin rastro no hay criterio para cerrar la ventana: {[r.getMessage() for r in caplog.records]}"


def test_asvs344_sin_cookie_devuelve_none(en_produccion):
    assert cookies.leer(_PeticionFalsa({}), cookies.REFRESCO) is None


def test_asvs344_al_cerrar_sesion_se_borran_todas_las_formas(en_produccion):
    """Tres formas: la nueva, y la vieja con sus dos `Path` posibles.

    Una cookie solo se borra desde el `Path` con que se creó. Un
    `delete_cookie` a secas dejaría viva la de `/api/v1/auth`.
    """
    resp = _RespuestaFalsa()
    cookies.borrar(resp, cookies.REFRESCO)

    borradas = {(clave, kw.get("path")) for clave, kw in resp.borradas}
    assert borradas == {
        ("__Host-refresh_token", "/"),
        ("refresh_token", "/"),
        ("refresh_token", "/api/v1/auth"),
    }, f"Falta borrar alguna forma: {borradas}"


# ---------------------------------------------------------------------------
# §4 — De punta a punta contra el endpoint real
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs344_el_login_real_emite_la_cookie_con_prefijo(
    client, db_session, monkeypatch
):
    """De punta a punta, sobre la cabecera `Set-Cookie` que ve el navegador.

    Los apartados anteriores prueban el helper; este prueba que el endpoint lo
    **usa**, que es lo que se rompe cuando alguien añade un `set_cookie` a mano
    en un flujo nuevo.
    """
    from tests.factories import create_tenant, create_user

    monkeypatch.setattr(cookies.settings, "PYTHON_ENV", "production")
    tenant = await create_tenant(db_session, slug="host-prefix", name="HostPrefix")
    await create_user(
        db_session, tenant=tenant, username="cookieuser",
        email="cookie@acme.example.com", password="Abcdefgh123!",
    )

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "cookie@acme.example.com", "password": "Abcdefgh123!"},
    )
    assert r.status_code == 200, r.text

    galletas = [c for c in r.headers.get_list("set-cookie") if "refresh_token" in c]
    assert len(galletas) == 1, f"Se esperaba una sola cookie de refresco: {galletas}"
    cabecera = galletas[0]

    assert cabecera.startswith("__Host-refresh_token="), cabecera
    assert "Path=/;" in cabecera or cabecera.rstrip().endswith("Path=/"), cabecera
    assert "Secure" in cabecera, cabecera
    assert "HttpOnly" in cabecera, cabecera
    assert "Domain=" not in cabecera, cabecera
