"""ENH-053 — Plan import: mapeo de columnas asistido por IA.

Cubre:
- TC-053.2: ai_mode=disabled → heurística devuelve `name` para
  "Tarea"/"Title"/"Task" (case-insensitive).
- Headers desconocidos → confidence baja / field None.
- Heurística sustring match para variantes (ej. "Fecha inicio" → start_date).
"""
import pytest

from app.services.ai.tenant_ai import TenantAIConfig
from app.services.import_mapping_suggest import (
    heuristic_suggestion,
    suggest_column_mapping,
)
from tests.factories import create_admin_role, create_tenant, create_user, login


def test_heuristic_exact_synonym():
    s = heuristic_suggestion("Tarea")
    assert s["field"] == "name"
    assert s["confidence"] >= 0.9


def test_heuristic_substring():
    s = heuristic_suggestion("Fecha inicio")
    assert s["field"] == "start_date"
    assert s["confidence"] >= 0.6


def test_heuristic_unknown_header():
    s = heuristic_suggestion("xqzy")
    assert s["field"] is None
    assert s["confidence"] == 0.0


@pytest.mark.asyncio
async def test_disabled_tenant_returns_only_heuristic():
    cfg = TenantAIConfig(mode="disabled")
    out = await suggest_column_mapping(
        ["Tarea", "Inicio", "Fin", "Responsable", "xqzy"],
        tenant_cfg=cfg,
    )
    assert out["Tarea"]["field"] == "name"
    assert out["Inicio"]["field"] == "start_date"
    assert out["Fin"]["field"] == "end_date"
    assert out["Responsable"]["field"] == "resources"
    assert out["xqzy"]["field"] is None
    # Ningún source AI cuando disabled.
    assert all(v["source"] in ("heuristic", "none") for v in out.values())


async def _con_respuesta_del_modelo(monkeypatch, texto: str, cabeceras: list[str]):
    """Corre el mapeo con el proveedor sustituido por `texto`."""
    from dataclasses import dataclass

    from app.services import import_mapping_suggest as mapeo

    @dataclass
    class _Resultado:
        text: str
        model: str = "stub"

    async def _fake(prompt, **kwargs):
        return _Resultado(text=texto)

    monkeypatch.setattr(mapeo, "generate_for_tenant", _fake)
    return await suggest_column_mapping(
        cabeceras, tenant_cfg=TenantAIConfig(mode="platform")
    )


@pytest.mark.asyncio
async def test_un_no_lo_se_del_modelo_no_borra_lo_que_la_heuristica_acerto(monkeypatch):
    """El modelo devuelve `field: null` con confianza 0,99.

    Antes ganaba —0,99 > el 0,8 de la heurística— y la columna llegaba sin
    asignar al asistente de importación, pese a que la heurística la había
    acertado. Un «no lo sé» no es información por seguro que venga.

    Encontrado por el conjunto de evaluación de IA (caso EV-C-35), no por un
    reporte de usuario.
    """
    out = await _con_respuesta_del_modelo(
        monkeypatch,
        '{"Nombre de la tarea": {"field": null, "confidence": 0.99}}',
        ["Nombre de la tarea"],
    )
    assert out["Nombre de la tarea"]["field"] == "name"
    assert out["Nombre de la tarea"]["source"] == "heuristic"


@pytest.mark.asyncio
async def test_el_modelo_sigue_ganando_cuando_aporta_un_campo(monkeypatch):
    """Control negativo: si la IA nunca puede ganar, sobra la llamada."""
    out = await _con_respuesta_del_modelo(
        monkeypatch, '{"Col_7": {"field": "progress", "confidence": 0.95}}', ["Col_7"]
    )
    assert out["Col_7"] == {"field": "progress", "confidence": 0.95, "source": "ai"}


@pytest.mark.asyncio
async def test_el_valor_del_mapeo_no_tiene_por_que_ser_un_objeto(monkeypatch):
    """`_safe_parse_ai_response` ya filtra los no-dict, pero la puerta de
    confianza no debe depender de que ese filtro exista."""
    out = await _con_respuesta_del_modelo(
        monkeypatch, '{"Tarea": "name", "Inicio": ["start_date"]}', ["Tarea", "Inicio"]
    )
    assert out["Tarea"]["source"] == "heuristic"
    assert out["Inicio"]["source"] == "heuristic"


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    org = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": "P1",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return auth, p.json()["id"]


@pytest.mark.asyncio
async def test_endpoint_returns_suggestions(client, db_session):
    auth, proj = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj}/tasks/import/suggest-mapping",
        json={"headers": ["Tarea", "Inicio", "Fin", "Avance"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["suggestions"]["Tarea"]["field"] == "name"
    assert body["suggestions"]["Inicio"]["field"] == "start_date"
    assert body["suggestions"]["Fin"]["field"] == "end_date"
    assert body["suggestions"]["Avance"]["field"] == "progress"
    # Tenant fresco no tiene AI configurada → ai_used False.
    assert body["ai_used"] is False
    assert "name" in body["system_fields"]
