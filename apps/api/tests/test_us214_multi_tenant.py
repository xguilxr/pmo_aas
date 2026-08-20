"""US-214 / AM-16 — Membresía multi-inquilino, autorizada desde la base.

Los mockups piden un selector de inquilino en el encabezado. Para eso la relación
usuario–inquilino tiene que ser de muchos a muchos: un consultor que trabaja para
dos clientes, una PMO que gestiona varias cuentas.

El defecto que esto cierra, y que el modelo de amenazas registra como **AM-16**:
hasta aquí el cambio de inquilino se autorizaba contra el claim `tenant_ids` del
JWT. Con un inquilino por usuario la lista era de un elemento y no tenía
consecuencia; con dos, **revocar una membresía no surtiría efecto hasta que el
token caduque** — una hora.

Lo que estos tests cuidan:

1. **Revocar surte efecto en la siguiente petición**, con el mismo token. Es el
   test que justifica la consulta por petición.
2. **Un claim no autoriza nada**: el cambio se resuelve contra la tabla.
3. **La membresía de origen se crea con el usuario**, desde los cinco caminos que
   crean usuarios.
4. **Conceder membresía es de superadministrador**, no de administrador de
   inquilino: el inquilino es la frontera de aislamiento.
5. **No se puede revocar el inquilino de origen**: dejaría la cuenta sin ningún
   sitio donde entrar, que es una baja disfrazada de cambio de permiso.
"""
import pytest
from sqlalchemy import select

from app.models.user_tenant_membership import UserTenantMembership
from app.services.membresia import conceder, inquilinos_de, revocar, tiene_membresia
from tests.factories import create_admin_role, create_tenant, create_user, login

# ---------------------------------------------------------------------------
# TC-214.1 — La membresía de origen nace con el usuario
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crear_un_usuario_le_da_la_membresia_de_su_inquilino(client, db_session):
    """Los usuarios se crean desde cinco caminos. La regla vive en el modelo, no
    en cada endpoint: en uno de cinco no es una regla, es una costumbre."""
    t = await create_tenant(db_session)
    u = await create_user(db_session, tenant=t, username="ana", email="ana@a.example.com")
    await db_session.flush()
    assert await tiene_membresia(db_session, user_id=u.id, tenant_id=t.id)


@pytest.mark.asyncio
async def test_un_superadministrador_no_gana_una_membresia_inventada(
    client, db_session
):
    """Su acceso viene de «entrar como administrador» (FC-4), no de una
    membresía. Inventarle una lo ataría a un inquilino que no es suyo."""
    u = await create_user(
        db_session,
        tenant=None,
        username="root",
        email="root@plataforma.example.com",
        is_superadmin=True,
    )
    await db_session.flush()
    filas = (
        await db_session.execute(
            select(UserTenantMembership).where(
                UserTenantMembership.user_id == str(u.id)
            )
        )
    ).scalars().all()
    assert filas == []


# ---------------------------------------------------------------------------
# TC-214.2 — Conceder, listar y revocar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conceder_y_listar_dos_inquilinos(client, db_session):
    t1 = await create_tenant(db_session)
    t2 = await create_tenant(db_session, slug="beta", name="Beta")
    u = await create_user(db_session, tenant=t1, username="ana", email="ana@a.example.com")
    await db_session.flush()
    await conceder(db_session, user_id=u.id, tenant_id=t2.id, concedida_por=None)
    nombres = [n for _, n, _ in await inquilinos_de(db_session, user_id=u.id)]
    # Ordenados por nombre: un desplegable sin orden se lee mal con tres.
    assert nombres == ["Acme", "Beta"]


@pytest.mark.asyncio
async def test_conceder_dos_veces_no_crea_dos_filas(client, db_session):
    """La unicidad es `(user_id, tenant_id)` sin importar el estado: dos filas
    para la misma pareja obligarían a decidir cuál manda al leer."""
    t1 = await create_tenant(db_session)
    t2 = await create_tenant(db_session, slug="beta", name="Beta")
    u = await create_user(db_session, tenant=t1, username="ana", email="ana@a.example.com")
    await db_session.flush()
    a = await conceder(db_session, user_id=u.id, tenant_id=t2.id, concedida_por=None)
    b = await conceder(db_session, user_id=u.id, tenant_id=t2.id, concedida_por=None)
    assert a.id == b.id


