"""US-151 — MetricSnapshot: cómputo y persistencia a 4 niveles de scope."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.metric_snapshot import MetricSnapshot
from app.models.modules import Risk
from app.models.organization import Organization
from app.models.project import Project
from app.services.analytics.snapshots import (
    compute_snapshot_values,
    snapshot_tenant,
)
from tests.factories import create_program, create_tenant


async def _seed(db_session):
    t = await create_tenant(db_session)
    org = Organization(tenant_id=t.id, name="Org A")
    db_session.add(org)
    await db_session.flush()
    prog = await create_program(
        db_session, tenant_id=t.id, organization_id=org.id, name="Prog A"
    )

    specs = [
        ("preparacion", "green", Decimal("100000"), Decimal("40000"), 10, prog.id),
        ("ejecucion", "yellow", Decimal("200000"), Decimal("100000"), 50, prog.id),
        ("ejecucion", "red", Decimal("500000"), Decimal("0"), 30, None),
        ("cerrado", "green", Decimal("50000"), Decimal("0"), 100, None),
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
            type="transformacion",
        )
        db_session.add(p)
        projects.append(p)
    await db_session.flush()

    # Riesgos sobre P3 (el rojo): 2 abiertos (1 severo), 1 cerrado.
    for folio, status, sev in [
        ("R-1", "open", 15),
        ("R-2", "in_progress", 8),
        ("R-3", "resolved", 20),
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
    # 1 tenant + 1 org + 1 portafolio + 1 programa + 4 proyectos = 8. El
    # portafolio lo sumó US-201: es el «Portafolio General» donde vive el
    # programa del seed (DEC-030).
    assert written == 8

    total = (
        await db_session.execute(
            select(func.count(MetricSnapshot.id)).where(
                MetricSnapshot.tenant_id == str(t.id)
            )
        )
    ).scalar_one()
    assert total == 8

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
    assert total2 == 8


@pytest.mark.asyncio
async def test_bug082_avg_progress_uses_wbs_rollup(db_session):
    """BUG-082: el snapshot toma el avance *efectivo* (rollup WBS del plan),
    no la columna `Project.progress` manual. Un proyecto con avance manual 0
    pero tareas que promedian 75 debe registrar avg_progress=75, no 0."""
    from app.models.task import Task

    t = await create_tenant(db_session)
    org = Organization(tenant_id=t.id, name="Org R")
    db_session.add(org)
    await db_session.flush()
    proj = Project(
        tenant_id=t.id,
        organization_id=org.id,
        folio="PRJ-2026-900",
        name="Plan-driven",
        phase="ejecucion",
        health_status="green",
        progress=0,  # avance manual stale; el real viene del plan
        type="transformacion",
    )
    db_session.add(proj)
    await db_session.flush()
    # Dos raíces WBS → avance general = promedio (100 + 50) / 2 = 75.
    for wbs_code, pr in [("1", 100), ("2", 50)]:
        db_session.add(
            Task(
                tenant_id=t.id,
                project_id=proj.id,
                wbs_code=wbs_code,
                name=f"Task {wbs_code}",
                progress=pr,
                status="in_progress",
            )
        )
    await db_session.commit()

    v = await compute_snapshot_values(db_session, str(t.id), "project", str(proj.id))
    assert v["avg_progress"] == pytest.approx(75.0, abs=0.01)
