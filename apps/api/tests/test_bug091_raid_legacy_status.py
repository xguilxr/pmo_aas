"""BUG-091 — editar un riesgo con status legacy no grababa (422).

Cadena del bug: el flujo de minutas IA creaba riesgos con
``status='identified'`` (legacy pre-US-179) → el form de edición
re-enviaba ese valor → el Literal de 4 estados lo rechazaba con 422 y
la edición nunca grababa. Cubre:
- Validator: legacy → canónico en RiskUpdate/RiskCreate/Issue*.
- Endpoint: PATCH de un riesgo con status legacy en DB ahora graba.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.modules import Risk
from app.schemas.modules import IssueUpdate, RiskCreate, RiskUpdate
from tests.factories import create_admin_role, create_tenant, create_user, login


def test_update_schema_coerces_legacy_statuses():
    assert RiskUpdate(status="identified").status == "open"
    assert RiskUpdate(status="analyzing").status == "in_progress"
    assert RiskUpdate(status="mitigating").status == "in_progress"
    assert RiskUpdate(status="materialized").status == "resolved"
    assert IssueUpdate(status="closed").status == "resolved"
    # Canónicos pasan intactos; basura sigue rechazada.
    assert RiskUpdate(status="on_hold").status == "on_hold"
    with pytest.raises(ValueError):
        RiskUpdate(status="whatever")


def test_create_schema_stays_strict():
    """Contrato US-179 (TC-179.4): CREATE con legacy sigue rechazado —
    la tolerancia es solo para EDITAR data vieja, no para seguir
    creándola."""
    from uuid import uuid4

    with pytest.raises(ValueError):
        RiskCreate(
            title="Riesgo X", probability=3, impact=3, area_id=uuid4(),
            status="identified",
        )


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    org = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": "P091",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return auth, t, p.json()["id"]


@pytest.mark.asyncio
async def test_patch_risk_with_legacy_status_saves(client, db_session):
    """El caso RIS-2026-009 del cliente: riesgo con status legacy en DB
    (creado por el flujo de minutas post-0089). El PATCH que re-envía el
    legacy ahora graba y normaliza — antes 422 y edición imposible."""
    auth, tenant, proj_id = await _setup(client, db_session)
    risk = Risk(
        tenant_id=str(tenant.id), project_id=proj_id, folio="RIS-2026-009",
        title="Riesgo legacy", description=None, category=None,
        probability=3, impact=3, severity=9, mitigation_strategy=None,
        status="identified", comments=[],
    )
    db_session.add(risk)
    await db_session.flush()  # asigna el UUID default
    risk_id = str(risk.id)  # antes del commit (expire_on_commit + async)
    await db_session.commit()

    r = await client.patch(
        f"/api/v1/risks/{risk_id}",
        json={"title": "Riesgo legacy editado", "status": "identified"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "open"
    db_session.expire_all()  # el API escribe en otra sesión
    stored = (
        await db_session.execute(select(Risk).where(Risk.id == risk_id))
    ).scalar_one()
    assert stored.status == "open"
    assert stored.title == "Riesgo legacy editado"
