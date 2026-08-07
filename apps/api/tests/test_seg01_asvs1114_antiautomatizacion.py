"""MCS SEG-01 · ASVS 11.1.4 — presupuesto de peticiones por cuenta.

«Verify that the application has anti-automation controls to protect against
excessive calls such as mass data exfiltration, business logic requests, file
uploads or denial of service attacks.»

## Qué faltaba exactamente

El tamaño de página **ya** estaba topado en 100, en los cincuenta listados que
lo declaran. Lo que no estaba topado era cuántas veces se pide: una cuenta
válida podía recorrer la cartera entera del inquilino, página a página, tan
rápido como aguantara la red. Un tope por página no frena una exfiltración —solo
decide en cuántos trozos se lleva el dato—.

## Los dos modos de fallo que esta suite vigila

El obvio es que no corte. El **caro** es que corte a quien está trabajando: un
límite que molesta se sube al día siguiente hasta que deja de servir, y entonces
el control existe en el código y no en la práctica. Por eso §2 fija que el
presupuesto tenga holgura sobre el uso real, y §3 que un Redis caído no deje a
nadie fuera.
"""
from __future__ import annotations

import pytest

from app.services import rate_limit
from app.services.rate_limit import PRESUPUESTO_POR_MINUTO, verifica_presupuesto


class _RedisFalso:
    """Cuenta en memoria, con la misma forma que usa `check_and_increment`."""

    def __init__(self) -> None:
        self.valores: dict[str, int] = {}
        self.expiraciones: dict[str, int] = {}

    def incr(self, clave):
        self.valores[clave] = self.valores.get(clave, 0) + 1
        return self.valores[clave]

    def expire(self, clave, segundos):
        self.expiraciones[clave] = segundos

    def get(self, clave):
        return self.valores.get(clave)

    def delete(self, clave):
        self.valores.pop(clave, None)


@pytest.fixture
def redis_falso(monkeypatch):
    falso = _RedisFalso()
    monkeypatch.setattr(rate_limit, "_get_client", lambda: falso)
    return falso


# ---------------------------------------------------------------------------
# §1 — Corta cuando se pasa
# ---------------------------------------------------------------------------


def test_asvs1114_el_presupuesto_corta_al_superarse(redis_falso):
    for numero in range(PRESUPUESTO_POR_MINUTO):
        assert verifica_presupuesto("u1"), f"cortó en la petición {numero + 1}"
    assert not verifica_presupuesto("u1"), "La que pasa del tope tiene que caer"


def test_asvs1114_el_presupuesto_es_por_cuenta_y_no_global(redis_falso):
    """Si fuera global, el primero que exfiltra deja al resto sin plataforma —
    que es convertir el control en la denegación de servicio que evita."""
    for _ in range(PRESUPUESTO_POR_MINUTO):
        verifica_presupuesto("u1")
    assert not verifica_presupuesto("u1")
    assert verifica_presupuesto("u2"), "La otra cuenta no ha gastado nada"


def test_asvs1114_la_ventana_se_fija_al_primer_uso(redis_falso):
    """Sin `EXPIRE` el contador no caduca nunca y el presupuesto pasa a ser
    de por vida: a las mil peticiones, la cuenta queda inservible para siempre."""
    verifica_presupuesto("u3")
    assert redis_falso.expiraciones["rl:api:user:u3"] == 60


# ---------------------------------------------------------------------------
# §2 — No corta a quien trabaja
# ---------------------------------------------------------------------------

#: Peticiones que hace la pantalla que más pide de toda la aplicación. Es una
#: cota alta a propósito: si el presupuesto aguanta el peor caso repetido, no
#: va a cortar a nadie haciendo su trabajo.
CARGA_DE_TABLERO = 30


