"""US-180 — Salud única híbrida (reemplaza ENH-101 status_rag).

Cubre:
- TC-180-1: default = green/auto, sin razón.
- TC-180-2: declarar amarillo/rojo sin razón → 422; con razón persiste.
- TC-180-3: declarar verde sin razón es válido.
- TC-180-4: volver a 'auto' recalcula y limpia razón.
- TC-180-5: PATCH genérico con health_status = declaración manual + audit.
- TC-180-6: health-detail con hito vencido → cronograma rojo y el
  semáforo auto persistido se refresca.
- TC-180-7: override manual NO es sobreescrito por el motor (computed
  se reporta aparte).
- TC-180-8: decisión pendiente vieja → dimensión decisiones amarilla.
- TC-180-9: riesgo severo → dimensión riesgos amarilla; presupuesto
  ≥90% → dimensión presupuesto amarilla; foco PM trae causas.
"""
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.modules import Issue, Risk
from app.models.task import Task
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup_project(client, db_session) -> tuple[dict, str, str]:
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    body = {
        "name": "Proyecto Salud",
        "description": "US-180",
        "type": "innovation",
        "priority": 3,
        "organization_id": org_id,
        "pm_id": pm_id,
    }
    p = await client.post("/api/v1/projects", json=body, headers=auth["_authz"])
    assert p.status_code == 201, p.text
    return auth, p.json()["id"], str(t.id)


