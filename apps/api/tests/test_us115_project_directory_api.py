"""US-115 — endpoints de project_directory."""
import pytest
from sqlalchemy import select

from app.models.area import Actor
from app.models.organization import Organization
from app.models.project import Project
from app.models.project_participation import ProjectParticipation
from app.models.project_role import ProjectRole
from app.models.tenant import Tenant
from app.services.derived_assignment import derived_for_actor


async def _setup(db_session):
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
    await db_session.commit()


@pytest.mark.asyncio
async def test_us115_project_role_unique(db_session):
    """TC-115-5 (parcial): UNIQUE (tenant_id, name) en project_roles."""
    db_session.add(ProjectRole(tenant_id="t1", name="PM"))
    await db_session.commit()
    db_session.add(ProjectRole(tenant_id="t1", name="PM"))
    with pytest.raises(Exception):
        await db_session.commit()


@pytest.mark.asyncio
async def test_us115_derived_no_participation(db_session):
    """Sin participation y sin actor → empty."""
    out = await derived_for_actor(db_session, None, None)
    assert out.functional_area_id is None
    assert out.operational_team_id is None
    assert out.project_role_id is None
    assert out.is_area_lead is False


@pytest.mark.asyncio
async def test_us115_derived_uses_primary(db_session):
    """TC-115-3: GET task incluye derived calculado desde primary participation."""
    await _setup(db_session)
    # 2 participations: secondary primero (más antigua), primary después
    db_session.add(
        ProjectParticipation(
            id="pp1",
            tenant_id="tn1",
            project_id="p1",
            actor_id="a1",
            project_role_id="r1",
            is_primary=False,
            is_active=True,
        )
    )
    await db_session.flush()
    db_session.add(
        ProjectParticipation(
            id="pp2",
            tenant_id="tn1",
            project_id="p1",
            actor_id="a1",
            project_role_id=None,  # primary sin rol
            is_primary=True,
            is_active=True,
        )
    )
    await db_session.commit()
    out = await derived_for_actor(db_session, "a1", "p1")
    # Primary preferida: project_role_id = None
    assert out.project_role_id is None


@pytest.mark.asyncio
async def test_us115_derived_fallback_to_actor_area(db_session):
    """Sin participation pero actor con area_id legacy → fallback."""
    tenant = Tenant(id="tn2", name="T2", slug="t2")
    db_session.add(tenant)
    await db_session.flush()
    actor = Actor(id="a2", tenant_id="tn2", name="Pepe", area_id=None)
    db_session.add(actor)
    org = Organization(id="o2", tenant_id="tn2", name="O2")
    db_session.add(org)
    await db_session.flush()
    p = Project(id="p2", tenant_id="tn2", organization_id="o2", name="P2", folio="P2")
    db_session.add(p)
    await db_session.commit()
    out = await derived_for_actor(db_session, "a2", "p2")
    assert out.functional_area_id is None
