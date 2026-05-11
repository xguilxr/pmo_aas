"""US-117 — eligible-actors filter + lessons.owner_actor_id."""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.area import Actor
from app.models.modules import Lesson
from app.models.organization import Organization
from app.models.project import Project
from app.models.project_participation import ProjectParticipation
from app.models.tenant import Tenant


async def _setup_min(db_session):
    db_session.add(Tenant(id="tn1", name="T1", slug="tn1"))
    await db_session.flush()
    db_session.add(Organization(id="o1", tenant_id="tn1", name="O1"))
    await db_session.flush()
    db_session.add(
        Project(
            id="p1",
            tenant_id="tn1",
            organization_id="o1",
            name="Px",
            folio="P-1",
        )
    )
    db_session.add(Actor(id="a1", tenant_id="tn1", name="Ana", is_active=True))
    db_session.add(Actor(id="a2", tenant_id="tn1", name="Bea", is_active=True))
    db_session.add(Actor(id="a3", tenant_id="tn1", name="Cele", is_active=True))
    await db_session.commit()


@pytest.mark.asyncio
async def test_us117_lesson_owner_actor_id(db_session):
    """Lesson.owner_actor_id se persiste."""
    await _setup_min(db_session)
    lesson = Lesson(
        tenant_id="tn1",
        project_id="p1",
        folio="L-1",
        title="Test lesson",
        status="open",
        category="success",
        owner_actor_id="a1",
    )
    db_session.add(lesson)
    await db_session.commit()
    fetched = (
        await db_session.execute(select(Lesson).where(Lesson.title == "Test lesson"))
    ).scalar_one()
    assert fetched.owner_actor_id == "a1"


@pytest.mark.asyncio
async def test_us117_eligible_filters_by_window(db_session):
    """Actor con participation expirada NO es eligible."""
    await _setup_min(db_session)
    today = date.today()
    # a1: activa sin ventana → eligible
    db_session.add(
        ProjectParticipation(
            tenant_id="tn1",
            project_id="p1",
            actor_id="a1",
            is_primary=True,
            is_active=True,
        )
    )
    # a2: ventana ya cerrada → NO eligible
    db_session.add(
        ProjectParticipation(
            tenant_id="tn1",
            project_id="p1",
            actor_id="a2",
            is_primary=True,
            is_active=True,
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=1),
        )
    )
    # a3: is_active=False → NO eligible
    db_session.add(
        ProjectParticipation(
            tenant_id="tn1",
            project_id="p1",
            actor_id="a3",
            is_primary=True,
            is_active=False,
        )
    )
    await db_session.commit()

    # Simular el filtro del endpoint a nivel de query.
    rows = (
        await db_session.execute(
            select(ProjectParticipation, Actor)
            .join(Actor, Actor.id == ProjectParticipation.actor_id)
            .where(
                ProjectParticipation.project_id == "p1",
                ProjectParticipation.is_active.is_(True),
            )
        )
    ).all()
    eligible = []
    for part, actor in rows:
        if part.start_date and part.start_date > today:
            continue
        if part.end_date and part.end_date < today:
            continue
        eligible.append(actor.id)
    assert "a1" in eligible
    assert "a2" not in eligible
    assert "a3" not in eligible
