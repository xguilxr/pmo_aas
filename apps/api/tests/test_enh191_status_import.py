"""ENH-191 — Estado importable end-to-end.

La plantilla y ambos exports generan columna "Estado" pero el import la
ignoraba: sin alias en el parser, sin campo en ParsedTask y el confirm
hardcodeaba not_started. Cubre:
- Normalización: enum crudo, etiquetas ES de la UI, sinónimos EN.
- Round-trip: XLSX con columna Estado → tasks con status correcto.
- Valores no reconocidos → default not_started + warning.
"""
from __future__ import annotations

import io
import time
from typing import Any

import pytest
from openpyxl import Workbook
from sqlalchemy import select

from app.models.task import Task
from app.services import import_job_store
from app.services.xlsx_task_parser import _coerce_status, parse_xlsx
from tests.factories import create_admin_role, create_tenant, create_user, login


def test_coerce_status_enum_and_labels():
    # Enum crudo (round-trip plantilla / export backend).
    assert _coerce_status("not_started") == "not_started"
    assert _coerce_status("in_progress") == "in_progress"
    assert _coerce_status("completed") == "completed"
    assert _coerce_status("on_hold") == "on_hold"
    # Etiquetas ES de la UI (export frontend + status_display).
    assert _coerce_status("No Iniciado") == "not_started"
    assert _coerce_status("No iniciada") == "not_started"
    assert _coerce_status("En Progreso") == "in_progress"
    assert _coerce_status("En curso") == "in_progress"
    assert _coerce_status("Completada") == "completed"
    assert _coerce_status("En Pausa") == "on_hold"
    # Sinónimos EN + legacy.
    assert _coerce_status("done") == "completed"
    assert _coerce_status("On Hold") == "on_hold"
    # No reconocido / vacío → None.
    assert _coerce_status("casi lista") is None
    assert _coerce_status("") is None
    assert _coerce_status(None) is None


def _build_xlsx(rows: list[list[Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_xlsx_status_column():
    data = _build_xlsx(
        [
            ["WBS", "Tarea", "Estado"],
            ["1", "A", "in_progress"],
            ["2", "B", "Completada"],
            ["3", "C", "casi lista"],
            ["4", "D", ""],
        ]
    )
    res = parse_xlsx(data)
    assert [t.status for t in res.tasks] == ["in_progress", "completed", None, None]
    warn = next(w for w in res.warnings if w["code"] == "STATUS_UNRECOGNIZED")
    assert warn["count"] == 1
    assert warn["rows"] == ["casi lista"]


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
            "name": "P191",
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
async def test_wizard_confirm_persists_status(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    data = _build_xlsx(
        [
            ["WBS", "Tarea", "Estado"],
            ["1", "Kickoff", "Completada"],
            ["2", "Desarrollo", "en curso"],
            ["3", "Cierre", "???"],
        ]
    )
    files = {
        "file": (
            "plan.xlsx",
            data,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    r_prev = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/preview",
        files=files,
        headers=auth["_authz"],
    )
    assert r_prev.status_code == 200, r_prev.text
    assert "status" in r_prev.json()["system_fields"]
    assert r_prev.json()["columns_detected"].get("status") == 2
    job_id = r_prev.json()["job_id"]

    r_conf = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/confirm",
        json={"strategy": "replace"},
        headers=auth["_authz"],
    )
    assert r_conf.status_code == 200, r_conf.text

    tasks = (
        (await db_session.execute(select(Task).where(Task.project_id == proj_id)))
        .scalars()
        .all()
    )
    by_wbs = {t.wbs: t for t in tasks}
    assert by_wbs["1"].status == "completed"
    assert by_wbs["2"].status == "in_progress"
    # No reconocido → default.
    assert by_wbs["3"].status == "not_started"
