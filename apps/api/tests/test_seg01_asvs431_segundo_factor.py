"""MCS SEG-01 · ASVS 4.3.1 — segundo factor para las interfaces de administración.

«Verify administrative interfaces use appropriate multi-factor authentication to
prevent unauthorized use.»

Decisión del owner (2026-08-07), ADR-035: código de seis dígitos por correo, con
la infraestructura de Resend que ya existe.

## Esta suite cubre cinco controles, no uno

Añadir un factor **fuera de banda** hace que dejen de «no aplicar» cuatro
controles que el mapeo tenía como NO APLICA, y cada uno exige algo concreto:

* `2.2.2` — el correo se usa como verificación **secundaria**, nunca en lugar de
  la contraseña. §1.
* `2.7.2` — caduca a los diez minutos. §3.
* `2.7.3` — un solo uso, y **solo para la petición que lo pidió**. §3.
* `2.7.4` — canal independiente del navegador. Es de diseño y se comprueba
  leyendo por dónde sale, no ejecutándolo.

`2.7.1` se queda **ACEPTADO**: pide ofrecer primero una alternativa más fuerte, y
aquí no hay ninguna. Está en ADR-035, no escondido.

## El modo de fallo que más importa

Un segundo factor se rompe silenciosamente de dos maneras: que se pueda saltar
(§2) y que se pueda adivinar (§4). Seis dígitos son un millón de combinaciones,
que sin freno se prueban enteras en minutos — el límite de intentos no es un
detalle, es lo que hace que el factor valga algo.
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.services import segundo_factor as sf

pytestmark = pytest.mark.con_segundo_factor


@pytest.fixture(autouse=True)
def _con_mfa(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_MFA_REQUIRED", True)


@pytest.fixture
def correos(monkeypatch):
    """Recoge los códigos que se habrían mandado.

    Se sustituye en `endpoints.auth` y no en `segundo_factor`: el endpoint
    importó el nombre directamente, así que tiene su propia referencia y
    parchear el módulo de origen no le afecta.
    """
    from app.api.v1.endpoints import auth as endpoint_auth

    enviados: list[tuple[str, str]] = []
    monkeypatch.setattr(
        endpoint_auth, "envia_codigo",
        lambda destino, codigo: enviados.append((destino, codigo)),
    )
    return enviados


async def _admin(db, sufijo: str):
    from tests.factories import create_admin_role, create_tenant, create_user

    tenant = await create_tenant(db, slug=f"mfa{sufijo}", name=f"Mfa{sufijo}")
    rol = await create_admin_role(db, tenant)
    return await create_user(
        db, tenant=tenant, username=f"mfa{sufijo}",
        email=f"mfa{sufijo}@acme.example.com", password="Zx9-Correcta-Larga!", roles=[rol],
    )


async def _entra(client, sufijo: str):
    return await client.post(
        "/api/v1/auth/login",
        json={"identifier": f"mfa{sufijo}@acme.example.com", "password": "Zx9-Correcta-Larga!"},
    )


# ---------------------------------------------------------------------------
# §1 — La contraseña correcta ya no basta para administración
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs431_el_admin_no_recibe_sesion_con_solo_la_contrasena(
    client, db_session, correos
):
    """Es el control entero: si aquí saliera una sesión, no hay segundo factor."""
    await _admin(db_session, "1")
    r = await _entra(client, "1")

    assert r.status_code == 202, r.text
    cuerpo = r.json()
    assert cuerpo["mfa_required"] is True
    assert cuerpo["desafio"]
    assert "access_token" not in cuerpo, "Salió una sesión sin el segundo factor"
    assert not any(
        "access_token" in c for c in r.headers.get_list("set-cookie")
    ), "Salió la cookie de sesión sin el segundo factor"


@pytest.mark.asyncio
async def test_asvs431_el_codigo_llega_al_correo_de_la_cuenta(client, db_session, correos):
    await _admin(db_session, "2")
    await _entra(client, "2")

    assert correos, "No se mandó ningún código"
    destino, codigo = correos[0]
    assert destino == "mfa2@acme.example.com"
    assert len(codigo) == sf.DIGITOS and codigo.isdigit()


@pytest.mark.asyncio
async def test_asvs431_con_el_codigo_correcto_entra(client, db_session, correos):
    """Sin esto la defensa se quita en un día, porque nadie podría entrar."""
    await _admin(db_session, "3")
    r = await _entra(client, "3")
    desafio = r.json()["desafio"]
    _, codigo = correos[0]

    r = await client.post(
        "/api/v1/auth/verificar-codigo", json={"desafio": desafio, "codigo": codigo}
    )
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]
    assert r.json()["user"]["email"] == "mfa3@acme.example.com"


@pytest.mark.asyncio
async def test_asvs222_a_un_usuario_normal_no_se_le_pide(client, db_session, correos):
    """`2.2.2` — el correo es verificación **secundaria** y solo donde hace
    falta. Pedírselo a quien no alcanza ninguna interfaz de administración sería
    fricción a cambio de nada."""
    from tests.factories import create_tenant, create_user

    tenant = await create_tenant(db_session, slug="mfanorm", name="MfaNorm")
    await create_user(
        db_session, tenant=tenant, username="normalito",
        email="normalito@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "normalito@acme.example.com", "password": "Zx9-Correcta-Larga!"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]
    assert not correos


def test_asvs222_el_codigo_nunca_sustituye_a_la_contrasena():
    """`2.2.2` — «not as a replacement for more secure authentication methods».

    El segundo factor se emite **después** de verificar la contraseña, dentro de
    `login`. No existe ninguna puerta que acepte un código sin contraseña
    previa: `verificar-codigo` solo consume desafíos que `login` creó.
    """
    import inspect

    from app.api.v1.endpoints import auth

    fuente = inspect.getsource(auth.login)
    assert "verify_password" in fuente
    assert fuente.index("verify_password") < fuente.index("necesita_segundo_factor"), (
        "El segundo factor se emite antes de comprobar la contraseña"
    )


# ---------------------------------------------------------------------------
# §2 — No se puede saltar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs431_un_desafio_inventado_no_entra(client, db_session, correos):
    await _admin(db_session, "4")
    await _entra(client, "4")

    r = await client.post(
        "/api/v1/auth/verificar-codigo",
        json={"desafio": "me-lo-invento", "codigo": "000000"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_asvs273_el_codigo_solo_sirve_para_su_desafio(client, db_session, correos):
    """`2.7.3` — «only for the original authentication request».

    Sin esto, un código pedido en una pestaña completaría el inicio de sesión
    que otra persona empezó en otra parte.
    """
    await _admin(db_session, "5")
    await _admin(db_session, "6")
    r5 = await _entra(client, "5")
    r6 = await _entra(client, "6")

    codigo_de_5 = correos[0][1]
    desafio_de_6 = r6.json()["desafio"]
    assert r5.json()["desafio"] != desafio_de_6

    r = await client.post(
        "/api/v1/auth/verificar-codigo",
        json={"desafio": desafio_de_6, "codigo": codigo_de_5},
    )
    assert r.status_code == 401, "El código de un desafío valió para otro"


@pytest.mark.asyncio
async def test_asvs273_el_codigo_es_de_un_solo_uso(client, db_session, correos):
    await _admin(db_session, "7")
    r = await _entra(client, "7")
    desafio = r.json()["desafio"]
    _, codigo = correos[0]

    primero = await client.post(
        "/api/v1/auth/verificar-codigo", json={"desafio": desafio, "codigo": codigo}
    )
    assert primero.status_code == 200

    segundo = await client.post(
        "/api/v1/auth/verificar-codigo", json={"desafio": desafio, "codigo": codigo}
    )
    assert segundo.status_code == 401, "El mismo código sirvió dos veces"


# ---------------------------------------------------------------------------
# §3 — Caduca, y a los diez minutos
# ---------------------------------------------------------------------------


def test_asvs272_la_vida_del_codigo_es_de_diez_minutos():
    """`2.7.2`, literal: «expires … after 10 minutes».

    Se fija el número y no solo «que caduque»: subirlo es exactamente lo que
    alguien haría para que dejara de molestar.
    """
    assert sf.VIDA_MINUTOS == 10


@pytest.mark.asyncio
async def test_asvs272_un_codigo_caducado_no_entra(client, db_session, correos):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.models.auth import AdminOtpCode

    await _admin(db_session, "8")
    r = await _entra(client, "8")
    desafio = r.json()["desafio"]
    _, codigo = correos[0]

    fila = (
        await db_session.execute(select(AdminOtpCode).where(AdminOtpCode.desafio == desafio))
    ).scalar_one()
    fila.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/verificar-codigo", json={"desafio": desafio, "codigo": codigo}
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# §4 — No se puede adivinar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs431_los_intentos_estan_acotados(client, db_session, correos):
    """Seis dígitos son un millón de combinaciones. Sin freno se prueban enteras
    en minutos, y entonces el segundo paso se salta más rápido que el primero."""
    await _admin(db_session, "9")
    r = await _entra(client, "9")
    desafio = r.json()["desafio"]
    _, correcto = correos[0]

    for _ in range(sf.INTENTOS_MAXIMOS):
        r = await client.post(
            "/api/v1/auth/verificar-codigo", json={"desafio": desafio, "codigo": "999999"}
        )
        assert r.status_code == 401

    # Agotados los intentos, ni siquiera el código bueno vale.
    r = await client.post(
        "/api/v1/auth/verificar-codigo", json={"desafio": desafio, "codigo": correcto}
    )
    assert r.status_code == 401, (
        "Tras agotar los intentos, el desafío seguía vivo: se puede probar sin "
        "límite pidiendo un código y machacándolo"
    )


@pytest.mark.asyncio
async def test_asvs431_el_codigo_no_se_guarda_en_claro(client, db_session, correos):
    """Un volcado de la base no puede entregar códigos utilizables tal cual."""
    from sqlalchemy import select

    from app.models.auth import AdminOtpCode

    await _admin(db_session, "10")
    r = await _entra(client, "10")
    _, codigo = correos[0]

    fila = (
        await db_session.execute(
            select(AdminOtpCode).where(AdminOtpCode.desafio == r.json()["desafio"])
        )
    ).scalar_one()
    assert fila.code_hash != codigo
    assert codigo not in fila.code_hash


@pytest.mark.asyncio
async def test_asvs431_todos_los_fallos_responden_igual(client, db_session, correos):
    """Distinguir «código incorrecto» de «desafío caducado» le diría a quien
    prueba si va por buen camino."""
    await _admin(db_session, "11")
    r = await _entra(client, "11")
    desafio = r.json()["desafio"]

    inventado = await client.post(
        "/api/v1/auth/verificar-codigo", json={"desafio": "no-existe", "codigo": "000000"}
    )
    incorrecto = await client.post(
        "/api/v1/auth/verificar-codigo", json={"desafio": desafio, "codigo": "000000"}
    )
    assert inventado.status_code == incorrecto.status_code == 401
    assert inventado.json() == incorrecto.json()


@pytest.mark.asyncio
async def test_asvs431_el_intento_fallido_queda_en_la_auditoria(client, db_session, correos):
    from sqlalchemy import select

    from app.models.audit import AuditLog

    await _admin(db_session, "12")
    r = await _entra(client, "12")
    await client.post(
        "/api/v1/auth/verificar-codigo",
        json={"desafio": r.json()["desafio"], "codigo": "000000"},
    )

    filas = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "mfa_failed"))
    ).scalars().all()
    assert filas, "Un segundo factor que falla sin dejar rastro no se puede vigilar"


def test_asvs431_el_correo_avisa_de_que_alguien_tiene_la_contrasena():
    """El código es además la primera alerta de intrusión: si llega sin haberlo
    pedido, alguien acertó la contraseña."""
    texto = sf.cuerpo_del_correo("123456")
    assert "123456" in texto
    assert "10 minutos" in texto
    assert "cámbiala" in texto.lower()


def test_asvs431_el_interruptor_viene_encendido():
    """Un control cuyo valor por defecto es «apagado» está apagado en producción
    el día que a alguien se le olvida encenderlo, que es siempre.

    Se lee el defecto de la clase, no el de esta sesión de pruebas —que la
    suite apaga a propósito—.
    """
    from app.core.config import Settings

    assert Settings.model_fields["ADMIN_MFA_REQUIRED"].default is True
