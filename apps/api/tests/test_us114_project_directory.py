"""US-114 — smoke tests del schema de directorio de proyecto."""
import pytest
from sqlalchemy import select

from app.models.area import Actor, Area
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
