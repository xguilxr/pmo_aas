"""US-118 Fase 1 — doble escritura project_members → project_participations."""
import pytest
from sqlalchemy import select

from app.models.area import Actor
from app.models.organization import Organization
from app.models.project import Project
from app.models.project_participation import ProjectParticipation
from app.models.project_role import ProjectRole
from app.models.tenant import Tenant
from app.models.user import User
from app.services.project_membership_sync import (
    sync_member_removal,
    sync_member_to_participation,
)


async def _setup(db_session):
    db_session.add(Tenant(id="tn1", name="T", slug="tn1"))
    await db_session.flush()
    db_session.add(Organization(id="o1", tenant_id="tn1", name="O"))
    await db_session.flush()
    db_session.add(
        Project(
            id="p1",
            tenant_id="tn1",
            organization_id="o1",
            name="P",
            folio="P-1",
        )
    )
    db_session.add(
        User(
            id="u1",
            tenant_id="tn1",
            email="ana@test",
            username="ana",
            full_name="Ana",
            password_hash="x",
            is_active=True,
        )
    )
    db_session.add(ProjectRole(id="rpm", tenant_id="tn1", name="PM"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_us118_creates_actor_and_participation(db_session):
    """Sync crea Actor para el user si no existe + participation con rol resuelto."""
    await _setup(db_session)
    part = await sync_member_to_participation(db_session, "tn1", "p1", "u1", "pm")
    await db_session.commit()
    assert part is not None
    assert part.project_role_id == "rpm"
    assert part.is_primary is True
    actor = (
        await db_session.execute(select(Actor).where(Actor.user_id == "u1"))
    ).scalar_one()
    assert actor.name == "Ana"


@pytest.mark.asyncio
async def test_us118_idempotent(db_session):
    """Llamar 2 veces no duplica filas; actualiza el rol."""
    await _setup(db_session)
    p1 = await sync_member_to_participation(db_session, "tn1", "p1", "u1", "pm")
    await db_session.commit()
    p2 = await sync_member_to_participation(db_session, "tn1", "p1", "u1", "team")
    await db_session.commit()
    rows = (
        await db_session.execute(select(ProjectParticipation))
    ).scalars().all()
    assert len(rows) == 1
    assert p1.id == p2.id


@pytest.mark.asyncio
async def test_us118_removal_soft_deletes(db_session):
    """sync_member_removal marca participation inactiva sin borrar."""
    await _setup(db_session)
    await sync_member_to_participation(db_session, "tn1", "p1", "u1", "pm")
    await db_session.commit()
    await sync_member_removal(db_session, "p1", "u1")
    await db_session.commit()
    rows = (
        await db_session.execute(select(ProjectParticipation))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].is_active is False
    assert rows[0].is_primary is False
