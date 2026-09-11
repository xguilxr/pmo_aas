"""ENH-204 (afecta US-167) — `user_scope_assignments` gana `scope_type`
`"portfolio"`, con la misma herencia hacia abajo que ya tenían org/program:
un portafolio da visibilidad a sus programas y proyectos (los que cuelgan
de un programa del portafolio y los que cuelgan del portafolio sin
programa), pero NO a otros portafolios de la misma org ni al resto del
contenido de la org.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.visibility import get_user_visibility
from app.models.project import Project
from app.models.user_scope_assignment import UserScopeAssignment
from tests.factories import (
    create_admin_role,
    create_portfolio,
    create_program,
    create_tenant,
    create_user,
    login,
)


async def _escenario(client, db_session):
    """Misma forma que test_us201: Cartera A (Programa A1 → P1, P2; sin
    programa → P3), Cartera B (Programa B1 → P4), sin clasificar → P5."""
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin204",
        email="admin204@acme.example.com", password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin204", "Str0ng-Admin-1!")
    r = await client.post(
        "/api/v1/organizations", json={"name": "Org204"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]

    pf_a = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org_id, name="Cartera A"
    )
    pf_b = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org_id, name="Cartera B"
    )
    prog_a1 = await create_program(
        db_session, tenant_id=t.id, organization_id=org_id,
        name="Programa A1", portfolio_id=str(pf_a.id),
    )
    prog_b1 = await create_program(
        db_session, tenant_id=t.id, organization_id=org_id,
        name="Programa B1", portfolio_id=str(pf_b.id),
    )

    especificaciones = [
        ("P1", str(pf_a.id), str(prog_a1.id)),
        ("P2", str(pf_a.id), str(prog_a1.id)),
        ("P3", str(pf_a.id), None),
        ("P4", str(pf_b.id), str(prog_b1.id)),
        ("P5", None, None),
    ]
    proyectos = {}
    for i, (nombre, pfid, pgid) in enumerate(especificaciones):
        p = Project(
            tenant_id=t.id, organization_id=org_id, portfolio_id=pfid,
            program_id=pgid, folio=f"E204-{i + 1:03d}", name=nombre,
            phase="ejecucion", health_status="green", budget=Decimal("1000"),
            progress=0, type="transformacion",
        )
        db_session.add(p)
        proyectos[nombre] = p
    await db_session.flush()
    await db_session.commit()

    pm = await create_user(
        db_session, tenant=t, username="pm204", email="pm204@acme.example.com",
        password="Str0ng-Pm-1!", role_type="user",
    )
    return {
        "tenant": t, "pm": pm, "org_id": org_id,
        "pf_a": pf_a, "pf_b": pf_b,
        "prog_a1": prog_a1, "prog_b1": prog_b1,
        "proyectos": proyectos,
    }


@pytest.mark.asyncio
async def test_portafolio_da_visibilidad_a_sus_programas_y_proyectos(client, db_session):
    e = await _escenario(client, db_session)

    db_session.add(UserScopeAssignment(
        tenant_id=str(e["tenant"].id), user_id=str(e["pm"].id),
        scope_type="portfolio", scope_id=str(e["pf_a"].id),
    ))
    await db_session.commit()

    scope = await get_user_visibility(e["pm"], db_session)

    assert scope.portfolio_ids == {str(e["pf_a"].id)}
    assert scope.program_ids == {str(e["prog_a1"].id)}
    assert scope.project_ids == {
        str(e["proyectos"]["P1"].id),
        str(e["proyectos"]["P2"].id),
        str(e["proyectos"]["P3"].id),  # cuelga del portafolio sin programa
    }
    # La org queda visible como contexto, pero no la otra cartera ni P4/P5.
    assert scope.org_ids == {str(e["org_id"])}
    assert str(e["proyectos"]["P4"].id) not in scope.project_ids
    assert str(e["proyectos"]["P5"].id) not in scope.project_ids


@pytest.mark.asyncio
async def test_asignacion_de_programa_deja_visible_el_portafolio_como_contexto(client, db_session):
    e = await _escenario(client, db_session)

    db_session.add(UserScopeAssignment(
        tenant_id=str(e["tenant"].id), user_id=str(e["pm"].id),
        scope_type="program", scope_id=str(e["prog_a1"].id),
    ))
    await db_session.commit()

    scope = await get_user_visibility(e["pm"], db_session)

    assert scope.portfolio_ids == {str(e["pf_a"].id)}
    assert scope.project_ids == {
        str(e["proyectos"]["P1"].id),
        str(e["proyectos"]["P2"].id),
    }


@pytest.mark.asyncio
async def test_scope_assignments_endpoint_acepta_portfolio(client, db_session):
    e = await _escenario(client, db_session)
    auth = await login(client, "admin204", "Str0ng-Admin-1!")

    r = await client.put(
        f"/api/v1/admin/users/{e['pm'].id}/scope-assignments",
        json={"assignments": [{"scope_type": "portfolio", "scope_id": str(e["pf_a"].id)}]},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["assignments"] == [
        {"scope_type": "portfolio", "scope_id": str(e["pf_a"].id)}
    ]
