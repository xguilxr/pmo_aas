"""US-185 — Memoria de proyecto para IA.

Cubre:
- TC-185-1: GET sin memoria devuelve shape vacío (no 404).
- TC-185-2: PUT upsert de context/instructions + audit.
- TC-185-3: PUT puede podar el resumen automático (y sella timestamp).
- TC-185-4: compose_context_block — prioridades, truncado y casos None.
- TC-185-5: load_context_block incluye descripción del proyecto aun sin
  memoria capturada (fix: antes la descripción no llegaba al LLM).
"""
import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.services.ai.project_context import (
    compose_context_block,
    load_context_block,
)
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup_project(client, db_session):
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
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto Memoria", "description": "Implementación ERP Wave 2",
            "type": "transformation", "priority": 3,
            "organization_id": org_id, "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return auth, p.json()["id"], str(t.id)


@pytest.mark.asyncio
async def test_us185_get_empty_shape(client, db_session):
    auth, pid, _ = await _setup_project(client, db_session)
    r = await client.get(f"/api/v1/projects/{pid}/ai-context", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["context_md"] is None
    assert body["instructions_md"] is None
    assert body["auto_summary_md"] is None


@pytest.mark.asyncio
async def test_us185_put_upsert_and_audit(client, db_session):
    auth, pid, _ = await _setup_project(client, db_session)
    r = await client.put(
        f"/api/v1/projects/{pid}/ai-context",
        json={
            "context_md": "Glosario: DBS = Danone Business Services.",
            "instructions_md": "Siempre en español formal; destacar decisiones.",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "DBS" in body["context_md"]
    assert "formal" in body["instructions_md"]

    g = await client.get(f"/api/v1/projects/{pid}/ai-context", headers=auth["_authz"])
    assert g.json()["context_md"] == body["context_md"]

    rows = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "project.ai_context.updated",
                AuditLog.entity_id == pid,
            )
        )
    ).scalars().all()
    assert len(rows) >= 1
    assert "context_md" in rows[-1].details.get("fields", [])


@pytest.mark.asyncio
async def test_us185_put_prunes_auto_summary(client, db_session):
    auth, pid, _ = await _setup_project(client, db_session)
    await client.put(
        f"/api/v1/projects/{pid}/ai-context",
        json={"auto_summary_md": "## Decisiones\n- Se aprobó blueprint."},
        headers=auth["_authz"],
    )
    r = await client.put(
        f"/api/v1/projects/{pid}/ai-context",
        json={"auto_summary_md": "## Decisiones\n- (podado por el PM)"},
        headers=auth["_authz"],
    )
    body = r.json()
    assert "podado" in body["auto_summary_md"]
    assert body["auto_summary_updated_at"] is not None


def test_us185_compose_block_priorities_and_truncation():
    # Sin nada que inyectar → None.
    assert compose_context_block() is None
    # Solo nombre sin memoria ni descripción → None (no aporta).
    assert compose_context_block(project_name="X") is None
    # Con memoria: bloque con tags y secciones en orden.
    block = compose_context_block(
        project_name="ERP",
        project_description="Wave 2",
        context_md="Reglas de negocio",
        instructions_md="Tono ejecutivo",
        auto_summary_md="Resumen previo",
    )
    assert block.startswith("<CONTEXTO_DEL_PROYECTO>")
    assert block.endswith("</CONTEXTO_DEL_PROYECTO>")
    assert block.index("Instrucciones permanentes") < block.index("Reglas de negocio")
    assert "Resumen acumulado" in block
    # Truncado: max_chars chico corta el resumen, no las instrucciones.
    small = compose_context_block(
        instructions_md="I" * 400,
        context_md="C" * 400,
        auto_summary_md="S" * 5000,
        max_chars=1200,
    )
    assert len(small) <= 1600  # margen por headers/tags
    assert "I" * 100 in small


@pytest.mark.asyncio
async def test_us185_load_block_includes_description(client, db_session):
    auth, pid, tid = await _setup_project(client, db_session)
    # Sin memoria: el bloque igual lleva la descripción del proyecto.
    block = await load_context_block(db_session, tid, pid)
    assert block is not None
    assert "Implementación ERP Wave 2" in block
    # Con memoria: se suma el contexto curado.
    await client.put(
        f"/api/v1/projects/{pid}/ai-context",
        json={"context_md": "SPOC de finanzas: Eli Gomora."},
        headers=auth["_authz"],
    )
    block = await load_context_block(db_session, tid, pid)
    assert "Eli Gomora" in block
