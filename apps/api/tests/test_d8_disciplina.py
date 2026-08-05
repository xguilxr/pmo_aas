"""D-8 / ADR-021 — `portfolio_function` se llama `discipline`.

El glosario veta «portafolio» para un área (**brecha B-6**): un portafolio es un
conjunto de proyectos y programas agrupados para gestión estratégica, y esa
entidad no existe en el producto. Lo que el campo guarda es la disciplina del
recurso —`pm`, `arquitectura`, `datos`, `seguridad`…—.

Estuvo bloqueada un día no por el trabajo sino por el **nombre**: el glosario
tenía el veto y dejaba la columna «Preferente» en «—». `discipline` se eligió
porque en este producto «función» y «rol» ya significan otras cosas.

Lo que estas pruebas defienden:

1. **La ventana de compatibilidad**, en sus dos puertas — el cuerpo de creación
   y el parámetro de consulta. `portfolio_function` era un **nombre público**,
   así que un filtro guardado o un script de cliente no puede romperse.
2. **La salida es siempre canónica.** La ventana es para entrar. Si el API
   siguiera devolviendo `portfolio_function`, el frontend —cuyo tipo ya no lo
   contempla— lo ignoraría en silencio.
3. **`by_discipline` siguió al campo.** Dejar la clave de agregación en
   `by_function` con el campo ya renombrado reintroduce exactamente el desajuste
   que ADR-021 existe para cerrar.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login

RAIZ_API = Path(__file__).resolve().parents[1]


@pytest.fixture
async def auth(client, db_session):
    inquilino = await create_tenant(db_session, slug="d8", name="D-8")
    rol = await create_admin_role(db_session, inquilino)
    await create_user(
        db_session, tenant=inquilino, username="d8_admin",
        email="d8@ejemplo.test", password="Str0ng-Pass-A1!", roles=[rol],
    )
    sesion = await login(client, "d8_admin", "Str0ng-Pass-A1!")
    return sesion["_authz"]


def test_el_vocabulario_canonico():
    from typing import get_args

    from app.schemas.area import Discipline

    assert "arquitectura" in get_args(Discipline)
    assert len(get_args(Discipline)) == 12


# ---------------------------------------------------------------------------
# La ventana, en sus dos puertas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crear_con_el_nombre_viejo_sigue_funcionando(client, auth):
    """Un script de cliente que aún manda `portfolio_function` no se rompe."""
    r = await client.post(
        "/api/v1/actors",
        json={"name": "Ana Vieja", "portfolio_function": "arquitectura"},
        headers=auth,
    )

    assert r.status_code in (200, 201), r.text
    assert r.json()["discipline"] == "arquitectura", (
        "El nombre viejo entra, pero el valor se guarda y se devuelve con el "
        "canónico (ADR-021)."
    )


@pytest.mark.asyncio
async def test_la_salida_no_lleva_el_nombre_viejo(client, auth):
    """La ventana es para entrar. El frontend ya no conoce el nombre viejo."""
    r = await client.post(
        "/api/v1/actors",
        json={"name": "Beto Nuevo", "discipline": "datos"},
        headers=auth,
    )

    cuerpo = r.json()
    assert cuerpo["discipline"] == "datos"
    assert "portfolio_function" not in cuerpo


@pytest.mark.asyncio
async def test_el_filtro_guardado_del_cliente_sigue_encontrando(client, auth):
    """El parámetro de consulta era público: un enlace guardado debe servir."""
    for nombre, disciplina in [("C Arq", "arquitectura"), ("D Datos", "datos")]:
        await client.post(
            "/api/v1/actors",
            json={"name": nombre, "discipline": disciplina},
            headers=auth,
        )

    viejo = await client.get(
        "/api/v1/actors?portfolio_function=arquitectura", headers=auth
    )
    nuevo = await client.get("/api/v1/actors?discipline=arquitectura", headers=auth)

    nombres_viejo = sorted(a["name"] for a in viejo.json())
    assert nombres_viejo == sorted(a["name"] for a in nuevo.json())
    assert nombres_viejo == ["C Arq"], "El filtro tiene que filtrar, no solo no fallar"


@pytest.mark.asyncio
async def test_el_nombre_nuevo_manda_si_llegan_los_dos(client, auth):
    """Un cliente a medio migrar puede mandar ambos; gana el canónico."""
    await client.post(
        "/api/v1/actors", json={"name": "E Seg", "discipline": "seguridad"},
        headers=auth,
    )

    r = await client.get(
        "/api/v1/actors?discipline=seguridad&portfolio_function=datos", headers=auth
    )

    assert [a["name"] for a in r.json()] == ["E Seg"]


# ---------------------------------------------------------------------------
# Que no quede nadie hablando el idioma viejo
# ---------------------------------------------------------------------------


#: Los sitios que leen o agregan por este campo. Uno que se quede con el nombre
#: viejo no falla: deja de encontrar recursos, que es peor.
LEEN_LA_DISCIPLINA = [
    "app/services/capacity.py",
    "app/services/organigrama_export.py",
    "app/models/area.py",
]


@pytest.mark.parametrize("ruta", LEEN_LA_DISCIPLINA)
def test_ningun_sitio_sigue_leyendo_portfolio_function(ruta):
    texto = (RAIZ_API / ruta).read_text(encoding="utf-8")
    vivas = [
        n
        for n, linea in enumerate(texto.splitlines(), 1)
        if "portfolio_function" in linea and not linea.lstrip().startswith("#")
    ]

    assert not vivas, f"{ruta} sigue leyendo `portfolio_function` en {vivas}"


def test_la_clave_de_agregacion_siguio_al_campo():
    """`by_function` con el campo en `discipline` reabre el desajuste de D-8."""
    capacity = (RAIZ_API / "app" / "services" / "capacity.py").read_text(encoding="utf-8")

    assert '"by_discipline"' in capacity
    assert '"by_function"' not in capacity


def test_la_migracion_renombra_la_columna_y_es_reversible():
    migracion = (
        RAIZ_API / "alembic" / "versions" / "20260805_0099_discipline.py"
    ).read_text(encoding="utf-8")

    subida = migracion.split("def upgrade")[1].split("def downgrade")[0]
    bajada = migracion.split("def downgrade")[1]

    assert 'new_column_name="discipline"' in subida
    assert 'new_column_name="portfolio_function"' in bajada
