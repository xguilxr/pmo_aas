"""ENH-083 — Reporte Seguimiento agrupado por área."""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.area import Area
from app.models.modules import Issue
from app.models.organization import Organization
from app.models.project import Project
from app.models.task import Task
from app.services.operational_reports import build_seguimiento_context
from tests.factories import create_admin_role, create_tenant, create_user


async def _seed(db_session):
    t = await create_tenant(db_session, slug="enh083", name="enh083")
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin_enh083",
        email="admin@enh083.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    org = Organization(tenant_id=t.id, name="Org083", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(t.id), organization_id=str(org.id),
        folio="P-083", name="Proyecto 083",
        budget=Decimal("0"), actual_budget=Decimal("0"), progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    a1 = Area(tenant_id=str(t.id), name="Operaciones")
    a2 = Area(tenant_id=str(t.id), name="Ingeniería")
    db_session.add_all([a1, a2])
    await db_session.flush()
    return t, p, a1, a2


@pytest.mark.asyncio
async def test_tc083_1_two_areas_produce_two_blocks(client, db_session):
    t, p, a1, a2 = await _seed(db_session)
    cut = date(2026, 5, 1)
    db_session.add_all([
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="T-op",
            status="in_progress", progress=20, area_id=str(a1.id),
            end_date=cut + timedelta(days=3),
        ),
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="T-ing",
            status="in_progress", progress=20, area_id=str(a2.id),
            end_date=cut + timedelta(days=5),
        ),
    ])
    await db_session.commit()

    ctx = await build_seguimiento_context(db_session, t.id, p.id, cut, window_days=14)
    blocks = ctx["groups_upcoming"]
    names = [g["area_name"] for g in blocks]
    assert "Operaciones" in names
    assert "Ingeniería" in names
    # ENH-083: ordenado alfabéticamente.
    assert names.index("Ingeniería") < names.index("Operaciones")


@pytest.mark.asyncio
async def test_tc083_2_item_without_area_falls_into_unassigned_block(client, db_session):
    t, p, a1, _ = await _seed(db_session)
    cut = date(2026, 5, 1)
    db_session.add_all([
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="T-con-area",
            status="in_progress", progress=20, area_id=str(a1.id),
            end_date=cut + timedelta(days=3),
        ),
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="T-sin-area",
            status="in_progress", progress=20,
            end_date=cut + timedelta(days=5),
        ),
    ])
    await db_session.commit()
    ctx = await build_seguimiento_context(db_session, t.id, p.id, cut, window_days=14)
    blocks = ctx["groups_upcoming"]
    names = [g["area_name"] for g in blocks]
    # Bloque "Sin área asignada" siempre al final.
    assert names[-1] == "Sin área asignada"


@pytest.mark.asyncio
async def test_tc083_3_items_within_block_sorted_by_date(client, db_session):
    t, p, a1, _ = await _seed(db_session)
    cut = date(2026, 5, 1)
    db_session.add_all([
        Issue(
            tenant_id=str(t.id), project_id=p.id, folio="ISS-A",
            title="Acción tarde", type="action", status="open", priority=2,
            area_id=str(a1.id),
            committed_date=cut + timedelta(days=10),
            reported_at=datetime.now(UTC),
        ),
        Issue(
            tenant_id=str(t.id), project_id=p.id, folio="ISS-B",
            title="Acción temprana", type="action", status="open", priority=2,
            area_id=str(a1.id),
            committed_date=cut + timedelta(days=2),
            reported_at=datetime.now(UTC),
        ),
    ])
    await db_session.commit()
    ctx = await build_seguimiento_context(db_session, t.id, p.id, cut, window_days=30)
    # ENH-154: las acciones ahora viven en su propia sección "Acciones"
    # (groups_actions), ya no mezcladas en los buckets de Actividades.
    block = next(g for g in ctx["groups_actions"] if g["area_name"] == "Operaciones")
    titles = [r["title"] for r in block["rows"]]
    assert titles == ["Acción temprana", "Acción tarde"]
