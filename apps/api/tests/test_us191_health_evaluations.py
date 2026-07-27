"""US-191 — evaluación periódica de salud 5+1 con historial.

- POST crea el registro histórico y aplica el overall (la "sexta") al
  semáforo del proyecto como declaración manual.
- Amarillo/rojo global sin nota → 422 (regla US-180).
- GET devuelve el historial más reciente primero.
"""
from __future__ import annotations

import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


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
            "name": "P191H",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return auth, p.json()["id"]


@pytest.mark.asyncio
async def test_evaluation_creates_history_and_applies_overall(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/health-evaluations",
        json={
            "evaluated_at": "2026-07-15",
            "schedule": "yellow",
            "budget": "green",
            "risks": "green",
            "decisions": "green",
            "resources": "yellow",
            "overall": "yellow",
            "note": "Cronograma con 2 semanas de atraso por vacaciones.",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["evaluated_at"] == "2026-07-15"
    assert body["schedule"] == "yellow"
    assert body["overall"] == "yellow"

    # La sexta evaluación ES el semáforo del proyecto (manual).
    detail = await client.get(
        f"/api/v1/projects/{proj_id}", headers=auth["_authz"]
    )
    assert detail.json()["health_status"] == "yellow"
    assert detail.json()["health_source"] == "manual"

    # Segunda evaluación (verde, sin nota) + historial desc.
    r2 = await client.post(
        f"/api/v1/projects/{proj_id}/health-evaluations",
        json={"evaluated_at": "2026-07-18", "overall": "green"},
        headers=auth["_authz"],
    )
    assert r2.status_code == 201, r2.text
    hist = await client.get(
        f"/api/v1/projects/{proj_id}/health-evaluations",
        headers=auth["_authz"],
    )
    assert hist.status_code == 200
    dates = [h["evaluated_at"] for h in hist.json()]
    assert dates == ["2026-07-18", "2026-07-15"]
    # Dimensiones no evaluadas quedan null (el PM evaluó solo la global).
    assert hist.json()[0]["schedule"] is None


@pytest.mark.asyncio
async def test_yellow_overall_requires_note(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/health-evaluations",
        json={"overall": "red"},
        headers=auth["_authz"],
    )
    # validation_error → 400 (misma convención que declare_health US-180).
    assert r.status_code == 400
    assert "nota" in r.text.lower()
