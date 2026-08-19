"""US-152 — Endpoints de analytics: trends, risk-matrix, heatmap, treemap, capture."""
from decimal import Decimal

import pytest

from app.models.modules import Risk
from app.models.project import Project
from app.models.role import Role
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

    specs = [
        ("preparacion", "green", Decimal("100000"), prog.id),
        ("ejecucion", "yellow", Decimal("200000"), prog.id),
        ("ejecucion", "red", Decimal("500000"), None),
    ]
    projects = []
    for i, (phase, health, budget, program_id) in enumerate(specs):
        p = Project(
            tenant_id=t.id, organization_id=org_id, program_id=program_id,
            folio=f"PRJ-2026-{i + 1:03d}", name=f"P{i + 1}", phase=phase,
            health_status=health, budget=budget, progress=20, type="transformacion",
        )
        db_session.add(p)
        projects.append(p)
    await db_session.flush()

    # Riesgos abiertos en P3 con prob/impacto para la matriz.
    for folio, prob, imp, sev, status in [
        ("R-1", 5, 4, 20, "open"),
        ("R-2", 5, 4, 20, "in_progress"),
        ("R-3", 2, 2, 4, "open"),
        ("R-4", 3, 3, 9, "resolved"),  # cerrado → excluido
    ]:
        db_session.add(
            Risk(
                tenant_id=t.id, project_id=projects[2].id, folio=folio, title=folio,
                status=status, probability=prob, impact=imp, severity=sev,
            )
        )
    await db_session.commit()
    return t, auth, org_id, prog, projects


@pytest.mark.asyncio
async def test_capture_then_trends(client, db_session):
    t, auth, org_id, prog, projects = await _setup(client, db_session)

    r = await client.post("/api/v1/dashboard/snapshots/capture", headers=auth["_authz"])
    assert r.status_code == 200
    # 1 tenant + 1 org + 1 programa + 3 proyectos
    assert r.json()["rows"] == 6

    r = await client.get("/api/v1/dashboard/trends?scope=tenant", headers=auth["_authz"])
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "tenant"
    assert len(body["series"]) == 1
    assert body["series"][0]["projects_total"] == 3

    # Filtro por métrica única.
    r = await client.get(
        "/api/v1/dashboard/trends?scope=tenant&metric=budget_plan", headers=auth["_authz"]
    )
    assert r.status_code == 200
    pt = r.json()["series"][0]
    assert pt["budget_plan"] == 800000.0
    assert "projects_total" not in pt


@pytest.mark.asyncio
async def test_trends_bad_params(client, db_session):
    _t, auth, *_ = await _setup(client, db_session)
    assert (
        await client.get("/api/v1/dashboard/trends?scope=bogus", headers=auth["_authz"])
    ).status_code == 400
    assert (
        await client.get(
            "/api/v1/dashboard/trends?scope=organization", headers=auth["_authz"]
        )
    ).status_code == 400  # falta id
    assert (
        await client.get(
            "/api/v1/dashboard/trends?scope=tenant&metric=nope", headers=auth["_authz"]
        )
    ).status_code == 400


@pytest.mark.asyncio
async def test_risk_matrix(client, db_session):
    _t, auth, *_ = await _setup(client, db_session)
    r = await client.get("/api/v1/dashboard/risk-matrix?scope=tenant", headers=auth["_authz"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3  # 3 abiertos (R-4 cerrado excluido)
    cell = next(c for c in body["cells"] if c["probability"] == 5 and c["impact"] == 4)
    assert cell["count"] == 2


@pytest.mark.asyncio
async def test_heatmap(client, db_session):
    t, auth, org_id, *_ = await _setup(client, db_session)
    r = await client.get("/api/v1/dashboard/heatmap", headers=auth["_authz"])
    assert r.status_code == 200
    rows = r.json()["rows"]
    row = next(x for x in rows if x["org_id"] == org_id)
    assert row["green"] == 1
    assert row["yellow"] == 1
    assert row["red"] == 1
    assert row["total"] == 3


@pytest.mark.asyncio
async def test_treemap_nesting(client, db_session):
    t, auth, org_id, prog, projects = await _setup(client, db_session)
    r = await client.get("/api/v1/dashboard/treemap?scope=tenant", headers=auth["_authz"])
    assert r.status_code == 200
    tree = r.json()["tree"]
    org_node = next(o for o in tree if o["id"] == org_id)
    prog_ids = {c["id"] for c in org_node["children"]}
    assert str(prog.id) in prog_ids
    assert "none" in prog_ids  # P3 sin programa
    prog_node = next(c for c in org_node["children"] if c["id"] == str(prog.id))
    assert len(prog_node["children"]) == 2  # P1 + P2
    assert all("value" in leaf and "health" in leaf for leaf in prog_node["children"])


@pytest.mark.asyncio
async def test_heatmap_scoped_to_pm_projects(client, db_session):
    """US-162: un PM ve en el heatmap solo los proyectos donde es pm_id."""
    t, auth, org_id, _prog, projects = await _setup(client, db_session)
    # Admin ve los 3 proyectos de la org.
    radm = await client.get("/api/v1/dashboard/heatmap", headers=auth["_authz"])
    org_row_adm = next(r for r in radm.json()["rows"] if r["org_id"] == org_id)
    assert org_row_adm["total"] == 3

    pm_role = Role(
        tenant_id=t.id, name="Project Manager", description="PM", is_system=True,
        permissions={"projects": ["read"], "dashboard": ["read"]},
    )
    db_session.add(pm_role)
    await db_session.flush()
    pm = await create_user(
        db_session, tenant=t, username="pmx", email="pmx@acme.example.com",
        password="Str0ng-Pmx-1!", roles=[pm_role],
    )
    from app.models.user_scope_assignment import UserScopeAssignment
    db_session.add(UserScopeAssignment(
        tenant_id=t.id, user_id=pm.id,
        scope_type="project", scope_id=str(projects[0].id),
    ))
    await db_session.commit()

    pauth = await login(client, "pmx", "Str0ng-Pmx-1!")
    rpm = await client.get("/api/v1/dashboard/heatmap", headers=pauth["_authz"])
    assert rpm.status_code == 200
    org_row_pm = next(r for r in rpm.json()["rows"] if r["org_id"] == org_id)
    assert org_row_pm["total"] == 1  # solo su proyecto


@pytest.mark.asyncio
async def test_heatmap_non_admin_scoped(client, db_session):
    """US-162: el heatmap ya no es admin-only; un no-admin lo consulta pero
    solo cuenta sus proyectos visibles (aquí, ninguno → conteos vacíos)."""
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="adm2", email="adm2@acme.example.com",
        password="Str0ng-Adm-2!", roles=[admin_role],
    )
    await create_user(
        db_session, tenant=t, username="plain", email="plain@acme.example.com",
        password="Str0ng-Pl-1!",
    )
    auth = await login(client, "plain", "Str0ng-Pl-1!")
    r = await client.get("/api/v1/dashboard/heatmap", headers=auth["_authz"])
    assert r.status_code == 200
    # Sin proyectos visibles: cada organización (si existiera) tendría 0.
    assert all(row["total"] == 0 for row in r.json()["rows"])
