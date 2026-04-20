"""US-NEW-040 — Formato estandarizado + export de Minuta IA."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models.modules import MeetingMinute
from app.models.organization import Organization
from app.models.project import Project
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="min-a"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


async def _seed_minute(db_session, tenant, *, folio="MIN-0001", project_folio="P-MIN"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id), organization_id=str(org.id),
        folio=project_folio, name="Proyecto de minuta",
        phase="execution", health_status="green", budget=Decimal("1"),
    )
    db_session.add(p)
    await db_session.flush()
    m = MeetingMinute(
        tenant_id=str(tenant.id),
        project_id=str(p.id),
        folio=folio,
        title="Kick-off del proyecto Alpha",
        status="final",
        meeting_date=datetime(2026, 4, 20, 15, 0, tzinfo=timezone.utc),
        participants=[
            {"name": "María López", "role": "Sponsor"},
            {"name": "Juan Pérez", "role": "PM"},
            {"name": "Externo SA", "role": "Proveedor"},
        ],
        topics=[
            {"title": "Alcance", "notes": "Se confirma MVP v1"},
            {"title": "Cronograma", "notes": "Fecha objetivo: dic 2026"},
        ],
        agreements=[
            {
                "kind": "risk", "description": "Retraso de proveedor",
                "severity": 15, "owner": "Juan Pérez",
            },
            {
                "kind": "action", "description": "Enviar propuesta de contrato",
                "owner": "Juan Pérez", "area": "PM",
                "due_date": "2026-04-25",
            },
            {
                "kind": "action", "description": "Coordinar kickoff técnico",
                "owner": "Área de Ingeniería",
                "due_date": "2026-04-30",
            },
            {
                "kind": "decision", "description": "Aprobar presupuesto v1",
                "owner": "María López",
            },
        ],
        generated_by_ai=True,
    )
    db_session.add(m)
    await db_session.flush()
    return m, p


@pytest.mark.asyncio
async def test_usnew040_export_md_contains_sections(client, db_session):
    t, auth = await _admin(client, db_session)
    m, _ = await _seed_minute(db_session, t)
    await db_session.commit()

    r = await client.get(
        f"/api/v1/meeting-minutes/{m.id}/export?format=md", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/markdown")
    body = r.text
    # Separadores corporativos
    assert body.count("========") >= 5
    # Secciones
    assert "Resumen e Hitos" in body
    assert "RAID" in body
    assert "Notas adicionales" in body
    # Acciones agrupadas por responsable/área
    assert "PM:" in body or "PM :" in body or "PM\n" in body
    assert "Área de Ingeniería" in body


@pytest.mark.asyncio
async def test_usnew040_export_txt(client, db_session):
    t, auth = await _admin(client, db_session, slug="min-b")
    m, _ = await _seed_minute(db_session, t, folio="MIN-0002", project_folio="P-MIN2")
    await db_session.commit()

    r = await client.get(
        f"/api/v1/meeting-minutes/{m.id}/export?format=txt", headers=auth["_authz"]
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert ".txt" in r.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_usnew040_export_docx_is_valid(client, db_session):
    t, auth = await _admin(client, db_session, slug="min-c")
    m, _ = await _seed_minute(db_session, t, folio="MIN-0003", project_folio="P-MIN3")
    await db_session.commit()

    r = await client.get(
        f"/api/v1/meeting-minutes/{m.id}/export?format=docx", headers=auth["_authz"]
    )
    assert r.status_code == 200
    assert "wordprocessingml" in r.headers["content-type"]
    # DOCX = ZIP file, empieza con PK
    assert r.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_usnew040_export_pdf(client, db_session):
    t, auth = await _admin(client, db_session, slug="min-d")
    m, _ = await _seed_minute(db_session, t, folio="MIN-0004", project_folio="P-MIN4")
    await db_session.commit()

    r = await client.get(
        f"/api/v1/meeting-minutes/{m.id}/export?format=pdf", headers=auth["_authz"]
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_usnew040_export_rejects_bad_format(client, db_session):
    t, auth = await _admin(client, db_session, slug="min-e")
    m, _ = await _seed_minute(db_session, t, folio="MIN-0005", project_folio="P-MIN5")
    await db_session.commit()

    r = await client.get(
        f"/api/v1/meeting-minutes/{m.id}/export?format=xlsx", headers=auth["_authz"]
    )
    # FastAPI rechaza por Query pattern → 422
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_usnew040_export_cross_tenant_404(client, db_session):
    t_a, auth_a = await _admin(client, db_session, slug="min-ta")
    _, auth_b = await _admin(client, db_session, slug="min-tb")
    m, _ = await _seed_minute(db_session, t_a, folio="MIN-X", project_folio="P-X")
    await db_session.commit()
    r = await client.get(
        f"/api/v1/meeting-minutes/{m.id}/export?format=md",
        headers=auth_b["_authz"],
    )
    assert r.status_code == 404


def test_usnew040_view_groups_actions_by_owner(db_session):
    """Test unitario: build_view agrupa acciones por owner/área."""
    from app.services.minutes_formatter import build_view

    class _Mini:
        title = "Test"
        meeting_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        participants = [{"name": "A"}]
        topics = [{"title": "t1"}]
        agreements = [
            {"kind": "action", "description": "a1", "owner": "Juan"},
            {"kind": "action", "description": "a2", "owner": "Juan"},
            {"kind": "action", "description": "a3", "area": "Ventas"},
            {"kind": "risk", "description": "r1", "severity": 10},
        ]

    view = build_view(_Mini(), None)
    assert len(view.raid_groups) == 2
    owners = [g["owner"] for g in view.raid_groups]
    assert "Juan" in owners
    assert "Ventas" in owners
    juan_rows = next(g for g in view.raid_groups if g["owner"] == "Juan")["rows"]
    assert len(juan_rows) == 2
