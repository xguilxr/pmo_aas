"""ENH-099 — Per-tenant task_load_thresholds setting."""
import pytest

from app.models.tenant import Tenant
from app.services.tenant_settings import (
    DEFAULT_TASK_LOAD_THRESHOLDS,
    get_task_load_thresholds,
    set_task_load_thresholds,
    validate_task_load_thresholds,
)
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="acme"):
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


# ---- service-level helpers ----


def test_get_task_load_thresholds_returns_defaults_when_unset():
    t = Tenant(slug="x", name="x", settings={})
    assert get_task_load_thresholds(t) == DEFAULT_TASK_LOAD_THRESHOLDS
    assert get_task_load_thresholds(t) is not DEFAULT_TASK_LOAD_THRESHOLDS  # copy


def test_get_task_load_thresholds_returns_defaults_for_malformed():
    t = Tenant(slug="x", name="x", settings={"report_builder": {"task_load_thresholds": "nope"}})
    assert get_task_load_thresholds(t) == DEFAULT_TASK_LOAD_THRESHOLDS


def test_get_task_load_thresholds_reads_nested_value():
    t = Tenant(
        slug="x",
        name="x",
        settings={"report_builder": {"task_load_thresholds": {"green_max": 3, "amber_max": 7}}},
    )
    assert get_task_load_thresholds(t) == {"green_max": 3, "amber_max": 7}


def test_validate_task_load_thresholds_rejects_invalid():
    with pytest.raises(ValueError):
        validate_task_load_thresholds(-1, 10)
    with pytest.raises(ValueError):
        validate_task_load_thresholds(5, -10)
    with pytest.raises(ValueError):
        validate_task_load_thresholds(0, 5)
    with pytest.raises(ValueError):
        validate_task_load_thresholds(10, 5)
    with pytest.raises(ValueError):
        validate_task_load_thresholds(5, 5)


def test_validate_task_load_thresholds_accepts_valid():
    validate_task_load_thresholds(1, 2)
    validate_task_load_thresholds(5, 10)


def test_set_task_load_thresholds_persists_and_preserves_siblings():
    t = Tenant(
        slug="x",
        name="x",
        settings={"report_builder": {"progress_calculation_method": "by_duration"}},
    )
    set_task_load_thresholds(t, 4, 8)
    assert t.settings["report_builder"]["task_load_thresholds"] == {
        "green_max": 4,
        "amber_max": 8,
    }
    # Sibling key untouched.
    assert (
        t.settings["report_builder"]["progress_calculation_method"] == "by_duration"
    )


# ---- HTTP endpoint ----


@pytest.mark.asyncio
async def test_get_settings_returns_default_thresholds(client, db_session):
    _, auth = await _admin(client, db_session)
    r = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert r.status_code == 200
    assert r.json()["settings"]["task_load_thresholds"] == DEFAULT_TASK_LOAD_THRESHOLDS


@pytest.mark.asyncio
async def test_patch_thresholds_persists(client, db_session):
    _, auth = await _admin(client, db_session)
    r = await client.patch(
        "/api/v1/admin/settings",
        json={"task_load_thresholds": {"green_max": 3, "amber_max": 8}},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["task_load_thresholds"] == {"green_max": 3, "amber_max": 8}

    # Round-trip via GET.
    g = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert g.status_code == 200
    assert g.json()["settings"]["task_load_thresholds"] == {"green_max": 3, "amber_max": 8}


@pytest.mark.asyncio
async def test_patch_thresholds_rejects_negative(client, db_session):
    _, auth = await _admin(client, db_session)
    r = await client.patch(
        "/api/v1/admin/settings",
        json={"task_load_thresholds": {"green_max": -1, "amber_max": 10}},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_thresholds_rejects_non_monotonic(client, db_session):
    _, auth = await _admin(client, db_session)
    r = await client.patch(
        "/api/v1/admin/settings",
        json={"task_load_thresholds": {"green_max": 10, "amber_max": 5}},
        headers=auth["_authz"],
    )
    assert r.status_code == 422
    # equal is also rejected.
    r2 = await client.patch(
        "/api/v1/admin/settings",
        json={"task_load_thresholds": {"green_max": 5, "amber_max": 5}},
        headers=auth["_authz"],
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_patch_thresholds_rejects_missing_keys(client, db_session):
    _, auth = await _admin(client, db_session)
    r = await client.patch(
        "/api/v1/admin/settings",
        json={"task_load_thresholds": {"green_max": 5}},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_thresholds_preserves_other_settings(client, db_session):
    _, auth = await _admin(client, db_session)
    # Set locale first.
    await client.patch(
        "/api/v1/admin/settings",
        json={"locale": "en-US"},
        headers=auth["_authz"],
    )
    # Then thresholds.
    r = await client.patch(
        "/api/v1/admin/settings",
        json={"task_load_thresholds": {"green_max": 2, "amber_max": 6}},
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    body = r.json()["settings"]
    assert body["locale"] == "en-US"
    assert body["task_load_thresholds"] == {"green_max": 2, "amber_max": 6}
