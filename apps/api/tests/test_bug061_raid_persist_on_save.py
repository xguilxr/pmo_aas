"""BUG-061 — Al guardar minuta desde el preview IA, los items RAID
marcados `status="pending"` se convierten en tickets reales (risks /
issues / lessons / changes). Items con `status="discarded"`
(desmarcados en el preview por el PM) NO se crean.
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.modules import ChangeRequest, Issue, Lesson, MeetingMinute, Risk
from app.models.organization import Organization
from app.models.project import Project
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="bug061"):
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


async def _seed_project(db_session, tenant, *, folio="P-0900"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id),
        organization_id=str(org.id),
        folio=folio,
        name=f"Proyecto {folio}",
        description="BUG-061",
        phase="execution",
        health_status="green",
        budget=Decimal("1000"),
        actual_budget=Decimal("400"),
        progress=10,
    )
    db_session.add(p)
    await db_session.flush()
    await db_session.commit()
    return p


def _make_payload(*, all_pending=True, discarded_keys: set[str] | None = None) -> dict:
    """5 items mixtos A/R/D/I. Por default todos `pending`. Si
    `discarded_keys` trae claves "kind:idx", esos van con
    `status="discarded"`.
    """
    discarded_keys = discarded_keys or set()

    def _mk(kind: str, idx: int, short_desc: str) -> dict:
        status = "discarded" if f"{kind}:{idx}" in discarded_keys else "pending"
        return {
            "short_desc": short_desc,
            "suggested_owner_name": None,
            "suggested_priority": 3,
            "raw_quote": None,
            "status": status,
            "ticket_id": None,
            "ticket_type": None,
        }

    return {
        "risks": [_mk("risks", 0, "Riesgo de retraso en componente X")],
        "issues": [
            _mk("issues", 0, "Build CI fallando en main"),
            _mk("issues", 1, "Tests flakey en módulo Y"),
        ],
        "lessons": [_mk("lessons", 0, "Documentar setup del entorno")],
        "changes": [_mk("changes", 0, "Cambiar fechas de hito Z")],
    }


@pytest.mark.asyncio
async def test_create_minute_auto_approves_all_pending_raid_items(
    client, db_session
):
    """TC-061: Crear minuta IA con 5 items mixtos (A/R/D/I), todos
    pending. Tras crear → 5 tickets reales, raid_suggestions queda con
    `status="approved"` + `ticket_id` para los 5.
    """
    tenant, auth = await _admin(client, db_session, slug="bug061-a")
    project = await _seed_project(db_session, tenant, folio="P-0901")

    payload = {
        "title": "Minuta de prueba BUG-061",
        "meeting_date": datetime.now(UTC).isoformat(),
        "participants": [{"name": "Ana", "role": "PM"}],
        "topics": [{"title": "Status", "notes": "OK"}],
        "agreements": [],
        "generated_by_ai": True,
        "raid_suggestions": _make_payload(),
        # auto_approve_raid default True
    }
    r = await client.post(
        f"/api/v1/projects/{project.id}/meeting-minutes",
        json=payload,
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    minute_id = r.json()["id"]

    # 1 risk, 2 issues, 1 lesson, 1 change creados
    risks = (await db_session.execute(select(Risk).where(Risk.project_id == project.id))).scalars().all()
    issues = (await db_session.execute(select(Issue).where(Issue.project_id == project.id))).scalars().all()
    lessons = (await db_session.execute(select(Lesson).where(Lesson.project_id == project.id))).scalars().all()
    changes = (await db_session.execute(select(ChangeRequest).where(ChangeRequest.project_id == project.id))).scalars().all()
    assert len(risks) == 1
    assert len(issues) == 2
    assert len(lessons) == 1
    assert len(changes) == 1

    # raid_suggestions queda marcado approved + ticket_id
    m = (
        await db_session.execute(select(MeetingMinute).where(MeetingMinute.id == minute_id))
    ).scalar_one()
    sugg = dict(m.raid_suggestions or {})
    for kind in ("risks", "issues", "lessons", "changes"):
        for item in sugg.get(kind) or []:
            assert item["status"] == "approved"
            assert item["ticket_id"] is not None
            assert item["ticket_type"] in {"risk", "issue", "lesson", "change_request"}


@pytest.mark.asyncio
async def test_create_minute_skips_discarded_items(client, db_session):
    """CA: si el PM desmarcó un sugerido en el preview, NO se crea
    ticket. Marcamos issues[1] como `discarded` → solo 4 tickets se
    crean en total.
    """
    tenant, auth = await _admin(client, db_session, slug="bug061-b")
    project = await _seed_project(db_session, tenant, folio="P-0902")

    payload = {
        "title": "Minuta con descartes",
        "meeting_date": datetime.now(UTC).isoformat(),
        "participants": [],
        "topics": [],
        "agreements": [],
        "generated_by_ai": True,
        "raid_suggestions": _make_payload(discarded_keys={"issues:1"}),
    }
    r = await client.post(
        f"/api/v1/projects/{project.id}/meeting-minutes",
        json=payload,
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    minute_id = r.json()["id"]

    issues = (await db_session.execute(select(Issue).where(Issue.project_id == project.id))).scalars().all()
    assert len(issues) == 1  # solo el index 0
    # Total tickets = 1 risk + 1 issue + 1 lesson + 1 change = 4
    risks = (await db_session.execute(select(Risk).where(Risk.project_id == project.id))).scalars().all()
    lessons = (await db_session.execute(select(Lesson).where(Lesson.project_id == project.id))).scalars().all()
    changes = (await db_session.execute(select(ChangeRequest).where(ChangeRequest.project_id == project.id))).scalars().all()
    assert len(risks) + len(issues) + len(lessons) + len(changes) == 4

    # El item descartado mantiene status="discarded" en raid_suggestions
    m = (
        await db_session.execute(select(MeetingMinute).where(MeetingMinute.id == minute_id))
    ).scalar_one()
    issues_sugg = (m.raid_suggestions or {}).get("issues") or []
    assert issues_sugg[0]["status"] == "approved"
    assert issues_sugg[0]["ticket_id"] is not None
    assert issues_sugg[1]["status"] == "discarded"
    assert issues_sugg[1].get("ticket_id") is None


@pytest.mark.asyncio
async def test_create_minute_skips_auto_approve_when_flag_off(
    client, db_session
):
    """Backward-compat: clientes legacy que envían
    `auto_approve_raid=False` no ven tickets creados (mantiene flow
    US-108 con approve explícito posterior).
    """
    tenant, auth = await _admin(client, db_session, slug="bug061-c")
    project = await _seed_project(db_session, tenant, folio="P-0903")

    payload = {
        "title": "Minuta sin auto-approve",
        "meeting_date": datetime.now(UTC).isoformat(),
        "participants": [],
        "topics": [],
        "agreements": [],
        "generated_by_ai": True,
        "raid_suggestions": _make_payload(),
        "auto_approve_raid": False,
    }
    r = await client.post(
        f"/api/v1/projects/{project.id}/meeting-minutes",
        json=payload,
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text

    # Sin auto-approve, ningún ticket se crea
    risks = (await db_session.execute(select(Risk).where(Risk.project_id == project.id))).scalars().all()
    issues = (await db_session.execute(select(Issue).where(Issue.project_id == project.id))).scalars().all()
    lessons = (await db_session.execute(select(Lesson).where(Lesson.project_id == project.id))).scalars().all()
    changes = (await db_session.execute(select(ChangeRequest).where(ChangeRequest.project_id == project.id))).scalars().all()
    assert (len(risks), len(issues), len(lessons), len(changes)) == (0, 0, 0, 0)
