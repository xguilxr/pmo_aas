"""EP003 — Project Requests tests."""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    # crear org para usar en requests
    r = await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    return t, auth, org_id


def _request_body(org_id: str, **overrides) -> dict:
    base = {
        "title": "Nuevo CRM",
        "description": "Implementar CRM",
        "objective": "Aumentar ventas",
        "organization_id": org_id,
        "business_unit": "Sales",
        "department": "Ventas",
        "sponsor": "CMO",
        "sponsor_email": "cmo@acme.example.com",
        "benefits": "Mejor conversión",
        "budget": "1000000.00",
        "scope": "Nacional México",
    }
    base.update(overrides)
    return base


# TC-043
@pytest.mark.asyncio
async def test_tc043_create_request_happy_path(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["folio"].startswith("SOL-")
    assert body["folio"].endswith("-001")
    assert body["status"] == "in_review"


# TC-047 filter by status
@pytest.mark.asyncio
async def test_tc047_filter_by_status(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r1 = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    assert r1.status_code == 201
    r2 = await client.get("/api/v1/project-requests?status=in_review", headers=auth["_authz"])
    assert r2.status_code == 200
    assert any(x["folio"] == r1.json()["folio"] for x in r2.json())
    r3 = await client.get("/api/v1/project-requests?status=approved", headers=auth["_authz"])
    assert all(x["status"] == "approved" for x in r3.json())


# TC-049 reject without comment
@pytest.mark.asyncio
async def test_tc049_reject_without_comment(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    rev = await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "reject"},
        headers=auth["_authz"],
    )
    assert rev.status_code == 400


# TC-050 approve already approved → 409
@pytest.mark.asyncio
async def test_tc050_double_approve(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    a1 = await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    assert a1.status_code == 200
    a2 = await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    assert a2.status_code == 409
    assert a2.json()["detail"]["code"] == "STATE_TRANSITION"


# TC-051 needs_info -> edit -> resubmit
@pytest.mark.asyncio
async def test_tc051_needs_info_resubmit(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    need = await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "needs_info", "comment": "Falta alcance"},
        headers=auth["_authz"],
    )
    assert need.status_code == 200
    assert need.json()["status"] == "needs_info"
    ed = await client.patch(
        f"/api/v1/project-requests/{req_id}",
        json={"scope": "MX + LATAM"},
        headers=auth["_authz"],
    )
    assert ed.status_code == 200
    rs = await client.post(f"/api/v1/project-requests/{req_id}/resubmit", headers=auth["_authz"])
    assert rs.status_code == 200
    assert rs.json()["status"] == "in_review"


# TC-052 create project from approved
@pytest.mark.asyncio
async def test_tc052_create_project_from_request(client, db_session):
    t, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    # obtener el admin user id
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    cp = await client.post(
        f"/api/v1/project-requests/{req_id}/create-project",
        json={"pm_id": pm_id},
        headers=auth["_authz"],
    )
    assert cp.status_code == 200, cp.text
    body = cp.json()
    assert body["folio"].startswith("PRJ-")
    assert not body["idempotent"]


# TC-053 create project from in_review
@pytest.mark.asyncio
async def test_tc053_create_project_from_in_review(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    cp = await client.post(
        f"/api/v1/project-requests/{req_id}/create-project",
        json={"pm_id": me.json()["id"]},
        headers=auth["_authz"],
    )
    assert cp.status_code == 422


# TC-054 idempotency
@pytest.mark.asyncio
async def test_tc054_create_project_idempotent(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    a = await client.post(
        f"/api/v1/project-requests/{req_id}/create-project",
        json={"pm_id": pm_id},
        headers=auth["_authz"],
    )
    b = await client.post(
        f"/api/v1/project-requests/{req_id}/create-project",
        json={"pm_id": pm_id},
        headers=auth["_authz"],
    )
    assert a.json()["project_id"] == b.json()["project_id"]
    assert b.json()["idempotent"] is True


# TC-055 cannot edit approved
@pytest.mark.asyncio
async def test_tc055_cannot_edit_approved(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    ed = await client.patch(
        f"/api/v1/project-requests/{req_id}",
        json={"title": "Other"},
        headers=auth["_authz"],
    )
    assert ed.status_code == 409


# ============================================================================
# US-011 — Campos adicionales en solicitud
# ============================================================================


# Full payload con nuevos campos
@pytest.mark.asyncio
async def test_us011_full_payload(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    body = _request_body(
        org_id,
        key_people="Juan (líder), María (PM)",
        if_not_done="Pérdida de clientes",
        observations="Revisar a 6 meses",
        entregables="Módulo CRM integrado a ERP",
        requester_name="Requester Custom",
        requester_email="req@acme.example.com",
    )
    r = await client.post("/api/v1/project-requests", json=body, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["entregables"] == "Módulo CRM integrado a ERP"
    assert data["key_people"] == "Juan (líder), María (PM)"
    assert data["if_not_done"] == "Pérdida de clientes"
    assert data["observations"] == "Revisar a 6 meses"
    assert data["requester_name"] == "Requester Custom"
    assert data["requester_email"] == "req@acme.example.com"
    assert data["sponsor_email"] == "cmo@acme.example.com"


# sponsor_email es obligatorio y debe ser email válido
@pytest.mark.asyncio
async def test_us011_sponsor_email_invalid(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    body = _request_body(org_id, sponsor_email="no-es-email")
    r = await client.post("/api/v1/project-requests", json=body, headers=auth["_authz"])
    assert r.status_code == 422


# requester defaults → user.full_name / user.email si no se envían
@pytest.mark.asyncio
async def test_us011_requester_defaults(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    body = _request_body(org_id)  # sin requester_*
    r = await client.post("/api/v1/project-requests", json=body, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    data = r.json()
    # el admin de _setup se llama "Admin User" con email del tenant
    assert data["requester_name"]
    assert "@" in (data["requester_email"] or "")


# FK business_unit_id inválida → 422 business_rule
@pytest.mark.asyncio
async def test_us011_bu_fk_mismatch(client, db_session):
    import uuid

    _, auth, org_id = await _setup(client, db_session)
    body = _request_body(org_id, business_unit_id=str(uuid.uuid4()))
    r = await client.post("/api/v1/project-requests", json=body, headers=auth["_authz"])
    assert r.status_code == 422


# Depto no pertenece a la BU indicada → 422
@pytest.mark.asyncio
async def test_us011_dept_in_wrong_bu(client, db_session):
    _, auth, org_id = await _setup(client, db_session)

    # Crear dos BUs y un depto en cada una
    bu_a = (
        await client.post(
            f"/api/v1/organizations/{org_id}/business-units",
            json={"name": "BU-A"},
            headers=auth["_authz"],
        )
    ).json()
    bu_b = (
        await client.post(
            f"/api/v1/organizations/{org_id}/business-units",
            json={"name": "BU-B"},
            headers=auth["_authz"],
        )
    ).json()
    dept_a = (
        await client.post(
            f"/api/v1/business-units/{bu_a['id']}/departments",
            json={"name": "DeptA"},
            headers=auth["_authz"],
        )
    ).json()

    body = _request_body(
        org_id, business_unit_id=bu_b["id"], department_id=dept_a["id"]
    )
    r = await client.post("/api/v1/project-requests", json=body, headers=auth["_authz"])
    assert r.status_code == 422


# FKs correctas → 201 + persistidas en el registro
@pytest.mark.asyncio
async def test_us011_bu_dept_fk_happy_path(client, db_session):
    _, auth, org_id = await _setup(client, db_session)

    bu = (
        await client.post(
            f"/api/v1/organizations/{org_id}/business-units",
            json={"name": "Comercial"},
            headers=auth["_authz"],
        )
    ).json()
    dept = (
        await client.post(
            f"/api/v1/business-units/{bu['id']}/departments",
            json={"name": "Ventas"},
            headers=auth["_authz"],
        )
    ).json()

    body = _request_body(org_id, business_unit_id=bu["id"], department_id=dept["id"])
    r = await client.post("/api/v1/project-requests", json=body, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["business_unit_id"] == bu["id"]
    assert data["department_id"] == dept["id"]


# ============================================================================
# US-012 — Project Charter
# ============================================================================


async def _approve_and_create_project(client, auth, org_id, *, req_overrides=None):
    """Helper: crea solicitud → aprueba → crea proyecto → retorna payload."""
    body = _request_body(org_id, **(req_overrides or {}))
    r = await client.post("/api/v1/project-requests", json=body, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    req_id = r.json()["id"]
    a = await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    assert a.status_code == 200
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    cp = await client.post(
        f"/api/v1/project-requests/{req_id}/create-project",
        json={"pm_id": pm_id},
        headers=auth["_authz"],
    )
    assert cp.status_code == 200, cp.text
    return cp.json()


# TC-NEW-019: aprobar solicitud → charter creado con datos correctos
@pytest.mark.asyncio
async def test_tcnew019_charter_auto_generated(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    result = await _approve_and_create_project(
        client, auth, org_id,
        req_overrides={
            "key_people": "Juan, María",
            "objective": "Implementar X",
            "scope": "Alcance detallado",
            "benefits": "Beneficios detallados",
        },
    )
    assert "charter_id" in result

    r = await client.get(
        f"/api/v1/projects/{result['project_id']}/charter", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    ch = r.json()
    assert ch["sponsor"] == "CMO"
    assert ch["sponsor_email"] == "cmo@acme.example.com"
    assert ch["objective"] == "Implementar X"
    assert ch["scope"] == "Alcance detallado"
    assert ch["benefits"] == "Beneficios detallados"
    assert ch["key_people"] == "Juan, María"
    # Líderes vacíos para completar después
    assert ch["business_leader"] is None
    assert ch["tech_leader"] is None


# TC-NEW-020: sección 4 refleja datos del proyecto
@pytest.mark.asyncio
async def test_tcnew020_section4_derived_from_project(client, db_session):
    from datetime import date
    from app.models.project import Project
    from sqlalchemy import select

    _, auth, org_id = await _setup(client, db_session)
    result = await _approve_and_create_project(client, auth, org_id)
    pid = result["project_id"]

    # Mutar proyecto directo en BD y verificar que sección 4 refleja
    project = (
        await db_session.execute(select(Project).where(Project.id == pid))
    ).scalar_one()
    project.phase = "execution"
    project.health_status = "yellow"
    project.progress = 42
    project.start_date = date(2026, 5, 1)
    await db_session.commit()

    r = await client.get(f"/api/v1/projects/{pid}/charter", headers=auth["_authz"])
    s4 = r.json()["section_4"]
    assert s4["phase"] == "execution"
    assert s4["health_status"] == "yellow"
    assert s4["progress"] == 42
    assert s4["start_date"] == "2026-05-01"


# TC-NEW-021: PDF (HTML imprimible) on-demand
@pytest.mark.asyncio
async def test_tcnew021_charter_pdf_printable(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    result = await _approve_and_create_project(client, auth, org_id)
    r = await client.get(
        f"/api/v1/projects/{result['project_id']}/charter/pdf",
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert "Project Charter" in body
    assert "Información general" in body
    assert "Stakeholders" in body
    assert "Gestión" in body


# PATCH charter: edita secciones 1-3
@pytest.mark.asyncio
async def test_charter_patch_edits_sections_1_to_3(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    result = await _approve_and_create_project(client, auth, org_id)
    pid = result["project_id"]

    r = await client.patch(
        f"/api/v1/projects/{pid}/charter",
        json={
            "business_leader": "Ana García",
            "business_leader_email": "ana@acme.example.com",
            "tech_leader": "Luis Ruiz",
            "tech_leader_email": "luis@acme.example.com",
            "project_type": "innovation",
            "priority": 2,
            "restrictions": "Plazo 6 meses",
            "risks_summary": "Top 3 riesgos",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["business_leader"] == "Ana García"
    assert data["business_leader_email"] == "ana@acme.example.com"
    assert data["project_type"] == "innovation"
    assert data["priority"] == 2
    assert data["restrictions"] == "Plazo 6 meses"


# Charter no existe → 404 para proyectos creados antes de US-012
@pytest.mark.asyncio
async def test_charter_404_when_missing(client, db_session):
    from app.db.base import new_uuid
    from app.models.project import Project

    t, auth, org_id = await _setup(client, db_session)
    orphan = Project(
        id=new_uuid(),
        tenant_id=t.id,
        organization_id=org_id,
        folio="PRJ-ORPH",
        name="Sin charter",
        phase="planning",
    )
    db_session.add(orphan)
    await db_session.commit()

    r = await client.get(f"/api/v1/projects/{orphan.id}/charter", headers=auth["_authz"])
    assert r.status_code == 404


# ============================================================================
# US-013 — Charter como documento del proyecto
# ============================================================================


# TC-NEW-022: al crear proyecto, charter se registra como Document
@pytest.mark.asyncio
async def test_tcnew022_charter_appears_as_document(client, db_session):
    from sqlalchemy import select
    from app.models.modules import Document

    _, auth, org_id = await _setup(client, db_session)
    result = await _approve_and_create_project(client, auth, org_id)
    pid = result["project_id"]
    assert "charter_doc_id" in result

    rows = (
        await db_session.execute(
            select(Document).where(
                Document.project_id == pid, Document.category == "charter"
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    doc = rows[0]
    assert doc.title.startswith("Project Charter")
    assert doc.file_url == f"/api/v1/projects/{pid}/charter/pdf"
    assert doc.mime_type == "text/html"
    assert doc.is_current is True