def test_asvs1114_el_presupuesto_tiene_holgura_sobre_el_uso_real():
    """El modo de fallo caro: un límite que molesta se sube hasta que no sirve.

    Veinte cargas completas del tablero en un minuto es más de lo que hace una
    persona, y tiene que caber sin acercarse al tope.
    """
    assert PRESUPUESTO_POR_MINUTO >= CARGA_DE_TABLERO * 20, (
        f"{PRESUPUESTO_POR_MINUTO}/min deja menos de veinte cargas de tablero "
        f"por minuto. Va a cortar a gente trabajando, y entonces se sube hasta "
        f"que deje de servir."
    )


def test_asvs1114_el_presupuesto_sigue_frenando_la_exfiltracion():
    """Y el límite por arriba: con páginas de 100, el presupuesto tiene que
    dejar la exfiltración en un orden de magnitud incómodo, no cómodo."""
    filas_por_minuto = PRESUPUESTO_POR_MINUTO * 100
    assert filas_por_minuto <= 100_000, (
        f"{filas_por_minuto} filas/minuto es barra libre: el control no está "
        f"frenando nada."
    )


# ---------------------------------------------------------------------------
# §3 — Un Redis caído no deja a nadie fuera
# ---------------------------------------------------------------------------


def test_asvs1114_sin_redis_se_deja_pasar(monkeypatch):
    """Fail-open, como el resto del módulo.

    Dejar a todos los inquilinos sin API porque el limitador no puede contar
    sería un daño mayor —y mucho más probable— que el que este control evita.
    """
    monkeypatch.setattr(rate_limit, "_get_client", lambda: None)
    for _ in range(PRESUPUESTO_POR_MINUTO * 2):
        assert verifica_presupuesto("u4")


def test_asvs1114_si_redis_falla_se_deja_pasar(monkeypatch):
    class Roto:
        def incr(self, clave):
            raise ConnectionError("caído")

    monkeypatch.setattr(rate_limit, "_get_client", lambda: Roto())
    assert verifica_presupuesto("u5")


# ---------------------------------------------------------------------------
# §4 — Está cableado en el único sitio por el que pasan todas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs1114_el_api_devuelve_429_al_agotarlo(client, db_session, redis_falso):
    """De punta a punta: se agota el presupuesto y el siguiente listado cae.

    Lo que esto fija, y las pruebas de unidad no, es que el presupuesto está
    cableado en `get_current_user` — o sea, en **todos** los endpoints
    autenticados y no en los que alguien se acordó de marcar.
    """
    from tests.factories import create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="auto", name="Auto")
    await create_user(
        db_session, tenant=tenant, username="scraper",
        email="scraper@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "scraper@acme.example.com", "Zx9-Correcta-Larga!")

    # `login` no pasa por `get_current_user`, así que el contador está a cero.
    r = await client.get("/api/v1/projects", headers=sesion["_authz"])
    assert r.status_code == 200, r.text

    clave = [k for k in redis_falso.valores if k.startswith("rl:api:user:")]
    assert clave, f"No se contó la petición: {redis_falso.valores}"
    redis_falso.valores[clave[0]] = PRESUPUESTO_POR_MINUTO

    r = await client.get("/api/v1/projects", headers=sesion["_authz"])
    assert r.status_code == 429, r.text


@pytest.mark.asyncio
async def test_asvs1114_el_429_dice_que_hacer(client, db_session, redis_falso):
    """LEN-02 — un 429 sin plazo no le dice a nadie qué hacer con él."""
    from tests.factories import create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="auto2", name="Auto2")
    await create_user(
        db_session, tenant=tenant, username="scraper2",
        email="scraper2@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "scraper2@acme.example.com", "Zx9-Correcta-Larga!")
    await client.get("/api/v1/projects", headers=sesion["_authz"])
    clave = next(k for k in redis_falso.valores if k.startswith("rl:api:user:"))
    redis_falso.valores[clave] = PRESUPUESTO_POR_MINUTO

    r = await client.get("/api/v1/projects", headers=sesion["_authz"])
    assert r.status_code == 429
    assert r.json()["detail"]["detail"].strip(), "El 429 llega sin texto"
