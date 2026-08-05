"""BUG-088 — WBS fiel al archivo importado.

Excel guarda "1.30" tipeado en celda numérica como float 1.3; el parser
colapsaba a "1.3" (colisión con el 1.3 real, sub-tareas 1.30.x
huérfanas). Cubre:
- Celda numérica con formato decimal ('0.00') → texto fiel "1.30".
- Celda numérica en General → representación mínima + warning.
- WBS texto preserva mayúsculas (sin lowercasing).
- Detección de huérfanos (padre WBS ausente) en preview.
"""
from __future__ import annotations

import io
import time
from typing import Any

import pytest
from openpyxl import Workbook

from app.services import import_job_store
from app.services.csv_task_parser import parse_csv
from app.services.xlsx_task_parser import _decimal_places, _wbs_text, parse_xlsx
from tests.factories import create_admin_role, create_tenant, create_user, login


def _build_xlsx(
    rows: list[list[Any]], wbs_formats: dict[int, str] | None = None
) -> bytes:
    """Construye un XLSX; `wbs_formats={row_number: fmt}` aplica
    number_format a la celda A de esa fila (1-based, contando header)."""
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    for row_num, fmt in (wbs_formats or {}).items():
        ws.cell(row=row_num, column=1).number_format = fmt
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# --- unit: _decimal_places / _wbs_text ---


def test_decimal_places():
    assert _decimal_places("0.00") == 2
    assert _decimal_places("#,##0.0") == 1
    assert _decimal_places("0") == 0
    assert _decimal_places("General") is None
    assert _decimal_places("@") is None
    assert _decimal_places(None) is None


def test_wbs_text_float_with_format():
    assert _wbs_text(1.3, "0.00") == "1.30"
    assert _wbs_text(1.03, "0.00") == "1.03"
    assert _wbs_text(2.0, "0.00") == "2.00"


def test_wbs_text_float_general():
    assert _wbs_text(1.3, None) == "1.3"
    assert _wbs_text(2.0, None) == "2"
    assert _wbs_text(1.03, "General") == "1.03"


def test_wbs_text_string_preserves_case():
    assert _wbs_text(" 1.A ") == "1.A"
    assert _wbs_text("1.30.1") == "1.30.1"
    assert _wbs_text("") is None
    assert _wbs_text(None) is None


# --- parse_xlsx: fidelidad + warnings ---


def test_parse_xlsx_wbs_decimal_format_preserved():
    """Celda numérica 1.3 con formato '0.00' (el usuario VE '1.30') se
    lee como '1.30' — no colisiona con un 1.3 real y las sub-tareas
    1.30.x mantienen a su padre."""
    data = _build_xlsx(
        [
            ["WBS", "Nombre"],
            [1.3, "Tarea 1.30"],
            ["1.30.1", "Sub A"],
            ["1.30.2", "Sub B"],
        ],
        wbs_formats={2: "0.00"},
    )
    res = parse_xlsx(data)
    assert [t.wbs_code for t in res.tasks] == ["1.30", "1.30.1", "1.30.2"]
    assert res.warnings == []


def test_parse_xlsx_wbs_general_warns():
    """Sin formato decimal el cero es irrecuperable: se lee la
    representación mínima y se emite el warning WBS_NUMERIC_GENERAL."""
    data = _build_xlsx(
        [
            ["WBS", "Nombre"],
            [1.3, "Tarea"],
            [2, "Entera (no warn)"],
        ]
    )
    res = parse_xlsx(data)
    assert [t.wbs_code for t in res.tasks] == ["1.3", "2"]
    codes = [w["code"] for w in res.warnings]
    assert codes == ["WBS_NUMERIC_GENERAL"]
    assert res.warnings[0]["rows"] == [2]


def test_parse_xlsx_wbs_text_not_lowercased():
    data = _build_xlsx([["WBS", "Nombre"], ["1.A", "Alfanumérica"]])
    res = parse_xlsx(data)
    assert res.tasks[0].wbs_code == "1.A"


def test_parse_csv_wbs_preserved():
    csv_data = b"Nombre,WBS\nTarea,1.30\nSub,1.30.1\n"
    res = parse_csv(csv_data)
    assert [t.wbs_code for t in res.tasks] == ["1.30", "1.30.1"]


# --- endpoint preview: warnings de huérfanos ---


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
            "name": "PWBS",
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
async def test_preview_reports_orphans_and_numeric_wbs(client, db_session):
    """El síntoma del reporte del owner: 1.30 numérico colapsa a 1.3 y
    las sub-tareas 1.30.1/1.30.2 quedan huérfanas. El preview lo avisa
    ANTES de confirmar."""
    auth, proj_id = await _setup(client, db_session)
    data = _build_xlsx(
        [
            ["WBS", "Nombre"],
            [1.3, "Línea 1.30 (celda numérica General)"],
            ["1.30.1", "Sub A"],
            ["1.30.2", "Sub B"],
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
    codes = {w["code"] for w in r.json()["warnings"]}
    assert codes == {"WBS_NUMERIC_GENERAL", "WBS_ORPHANS"}
    orphan = next(w for w in r.json()["warnings"] if w["code"] == "WBS_ORPHANS")
    assert orphan["count"] == 2
    assert set(orphan["rows"]) == {"1.30.1", "1.30.2"}
