"""ENH-106 — meeting_minutes.origin audit field.

Verifica que:
- El POST manual acepta el campo `origin` (Literal de 4 valores) y lo
  devuelve en la respuesta.
- El default es `'manual'` cuando no se manda.
- Un valor inválido devuelve 422.
- Si `generated_by_ai=True` y no se manda origin → backfill a
  `transcript_ai`.
"""
import pytest

from app.core.security import validate_password_policy  # noqa: F401
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin",
        email="admin@enh106.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        "/api/v1/organizations", json={"name": "Org"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "P1", "description": "d", "type": "innovation",
            "priority": 3, "organization_id": org_id, "pm_id": pm_id,
        },
        headers=auth["_authz"],
    )
    proj_id = r.json()["id"]
    return auth, proj_id


@pytest.mark.asyncio
async def test_enh106_origin_default_manual(client, db_session):
    """POST sin `origin` → default `manual`."""
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/meeting-minutes",
        json={
            "title": "Sin origin",
            "meeting_date": "2026-05-23T10:00:00+00:00",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["origin"] == "manual"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value", ["manual", "transcript_ai", "import_file", "import_paste"]
)
async def test_enh106_origin_accepts_all_values(client, db_session, value):
    """POST acepta los 4 valores y los devuelve tal cual."""
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/meeting-minutes",
        json={
            "title": f"Origin {value}",
            "meeting_date": "2026-05-23T10:00:00+00:00",
            "origin": value,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["origin"] == value


@pytest.mark.asyncio
async def test_enh106_origin_invalid_returns_422(client, db_session):
    """Valor fuera del enum → 422 (Pydantic Literal)."""
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/meeting-minutes",
        json={
            "title": "Mal origin",
            "meeting_date": "2026-05-23T10:00:00+00:00",
            "origin": "bogus_value",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_enh106_origin_auto_transcript_ai_when_generated_by_ai(client, db_session):
    """Si body declara generated_by_ai=True y origin default → corrige a
    `transcript_ai` por consistencia con el backfill de la migración."""
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/meeting-minutes",
        json={
            "title": "IA sin origin",
            "meeting_date": "2026-05-23T10:00:00+00:00",
            "generated_by_ai": True,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["origin"] == "transcript_ai"
    assert r.json()["generated_by_ai"] is True


@pytest.mark.asyncio
async def test_enh106_origin_read_endpoint(client, db_session):
    """GET /meeting-minutes/{id} devuelve origin."""
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/meeting-minutes",
        json={
            "title": "Pasted",
            "meeting_date": "2026-05-23T10:00:00+00:00",
            "origin": "import_paste",
        },
        headers=auth["_authz"],
    )
    mid = r.json()["id"]
    g = await client.get(
        f"/api/v1/meeting-minutes/{mid}", headers=auth["_authz"]
    )
    assert g.status_code == 200
    assert g.json()["origin"] == "import_paste"
