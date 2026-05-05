"""ENH-053 — Plan import: mapeo de columnas asistido por IA.

Cubre:
- TC-053.2: ai_mode=disabled → heurística devuelve `name` para
  "Tarea"/"Title"/"Task" (case-insensitive).
- Headers desconocidos → confidence baja / field None.
- Heurística sustring match para variantes (ej. "Fecha inicio" → start_date).
"""
import pytest

from app.services.ai.tenant_ai import TenantAIConfig
from app.services.import_mapping_suggest import (
    heuristic_suggestion,
    suggest_column_mapping,
)
from tests.factories import create_admin_role, create_tenant, create_user, login


def test_heuristic_exact_synonym():
    s = heuristic_suggestion("Tarea")
    assert s["field"] == "name"
    assert s["confidence"] >= 0.9


def test_heuristic_substring():
    s = heuristic_suggestion("Fecha inicio")
    assert s["field"] == "start_date"
    assert s["confidence"] >= 0.6


def test_heuristic_unknown_header():
    s = heuristic_suggestion("xqzy")
    assert s["field"] is None
    assert s["confidence"] == 0.0


@pytest.mark.asyncio
async def test_disabled_tenant_returns_only_heuristic():
    cfg = TenantAIConfig(mode="disabled")
    out = await suggest_column_mapping(
        ["Tarea", "Inicio", "Fin", "Responsable", "xqzy"],
        tenant_cfg=cfg,
    )
    assert out["Tarea"]["field"] == "name"
    assert out["Inicio"]["field"] == "start_date"
    assert out["Fin"]["field"] == "end_date"
    assert out["Responsable"]["field"] == "resources"
    assert out["xqzy"]["field"] is None
    # Ningún source AI cuando disabled.
    assert all(v["source"] in ("heuristic", "none") for v in out.values())


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
            "name": "P1",
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
async def test_endpoint_returns_suggestions(client, db_session):
    auth, proj = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj}/tasks/import/suggest-mapping",
        json={"headers": ["Tarea", "Inicio", "Fin", "Avance"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["suggestions"]["Tarea"]["field"] == "name"
    assert body["suggestions"]["Inicio"]["field"] == "start_date"
    assert body["suggestions"]["Fin"]["field"] == "end_date"
    assert body["suggestions"]["Avance"]["field"] == "progress"
    # Tenant fresco no tiene AI configurada → ai_used False.
    assert body["ai_used"] is False
    assert "name" in body["system_fields"]
