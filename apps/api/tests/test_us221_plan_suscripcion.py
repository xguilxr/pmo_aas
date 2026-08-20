"""US-221 — Plan de suscripción: límites y consumo, solo lectura.

Del artboard «Admin — Plan (suscripción)»: «Plan actual: Free / Pro /
Enterprise», «Límites y consumo (organizaciones 1/1 · proyectos 3/3 · usuarios ·
IA)», y la línea que manda sobre todo lo demás: **«Solo lectura — sin paywall ni
billing en esta fase»**.

Lo que estos tests cuidan:

1. **Nada bloquea.** Un límite excedido se muestra y el inquilino sigue
   trabajando. Es el criterio del artboard y el test que lo fija.
2. **Un límite ausente no es un límite de cero.** Un cero diría «no puedes crear
   ninguna», que es lo contrario de «no hay tope» (MCS DAT-12).
3. **Los números no se inventan.** Los tres nombres de tier salen del artboard;
   los topes de cada uno no están en ningún documento, así que se capturan por
   inquilino y sin ellos se dice «sin límite declarado».
4. **El consumo se cuenta, no se guarda.** Un contador almacenado se desincroniza
   el día que alguien borra un proyecto por un camino que se olvidó de
   decrementarlo.
5. **Ver es del inquilino, escribir del superadministrador.** Un inquilino que
   pudiera subirse su propio tope tendría un plan decorativo.
"""
from datetime import date

import pytest

from app.dominio.plan import (
    CLAVES,
    RECURSOS,
    TIER_POR_DEFECTO,
    TIERS,
    evaluar,
    evaluar_uno,
    hay_algo_fuera,
    normalizar_limites,
    normalizar_tier,
)
from app.services.plan_suscripcion import _inicio_del_mes
from tests.factories import create_admin_role, create_tenant, create_user, login

# ---------------------------------------------------------------------------
# TC-221.1 — La regla, sin base de datos (MCS DEV-02)
# ---------------------------------------------------------------------------


def test_los_tres_tiers_del_artboard():
    assert TIERS == ("free", "pro", "enterprise")
    # El default es el más bajo: equivocarse hacia abajo se ve —el inquilino
    # pregunta— y hacia arriba no, porque nadie reporta que le sobran permisos.
    assert TIER_POR_DEFECTO == "free"


def test_un_tier_desconocido_cae_al_default_y_no_se_propaga():
    """`settings` lo edita una persona, y una errata no debe dejar la pantalla
    del plan sin nada que decir."""
    assert normalizar_tier("premium") == "free"
    assert normalizar_tier(None) == "free"
    assert normalizar_tier("pro") == "pro"


def test_sin_limite_declarado_no_es_limite_de_cero():
    u = evaluar_uno("projects", "Proyectos", consumo=7, limite=None)
    assert u.estado == "sin_limite"
    assert u.limite is None
    # Sin denominador no hay porcentaje: no se calcula contra un tope inventado.
    assert u.porcentaje is None


def test_los_tres_estados_frente_a_un_tope():
    assert evaluar_uno("p", "P", 2, 3).estado == "dentro"
    assert evaluar_uno("p", "P", 3, 3).estado == "al_limite"
    assert evaluar_uno("p", "P", 4, 3).estado == "excedido"
    assert evaluar_uno("p", "P", 3, 3).porcentaje == 100


def test_un_tope_de_cero_es_un_tope_valido_y_no_divide_por_cero():
    """«Este plan no incluye esto» es una configuración legítima."""
    assert evaluar_uno("p", "P", 0, 0).estado == "al_limite"
    assert evaluar_uno("p", "P", 1, 0).estado == "excedido"


def test_un_limite_negativo_o_no_numerico_se_descarta():
    """Queda como «sin límite declarado», que es la verdad —no hay un tope
    legible—, en vez de caer a cero, que diría «ninguno permitido»."""
    limpios = normalizar_limites(
        {"projects": -1, "users": "muchos", "organizations": True, "ai_jobs_month": 50}
    )
    assert limpios == {"ai_jobs_month": 50}
    assert normalizar_limites("no es un diccionario") == {}


def test_una_clave_desconocida_se_ignora():
    assert normalizar_limites({"inventada": 3}) == {}


