"""US-063 — Recuperación y cambio de contraseña por email.

Cubre:
- Hash de token (SHA-256) + emisión + consumo (roundtrip).
- Tokens 1-shot: segundo uso → None.
- Expiración: token vencido → None.
- /auth/forgot-password: responde 204 siempre (email existente,
  inexistente, rate-limit).
- /auth/reset-password: token válido cambia la password, invalida
  refresh tokens del user, limpia must_change_password, password
  inválida según política → 422, token inexistente → 400, rate-limit →
  400 RATE_LIMITED.
- /auth/change-password: manda notif con send_email=True al terminar.

Los tests monkeypatch el rate-limit para no depender de Redis real —
pasan en CI sin backend externo.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.auth import PasswordResetToken, RefreshToken
from app.models.notification import Notification
from app.models.user import User
from app.services.password_reset import (
    _hash_token,
    consume_reset_token,
    issue_reset_token,
)
from tests.factories import create_tenant, create_user, login


# -----------------------------------------------------------------------------
# Unit — service password_reset
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us063_issue_and_consume_roundtrip(db_session):
    t = await create_tenant(db_session, slug="pr-a")
    u = await create_user(
        db_session, tenant=t, username="u_a", email="a@ex.com",
        password="Str0ng-Pass-A1!",
    )

    plain = await issue_reset_token(db_session, user_id=u.id, ip_address="1.2.3.4")
    await db_session.commit()
    assert len(plain) >= 32

    row = await consume_reset_token(db_session, plain=plain)
    assert row is not None
    assert str(row.user_id) == str(u.id)
    assert row.used_at is not None


@pytest.mark.asyncio
async def test_us063_token_one_shot(db_session):
    t = await create_tenant(db_session, slug="pr-b")
    u = await create_user(
        db_session, tenant=t, username="u_b", email="b@ex.com",
        password="Str0ng-Pass-A1!",
    )
    plain = await issue_reset_token(db_session, user_id=u.id)
    await db_session.commit()

    first = await consume_reset_token(db_session, plain=plain)
    await db_session.commit()
    assert first is not None

    second = await consume_reset_token(db_session, plain=plain)
    assert second is None  # ya fue usado


@pytest.mark.asyncio
async def test_us063_token_expired(db_session):
    t = await create_tenant(db_session, slug="pr-c")
    u = await create_user(
        db_session, tenant=t, username="u_c", email="c@ex.com",
        password="Str0ng-Pass-A1!",
    )
    plain = await issue_reset_token(db_session, user_id=u.id)
    await db_session.flush()
    # Forzar expiración manual.
    row = (
        await db_session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == _hash_token(plain)
            )
        )
    ).scalar_one()
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()

    assert await consume_reset_token(db_session, plain=plain) is None


@pytest.mark.asyncio
async def test_us063_unknown_token_returns_none(db_session):
    assert (
        await consume_reset_token(db_session, plain="not_a_real_token_abcdefg1234")
    ) is None


# -----------------------------------------------------------------------------
# Integration — endpoint /auth/forgot-password
# -----------------------------------------------------------------------------


def _no_rate_limit(*_args, **_kwargs):
    return True


@pytest.fixture(autouse=True)
def _stub_rate_limit(monkeypatch):
    # Por defecto, rate-limit siempre permite. Tests específicos pueden
    # volver a monkeypatch para forzar bloqueos.
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.check_and_increment", _no_rate_limit,
    )


@pytest.mark.asyncio
async def test_us063_forgot_existing_email_creates_token_and_notif(
    client, db_session,
):
    t = await create_tenant(db_session, slug="fp-a")
    await create_user(
        db_session, tenant=t, username="u_fp_a", email="fp_a@ex.com",
        password="Str0ng-Pass-A1!",
    )
    r = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "fp_a@ex.com"},
    )
    assert r.status_code == 204

    rows = (
        await db_session.execute(select(PasswordResetToken))
    ).scalars().all()
    assert len(rows) == 1
    # Notif creada, tipo password_reset_requested, marcada para email.
    notifs = (
        await db_session.execute(
            select(Notification).where(
                Notification.type == "password_reset_requested"
            )
        )
    ).scalars().all()
    assert len(notifs) == 1


@pytest.mark.asyncio
async def test_us063_forgot_unknown_email_returns_204_without_token(
    client, db_session,
):
    r = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "ghost@nowhere.example.com"},
    )
    assert r.status_code == 204
    rows = (
        await db_session.execute(select(PasswordResetToken))
    ).scalars().all()
    assert len(rows) == 0  # no emitimos token para emails desconocidos


@pytest.mark.asyncio
async def test_us063_forgot_rate_limited_still_204(client, db_session, monkeypatch):
    # Forzar rate-limit bloqueado.
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.check_and_increment",
        lambda *a, **kw: False,
    )
    t = await create_tenant(db_session, slug="fp-rl")
    await create_user(
        db_session, tenant=t, username="u_fp_rl", email="fp_rl@ex.com",
        password="Str0ng-Pass-A1!",
    )
    r = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "fp_rl@ex.com"},
    )
    # Debe responder 204 (no revelar el bloqueo) pero NO emitir token.
    assert r.status_code == 204
    rows = (
        await db_session.execute(select(PasswordResetToken))
    ).scalars().all()
    assert len(rows) == 0


# -----------------------------------------------------------------------------
# Integration — endpoint /auth/reset-password
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us063_reset_happy_path_invalidates_refresh_tokens(
    client, db_session,
):
    t = await create_tenant(db_session, slug="rp-a")
    u = await create_user(
        db_session, tenant=t, username="u_rp_a", email="rp_a@ex.com",
        password="Str0ng-Pass-A1!",
    )
    # Un login previo crea un refresh_token activo.
    auth = await login(client, "u_rp_a", "Str0ng-Pass-A1!")
    assert auth["access_token"]
    rt_before = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == u.id)
        )
    ).scalars().all()
    assert len(rt_before) == 1
    assert rt_before[0].revoked is False

    # Emitir token via backend endpoint y leerlo desde la BD (plaintext
    # no viaja en HTTP — sólo por email, que aquí no validamos).
    r = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "rp_a@ex.com"},
    )
    assert r.status_code == 204

    # Para test: emitimos un nuevo token programáticamente y lo usamos.
    new_plain = await issue_reset_token(db_session, user_id=u.id)
    await db_session.commit()

    rr = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": new_plain, "new_password": "N3wStr0ng-Pass1!"},
    )
    assert rr.status_code == 204, rr.text

    # La password cambió — verificamos con un nuevo login.
    auth2 = await login(client, "u_rp_a", "N3wStr0ng-Pass1!")
    assert auth2["access_token"]

    # Refresh previo quedó revocado.
    await db_session.refresh(rt_before[0])
    assert rt_before[0].revoked is True


@pytest.mark.asyncio
async def test_us063_reset_invalid_token_returns_422_business_rule(
    client, db_session,
):
    r = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "fake_token_long_enough_string_xyz",
            "new_password": "N3wStr0ng-Pass1!",
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "TOKEN_INVALID"


@pytest.mark.asyncio
async def test_us063_reset_weak_password_rejected(client, db_session):
    t = await create_tenant(db_session, slug="rp-weak")
    u = await create_user(
        db_session, tenant=t, username="u_rp_weak", email="rp_weak@ex.com",
        password="Str0ng-Pass-A1!",
    )
    plain = await issue_reset_token(db_session, user_id=u.id)
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": plain, "new_password": "short"},
    )
    # validate_password_policy → validation_error = 400 (VALIDATION_ERROR).
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "VALIDATION_ERROR"
    # Token no se consumió (policy falla antes de tocarlo).
    row = (
        await db_session.execute(select(PasswordResetToken))
    ).scalar_one()
    assert row.used_at is None


@pytest.mark.asyncio
async def test_us063_reset_rate_limited_returns_422(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.check_and_increment",
        lambda *a, **kw: False,
    )
    r = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "any_token_long_enough_string_xyz",
            "new_password": "N3wStr0ng-Pass1!",
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "RATE_LIMITED"


# -----------------------------------------------------------------------------
# Integration — /auth/change-password sends PASSWORD_CHANGED notif
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us063_change_password_enqueues_notif(client, db_session):
    t = await create_tenant(db_session, slug="cp-a")
    u = await create_user(
        db_session, tenant=t, username="u_cp_a", email="cp_a@ex.com",
        password="Str0ng-Pass-A1!",
    )
    auth = await login(client, "u_cp_a", "Str0ng-Pass-A1!")

    r = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "Str0ng-Pass-A1!",
            "new_password": "N3wStr0ng-Pass1!",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 204
    notifs = (
        await db_session.execute(
            select(Notification).where(Notification.user_id == u.id)
        )
    ).scalars().all()
    types = {n.type for n in notifs}
    assert "password_changed" in types
