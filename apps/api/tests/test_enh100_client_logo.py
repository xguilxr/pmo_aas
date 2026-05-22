"""ENH-100 — organizations.client_logo_url (logo del cliente para EP020).

Cubre:
- La columna `client_logo_url` existe y acepta NULL en el schema.
- POST /organizations persiste `client_logo_url` cuando viene en el body.
- PATCH /organizations/{id} actualiza `client_logo_url`.
- GET /organizations/{id} y la lista exponen `client_logo_url`.
"""
from __future__ import annotations

import pytest
from sqlalchemy import inspect

from app.models.organization import Organization
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug: str = "enh100"):
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
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


@pytest.mark.asyncio
async def test_enh100_column_exists_and_nullable(db_session):
    """La columna client_logo_url existe en organizations y es nullable."""
    bind = db_session.bind

    def _inspect(sync_conn):
        insp = inspect(sync_conn)
        return {c["name"]: c for c in insp.get_columns("organizations")}

    async with bind.connect() as conn:
        cols = await conn.run_sync(_inspect)

    assert "client_logo_url" in cols, "Falta columna client_logo_url"
    assert cols["client_logo_url"]["nullable"] is True
    # Y la columna original logo_url sigue presente, separada.
    assert "logo_url" in cols


@pytest.mark.asyncio
async def test_enh100_create_persists_client_logo(client, db_session):
    _t, auth = await _admin(client, db_session, slug="enh100-create")
    r = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Org Cliente",
            "logo_url": "https://cdn.example.com/org.png",
            "client_logo_url": "https://cdn.example.com/cliente.png",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["logo_url"] == "https://cdn.example.com/org.png"
    assert body["client_logo_url"] == "https://cdn.example.com/cliente.png"


@pytest.mark.asyncio
async def test_enh100_patch_updates_client_logo(client, db_session):
    t, auth = await _admin(client, db_session, slug="enh100-patch")
    org = Organization(tenant_id=t.id, name="Org-P", is_active=True)
    db_session.add(org)
    await db_session.flush()
    await db_session.commit()

    r = await client.patch(
        f"/api/v1/organizations/{org.id}",
        json={"client_logo_url": "https://cdn.example.com/nuevo-cliente.png"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["client_logo_url"] == "https://cdn.example.com/nuevo-cliente.png"

    # GET devuelve el mismo valor.
    r2 = await client.get(
        f"/api/v1/organizations/{org.id}", headers=auth["_authz"]
    )
    assert r2.status_code == 200
    assert r2.json()["client_logo_url"] == "https://cdn.example.com/nuevo-cliente.png"


@pytest.mark.asyncio
async def test_enh100_list_returns_client_logo_field(client, db_session):
    t, auth = await _admin(client, db_session, slug="enh100-list")
    o1 = Organization(
        tenant_id=t.id,
        name="ConClienteLogo",
        is_active=True,
        client_logo_url="https://cdn.example.com/c1.png",
    )
    o2 = Organization(tenant_id=t.id, name="SinClienteLogo", is_active=True)
    db_session.add_all([o1, o2])
    await db_session.commit()

    r = await client.get("/api/v1/organizations", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    by_name = {o["name"]: o for o in r.json()}
    assert by_name["ConClienteLogo"]["client_logo_url"] == "https://cdn.example.com/c1.png"
    assert by_name["SinClienteLogo"]["client_logo_url"] is None
