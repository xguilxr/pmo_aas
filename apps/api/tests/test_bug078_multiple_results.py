"""BUG-078 — `scalar_one_or_none()` reventaba con `MultipleResultsFound` al
subir planes / documentos cuando ya existían filas duplicadas en BD (sin
unique constraint que las cubra). El 500 salía sin headers CORS, así que el
front lo mostraba como "No se pudo conectar con el servidor".

Cubre:
- Import de plan (merge) con tasks existentes que comparten `external_id`.
- Subida de documento con >1 versión vigente (`is_current`) del mismo
  `(title, category)`.
"""
from __future__ import annotations

import io
import time

import pytest
from openpyxl import Workbook
from sqlalchemy import select

from app.models.modules import Document
from app.models.task import Task
from app.services import import_job_store
from tests.factories import create_admin_role, create_tenant, create_user, login


class _FakeRedis:
    """Stub mínimo de redis para `import_job_store` (igual que test_us070)."""

    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}

    def set(self, key, value, ex=None):
        expiry = time.monotonic() + ex if ex else float("inf")
        self._store[key] = (value, expiry)

    def get(self, key):
        row = self._store.get(key)
        if row is None:
            return None
        value, expiry = row
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return value

    def delete(self, key):
        return int(bool(self._store.pop(key, None)))


@pytest.fixture(autouse=True)
def _stub_redis(monkeypatch):
    fake = _FakeRedis()  # una sola instancia: preview y confirm comparten store.
    monkeypatch.setattr(import_job_store, "_get_client", lambda: fake)
    yield


def _build_xlsx(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Plan"
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


HEADERS = ["Nombre", "WBS", "Inicio", "Fin", "Duración", "% completado"]
ROWS = [
    HEADERS,
    ["Analisis", "1", "2026-01-01", "2026-01-10", 10, 50],
    ["Desarrollo", "2", "2026-01-11", "2026-02-10", 31, 10],
]


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin",
        email="admin@acme.example.com", password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    org = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={"name": "PMSP", "description": "d", "type": "bau", "priority": 3,
              "organization_id": org.json()["id"], "pm_id": me.json()["id"]},
        headers=auth["_authz"],
    )
    return auth, p.json()["id"], t.id


@pytest.mark.asyncio
async def test_bug078_merge_import_with_duplicate_external_id(client, db_session):
    """Con >1 Task con el mismo (project_id, external_id), el confirm en modo
    merge antes reventaba con MultipleResultsFound (500). Ahora actualiza la
    primera y termina OK."""
    auth, proj_id, tenant_id = await _setup(client, db_session)

    # Sembramos 2 tasks con el MISMO external_id "1" — situación que se da con
    # WBS duplicados o imports previos; no hay unique constraint que la impida.
    for i in range(2):
        db_session.add(Task(
            tenant_id=str(tenant_id), project_id=str(proj_id),
            name=f"dup-{i}", wbs="1", external_id="1",
            status="not_started", source="manual",
        ))
    await db_session.commit()

    data = _build_xlsx(ROWS)
    files = {"file": ("plan.xlsx", data,
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r_prev = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/preview",
        files=files, headers=auth["_authz"],
    )
    assert r_prev.status_code == 200, r_prev.text
    job_id = r_prev.json()["job_id"]

    r_conf = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import/{job_id}/confirm",
        json={"strategy": "merge"}, headers=auth["_authz"],
    )
    # Antes del fix: 500 (MultipleResultsFound). Ahora: 200.
    assert r_conf.status_code == 200, r_conf.text
    assert r_conf.json()["imported"] == 2


@pytest.mark.asyncio
async def test_bug078_document_upload_with_duplicate_current(client, db_session):
    """Con >1 Document is_current del mismo (title, category), subir una
    versión nueva antes reventaba con MultipleResultsFound. Ahora desmarca
    todas las vigentes y versiona desde el máximo."""
    auth, proj_id, tenant_id = await _setup(client, db_session)

    for i in range(2):
        db_session.add(Document(
            tenant_id=str(tenant_id), project_id=str(proj_id),
            folio=f"DOC-DUP-{i}", title="Acta", category="other",
            file_url="http://x/y.pdf", mime_type="application/pdf",
            size_bytes=10, version=1, is_current=True, status="active",
        ))
    await db_session.commit()

    r = await client.post(
        f"/api/v1/projects/{proj_id}/documents",
        json={"title": "Acta", "category": "other",
              "file_url": "http://x/z.pdf", "mime_type": "application/pdf",
              "size_bytes": 20},
        headers=auth["_authz"],
    )
    # Antes del fix: 500 (MultipleResultsFound). Ahora: 201.
    assert r.status_code == 201, r.text
    assert r.json()["version"] == 2  # max(1, 1) + 1
    assert r.json()["is_current"] is True

    # Las 2 versiones previas quedaron desmarcadas → solo 1 vigente.
    db_session.expire_all()
    current = (
        await db_session.execute(
            select(Document).where(
                Document.project_id == str(proj_id),
                Document.title == "Acta",
                Document.is_current.is_(True),
            )
        )
    ).scalars().all()
    assert len(current) == 1
