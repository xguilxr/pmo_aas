"""US-056 — Calendarizar envío automático de reportes vía Resend."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.models.ai import Report
from app.models.organization import Organization
from app.models.project import Project
from app.models.scheduled_report import ScheduledReport
from app.services.scheduled_reports import compute_next_run
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="sched-a"):
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


async def _seed_project(db_session, tenant, *, folio="P-0500"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id),
        organization_id=str(org.id),
        folio=folio,
        name=f"Proyecto {folio}",
        description="Proyecto para US-056",
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


def test_compute_next_run_cadences():
    base = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    # Legacy: sin params → suma fija (compat con código pre-ENH-046).
    assert compute_next_run("daily", from_dt=base) == base + timedelta(days=1)
    assert compute_next_run("weekly", from_dt=base) == base + timedelta(days=7)
    assert compute_next_run("monthly", from_dt=base) == base + timedelta(days=30)
    with pytest.raises(ValueError):
        compute_next_run("yearly")


@pytest.mark.asyncio
async def test_us056_create_scheduled_report(client, db_session):
    t, auth = await _admin(client, db_session, slug="sched-create")
    p = await _seed_project(db_session, t, folio="P-0501")

    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "avance",
            "cadence": "weekly",
            "day_of_week": 0,
            "hour_of_day": 9,
            "recipients": ["pm@example.com", "sponsor@example.com"],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["report_type"] == "avance"
    assert body["cadence"] == "weekly"
    assert body["enabled"] is True
    assert body["next_run_at"] is not None
    assert len(body["recipients"]) == 2


@pytest.mark.asyncio
async def test_us056_update_toggles_next_run(client, db_session):
    t, auth = await _admin(client, db_session, slug="sched-update")
    p = await _seed_project(db_session, t, folio="P-0502")

    created = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "seguimiento",
            "cadence": "daily",
            "hour_of_day": 9,
            "recipients": ["a@x.com"],
        },
        headers=auth["_authz"],
    )
    sid = created.json()["id"]

    # Pausar limpia next_run_at
    paused = await client.patch(
        f"/api/v1/scheduled-reports/{sid}",
        json={"enabled": False},
        headers=auth["_authz"],
    )
    assert paused.status_code == 200
    assert paused.json()["enabled"] is False
    assert paused.json()["next_run_at"] is None

    # Reactivar re-computa next_run_at
    resumed = await client.patch(
        f"/api/v1/scheduled-reports/{sid}",
        json={
            "enabled": True,
            "cadence": "weekly",
            "day_of_week": 1,
            "hour_of_day": 9,
        },
        headers=auth["_authz"],
    )
    assert resumed.status_code == 200
    assert resumed.json()["enabled"] is True
    assert resumed.json()["cadence"] == "weekly"
    assert resumed.json()["next_run_at"] is not None


@pytest.mark.asyncio
async def test_us056_delete_scheduled_report(client, db_session):
    t, auth = await _admin(client, db_session, slug="sched-delete")
    p = await _seed_project(db_session, t, folio="P-0503")

    created = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "avance",
            "cadence": "monthly",
            # ENH-056: monthly ahora requiere day_of_month + hour_of_day.
            "day_of_month": 1,
            "hour_of_day": 9,
            "recipients": ["a@x.com"],
        },
        headers=auth["_authz"],
    )
    sid = created.json()["id"]

    dl = await client.delete(
        f"/api/v1/scheduled-reports/{sid}", headers=auth["_authz"]
    )
    assert dl.status_code == 204

    lst = await client.get(
        f"/api/v1/projects/{p.id}/scheduled-reports", headers=auth["_authz"]
    )
    assert lst.status_code == 200
    assert lst.json() == []


@pytest.mark.asyncio
async def test_us056_cross_tenant_404(client, db_session):
    t_a, auth_a = await _admin(client, db_session, slug="sched-ta")
    _t_b, auth_b = await _admin(client, db_session, slug="sched-tb")
    p = await _seed_project(db_session, t_a, folio="P-AAA")

    created = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "avance",
            "cadence": "weekly",
            "day_of_week": 0,
            "hour_of_day": 9,
            "recipients": ["a@x.com"],
        },
        headers=auth_a["_authz"],
    )
    sid = created.json()["id"]

    r = await client.patch(
        f"/api/v1/scheduled-reports/{sid}",
        json={"enabled": False},
        headers=auth_b["_authz"],
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_us056_non_admin_cannot_create(client, db_session):
    """Post-DEC-024: cualquier user autenticado del tenant puede
    programar reportes; el gate admin-only desapareció."""
    t, _auth = await _admin(client, db_session, slug="sched-viewer")
    p = await _seed_project(db_session, t, folio="P-0504")
    await create_user(
        db_session,
        tenant=t,
        username="viewer_sched",
        email="viewer@sched-viewer.example.com",
        password="Str0ng-User-1!",
    )
    viewer = await login(client, "viewer_sched", "Str0ng-User-1!")

    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "avance",
            "cadence": "weekly",
            "day_of_week": 0,
            "hour_of_day": 9,
            "recipients": ["a@x.com"],
        },
        headers=viewer["_authz"],
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_us056_validates_recipients_not_empty(client, db_session):
    t, auth = await _admin(client, db_session, slug="sched-val")
    p = await _seed_project(db_session, t, folio="P-0505")
    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        json={
            "report_type": "avance",
            "cadence": "weekly",
            "day_of_week": 0,
            "hour_of_day": 9,
            "recipients": [],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_us056_worker_send_persists_report_and_updates_next_run(
    client, db_session
):
    """El worker genera PDF, persiste `reports` row, update last/next_run_at."""
    from app.workers.tasks import scheduled_reports as task_mod

    t, _auth = await _admin(client, db_session, slug="sched-worker")
    p = await _seed_project(db_session, t, folio="P-0506")

    sched = ScheduledReport(
        tenant_id=str(t.id),
        project_id=str(p.id),
        report_type="avance",
        cadence="daily",
        recipients=["a@example.com"],
        enabled=True,
        next_run_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(sched)
    await db_session.commit()

    fake_resend = AsyncMock(return_value={"id": "resend-123"})
    with patch.object(task_mod, "send_email_via_resend", fake_resend):
        result = await task_mod._send(str(sched.id))

    assert result["sent"] is True
    assert result["provider_id"] == "resend-123"
    fake_resend.assert_awaited_once()
    call_kwargs = fake_resend.call_args.kwargs
    assert call_kwargs["to"] == ["a@example.com"]
    assert call_kwargs["attachments"] and call_kwargs["attachments"][0][
        "filename"
    ].endswith(".pdf")

    # Report snapshot persistido y schedule actualizado.
    from sqlalchemy import select

    rep = (
        await db_session.execute(
            select(Report).where(
                Report.tenant_id == str(t.id),
                Report.project_id == str(p.id),
                Report.generator == "avance",
            )
        )
    ).scalar_one()
    assert rep.status == "sent"
    assert rep.sent_at is not None

    await db_session.refresh(sched)
    assert sched.last_run_at is not None
    assert sched.next_run_at is not None
    assert sched.next_run_at > sched.last_run_at


@pytest.mark.asyncio
async def test_us056_worker_dispatch_only_due_schedules(client, db_session):
    from app.workers.tasks import scheduled_reports as task_mod

    t, _auth = await _admin(client, db_session, slug="sched-dispatch")
    p = await _seed_project(db_session, t, folio="P-0507")

    now = datetime.now(UTC)
    # Due, enabled → se despacha
    due = ScheduledReport(
        tenant_id=str(t.id),
        project_id=str(p.id),
        report_type="avance",
        cadence="daily",
        recipients=["a@example.com"],
        enabled=True,
        next_run_at=now - timedelta(minutes=1),
    )
    # Future → no se despacha
    future = ScheduledReport(
        tenant_id=str(t.id),
        project_id=str(p.id),
        report_type="avance",
        cadence="daily",
        recipients=["b@example.com"],
        enabled=True,
        next_run_at=now + timedelta(days=1),
    )
    # Disabled → no se despacha
    disabled = ScheduledReport(
        tenant_id=str(t.id),
        project_id=str(p.id),
        report_type="avance",
        cadence="daily",
        recipients=["c@example.com"],
        enabled=False,
        next_run_at=now - timedelta(minutes=5),
    )
    db_session.add_all([due, future, disabled])
    await db_session.commit()

    dispatched: list[str] = []

    class _StubTask:
        @staticmethod
        def delay(sid: str) -> None:
            dispatched.append(sid)

    with patch.object(task_mod, "send_scheduled_report", _StubTask):
        out = await task_mod._dispatch_due()

    assert out == {"dispatched": 1}
    assert dispatched == [str(due.id)]
