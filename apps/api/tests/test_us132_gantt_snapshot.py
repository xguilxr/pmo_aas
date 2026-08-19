"""US-132 — Render headless del Gantt WBS-1 para S-19 (EP020).

TC-235 (endpoint devuelve PNG válido — adaptado a SVG en v1.0 según
decisión documentada), TC-236 (fallback / placeholder en proyecto
grande), TC-237 (image embebida en PDF — validamos contrato SVG con
<svg> root tag).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.organization import Organization
from app.models.project import Project
from app.models.task import Task
from app.services.reports.gantt_renderer import render_gantt_svg
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session, slug, n_tasks=5):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[role],
    )
    org = Organization(tenant_id=t.id, name="Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(t.id),
        organization_id=str(org.id),
        folio="P-GANTT",
        name="Proj Gantt",
        phase="ejecucion",
        health_status="green",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    today = date(2026, 6, 1)
    for i in range(n_tasks):
        db_session.add(
            Task(
                tenant_id=str(t.id),
                project_id=p.id,
                wbs_code=f"{(i % 3) + 1}.{i // 3 + 1}",
                name=f"Task {i}",
                status="in_progress",
                start_date=today - timedelta(days=10 - i),
                end_date=today + timedelta(days=5 + i),
                duration_days=15,
                progress=20 * (i % 5),
                is_milestone=(i % 7 == 0),
                is_critical=(i % 5 == 0),
            )
        )
    await db_session.flush()
    await db_session.commit()
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, p, auth


@pytest.mark.asyncio
async def test_tc235_endpoint_returns_svg(client, db_session):
    """TC-235 (adaptado) — endpoint devuelve SVG válido con <svg root."""
    _t, p, auth = await _setup(client, db_session, "us132-svg")
    r = await client.get(
        f"/api/v1/projects/{p.id}/gantt/snapshot?wbs_level=1",
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "image/svg+xml"
    assert r.text.lstrip().startswith("<svg")
    # Aparece el folio del proyecto en el SVG
    assert "P-GANTT" in r.text


@pytest.mark.asyncio
async def test_tc236_placeholder_on_large_project(db_session):
    """TC-236 — fallback a placeholder cuando hay > MAX_ROWS_DETAIL WBS groups."""
    from app.services.reports.gantt_renderer import MAX_ROWS_DETAIL

    t = await create_tenant(db_session, slug="us132-big", name="us132-big")
    org = Organization(tenant_id=t.id, name="Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(t.id),
        organization_id=str(org.id),
        folio="P-BIG",
        name="Big",
        phase="ejecucion",
        health_status="green",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    # Crear MAX_ROWS_DETAIL + 5 grupos WBS únicos.
    tasks = []
    for i in range(MAX_ROWS_DETAIL + 5):
        tasks.append(
            Task(
                tenant_id=str(t.id),
                project_id=p.id,
                wbs_code=f"{i + 1}",  # cada uno único en WBS-1
                name=f"T{i}",
                status="in_progress",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                duration_days=10,
                progress=0,
            )
        )
    db_session.add_all(tasks)
    await db_session.flush()

    svg = render_gantt_svg(
        p, tasks, wbs_level=1,
        window_start=date(2026, 1, 1), window_end=date(2026, 12, 31),
    )
    assert "Vista detallada deshabilitada" in svg


@pytest.mark.asyncio
async def test_tc237_svg_embeddable(client, db_session):
    """TC-237 — el SVG es embebible como <img src=...>: chequeamos que el
    body sea XML válido (no JSON ni HTML)."""
    _t, p, auth = await _setup(client, db_session, "us132-emb", n_tasks=3)
    r = await client.get(
        f"/api/v1/projects/{p.id}/gantt/snapshot",
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    body = r.text.strip()
    assert body.startswith("<svg")
    assert body.endswith("</svg>")


@pytest.mark.asyncio
async def test_png_not_supported_v1(client, db_session):
    _t, p, auth = await _setup(client, db_session, "us132-png", n_tasks=1)
    r = await client.get(
        f"/api/v1/projects/{p.id}/gantt/snapshot?format=png",
        headers=auth["_authz"],
    )
    assert r.status_code == 501
