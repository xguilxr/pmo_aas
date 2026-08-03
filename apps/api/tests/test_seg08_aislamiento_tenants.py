"""SEG-08 — aislamiento entre inquilinos.

Auditoría MCS 2026-08-03, hallazgo T-4. Este es un producto multiinquilino y
182 archivos de prueba tocaban `tenant_id`, así que había cobertura **de hecho**.
Lo que no había era una prueba cuyo único propósito sea **fallar si el filtro
por inquilino desaparece**. La diferencia importa: si alguien quita un
`where tenant_id ==`, con cobertura de hecho puede que algún test falle por
casualidad; con esta suite falla por diseño y el mensaje dice por qué.

El aislamiento aquí no lo garantiza un mecanismo central: cada endpoint debe
acordarse de filtrar por `CurrentUser.effective_tenant_id` (hallazgo T-3). Esa
es exactamente la razón por la que hace falta esta red.

Forma de cada caso: un usuario del tenant A intenta alcanzar un objeto del
tenant B **por su identificador**. La respuesta correcta es 403 o 404. Nunca
200, y nunca una modificación aplicada.

VERIFICADA POR MUTACIÓN el 2026-08-03: al quitar `Project.tenant_id == tenant_id`
de `_get_project` en endpoints/projects.py, esta suite falla en tres casos —
lectura (200), modificación (200) y borrado (204, el proyecto ajeno desaparece
de verdad). Ocho tests verdes no demuestran nada si no se comprueba que sepan
ponerse rojos.
"""
from uuid import uuid4

import pytest

from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    login,
)

# Un 200 aquí es una fuga entre clientes. Un 500 tampoco vale: significa que el
# filtro no está y el fallo llegó hasta la base de datos.
ACEPTABLES = {403, 404}


async def _tenant_con_admin(db, sufijo: str):
    """Crea un tenant con su admin. Devuelve (tenant, usuario, contraseña)."""
    t = await create_tenant(db, slug=f"iso-{sufijo}", name=f"Iso {sufijo.upper()}")
    rol = await create_admin_role(db, t)
    clave = f"Str0ng-Pass-{sufijo}{uuid4().hex[:4]}!"
    u = await create_user(
        db,
        tenant=t,
        username=f"admin-{sufijo}",
        email=f"admin-{sufijo}@iso.example.com",
        password=clave,
        roles=[rol],
        role_type="admin",
    )
    return t, u, clave


@pytest.fixture
async def dos_tenants(db_session, client):
    """Dos tenants con datos propios y sesiones separadas.

    Devuelve un dict con lo necesario para cruzar peticiones entre ambos.
    """
    a, ua, clave_a = await _tenant_con_admin(db_session, "a")
    b, ub, clave_b = await _tenant_con_admin(db_session, "b")
    await db_session.commit()

    sesion_a = await login(client, ua.email, clave_a)
    sesion_b = await login(client, ub.email, clave_b)

    # Datos que viven en B. A no debe poder verlos ni tocarlos.
    org_b = await client.post(
        "/api/v1/organizations",
        json={"name": "Org de B", "code": "ORGB"},
        headers=sesion_b["_authz"],
    )
    assert org_b.status_code in (200, 201), org_b.text
    org_b_id = org_b.json()["id"]

    proy_b = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto de B",
            "description": "Datos que el tenant A no debe alcanzar",
            "type": "operation",
            "priority": 3,
            "organization_id": org_b_id,
            "pm_id": str(ub.id),
        },
        headers=sesion_b["_authz"],
    )
    assert proy_b.status_code in (200, 201), proy_b.text

    return {
        "authz_a": sesion_a["_authz"],
        "authz_b": sesion_b["_authz"],
        "org_b": org_b_id,
        "proyecto_b": proy_b.json()["id"],
        "pm_a": str(ua.id),
        "tenant_a": str(a.id),
        "tenant_b": str(b.id),
    }


# ── Lectura ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seg08_no_lee_organizacion_de_otro_tenant(client, dos_tenants):
    r = await client.get(
        f"/api/v1/organizations/{dos_tenants['org_b']}",
        headers=dos_tenants["authz_a"],
    )
    assert r.status_code in ACEPTABLES, (
        f"FUGA ENTRE INQUILINOS: el tenant A leyó la organización del tenant B "
        f"(HTTP {r.status_code}). Falta el filtro por tenant en el endpoint."
    )


@pytest.mark.asyncio
async def test_seg08_no_lee_proyecto_de_otro_tenant(client, dos_tenants):
    r = await client.get(
        f"/api/v1/projects/{dos_tenants['proyecto_b']}",
        headers=dos_tenants["authz_a"],
    )
    assert r.status_code in ACEPTABLES, (
        f"FUGA ENTRE INQUILINOS: el tenant A leyó el proyecto del tenant B "
        f"(HTTP {r.status_code}). Falta el filtro por tenant en el endpoint."
    )


