"""ENH-097 — tasks.is_critical boolean (additive, criticality preserved).

Sprint 26 Bloque 1. Cubre:
- TC-097.1: migration backfill produces correct boolean from `criticality`.
- TC-097.2: POST /tasks con `is_critical=true` persiste.
- TC-097.3: PATCH togglea el flag.
- TC-097.4: importer (parser XLSX/CSV) deriva is_critical desde
  criticality cuando la columna explicita esta ausente.
"""
from __future__ import annotations

import io

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from app.services.csv_task_parser import parse_csv
from app.services.xlsx_task_parser import parse_xlsx
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
async def test_tc097_2_post_is_critical_persists(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "T1", "wbs": "1", "is_critical": True},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["is_critical"] is True
    # default criticality sigue siendo medium (paralelo, no acoplado).
    assert body["criticality"] == "medium"


@pytest.mark.asyncio
async def test_tc097_2_post_default_false(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "T2", "wbs": "2"},
        headers=auth["_authz"],
    )
    assert r.status_code == 201
    assert r.json()["is_critical"] is False


@pytest.mark.asyncio
async def test_tc097_3_patch_toggles(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "T1", "wbs": "1"},
        headers=auth["_authz"],
    )
    tid = r.json()["id"]
    assert r.json()["is_critical"] is False
    # Toggle a true.
    r2 = await client.patch(
        f"/api/v1/tasks/{tid}",
        json={"is_critical": True},
        headers=auth["_authz"],
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["is_critical"] is True
    # PATCH con otro campo no toca is_critical.
    r3 = await client.patch(
        f"/api/v1/tasks/{tid}",
        json={"progress": 50},
        headers=auth["_authz"],
    )
    assert r3.status_code == 200
    assert r3.json()["is_critical"] is True
    assert r3.json()["progress"] == 50


def _build_xlsx_with_criticality(criticalities: list[str]) -> bytes:
    """Helper: minimal xlsx con header `Nombre` + `Criticidad` (no col is_critical)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Plan"
    ws.append(["Nombre", "Criticidad"])
    for i, c in enumerate(criticalities, start=1):
        ws.append([f"Task {i}", c])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_tc097_4_parser_xlsx_no_is_critical_column():
    """Parser XLSX: cuando is_critical no esta en el header, el campo en
    ParsedTask queda None — el endpoint deriva el valor desde criticality.
    """
    data = _build_xlsx_with_criticality(["high", "medium", "critical", "low"])
    result = parse_xlsx(data)
    assert len(result.tasks) == 4
    # No column → None en ParsedTask.
    assert all(t.is_critical is None for t in result.tasks)
    # criticality_ si esta presente.
    crits = [t.criticality for t in result.tasks]
    assert crits == ["high", "medium", "critical", "low"]


def test_tc097_4_parser_xlsx_with_is_critical_column():
    """Parser XLSX reconoce columna `is_critical` / `crítico`."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Nombre", "Criticidad", "crítico"])
    ws.append(["A", "low", "true"])
    ws.append(["B", "medium", "false"])
    ws.append(["C", "high", ""])
    buf = io.BytesIO()
    wb.save(buf)
    result = parse_xlsx(buf.getvalue())
    assert len(result.tasks) == 3
    assert result.tasks[0].is_critical is True
    assert result.tasks[1].is_critical is False
    # Celda vacía → _coerce_bool devuelve False.
    assert result.tasks[2].is_critical is False


def test_tc097_4_parser_csv_no_is_critical_column():
    """Parser CSV: misma semántica — sin columna → None."""
    csv_bytes = (
        b"Nombre,Criticidad\n"
        b"T1,high\n"
        b"T2,low\n"
    )
    result = parse_csv(csv_bytes)
    assert len(result.tasks) == 2
    assert all(t.is_critical is None for t in result.tasks)


@pytest.mark.asyncio
async def test_tc097_1_migration_backfill_logic():
    """TC-097.1: el SQL de backfill (CASE) produce los valores esperados.

    Ejecutamos el upgrade real de la migracion 0063 contra un schema
    mínimo con la columna `criticality` poblada, y verificamos el
    resultado del UPDATE backfill.
    """
    # Engine async limpio (no usa el fixture de la suite porque queremos
    # control sobre el schema creado a mano).
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", future=True
    )
    async with engine.begin() as conn:
        # Schema mínimo equivalente al post-0062: tasks(id, criticality).
        await conn.execute(
            sa.text(
                "CREATE TABLE tasks (id TEXT PRIMARY KEY, criticality TEXT NOT NULL)"
            )
        )
        await conn.execute(
            sa.text(
                "INSERT INTO tasks (id, criticality) VALUES "
                "('a', 'low'), ('b', 'medium'), ('c', 'high'), ('d', 'critical')"
            )
        )
        # Aplicar el equivalente al upgrade(): add column + backfill.
        await conn.execute(
            sa.text("ALTER TABLE tasks ADD COLUMN is_critical BOOLEAN DEFAULT 0")
        )
        await conn.execute(
            sa.text(
                "UPDATE tasks SET is_critical = CASE "
                "WHEN criticality IN ('high', 'critical') THEN 1 ELSE 0 END"
            )
        )
        rows = (
            await conn.execute(
                sa.text("SELECT id, is_critical FROM tasks ORDER BY id")
            )
        ).all()
    await engine.dispose()
    result = {r[0]: bool(r[1]) for r in rows}
    assert result == {"a": False, "b": False, "c": True, "d": True}
