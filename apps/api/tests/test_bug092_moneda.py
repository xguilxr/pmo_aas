"""BUG-092 — la moneda va sobre el proyecto, y los agregados no la mezclan.

`tenant.settings.currency` ofrecía MXN, USD y EUR y **el formulario que la
guardaba era el único sitio que la leía**. Diez superficies traían
`currency: "MXN"` escrito, así que un inquilino en dólares —el propio sembrado
crea uno— veía sus importes rotulados en pesos. El número no estaba mal; la
unidad era mentira, que en un importe es lo mismo que estar mal.

Salió midiendo DAT-02, y DAT-01 lo dejó declarado con su disparador: «la unidad
canónica del importe deja de ser MXN el día que la moneda llegue a la
presentación». Ese día es hoy.

**Decisión del owner (2026-08-07):** la moneda va sobre el **proyecto**; el
inquilino declara una *preferida* que es el valor inicial de los que no eligen.

## La parte que no era evidente

Un portafolio con un proyecto en pesos y otro en euros **no tiene un
presupuesto total**. Sumar 1.000 y 1.000 para escribir «2.000» produce un
número que no existe en ninguna parte. `dominio.moneda.agregar` no ofrece la
forma de hacerlo: devuelve un importe por moneda y no hay total al que caerse.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.dominio.moneda import (
    MONEDAS,
    POR_DEFECTO,
    agregar,
    es_valida,
    resolver,
    unica,
)

# --------------------------------------------------------------------------
# Resolver: proyecto → preferida → por defecto
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "del_proyecto,preferida,esperado",
    [
        ("EUR", "USD", "EUR"),
        (None, "USD", "USD"),
        (None, None, POR_DEFECTO),
        ("", "USD", "USD"),
        ("XYZ", "USD", "USD"),
        ("EUR", None, "EUR"),
        (None, "xyz", POR_DEFECTO),
    ],
)
def test_gana_la_mas_especifica(
    del_proyecto: str | None, preferida: str | None, esperado: str
) -> None:
    """El nulo del proyecto significa «la que diga el inquilino», no «ninguna».

    Es lo que hace que cambiar la preferida arrastre a los proyectos que no
    eligieron, que es lo que espera quien la cambia.
    """
    assert resolver(del_proyecto, preferida) == esperado


def test_un_codigo_desconocido_no_se_propaga() -> None:
    """`settings` lo edita una persona desde un formulario.

    Un importe sin rótulo por una errata es peor que uno con el rótulo por
    defecto: el segundo se puede corregir, el primero no se ve.
    """
    assert not es_valida("BTC")
    assert resolver("BTC", "ETH") == POR_DEFECTO
    assert set(MONEDAS) == {"MXN", "USD", "EUR"}


# --------------------------------------------------------------------------
# Agregar: el error que la firma hace imposible
# --------------------------------------------------------------------------


def test_no_hay_forma_de_sumar_monedas_distintas() -> None:
    """La firma es la mitad del control: no devuelve un número solo."""
    resultado = agregar([("MXN", Decimal(1000)), ("EUR", Decimal(1000))])
    assert resultado == {"MXN": Decimal(1000), "EUR": Decimal(1000)}
    assert unica(resultado) is None, (
        "Con dos monedas no hay una sola, y la pantalla tiene que enterarse "
        "para pintar el desglose en vez de un total inventado."
    )


def test_con_una_sola_moneda_si_hay_total() -> None:
    resultado = agregar([("MXN", Decimal(1000)), ("MXN", Decimal(500))])
    assert resultado == {"MXN": Decimal(1500)}
    assert unica(resultado) == "MXN"


def test_los_nulos_no_suman_y_tampoco_cuentan_como_cero() -> None:
    """DAT-12 aplicado al dinero: sin presupuesto cargado no es cero.

    Una moneda cuyos importes son todos nulos **no aparece**: si apareciera con
    0, la pantalla pintaría «$0» y diría que alguien decidió no gastar.
    """
    assert agregar([("MXN", None), ("EUR", None)]) == {}
    assert agregar([("MXN", None), ("MXN", Decimal(10))]) == {"MXN": Decimal(10)}
    assert unica(agregar([])) is None


def test_un_codigo_invalido_cae_al_por_defecto_al_agregar() -> None:
    """No se pierde el importe por una errata en la fila."""
    assert agregar([("XXX", Decimal(5))]) == {POR_DEFECTO: Decimal(5)}


# --------------------------------------------------------------------------
# Que llegue a donde se ve
# --------------------------------------------------------------------------


async def _sesion(client, db_session):
    """Un inquilino con administrador, listo para pedir con permisos."""
    from tests.factories import create_admin_role, create_tenant, create_user, login

    t = await create_tenant(db_session)
    rol = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="mon", email="mon@acme.example.com",
        password="Str0ng-Admin-1!", roles=[rol],
    )
    return await login(client, "mon", "Str0ng-Admin-1!")


@pytest.mark.asyncio
async def test_el_proyecto_publica_su_moneda_resuelta(client, db_session) -> None:
    """Nunca sale vacía: quien la lea no tiene que conocer la regla del nulo."""
    auth = await _sesion(client, db_session)
    org = await client.post(
        "/api/v1/organizations", json={"name": "OrgMoneda"}, headers=auth["_authz"]
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    creado = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto en euros", "description": "d", "type": "innovacion",
            "priority": 3, "organization_id": org.json()["id"],
            "pm_id": me.json()["id"], "budget": 1000, "currency": "EUR",
        },
        headers=auth["_authz"],
    )
    assert creado.status_code in (200, 201), creado.text
    assert creado.json()["currency"] == "EUR", (
        "El proyecto no conservó la moneda elegida. Es la mitad de la decisión "
        "del owner: «deben poder escoger la que necesite el proyecto»."
    )

    sin_elegir = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto sin moneda", "description": "d", "type": "innovacion",
            "priority": 3, "organization_id": org.json()["id"],
            "pm_id": me.json()["id"], "budget": 500,
        },
        headers=auth["_authz"],
    )
    assert sin_elegir.status_code in (200, 201), sin_elegir.text
    assert es_valida(sin_elegir.json()["currency"]), (
        "Un proyecto sin moneda propia salió sin ninguna. El nulo significa «la "
        "del inquilino», y eso lo resuelve la API — no quien la consume."
    )


@pytest.mark.asyncio
async def test_el_tablero_agrega_por_moneda(client, db_session) -> None:
    """La forma del dato es la que impide sumar peras con manzanas aguas abajo."""
    auth = await _sesion(client, db_session)
    r = await client.get("/api/v1/dashboard/kpis", headers=auth["_authz"])
    assert r.status_code == 200
    datos = r.json()
    assert "budget_by_currency" in datos, (
        "El tablero dejó de publicar el desglose. Sin él, la pantalla no puede "
        "distinguir «un total» de «varias monedas» y volverá a inventar uno."
    )
    assert isinstance(datos["budget_by_currency"], dict)
    for codigo in datos["budget_by_currency"]:
        assert es_valida(codigo)


@pytest.mark.asyncio
async def test_la_preferida_del_inquilino_llega_al_frontend(client, db_session) -> None:
    """Viaja por `tenant-branding`, igual que `org_label` y por el mismo motivo:
    es un dato de presentación que toda pantalla necesita."""
    auth = await _sesion(client, db_session)
    r = await client.get("/api/v1/me/tenant-branding", headers=auth["_authz"])
    assert r.status_code == 200
    assert es_valida(r.json().get("preferred_currency"))


# --------------------------------------------------------------------------
# Los dos lados de la frontera dicen lo mismo
# --------------------------------------------------------------------------


def test_el_frontend_declara_las_mismas_monedas() -> None:
    """Dos listas del mismo vocabulario divergen. Ya pasó con los colores.

    El desplegable ofrecería una moneda que el servidor rechaza, o al revés, y
    el síntoma sería un error de validación sin explicación en un formulario.
    """
    import re
    from pathlib import Path

    fuente = (
        Path(__file__).resolve().parents[3] / "apps" / "web" / "lib" / "moneda.ts"
    ).read_text(encoding="utf-8")
    m = re.search(r"export const MONEDAS = \[(.*?)\] as const;", fuente, re.S)
    assert m
    del_web = {c.strip().strip('"') for c in m.group(1).split(",") if c.strip()}
    assert del_web == set(MONEDAS), (
        f"El frontend admite {sorted(del_web)} y el dominio {sorted(MONEDAS)}."
    )
    assert f'export const POR_DEFECTO = "{POR_DEFECTO}";' in fuente, (
        "El valor por defecto difiere entre los dos lados. Un importe sin "
        "moneda se rotularía distinto según quién lo pinte."
    )
