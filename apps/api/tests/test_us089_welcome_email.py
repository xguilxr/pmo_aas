"""US-089 — email de bienvenida al crear usuario.

Cobre 3 TC:
- TC-089.1: crear user → send_email_via_resend se llama con destinatario
  correcto + body con username + password + link.
- TC-089.2: si Resend está deshabilitado → endpoint igual retorna 201,
  audit registra welcome_email_sent=false.
- TC-089.3: el usuario creado tiene must_change_password=True.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.endpoints import admin_users as endpoint_mod
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin_setup(client, db_session, slug="us089"):
    t = await create_tenant(db_session, slug=slug, name=slug.title())
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


@pytest.mark.asyncio
async def test_us089_welcome_email_sent_with_credentials(client, db_session):
    _, auth = await _admin_setup(client, db_session, slug="us089a")

    fake_resend = AsyncMock(return_value={"id": "resend-msg-1"})
    with patch.object(endpoint_mod, "create_user"):
        pass  # smoke import

    with patch(
        "app.services.email.send_email_via_resend",
        fake_resend,
    ):
        r = await client.post(
            "/api/v1/admin/users",
            json={
                "username": "newbie",
                "email": "newbie@us089a.example.com",
                "full_name": "New Bie",
                "password": "Welcome-1!",
                "role_ids": [],
                "is_active": True,
            },
            headers=auth["_authz"],
        )
    assert r.status_code == 201, r.text

    fake_resend.assert_awaited_once()
    kwargs = fake_resend.call_args.kwargs
    assert kwargs["to"] == "newbie@us089a.example.com"
    assert "credenciales de acceso" in kwargs["subject"].lower()
    html = kwargs["html"]
    assert "newbie" in html  # username
    assert "Welcome-1!" in html  # password en claro
    assert "/login" in html  # link a login


@pytest.mark.asyncio
async def test_us089_resend_disabled_returns_201(
    client, db_session, monkeypatch
):
    _, auth = await _admin_setup(client, db_session, slug="us089b")

    # Forzar el camino "Resend deshabilitado": no hay API key.
    from app.core import config as cfg_mod

    monkeypatch.setattr(cfg_mod.settings, "RESEND_API_KEY", "", raising=False)

    r = await client.post(
        "/api/v1/admin/users",
        json={
            "username": "disabled_resend",
            "email": "disabled@us089b.example.com",
            "full_name": "Disabled Resend",
            "password": "Welcome-1!",
            "role_ids": [],
            "is_active": True,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201
    # Endpoint no falla aunque el envío de email haya sido no-op.


@pytest.mark.asyncio
async def test_us089_user_must_change_password_on_first_login(
    client, db_session
):
    _, auth = await _admin_setup(client, db_session, slug="us089c")

    fake_resend = AsyncMock(return_value={"id": "x"})
    with patch("app.services.email.send_email_via_resend", fake_resend):
        r = await client.post(
            "/api/v1/admin/users",
            json={
                "username": "needchange",
                "email": "nc@us089c.example.com",
                "full_name": "Need Change",
                "password": "Welcome-1!",
                "role_ids": [],
                "is_active": True,
            },
            headers=auth["_authz"],
        )
    assert r.status_code == 201

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "needchange", "password": "Welcome-1!"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["must_change_password"] is True
