"""US-058 — comentarios sobre Riesgos (panel editable RAID)."""
from decimal import Decimal

import pytest

from app.models.modules import Risk
from app.models.organization import Organization
from app.models.project import Project
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="risk-cmt"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    u = await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, u, auth


async def _project_with_risk(db_session, tenant, *, folio="P-Q01"):
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
    r = Risk(
        tenant_id=str(tenant.id),
        project_id=p.id,
        folio="RIS-Q1",
        title="Riesgo comentable",
        status="open",
        severity=12,
        probability=3,
        impact=4,
    )
    db_session.add(r)
    await db_session.flush()
    await db_session.commit()
    return p, r


@pytest.mark.asyncio
async def test_us058_add_risk_comment_appends_entry(client, db_session):
    t, u, auth = await _admin(client, db_session, slug="risk-cmt-append")
    _p, risk = await _project_with_risk(db_session, t, folio="P-Q10")

    r1 = await client.post(
        f"/api/v1/risks/{risk.id}/comments",
        json={"text": "Primer análisis del riesgo"},
        headers=auth["_authz"],
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert len(body1["comments"]) == 1
    assert body1["comments"][0]["text"] == "Primer análisis del riesgo"
    assert body1["comments"][0]["author_id"] == str(u.id)
    assert body1["comments"][0]["created_at"]

    r2 = await client.post(
        f"/api/v1/risks/{risk.id}/comments",
        json={"text": "Mitigación acordada"},
        headers=auth["_authz"],
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert len(body2["comments"]) == 2
    assert body2["comments"][1]["text"] == "Mitigación acordada"


@pytest.mark.asyncio
async def test_us058_empty_comment_rejected(client, db_session):
    t, _u, auth = await _admin(client, db_session, slug="risk-cmt-empty")
    _p, risk = await _project_with_risk(db_session, t, folio="P-Q11")

    r = await client.post(
        f"/api/v1/risks/{risk.id}/comments",
        json={"text": ""},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_us058_risk_comment_cross_tenant_404(client, db_session):
    t_a, _ua, _auth_a = await _admin(client, db_session, slug="risk-cmt-ta")
    _, _ub, auth_b = await _admin(client, db_session, slug="risk-cmt-tb")
    _p, risk = await _project_with_risk(db_session, t_a, folio="P-Q12")

    r = await client.post(
        f"/api/v1/risks/{risk.id}/comments",
        json={"text": "No debería poder"},
        headers=auth_b["_authz"],
    )
    assert r.status_code == 404
