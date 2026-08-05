"""AM-10 — el bloqueo de cuenta deja de ser un arma contra el dueño.

`docs/architecture/modelo-amenazas.md` AM-10, el reverso de AM-09: quien
conociera un nombre de usuario podía fallar cinco veces y dejar esa cuenta
bloqueada un cuarto de hora. Con una lista de usuarios, al inquilino entero.

**Decisión del owner (2026-08-05): retardo creciente en vez de bloqueo duro.**
La diferencia es toda la amenaza: la cuenta nunca queda fuera, solo se responde
más despacio. Quien tecleó mal espera segundos; quien sufre un ataque espera,
como mucho, el tope.

Contra la adivinación protege igual o mejor —doce intentos por hora y por cuenta
con el tope por defecto— y el rociado lo corta AM-09 por IP. Las dos se
complementan: una mira la cuenta, la otra la IP.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.v1.endpoints.auth import espera_tras_fallos
from app.core.config import settings
from app.models.user import User
from tests.factories import create_tenant, create_user

CLAVE = "Str0ng-Pass-A1!"


@pytest.fixture(autouse=True)
def _sin_limite_por_ip(monkeypatch):
    """AM-09 no debe interferir: aquí se mide el retardo por cuenta."""
    monkeypatch.setattr("app.api.v1.endpoints.auth.excede", lambda *a, **k: False)
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.check_and_increment", lambda *a, **k: True
    )


async def _usuario(db_session):
    from uuid import uuid4

    sufijo = uuid4().hex[:8]
    inquilino = await create_tenant(db_session, slug=f"am10{sufijo}", name="AM-10")
    usuario = await create_user(
        db_session, tenant=inquilino, username=f"am10_{sufijo}",
        email=f"am10_{sufijo}@ejemplo.test", password=CLAVE,
    )
    return usuario


# ---------------------------------------------------------------------------
# La forma del retardo
# ---------------------------------------------------------------------------


def test_antes_del_umbral_no_se_espera_nada():
    """Teclear mal dos veces no puede costar nada. Es lo normal."""
    for fallos in range(settings.MAX_FAILED_LOGIN_ATTEMPTS):
        assert espera_tras_fallos(fallos) == 0


def test_a_partir_del_umbral_cada_fallo_duplica_la_espera():
    umbral = settings.MAX_FAILED_LOGIN_ATTEMPTS
    base = settings.LOGIN_BACKOFF_BASE_SECONDS

    assert espera_tras_fallos(umbral) == base
    assert espera_tras_fallos(umbral + 1) == base * 2
    assert espera_tras_fallos(umbral + 2) == base * 4


def test_la_espera_tiene_tope():
    """Sin tope, el retardo creciente **es** el bloqueo duro con otro nombre.

    Es la propiedad que cierra AM-10: por muchos intentos que haga un atacante,
    quien sufre el ataque nunca espera más de esto.
    """
    assert espera_tras_fallos(1000) == settings.LOGIN_BACKOFF_MAX_SECONDS
    assert settings.LOGIN_BACKOFF_MAX_SECONDS <= 600, (
        "Un tope de más de diez minutos vuelve a ser una denegación de servicio "
        "útil para un atacante."
    )


def test_ya_no_existe_el_bloqueo_de_quince_minutos():
    """`ACCOUNT_LOCK_MINUTES` era el arma. No debe volver por la puerta de atrás."""
    assert not hasattr(settings, "ACCOUNT_LOCK_MINUTES")


# ---------------------------------------------------------------------------
# Por HTTP — que la cuenta no quede fuera
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tras_el_umbral_se_pide_esperar_y_se_dice_cuanto(client, db_session):
    usuario = await _usuario(db_session)

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS):
        r = await client.post(
            "/api/v1/auth/login",
            json={"identifier": usuario.username, "password": "mal"},
        )
        assert r.status_code == 401

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": usuario.username, "password": "mal"},
    )
    cuerpo = r.json()["detail"]
    assert cuerpo["code"] == "ACCOUNT_LOCKED"
    # LEN-02: qué, por qué y qué hacer — con el número, para que la espera no
    # parezca indefinida.
    assert "segundos" in cuerpo["detail"]
    assert "Olvidaste tu contraseña" in cuerpo["detail"]


@pytest.mark.asyncio
async def test_pasada_la_espera_la_cuenta_entra(client, db_session):
    """La prueba de que ya no es un bloqueo: se espera y se entra."""
    usuario = await _usuario(db_session)

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS + 1):
        await client.post(
            "/api/v1/auth/login",
            json={"identifier": usuario.username, "password": "mal"},
        )

    # Se adelanta el reloj en vez de dormir: lo que se comprueba es que pasada
    # la espera no queda ningún bloqueo, no cuánto tarda el reloj.
    guardado = (
        await db_session.execute(select(User).where(User.id == usuario.id))
    ).scalar_one()
    guardado.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": usuario.username, "password": CLAVE},
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_acertar_borra_el_retardo(client, db_session):
    """Si el contador no se reintegra, el retardo se acumula para siempre."""
    usuario = await _usuario(db_session)

    for _ in range(2):
        await client.post(
            "/api/v1/auth/login",
            json={"identifier": usuario.username, "password": "mal"},
        )
    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": usuario.username, "password": CLAVE},
    )
    assert r.status_code == 200

    guardado = (
        await db_session.execute(select(User).where(User.id == usuario.id))
    ).scalar_one()
    assert guardado.failed_login_attempts == 0
    assert guardado.locked_until is None


@pytest.mark.asyncio
async def test_el_ataque_a_una_cuenta_no_alcanza_a_otra(client, db_session):
    """Es lo que AM-10 describe: con una lista de usuarios, el inquilino entero."""
    victima = await _usuario(db_session)
    vecino = await _usuario(db_session)

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS + 2):
        await client.post(
            "/api/v1/auth/login",
            json={"identifier": victima.username, "password": "mal"},
        )

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": vecino.username, "password": CLAVE},
    )
    assert r.status_code == 200, "El retardo es por cuenta, no por inquilino"