def test_evaluar_recorre_los_recursos_declarados_y_no_el_consumo():
    """Así un recurso nuevo aparece en cuanto se declara, y un límite guardado con
    una clave retirada se ignora en vez de pintar una fila sin nombre."""
    usos = evaluar({"projects": 2, "inventado": 99}, {"projects": 5})
    assert [u.clave for u in usos] == list(CLAVES)
    assert all(len(r.consecuencia) > 20 for r in RECURSOS)


def test_hay_algo_fuera_solo_mira_lo_excedido():
    dentro = evaluar({"projects": 1}, {"projects": 5})
    assert not hay_algo_fuera(dentro)
    fuera = evaluar({"projects": 9}, {"projects": 5})
    assert hay_algo_fuera(fuera)


def test_el_mes_de_ia_es_calendario_y_no_una_ventana_movil():
    """Una ventana móvil daría un número que baja sin que nadie haya hecho nada."""
    inicio = _inicio_del_mes(date(2026, 8, 20))
    assert (inicio.year, inicio.month, inicio.day) == (2026, 8, 1)


# ---------------------------------------------------------------------------
# TC-221.2 — Contra la API
# ---------------------------------------------------------------------------


async def _inquilino(client, db_session):
    t = await create_tenant(db_session)
    rol = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[rol],
    )
    await db_session.commit()
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    return {"h": auth["_authz"], "t": t}


async def _superadmin(client, db_session):
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
    return auth["_authz"]


@pytest.mark.asyncio
async def test_un_inquilino_sin_plan_declarado_lo_dice(client, db_session):
    """No inventa números: dice «sin límite declarado» en los cuatro."""
    e = await _inquilino(client, db_session)
    r = await client.get("/api/v1/admin/plan", headers=e["h"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tier"] == "free"
    assert d["tier_label"] == "Free"
    assert d["undeclared_limits"] == 4
    assert all(u["limit"] is None for u in d["usage"])
    assert d["over_limit"] is False
    # El contrato dice que no bloquea, sin tener que leer la documentación.
    assert d["enforced"] is False


@pytest.mark.asyncio
async def test_el_consumo_se_cuenta_de_lo_que_hay(client, db_session):
    e = await _inquilino(client, db_session)
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgA"}, headers=e["h"]
        )
    ).json()["id"]
    me = (await client.get("/api/v1/auth/me", headers=e["h"])).json()["id"]
    for n in ("A", "B"):
        r = await client.post(
            "/api/v1/projects",
            json={
                "name": f"Proyecto {n}",
                "description": "US-221",
                "type": "transformacion",
                "priority": 3,
                "organization_id": org,
                "pm_id": me,
            },
            headers=e["h"],
        )
        assert r.status_code == 201, r.text

    d = (await client.get("/api/v1/admin/plan", headers=e["h"])).json()
    por_clave = {u["key"]: u for u in d["usage"]}
    assert por_clave["organizations"]["used"] == 1
    assert por_clave["projects"]["used"] == 2
    assert por_clave["users"]["used"] >= 1


@pytest.mark.asyncio
async def test_borrar_un_proyecto_baja_el_consumo(client, db_session):
    """El consumo se **cuenta**, no se guarda: un contador almacenado se
    desincroniza el día que alguien borra por un camino que lo olvidó."""
    e = await _inquilino(client, db_session)
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgA"}, headers=e["h"]
        )
    ).json()["id"]
    me = (await client.get("/api/v1/auth/me", headers=e["h"])).json()["id"]
    pid = (
        await client.post(
            "/api/v1/projects",
            json={
                "name": "Se va",
                "description": "US-221",
                "type": "operacion",
                "priority": 1,
                "organization_id": org,
                "pm_id": me,
            },
            headers=e["h"],
        )
    ).json()["id"]
    antes = (await client.get("/api/v1/admin/plan", headers=e["h"])).json()
    assert next(u for u in antes["usage"] if u["key"] == "projects")["used"] == 1

    assert (
        await client.delete(f"/api/v1/projects/{pid}", headers=e["h"])
    ).status_code in (200, 204)
    despues = (await client.get("/api/v1/admin/plan", headers=e["h"])).json()
    assert next(u for u in despues["usage"] if u["key"] == "projects")["used"] == 0


