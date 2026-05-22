"""ENH-103 — Match participantes de minuta ↔ actores del proyecto.

Reglas:
- Match fuzzy case-insensitive contra actors ligados al proyecto vía
  project_participations.
- Match → actor_id + match_status="matched" + verified.
- Sin match → crea Actor (auto_created=True, verified=False) +
  ProjectParticipation guest. match_status="auto_created".
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.area import Actor
from app.models.modules import MeetingMinute
from app.models.organization import Organization
from app.models.project import Project
from app.models.project_participation import ProjectParticipation
from app.services.minutes.participant_matcher import match_participants
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


async def _seed_project(db_session, tenant, *, folio="P-1000"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id),
        organization_id=str(org.id),
        folio=folio,
        name=f"Proyecto {folio}",
        description="ENH-103",
        phase="execution",
        health_status="green",
        budget=Decimal("100"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    await db_session.commit()
    return p


async def _seed_actor(db_session, tenant, project, *, name, verified=True):
    actor = Actor(
        tenant_id=str(tenant.id),
        name=name,
        is_active=True,
        is_lead=False,
        auto_created=False,
        verified=verified,
    )
    db_session.add(actor)
    await db_session.flush()
    part = ProjectParticipation(
        tenant_id=str(tenant.id),
        project_id=str(project.id),
        actor_id=str(actor.id),
        is_primary=False,
        is_active=True,
        is_area_lead=False,
    )
    db_session.add(part)
    await db_session.flush()
    await db_session.commit()
    return actor


@pytest.mark.asyncio
async def test_match_links_existing_actor_case_insensitive(client, db_session):
    """Participante "ana garcía" matchea con actor "Ana García"
    (fuzzy + case-insensitive)."""
    tenant, _ = await _admin(client, db_session, slug="enh103-a")
    project = await _seed_project(db_session, tenant, folio="P-1001")
    ana = await _seed_actor(db_session, tenant, project, name="Ana García")

    out = await match_participants(
        db_session,
        project_id=project.id,
        tenant_id=tenant.id,
        participants=[{"name": "ana garcía", "role": "PM"}],
    )
    assert len(out) == 1
    assert out[0]["actor_id"] == str(ana.id)
    assert out[0]["match_status"] == "matched"
    assert out[0]["verified"] is True
    # Campos originales preservados
    assert out[0]["role"] == "PM"


@pytest.mark.asyncio
async def test_unmatched_creates_auto_actor_and_participation(client, db_session):
    """Sin match → crea Actor (auto_created=True, verified=False) +
    ProjectParticipation guest."""
    tenant, _ = await _admin(client, db_session, slug="enh103-b")
    project = await _seed_project(db_session, tenant, folio="P-1002")
    # Sin actores previos en el proyecto.

    out = await match_participants(
        db_session,
        project_id=project.id,
        tenant_id=tenant.id,
        participants=[{"name": "Juan Pérez", "role": "Stakeholder"}],
    )
    assert len(out) == 1
    assert out[0]["match_status"] == "auto_created"
    assert out[0]["verified"] is False
    new_actor_id = out[0]["actor_id"]
    assert new_actor_id

    # Actor creado con flags correctos
    actor = (
        await db_session.execute(select(Actor).where(Actor.id == new_actor_id))
    ).scalar_one()
    assert actor.auto_created is True
    assert actor.verified is False
    assert actor.name == "Juan Pérez"

    # ProjectParticipation creado
    parts = (
        await db_session.execute(
            select(ProjectParticipation).where(
                ProjectParticipation.actor_id == new_actor_id,
                ProjectParticipation.project_id == project.id,
            )
        )
    ).scalars().all()
    assert len(parts) == 1


@pytest.mark.asyncio
async def test_duplicate_participants_dedup_within_same_call(client, db_session):
    """Dos participantes idénticos en la misma minuta NO crean dos
    actores duplicados: el segundo matchea con el primero recién creado.
    """
    tenant, _ = await _admin(client, db_session, slug="enh103-c")
    project = await _seed_project(db_session, tenant, folio="P-1003")

    out = await match_participants(
        db_session,
        project_id=project.id,
        tenant_id=tenant.id,
        participants=[
            {"name": "María López"},
            {"name": "maria lopez"},
        ],
    )
    assert len(out) == 2
    # Primero auto_created, segundo matchea con el primero
    assert out[0]["match_status"] == "auto_created"
    assert out[1]["match_status"] == "matched"
    assert out[0]["actor_id"] == out[1]["actor_id"]


@pytest.mark.asyncio
async def test_create_minute_enriches_participants_e2e(client, db_session):
    """E2E: POST /meeting-minutes con 3 participantes (1 existe, 2
    nuevos) → MeetingMinute.participants queda enriquecido con match
    info; los 2 nuevos generan actors auto_created.
    """
    tenant, auth = await _admin(client, db_session, slug="enh103-d")
    project = await _seed_project(db_session, tenant, folio="P-1004")
    ana = await _seed_actor(db_session, tenant, project, name="Ana García")

    r = await client.post(
        f"/api/v1/projects/{project.id}/meeting-minutes",
        json={
            "title": "Reunión kickoff",
            "meeting_date": datetime.now(UTC).isoformat(),
            "participants": [
                {"name": "Ana García"},
                {"name": "Carlos Ruiz"},
                {"name": "Pedro Soto"},
            ],
            "topics": [],
            "agreements": [],
            "raid_suggestions": {},
            "auto_approve_raid": False,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    minute_id = r.json()["id"]

    m = (
        await db_session.execute(select(MeetingMinute).where(MeetingMinute.id == minute_id))
    ).scalar_one()
    ps = list(m.participants or [])
    assert len(ps) == 3
    ana_p = next(p for p in ps if p["name"] == "Ana García")
    assert ana_p["actor_id"] == str(ana.id)
    assert ana_p["match_status"] == "matched"
    new_ps = [p for p in ps if p["match_status"] == "auto_created"]
    assert len(new_ps) == 2
    assert all(p["verified"] is False for p in new_ps)
