"""ENH-192 — wizard con mapeo completo + preview interpretado en vivo.

- `system_fields` del preview = lista completa del parser (14 campos,
  antes 9: área/criticidad/hito relacionado/estado no se podían mapear).
- `parsed_preview`: tareas ya interpretadas (WBS fiel, % escalado,
  estado normalizado) en preview y en el nuevo POST /repreview.
- /repreview re-interpreta con mapping manual sin persistir.
"""
from __future__ import annotations

import io
import time
from typing import Any

import pytest
from openpyxl import Workbook

from app.services import import_job_store
from app.services.import_mapping_suggest import SYSTEM_FIELDS as FULL_FIELDS
from tests.factories import create_admin_role, create_tenant, create_user, login


class _FakeRedis:
    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        expiry = time.monotonic() + ex if ex else float("inf")
        self._store[key] = (value, expiry)

    def get(self, key: str) -> str | None:
        row = self._store.get(key)
        if row is None:
            return None
        value, expiry = row
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return value

    def delete(self, key: str) -> int:
        return int(bool(self._store.pop(key, None)))


@pytest.fixture(autouse=True)
def _stub_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(import_job_store, "_get_client", lambda: fake)
    yield fake


def _build_xlsx(rows: list[list[Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


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
            "name": "P192",
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
async def test_preview_full_system_fields_and_parsed_preview(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    data = _build_xlsx(
        [
            ["WBS", "Tarea", "Avance (%)", "Estado"],
            ["1", "Kickoff", 50, "En Progreso"],
            ["2", "Cierre", 0, "not_started"],
        ]
    )
    files = {
        "file": (
            "plan.xlsx",
            data,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/preview",
        files=files,
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Lista completa (14) — incluye los que antes no se podían re-mapear.
    assert body["system_fields"] == list(FULL_FIELDS)
    for f in ("status", "area", "criticality", "is_critical", "related_milestone"):
        assert f in body["system_fields"]
    # Interpretación: estado normalizado + % correcto.
    pp = body["parsed_preview"]
    assert [t["status"] for t in pp] == ["in_progress", "not_started"]
    assert [t["progress"] for t in pp] == [50, 0]


@pytest.mark.asyncio
async def test_repreview_with_manual_mapping(client, db_session):
    """Headers crípticos → auto-detect falla → repreview con mapping
    manual devuelve la interpretación actualizada sin persistir nada."""
    auth, proj_id = await _setup(client, db_session)
    data = _build_xlsx(
        [
            ["Actividad", "Cod", "Situación"],
            ["Task A", "1.1", "Completada"],
            ["Task B", "1.2", "en curso"],
        ]
    )
    files = {
        "file": (
            "custom.xlsx",
            data,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    r_prev = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/preview",
        files=files,
        headers=auth["_authz"],
    )
    assert r_prev.status_code == 200
    assert r_prev.json()["task_count"] == 0  # sin columna Nombre detectada
    job_id = r_prev.json()["job_id"]

    r_re = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/repreview",
        json={"mapping": {"name": 0, "wbs_code": 1, "status": 2}},
        headers=auth["_authz"],
    )
    assert r_re.status_code == 200, r_re.text
    body = r_re.json()
    assert body["task_count"] == 2
    assert [t["status"] for t in body["parsed_preview"]] == [
        "completed",
        "in_progress",
    ]
    assert [t["wbs_code"] for t in body["parsed_preview"]] == ["1.1", "1.2"]

    # Mapping sin 'name' → sin tareas, sin error (preview-friendly).
    r_re2 = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/repreview",
        json={"mapping": {"wbs_code": 1}},
        headers=auth["_authz"],
    )
    assert r_re2.status_code == 200
    assert r_re2.json()["task_count"] == 0
