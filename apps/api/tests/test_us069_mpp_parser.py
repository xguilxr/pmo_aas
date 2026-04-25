"""US-069 — Import MPP nativo vía MPXJ (subprocess Java).

Los tests unitarios mockean `subprocess.run` para probar el mapeo JSON →
`ParsedTask` sin depender de una JVM + jar de MPXJ. El contrato con el
endpoint se cubre con un test de integración que stubbea el parser.

TC-069.1 — fixture .mpp pequeño parseado a ParsedTask (mock subprocess).
TC-069.2 — .mpp corrupto → 422 en endpoint, no 500.
TC-069.3 — subprocess timeout → ValueError claro, no hang.
TC-069.4 — smoke: Java disponible + MpxjCli carga (skipped si no JRE).
TC-069.5 — contrato: parse_mpp devuelve mismo shape que parse_xlsx.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import date

import pytest

from app.services.msproject import mpp_parser
from app.services.msproject.mpp_parser import parse_mpp
from app.services.xlsx_task_parser import ParsedTask, XlsxParseResult
from tests.factories import create_admin_role, create_tenant, create_user, login

CANNED_OK_JSON = json.dumps(
    {
        "tasks": [
            {
                "row_number": 2,
                "name": "Analisis",
                "wbs": "1",
                "start_date": "2026-01-01",
                "end_date": "2026-01-10",
                "duration_days": 10,
                "progress": 50,
                "is_milestone": False,
                "predecessors_raw": None,
                "resources_raw": "Juan, Maria",
            },
            {
                "row_number": 3,
                "name": "Desarrollo",
                "wbs": "2",
                "start_date": "2026-01-11",
                "end_date": "2026-02-10",
                "duration_days": 31,
                "progress": 10,
                "is_milestone": False,
                "predecessors_raw": "1",
                "resources_raw": None,
            },
            {
                "row_number": 4,
                "name": "Go-Live",
                "wbs": None,
                "start_date": "2026-02-11",
                "end_date": "2026-02-11",
                "duration_days": None,
                "progress": 0,
                "is_milestone": True,
                "predecessors_raw": "2",
                "resources_raw": None,
            },
        ]
    }
).encode()


def _fake_run_factory(
    *,
    payload: bytes | None = None,
    stderr: bytes = b"",
    returncode: int = 0,
):
    """Factoría de stubs para `subprocess.run`. Si `payload` viene, lo
    escribe al `output_path` (último arg del comando) emulando lo que
    hace el wrapper Java real (post fix 2026-04-25). Devuelve
    `CompletedProcess` con stdout vacío — el contrato ya no lo usa.
    """

    def _fake(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        if payload is not None and len(cmd) >= 6:
            output_path = cmd[5]
            with open(output_path, "wb") as f:
                f.write(payload)
        return subprocess.CompletedProcess(
            args=cmd, returncode=returncode, stdout=b"", stderr=stderr
        )

    return _fake


# TC-069.1 — happy path: JSON del CLI se mapea a ParsedTask.
def test_tc069_1_parses_tasks_from_cli_output(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/java")
    monkeypatch.setattr(
        mpp_parser.subprocess,
        "run",
        _fake_run_factory(payload=CANNED_OK_JSON),
    )
    result = parse_mpp(b"\x00FAKE_MPP_BYTES\x00")
    assert isinstance(result, XlsxParseResult)
    assert len(result.tasks) == 3
    assert result.errors == []

    t0, t1, t2 = result.tasks
    assert t0.name == "Analisis"
    assert t0.wbs == "1"
    assert t0.start_date == date(2026, 1, 1)
    assert t0.end_date == date(2026, 1, 10)
    assert t0.duration_days == 10
    assert t0.progress == 50
    assert t0.is_milestone is False
    assert t0.resources_raw == "Juan, Maria"

    assert t1.predecessors_raw == "1"
    assert t2.is_milestone is True
    assert t2.duration_days is None


# TC-069.2 — CLI returncode != 0 → ValueError acotado (no 500 luego).
def test_tc069_2_corrupt_file_raises_value_error(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/java")
    monkeypatch.setattr(
        mpp_parser.subprocess,
        "run",
        _fake_run_factory(stderr=b"unsupported format", returncode=2),
    )
    with pytest.raises(ValueError, match=r"corrupto|no soportada"):
        parse_mpp(b"garbage")


# TC-069.3 — TimeoutExpired → ValueError con mensaje de timeout.
def test_tc069_3_timeout_raises_value_error(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/java")

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=5)

    monkeypatch.setattr(mpp_parser.subprocess, "run", _raise_timeout)
    monkeypatch.setenv("MPP_PARSE_TIMEOUT_SECONDS", "5")
    with pytest.raises(ValueError, match="timeout"):
        parse_mpp(b"\x00")


# TC-069.3b — Java ausente en el PATH → ValueError explícito.
def test_tc069_3b_java_missing_raises_value_error(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(ValueError, match="Java runtime"):
        parse_mpp(b"\x00")


# TC-069.3c — archivo vacío.
def test_tc069_3c_empty_file_raises():
    with pytest.raises(ValueError, match="vacío"):
        parse_mpp(b"")


# TC-069.4 — smoke del JRE + MpxjCli (integration). Skipped si el
# contenedor no tiene Java (local dev). En CI corre en la imagen Docker.
@pytest.mark.skipif(
    shutil.which("java") is None or not os.path.exists("/opt/mpxj/cli"),
    reason="JRE/MPXJ no disponibles en este entorno (integración Docker).",
)
def test_tc069_4_mpxj_cli_smoke():
    cp = subprocess.run(
        ["java", "-cp", mpp_parser.DEFAULT_CLI_CP, "MpxjCli"],
        capture_output=True,
        timeout=10,
    )
    # Sin args, devuelve usage + exit 2 — prueba que la clase se resolvió.
    assert cp.returncode == 2
    assert b"usage" in cp.stderr.lower() or b"MpxjCli" in cp.stderr


# TC-069.5 — contrato: parse_mpp y parse_xlsx devuelven el mismo shape
# (XlsxParseResult con tasks:list[ParsedTask]).
def test_tc069_5_same_shape_as_xlsx(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/java")
    monkeypatch.setattr(
        mpp_parser.subprocess,
        "run",
        _fake_run_factory(payload=CANNED_OK_JSON),
    )
    mpp_result = parse_mpp(b"\x00")
    assert type(mpp_result) is XlsxParseResult
    for t in mpp_result.tasks:
        assert type(t) is ParsedTask
        for attr in (
            "row_number",
            "name",
            "wbs",
            "start_date",
            "end_date",
            "duration_days",
            "progress",
            "is_milestone",
            "predecessors_raw",
            "resources_raw",
        ):
            assert hasattr(t, attr), f"ParsedTask sin atributo {attr}"


# TC-069.6 — CLI devuelve proyecto vacío (solo root filtrado) → ValueError.
def test_tc069_6_empty_project_raises(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/java")
    monkeypatch.setattr(
        mpp_parser.subprocess,
        "run",
        _fake_run_factory(payload=b'{"tasks":[]}'),
    )
    with pytest.raises(ValueError, match="no contiene tareas"):
        parse_mpp(b"\x00")


# --- Integration: endpoint /tasks/import con .mpp ---


async def _setup_project(client, db_session):
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
            "name": "PMSP",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return auth, p.json()["id"]


# TC-069.7 — endpoint detecta .mpp y delega al parser; source=mpp.
@pytest.mark.asyncio
async def test_tc069_7_endpoint_accepts_mpp(client, db_session, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/java")
    monkeypatch.setattr(
        "app.services.msproject.mpp_parser.subprocess.run",
        _fake_run_factory(payload=CANNED_OK_JSON),
    )
    auth, proj_id = await _setup_project(client, db_session)
    files = {"file": ("plan.mpp", b"\x00MPP_BINARY", "application/vnd.ms-project")}
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import",
        files=files,
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported"] == 3
    assert body["source"] == "mpp"


# TC-069.8 — endpoint traduce error del parser a 422, no 500.
@pytest.mark.asyncio
async def test_tc069_8_corrupt_mpp_returns_422(client, db_session, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/java")
    monkeypatch.setattr(
        "app.services.msproject.mpp_parser.subprocess.run",
        _fake_run_factory(stderr=b"boom", returncode=2),
    )
    auth, proj_id = await _setup_project(client, db_session)
    files = {"file": ("bad.mpp", b"garbage", "application/vnd.ms-project")}
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/import",
        files=files,
        headers=auth["_authz"],
    )
    assert r.status_code == 422
