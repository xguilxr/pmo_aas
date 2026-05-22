"""ENH-098 — Per-tenant `progress_calculation_method` setting."""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="enh098"):
    t = await create_tenant(db_session, slug=slug, name=slug)
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
async def test_get_returns_default_when_unset(client, db_session):
    _, auth = await _admin(client, db_session, slug="enh098a")
    r = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert r.status_code == 200
    body = r.json()
    assert body["settings"]["progress_calculation_method"] == "by_task_count"


@pytest.mark.asyncio
async def test_patch_persists_value(client, db_session):
    _, auth = await _admin(client, db_session, slug="enh098b")
    r = await client.patch(
        "/api/v1/admin/settings",
        json={"progress_calculation_method": "by_duration"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["settings"]["progress_calculation_method"] == "by_duration"
    # Canonical nested shape
    assert (
        body["settings"]["report_builder"]["progress_calculation_method"]
        == "by_duration"
    )

    # Re-GET confirms persistence.
    r2 = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert r2.status_code == 200
    assert (
        r2.json()["settings"]["progress_calculation_method"] == "by_duration"
    )


@pytest.mark.asyncio
async def test_patch_rejects_invalid_enum(client, db_session):
    _, auth = await _admin(client, db_session, slug="enh098c")
    r = await client.patch(
        "/api/v1/admin/settings",
        json={"progress_calculation_method": "by_unicorns"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422
