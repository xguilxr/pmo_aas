"""ENH-189 — Arquitectura de prompts composable.

Cubre:
- TC-189-1: build_system_prompt sin instrucciones deja el base intacto y solo
  le anexa la regla de contenido no confiable (B2 / MCS IA-11 cambió esto: la
  función devolvía `base` tal cual y ahora nunca lo hace; la cobertura de esa
  regla vive en `test_ia11_inyeccion_prompt.py`).
- TC-189-2: con instrucciones anexa el bloque con regla de precedencia.
- TC-189-3: truncado a 2000 chars.
- TC-189-4: load_tenant_ai lee settings.ai.instructions_md.
- TC-189-5: admin PATCH /admin/ai/provider persiste instructions_md y el
  GET lo devuelve; "" lo borra.
"""
import pytest
from sqlalchemy import select

from app.models.tenant import Tenant
from app.services.ai.prompt_builder import (
    TENANT_INSTRUCTIONS_MAX_CHARS,
    build_system_prompt,
)
from app.services.ai.tenant_ai import load_tenant_ai
from app.services.ai.untrusted import REGLA_CONTENIDO_NO_CONFIABLE
from tests.factories import create_admin_role, create_tenant, create_user, login


def test_enh189_builder_no_instructions_keeps_base_intact():
    base = "Eres un asistente. Devuelve SOLO JSON."
    for sin_instrucciones in (None, "   "):
        out = build_system_prompt(base, sin_instrucciones)
        assert out.startswith(base)
        assert "<INSTRUCCIONES_DEL_TENANT>" not in out
        # Lo único que se anexa sin instrucciones es la defensa de IA-11.
        assert out[len(base):].strip() == REGLA_CONTENIDO_NO_CONFIABLE


def test_enh189_builder_appends_block():
    base = "Eres un asistente. Devuelve SOLO JSON."
    out = build_system_prompt(base, "Usa español formal.")
    assert out.startswith(base)
    assert "<INSTRUCCIONES_DEL_TENANT>" in out
    assert "Usa español formal." in out
    assert "NUNCA cambies el formato" in out


def test_enh189_builder_truncates():
    out = build_system_prompt("base", "X" * 5000)
    # Se mide solo el bloque del tenant: detrás va la regla de IA-11, que es
    # de la plataforma y no está sujeta a este tope.
    block = out.split("<INSTRUCCIONES_DEL_TENANT>")[1].split(
        "</INSTRUCCIONES_DEL_TENANT>"
    )[0]
    assert len(block) < TENANT_INSTRUCTIONS_MAX_CHARS + 200
    assert "…" in out


@pytest.mark.asyncio
async def test_enh189_load_tenant_ai_reads_instructions(client, db_session):
    t = await create_tenant(db_session)
    t.settings = {
        **(t.settings or {}),
        "ai": {"mode": "platform", "instructions_md": "  Tono ejecutivo.  "},
    }
    await db_session.commit()
    cfg = await load_tenant_ai(db_session, str(t.id))
    assert cfg.mode == "platform"
    assert cfg.instructions_md == "Tono ejecutivo."


@pytest.mark.asyncio
async def test_enh189_admin_patch_persists_instructions(client, db_session):
    t = await create_tenant(db_session)
    tid = str(t.id)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")

    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={"mode": "platform", "instructions_md": "Fechas en formato DD/MMM."},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["instructions_md"] == "Fechas en formato DD/MMM."

    g = await client.get("/api/v1/admin/ai/provider", headers=auth["_authz"])
    assert g.json()["instructions_md"] == "Fechas en formato DD/MMM."

    # La sesión del test cachea el Tenant creado por la factory; expirar
    # para leer lo que persistió la request del app (id capturado antes
    # de expirar — acceder a atributos expirados en async dispara
    # MissingGreenlet).
    db_session.expire_all()
    tenant = (
        await db_session.execute(select(Tenant).where(Tenant.id == tid))
    ).scalar_one()
    assert tenant.settings["ai"]["instructions_md"] == "Fechas en formato DD/MMM."

    # "" borra las instrucciones.
    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={"mode": "platform", "instructions_md": ""},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["instructions_md"] is None
