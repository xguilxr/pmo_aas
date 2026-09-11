"""US-258 (FASE-4, revamp v2, DEC-037) — el "Programa General" por defecto.

Un proyecto que se crea sin portafolio ni programa ya no queda huérfano: cae
en el "Programa General" (y su "Portafolio General") de la organización,
creado al vuelo la primera vez que hace falta — mismo patrón que
`portafolio_general()` (US-198) ya usa para programas sin portafolio.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.organization import Organization, Portfolio, Program
from app.services.jerarquia import (
    NOMBRE_PORTAFOLIO_GENERAL,
    NOMBRE_PROGRAMA_GENERAL,
    programa_general,
)
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _org(db, tenant_id: str, nombre: str = "Org A") -> Organization:
    org = Organization(tenant_id=tenant_id, name=nombre, is_active=True)
    db.add(org)
    await db.flush()
    return org


# --------------------------------------------------------------------------
# 1. El servicio: crea el par y lo reusa
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_programa_general_crea_el_par_y_lo_reusa(db_session) -> None:
    t = await create_tenant(db_session, slug="us258-a", name="US258 A")
    org = await _org(db_session, t.id)

    primero = await programa_general(db_session, tenant_id=t.id, organization_id=org.id)
    assert primero.name == NOMBRE_PROGRAMA_GENERAL

    pf = (
        await db_session.execute(select(Portfolio).where(Portfolio.id == primero.portfolio_id))
    ).scalar_one()
    assert pf.name == NOMBRE_PORTAFOLIO_GENERAL
    assert str(pf.organization_id) == str(org.id)

    segundo = await programa_general(db_session, tenant_id=t.id, organization_id=org.id)
    assert str(segundo.id) == str(primero.id)

    cuantos = (
        await db_session.execute(
            select(Program).where(Program.tenant_id == t.id, Program.organization_id == org.id)
        )
    ).scalars().all()
    assert len(cuantos) == 1


# --------------------------------------------------------------------------
# 2. `POST /projects` sin portafolio ni programa
# --------------------------------------------------------------------------


async def _setup(client, db_session):
    t = await create_tenant(db_session, slug="us258-api", name="US258 API")
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin258", email="admin258@pmoaas.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin258", "Str0ng-Admin-1!")
    r = await client.post("/api/v1/organizations", json={"name": "Org258"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    return t, auth, org_id


@pytest.mark.asyncio
async def test_proyecto_sin_portafolio_cae_en_programa_general(client, db_session) -> None:
    _, auth, org_id = await _setup(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]

    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto huérfano",
            "description": "Sin portafolio ni programa al crearse",
            "type": "innovacion",
            "priority": 3,
            "organization_id": org_id,
            "pm_id": pm_id,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["portfolio_id"] is not None
    assert body["program_id"] is not None

    pf = (
        await db_session.execute(select(Portfolio).where(Portfolio.id == body["portfolio_id"]))
    ).scalar_one()
    prog = (
        await db_session.execute(select(Program).where(Program.id == body["program_id"]))
    ).scalar_one()
    assert pf.name == NOMBRE_PORTAFOLIO_GENERAL
    assert prog.name == NOMBRE_PROGRAMA_GENERAL
    assert str(prog.portfolio_id) == str(pf.id)

    # Un segundo proyecto huérfano cae en el MISMO par — no se duplica.
    r2 = await client.post(
        "/api/v1/projects",
        json={
            "name": "Otro huérfano",
            "description": "También sin portafolio ni programa",
            "type": "innovacion",
            "priority": 3,
            "organization_id": org_id,
            "pm_id": pm_id,
        },
        headers=auth["_authz"],
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["portfolio_id"] == body["portfolio_id"]
    assert r2.json()["program_id"] == body["program_id"]
