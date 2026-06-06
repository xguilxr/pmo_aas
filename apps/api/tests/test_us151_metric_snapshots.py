"""US-151 — MetricSnapshot: cómputo y persistencia a 4 niveles de scope."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.metric_snapshot import MetricSnapshot
from app.models.modules import Risk
from app.models.organization import Organization, Program
from app.models.project import Project
from app.services.analytics.snapshots import (
    compute_snapshot_values,
    snapshot_tenant,
)
from tests.factories import create_tenant


async def _seed(db_session):
    t = await create_tenant(db_session)
    org = Organization(tenant_id=t.id, name="Org A")
    db_session.add(org)
    await db_session.flush()
    prog = Program(tenant_id=t.id, organization_id=org.id, name="Prog A")
    db_session.add(prog)
    await db_session.flush()

    specs = [
        ("planning", "green", Decimal("100000"), Decimal("40000"), 10, prog.id),
        ("execution", "yellow", Decimal("200000"), Decimal("100000"), 50, prog.id),
        ("execution", "red", Decimal("500000"), Decimal("0"), 30, None),
        ("closed", "green", Decimal("50000"), Decimal("0"), 100, None),
    ]
    projects = []
    for i, (phase, health, budget, actual, prog_, program_id) in enumerate(specs):
        p = Project(
            tenant_id=t.id,
            organization_id=org.id,
            program_id=program_id,
            folio=f"PRJ-2026-{i + 1:03d}",
            name=f"P{i + 1}",
            phase=phase,
            health_status=health,
            budget=budget,
            actual_budget=actual,
            progress=prog_,
            type="transformation",
        )
        db_session.add(p)
        projects.append(p)
    await db_session.flush()

    # Riesgos sobre P3 (el rojo): 2 abiertos (1 severo), 1 cerrado.
    for folio, status, sev in [
        ("R-1", "identified", 15),
        ("R-2", "mitigating", 8),
        ("R-3", "closed", 20),
    ]:
        db_session.add(
            Risk(
                tenant_id=t.id,
                project_id=projects[2].id,
                folio=folio,
                title=folio,
                status=status,
                probability=5,
                impact=3,
                severity=sev,
            )
        )
    await db_session.commit()
    return t, org, prog, projects


@pytest.mark.asyncio
async def test_compute_tenant_scope(db_session):
    t, org, prog, _ = await _seed(db_session)
    v = await compute_snapshot_values(db_session, str(t.id), "tenant", str(t.id))

    assert v["projects_total"] == 4
    assert v["projects_active"] == 3
    assert (v["health_green"], v["health_yellow"], v["health_red"]) == (2, 1, 1)
    assert v["avg_progress"] == pytest.approx((10 + 50 + 30) / 3, abs=0.01)
    assert v["budget_plan"] == 850000.0
    assert v["budget_actual"] == 140000.0
    assert v["open_risks"] == 2
    assert v["severe_risks"] == 1


@pytest.mark.asyncio
async def test_compute_program_and_project_scope(db_session):
    t, org, prog, projects = await _seed(db_session)

    vp = await compute_snapshot_values(db_session, str(t.id), "program", str(prog.id))
    assert vp["projects_total"] == 2  # solo P1 + P2
    assert vp["budget_plan"] == 300000.0
    assert vp["health_red"] == 0

    vj = await compute_snapshot_values(
        db_session, str(t.id), "project", str(projects[2].id)
    )
    assert vj["projects_total"] == 1
    assert vj["health_red"] == 1
    assert vj["open_risks"] == 2
    assert vj["severe_risks"] == 1


@pytest.mark.asyncio
async def test_snapshot_tenant_writes_all_levels_idempotent(db_session):
    t, org, prog, projects = await _seed(db_session)
    today = date.today()

    written = await snapshot_tenant(db_session, str(t.id), today)
    # 1 tenant + 1 org + 1 programa + 4 proyectos = 7
    assert written == 7

    total = (
        await db_session.execute(
            select(func.count(MetricSnapshot.id)).where(
                MetricSnapshot.tenant_id == str(t.id)
            )
        )
    ).scalar_one()
    assert total == 7

    tenant_snap = (
        await db_session.execute(
            select(MetricSnapshot).where(
                MetricSnapshot.tenant_id == str(t.id),
                MetricSnapshot.scope_type == "tenant",
                MetricSnapshot.snapshot_date == today,
            )
        )
    ).scalar_one()
    assert tenant_snap.projects_total == 4
    assert tenant_snap.severe_risks == 1

    # Idempotencia: segunda corrida no duplica filas.
    await snapshot_tenant(db_session, str(t.id), today)
    total2 = (
        await db_session.execute(
            select(func.count(MetricSnapshot.id)).where(
                MetricSnapshot.tenant_id == str(t.id)
            )
        )
    ).scalar_one()
    assert total2 == 7
