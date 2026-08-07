"""MCS SEG-01 · ASVS 8.3.3 — texto claro sobre los datos, y consentimiento.

«Verify that users are provided clear language regarding collection and use of
supplied personal information and that users have provided opt-in consent for
the use of that data before it is used in any way.»

## Dónde va el consentimiento si no hay registro

En este producto las cuentas las crea un administrador: no hay alta por
autoservicio donde poner una casilla. El sitio es el **primer inicio de sesión**
—decisión del owner—, y la pantalla vuelve a salir **si el aviso cambia**.

## Lo que hace falta vigilar, que no es que exista la pantalla

Un consentimiento se rompe de tres formas, y las tres son silenciosas:

1. **Que se dé por hecho.** Rellenar las cuentas viejas con la fecha de la
   migración habría fabricado un consentimiento que nadie dio. §1.
2. **Que caduque sin que nadie se entere.** Si al cambiar el aviso la pantalla
   no vuelve a salir, lo aceptado y lo aplicado dejan de ser lo mismo. §2.
3. **Que lo decida el cliente.** Si la versión aceptada viniera en el cuerpo de
   la petición, bastaría con mandar una antigua para que la pantalla no
   apareciera nunca más. §3.
"""
from __future__ import annotations

import pytest

from app.services import aviso_privacidad as aviso

# ---------------------------------------------------------------------------
# §1 — Nadie consiente por omisión
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs833_una_cuenta_nueva_debe_aceptar(client, db_session):
    from tests.factories import create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="priv1", name="Priv1")
    await create_user(
        db_session, tenant=tenant, username="priv1u",
        email="priv1@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "priv1@acme.example.com", "Zx9-Correcta-Larga!")
    assert sesion["user"]["debe_aceptar_privacidad"] is True


def test_asvs833_sin_version_aceptada_no_vale():
    """`None` es «nunca aceptó», y es lo que tienen las cuentas anteriores al
    aviso. Rellenarlas en la migración habría sido falsificar el
    consentimiento — justo lo que el control quiere impedir."""
    assert aviso.acepto_lo_vigente(None) is False


# ---------------------------------------------------------------------------
# §2 — Si el aviso cambia, se vuelve a preguntar
# ---------------------------------------------------------------------------


def test_asvs833_una_version_anterior_no_vale():
    assert aviso.acepto_lo_vigente("2020-01-01") is False
    assert aviso.acepto_lo_vigente(aviso.VERSION) is True


@pytest.mark.asyncio
async def test_asvs833_al_subir_la_version_vuelve_a_pedirse(
    client, db_session, monkeypatch
):
    """Es la mitad que el owner pidió expresamente: «y si hay algún cambio».

    Sin esto, quien aceptó una vez no vuelve a ver nada nunca, y lo que la
    plataforma aplica deja de ser lo que esa persona aceptó.
    """
    from tests.factories import create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="priv2", name="Priv2")
    await create_user(
        db_session, tenant=tenant, username="priv2u",
        email="priv2@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "priv2@acme.example.com", "Zx9-Correcta-Larga!")

    r = await client.post("/api/v1/auth/aceptar-privacidad", headers=sesion["_authz"])
    assert r.status_code == 200, r.text
    assert r.json()["debe_aceptar_privacidad"] is False

    # Cambia el aviso: la misma persona tiene que volver a verlo.
    monkeypatch.setattr(aviso, "VERSION", "2027-01-01")
    r = await client.get("/api/v1/auth/me", headers=sesion["_authz"])
    assert r.status_code == 200
    assert r.json()["debe_aceptar_privacidad"] is True, (
        "El aviso cambió y no se volvió a pedir: lo aceptado y lo aplicado ya no "
        "son lo mismo"
    )


# ---------------------------------------------------------------------------
# §3 — La versión la pone el servidor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs833_el_cliente_no_elige_que_version_acepta(client, db_session):
    """El endpoint no lee versión del cuerpo. Si la leyera, mandar una antigua
    bastaría para que la pantalla no volviera a salir nunca."""
    from tests.factories import create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="priv3", name="Priv3")
    u = await create_user(
        db_session, tenant=tenant, username="priv3u",
        email="priv3@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "priv3@acme.example.com", "Zx9-Correcta-Larga!")

    r = await client.post(
        "/api/v1/auth/aceptar-privacidad",
        json={"version": "1999-01-01"},
        headers=sesion["_authz"],
    )
    assert r.status_code == 200, r.text

    await db_session.refresh(u)
    assert u.privacy_version == aviso.VERSION, (
        f"Se guardó {u.privacy_version!r} en vez de la vigente"
    )
    assert u.privacy_accepted_at is not None


@pytest.mark.asyncio
async def test_asvs833_aceptar_queda_en_la_auditoria(client, db_session):
    """Un consentimiento es exactamente el tipo de hecho que alguien puede
    tener que demostrar después."""
    from sqlalchemy import select

    from app.models.audit import AuditLog
    from tests.factories import create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="priv4", name="Priv4")
    await create_user(
        db_session, tenant=tenant, username="priv4u",
        email="priv4@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "priv4@acme.example.com", "Zx9-Correcta-Larga!")
    await client.post("/api/v1/auth/aceptar-privacidad", headers=sesion["_authz"])

    filas = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "privacy_accepted")
        )
    ).scalars().all()
    assert filas, "El consentimiento no quedó registrado"
    assert filas[0].details.get("version") == aviso.VERSION


# ---------------------------------------------------------------------------
# §4 — El texto dice algo, y se puede leer sin cuenta
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs833_el_aviso_se_lee_sin_autenticar(client):
    """La pantalla sale antes de aceptar nada, y quien quiera saber qué se
    recoge sobre él antes de entrar tiene derecho a leerlo."""
    r = await client.get("/api/v1/auth/aviso-privacidad")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["version"] == aviso.VERSION
    assert len(cuerpo["apartados"]) >= 5


def test_asvs833_el_texto_responde_lo_que_el_control_pide():
    """«Clear language regarding collection **and use**».

    Un aviso que dice qué se guarda y no para qué cumple la mitad. Esto fija
    que estén las dos, y que ningún apartado se quede vacío al editarlo.
    """
    titulos = " ".join(a.titulo.lower() for a in aviso.APARTADOS)
    assert "qué se guarda" in titulos, "Falta qué se recoge"
    assert "para qué" in titulos, "Falta para qué se usa"
    assert "qué puedes hacer" in titulos, "Falta qué derechos tiene la persona"

    for apartado in aviso.APARTADOS:
        assert len(apartado.cuerpo) > 80, (
            f"El apartado «{apartado.titulo}» se quedó en {len(apartado.cuerpo)} "
            f"caracteres: no es lenguaje claro, es un titular."
        )


def test_asvs833_el_aviso_no_promete_lo_que_el_producto_no_hace():
    """El texto dice que puedes exportar y borrar tus datos.

    Eso es `8.3.2`, y va en el mismo bloque de trabajo. Si algún día se
    revierte, esta prueba obliga a corregir también el aviso — un aviso de
    privacidad que promete un derecho que no existe es peor que no tenerlo.
    """
    from app.api.v1.endpoints import users

    rutas = {getattr(r, "path", "") for r in users.router.routes}
    assert any("datos-personales" in ruta for ruta in rutas), (
        f"El aviso promete exportación y supresión, y no hay endpoint que lo "
        f"cumpla. Rutas: {sorted(rutas)}"
    )
