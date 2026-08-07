"""MCS SEG-01 · ASVS 2.2.3 y 2.5.5 — aviso al cambiar los datos de acceso.

- 2.2.3: «secure notifications are sent to users after updates to
  authentication details, such as credential resets, email or address changes».
- 2.5.5: «if an authentication factor is changed or replaced, that the user is
  notified of this event».

Son el mismo aviso visto desde dos sitios, así que se cierran juntos.

## Qué enseñó medir

El aviso **existía**, en uno de los seis sitios que tocan una credencial: el
cambio de contraseña hecho por el propio usuario. Faltaba en el
restablecimiento, en los dos cambios de correo y en los dos cambios de
contraseña hechos por un administrador — es decir, faltaba justo donde el
cambio **no** lo hace el dueño de la cuenta, que es el único caso en que el
aviso sirve para algo. Cuando lo haces tú ya lo sabes.

Y donde sí estaba llevaba un `if tenant_id is not None`, así que el
superadministrador —la cuenta con más permisos de la plataforma— era la única
que cambiaba su contraseña sin enterarse nadie.

## Los dos casos que esta suite defiende, y que son fáciles de perder

**§2 — la dirección que se abandona.** Al cambiar el correo hay que avisar
también al anterior. Sin eso, quien se apodera de una cuenta y le cambia el
correo consigue que el dueño no se entere **nunca**: todos los avisos
posteriores van al atacante. Es el aviso más importante del control y el que no
tiene a quién colgarse, porque ya no hay usuario con esa dirección.

**§3 — que no se pueda apagar.** Un aviso de seguridad que se desactiva desde
los ajustes de notificaciones no es un control.
"""
from __future__ import annotations

import pytest

from app.services import notifications as svc


@pytest.fixture
def avisos(monkeypatch):
    """Recoge los correos directos (sin notificación in-app detrás)."""
    enviados: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        svc, "_envia_aviso_directo",
        lambda destino, titulo, cuerpo: enviados.append((destino, titulo, cuerpo)),
    )
    return enviados


async def _cuenta_notificaciones(db, user_id) -> list:
    from sqlalchemy import select

    from app.models.notification import Notification

    return list(
        (
            await db.execute(
                select(Notification).where(Notification.user_id == str(user_id))
            )
        ).scalars().all()
    )


# ---------------------------------------------------------------------------
# §1 — Los seis sitios avisan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs223_el_cambio_propio_avisa(client, db_session, avisos):
    from tests.factories import create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="av1", name="Av1")
    u = await create_user(
        db_session, tenant=tenant, username="av1u",
        email="av1@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "av1@acme.example.com", "Zx9-Correcta-Larga!")

    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Zx9-Correcta-Larga!", "new_password": "Qw3-Otra-Distinta!"},
        headers=sesion["_authz"],
    )
    assert r.status_code == 204, r.text

    notis = await _cuenta_notificaciones(db_session, u.id)
    assert any(n.type in (svc.CREDENTIAL_CHANGED, svc.PASSWORD_CHANGED) for n in notis), (
        f"Sin aviso tras cambiar la contraseña: {[n.type for n in notis]}"
    )


@pytest.mark.asyncio
async def test_asvs223_el_restablecimiento_avisa(client, db_session, avisos):
    from app.services.password_reset import issue_reset_token
    from tests.factories import create_tenant, create_user

    tenant = await create_tenant(db_session, slug="av2", name="Av2")
    u = await create_user(
        db_session, tenant=tenant, username="av2u",
        email="av2@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    token = await issue_reset_token(db_session, user_id=u.id, ip_address="1.2.3.4")
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "Qw3-Otra-Distinta!"},
    )
    assert r.status_code in (200, 204), r.text

    notis = await _cuenta_notificaciones(db_session, u.id)
    assert any(n.type in (svc.CREDENTIAL_CHANGED, svc.PASSWORD_CHANGED) for n in notis)


