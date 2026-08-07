"""MCS SEG-01 · ASVS 8.3.2 — exportar y suprimir los datos propios.

«Verify that users have a method to remove or export their data on demand.»

Cierra además lo que `docs/dominio/05-DATOS-PERSONALES.md` §5 declaraba como «la
carencia más seria de este inventario»: no había procedimiento, así que una
solicitud se habría atendido a mano y sin garantía de completitud.

## La decisión que hay detrás (ADR-034)

Se **anonimiza**, no se borra. El borrado físico choca con `audit_log` —de solo
anexado por diseño, con su trinquete— y con el historial de los proyectos, que
es dato del inquilino y no de la persona. Anonimizar deja las filas y corta el
vínculo: si el dato ya no identifica a nadie, deja de ser dato personal.

## Lo que esta suite vigila

§1 — que la exportación traiga lo que hay, no un esqueleto. Un endpoint que
devuelve `{}` cumple el control sobre el papel y no sirve a nadie.
§2 — que la supresión **corte el vínculo de verdad**: es lo único que hace que
anonimizar valga como supresión. Si el correo o el nombre sobreviven en algún
sitio, no se ha suprimido nada.
§3 — que `audit_log` siga intacto. Es la mitad que justifica la decisión: si la
anonimización borrara el registro, no habría hecho falta anonimizar.
§4 — que sea difícil de hacer sin querer, y que cierre la sesión.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.services.datos_personales import NOMBRE_ANONIMO, anonimiza, exporta


async def _persona(db, client, sufijo: str):
    from tests.factories import create_tenant, create_user, login

    tenant = await create_tenant(db, slug=f"dp{sufijo}", name=f"Dp{sufijo}")
    u = await create_user(
        db, tenant=tenant, username=f"dp{sufijo}",
        email=f"dp{sufijo}@acme.example.com", password="Zx9-Correcta-Larga!",
        full_name="Ana Pérez Ruiz",
    )
    sesion = await login(client, f"dp{sufijo}@acme.example.com", "Zx9-Correcta-Larga!")
    return u, sesion


# ---------------------------------------------------------------------------
# §1 — La exportación trae lo que hay
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs832_la_exportacion_trae_la_cuenta_y_la_actividad(client, db_session):
    """Un endpoint que devuelve un esqueleto cumple el control sobre el papel."""
    u, sesion = await _persona(db_session, client, "1")

    r = await client.get("/api/v1/users/me/datos-personales", headers=sesion["_authz"])
    assert r.status_code == 200, r.text
    datos = r.json()

    assert datos["cuenta"]["correo"] == "dp1@acme.example.com"
    assert datos["cuenta"]["nombre"] == "Ana Pérez Ruiz"
    # El inicio de sesión que acaba de hacer ya es actividad suya.
    assert datos["actividad"], "La exportación no trae el registro de actividad"
    assert any(a["accion"] == "login_success" for a in datos["actividad"])


@pytest.mark.asyncio
async def test_asvs832_la_exportacion_se_descarga_como_archivo(client, db_session):
    _, sesion = await _persona(db_session, client, "2")
    r = await client.get("/api/v1/users/me/datos-personales", headers=sesion["_authz"])
    assert "attachment" in r.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_asvs832_la_exportacion_declara_su_limite(client, db_session):
    """El texto libre no se puede barrer, y eso va escrito en vez de fingido.

    Una minuta que dice «lo comenta Ana» sigue diciéndolo. Prometer una copia
    «completa» cuando no lo es sería peor que declarar el límite.
    """
    _, sesion = await _persona(db_session, client, "3")
    r = await client.get("/api/v1/users/me/datos-personales", headers=sesion["_authz"])
    assert "no incluye" in r.json()["aviso"].lower()


@pytest.mark.asyncio
async def test_asvs832_exportar_deja_rastro(client, db_session):
    """Es una lectura masiva de datos personales: si alguien se hace con una
    sesión, esto es lo primero que haría."""
    _, sesion = await _persona(db_session, client, "4")
    await client.get("/api/v1/users/me/datos-personales", headers=sesion["_authz"])

    filas = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "personal_data_exported")
        )
    ).scalars().all()
    assert filas


# ---------------------------------------------------------------------------
# §2 — La supresión corta el vínculo de verdad
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs832_al_suprimir_no_queda_nada_que_identifique(client, db_session):
    """Es lo único que hace que anonimizar valga como supresión.

    Si el correo o el nombre sobreviven en algún sitio, no se ha suprimido nada
    — se ha cambiado una etiqueta.
    """
    u, sesion = await _persona(db_session, client, "5")

    r = await client.post(
        "/api/v1/users/me/datos-personales/suprimir",
        json={"confirmacion": "dp5@acme.example.com"},
        headers=sesion["_authz"],
    )
    assert r.status_code == 200, r.text

    await db_session.refresh(u)
    assert "dp5@acme.example.com" not in (u.email or "")
    assert u.full_name == NOMBRE_ANONIMO
    assert "Ana" not in (u.full_name or "")
    assert not u.username.startswith("dp5")
    assert u.is_active is False, "Anonimizada y activa sería una cuenta sin dueño"
    assert u.preferences == {}


@pytest.mark.asyncio
async def test_asvs832_el_seudonimo_es_estable(db_session):
    """Dos filas del mismo usuario anonimizado tienen que seguir siendo del
    mismo, o el historial de un proyecto se vuelve incoherente."""
    from app.services.datos_personales import _seudonimo

    assert _seudonimo("abc") == _seudonimo("abc")
    assert _seudonimo("abc") != _seudonimo("def")


@pytest.mark.asyncio
async def test_asvs832_el_seudonimo_no_es_reversible(db_session):
    """Si se pudiera deshacer no sería anonimización, sería ofuscación — y el
    dato seguiría siendo personal."""
    from app.services.datos_personales import _seudonimo

    identificador = "11111111-2222-3333-4444-555555555555"
    assert identificador not in _seudonimo(identificador)
    assert len(_seudonimo(identificador)) <= 16


# ---------------------------------------------------------------------------
# §3 — `audit_log` sobrevive intacto: es lo que justifica la decisión
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs832_la_supresion_no_borra_la_auditoria(client, db_session):
    """Si la anonimización borrara el registro, no habría hecho falta anonimizar.

    `audit_log` es de solo anexado (AM-08) y su trinquete lo impide; lo que se
    corta es el vínculo, en `users`.
    """
    u, sesion = await _persona(db_session, client, "6")
    antes = len(
        (
            await db_session.execute(select(AuditLog).where(AuditLog.user_id == str(u.id)))
        ).scalars().all()
    )
    assert antes > 0

    await client.post(
        "/api/v1/users/me/datos-personales/suprimir",
        json={"confirmacion": "dp6@acme.example.com"},
        headers=sesion["_authz"],
    )

    despues = (
        await db_session.execute(select(AuditLog).where(AuditLog.user_id == str(u.id)))
    ).scalars().all()
    assert len(despues) >= antes, "Se perdieron filas de auditoría"
    assert any(f.action == "personal_data_erased" for f in despues)


# ---------------------------------------------------------------------------
# §4 — Difícil de hacer sin querer, y cierra la sesión
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs832_sin_la_confirmacion_exacta_no_se_suprime(client, db_session):
    """Irreversible con un solo clic es un accidente esperando a pasar. Mismo
    patrón que el borrado permanente de entidades."""
    u, sesion = await _persona(db_session, client, "7")

    r = await client.post(
        "/api/v1/users/me/datos-personales/suprimir",
        json={"confirmacion": "sí, bórralo"},
        headers=sesion["_authz"],
    )
    assert r.status_code == 400, r.text

    await db_session.refresh(u)
    assert u.email == "dp7@acme.example.com", "Se anonimizó sin confirmar"
    assert u.is_active is True


@pytest.mark.asyncio
async def test_asvs832_al_suprimir_se_cierra_la_sesion(client, db_session):
    """Una cuenta anonimizada con sesión viva es una cuenta sin dueño desde la
    que todavía se puede operar."""
    _, sesion = await _persona(db_session, client, "8")

    r = await client.post(
        "/api/v1/users/me/datos-personales/suprimir",
        json={"confirmacion": "dp8@acme.example.com"},
        headers=sesion["_authz"],
    )
    assert r.status_code == 200

    borradas = [
        c for c in r.headers.get_list("set-cookie")
        if "max-age=0" in c.lower() or "01 jan 1970" in c.lower()
    ]
    assert borradas, f"No se borraron las cookies: {r.headers.get_list('set-cookie')}"

    # Y el token deja de servir: la cuenta está inactiva.
    r = await client.get("/api/v1/auth/me", headers=sesion["_authz"])
    assert r.status_code == 401, "La sesión sigue viva tras suprimir la cuenta"


@pytest.mark.asyncio
async def test_asvs832_hay_que_estar_autenticado(client):
    """«Their data»: solo se exportan y suprimen los datos de quien pide."""
    r = await client.get("/api/v1/users/me/datos-personales")
    assert r.status_code == 401
    r = await client.post(
        "/api/v1/users/me/datos-personales/suprimir", json={"confirmacion": "x"}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_asvs832_el_servicio_no_deja_notificaciones_con_el_nombre(db_session):
    """El cuerpo de una notificación puede llevar el nombre («Hola Ana…»)."""
    from tests.factories import create_tenant, create_user
    from app.services.notifications import enqueue_notification

    tenant = await create_tenant(db_session, slug="dp9", name="Dp9")
    u = await create_user(
        db_session, tenant=tenant, username="dp9", email="dp9@acme.example.com",
        password="Zx9-Correcta-Larga!", full_name="Ana Pérez Ruiz",
    )
    await enqueue_notification(
        db_session, tenant_id=tenant.id, user_id=u.id, type="pm_assigned",
        title="Hola Ana", body="Ana Pérez Ruiz, te asignaron un proyecto",
        send_email=False,
    )
    await db_session.commit()

    await anonimiza(db_session, user=u)
    await db_session.commit()

    from app.models.notification import Notification

    avisos = (
        await db_session.execute(
            select(Notification).where(Notification.user_id == str(u.id))
        )
    ).scalars().all()
    for aviso in avisos:
        assert "Ana" not in (aviso.body or ""), aviso.body
        assert "Ana" not in (aviso.title or ""), aviso.title


@pytest.mark.asyncio
async def test_asvs832_exporta_no_lanza_con_una_cuenta_vacia(db_session):
    """Una cuenta recién creada, sin actividad, tiene que poder exportarse."""
    from tests.factories import create_tenant, create_user

    tenant = await create_tenant(db_session, slug="dp10", name="Dp10")
    u = await create_user(
        db_session, tenant=tenant, username="dp10", email="dp10@acme.example.com",
        password="Zx9-Correcta-Larga!",
    )
    datos = await exporta(db_session, user=u)
    assert datos["cuenta"]["correo"] == "dp10@acme.example.com"
    assert datos["actividad"] == []
