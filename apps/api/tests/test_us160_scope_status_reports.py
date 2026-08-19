"""US-160 — reportes de status N1 (portafolio) y N2 (org/programa) en PDF.

render_pdf está stubbeado por conftest (devuelve %PDF mock), así que estos
tests validan el wiring endpoint→builder→PDF y la autorización, no el render
real de WeasyPrint.
"""
from decimal import Decimal

import pytest

from app.models.project import Project
from tests.factories import (
    create_admin_role,
    create_program,
    create_tenant,
    create_user,
    login,
)


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        "/api/v1/organizations", json={"name": "OrgA"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]
    prog = await create_program(
        db_session, tenant_id=t.id, organization_id=org_id, name="Prog A"
    )
    for i, (phase, health, prog_id) in enumerate([
        ("preparacion", "green", prog.id),
        ("ejecucion", "red", prog.id),
        ("ejecucion", "yellow", None),
    ]):
        db_session.add(Project(
            tenant_id=t.id, organization_id=org_id, program_id=prog_id,
            folio=f"PRJ-{i+1:03d}", name=f"P{i+1}", phase=phase,
            health_status=health, budget=Decimal("100000"), progress=30,
            type="transformacion",
        ))
    await db_session.commit()
    return t, auth, org_id, str(prog.id)


def _is_pdf(resp):
    return (
        resp.status_code == 200
        and resp.headers["content-type"] == "application/pdf"
        and resp.content[:4] == b"%PDF"
    )


@pytest.mark.asyncio
async def test_portfolio_report_pdf(client, db_session):
    _t, auth, _org, _prog = await _setup(client, db_session)
    r = await client.post("/api/v1/dashboard/reports/portfolio", headers=auth["_authz"])
    assert _is_pdf(r)


@pytest.mark.asyncio
async def test_org_report_pdf(client, db_session):
    _t, auth, org_id, _prog = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/organizations/{org_id}/reports/status", headers=auth["_authz"]
    )
    assert _is_pdf(r)


@pytest.mark.asyncio
async def test_program_report_pdf(client, db_session):
    _t, auth, _org, prog_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/programs/{prog_id}/reports/status", headers=auth["_authz"]
    )
    assert _is_pdf(r)


@pytest.mark.asyncio
async def test_portfolio_report_non_admin_scoped(client, db_session):
    """US-162: un no-admin puede descargar el reporte (scoped a sus proyectos);
    capturar snapshots sigue siendo admin-only."""
    t = await create_tenant(db_session, slug="np", name="NP")
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="adm", email="adm@np.example.com",
        password="Str0ng-Adm-9!", roles=[admin_role],
    )
    await create_user(
        db_session, tenant=t, username="plain", email="plain@np.example.com",
        password="Str0ng-Pl-9!",
    )
    auth = await login(client, "plain", "Str0ng-Pl-9!")
    r = await client.post("/api/v1/dashboard/reports/portfolio", headers=auth["_authz"])
    assert _is_pdf(r)
    # capture sigue restringido a admins
    rc = await client.post("/api/v1/dashboard/snapshots/capture", headers=auth["_authz"])
    assert rc.status_code == 403
