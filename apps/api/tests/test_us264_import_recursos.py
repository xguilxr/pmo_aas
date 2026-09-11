"""US-264 (FASE-6, revamp v2, DEC-038) — importador de recursos por organización.

`(tenant_id, organization_id, email)` es la clave de unicidad (D1): un correo
que ya existe en la organización se marca "actualizar" (no se toca, per la
regla de US-216) y un correo nuevo se marca "crear"; una fila sin correo es
inválida porque el correo es obligatorio. El mismo correo en otra
organización del tenant es un actor nuevo e independiente.
"""
from __future__ import annotations

import io
import time

import pytest

from app.services import import_job_store
from tests.factories import create_admin_role, create_tenant, create_user, login


class _FakeRedis:
    """Mismo stub que `test_us216_importacion_masiva.py`: el store es el mismo."""

    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = (value, time.monotonic() + ex if ex else float("inf"))

    def get(self, key: str) -> str | None:
        row = self._store.get(key)
        if row is None:
            return None
        value, expiry = row
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return value

    def delete(self, key: str) -> int:
        return int(bool(self._store.pop(key, None)))


@pytest.fixture(autouse=True)
def _stub_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(import_job_store, "_get_client", lambda: fake)


def _csv(lineas: list[str]) -> tuple[str, io.BytesIO, str]:
    contenido = "\n".join(lineas).encode("utf-8")
    return ("carga.csv", io.BytesIO(contenido), "text/csv")


async def _escenario(client, db_session):
    t = await create_tenant(db_session, slug="us264", name="US264")
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin264", email="admin264@pmoaas.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin264", "Str0ng-Admin-1!")
    h = auth["_authz"]
    org_a = (
        await client.post("/api/v1/organizations", json={"name": "Org A"}, headers=h)
    ).json()["id"]
    org_b = (
        await client.post("/api/v1/organizations", json={"name": "Org B"}, headers=h)
    ).json()["id"]

    async def preview(lineas, org_id):
        return await client.post(
            "/api/v1/imports/preview",
            data={"kind": "resources", "organization_id": org_id},
            files={"file": _csv(lineas)},
            headers=h,
        )

    return {"h": h, "org_a": org_a, "org_b": org_b, "preview": preview}


@pytest.mark.asyncio
async def test_nuevo_y_existente_en_la_misma_organizacion(client, db_session):
    e = await _escenario(client, db_session)
    d = (
        await e["preview"](
            [
                "Nombre,Correo,Empresa,Tarifa,Unidad tarifa",
                "Ana Ruiz,ana@example.com,Acme,,",
            ],
            e["org_a"],
        )
    ).json()
    assert d["summary"]["valid"] == 1
    r = await client.post(f"/api/v1/imports/{d['job_id']}/confirm", headers=e["h"])
    assert r.status_code == 201, r.text
    assert r.json()["created_count"] == 1

    # Mismo correo, misma organización → duplicada (no se actualiza, US-216).
    # Correo nuevo → válida.
    d2 = (
        await e["preview"](
            [
                "Nombre,Correo,Empresa,Tarifa,Unidad tarifa",
                "Ana Ruiz otra vez,ana@example.com,Acme,,",
                "Roberto Vega,roberto@example.com,Acme,,",
            ],
            e["org_a"],
        )
    ).json()
    estados = {f["name"]: f["state"] for f in d2["rows"]}
    assert estados["Ana Ruiz otra vez"] == "duplicada"
    assert estados["Roberto Vega"] == "valida"


@pytest.mark.asyncio
async def test_mismo_correo_en_otra_organizacion_no_es_duplicado(client, db_session):
    e = await _escenario(client, db_session)
    d1 = (
        await e["preview"](
            ["Nombre,Correo,Empresa,Tarifa,Unidad tarifa", "Ana Ruiz,ana@example.com,Acme,,"],
            e["org_a"],
        )
    ).json()
    await client.post(f"/api/v1/imports/{d1['job_id']}/confirm", headers=e["h"])

    d2 = (
        await e["preview"](
            ["Nombre,Correo,Empresa,Tarifa,Unidad tarifa", "Ana Ruiz,ana@example.com,Acme,,"],
            e["org_b"],
        )
    ).json()
    assert d2["summary"]["valid"] == 1
    r2 = await client.post(f"/api/v1/imports/{d2['job_id']}/confirm", headers=e["h"])
    assert r2.status_code == 201, r2.text
    assert r2.json()["created_count"] == 1

    actores = (await client.get("/api/v1/actors", headers=e["h"])).json()
    filas = actores if isinstance(actores, list) else actores["items"]
    anas = [a for a in filas if a["email"] == "ana@example.com"]
    assert len(anas) == 2
    assert anas[0]["organization_id"] != anas[1]["organization_id"]
