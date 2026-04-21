"""EP004 — Dashboard tests."""
from decimal import Decimal

import pytest

from app.models.project import Project
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _seed_projects(db_session, tenant_id: str, org_id: str) -> list[Project]:
    projects = []
    for i, (phase, health, budget, progress, ptype) in enumerate([
        ("planning", "green", Decimal("100000"), 10, "innovation"),
        ("execution", "yellow", Decimal("200000"), 45, "transformation"),
        ("execution", "red", Decimal("500000"), 30, "transformation"),
        ("closed", "green", Decimal("50000"), 100, "bau"),
    ]):
        p = Project(
            tenant_id=tenant_id,
            organization_id=org_id,
            folio=f"PRJ-2026-{i+1:03d}",
            name=f"Project {i+1}",
            phase=phase,
            health_status=health,
            budget=budget,
            progress=progress,
            type=ptype,
        )
        db_session.add(p)
        projects.append(p)
    await db_session.commit()
    return projects


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post("/api/v1/organizations", json={"name": "OrgDash"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    return t, auth, org_id


@pytest.mark.asyncio
async def test_kpis_with_projects(client, db_session):
    t, auth, org_id = await _setup(client, db_session)
    await _seed_projects(db_session, str(t.id), org_id)
    r = await client.get("/api/v1/dashboard/kpis", headers=auth["_authz"])
    assert r.status_code == 200
    data = r.json()
    assert data["active_projects"] == 3  # planning + execution*2
    assert data["budget_total"] == 100000.0 + 200000.0 + 500000.0 + 50000.0
    # Avance promedio de activos: (10+45+30)/3
    assert abs(data["progress_avg"] - ((10 + 45 + 30) / 3)) < 0.5


@pytest.mark.asyncio
async def test_charts_datasets(client, db_session):
    t, auth, org_id = await _setup(client, db_session)
    await _seed_projects(db_session, str(t.id), org_id)
    r = await client.get("/api/v1/dashboard/charts", headers=auth["_authz"])
    assert r.status_code == 200
    data = r.json()
    assert data["projects_by_phase"]["execution"] == 2
    assert data["projects_by_phase"]["planning"] == 1
    assert data["portfolio_health"]["red"] == 1
    assert data["portfolio_health"]["yellow"] == 1


@pytest.mark.asyncio
async def test_plan_vs_actual_order_red_first(client, db_session):
    t, auth, org_id = await _setup(client, db_session)
    await _seed_projects(db_session, str(t.id), org_id)
    r = await client.get("/api/v1/dashboard/plan-vs-actual", headers=auth["_authz"])
    assert r.status_code == 200
    rows = r.json()
    assert rows[0]["health"] == "red"
    assert rows[-1]["health"] == "green"


@pytest.mark.asyncio
async def test_plan_vs_actual_filter_phase(client, db_session):
    t, auth, org_id = await _setup(client, db_session)
    await _seed_projects(db_session, str(t.id), org_id)
    r = await client.get(
        "/api/v1/dashboard/plan-vs-actual?phase=execution", headers=auth["_authz"]
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_plan_vs_actual_csv_export(client, db_session):
    t, auth, org_id = await _setup(client, db_session)
    await _seed_projects(db_session, str(t.id), org_id)
    r = await client.get("/api/v1/dashboard/plan-vs-actual/export.csv", headers=auth["_authz"])
    assert r.status_code == 200
    content = r.content.decode()
    assert "folio" in content
    assert "health" in content
    # 4 filas + header
    assert content.count("\r\n") >= 4 or content.count("\n") >= 4


@pytest.mark.asyncio
async def test_dashboard_tenant_isolation(client, db_session):
    t_a = await create_tenant(db_session, slug="aa", name="A")
    t_b = await create_tenant(db_session, slug="bb", name="B")
    role_a = await create_admin_role(db_session, t_a)
    role_b = await create_admin_role(db_session, t_b)
    await create_user(db_session, tenant=t_a, username="admin_a", email="admin@a.example.com",
                      password="Str0ng-AA-1!", roles=[role_a])
    await create_user(db_session, tenant=t_b, username="admin_b", email="admin@b.example.com",
                      password="Str0ng-BB-1!", roles=[role_b])

    auth_a = await login(client, "admin_a", "Str0ng-AA-1!")
    auth_b = await login(client, "admin_b", "Str0ng-BB-1!")
    ra = await client.post("/api/v1/organizations", json={"name": "OA"}, headers=auth_a["_authz"])
    await _seed_projects(db_session, str(t_a.id), ra.json()["id"])

    rk = await client.get("/api/v1/dashboard/kpis", headers=auth_b["_authz"])
    assert rk.status_code == 200
    assert rk.json()["active_projects"] == 0
    assert rk.json()["budget_total"] == 0.0


# ============================================================================
# US-014 — Filtro de organización en dashboard
# ============================================================================


@pytest.mark.asyncio
async def test_us014_kpis_filtered_by_org(client, db_session):
    """Dos orgs con proyectos distintos: filtro por org devuelve sólo los suyos."""
    t, auth, org_a = await _setup(client, db_session)
    # Segunda org dentro del mismo tenant
    rb = await client.post(
        "/api/v1/organizations", json={"name": "OrgBeta"}, headers=auth["_authz"]
    )
    org_b = rb.json()["id"]

    await _seed_projects(db_session, str(t.id), org_a)
    # Proyecto adicional en org B
    other = Project(
        tenant_id=str(t.id),
        organization_id=org_b,
        folio="PRJ-2026-099",
        name="Beta-1",
        phase="execution",
        health_status="green",
        budget=Decimal("700000"),
        progress=20,
        type="innovation",
    )
    db_session.add(other)
    await db_session.commit()

    # Sin filtro: 4 activos (3 de A + 1 de B) y budget total suma ambos
    r_all = await client.get("/api/v1/dashboard/kpis", headers=auth["_authz"])
    all_kpis = r_all.json()
    assert all_kpis["active_projects"] == 4

    # Filtro por org_a: 3 activos (excluye el closed y el de org B)
    r_a = await client.get(
        f"/api/v1/dashboard/kpis?organization_id={org_a}", headers=auth["_authz"]
    )
    kpis_a = r_a.json()
    assert kpis_a["active_projects"] == 3
    # Budget total del filtro ≠ total sin filtro
    assert kpis_a["budget_total"] != all_kpis["budget_total"]

    # Filtro por org_b: 1 solo proyecto
    r_b = await client.get(
        f"/api/v1/dashboard/kpis?organization_id={org_b}", headers=auth["_authz"]
    )
    assert r_b.json()["active_projects"] == 1


@pytest.mark.asyncio
async def test_us014_charts_filtered_by_org(client, db_session):
    t, auth, org_a = await _setup(client, db_session)
    rb = await client.post(
        "/api/v1/organizations", json={"name": "OrgBeta"}, headers=auth["_authz"]
    )
    org_b = rb.json()["id"]
    await _seed_projects(db_session, str(t.id), org_a)

    r = await client.get(
        f"/api/v1/dashboard/charts?organization_id={org_b}", headers=auth["_authz"]
    )
    assert r.status_code == 200
    data = r.json()
    # OrgB no tiene proyectos → conteos vacíos
    assert data["projects_by_phase"] == {}


# ============================================================================
# US-015 — KPIs respetan jerarquía de roles
# ============================================================================


async def _pm_role(db_session, tenant) -> "Role":
    from app.models.role import Role
    r = Role(
        tenant_id=tenant.id,
        name="Project Manager",
        description="PM",
        is_system=True,
        permissions={
            "projects": ["read", "update"],
            "dashboard": ["read"],
        },
    )
    db_session.add(r)
    await db_session.flush()
    return r


@pytest.mark.asyncio
async def test_us015_admin_sees_all(client, db_session):
    """Admin-equivalente ve todos los proyectos del tenant."""
    t, auth, org_id = await _setup(client, db_session)
    await _seed_projects(db_session, str(t.id), org_id)

    r = await client.get("/api/v1/dashboard/kpis", headers=auth["_authz"])
    assert r.status_code == 200
    # _seed_projects crea 4 proyectos, 3 activos
    assert r.json()["active_projects"] == 3


@pytest.mark.asyncio
async def test_us015_pm_sees_only_assigned_projects(client, db_session):
    """Project Manager ve solo proyectos donde es pm_id o member."""
    from sqlalchemy import select as sa_select
    from app.models.project import Project

    t, _admin_auth, org_id = await _setup(client, db_session)
    projects = await _seed_projects(db_session, str(t.id), org_id)

    pm_role = await _pm_role(db_session, t)
    pm_user = await create_user(
        db_session, tenant=t, username="pmuser",
        email="pm@acme.example.com", password="Str0ng-Pm-1!",
        roles=[pm_role],
    )
    # Asignar al PM sólo al primer proyecto (phase=planning → activo)
    projects[0].pm_id = str(pm_user.id)
    await db_session.commit()

    auth = await login(client, "pmuser", "Str0ng-Pm-1!")
    r = await client.get("/api/v1/dashboard/kpis", headers=auth["_authz"])
    assert r.status_code == 200
    # Sólo 1 proyecto activo (el que le asignaron) vs 3 que ve el admin
    assert r.json()["active_projects"] == 1
    # Budget total sólo del proyecto asignado
    assert r.json()["budget_total"] == 100000.0


@pytest.mark.asyncio
async def test_us015_pm_sees_member_projects(client, db_session):
    """Project Manager también ve proyectos donde es miembro, no sólo pm_id."""
    from app.models.project_member import ProjectMember

    t, _admin_auth, org_id = await _setup(client, db_session)
    projects = await _seed_projects(db_session, str(t.id), org_id)

    pm_role = await _pm_role(db_session, t)
    pm_user = await create_user(
        db_session, tenant=t, username="member1",
        email="mem1@acme.example.com", password="Str0ng-M1-1!",
        roles=[pm_role],
    )
    # Sólo como miembro del segundo proyecto (no pm)
    db_session.add(
        ProjectMember(
            project_id=projects[1].id,
            user_id=str(pm_user.id),
            role_in_project="team",
        )
    )
    await db_session.commit()
    auth = await login(client, "member1", "Str0ng-M1-1!")

    r = await client.get("/api/v1/dashboard/kpis", headers=auth["_authz"])
    assert r.status_code == 200
    assert r.json()["active_projects"] == 1


@pytest.mark.asyncio
async def test_us015_pm_without_projects_sees_zero(client, db_session):
    """Un PM sin proyectos asignados ve ceros."""
    t, _admin_auth, org_id = await _setup(client, db_session)
    await _seed_projects(db_session, str(t.id), org_id)

    pm_role = await _pm_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="orphan",
        email="orphan@acme.example.com", password="Str0ng-Or-1!",
        roles=[pm_role],
    )
    auth = await login(client, "orphan", "Str0ng-Or-1!")
    r = await client.get("/api/v1/dashboard/kpis", headers=auth["_authz"])
    assert r.status_code == 200
    assert r.json()["active_projects"] == 0
    assert r.json()["budget_total"] == 0.0


@pytest.mark.asyncio
async def test_us015_charts_respect_role(client, db_session):
    t, _admin_auth, org_id = await _setup(client, db_session)
    projects = await _seed_projects(db_session, str(t.id), org_id)

    pm_role = await _pm_role(db_session, t)
    pm_user = await create_user(
        db_session, tenant=t, username="cpm",
        email="cpm@acme.example.com", password="Str0ng-Cpm-1!",
        roles=[pm_role],
    )
    projects[0].pm_id = str(pm_user.id)
    await db_session.commit()

    auth = await login(client, "cpm", "Str0ng-Cpm-1!")
    r = await client.get("/api/v1/dashboard/charts", headers=auth["_authz"])
    data = r.json()
    # Sólo 1 proyecto (phase=planning)
    assert data["projects_by_phase"] == {"planning": 1}


@pytest.mark.asyncio
async def test_us015_plan_vs_actual_respects_role(client, db_session):
    t, _admin_auth, org_id = await _setup(client, db_session)
    projects = await _seed_projects(db_session, str(t.id), org_id)

    pm_role = await _pm_role(db_session, t)
    pm_user = await create_user(
        db_session, tenant=t, username="pvapm",
        email="pva@acme.example.com", password="Str0ng-Pva-1!",
        roles=[pm_role],
    )
    projects[0].pm_id = str(pm_user.id)
    await db_session.commit()

    auth = await login(client, "pvapm", "Str0ng-Pva-1!")
    r = await client.get("/api/v1/dashboard/plan-vs-actual", headers=auth["_authz"])
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["folio"] == projects[0].folio


# ============================================================================
# BUG-003 — columna PM Asignado en Plan vs Real
# ============================================================================


@pytest.mark.asyncio
async def test_bug003_pm_name_in_plan_vs_actual(client, db_session):
    """/plan-vs-actual devuelve pm_id y pm_name para cada proyecto."""
    t, auth, org_id = await _setup(client, db_session)
    projects = await _seed_projects(db_session, str(t.id), org_id)

    pm = await create_user(
        db_session, tenant=t, username="pm_asignado",
        email="pma@acme.example.com", password="Str0ng-Pma-1!",
        full_name="Pedro García",
    )
    projects[0].pm_id = str(pm.id)
    await db_session.commit()

    r = await client.get("/api/v1/dashboard/plan-vs-actual", headers=auth["_authz"])
    assert r.status_code == 200
    data = r.json()
    with_pm = next(row for row in data if row["folio"] == projects[0].folio)
    assert with_pm["pm_id"] == str(pm.id)
    assert with_pm["pm_name"] == "Pedro García"

    # Proyecto sin PM → pm_id None y pm_name None
    no_pm = next(row for row in data if row["folio"] == projects[1].folio)
    assert no_pm["pm_id"] is None
    assert no_pm["pm_name"] is None
