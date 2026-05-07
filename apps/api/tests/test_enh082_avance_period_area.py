"""ENH-082 — Reporte Avance: cota de período en hitos próximos + área."""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.area import Area
from app.models.modules import Issue, Risk
from app.models.organization import Organization
from app.models.project import Project
from app.models.task import Task
from app.services.operational_reports import build_avance_context
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _seed(db_session):
    t = await create_tenant(db_session, slug="enh082", name="enh082")
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin_enh082",
        email="admin@enh082.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    org = Organization(tenant_id=t.id, name="Org082", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(t.id), organization_id=str(org.id),
        folio="P-082", name="Proyecto 082",
        budget=Decimal("0"), actual_budget=Decimal("0"), progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    a = Area(tenant_id=str(t.id), name="Operaciones")
    db_session.add(a)
    await db_session.flush()
    return t, p, a


@pytest.mark.asyncio
async def test_tc082_1_milestone_outside_window_is_excluded(client, db_session):
    """Hito con end_date > cut + window_days no debe aparecer en upcoming."""
    t, p, a = await _seed(db_session)
    cut = date(2026, 5, 1)
    # Dentro: cut + 10
    db_session.add(Task(
        tenant_id=str(t.id), project_id=str(p.id), name="Hito dentro",
        is_milestone=True, status="not_started", progress=0,
        end_date=cut + timedelta(days=10), area_id=str(a.id),
    ))
    # Fuera: cut + 90 (más allá del window=30)
    db_session.add(Task(
        tenant_id=str(t.id), project_id=str(p.id), name="Hito fuera",
        is_milestone=True, status="not_started", progress=0,
        end_date=cut + timedelta(days=90), area_id=str(a.id),
    ))
    await db_session.commit()

    ctx = await build_avance_context(
        db_session, t.id, p.id, cut, window_days=30
    )
    names = [m["name"] for m in ctx["milestones_upcoming"]]
    assert "Hito dentro" in names
    assert "Hito fuera" not in names


@pytest.mark.asyncio
async def test_tc082_2_milestone_includes_area_and_delayed(client, db_session):
    t, p, a = await _seed(db_session)
    cut = date(2026, 5, 1)
    # Tarea con end_date < cut, no milestone, baseline para delayed.
    db_session.add(Task(
        tenant_id=str(t.id), project_id=str(p.id), name="Hito alfa",
        is_milestone=True, status="not_started", progress=10,
        end_date=cut + timedelta(days=5), area_id=str(a.id),
    ))
    await db_session.commit()
    ctx = await build_avance_context(
        db_session, t.id, p.id, cut, window_days=30
    )
    m = next(m for m in ctx["milestones_upcoming"] if m["name"] == "Hito alfa")
    assert m["area_name"] == "Operaciones"
    assert m["status"] == "not_started"
    assert "delayed" in m


@pytest.mark.asyncio
async def test_tc082_3_risk_includes_area_and_due_date(client, db_session):
    t, p, a = await _seed(db_session)
    cut = date(2026, 5, 1)
    db_session.add(Risk(
        tenant_id=str(t.id), project_id=p.id, folio="RIS-082",
        title="Riesgo área", status="identified", severity=15,
        probability=3, impact=5,
        area_id=str(a.id), due_date=cut + timedelta(days=20),
    ))
    await db_session.commit()
    ctx = await build_avance_context(
        db_session, t.id, p.id, cut, window_days=30
    )
    r = next(r for r in ctx["top_risks"] if r["folio"] == "RIS-082")
    assert r["area_name"] == "Operaciones"
    assert r["due_date"] == (cut + timedelta(days=20)).isoformat()


@pytest.mark.asyncio
async def test_tc082_4_issue_falls_back_to_area_when_no_owner(client, db_session):
    t, p, a = await _seed(db_session)
    cut = date(2026, 5, 1)
    db_session.add(Issue(
        tenant_id=str(t.id), project_id=p.id, folio="ISS-082",
        title="Incidencia área", type="action", status="open", priority=2,
        area_id=str(a.id), committed_date=cut + timedelta(days=3),
        reported_at=datetime.now(UTC),
    ))
    await db_session.commit()
    ctx = await build_avance_context(
        db_session, t.id, p.id, cut, window_days=30
    )
    i = next(i for i in ctx["open_aids"] if i["folio"] == "ISS-082")
    assert i["owner_name"] == "—"  # sin owner
    assert i["area_name"] == "Operaciones"