@pytest.mark.asyncio
async def test_revocar_y_reactivar_reusa_la_fila(client, db_session):
    t1 = await create_tenant(db_session)
    t2 = await create_tenant(db_session, slug="beta", name="Beta")
    u = await create_user(db_session, tenant=t1, username="ana", email="ana@a.example.com")
    await db_session.flush()
    await conceder(db_session, user_id=u.id, tenant_id=t2.id, concedida_por=None)
    assert await revocar(db_session, user_id=u.id, tenant_id=t2.id, revocada_por=None)
    assert not await tiene_membresia(db_session, user_id=u.id, tenant_id=t2.id)
    # Revocar dos veces no es un error del sistema, es que no había nada que
    # revocar. El llamador decide si eso es un 404.
    assert not await revocar(
        db_session, user_id=u.id, tenant_id=t2.id, revocada_por=None
    )
    await conceder(db_session, user_id=u.id, tenant_id=t2.id, concedida_por=None)
    assert await tiene_membresia(db_session, user_id=u.id, tenant_id=t2.id)


@pytest.mark.asyncio
async def test_una_membresia_revocada_no_aparece_en_el_selector(client, db_session):
    t1 = await create_tenant(db_session)
    t2 = await create_tenant(db_session, slug="beta", name="Beta")
    u = await create_user(db_session, tenant=t1, username="ana", email="ana@a.example.com")
    await db_session.flush()
    await conceder(db_session, user_id=u.id, tenant_id=t2.id, concedida_por=None)
    await revocar(db_session, user_id=u.id, tenant_id=t2.id, revocada_por=None)
    assert [n for _, n, _ in await inquilinos_de(db_session, user_id=u.id)] == ["Acme"]


# ---------------------------------------------------------------------------
# TC-214.3 — Contra la API: el cambio y la revocación
# ---------------------------------------------------------------------------


async def _con_dos_inquilinos(client, db_session):
    t1 = await create_tenant(db_session)
    t2 = await create_tenant(db_session, slug="beta", name="Beta")
    rol = await create_admin_role(db_session, t1)
    u = await create_user(
        db_session,
        tenant=t1,
        username="ana",
        email="ana@acme.example.com",
        password="Str0ng-Ana-1!",
        roles=[rol],
    )
    await db_session.flush()
    await conceder(db_session, user_id=u.id, tenant_id=t2.id, concedida_por=None)
    await db_session.commit()
    auth = await login(client, "ana", "Str0ng-Ana-1!")
    return {"h": auth["_authz"], "u": u, "t1": t1, "t2": t2}


@pytest.mark.asyncio
async def test_el_login_trae_los_dos_inquilinos_y_aterriza_en_el_de_origen(
    client, db_session
):
    e = await _con_dos_inquilinos(client, db_session)
    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "ana", "password": "Str0ng-Ana-1!"},
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["tenants"]) == 2
    # El de origen es el activo: es donde se creó la cuenta y donde espera
    # aterrizar quien inicia sesión.
    assert d["active_tenant_id"] == str(e["t1"].id)


@pytest.mark.asyncio
async def test_cambiar_de_inquilino(client, db_session):
    e = await _con_dos_inquilinos(client, db_session)
    r = await client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": str(e["t2"].id)},
        headers=e["h"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["active_tenant_id"] == str(e["t2"].id)


@pytest.mark.asyncio
async def test_no_se_puede_cambiar_a_un_inquilino_sin_membresia(client, db_session):
    e = await _con_dos_inquilinos(client, db_session)
    ajeno = await create_tenant(db_session, slug="gamma", name="Gamma")
    await db_session.commit()
    r = await client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": str(ajeno.id)},
        headers=e["h"],
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_revocar_surte_efecto_en_la_siguiente_peticion(client, db_session):
    """**El test que justifica la consulta por petición.**

    Sin ella, el token seguiría valiendo hasta caducar —una hora— y el consultor
    al que se le quitó el acceso seguiría viendo la cartera del cliente que ya no
    es suyo. Aquí se usa el **mismo** token después de revocar.
    """
    e = await _con_dos_inquilinos(client, db_session)
    cambio = await client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": str(e["t2"].id)},
        headers=e["h"],
    )
    assert cambio.status_code == 200
    activo = {"Authorization": f"Bearer {cambio.json()['access_token']}"}
    # Con el inquilino activo puesto, la sesión funciona.
    assert (await client.get("/api/v1/auth/me", headers=activo)).status_code == 200

    await revocar(
        db_session, user_id=e["u"].id, tenant_id=e["t2"].id, revocada_por=None
    )
    await db_session.commit()

    # Mismo token, sin esperar la caducidad.
    r = await client.get("/api/v1/auth/me", headers=activo)
    assert r.status_code == 403, r.text
    assert "TENANT_MEMBERSHIP_REVOKED" in r.text


