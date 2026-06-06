"""ENH-154 — Reporte de Seguimiento: sección "Acciones".

Las AIDs tipo `action` abiertas se listan completas en su propia sección
(`groups_actions`) y dejan de mezclarse con las tareas en los buckets de
Actividades (vencidas / en curso / próximas). Criterio "vigente" = toda
acción abierta (status notin resolved/closed), sin filtro de ventana.
"""
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
    t = await create_tenant(db_session, slug="enh154", name="enh154")
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin_enh154",
        email="admin@enh154.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    org = Organization(tenant_id=t.id, name="Org154", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(t.id), organization_id=str(org.id),
        folio="P-154", name="Proyecto 154",
        budget=Decimal("0"), actual_budget=Decimal("0"), progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    a1 = Area(tenant_id=str(t.id), name="Operaciones")
    db_session.add(a1)
    await db_session.flush()
    return t, p, a1


def _all_titles(groups) -> list[str]:
    return [r["title"] for g in groups for r in g["rows"]]


@pytest.mark.asyncio
async def test_enh154_open_actions_separated_from_activity_buckets(client, db_session):
    """Las acciones abiertas van a groups_actions y NO a los buckets de
    Actividades; las tareas van a los buckets y NO a Acciones."""
    t, p, a1 = await _seed(db_session)
    cut = date(2026, 5, 1)
    db_session.add_all([
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="Tarea próxima",
            status="in_progress", progress=20, area_id=str(a1.id),
            end_date=cut + timedelta(days=3),
        ),
        Issue(
            tenant_id=str(t.id), project_id=p.id, folio="ACC-1",
            title="Acción con fecha", type="action", status="open", priority=2,
            area_id=str(a1.id),
            committed_date=cut + timedelta(days=3),
            reported_at=datetime.now(UTC),
        ),
    ])
    await db_session.commit()

    ctx = await build_seguimiento_context(db_session, t.id, p.id, cut, window_days=14)

    # La acción está en su sección, no en los buckets de Actividades.
    assert "Acción con fecha" in _all_titles(ctx["groups_actions"])
    bucket_titles = (
        _all_titles(ctx["groups_overdue"])
        + _all_titles(ctx["groups_in_progress"])
        + _all_titles(ctx["groups_upcoming"])
    )
    assert "Acción con fecha" not in bucket_titles
    # La tarea sigue en su bucket y no aparece en Acciones.
    assert "Tarea próxima" in _all_titles(ctx["groups_upcoming"])
    assert "Tarea próxima" not in _all_titles(ctx["groups_actions"])


@pytest.mark.asyncio
async def test_enh154_action_without_committed_date_is_rescued(client, db_session):
    """Criterio 'toda acción abierta': una acción SIN fecha de compromiso
    (que antes no caía en ningún bucket) ahora se lista en Acciones."""
    t, p, a1 = await _seed(db_session)
    cut = date(2026, 5, 1)
    db_session.add(
        Issue(
            tenant_id=str(t.id), project_id=p.id, folio="ACC-SF",
            title="Acción sin fecha", type="action", status="open", priority=3,
            area_id=str(a1.id),
            committed_date=None,
            reported_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    ctx = await build_seguimiento_context(db_session, t.id, p.id, cut, window_days=14)
    assert "Acción sin fecha" in _all_titles(ctx["groups_actions"])


@pytest.mark.asyncio
async def test_enh154_resolved_action_excluded(client, db_session):
    """Una acción resuelta/cerrada no es 'abierta' → no aparece en Acciones."""
    t, p, a1 = await _seed(db_session)
    cut = date(2026, 5, 1)
    db_session.add(
        Issue(
            tenant_id=str(t.id), project_id=p.id, folio="ACC-RES",
            title="Acción resuelta", type="action", status="resolved", priority=1,
            area_id=str(a1.id),
            committed_date=cut + timedelta(days=2),
            reported_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    ctx = await build_seguimiento_context(db_session, t.id, p.id, cut, window_days=14)
    assert "Acción resuelta" not in _all_titles(ctx["groups_actions"])
