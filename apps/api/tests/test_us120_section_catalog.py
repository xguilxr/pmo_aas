"""US-120 — Catálogo de secciones atómicas (EP020).

Cubre:
- Migración seedea 22 secciones con códigos únicos y niveles válidos.
- Cada sección tiene `data_shape` y `parameters_schema` parseables.
- Endpoint `GET /report-sections` devuelve el catálogo y filtra por
  categoría y nivel.
"""
import importlib.util
import json
from pathlib import Path

import pytest

from app.models.report_section import ReportSection
from tests.factories import create_admin_role, create_tenant, create_user, login

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260523_0070_report_sections.py"
)


def _load_seed():
    spec = importlib.util.spec_from_file_location(
        "_us120_migration", _MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SEED_SECTIONS


def test_us120_seed_has_22_sections_unique_codes():
    seed = _load_seed()
    assert len(seed) == 22, f"expected 22 seed sections, got {len(seed)}"
    codes = [row[0] for row in seed]
    assert len(set(codes)) == 22, "duplicate codes in seed"
    for code in codes:
        assert code.startswith("S-") and len(code) <= 8, code


def test_us120_seed_levels_and_modes_valid():
    seed = _load_seed()
    for row in seed:
        code, name, category, level, mode = row[0], row[1], row[2], row[3], row[4]
        assert category in {
            "HDR", "EST", "AVN", "PLN", "RAID", "EQP", "NAR", "KPI", "PRT"
        }, f"{code} category {category}"
        assert level in {1, 2, 3, 4}, f"{code} level {level}"
        assert mode in {"A", "B"}, f"{code} mode {mode}"
        assert isinstance(name, str) and len(name) >= 3


def test_us120_seed_json_shapes_parse():
    seed = _load_seed()
    for row in seed:
        code, data_shape, params_schema = row[0], row[7], row[8]
        json.dumps(data_shape)
        json.dumps(params_schema)
        assert isinstance(data_shape, dict), f"{code} data_shape not dict"
        assert isinstance(params_schema, dict), f"{code} params_schema not dict"


async def _seed_db(db_session):
    import uuid

    seed = _load_seed()
    for (
        code, name, category, level, mode, supports_ia,
        description, data_shape, parameters_schema,
    ) in seed:
        db_session.add(ReportSection(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            description=description,
            category=category,
            level=level,
            data_shape=data_shape,
            parameters_schema=parameters_schema,
            composition_mode_default=mode,
            supports_ia=supports_ia,
            enabled=True,
        ))
    await db_session.flush()


async def _admin(client, db_session, slug="us120"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


@pytest.mark.asyncio
async def test_us120_endpoint_lists_catalog(client, db_session):
    await _seed_db(db_session)
    _t, auth = await _admin(client, db_session)
    r = await client.get("/api/v1/report-sections", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 22
    codes = {row["code"] for row in data}
    for must in ["S-01", "S-09", "S-11", "S-35"]:
        assert must in codes


@pytest.mark.asyncio
async def test_us120_endpoint_filters_by_category(client, db_session):
    await _seed_db(db_session)
    _t, auth = await _admin(client, db_session)
    r = await client.get(
        "/api/v1/report-sections?category=PRT", headers=auth["_authz"]
    )
    assert r.status_code == 200
    data = r.json()
    assert {row["code"] for row in data} == {"S-33", "S-34", "S-35", "S-36"}


@pytest.mark.asyncio
async def test_us120_endpoint_filters_by_level(client, db_session):
    await _seed_db(db_session)
    _t, auth = await _admin(client, db_session)
    r = await client.get(
        "/api/v1/report-sections?level=1", headers=auth["_authz"]
    )
    assert r.status_code == 200
    data = r.json()
    assert all(row["level"] <= 1 for row in data)
    assert {row["code"] for row in data} == {"S-33", "S-34", "S-35", "S-36"}


@pytest.mark.asyncio
async def test_us120_endpoint_requires_auth(client):
    r = await client.get("/api/v1/report-sections")
    assert r.status_code in {401, 403}


@pytest.mark.asyncio
async def test_us120_endpoint_tolerates_double_encoded_json(client, db_session):
    """BUG-063 — regresión: las migraciones de seed 0070/0071 guardaron
    data_shape/parameters_schema como strings (double-encoded). El
    endpoint debe parsearlos en vez de tirar 500.

    Simulamos el estado corrupto insertando un row con strings JSON en
    las columnas y verificamos que el endpoint los normaliza.
    """
    import uuid

    from sqlalchemy import text

    _t, auth = await _admin(client, db_session, slug="us120dbl")
    # Inserta una sección con data_shape/parameters_schema como STRING
    # (lo que dejaron las migraciones con json.dumps). Usamos SQL crudo
    # con bind params para evitar que el JSON type del ORM lo re-serialice.
    sid = str(uuid.uuid4())
    await db_session.execute(
        text(
            "INSERT INTO report_sections "
            "(id, code, name, description, category, level, data_shape, "
            " parameters_schema, composition_mode_default, supports_ia, "
            " enabled, created_at, updated_at) "
            "VALUES (:id, :code, :name, :desc, :cat, :lvl, :ds, :ps, :mode, "
            " :ia, :en, :ca, :ua)"
        ),
        {
            "id": sid,
            "code": "S-DBL",
            "name": "Double encoded section",
            "desc": None,
            "cat": "HDR",
            "lvl": 3,
            "ds": '{"fields": ["title", "period"]}',
            "ps": '{"period": {"type": "date_range"}}',
            "mode": "A",
            "ia": False,
            "en": True,
            "ca": "2026-05-25T00:00:00+00:00",
            "ua": "2026-05-25T00:00:00+00:00",
        },
    )
    await db_session.flush()

    r = await client.get("/api/v1/report-sections", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    row = next(x for x in r.json() if x["code"] == "S-DBL")
    # El endpoint parseó el string a dict real.
    assert row["data_shape"] == {"fields": ["title", "period"]}
    assert row["parameters_schema"] == {"period": {"type": "date_range"}}
