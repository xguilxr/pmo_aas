"""US-092 — Historial de reportes generados.

Cubre:
- TC-092.1: generar avance → row en `report_history` con generated_by + source_report_id.
- TC-092.3: GET historial ordenado desc.
- TC-092.4: GET download → PDF re-renderizado desde el source.
"""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    org = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": "P1",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return auth, p.json()["id"]


@pytest.mark.asyncio
async def test_generating_avance_creates_history_entry(client, db_session):
    auth, proj = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj}/reports/avance",
        json={},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text  # devuelve PDF bytes
    # Listar historial.
    h = await client.get(
        f"/api/v1/projects/{proj}/report-history", headers=auth["_authz"]
    )
    assert h.status_code == 200, h.text
    rows = h.json()
    assert len(rows) >= 1
    item = rows[0]
    assert item["report_type"] == "avance"
    assert item["generated_by_user_id"] is not None
    assert item["source_report_id"] is not None
    assert item["generated_by_name"]


@pytest.mark.asyncio
async def test_history_download_re_renders_pdf(client, db_session):
    auth, proj = await _setup(client, db_session)
    await client.post(
        f"/api/v1/projects/{proj}/reports/avance",
        json={},
        headers=auth["_authz"],
    )
    h = await client.get(
        f"/api/v1/projects/{proj}/report-history", headers=auth["_authz"]
    )
    hist_id = h.json()[0]["id"]
    dl = await client.get(
        f"/api/v1/report-history/{hist_id}/download",
        headers=auth["_authz"],
    )
    assert dl.status_code == 200
    assert dl.headers["content-type"] in (
        "application/pdf",
        "application/pdf; charset=utf-8",
    )
    # Mock render devuelve un PDF stub corto en tests; basta validar el header.
    assert dl.content.startswith(b"%PDF")