@pytest.mark.asyncio
async def test_us180_default_green_auto(client, db_session):
    auth, pid, _ = await _setup_project(client, db_session)
    r = await client.get(f"/api/v1/projects/{pid}", headers=auth["_authz"])
    assert r.status_code == 200
    body = r.json()
    assert body["health_status"] == "green"
    assert body["health_source"] == "auto"
    assert body["health_reason"] is None
    assert "status_rag" not in body


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["yellow", "red"])
async def test_us180_declare_requires_reason(client, db_session, value):
    auth, pid, _ = await _setup_project(client, db_session)
    r = await client.patch(
        f"/api/v1/projects/{pid}/health", json={"status": value}, headers=auth["_authz"]
    )
    # validation_error() del app devuelve 400 VALIDATION_ERROR.
    assert r.status_code == 400

    r = await client.patch(
        f"/api/v1/projects/{pid}/health",
        json={"status": value, "reason": "Retraso del proveedor de infraestructura"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["health_status"] == value
    assert body["health_source"] == "manual"
    assert "proveedor" in body["health_reason"]


@pytest.mark.asyncio
async def test_us180_declare_green_without_reason(client, db_session):
    auth, pid, _ = await _setup_project(client, db_session)
    r = await client.patch(
        f"/api/v1/projects/{pid}/health", json={"status": "green"}, headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["health_source"] == "manual"


@pytest.mark.asyncio
async def test_us180_back_to_auto_recomputes(client, db_session):
    auth, pid, _ = await _setup_project(client, db_session)
    await client.patch(
        f"/api/v1/projects/{pid}/health",
        json={"status": "red", "reason": "Bloqueo mayor de alcance"},
        headers=auth["_authz"],
    )
    # Proyecto vacío: el recálculo automático debe regresar a verde.
    r = await client.patch(
        f"/api/v1/projects/{pid}/health", json={"status": None}, headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["health_source"] == "auto"
    assert body["health_status"] == "green"
    assert body["health_reason"] is None


@pytest.mark.asyncio
async def test_us180_generic_patch_declares_manual(client, db_session):
    auth, pid, _ = await _setup_project(client, db_session)
    r = await client.patch(
        f"/api/v1/projects/{pid}", json={"health_status": "yellow"}, headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["health_source"] == "manual"
    rows = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "project.health.declared",
                AuditLog.entity_id == pid,
            )
        )
    ).scalars().all()
    assert len(rows) >= 1
    assert rows[-1].details.get("after") == "yellow"


@pytest.mark.asyncio
async def test_us180_overdue_milestone_turns_red_and_persists(client, db_session):
    auth, pid, tid = await _setup_project(client, db_session)
    db_session.add(
        Task(
            tenant_id=tid, project_id=pid, name="Hito kickoff",
            status="in_progress", is_milestone=True,
            end_date=date.today() - timedelta(days=10),
        )
    )
    await db_session.commit()

    r = await client.get(f"/api/v1/projects/{pid}/health-detail", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    body = r.json()
    schedule = next(d for d in body["dimensions"] if d["key"] == "schedule")
    # 1 tarea abierta, 1 atrasada (100% ≥ 25) → rojo.
    assert schedule["color"] == "red"
    assert schedule["causes"][0]["what"] == "Hito kickoff"
    assert body["computed"] == "red"
    # El semáforo auto persistido se refrescó.
    assert body["health_status"] == "red"
    g = await client.get(f"/api/v1/projects/{pid}", headers=auth["_authz"])
    assert g.json()["health_status"] == "red"
    # Recursos sigue N/A (hook US-183).
    resources = next(d for d in body["dimensions"] if d["key"] == "resources")
    assert resources["color"] is None


@pytest.mark.asyncio
async def test_us180_manual_override_not_overwritten(client, db_session):
    auth, pid, tid = await _setup_project(client, db_session)
    db_session.add(
        Task(
            tenant_id=tid, project_id=pid, name="Hito vencido",
            status="in_progress", is_milestone=True,
            end_date=date.today() - timedelta(days=5),
        )
    )
    await db_session.commit()
    await client.patch(
        f"/api/v1/projects/{pid}/health",
        json={"status": "yellow", "reason": "Mitigación en curso con el sponsor"},
        headers=auth["_authz"],
    )
    r = await client.get(f"/api/v1/projects/{pid}/health-detail", headers=auth["_authz"])
    body = r.json()
    assert body["health_status"] == "yellow"  # manda el override
    assert body["health_source"] == "manual"
    assert body["computed"] == "red"  # el cálculo se reporta aparte


@pytest.mark.asyncio
async def test_us180_stale_decision_yellow(client, db_session):
    auth, pid, tid = await _setup_project(client, db_session)
    db_session.add(
        Issue(
            tenant_id=tid, project_id=pid, folio="AID-0001",
            title="Definir estrategia de rollout", status="open", type="decision",
            reported_at=datetime.now(UTC) - timedelta(days=30),
        )
    )
    await db_session.commit()
    r = await client.get(f"/api/v1/projects/{pid}/health-detail", headers=auth["_authz"])
    body = r.json()
    decisions = next(d for d in body["dimensions"] if d["key"] == "decisions")
    assert decisions["color"] == "yellow"
    assert decisions["causes"][0]["what"] == "Definir estrategia de rollout"
    assert body["computed"] == "yellow"


@pytest.mark.asyncio
async def test_us180_severe_risk_budget_and_focus(client, db_session):
    auth, pid, tid = await _setup_project(client, db_session)
    db_session.add(
        Risk(
            tenant_id=tid, project_id=pid, folio="R-0001",
            title="Dependencia de un solo arquitecto", status="open",
            probability=4, impact=4, severity=16,
        )
    )
    await db_session.commit()
    await client.patch(
        f"/api/v1/projects/{pid}",
        json={"budget": "100000", "actual_budget": "95000"},
        headers=auth["_authz"],
    )
    r = await client.get(f"/api/v1/projects/{pid}/health-detail", headers=auth["_authz"])
    body = r.json()
    risks = next(d for d in body["dimensions"] if d["key"] == "risks")
    assert risks["color"] == "yellow"
    assert risks["metrics"]["severe_risks"] == 1
    budget = next(d for d in body["dimensions"] if d["key"] == "budget")
    assert budget["color"] == "yellow"
    # Foco PM: al menos el riesgo severo con acción sugerida.
    assert any(f["type"] == "severe_risk" for f in body["focus"])
    focus_risk = next(f for f in body["focus"] if f["type"] == "severe_risk")
    assert focus_risk["suggested_action"]
    assert focus_risk["dimension_label"] == "Riesgos / Issues"
