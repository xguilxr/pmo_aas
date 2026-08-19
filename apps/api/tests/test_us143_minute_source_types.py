"""US-143 — generador unificado de minutas: 3 source_types.

Verifica que `POST /ai/minutes` ahora discrimina por `source_type`:
- `transcript` (default, retrocompatible) → dispatch celery con prompt MINUTE_SYSTEM.
- `minute` → dispatch celery con prompt MINUTE_NORMALIZE_SYSTEM.
- `manual` → persiste MeetingMinute directo, sin invocar IA.
"""
from __future__ import annotations

import pytest

from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    enable_tenant_ai,
    login,
)


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    await enable_tenant_ai(
        db_session, t, mode="byo",
        byo={"provider": "openai", "api_key_encrypted": "stub-key", "model": "stub"},
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        "/api/v1/organizations", json={"name": "OrgUS143"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": "PUS143", "description": "d", "type": "innovacion",
            "priority": 3, "organization_id": org_id, "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return t, auth, p.json()["id"]


@pytest.mark.asyncio
async def test_source_type_transcript_dispatches_with_transcript(
    client, db_session, monkeypatch,
):
    """Default `source_type=transcript` (omitido) → delega a celery con kwarg
    `source_type='transcript'`."""
    from app.workers.tasks import ai as ai_tasks

    captured = {}

    def fake_delay(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(ai_tasks.generate_minute_task, "delay", fake_delay)

    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={
            "project_id": proj_id,
            "transcript": "transcript válido largo de reunión Estado del proyecto...",
            "save_as_minute": False,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 202, r.text
    assert captured["source_type"] == "transcript"
    assert "transcript válido" in captured["transcript"]


@pytest.mark.asyncio
async def test_source_type_minute_dispatches_with_minute(
    client, db_session, monkeypatch,
):
    """`source_type=minute` → delega a celery con `source_type='minute'`
    (worker usará MINUTE_NORMALIZE_SYSTEM)."""
    from app.workers.tasks import ai as ai_tasks

    captured = {}

    def fake_delay(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(ai_tasks.generate_minute_task, "delay", fake_delay)

    _, auth, proj_id = await _setup(client, db_session)
    minute_text = (
        "# Minuta Reunión Estado\n\n"
        "## Participantes\n- Juan Pérez (PM)\n\n"
        "## Acuerdos\n1. Subir cotización antes del viernes."
    )
    r = await client.post(
        "/api/v1/ai/minutes",
        json={
            "project_id": proj_id,
            "source_type": "minute",
            "transcript": minute_text,
            "save_as_minute": True,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 202, r.text
    assert captured["source_type"] == "minute"


@pytest.mark.asyncio
async def test_source_type_manual_persists_directly_no_ai(
    client, db_session, monkeypatch,
):
    """`source_type=manual` → NO dispatcha celery; crea MeetingMinute directo
    desde structured_data; responde con minute_id."""
    from app.workers.tasks import ai as ai_tasks

    dispatched = {"called": False}

    def fake_delay(**kwargs):
        dispatched["called"] = True

    monkeypatch.setattr(ai_tasks.generate_minute_task, "delay", fake_delay)

    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={
            "project_id": proj_id,
            "source_type": "manual",
            "title": "Acta Manual Sprint 30",
            "structured_data": {
                "header": {"title": "Acta Manual Sprint 30"},
                "participants": {
                    "attendees": [{"name": "Ana", "role": "PM"}],
                },
                "summary": "Sesión de planeación.",
                "topics": [{"title": "Backlog", "bullets": ["Revisar prioridades"]}],
                "agreements": [],
                "raid": [],
                "free_notes": None,
            },
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 202, r.text  # endpoint sigue declarando 202 default
    body = r.json()
    assert body.get("status") == "saved"
    assert body.get("minute_id")
    assert body.get("folio", "").startswith("MIN-")
    # No se llamó al worker.
    assert dispatched["called"] is False

    # Verifica que la minuta quedó en DB.
    mm = await client.get(
        f"/api/v1/meeting-minutes/{body['minute_id']}", headers=auth["_authz"]
    )
    assert mm.status_code == 200, mm.text
    data = mm.json()
    assert data["title"] == "Acta Manual Sprint 30"
    assert data["generated_by_ai"] is False
    assert len(data["participants"]) == 1
    assert data["participants"][0]["name"] == "Ana"


@pytest.mark.asyncio
async def test_source_type_transcript_missing_transcript_rejected(
    client, db_session,
):
    """`source_type=transcript` sin campo `transcript` → 422."""
    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={"project_id": proj_id, "source_type": "transcript"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_source_type_manual_missing_structured_data_rejected(
    client, db_session,
):
    """`source_type=manual` sin `structured_data` → 422."""
    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={"project_id": proj_id, "source_type": "manual"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422
