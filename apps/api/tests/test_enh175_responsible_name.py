"""ENH-175 — _attach_owners resuelve `responsible_name` (Actor con fallback
a Usuario) para la columna Responsable de las listas RAID."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.v1.endpoints.modules import _attach_owners
from app.models.area import Actor
from tests.factories import create_tenant, create_user


@pytest.mark.asyncio
async def test_attach_owners_resolves_actor_then_user(db_session):
    t = await create_tenant(db_session)
    user = await create_user(
        db_session,
        tenant=t,
        username="resp",
        email="resp@acme.example.com",
        password="Str0ng-Pass-1!",
        full_name="Usuario Login",
    )
    actor = Actor(tenant_id=str(t.id), name="Carla Actor")
    db_session.add(actor)
    await db_session.flush()

    item_actor = SimpleNamespace(owner_id=None, owner_actor_id=str(actor.id), owner=None)
    item_user = SimpleNamespace(owner_id=str(user.id), owner_actor_id=None, owner=None)
    item_none = SimpleNamespace(owner_id=None, owner_actor_id=None, owner=None)

    await _attach_owners(db_session, [item_actor, item_user, item_none])

    # Actor preferido; fallback a Usuario; None si no hay responsable.
    assert item_actor.responsible_name == "Carla Actor"
    assert item_user.responsible_name == "Usuario Login"
    assert item_none.responsible_name is None
    # `owner` (UserMini) sigue resolviéndose para el item con owner_id.
    assert item_user.owner is not None and item_user.owner["full_name"] == "Usuario Login"
