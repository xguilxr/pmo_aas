"""US-131 — Suscripciones de reportes custom (EP020).

TC-232 (schedule custom corre en cron — el endpoint create acepta
report_type='custom' + report_builder_template_id), TC-233/234
(destinatarios externos aceptados por EmailStr) — el envío real vía
Resend está stubbeado en el worker; aquí validamos el cableado.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.organization import Organization
from app.models.project import Project
from app.models.report_builder_template import ReportBuilderTemplate
from app.models.report_section import ReportSection
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session, slug):
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
    org = Organization(tenant_id=t.id, name="Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(t.id),
        organization_id=str(org.id),
        folio="P-CUST",
        name="Proj custom",
        phase="execution",
        health_status="green",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db_session.add(p)
    db_session.add(
        ReportSection(
            code="S-01",
            name="Portada",
            category="HDR",
            level=3,
            data_shape={},
            parameters_schema={},
            composition_mode_default="A",
            supports_ia=False,
            enabled=True,
        )
    )
    tpl = ReportBuilderTemplate(
        tenant_id=str(t.id),
        code="T-CUSTOM",
        name="Mi plantilla",
        level=3,
        composition_mode="A",
        section_codes=["S-01"],
        default_parameters={},
        is_seed=False,
    )
    db_session.add(tpl)
    await db_session.flush()
    await db_session.commit()
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, p, tpl, auth


@pytest.mark.asyncio
async def test_tc232_create_custom_schedule(client, db_session):
    t, p, tpl, auth = await _setup(client, db_session, "us131-create")

    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        headers=auth["_authz"],
        json={
            "report_type": "custom",
            "cadence": "weekly",
            "day_of_week": 0,
            "hour_of_day": 9,
            "recipients": ["pm@example.com"],
            "report_builder_template_id": str(tpl.id),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["report_type"] == "custom"
    assert body["report_builder_template_id"] == str(tpl.id)
    assert body["next_run_at"] is not None


@pytest.mark.asyncio
async def test_custom_requires_template_id(client, db_session):
    t, p, _, auth = await _setup(client, db_session, "us131-no-tpl")
    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        headers=auth["_authz"],
        json={
            "report_type": "custom",
            "cadence": "daily",
            "hour_of_day": 8,
            "recipients": ["pm@example.com"],
        },
    )
    assert r.status_code == 422  # pydantic validation error


@pytest.mark.asyncio
async def test_tc234_external_email_accepted(client, db_session):
    """TC-234 — destinatarios externos (email no del tenant) son OK."""
    t, p, tpl, auth = await _setup(client, db_session, "us131-ext")
    r = await client.post(
        f"/api/v1/projects/{p.id}/scheduled-reports",
        headers=auth["_authz"],
        json={
            "report_type": "custom",
            "cadence": "once",
            "run_at": "2099-12-31T10:00:00+00:00",
            "recipients": ["cliente@otra-empresa.example.com"],
            "report_builder_template_id": str(tpl.id),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["recipients"] == ["cliente@otra-empresa.example.com"]