@pytest.mark.asyncio
async def test_asvs223_el_restablecimiento_por_admin_avisa_al_dueno(
    client, db_session, avisos
):
    """El caso donde más falta hace: el cambio no lo hizo el dueño de la cuenta.

    Es el único que puede detectar que un administrador —o quien haya entrado
    con sus credenciales— le está tocando la cuenta.
    """
    from tests.factories import create_admin_role, create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="av3", name="Av3")
    rol = await create_admin_role(db_session, tenant)
    await create_user(
        db_session, tenant=tenant, username="av3admin",
        email="av3admin@acme.example.com", password="Zx9-Correcta-Larga!", roles=[rol],
    )
    victima = await create_user(
        db_session, tenant=tenant, username="av3victima",
        email="av3victima@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "av3admin@acme.example.com", "Zx9-Correcta-Larga!")

    r = await client.post(
        f"/api/v1/admin/users/{victima.id}/reset-password", headers=sesion["_authz"]
    )
    assert r.status_code == 200, r.text

    notis = await _cuenta_notificaciones(db_session, victima.id)
    assert any(n.type in (svc.CREDENTIAL_CHANGED, svc.PASSWORD_CHANGED) for n in notis), (
        "El dueño de la cuenta no se enteró de que le cambiaron la contraseña"
    )


# ---------------------------------------------------------------------------
# §2 — La dirección que se abandona también recibe el aviso
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs223_al_cambiar_el_correo_avisa_al_anterior(
    client, db_session, avisos
):
    """El aviso más importante del control, y el que no tiene a quién colgarse.

    Quien se apodera de una cuenta le cambia el correo. A partir de ahí, todos
    los avisos van al atacante y el dueño no se entera nunca. El único momento
    en que se le puede decir algo es **ese**, y a la dirección vieja.
    """
    from tests.factories import create_admin_role, create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="av4", name="Av4")
    rol = await create_admin_role(db_session, tenant)
    await create_user(
        db_session, tenant=tenant, username="av4admin",
        email="av4admin@acme.example.com", password="Zx9-Correcta-Larga!", roles=[rol],
    )
    victima = await create_user(
        db_session, tenant=tenant, username="av4victima",
        email="viejo@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "av4admin@acme.example.com", "Zx9-Correcta-Larga!")

    r = await client.patch(
        f"/api/v1/admin/users/{victima.id}",
        json={"email": "delatacante@example.com"},
        headers=sesion["_authz"],
    )
    assert r.status_code == 200, r.text

    destinos = [destino for destino, _, _ in avisos]
    assert "viejo@acme.example.com" in destinos, (
        f"No se avisó a la dirección abandonada. Avisos enviados: {destinos}"
    )


@pytest.mark.asyncio
async def test_asvs223_sin_cambio_de_correo_no_se_avisa_a_nadie(
    client, db_session, avisos
):
    """Un aviso que llega cuando no pasó nada enseña a ignorar los avisos."""
    from tests.factories import create_admin_role, create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="av5", name="Av5")
    rol = await create_admin_role(db_session, tenant)
    await create_user(
        db_session, tenant=tenant, username="av5admin",
        email="av5admin@acme.example.com", password="Zx9-Correcta-Larga!", roles=[rol],
    )
    otro = await create_user(
        db_session, tenant=tenant, username="av5otro",
        email="av5otro@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "av5admin@acme.example.com", "Zx9-Correcta-Larga!")

    r = await client.patch(
        f"/api/v1/admin/users/{otro.id}",
        json={"full_name": "Nombre Nuevo"},
        headers=sesion["_authz"],
    )
    assert r.status_code == 200, r.text
    assert not avisos, f"Se avisó de un cambio que no toca credenciales: {avisos}"


# ---------------------------------------------------------------------------
# §3 — No se puede apagar, y llega a quien no tiene inquilino
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs223_el_aviso_no_respeta_las_preferencias(db_session, avisos):
    """Un aviso de seguridad desactivable desde los ajustes no es un control.

    Se apaga el interruptor global de correo del usuario y el aviso tiene que
    salir igual — `send_email=True` fuerza el canal.
    """
    from tests.factories import create_tenant, create_user

    tenant = await create_tenant(db_session, slug="av6", name="Av6")
    u = await create_user(
        db_session, tenant=tenant, username="av6u",
        email="av6@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    u.preferences = {"notifications": {"email_enabled": False}}
    await db_session.commit()

    # El interruptor está apagado de verdad: sin forzar, este usuario no
    # recibiría correo de ningún tipo.
    assert not await svc._user_wants_email(db_session, u.id, svc.PASSWORD_CHANGED)

    encolados: list[str] = []
    import app.workers.tasks.notifications as tareas

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        tareas.send_notification_email, "delay", lambda nid: encolados.append(nid)
    )
    try:
        await svc.avisa_cambio_de_credencial(db_session, usuario=u, motivo="password")
        await db_session.commit()
    finally:
        monkeypatch.undo()

    notis = await _cuenta_notificaciones(db_session, u.id)
    assert any(n.type in (svc.CREDENTIAL_CHANGED, svc.PASSWORD_CHANGED) for n in notis)
    assert encolados, (
        "La preferencia apagó el aviso de seguridad. Un control que se "
        "desactiva desde los ajustes no es un control."
    )


@pytest.mark.asyncio
async def test_asvs223_el_superadmin_sin_inquilino_recibe_correo(db_session, avisos):
    """`notifications.tenant_id` es NOT NULL, así que un superadministrador no
    puede tener notificación in-app. Antes eso significaba: ningún aviso."""
    from tests.factories import create_user

    superadmin = await create_user(
        db_session, tenant=None, username="raiz",
        email="raiz@pmoaas.example.com", password="Zx9-Correcta-Larga!",
        is_superadmin=True,
    )
    assert superadmin.tenant_id is None

    await svc.avisa_cambio_de_credencial(db_session, usuario=superadmin, motivo="password")

    destinos = [destino for destino, _, _ in avisos]
    assert "raiz@pmoaas.example.com" in destinos, (
        f"El superadministrador se quedó sin aviso: {avisos}"
    )


@pytest.mark.asyncio
async def test_asvs223_el_aviso_dice_que_hacer_si_no_fuiste_tu(db_session, avisos):
    """Un aviso que no dice qué hacer solo produce inquietud.

    LEN-02 pide las tres partes, y aquí la tercera es la que convierte el
    correo en una defensa: si no fuiste tú, cambia la contraseña YA.
    """
    from tests.factories import create_user

    superadmin = await create_user(
        db_session, tenant=None, username="raiz2",
        email="raiz2@pmoaas.example.com", password="Zx9-Correcta-Larga!",
        is_superadmin=True,
    )
    await svc.avisa_cambio_de_credencial(db_session, usuario=superadmin, motivo="password")

    _, _, cuerpo = avisos[0]
    assert "contraseña" in cuerpo
    assert "Si no" in cuerpo, "Tiene que decir qué hacer cuando no fue el dueño"


@pytest.mark.asyncio
async def test_asvs223_un_fallo_del_aviso_no_tumba_el_cambio(db_session, monkeypatch):
    """El cambio ya ocurrió. Si el aviso revienta, el usuario se quedaría sin
    saber siquiera si su contraseña cambió o no."""
    from tests.factories import create_tenant, create_user

    tenant = await create_tenant(db_session, slug="av7", name="Av7")
    u = await create_user(
        db_session, tenant=tenant, username="av7u",
        email="av7@acme.example.com", password="Zx9-Correcta-Larga!",
    )

    async def revienta(*a, **kw):
        raise RuntimeError("el canal se cayó")

    monkeypatch.setattr(svc, "enqueue_notification", revienta)
    # No debe propagar.
    await svc.avisa_cambio_de_credencial(db_session, usuario=u, motivo="password")
