"""US-034 — Resumen de programa."""
from decimal import Decimal

import pytest

from app.models.modules import Risk
from app.models.organization import Organization, Program
from app.models.project import Project
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


@pytest.mark.asyncio
async def test_us034_summary_aggregates_correctly(client, db_session):
    t, auth = await _admin(client, db_session, slug="summary-a")
    me = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()

    org = Organization(tenant_id=t.id, name="Org-A", is_active=True)
    db_session.add(org)
    await db_session.flush()
    prog = Program(
        tenant_id=t.id, organization_id=org.id, name="Prog-A", is_active=True
    )
    db_session.add(prog)
    await db_session.flush()

    # 3 proyectos: 1 green activo, 1 yellow activo, 1 red cerrado
    projects_data = [
        ("P-100", "green", "execution", 10000, 3000, 40),
        ("P-101", "yellow", "execution", 5000, 2000, 20),
        ("P-102", "red", "closed", 20000, 20000, 100),
    ]
    created_projects = []
    for folio, health, phase, budget, actual, progress in projects_data:
        p = Project(
            tenant_id=str(t.id),
            organization_id=str(org.id),
            program_id=str(prog.id),
            folio=folio,
            name=folio,
            phase=phase,
            health_status=health,
            budget=Decimal(str(budget)),
            actual_budget=Decimal(str(actual)),
            progress=progress,
            pm_id=me["id"],
        )
        db_session.add(p)
        await db_session.flush()
        created_projects.append(p)

    # Riesgos: uno severity 20 abierto (aparece), uno 5 abierto (no aparece),
    # uno 25 cerrado (no aparece).
    db_session.add(
        Risk(
            tenant_id=str(t.id), project_id=created_projects[0].id,
            folio="RIS-1", title="Riesgo alto", status="identified",
            severity=20, probability=4, impact=5,
        )
    )
    db_session.add(
        Risk(
            tenant_id=str(t.id), project_id=created_projects[0].id,
            folio="RIS-2", title="Riesgo bajo", status="identified",
            severity=5, probability=1, impact=5,
        )
    )
    db_session.add(
        Risk(
            tenant_id=str(t.id), project_id=created_projects[1].id,
            folio="RIS-3", title="Riesgo cerrado", status="closed",
            severity=25, probability=5, impact=5,
        )
    )
    await db_session.commit()

    r = await client.get(
        f"/api/v1/programs/{prog.id}/summary", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == str(prog.id)
    assert data["organization_name"] == "Org-A"
    assert data["project_total"] == 3
    assert data["project_active"] == 2
    assert data["project_closed"] == 1
    # at_risk cuenta proyectos no-cerrados con health != green
    assert data["project_at_risk"] == 1
    assert data["health"]["green"] == 1
    assert data["health"]["yellow"] == 1
    # El red está cerrado, no se cuenta en health de proyectos activos
    assert data["health"]["red"] == 0
    assert data["budget_planned"] == 35000.0
    assert data["budget_actual"] == 25000.0
    assert len(data["projects"]) == 3
    # Top risks: solo uno califica (severity 20, not closed)
    assert len(data["top_risks"]) == 1
    assert data["top_risks"][0]["severity"] == 20
    assert data["top_risks"][0]["title"] == "Riesgo alto"


@pytest.mark.asyncio
async def test_us034_summary_cross_tenant_404(client, db_session):
    t_a, _auth_a = await _admin(client, db_session, slug="summary-b")
    _, auth_b = await _admin(client, db_session, slug="summary-c")

    org = Organization(tenant_id=t_a.id, name="Org-B", is_active=True)
    db_session.add(org)
    await db_session.flush()
    prog = Program(
        tenant_id=t_a.id, organization_id=org.id, name="Prog-B", is_active=True
    )
    db_session.add(prog)
    await db_session.commit()

    r = await client.get(
        f"/api/v1/programs/{prog.id}/summary", headers=auth_b["_authz"]
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_us034_summary_empty_program(client, db_session):
    t, auth = await _admin(client, db_session, slug="summary-d")
    org = Organization(tenant_id=t.id, name="Org-D", is_active=True)
    db_session.add(org)
    await db_session.flush()
    prog = Program(
        tenant_id=t.id, organization_id=org.id, name="Prog-D", is_active=True
    )
    db_session.add(prog)
    await db_session.commit()

    r = await client.get(
        f"/api/v1/programs/{prog.id}/summary", headers=auth["_authz"]
    )
    assert r.status_code == 200
    data = r.json()
    assert data["project_total"] == 0
    assert data["budget_planned"] == 0
    assert data["top_risks"] == []
