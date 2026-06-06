"""US-122 — Plantillas seed del Report Builder (EP020).

Cubre:
- Migración seedea 4 plantillas (L3-AVANCE, L3-SEGUIMIENTO,
  L1-PORTAFOLIO, L2-ORG) con `is_seed=True` y `tenant_id=NULL`.
- Todos los `section_codes` referenciados resuelven en el catálogo
  US-120 (`report_sections.code`).
- Modos y niveles coinciden con el spec del epic.
- Endpoint `GET /report-builder-templates` devuelve los seeds.
"""
import importlib.util
from pathlib import Path

import pytest

from app.models.report_builder_template import ReportBuilderTemplate
from app.models.report_section import ReportSection
from tests.factories import create_admin_role, create_tenant, create_user, login

_VERSIONS_DIR = (
    Path(__file__).resolve().parents[1] / "alembic" / "versions"
)
_SECTIONS_MIGRATION = _VERSIONS_DIR / "20260523_0070_report_sections.py"
_TEMPLATES_MIGRATION = _VERSIONS_DIR / "20260523_0071_report_builder_templates.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sections_codes() -> set[str]:
    mod = _load_module("_us120_mig", _SECTIONS_MIGRATION)
    return {row[0] for row in mod.SEED_SECTIONS}


def _templates_seed() -> list[tuple]:
    mod = _load_module("_us122_mig", _TEMPLATES_MIGRATION)
    return mod.SEED_TEMPLATES


def test_us122_seed_has_4_templates_unique_codes():
    seed = _templates_seed()
    assert len(seed) == 4
    codes = [row[0] for row in seed]
    assert set(codes) == {"L3-AVANCE", "L3-SEGUIMIENTO", "L1-PORTAFOLIO", "L2-ORG"}


def test_us122_seed_levels_and_modes_match_spec():
    by_code = {row[0]: row for row in _templates_seed()}
    # (code, name, description, level, mode, section_codes)
    assert by_code["L3-AVANCE"][3] == 3 and by_code["L3-AVANCE"][4] == "A"
    assert by_code["L3-SEGUIMIENTO"][3] == 3 and by_code["L3-SEGUIMIENTO"][4] == "B"
    assert by_code["L1-PORTAFOLIO"][3] == 1 and by_code["L1-PORTAFOLIO"][4] == "A"
    assert by_code["L2-ORG"][3] == 2 and by_code["L2-ORG"][4] == "A"


def test_us122_section_codes_resolve_in_catalog():
    catalog = _sections_codes()
    for code, _name, _desc, _lvl, _mode, sections in _templates_seed():
        for s in sections:
            assert s in catalog, (
                f"template {code} references unknown section {s}"
            )


def test_us122_avance_includes_required_sections():
    """Spec del epic — L3-AVANCE debe incluir hitos/críticos/raid."""
    by_code = {row[0]: row for row in _templates_seed()}
    avance = set(by_code["L3-AVANCE"][5])
    assert {"S-01", "S-02", "S-03", "S-04", "S-06", "S-19"} <= avance
    assert {"S-09", "S-16", "S-17", "S-18"} <= avance  # PLN
    assert {"S-14", "S-11", "S-13", "S-12"} <= avance  # RAID A-R-D-I


def test_us122_seguimiento_uses_mode_b_with_area_sections():
    by_code = {row[0]: row for row in _templates_seed()}
    seguimiento = by_code["L3-SEGUIMIENTO"]
    assert seguimiento[4] == "B"
    sections = set(seguimiento[5])
    assert {"S-20", "S-21"} <= sections  # EQP


def test_us122_portfolio_uses_prt_sections():
    by_code = {row[0]: row for row in _templates_seed()}
    portfolio = set(by_code["L1-PORTAFOLIO"][5])
    assert {"S-33", "S-34", "S-35", "S-36"} <= portfolio


# ------------------------------------------------------------------
# Endpoint tests
# ------------------------------------------------------------------

async def _seed_sections(db_session):
    import uuid

    mig = _load_module("_us120_mig_seed", _SECTIONS_MIGRATION)
    for (
        code, name, category, level, mode, supports_ia,
        description, data_shape, parameters_schema,
    ) in mig.SEED_SECTIONS:
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


async def _seed_templates(db_session):
    import uuid

    for code, name, description, level, mode, section_codes in _templates_seed():
        db_session.add(ReportBuilderTemplate(
            id=str(uuid.uuid4()),
            tenant_id=None,
            code=code,
            name=name,
            description=description,
            level=level,
            composition_mode=mode,
            section_codes=section_codes,
            default_parameters={},
            is_seed=True,
        ))
    await db_session.flush()


async def _admin(client, db_session, slug="us122"):
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
async def test_us122_endpoint_returns_seed_templates(client, db_session):
    await _seed_sections(db_session)
    await _seed_templates(db_session)
    _t, auth = await _admin(client, db_session)
    r = await client.get(
        "/api/v1/report-builder-templates", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    data = r.json()
    codes = {row["code"] for row in data}
    assert codes >= {"L3-AVANCE", "L3-SEGUIMIENTO", "L1-PORTAFOLIO", "L2-ORG"}
    for row in data:
        if row["code"] == "L3-AVANCE":
            assert row["composition_mode"] == "A"
            assert row["level"] == 3
            assert "S-09" in row["section_codes"]


@pytest.mark.asyncio
async def test_us122_endpoint_filters_by_level(client, db_session):
    await _seed_sections(db_session)
    await _seed_templates(db_session)
    _t, auth = await _admin(client, db_session)
    r = await client.get(
        "/api/v1/report-builder-templates?level=1", headers=auth["_authz"]
    )
    assert r.status_code == 200
    data = r.json()
    assert {row["code"] for row in data} == {"L1-PORTAFOLIO"}


@pytest.mark.asyncio
async def test_us122_endpoint_requires_auth(client):
    r = await client.get("/api/v1/report-builder-templates")
    assert r.status_code in {401, 403}
