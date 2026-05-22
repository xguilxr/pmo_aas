"""ENH-107 — Scheduled minutes (símil US-056 scheduled reports)."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.models.modules import MeetingMinute
from app.models.organization import Organization
from app.models.project import Project
from app.models.scheduled_minute import ScheduledMinute
from app.services.scheduled_minutes import (
    select_latest_minute,
    should_send_now,
)
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="sm-a"):
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


async def _seed_project(db_session, tenant, *, folio="P-0700"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id),
        organization_id=str(org.id),
        folio=folio,
        name=f"Proyecto {folio}",
        description="Proyecto para ENH-107",
        phase="execution",
        health_status="green",
        budget=Decimal("1000"),
        actual_budget=Decimal("400"),
        progress=40,
    )
    db_session.add(p)
    await db_session.flush()
    await db_session.commit()
    return p


def _make_minute(tenant_id: str, project_id: str, *, when: datetime, folio: str) -> MeetingMinute:
    return MeetingMinute(
        tenant_id=tenant_id,
        project_id=project_id,
        folio=folio,
        title=f"Minuta {folio}",
        status="open",
        meeting_date=when,
        participants=[{"name": "Ana", "role": "PM"}],
        topics=[{"title": "Avance semanal", "notes": "OK"}],
        agreements=[],
        attachments=[],
        raid_suggestions={},
    )


def test_should_send_now_respects_enabled_and_due():
    now = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)
    sched = ScheduledMinute(
        tenant_id="t", project_id="p", cadence="daily",
        recipients=["a@x.com"], enabled=True,
        next_run_at=now - timedelta(minutes=1),
    )
    assert should_send_now(sched, now) is True
    sched.enabled = False
    assert should_send_now(sched, now) is False
    sched.enabled = True
    sched.next_run_at = None
    assert should_send_now(sched, now) is False
    sched.next_run_at = now + timedelta(minutes=5)
    assert should_send_now(sched, now) is False


@pytest.mark.asyncio
async def test_enh107_create_scheduled_minute(client, db_session):
    t, auth = await _admin(client, db_session, slug="sm-create")
    p = await _seed_project(db_session, t, folio="P-0701")

    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-minutes",
        json={
            "cadence": "weekly",
            "day_of_week": 0,
            "hour_of_day": 9,
            "recipients": ["pm@example.com", "sponsor@example.com"],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["cadence"] == "weekly"
    assert body["enabled"] is True
    assert body["next_run_at"] is not None
    assert len(body["recipients"]) == 2


@pytest.mark.asyncio
async def test_enh107_list_scheduled_minutes(client, db_session):
    t, auth = await _admin(client, db_session, slug="sm-list")
    p = await _seed_project(db_session, t, folio="P-0702")

    await client.post(
        f"/api/v1/projects/{p.id}/scheduled-minutes",
        json={
            "cadence": "daily",
            "hour_of_day": 9,
            "recipients": ["a@x.com"],
        },
        headers=auth["_authz"],
    )

    lst = await client.get(
        f"/api/v1/projects/{p.id}/scheduled-minutes", headers=auth["_authz"]
    )
    assert lst.status_code == 200
    assert len(lst.json()) == 1
    assert lst.json()[0]["cadence"] == "daily"


@pytest.mark.asyncio
async def test_enh107_patch_toggles_next_run(client, db_session):
    t, auth = await _admin(client, db_session, slug="sm-patch")
    p = await _seed_project(db_session, t, folio="P-0703")

    created = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-minutes",
        json={
            "cadence": "daily",
            "hour_of_day": 9,
            "recipients": ["a@x.com"],
        },
        headers=auth["_authz"],
    )
    sid = created.json()["id"]

    paused = await client.patch(
        f"/api/v1/scheduled-minutes/{sid}",
        json={"enabled": False},
        headers=auth["_authz"],
    )
    assert paused.status_code == 200
    assert paused.json()["enabled"] is False
    assert paused.json()["next_run_at"] is None

    resumed = await client.patch(
        f"/api/v1/scheduled-minutes/{sid}",
        json={
            "enabled": True,
            "cadence": "weekly",
            "day_of_week": 1,
            "hour_of_day": 9,
        },
        headers=auth["_authz"],
    )
    assert resumed.status_code == 200
    assert resumed.json()["cadence"] == "weekly"
    assert resumed.json()["next_run_at"] is not None


@pytest.mark.asyncio
async def test_enh107_delete_scheduled_minute(client, db_session):
    t, auth = await _admin(client, db_session, slug="sm-delete")
    p = await _seed_project(db_session, t, folio="P-0704")

    created = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-minutes",
        json={
            "cadence": "monthly",
            "day_of_month": 1,
            "hour_of_day": 9,
            "recipients": ["a@x.com"],
        },
        headers=auth["_authz"],
    )
    sid = created.json()["id"]

    dl = await client.delete(
        f"/api/v1/scheduled-minutes/{sid}", headers=auth["_authz"]
    )
    assert dl.status_code == 204

    lst = await client.get(
        f"/api/v1/projects/{p.id}/scheduled-minutes", headers=auth["_authz"]
    )
    assert lst.json() == []


@pytest.mark.asyncio
async def test_enh107_validates_recipients_not_empty(client, db_session):
    t, auth = await _admin(client, db_session, slug="sm-val")
    p = await _seed_project(db_session, t, folio="P-0705")
    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-minutes",
        json={
            "cadence": "weekly",
            "day_of_week": 0,
            "hour_of_day": 9,
            "recipients": [],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_enh107_select_latest_minute_in_period(client, db_session):
    t, _auth = await _admin(client, db_session, slug="sm-select")
    p = await _seed_project(db_session, t, folio="P-0706")

    now = datetime.now(UTC)
    old = _make_minute(
        str(t.id), str(p.id), when=now - timedelta(days=60), folio=f"MIN-{p.folio}-1"
    )
    mid = _make_minute(
        str(t.id), str(p.id), when=now - timedelta(days=5), folio=f"MIN-{p.folio}-2"
    )
    recent = _make_minute(
        str(t.id), str(p.id), when=now - timedelta(days=1), folio=f"MIN-{p.folio}-3"
    )
    db_session.add_all([old, mid, recent])
    await db_session.commit()

    found = await select_latest_minute(
        db_session, p.id, now - timedelta(days=7), now
    )
    assert found is not None
    assert found.id == recent.id

    none = await select_latest_minute(
        db_session, p.id, now + timedelta(days=10), now + timedelta(days=20)
    )
    assert none is None


@pytest.mark.asyncio
async def test_enh107_worker_send_selects_and_emails_minute(client, db_session):
    """El worker selecciona la última minuta del periodo y la envía."""
    from app.workers.tasks import scheduled_minutes as task_mod

    t, _auth = await _admin(client, db_session, slug="sm-worker")
    p = await _seed_project(db_session, t, folio="P-0707")

    now = datetime.now(UTC)
    minute = _make_minute(
        str(t.id), str(p.id), when=now - timedelta(days=1), folio="MIN-W-1"
    )
    db_session.add(minute)

    sched = ScheduledMinute(
        tenant_id=str(t.id),
        project_id=str(p.id),
        cadence="weekly",
        day_of_week=0,
        hour_of_day=9,
        recipients=["a@example.com"],
        enabled=True,
        next_run_at=now - timedelta(minutes=1),
    )
    db_session.add(sched)
    await db_session.commit()

    fake_resend = AsyncMock(return_value={"id": "resend-min-1"})
    with patch(
        "app.services.scheduled_minutes.send_email_via_resend", fake_resend
    ):
        result = await task_mod._send(str(sched.id))

    assert result["sent"] is True
    assert result["fallback"] is False
    assert result["minute_id"] == str(minute.id)
    fake_resend.assert_awaited_once()
    call_kwargs = fake_resend.call_args.kwargs
    assert call_kwargs["to"] == ["a@example.com"]
    assert call_kwargs["attachments"] and call_kwargs["attachments"][0][
        "filename"
    ].endswith(".pdf")

    await db_session.refresh(sched)
    assert sched.last_run_at is not None
    assert sched.next_run_at is not None
    assert sched.next_run_at > sched.last_run_at


@pytest.mark.asyncio
async def test_enh107_worker_send_fallback_when_no_minute(client, db_session):
    """Sin minuta en el periodo → email fallback informativo."""
    from app.workers.tasks import scheduled_minutes as task_mod

    t, _auth = await _admin(client, db_session, slug="sm-fallback")
    p = await _seed_project(db_session, t, folio="P-0708")

    now = datetime.now(UTC)
    sched = ScheduledMinute(
        tenant_id=str(t.id),
        project_id=str(p.id),
        cadence="daily",
        hour_of_day=9,
        recipients=["a@example.com"],
        enabled=True,
        next_run_at=now - timedelta(minutes=1),
    )
    db_session.add(sched)
    await db_session.commit()

    fake_resend = AsyncMock(return_value={"id": "resend-min-fb"})
    with patch(
        "app.services.scheduled_minutes.send_email_via_resend", fake_resend
    ):
        result = await task_mod._send(str(sched.id))

    assert result["sent"] is True
    assert result["fallback"] is True
    assert result["minute_id"] is None
    fake_resend.assert_awaited_once()
    call_kwargs = fake_resend.call_args.kwargs
    # Fallback: sin attachments.
    assert not call_kwargs.get("attachments")


@pytest.mark.asyncio
async def test_enh107_worker_dispatch_only_due(client, db_session):
    from app.workers.tasks import scheduled_minutes as task_mod

    t, _auth = await _admin(client, db_session, slug="sm-dispatch")
    p = await _seed_project(db_session, t, folio="P-0709")

    now = datetime.now(UTC)
    due = ScheduledMinute(
        tenant_id=str(t.id), project_id=str(p.id),
        cadence="daily", hour_of_day=9,
        recipients=["a@example.com"], enabled=True,
        next_run_at=now - timedelta(minutes=1),
    )
    future = ScheduledMinute(
        tenant_id=str(t.id), project_id=str(p.id),
        cadence="daily", hour_of_day=9,
        recipients=["b@example.com"], enabled=True,
        next_run_at=now + timedelta(days=1),
    )
    disabled = ScheduledMinute(
        tenant_id=str(t.id), project_id=str(p.id),
        cadence="daily", hour_of_day=9,
        recipients=["c@example.com"], enabled=False,
        next_run_at=now - timedelta(minutes=5),
    )
    db_session.add_all([due, future, disabled])
    await db_session.commit()

    dispatched: list[str] = []

    class _StubTask:
        @staticmethod
        def delay(sid: str) -> None:
            dispatched.append(sid)

    with patch.object(task_mod, "send_scheduled_minute", _StubTask):
        out = await task_mod._dispatch_due()

    assert out == {"dispatched": 1}
    assert dispatched == [str(due.id)]


@pytest.mark.asyncio
async def test_enh107_cross_tenant_404(client, db_session):
    t_a, auth_a = await _admin(client, db_session, slug="sm-ta")
    _t_b, auth_b = await _admin(client, db_session, slug="sm-tb")
    p = await _seed_project(db_session, t_a, folio="P-AAB")

    created = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-minutes",
        json={
            "cadence": "weekly",
            "day_of_week": 0,
            "hour_of_day": 9,
            "recipients": ["a@x.com"],
        },
        headers=auth_a["_authz"],
    )
    sid = created.json()["id"]

    r = await client.patch(
        f"/api/v1/scheduled-minutes/{sid}",
        json={"enabled": False},
        headers=auth_b["_authz"],
    )
    assert r.status_code == 404