@pytest.mark.asyncio
async def test_el_claim_del_token_no_autoriza_por_si_mismo(client, db_session):
    """El token de antes de revocar sigue llevando el inquilino en `tenant_ids`.
    Cambiar a él tiene que fallar: la autorización va contra la tabla."""
    e = await _con_dos_inquilinos(client, db_session)
    await revocar(
        db_session, user_id=e["u"].id, tenant_id=e["t2"].id, revocada_por=None
    )
    await db_session.commit()
    r = await client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": str(e["t2"].id)},
        headers=e["h"],
    )
    assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# TC-214.4 — Conceder es de superadministrador (FC-4)
# ---------------------------------------------------------------------------


async def _superadmin(client, db_session):
    t = await create_tenant(db_session, slug="plat", name="Plataforma")
    await create_user(
        db_session,
        tenant=None,
        username="root",
        email="root@plat.example.com",
        password="Str0ng-Root-1!",
        is_superadmin=True,
    )
    await db_session.commit()
    auth = await login(client, "root", "Str0ng-Root-1!")
    return {"h": auth["_authz"], "t": t}


@pytest.mark.asyncio
async def test_un_administrador_de_inquilino_no_puede_conceder_membresias(
    client, db_session
):
    """El inquilino es la frontera de aislamiento. Un administrador que pudiera
    añadir a alguien a otro inquilino podría concederse acceso a otro cliente."""
    e = await _con_dos_inquilinos(client, db_session)
    r = await client.post(
        "/api/v1/superadmin/memberships",
        json={"user_id": str(e["u"].id), "tenant_id": str(e["t2"].id)},
        headers=e["h"],
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_el_superadministrador_concede_y_revoca(client, db_session):
    s = await _superadmin(client, db_session)
    otro = await create_tenant(db_session, slug="cli", name="Cliente")
    u = await create_user(
        db_session, tenant=otro, username="pm", email="pm@cli.example.com"
    )
    destino = await create_tenant(db_session, slug="cli2", name="Cliente 2")
    await db_session.commit()

    r = await client.post(
        "/api/v1/superadmin/memberships",
        json={"user_id": str(u.id), "tenant_id": str(destino.id)},
        headers=s["h"],
    )
    assert r.status_code == 201, r.text

    lista = await client.get(
        f"/api/v1/superadmin/users/{u.id}/tenants", headers=s["h"]
    )
    assert {t["name"] for t in lista.json()["tenants"]} == {"Cliente", "Cliente 2"}

    quita = await client.delete(
        f"/api/v1/superadmin/memberships?user_id={u.id}&tenant_id={destino.id}",
        headers=s["h"],
    )
    assert quita.status_code == 204, quita.text


@pytest.mark.asyncio
async def test_no_se_puede_revocar_el_inquilino_de_origen(client, db_session):
    """Dejaría la cuenta sin ningún sitio donde entrar: una baja disfrazada de
    cambio de permiso. Para dar de baja está `is_active`, que dice lo que hace."""
    s = await _superadmin(client, db_session)
    origen = await create_tenant(db_session, slug="cli", name="Cliente")
    u = await create_user(
        db_session, tenant=origen, username="pm", email="pm@cli.example.com"
    )
    await db_session.commit()
    r = await client.delete(
        f"/api/v1/superadmin/memberships?user_id={u.id}&tenant_id={origen.id}",
        headers=s["h"],
    )
    assert r.status_code == 422, r.text
    assert "origen" in r.text


@pytest.mark.asyncio
async def test_a_un_superadministrador_no_se_le_conceden_membresias(
    client, db_session
):
    """Le daría el mismo acceso que «entrar como administrador» sin el rastro de
    auditoría que esa operación deja."""
    s = await _superadmin(client, db_session)
    otro = await create_user(
        db_session,
        tenant=None,
        username="root2",
        email="root2@plat.example.com",
        is_superadmin=True,
    )
    destino = await create_tenant(db_session, slug="cli", name="Cliente")
    await db_session.commit()
    r = await client.post(
        "/api/v1/superadmin/memberships",
        json={"user_id": str(otro.id), "tenant_id": str(destino.id)},
        headers=s["h"],
    )
    assert r.status_code == 422, r.text
