"""EP002 — Org Hierarchy tests."""
import pytest

from tests.factories import (
    create_admin_role,
    create_program,
    create_tenant,
    create_user,
    login,
)


async def _admin_setup(client, db_session, slug="acme"):
    t = await create_tenant(db_session, slug=slug, name=slug.title())
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}", email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


# TC-023
@pytest.mark.asyncio
async def test_tc023_duplicate_org_name(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    r1 = await client.post("/api/v1/organizations", json={"name": "OrgUno"}, headers=auth["_authz"])
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/organizations", json={"name": "OrgUno"}, headers=auth["_authz"])
    assert r2.status_code == 409


# TC-024: soft delete keeps record readable
@pytest.mark.asyncio
async def test_tc024_soft_delete_org(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    r = await client.post("/api/v1/organizations", json={"name": "OrgSoft"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    dr = await client.delete(f"/api/v1/organizations/{org_id}", headers=auth["_authz"])
    assert dr.status_code == 204
    # Se puede leer aún (soft delete)
    g = await client.get(f"/api/v1/organizations/{org_id}", headers=auth["_authz"])
    assert g.status_code == 200
    assert g.json()["is_active"] is False


# BUG-068: logo subido como data-URL base64 (>500 chars) persiste íntegro.
@pytest.mark.asyncio
async def test_bug068_logo_data_url_persists(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    data_url = "data:image/png;base64," + ("A" * 1000)
    client_url = "data:image/png;base64," + ("B" * 1200)
    r = await client.post(
        "/api/v1/organizations",
        json={"name": "OrgLogo", "logo_url": data_url, "client_logo_url": client_url},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]
    g = await client.get(f"/api/v1/organizations/{org_id}", headers=auth["_authz"])
    assert g.status_code == 200
    body = g.json()
    assert body["logo_url"] == data_url
    assert body["client_logo_url"] == client_url


# TC-027: program cross-org rejected
@pytest.mark.asyncio
async def test_tc027_program_cross_org(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    ra = await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=auth["_authz"])
    org_a_id = ra.json()["id"]
    # Crear program en org A -> ok
    p = await client.post(
        "/api/v1/programs",
        json={"name": "Prog1", "organization_id": org_a_id},
        headers=auth["_authz"],
    )
    assert p.status_code == 201

    # Program con organization_id inexistente debe fallar
    import uuid

    p2 = await client.post(
        "/api/v1/programs",
        json={"name": "Prog2", "organization_id": str(uuid.uuid4())},
        headers=auth["_authz"],
    )
    assert p2.status_code == 422


# TC-028 filter programs by org
@pytest.mark.asyncio
async def test_tc028_filter_programs_by_org(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    a = (await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=auth["_authz"])).json()
    b = (await client.post("/api/v1/organizations", json={"name": "OrgB"}, headers=auth["_authz"])).json()
    await client.post("/api/v1/programs",
                       json={"name": "PA1", "organization_id": a["id"]}, headers=auth["_authz"])
    await client.post("/api/v1/programs",
                       json={"name": "PB1", "organization_id": b["id"]}, headers=auth["_authz"])
    r = await client.get(f"/api/v1/programs?organization_id={a['id']}", headers=auth["_authz"])
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1 and rows[0]["name"] == "PA1"


# TC-031 provision tenant
@pytest.mark.asyncio
async def test_tc031_provision_tenant(client, db_session):
    # superadmin sin tenant
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    r = await client.post(
        "/api/v1/superadmin/provision",
        json={
            "name": "New Client Inc",
            "slug": "newco",
            "admin_email": "admin@newco.example.com",
            "admin_full_name": "New Admin",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == "newco"
    assert body["admin_password"]

    # El admin nuevo puede hacer login
    await client.post("/api/v1/auth/login", json={
        "identifier": body.get("admin_email") or "admin@newco.example.com",
        "password": body["admin_password"],
    })
    # identifier debe ser username o email; probemos con email
    login_r2 = await client.post("/api/v1/auth/login", json={
        "identifier": "admin@newco.example.com", "password": body["admin_password"],
    })
    assert login_r2.status_code == 200
    assert login_r2.json()["user"]["must_change_password"] is True


# TC-032 slug duplicado
@pytest.mark.asyncio
async def test_tc032_provision_duplicate_slug(client, db_session):
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    payload = {
        "name": "AA", "slug": "dup", "admin_email": "a@dup.example.com",
        "admin_full_name": "AA",
    }
    r1 = await client.post("/api/v1/superadmin/provision", json=payload, headers=auth["_authz"])
    assert r1.status_code == 201
    payload["admin_email"] = "b@dup.example.com"
    r2 = await client.post("/api/v1/superadmin/provision", json=payload, headers=auth["_authz"])
    assert r2.status_code == 409


# TC-033 slug inválido
@pytest.mark.asyncio
async def test_tc033_provision_invalid_slug(client, db_session):
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    r = await client.post(
        "/api/v1/superadmin/provision",
        json={"name": "Foo", "slug": "Foo Bar",
              "admin_email": "a@foo.example.com", "admin_full_name": "A"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-038 hard delete wrong slug
@pytest.mark.asyncio
async def test_tc038_hard_delete_wrong_slug(client, db_session):
    t = await create_tenant(db_session, slug="xd", name="xd")
    await db_session.commit()
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    r = await client.delete(
        f"/api/v1/superadmin/tenants/{t.id}/permanent?confirm_slug=wrong",
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-040 join as admin
@pytest.mark.asyncio
async def test_tc040_join_as_admin(client, db_session):
    t = await create_tenant(db_session, slug="clientx", name="ClientX")
    admin_role = await create_admin_role(db_session, t)  # noqa: F841
    await db_session.commit()
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    r = await client.post(
        f"/api/v1/superadmin/tenants/{t.id}/join-as-admin", headers=auth["_authz"]
    )
    assert r.status_code == 200
    assert r.json()["tenant_slug"] == "clientx"


# TC-MT-001: tenant A admin no ve orgs del tenant B
@pytest.mark.asyncio
async def test_tcmt001_isolation_orgs(client, db_session):
    _, auth_a = await _admin_setup(client, db_session, slug="tenanta")
    _, auth_b = await _admin_setup(client, db_session, slug="tenantb")

    await client.post("/api/v1/organizations", json={"name": "OrgInA"}, headers=auth_a["_authz"])
    r = await client.get("/api/v1/organizations", headers=auth_b["_authz"])
    assert r.status_code == 200
    names = [o["name"] for o in r.json()]
    assert "OrgInA" not in names


async def _create_org(client, auth, name="OrgRoot"):
    r = await client.post("/api/v1/organizations", json={"name": name}, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ==============================================================================
# US-199 — CRUD de portafolios (reemplaza el de BU/departamentos, ADR-037)
# ==============================================================================


async def _create_portfolio(client, auth, org_id, name, **extra):
    r = await client.post(
        f"/api/v1/organizations/{org_id}/portfolios",
        json={"name": name, **extra},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_portfolio_nombre_duplicado_en_la_misma_org(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)

    await _create_portfolio(client, auth, org_id, "Transformación")
    r2 = await client.post(
        f"/api/v1/organizations/{org_id}/portfolios",
        json={"name": "Transformación"},
        headers=auth["_authz"],
    )
    assert r2.status_code == 409, (
        "Dos portafolios con el mismo nombre en una organización serían "
        "indistinguibles al clasificar un programa."
    )


@pytest.mark.asyncio
async def test_portfolios_se_listan_por_organizacion(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_a = await _create_org(client, auth, name="OrgAlpha")
    org_b = await _create_org(client, auth, name="OrgBeta")

    await _create_portfolio(client, auth, org_a, "Cartera-Alpha")
    await _create_portfolio(client, auth, org_b, "Cartera-Beta")

    r = await client.get(
        f"/api/v1/organizations/{org_a}/portfolios", headers=auth["_authz"]
    )
    assert r.status_code == 200
    assert [pf["name"] for pf in r.json()] == ["Cartera-Alpha"]


@pytest.mark.asyncio
async def test_portfolio_edicion_y_conflicto_al_renombrar(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    pf1 = await _create_portfolio(client, auth, org_id, "Crecimiento", code="CRE")
    pf2 = await _create_portfolio(client, auth, org_id, "Eficiencia")

    r = await client.patch(
        f"/api/v1/portfolios/{pf1['id']}",
        json={"description": "Lo que mueve la aguja del ingreso"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["description"] == "Lo que mueve la aguja del ingreso"
    assert r.json()["code"] == "CRE"

    r2 = await client.patch(
        f"/api/v1/portfolios/{pf1['id']}",
        json={"name": pf2["name"]},
        headers=auth["_authz"],
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_portfolio_papelera_sin_programas(client, db_session):
    """Primer paso de ADR-017: desactiva y sale de las listas."""
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    pf = await _create_portfolio(client, auth, org_id, "Innovación")

    r = await client.delete(f"/api/v1/portfolios/{pf['id']}", headers=auth["_authz"])
    assert r.status_code == 204
    g = await client.get(f"/api/v1/portfolios/{pf['id']}", headers=auth["_authz"])
    assert g.status_code == 404, "Tras la papelera ya no se lee como vivo."


@pytest.mark.asyncio
async def test_portfolio_aislamiento_entre_inquilinos(client, db_session):
    _, auth_a = await _admin_setup(client, db_session, slug="pf_t_a")
    _, auth_b = await _admin_setup(client, db_session, slug="pf_t_b")
    org_a = await _create_org(client, auth_a, name="OrgEnA")
    await _create_portfolio(client, auth_a, org_a, "CarteraDeA")

    r = await client.get(
        f"/api/v1/organizations/{org_a}/portfolios", headers=auth_b["_authz"]
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_portfolio_con_programas_activos_exige_force(client, db_session):
    """Lo que hacía la unidad de negocio con sus departamentos, ahora aquí."""
    t, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    pf = await _create_portfolio(client, auth, org_id, "ConProgramas")
    await create_program(
        db_session,
        tenant_id=t.id,
        organization_id=org_id,
        portfolio_id=pf["id"],
        name="ProgDelPortafolio",
        is_active=True,
    )
    await db_session.commit()

    r = await client.delete(f"/api/v1/portfolios/{pf['id']}", headers=auth["_authz"])
    assert r.status_code == 422, (
        "Retirar el portafolio sin decirlo dejaría sus programas colgando de "
        "algo que ninguna pantalla lista."
    )
    r2 = await client.delete(
        f"/api/v1/portfolios/{pf['id']}?force=true", headers=auth["_authz"]
    )
    assert r2.status_code == 204


@pytest.mark.asyncio
async def test_las_rutas_de_bu_y_departamentos_ya_no_existen(client, db_session):
    """TC-199 — 404, no 410 ni redirect: la entidad se retiró (ADR-037).

    Se comprueba con el token puesto para que un 404 no pueda confundirse con
    un 401: lo que se afirma es que la **ruta** no existe, no que falte auth.
    """
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    retiradas = [
        ("post", f"/api/v1/organizations/{org_id}/business-units"),
        ("get", f"/api/v1/organizations/{org_id}/business-units"),
        ("get", "/api/v1/business-units/00000000-0000-0000-0000-000000000001"),
        ("patch", "/api/v1/business-units/00000000-0000-0000-0000-000000000001"),
        ("delete", "/api/v1/business-units/00000000-0000-0000-0000-000000000001"),
        ("post", "/api/v1/business-units/00000000-0000-0000-0000-000000000001/departments"),
        ("get", "/api/v1/departments/00000000-0000-0000-0000-000000000001"),
        ("patch", "/api/v1/departments/00000000-0000-0000-0000-000000000001"),
        ("delete", "/api/v1/departments/00000000-0000-0000-0000-000000000001"),
    ]
    for metodo, ruta in retiradas:
        llamar = getattr(client, metodo)
        r = (
            await llamar(ruta, json={"name": "X"}, headers=auth["_authz"])
            if metodo in ("post", "patch")
            else await llamar(ruta, headers=auth["_authz"])
        )
        assert r.status_code == 404, f"{metodo.upper()} {ruta} devolvió {r.status_code}"


# ==============================================================================
# US-006 — Vista paneles de organizaciones (métricas)
# ==============================================================================


# TC-NEW-010: métricas de card coinciden con queries directas
@pytest.mark.asyncio
async def test_tcnew010_org_panels_metrics(client, db_session):
    from app.db.base import new_uuid
    from app.models.project import Project

    t, auth = await _admin_setup(client, db_session)

    # Org con: 2 portafolios, 1 programa, 2 proyectos (1 green, 1 red)
    org_id = await _create_org(client, auth, name="OrgConMetricas")
    pf_a = await _create_portfolio(client, auth, org_id, "Cartera-A")
    await _create_portfolio(client, auth, org_id, "Cartera-B")

    await create_program(
        db_session,
        tenant_id=t.id,
        organization_id=org_id,
        portfolio_id=pf_a["id"],
        name="Prog-1",
        is_active=True,
    )
    p1 = Project(
        id=new_uuid(),
        tenant_id=t.id,
        organization_id=org_id,
        folio="PMO-000001",
        name="P1",
        phase="ejecucion",
        health_status="green",
    )
    p2 = Project(
        id=new_uuid(),
        tenant_id=t.id,
        organization_id=org_id,
        folio="PMO-000002",
        name="P2",
        phase="preparacion",
        health_status="red",
    )
    db_session.add_all([p1, p2])
    await db_session.commit()

    r = await client.get("/api/v1/organizations/panels", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    panels = r.json()
    card = next(c for c in panels if c["name"] == "OrgConMetricas")
    assert card["portfolio_count"] == 2
    assert card["program_count"] == 1
    assert card["active_project_count"] == 2
    assert card["portfolio_health"] == {"green": 1, "yellow": 0, "red": 1}


# Panels excluye proyectos cerrados del conteo activo
@pytest.mark.asyncio
async def test_org_panels_exclude_closed(client, db_session):
    from app.db.base import new_uuid
    from app.models.project import Project

    t, auth = await _admin_setup(client, db_session, slug="closedtest")
    org_id = await _create_org(client, auth, name="OrgCerrados")
    p_closed = Project(
        id=new_uuid(),
        tenant_id=t.id,
        organization_id=org_id,
        folio="PMO-C1",
        name="Cerrado",
        phase="cerrado",
        health_status="green",
    )
    p_open = Project(
        id=new_uuid(),
        tenant_id=t.id,
        organization_id=org_id,
        folio="PMO-O1",
        name="Abierto",
        phase="ejecucion",
        health_status="yellow",
    )
    db_session.add_all([p_closed, p_open])
    await db_session.commit()
    r = await client.get("/api/v1/organizations/panels", headers=auth["_authz"])
    card = next(c for c in r.json() if c["name"] == "OrgCerrados")
    assert card["active_project_count"] == 1
    assert card["portfolio_health"]["yellow"] == 1


# Soft-delete sin hijos
