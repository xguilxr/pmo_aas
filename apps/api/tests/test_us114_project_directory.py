"""US-114 — smoke tests del schema de directorio de proyecto."""
import pytest
from sqlalchemy import select

from app.models.area import Actor
from app.models.project_participation import ProjectParticipation
from app.models.project_role import ProjectRole


@pytest.mark.asyncio
async def test_us114_project_role_table_exists(db_session):
    """TC-114-1 (parcial): tabla project_roles persiste filas con UNIQUE."""
    role = ProjectRole(tenant_id="t1", name="PM", description="Project Manager")
    db_session.add(role)
    await db_session.commit()
    rows = (await db_session.execute(select(ProjectRole))).scalars().all()
    assert len(rows) == 1
    assert rows[0].name == "PM"


@pytest.mark.asyncio
async def test_us114_actor_new_fields(db_session):
    """Actores aceptan company / job_title / manager_actor_id."""
    boss = Actor(tenant_id="t1", name="Jefa", is_active=True)
    db_session.add(boss)
    await db_session.flush()
    sub = Actor(
        tenant_id="t1",
        name="Empleada",
        company="ACME",
        job_title="Analista",
        manager_actor_id=boss.id,
        is_active=True,
    )
    db_session.add(sub)
    await db_session.commit()
    fetched = (
        await db_session.execute(select(Actor).where(Actor.name == "Empleada"))
    ).scalar_one()
    assert fetched.company == "ACME"
    assert fetched.job_title == "Analista"
    assert fetched.manager_actor_id == boss.id


@pytest.mark.asyncio
async def test_us114_participation_basic(db_session):
    """TC-114-2: una participation se crea y vincula proyecto+actor+rol."""
    from app.models.organization import Organization
    from app.models.project import Project
    from app.models.tenant import Tenant

    # Setup mínimo
    tenant = Tenant(id="tn1", name="Tenant 1", slug="tn1")
    db_session.add(tenant)
    await db_session.flush()
    org = Organization(id="o1", tenant_id="tn1", name="Org 1")
    db_session.add(org)
    await db_session.flush()
    project = Project(
        id="p1",
        tenant_id="tn1",
        organization_id="o1",
        name="Proyecto X",
        folio="PX-1",
    )
    db_session.add(project)
    actor = Actor(id="a1", tenant_id="tn1", name="María")
    db_session.add(actor)
    role = ProjectRole(id="r1", tenant_id="tn1", name="PM")
    db_session.add(role)
    await db_session.flush()

    part = ProjectParticipation(
        tenant_id="tn1",
        project_id="p1",
        actor_id="a1",
        project_role_id="r1",
        is_primary=True,
        is_active=True,
    )
    db_session.add(part)
    await db_session.commit()

    rows = (await db_session.execute(select(ProjectParticipation))).scalars().all()
    assert len(rows) == 1
    assert rows[0].is_primary is True
    assert rows[0].project_role_id == "r1"


# BUG-072: el endpoint POST /api/v1/actors ignoraba company / job_title /
# manager_actor_id al construir el modelo, aunque ActorCreate los aceptaba.
# El frontend pedía Empresa al crear persona y luego no se reflejaba.
@pytest.mark.asyncio
async def test_bug072_create_actor_persists_us114_fields(client, db_session):
    from tests.factories import create_admin_role, create_tenant, create_user, login

    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin072",
        email="admin072@acme.example.com", password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin072", "Str0ng-Admin-1!")

    r = await client.post(
        "/api/v1/actors",
        json={
            "name": "Laura Pérez",
            "email": "laura@acme.example.com",
            "company": "ACME Corp",
            "job_title": "Project Manager",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["company"] == "ACME Corp"
    assert body["job_title"] == "Project Manager"

    # Verifica que persiste round-trip vía GET.
    r2 = await client.get(
        f"/api/v1/actors/{body['id']}", headers=auth["_authz"]
    )
    assert r2.status_code == 200
    assert r2.json()["company"] == "ACME Corp"
    assert r2.json()["job_title"] == "Project Manager"


@pytest.mark.asyncio
async def test_bug072_revive_actor_updates_us114_fields(client, db_session):
    """Si un actor está soft-deleted y se re-POSTea con email igual, el
    branch de revive también debe actualizar company / job_title."""
    from tests.factories import create_admin_role, create_tenant, create_user, login

    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin072b",
        email="admin072b@acme.example.com", password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin072b", "Str0ng-Admin-1!")

    # 1) crea con company X
    r = await client.post(
        "/api/v1/actors",
        json={
            "name": "Rocío Vega",
            "email": "rocio@acme.example.com",
            "company": "Old Co",
        },
        headers=auth["_authz"],
    )
    actor_id = r.json()["id"]

    # 2) soft-delete
    r = await client.delete(
        f"/api/v1/actors/{actor_id}", headers=auth["_authz"]
    )
    assert r.status_code in (200, 204)

    # 3) re-create con mismo email + company nueva → debe revivir
    # actualizando los datos.
    r = await client.post(
        "/api/v1/actors",
        json={
            "name": "Rocío Vega",
            "email": "rocio@acme.example.com",
            "company": "New Co",
            "job_title": "Director",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] == actor_id  # mismo registro reactivado
    assert body["company"] == "New Co"
    assert body["job_title"] == "Director"
