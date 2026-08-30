"""EP005 — Projects CRUD tests."""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    return t, auth, org_id


def _project_body(org_id: str, pm_id: str, **overrides) -> dict:
    base = {
        "name": "Proyecto Alfa",
        "description": "Desc",
        "type": "innovacion",
        "priority": 3,
        "organization_id": org_id,
        "pm_id": pm_id,
    }
    base.update(overrides)
    return base


# TC-070 fechas inconsistentes
@pytest.mark.asyncio
async def test_tc070_invalid_dates(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    body = _project_body(org_id, me.json()["id"], start_date="2026-05-10", end_date="2026-05-01")
    r = await client.post("/api/v1/projects", json=body, headers=auth["_authz"])
    assert r.status_code == 422


# TC-071 PM auto-asignado al team
@pytest.mark.asyncio
async def test_tc071_pm_auto_assigned(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    r = await client.post("/api/v1/projects", json=_project_body(org_id, pm_id), headers=auth["_authz"])
    assert r.status_code == 201
    proj_id = r.json()["id"]
    m = await client.get(f"/api/v1/projects/{proj_id}/members", headers=auth["_authz"])
    assert m.status_code == 200
    members = m.json()
    assert any(mm["user_id"] == pm_id and mm["role_in_project"] == "pm" for mm in members)


# TC-072 detail counts (sin módulos aún)
@pytest.mark.asyncio
async def test_tc072_detail_includes_counts(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post("/api/v1/projects",
                          json=_project_body(org_id, me.json()["id"]),
                          headers=auth["_authz"])
    proj_id = r.json()["id"]
    d = await client.get(f"/api/v1/projects/{proj_id}", headers=auth["_authz"])
    assert d.status_code == 200
    body = d.json()
    assert "members" in body and "module_counts" in body


# TC-076 transición inválida
@pytest.mark.asyncio
async def test_tc076_invalid_phase_transition(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post(
        "/api/v1/projects",
        json=_project_body(org_id, me.json()["id"], start_date="2026-01-01", end_date="2026-12-31"),
        headers=auth["_authz"],
    )
    proj_id = r.json()["id"]
    # planning -> execution OK
    ok = await client.post(f"/api/v1/projects/{proj_id}/phase/change",
                            json={"new_phase": "ejecucion"}, headers=auth["_authz"])
    assert ok.status_code == 200
    # execution -> planning inválido
    bad = await client.post(f"/api/v1/projects/{proj_id}/phase/change",
                             json={"new_phase": "preparacion"}, headers=auth["_authz"])
    assert bad.status_code == 409
    # execution -> closed OK; closed -> execution inválido
    close = await client.post(f"/api/v1/projects/{proj_id}/phase/change",
                               json={"new_phase": "cerrado"}, headers=auth["_authz"])
    assert close.status_code == 200
    reopen = await client.post(f"/api/v1/projects/{proj_id}/phase/change",
                                 json={"new_phase": "ejecucion"}, headers=auth["_authz"])
    assert reopen.status_code == 409


# TC-077 closed -> edit prohibido
@pytest.mark.asyncio
async def test_tc077_closed_readonly(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post("/api/v1/projects",
                          json=_project_body(org_id, me.json()["id"]),
                          headers=auth["_authz"])
    proj_id = r.json()["id"]
    await client.post(f"/api/v1/projects/{proj_id}/phase/change",
                       json={"new_phase": "cerrado"}, headers=auth["_authz"])
    ed = await client.patch(f"/api/v1/projects/{proj_id}",
                             json={"description": "nuevo"}, headers=auth["_authz"])
    assert ed.status_code == 422


# TC-078 miembro duplicado
@pytest.mark.asyncio
async def test_tc078_duplicate_member(client, db_session):
    t, auth, org_id = await _setup(client, db_session)
    other = await create_user(
        db_session, tenant=t, username="other", email="other@acme.example.com",
        password="Str0ng-Other-1!",
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post("/api/v1/projects",
                          json=_project_body(org_id, me.json()["id"]),
                          headers=auth["_authz"])
    proj_id = r.json()["id"]
    a = await client.post(f"/api/v1/projects/{proj_id}/members",
                           json={"user_id": str(other.id), "role_in_project": "team"},
                           headers=auth["_authz"])
    assert a.status_code == 201
    b = await client.post(f"/api/v1/projects/{proj_id}/members",
                           json={"user_id": str(other.id), "role_in_project": "team"},
                           headers=auth["_authz"])
    assert b.status_code == 409


# TC-079 remover PM
@pytest.mark.asyncio
async def test_tc079_cannot_remove_pm(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    r = await client.post("/api/v1/projects",
                          json=_project_body(org_id, pm_id),
                          headers=auth["_authz"])
    proj_id = r.json()["id"]
    rm = await client.delete(f"/api/v1/projects/{proj_id}/members/{pm_id}",
                              headers=auth["_authz"])
    assert rm.status_code == 422


# TC-080 export JSON
@pytest.mark.asyncio
async def test_tc080_export_json(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post("/api/v1/projects",
                          json=_project_body(org_id, me.json()["id"]),
                          headers=auth["_authz"])
    proj_id = r.json()["id"]
    j = await client.get(f"/api/v1/projects/{proj_id}/export?format=json",
                          headers=auth["_authz"])
    assert j.status_code == 200
    assert j.json()["folio"]


# TC-067 filtros combinados
@pytest.mark.asyncio
async def test_tc067_filters_combine(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    for i, ptype in enumerate(["innovacion", "transformacion", "bau"]):
        await client.post(
            "/api/v1/projects",
            json=_project_body(org_id, pm_id, name=f"P{i}", type=ptype, priority=(i % 5) + 1),
            headers=auth["_authz"],
        )
    r = await client.get(
        "/api/v1/projects?type=innovation&phase=planning", headers=auth["_authz"]
    )
    assert r.status_code == 200
    assert all(p["type"] == "innovacion" and p["phase"] == "preparacion" for p in r.json())


# ADR-038 — el filtro con el vocabulario viejo devolvía cero y no fallaba: un
# marcador guardado antes del renombrado veía una lista vacía y la creía cierta.
@pytest.mark.asyncio
async def test_filtro_phase_acepta_el_nombre_viejo(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post(
        "/api/v1/projects", json=_project_body(org_id, me.json()["id"]), headers=auth["_authz"]
    )
    assert r.status_code == 201
    creado = r.json()["id"]

    viejo = await client.get("/api/v1/projects?phase=planning", headers=auth["_authz"])
    assert viejo.status_code == 200
    assert [p["id"] for p in viejo.json()] == [creado]

    nuevo = await client.get("/api/v1/projects?phase=preparacion", headers=auth["_authz"])
    assert nuevo.json() == viejo.json(), "el nombre viejo y el canónico son el mismo filtro"


# ============================================================================
# US-018 — Módulo Áreas/Organigrama del proyecto
# ============================================================================


# Tests de project_areas eliminados (ENH-078): la feature se movió al
# catálogo tenant `/api/v1/areas` + `area_assignments`. Ver
# test_us064_raid_area.py para el helper actualizado y test_us097_*
# para el catálogo nuevo.