@pytest.mark.asyncio
async def test_el_superadministrador_fija_el_tier_y_los_topes(client, db_session):
    e = await _inquilino(client, db_session)
    h = await _superadmin(client, db_session)
    r = await client.put(
        f"/api/v1/superadmin/tenants/{e['t'].id}/plan",
        json={"tier": "pro", "limits": {"organizations": 3, "projects": 25}},
        headers=h,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tier"] == "pro"
    por_clave = {u["key"]: u for u in d["usage"]}
    assert por_clave["organizations"]["limit"] == 3
    assert por_clave["projects"]["limit"] == 25
    # Los dos que no se fijaron siguen sin tope, no en cero.
    assert por_clave["users"]["limit"] is None
    assert d["undeclared_limits"] == 2


@pytest.mark.asyncio
async def test_un_tope_se_puede_quitar(client, db_session):
    """Sin poder volver a «sin límite declarado», un plan mal capturado obligaría
    a editar el JSON a mano."""
    e = await _inquilino(client, db_session)
    h = await _superadmin(client, db_session)
    await client.put(
        f"/api/v1/superadmin/tenants/{e['t'].id}/plan",
        json={"limits": {"projects": 5}},
        headers=h,
    )
    r = await client.put(
        f"/api/v1/superadmin/tenants/{e['t'].id}/plan",
        json={"limits": {"projects": None}},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert next(
        u for u in r.json()["usage"] if u["key"] == "projects"
    )["limit"] is None


@pytest.mark.asyncio
async def test_pasarse_del_tope_se_muestra_y_no_bloquea(client, db_session):
    """**El test del criterio del artboard**: «solo lectura — sin paywall ni
    billing en esta fase». Un cliente cuya cartera creció no se queda fuera de su
    propia plataforma un viernes por la tarde."""
    e = await _inquilino(client, db_session)
    h = await _superadmin(client, db_session)
    await client.put(
        f"/api/v1/superadmin/tenants/{e['t'].id}/plan",
        json={"tier": "free", "limits": {"organizations": 1, "projects": 1}},
        headers=h,
    )
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgA"}, headers=e["h"]
        )
    ).json()["id"]
    me = (await client.get("/api/v1/auth/me", headers=e["h"])).json()["id"]
    for n in ("A", "B", "C"):
        r = await client.post(
            "/api/v1/projects",
            json={
                "name": f"Proyecto {n}",
                "description": "US-221",
                "type": "bau",
                "priority": 2,
                "organization_id": org,
                "pm_id": me,
            },
            headers=e["h"],
        )
        # Tres proyectos con tope de uno: los tres se crean.
        assert r.status_code == 201, (n, r.text)
    # Y una segunda organización también, con tope de una.
    assert (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgB"}, headers=e["h"]
        )
    ).status_code == 201

    d = (await client.get("/api/v1/admin/plan", headers=e["h"])).json()
    por_clave = {u["key"]: u for u in d["usage"]}
    assert por_clave["projects"]["state"] == "excedido"
    assert por_clave["projects"]["used"] == 3
    assert d["over_limit"] is True
    # Y la consecuencia se nombra: «excedido» sin decir qué pasa no es accionable.
    assert d["consequences"]["projects"]


@pytest.mark.asyncio
async def test_un_administrador_de_inquilino_no_puede_fijar_su_propio_plan(
    client, db_session
):
    """Un inquilino que pudiera subirse el tope tendría un plan decorativo."""
    e = await _inquilino(client, db_session)
    r = await client.put(
        f"/api/v1/superadmin/tenants/{e['t'].id}/plan",
        json={"tier": "enterprise"},
        headers=e["h"],
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_el_catalogo_de_tiers_y_recursos_lo_sirve_el_backend(
    client, db_session
):
    """El vocabulario vive en el dominio: dos listas separadas divergen en cuanto
    se añade un recurso."""
    await _inquilino(client, db_session)
    h = await _superadmin(client, db_session)
    r = await client.get("/api/v1/superadmin/plan-catalog", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert [t["key"] for t in d["tiers"]] == ["free", "pro", "enterprise"]
    assert {x["key"] for x in d["resources"]} == set(CLAVES)


@pytest.mark.asyncio
async def test_un_tier_invalido_se_rechaza_en_la_frontera(client, db_session):
    e = await _inquilino(client, db_session)
    h = await _superadmin(client, db_session)
    r = await client.put(
        f"/api/v1/superadmin/tenants/{e['t'].id}/plan",
        json={"tier": "premium"},
        headers=h,
    )
    assert r.status_code == 422, r.text