# ── Listados ───────────────────────────────────────────────────────────────
#
# Un listado que no filtra es peor que un GET por id que no filtra: no hace
# falta conocer el identificador para explotarlo.

@pytest.mark.asyncio
async def test_seg08_el_listado_de_organizaciones_no_incluye_otro_tenant(
    client, dos_tenants
):
    r = await client.get("/api/v1/organizations", headers=dos_tenants["authz_a"])
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    items = cuerpo if isinstance(cuerpo, list) else cuerpo.get("items", [])
    ids = {str(o.get("id")) for o in items}
    assert dos_tenants["org_b"] not in ids, (
        "FUGA ENTRE INQUILINOS: el listado de organizaciones del tenant A "
        "incluye una organización del tenant B."
    )


@pytest.mark.asyncio
async def test_seg08_el_listado_de_proyectos_no_incluye_otro_tenant(
    client, dos_tenants
):
    r = await client.get("/api/v1/projects", headers=dos_tenants["authz_a"])
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    items = cuerpo if isinstance(cuerpo, list) else cuerpo.get("items", [])
    ids = {str(p.get("id")) for p in items}
    assert dos_tenants["proyecto_b"] not in ids, (
        "FUGA ENTRE INQUILINOS: el listado de proyectos del tenant A incluye "
        "un proyecto del tenant B."
    )


# ── Escritura ──────────────────────────────────────────────────────────────
#
# Leer datos ajenos es una brecha. Modificarlos o borrarlos es peor, y son
# rutas distintas: que el GET filtre no implica que el PATCH lo haga.

@pytest.mark.asyncio
async def test_seg08_no_modifica_proyecto_de_otro_tenant(client, dos_tenants):
    r = await client.patch(
        f"/api/v1/projects/{dos_tenants['proyecto_b']}",
        json={"name": "Secuestrado por A"},
        headers=dos_tenants["authz_a"],
    )
    assert r.status_code in ACEPTABLES, (
        f"FUGA ENTRE INQUILINOS: el tenant A modificó el proyecto del tenant B "
        f"(HTTP {r.status_code})."
    )

    # Y comprobamos el efecto, no solo el código: un 4xx que igual escribió
    # sería peor que un 200 honesto.
    verificacion = await client.get(
        f"/api/v1/projects/{dos_tenants['proyecto_b']}",
        headers=dos_tenants["authz_b"],
    )
    assert verificacion.status_code == 200, verificacion.text
    assert verificacion.json()["name"] == "Proyecto de B", (
        "FUGA ENTRE INQUILINOS: la petición del tenant A devolvió error pero "
        "el cambio SÍ se aplicó sobre el dato del tenant B."
    )


@pytest.mark.asyncio
async def test_seg08_no_borra_proyecto_de_otro_tenant(client, dos_tenants):
    r = await client.delete(
        f"/api/v1/projects/{dos_tenants['proyecto_b']}",
        headers=dos_tenants["authz_a"],
    )
    assert r.status_code in ACEPTABLES, (
        f"FUGA ENTRE INQUILINOS: el tenant A borró el proyecto del tenant B "
        f"(HTTP {r.status_code})."
    )

    verificacion = await client.get(
        f"/api/v1/projects/{dos_tenants['proyecto_b']}",
        headers=dos_tenants["authz_b"],
    )
    assert verificacion.status_code == 200, (
        "FUGA ENTRE INQUILINOS: la petición del tenant A devolvió error pero "
        "el proyecto del tenant B desapareció."
    )


# ── Creación cruzada ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seg08_no_crea_proyecto_dentro_de_organizacion_ajena(
    client, dos_tenants
):
    """Pasar el identificador de una organización ajena en el cuerpo.

    El endpoint valida permisos sobre el usuario, pero el `organization_id`
    viene del cliente: si no se comprueba que pertenezca a su tenant, A puede
    sembrar datos dentro de B.
    """
    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "Infiltrado",
            "description": "Creado por A dentro de la organización de B",
            "type": "operation",
            "priority": 3,
            "organization_id": dos_tenants["org_b"],
            "pm_id": dos_tenants["pm_a"],
        },
        headers=dos_tenants["authz_a"],
    )
    assert r.status_code not in (200, 201), (
        f"FUGA ENTRE INQUILINOS: el tenant A creó un proyecto dentro de una "
        f"organización del tenant B (HTTP {r.status_code})."
    )


# ── Control negativo ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seg08_control_cada_tenant_si_ve_lo_suyo(client, dos_tenants):
    """Sin esto, la suite pasaría con un endpoint que devuelve 403 a todos.

    Un aislamiento que se logra rompiendo el producto no es aislamiento.
    """
    r = await client.get(
        f"/api/v1/projects/{dos_tenants['proyecto_b']}",
        headers=dos_tenants["authz_b"],
    )
    assert r.status_code == 200, (
        "El tenant B no puede ver su propio proyecto: las pruebas de "
        "aislamiento estarían pasando por la razón equivocada."
    )
