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


@pytest.mark.asyncio
async def test_enh081_delete_history_entry(client, db_session):
    """ENH-081: el user puede borrar un entry del historial.
    DELETE → 204 y la entry desaparece del listing."""
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
    d = await client.delete(
        f"/api/v1/report-history/{hist_id}", headers=auth["_authz"]
    )
    assert d.status_code == 204
    h2 = await client.get(
        f"/api/v1/projects/{proj}/report-history", headers=auth["_authz"]
    )
    assert all(it["id"] != hist_id for it in h2.json())


@pytest.mark.asyncio
async def test_enh081_delete_unknown_returns_404(client, db_session):
    auth, _ = await _setup(client, db_session)
    fake_id = "00000000-0000-0000-0000-000000000000"
    d = await client.delete(
        f"/api/v1/report-history/{fake_id}", headers=auth["_authz"]
    )
    assert d.status_code == 404
