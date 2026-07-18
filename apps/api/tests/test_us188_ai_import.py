"""US-188 — Import inteligente de planes con IA (3 niveles).

Todo mockeado a nivel `generate_for_tenant` (sin llamadas reales):
- Nivel 2: normalización de estados libres + match de responsables.
- Nivel 3: propuesta de estructura desde filas crudas + confirm con
  `use_ai_structure` + gating por tenant.ai_mode.
"""
from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Any

import pytest
from openpyxl import Workbook
from sqlalchemy import select

from app.models.task import Task
from app.services import import_ai, import_job_store
from app.services.ai.tenant_ai import TenantAIConfig
from app.services.import_ai import (
    ai_normalize_statuses,
    ai_propose_structure,
    extract_raw_rows,
)
from tests.factories import create_admin_role, create_tenant, create_user, login


@dataclass
class _FakeAIResult:
    text: str


def _patch_llm(monkeypatch, response_text: str):
    async def _fake_generate(prompt, **kwargs):
        return _FakeAIResult(text=response_text)

    monkeypatch.setattr(import_ai, "generate_for_tenant", _fake_generate)


_CFG = TenantAIConfig(mode="platform")


# --- Nivel 2: normalización de valores ---


@pytest.mark.asyncio
async def test_ai_normalize_statuses(monkeypatch):
    _patch_llm(
        monkeypatch,
        '{"casi lista": "in_progress", "80% done": "in_progress", '
        '"quién sabe": null, "inventado": "otra_cosa"}',
    )
    out = await ai_normalize_statuses(
        ["casi lista", "80% done", "quién sabe", "inventado"], tenant_cfg=_CFG
    )
    # Solo valores del enum; null y valores inválidos se descartan.
    assert out == {"casi lista": "in_progress", "80% done": "in_progress"}


@pytest.mark.asyncio
async def test_ai_normalize_disabled_returns_empty(monkeypatch):
    _patch_llm(monkeypatch, '{"x": "completed"}')
    out = await ai_normalize_statuses(
        ["x"], tenant_cfg=TenantAIConfig(mode="disabled")
    )
    assert out == {}


@pytest.mark.asyncio
async def test_ai_normalize_llm_failure_is_silent(monkeypatch):
    async def _boom(prompt, **kwargs):
        raise RuntimeError("provider caído")

    monkeypatch.setattr(import_ai, "generate_for_tenant", _boom)
    out = await ai_normalize_statuses(["x"], tenant_cfg=_CFG)
    assert out == {}


# --- Nivel 3: estructura ---


@pytest.mark.asyncio
async def test_ai_propose_structure_validates(monkeypatch):
    _patch_llm(
        monkeypatch,
        """[
          {"wbs": "1", "name": "Fase 1", "start_date": "2026-01-05",
           "end_date": "2026-01-30", "progress": 0.45,
           "status": "in_progress", "is_milestone": false},
          {"wbs": "1.30", "name": "Sub", "progress": 80, "status": "Completada"},
          {"name": ""},
          "basura"
        ]""",
    )
    tasks = await ai_propose_structure([["algo"]], tenant_cfg=_CFG)
    assert len(tasks) == 2
    assert tasks[0].wbs == "1"
    assert tasks[0].progress == 45  # fracción 0.45 → 45
    assert tasks[0].status == "in_progress"
    assert tasks[1].wbs == "1.30"  # WBS preservado como texto
    assert tasks[1].progress == 80
    assert tasks[1].status == "completed"  # label ES normalizado


def test_extract_raw_rows_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.append(["PLAN PROYECTO X", None])
    ws.append(["Actividad", "Cuando"])
    ws.append(["Kickoff", "enero"])
    buf = io.BytesIO()
    wb.save(buf)
    rows = extract_raw_rows("xlsx", buf.getvalue())
    assert rows[0][0] == "PLAN PROYECTO X"
    assert rows[2] == ["Kickoff", "enero"]


# --- Endpoint ai-structure + confirm use_ai_structure ---


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
            "name": "P188",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return auth, p.json()["id"]


# Archivo "sucio": sin headers reconocibles.
DIRTY_ROWS = [
    ["CRONOGRAMA PROYECTO X", None, None],
    ["Preparación", None, None],
    ["  Kickoff", "05/01", "listo"],
    ["  Análisis", "12/01", "en curso"],
]


async def _preview(client, auth, proj_id):
    files = {
        "file": (
            "sucio.xlsx",
            _build_xlsx(DIRTY_ROWS),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/preview",
        files=files,
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    return r.json()["job_id"]


@pytest.mark.asyncio
async def test_ai_structure_gated_by_tenant_mode(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    job_id = await _preview(client, auth, proj_id)
    # Tenant default: ai_mode disabled → 422 AI_DISABLED.
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/ai-structure",
        headers=auth["_authz"],
    )
    assert r.status_code == 422
    assert "AI_DISABLED" in r.text


@pytest.mark.asyncio
async def test_ai_structure_flow_and_confirm(client, db_session, monkeypatch):
    from app.api.v1.endpoints import tasks as tasks_ep

    auth, proj_id = await _setup(client, db_session)
    job_id = await _preview(client, auth, proj_id)

    async def _fake_load_tenant_ai(db, tenant_id):
        return _CFG

    monkeypatch.setattr(tasks_ep, "load_tenant_ai", _fake_load_tenant_ai)
    _patch_llm(
        monkeypatch,
        """[
          {"wbs": "1", "name": "Preparación", "is_milestone": false},
          {"wbs": "1.1", "name": "Kickoff", "start_date": "2026-01-05",
           "status": "completed", "progress": 100},
          {"wbs": "1.2", "name": "Análisis", "start_date": "2026-01-12",
           "status": "in_progress", "progress": 30}
        ]""",
    )

    r_ai = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/ai-structure",
        headers=auth["_authz"],
    )
    assert r_ai.status_code == 200, r_ai.text
    body = r_ai.json()
    assert body["task_count"] == 3
    assert [t["wbs"] for t in body["parsed_preview"]] == ["1", "1.1", "1.2"]

    # Confirm persistiendo la propuesta IA.
    r_conf = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/confirm",
        json={"strategy": "replace", "use_ai_structure": True},
        headers=auth["_authz"],
    )
    assert r_conf.status_code == 200, r_conf.text
    assert r_conf.json()["imported"] == 3

    tasks = (
        (await db_session.execute(select(Task).where(Task.project_id == proj_id)))
        .scalars()
        .all()
    )
    by_wbs = {t.wbs: t for t in tasks}
    assert by_wbs["1.1"].status == "completed"
    assert by_wbs["1.2"].progress == 30
    assert by_wbs["1.2"].outline_level == 2


@pytest.mark.asyncio
async def test_confirm_use_ai_structure_without_proposal_422(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    job_id = await _preview(client, auth, proj_id)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/confirm",
        json={"strategy": "replace", "use_ai_structure": True},
        headers=auth["_authz"],
    )
    assert r.status_code == 422
    assert "AI_STRUCTURE_MISSING" in r.text
