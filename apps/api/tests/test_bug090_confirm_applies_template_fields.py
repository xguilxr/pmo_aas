"""BUG-090 — el confirm del wizard aplica TODO lo que la plantilla promete.

La hoja Instrucciones de la plantilla (US-096/ENH-134) promete cosas que
el confirm descartaba silenciosamente:
- Responsable → fuzzy-match contra el pool de recursos (actors).
- Hito Relacionado → resolución por WBS.
- Predecessors → reconstrucción de dependencias.
- Fin vacío + duración → Fin calculado.
"""
from __future__ import annotations

import io
import time
from datetime import date
from typing import Any

import pytest
from openpyxl import Workbook
from sqlalchemy import select

from app.models.area import Actor
from app.models.task import Task, TaskDependency
from app.services import import_job_store
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
            "name": "P090",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    # Actor del pool para el fuzzy-match de Responsable.
    actor = Actor(tenant_id=str(t.id), name="Juan Pérez", email="juan.perez@acme.example.com")
    db_session.add(actor)
    await db_session.commit()
    return auth, p.json()["id"], str(actor.id)


TEMPLATE_ROWS = [
    # Headers de la plantilla V1 (subset relevante).
    ["WBS", "Tarea", "Inicio", "Fin", "Duración (días)", "Es hito",
     "Hito Relacionado", "Predecessors", "Responsable"],
    ["1", "Kickoff", "2026-01-05", "", 5, "No", "", "", "Juan Perez"],
    ["1.1", "Análisis", "2026-01-12", "2026-01-16", 5, "No", "1.2", "1", ""],
    ["1.2", "Cierre fase", "2026-01-20", "2026-01-20", 1, "Sí", "", "1, 1.1", ""],
]


async def _import_template(client, auth, proj_id):
    data = _build_xlsx(TEMPLATE_ROWS)
    files = {
        "file": (
            "plantilla.xlsx",
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
    job_id = r_prev.json()["job_id"]
    r_conf = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/confirm",
        json={"strategy": "replace"},
        headers=auth["_authz"],
    )
    assert r_conf.status_code == 200, r_conf.text
    return r_conf.json()


@pytest.mark.asyncio
async def test_confirm_applies_promised_fields(client, db_session):
    auth, proj_id, actor_id = await _setup(client, db_session)
    body = await _import_template(client, auth, proj_id)
    assert body["imported"] == 3
    # Predecesoras: 1.1→[1], 1.2→[1, 1.1] = 3 dependencias FS.
    assert body["dependencies_created"] == 3

    tasks = (
        (await db_session.execute(select(Task).where(Task.project_id == proj_id)))
        .scalars()
        .all()
    )
    by_wbs = {t.wbs_code: t for t in tasks}

    # Fin desde duración: Inicio 2026-01-05 + 5 días inclusivos → 01-09.
    assert by_wbs["1"].end_date == date(2026, 1, 9)
    # Responsable con typo leve ("Juan Perez" sin tilde) → fuzzy ≥0.85.
    assert str(by_wbs["1"].assignee_actor_id) == actor_id
    # Hito relacionado por WBS: 1.1 → 1.2 (que es hito).
    assert str(by_wbs["1.1"].related_milestone_id) == str(by_wbs["1.2"].id)
    # Predecesoras JSON + successors derivados.
    assert by_wbs["1.1"].predecessors == ["1"]
    assert sorted(by_wbs["1.2"].predecessors) == ["1", "1.1"]
    assert "1.1" in (by_wbs["1"].successors or [])

    deps = (
        (
            await db_session.execute(
                select(TaskDependency).where(
                    TaskDependency.successor_id.in_([str(t.id) for t in tasks])
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(deps) == 3
    assert all(d.type == "FS" for d in deps)


@pytest.mark.asyncio
async def test_confirm_merge_does_not_duplicate_dependencies(client, db_session):
    auth, proj_id, _actor_id = await _setup(client, db_session)
    await _import_template(client, auth, proj_id)

    # Re-import en merge: mismas predecesoras → 0 dependencias nuevas.
    data = _build_xlsx(TEMPLATE_ROWS)
    files = {
        "file": (
            "plantilla.xlsx",
            data,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    r_prev = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/preview",
        files=files,
        headers=auth["_authz"],
    )
    job_id = r_prev.json()["job_id"]
    r_conf = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/confirm",
        json={"strategy": "merge"},
        headers=auth["_authz"],
    )
    assert r_conf.status_code == 200, r_conf.text
    assert r_conf.json()["dependencies_created"] == 0


@pytest.mark.asyncio
async def test_confirm_skips_cyclic_predecessors(client, db_session):
    """A→B y B→A: el import no aborta; la segunda arista se omite y se
    reporta en errors."""
    auth, proj_id, _actor_id = await _setup(client, db_session)
    data = _build_xlsx(
        [
            ["WBS", "Tarea", "Predecessors"],
            ["1", "A", "2"],
            ["2", "B", "1"],
        ]
    )
    files = {
        "file": (
            "ciclo.xlsx",
            data,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    r_prev = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/preview",
        files=files,
        headers=auth["_authz"],
    )
    job_id = r_prev.json()["job_id"]
    r_conf = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/confirm",
        json={"strategy": "replace"},
        headers=auth["_authz"],
    )
    assert r_conf.status_code == 200, r_conf.text
    body = r_conf.json()
    # La primera arista (1←2) entra; la inversa se omite por ciclo.
    assert body["dependencies_created"] == 1
    assert any("ciclo" in str(e).lower() for e in body["errors"])
