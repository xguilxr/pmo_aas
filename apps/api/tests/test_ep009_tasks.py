"""EP009 — MS Project + tasks tests."""
import pytest

from app.services.msproject.xml_parser import parse_ms_project_xml
from tests.factories import create_admin_role, create_tenant, create_user, login


SIMPLE_MSP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Tasks>
    <Task>
      <UID>0</UID>
      <Name>Root</Name>
    </Task>
    <Task>
      <UID>1</UID>
      <Name>Analisis</Name>
      <WBS>1</WBS>
      <Start>2026-01-01T09:00:00</Start>
      <Finish>2026-01-10T17:00:00</Finish>
      <Duration>PT80H0M0S</Duration>
      <PercentComplete>50</PercentComplete>
      <Milestone>0</Milestone>
    </Task>
    <Task>
      <UID>2</UID>
      <Name>Desarrollo</Name>
      <WBS>2</WBS>
      <Start>2026-01-11T09:00:00</Start>
      <Finish>2026-02-10T17:00:00</Finish>
      <Duration>PT240H0M0S</Duration>
      <PercentComplete>10</PercentComplete>
      <Milestone>0</Milestone>
      <PredecessorLink>
        <PredecessorUID>1</PredecessorUID>
        <Type>1</Type>
        <LinkLag>0</LinkLag>
      </PredecessorLink>
    </Task>
    <Task>
      <UID>3</UID>
      <Name>Go-Live</Name>
      <Milestone>1</Milestone>
      <Start>2026-02-11T00:00:00</Start>
      <Finish>2026-02-11T00:00:00</Finish>
      <PredecessorLink>
        <PredecessorUID>2</PredecessorUID>
        <Type>1</Type>
        <LinkLag>480</LinkLag>
      </PredecessorLink>
    </Task>
  </Tasks>
</Project>
"""


# TC-126 parser deps + lag
def test_tc126_parser_extracts_deps_lag():
    tasks, errs = parse_ms_project_xml(SIMPLE_MSP_XML.encode())
    assert not errs
    assert len(tasks) == 3
    go_live = next(t for t in tasks if t.external_id == "3")
    assert go_live.is_milestone is True
    assert len(go_live.predecessors) == 1
    assert go_live.predecessors[0].type == "FS"
    assert go_live.predecessors[0].lag_days == 1


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    org = await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"])
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={"name": "PMSP", "description": "d", "type": "bau", "priority": 3,
              "organization_id": org.json()["id"], "pm_id": me.json()["id"]},
        headers=auth["_authz"],
    )
    return t, auth, p.json()["id"]


# TC-127 integration: xml con tasks importados
@pytest.mark.asyncio
async def test_tc127_import_msp_xml(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    files = {"file": ("project.xml", SIMPLE_MSP_XML.encode(), "application/xml")}
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import",
        files=files, headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported"] == 3
    assert body["dependencies_created"] == 2

    # Gantt returns tasks + deps
    g = await client.get(f"/api/v1/projects/{proj_id}/gantt", headers=auth["_authz"])
    assert g.status_code == 200
    assert len(g.json()["tasks"]) == 3
    assert len(g.json()["dependencies"]) == 2


# TC-128 archivo corrupto
@pytest.mark.asyncio
async def test_tc128_corrupt_file(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    files = {"file": ("bad.xml", b"<not valid xml", "application/xml")}
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import",
        files=files, headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-129 merge strategy actualiza existing
@pytest.mark.asyncio
async def test_tc129_merge_strategy(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    files = {"file": ("p.xml", SIMPLE_MSP_XML.encode(), "application/xml")}
    r1 = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import?strategy=replace",
        files=files, headers=auth["_authz"],
    )
    assert r1.status_code == 200
    # Re-import merge (no duplicados)
    files2 = {"file": ("p.xml", SIMPLE_MSP_XML.encode(), "application/xml")}
    r2 = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import?strategy=merge",
        files=files2, headers=auth["_authz"],
    )
    assert r2.status_code == 200
    lst = await client.get(f"/api/v1/projects/{proj_id}/tasks", headers=auth["_authz"])
    assert len(lst.json()) == 3  # sin duplicar


# US-050 CRUD manual de tareas
@pytest.mark.asyncio
async def test_manual_task_crud(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "Tarea 1", "start_date": "2026-01-01", "end_date": "2026-01-10", "progress": 20},
        headers=auth["_authz"],
    )
    assert r.status_code == 201
    tid = r.json()["id"]
    u = await client.patch(f"/api/v1/tasks/{tid}",
                             json={"progress": 60, "status": "in_progress"},
                             headers=auth["_authz"])
    assert u.status_code == 200
    assert u.json()["progress"] == 60
    d = await client.delete(f"/api/v1/tasks/{tid}", headers=auth["_authz"])
    assert d.status_code == 204
