"""ENH-046 — scheduled reports day-of-week + hour-of-day + one-time.

TC:
- TC-046.1: weekly + day_of_week=2 + hour=14 → próxima ejecución es
  miércoles a las 14:00.
- TC-046.2: daily + hour=9 → mañana 09:00 si ya pasaron las 9 hoy.
- TC-046.3: once + run_at = fecha futura → next_run_at = run_at; tras
  la ejecución, enabled=false.
- TC-046.4: schema rechaza weekly sin day_of_week (422).
- TC-046.5: schema rechaza once sin run_at (422).
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.models.scheduled_report import ScheduledReport
from app.services.scheduled_reports import compute_next_run
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="enh046"):
    t = await create_tenant(db_session, slug=slug, name=slug.title())
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


async def _seed_project(db_session, tenant):
    me = await create_user(
        db_session,
        tenant=tenant,
        username=f"pm_{tenant.slug}",
        email=f"pm@{tenant.slug}.example.com",
        password="Str0ng-User-1!",
    )
    from app.models.project import Project

    p = Project(
        tenant_id=str(tenant.id),
        organization_id=None,
        program_id=None,
        folio="P-046",
        name="P046",
        description="t",
        type="operation",
        priority=3,
        phase="execution",
        pm_id=me.id,
    )
    # organization_id NOT NULL FK → seed un org rápida.
    from app.models.organization import Organization

    org = Organization(tenant_id=str(tenant.id), name=f"Org-{tenant.slug}")
    db_session.add(org)
    await db_session.flush()
    p.organization_id = org.id
    db_session.add(p)
    await db_session.commit()
    return p


# -----------------------------------------------------------------------------
# Pure unit tests del compute_next_run con los nuevos params.
# -----------------------------------------------------------------------------


def test_enh046_weekly_with_dow_and_hour():
    # base = lunes 12:00.
    base = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)  # weekday() = 0
    # próximo miércoles 14:00 = 2 días después.
    nxt = compute_next_run("weekly", from_dt=base, day_of_week=2, hour_of_day=14)
    assert nxt == datetime(2026, 4, 29, 14, 0, tzinfo=UTC)


def test_enh046_weekly_same_day_already_past_hour():
    # base = miércoles 14:30; queremos miércoles 09:00 → es la próxima semana.
    base = datetime(2026, 4, 29, 14, 30, tzinfo=UTC)  # weekday() = 2
    nxt = compute_next_run("weekly", from_dt=base, day_of_week=2, hour_of_day=9)
    # candidate sería miércoles 09:00 que ya pasó → +7 días.
    assert nxt == datetime(2026, 5, 6, 9, 0, tzinfo=UTC)


def test_enh046_daily_hour_today_or_tomorrow():
    # base = 08:00 → siguiente 09:00 hoy.
    base = datetime(2026, 4, 27, 8, 0, tzinfo=UTC)
    nxt = compute_next_run("daily", from_dt=base, hour_of_day=9)
    assert nxt == datetime(2026, 4, 27, 9, 0, tzinfo=UTC)
    # base = 10:00 → siguiente 09:00 mañana.
    base = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
    nxt = compute_next_run("daily", from_dt=base, hour_of_day=9)
    assert nxt == datetime(2026, 4, 28, 9, 0, tzinfo=UTC)


def test_enh046_once_returns_run_at():
    target = datetime(2026, 6, 15, 18, 0, tzinfo=UTC)
    nxt = compute_next_run("once", run_at=target)
    assert nxt == target


def test_enh046_once_without_run_at_raises():
    with pytest.raises(ValueError):
        compute_next_run("once")


# -----------------------------------------------------------------------------
# E2E API tests.
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enh046_create_weekly_requires_dow_and_hour(client, db_session):
    t, auth = await _admin(client, db_session, slug="enh046a")
    p = await _seed_project(db_session, t)

    # Sin day_of_week + hour → 422.
    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "avance",
            "cadence": "weekly",
            "recipients": ["a@x.com"],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422

    # Con ambos → 201.
    r2 = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "avance",
            "cadence": "weekly",
            "day_of_week": 2,
            "hour_of_day": 14,
            "recipients": ["a@x.com"],
        },
        headers=auth["_authz"],
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["day_of_week"] == 2
    assert r2.json()["hour_of_day"] == 14


@pytest.mark.asyncio
async def test_enh046_once_requires_run_at(client, db_session):
    t, auth = await _admin(client, db_session, slug="enh046b")
    p = await _seed_project(db_session, t)

    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "avance",
            "cadence": "once",
            "recipients": ["a@x.com"],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422

    target = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0).isoformat()
    r2 = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "avance",
            "cadence": "once",
            "run_at": target,
            "recipients": ["a@x.com"],
        },
        headers=auth["_authz"],
    )
    assert r2.status_code == 201, r2.text
    body = r2.json()
    assert body["cadence"] == "once"
    assert body["run_at"] is not None
    assert body["next_run_at"] is not None


@pytest.mark.asyncio
async def test_enh046_once_disables_after_run(client, db_session):
    """Tras la ejecución, una programación `once` queda enabled=False."""
    from app.workers.tasks import scheduled_reports as task_mod

    t, _auth = await _admin(client, db_session, slug="enh046c")
    p = await _seed_project(db_session, t)

    sched = ScheduledReport(
        tenant_id=str(t.id),
        project_id=str(p.id),
        report_type="avance",
        cadence="once",
        recipients=["once@example.com"],
        enabled=True,
        run_at=datetime.now(UTC) - timedelta(seconds=30),
        next_run_at=datetime.now(UTC) - timedelta(seconds=30),
    )
    db_session.add(sched)
    await db_session.commit()

    fake_resend = AsyncMock(return_value={"id": "x"})
    with patch.object(task_mod, "send_email_via_resend", fake_resend):
        result = await task_mod._send(str(sched.id))
    assert result["sent"] is True

    await db_session.refresh(sched)
    assert sched.enabled is False
    assert sched.next_run_at is None
