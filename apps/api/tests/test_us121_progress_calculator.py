"""US-121 — Progress calculator service (3 modes)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.models.organization import Organization
from app.models.project import Project
from app.models.task import Task
from app.services.progress_calculator import (
    FALLBACK_HOURS_UNAVAILABLE,
    compute_progress,
    compute_progress_detailed,
)
from app.services.tenant_settings import set_progress_calculation_method
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="us121"):
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


async def _make_project(db_session, tenant, folio="P-US121"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id),
        organization_id=str(org.id),
        folio=folio,
        name=f"Proyecto {folio}",
        description="",
        phase="execution",
        health_status="green",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    return p


async def _seed_tasks(db_session, tenant, project):
    """4 tasks: 2 done, 2 in progress. Durations chosen so by_duration ≠ 50.

    Done tasks: durations 4 + 6 = 10.
    In-progress tasks: durations 20 + 10 = 30.
    Total = 40 → by_duration = 10/40 = 25%.
    """
    specs = [
        ("T1-done", "completed", 4),
        ("T2-done", "completed", 6),
        ("T3-wip", "in_progress", 20),
        ("T4-wip", "in_progress", 10),
    ]
    for name, status, duration in specs:
        db_session.add(
            Task(
                tenant_id=str(tenant.id),
                project_id=project.id,
                name=name,
                status=status,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                duration_days=duration,
            )
        )
    await db_session.flush()


@pytest.mark.asyncio
async def test_by_task_count_returns_50(db_session):
    t = await create_tenant(db_session, slug="us121-count", name="us121-count")
    p = await _make_project(db_session, t, folio="P-CNT")
    await _seed_tasks(db_session, t, p)

    value = await compute_progress(db_session, p.id, method="by_task_count")
    assert value == 50.0


@pytest.mark.asyncio
async def test_by_duration_uses_weighted_pct(db_session):
    t = await create_tenant(db_session, slug="us121-dur", name="us121-dur")
    p = await _make_project(db_session, t, folio="P-DUR")
    await _seed_tasks(db_session, t, p)

    result = await compute_progress_detailed(
        db_session, p.id, method="by_duration"
    )
    # 10 / 40 = 25.0, and clearly ≠ 50.
    assert result.value == 25.0
    assert result.method == "by_duration"
    assert result.fallback is None


@pytest.mark.asyncio
async def test_by_effort_falls_back_to_count(db_session):
    t = await create_tenant(db_session, slug="us121-eff", name="us121-eff")
    p = await _make_project(db_session, t, folio="P-EFF")
    await _seed_tasks(db_session, t, p)

    result = await compute_progress_detailed(
        db_session, p.id, method="by_effort"
    )
    assert result.value == 50.0
    assert result.method == "by_effort"
    assert result.fallback == FALLBACK_HOURS_UNAVAILABLE


@pytest.mark.asyncio
async def test_resolves_tenant_default_when_method_none(db_session):
    t = await create_tenant(db_session, slug="us121-def", name="us121-def")
    set_progress_calculation_method(t, "by_duration")
    await db_session.flush()
    p = await _make_project(db_session, t, folio="P-DEF")
    await _seed_tasks(db_session, t, p)

    result = await compute_progress_detailed(db_session, p.id)
    assert result.method == "by_duration"
    assert result.value == 25.0


@pytest.mark.asyncio
async def test_empty_project_returns_zero(db_session):
    t = await create_tenant(db_session, slug="us121-empty", name="us121-empty")
    p = await _make_project(db_session, t, folio="P-EMP")

    value = await compute_progress(db_session, p.id, method="by_task_count")
    assert value == 0.0


@pytest.mark.asyncio
async def test_endpoint_returns_expected_shape(client, db_session):
    t, auth = await _admin(client, db_session, slug="us121api")
    p = await _make_project(db_session, t, folio="P-API")
    await _seed_tasks(db_session, t, p)
    await db_session.commit()

    # Default method (tenant unset → by_task_count).
    r = await client.get(
        f"/api/v1/projects/{p.id}/progress", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["value"] == 50.0
    assert body["method"] == "by_task_count"
    assert "fallback" not in body

    # Override method=by_effort → fallback flag present.
    r2 = await client.get(
        f"/api/v1/projects/{p.id}/progress?method=by_effort",
        headers=auth["_authz"],
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["method"] == "by_effort"
    assert body2["fallback"] == FALLBACK_HOURS_UNAVAILABLE
    assert body2["value"] == 50.0

    # Override method=by_duration → 25%.
    r3 = await client.get(
        f"/api/v1/projects/{p.id}/progress?method=by_duration",
        headers=auth["_authz"],
    )
    assert r3.status_code == 200, r3.text
    assert r3.json()["value"] == 25.0
