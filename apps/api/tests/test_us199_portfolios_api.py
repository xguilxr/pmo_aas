"""US-199 — la superficie de la jerarquía nueva, y el retiro de la vieja.

Lo que se defiende aquí, y por qué cada cosa necesita su caso:

1. **El CRUD de portafolios por rol.** `organizations` sigue el modelo
   «read/create/update libre, delete solo admin» (`core/permissions.py`), así que
   un usuario plano puede dar de alta un portafolio y **no** puede mandarlo a la
   papelera. Probar solo con administrador dejaría sin verificar la mitad que
   importa: la que dice quién *no* puede.
2. **La herencia de la solicitud al proyecto.** La clasificación se elige antes
   de que el proyecto exista; si no se heredaran los dos campos, el proyecto
   aprobado aparecería sin portafolio y alguien tendría que reclasificarlo.
3. **Que las rutas viejas devuelvan 404** — vive en `test_ep002_orgs.py`, junto
   al CRUD que reemplazan.
4. **La papelera de dos pasos** (ADR-017) y su cascada, que borra proyectos: es
   la operación más destructiva que esta US añade, y el preview es lo único que
   la separa de un clic accidental.
5. **Que la migración 0109 se niegue a soltar columnas con datos.** El owner
   confirmó que BU/departamentos nunca se usaron, pero eso es una afirmación
   sobre una instalación. Si otra tuviera filas, una migración que las tira en
   silencio es peor que una que no corre.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession

from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.models.organization import Program
from app.models.project import Project
from app.models.project_charter import ProjectCharter
from app.models.project_request import ProjectRequest
from tests.factories import create_admin_role, create_tenant, create_user, login

RAIZ_API = Path(__file__).resolve().parents[1]
MIGRACION = RAIZ_API / "alembic" / "versions" / "20260819_0109_retiro_bu_depto.py"


async def _admin(client, db_session, slug: str = "us199"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    rol = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username=f"adm{slug}",
        email=f"adm{slug}@pmoaas.example.com",
        password="Str0ng-R-1!",
        roles=[rol],
    )
    await db_session.commit()
    auth = await login(client, f"adm{slug}@pmoaas.example.com", "Str0ng-R-1!")
    return t, auth


async def _usuario_plano(client, db_session, tenant, slug: str):
    await create_user(
        db_session,
        tenant=tenant,
        username=f"usr{slug}",
        email=f"usr{slug}@pmoaas.example.com",
        password="Str0ng-R-1!",
        role_type="user",
    )
    await db_session.commit()
    return await login(client, f"usr{slug}@pmoaas.example.com", "Str0ng-R-1!")


async def _org(client, auth, name: str = "Org US199") -> str:
    r = await client.post(
        "/api/v1/organizations", json={"name": name}, headers=auth["_authz"]
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --------------------------------------------------------------------------
# 1. CRUD por rol
# --------------------------------------------------------------------------


async def test_tc_crud_de_portafolio_admin_y_usuario(client, db_session) -> None:
    """TC-199.1 — el ciclo completo, y el límite del usuario plano."""
    t, auth = await _admin(client, db_session, slug="pfcrud")
    org_id = await _org(client, auth)
    auth_user = await _usuario_plano(client, db_session, t, "pfcrud")

    # Alta: el usuario plano puede (organizations.create es libre).
    creado = await client.post(
        f"/api/v1/organizations/{org_id}/portfolios",
        json={"name": "Transformación 2026", "code": "TRX26", "description": "La apuesta"},
        headers=auth_user["_authz"],
    )
    assert creado.status_code == 201, creado.text
    pf = creado.json()
    assert pf["code"] == "TRX26"
    assert pf["program_count"] == 0 and pf["active_project_count"] == 0

    # Lectura y edición: también.
    leido = await client.get(f"/api/v1/portfolios/{pf['id']}", headers=auth_user["_authz"])
    assert leido.status_code == 200
    editado = await client.patch(
        f"/api/v1/portfolios/{pf['id']}",
        json={"description": "La apuesta del año"},
        headers=auth_user["_authz"],
    )
    assert editado.status_code == 200
    assert editado.json()["description"] == "La apuesta del año"

    # Papelera: **no**. `organizations.delete` es solo de administrador.
    negado = await client.delete(
        f"/api/v1/portfolios/{pf['id']}", headers=auth_user["_authz"]
    )
    assert negado.status_code == 403, (
        "Un usuario plano no manda portafolios a la papelera: `organizations."
        "delete` es capacidad de administrador (DEC-024)."
    )

    # Y el administrador sí.
    borrado = await client.delete(
        f"/api/v1/portfolios/{pf['id']}", headers=auth["_authz"]
    )
    assert borrado.status_code == 204


async def test_los_conteos_del_portafolio_son_derivados(client, db_session) -> None:
    """Un portafolio no guarda métricas (ADR-037): las cuenta al leerlo."""
    t, auth = await _admin(client, db_session, slug="pfcont")
    org_id = await _org(client, auth)
    pf = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Con cosas dentro"},
            headers=auth["_authz"],
        )
    ).json()

    prog = (
        await client.post(
            "/api/v1/programs",
            json={
                "name": "Prog dentro",
                "organization_id": org_id,
                "portfolio_id": pf["id"],
            },
            headers=auth["_authz"],
        )
    ).json()
    assert prog["portfolio_id"] == pf["id"]

    db_session.add_all(
        [
            Project(
                tenant_id=t.id,
                organization_id=org_id,
                portfolio_id=pf["id"],
                program_id=prog["id"],
                folio="PRJ-A",
                name="En el programa",
                phase="execution",
            ),
            Project(
                tenant_id=t.id,
                organization_id=org_id,
                portfolio_id=pf["id"],
                folio="PRJ-B",
                name="Directo al portafolio",
                phase="planning",
            ),
            Project(
                tenant_id=t.id,
                organization_id=org_id,
                portfolio_id=pf["id"],
                folio="PRJ-C",
                name="Cerrado, no cuenta",
                phase="closed",
            ),
        ]
    )
    await db_session.commit()

    leido = (
        await client.get(f"/api/v1/portfolios/{pf['id']}", headers=auth["_authz"])
    ).json()
    assert leido["program_count"] == 1
    assert leido["active_project_count"] == 2, (
        "Cuenta los del programa y los directos, y excluye los cerrados."
    )


async def test_el_portafolio_de_otra_organizacion_no_agrupa_programas(
    client, db_session
) -> None:
    """La jerarquía es un árbol: el alta de programa lo hace cumplir."""
    _, auth = await _admin(client, db_session, slug="pfarbol")
    org_a = await _org(client, auth, name="Org A")
    org_b = await _org(client, auth, name="Org B")
    pf_a = (
        await client.post(
            f"/api/v1/organizations/{org_a}/portfolios",
            json={"name": "Cartera de A"},
            headers=auth["_authz"],
        )
    ).json()

    r = await client.post(
        "/api/v1/programs",
        json={"name": "Prog de B", "organization_id": org_b, "portfolio_id": pf_a["id"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text


async def test_mover_un_programa_de_portafolio_arrastra_sus_proyectos(
    client, db_session
) -> None:
    """Sin el arrastre, los proyectos se quedan en el portafolio viejo y el par
    programa/portafolio queda incoherente en el instante siguiente."""
    t, auth = await _admin(client, db_session, slug="pfmueve")
    org_id = await _org(client, auth)
    origen = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Origen"},
            headers=auth["_authz"],
        )
    ).json()
    destino = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Destino"},
            headers=auth["_authz"],
        )
    ).json()
    prog = (
        await client.post(
            "/api/v1/programs",
            json={
                "name": "Prog viajero",
                "organization_id": org_id,
                "portfolio_id": origen["id"],
            },
            headers=auth["_authz"],
        )
    ).json()
    proyecto = Project(
        tenant_id=t.id,
        organization_id=org_id,
        portfolio_id=origen["id"],
        program_id=prog["id"],
        folio="PRJ-MOV",
        name="Viaja con su programa",
        phase="execution",
    )
    db_session.add(proyecto)
    await db_session.commit()

    r = await client.patch(
        f"/api/v1/programs/{prog['id']}",
        json={"portfolio_id": destino["id"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["portfolio_id"] == destino["id"]

    await db_session.refresh(proyecto)
    assert str(proyecto.portfolio_id) == destino["id"], (
        "El proyecto se quedó en el portafolio viejo: la vista del destino "
        "mostraría el programa sin sus proyectos."
    )


# --------------------------------------------------------------------------
# 2. Proyectos y solicitudes con la regla de consistencia
# --------------------------------------------------------------------------


async def test_el_proyecto_hereda_el_portafolio_de_su_programa(
    client, db_session
) -> None:
    """Se manda solo el programa; el portafolio se autocompleta."""
    t, auth = await _admin(client, db_session, slug="pjhered")
    org_id = await _org(client, auth)
    pf = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Cartera"},
            headers=auth["_authz"],
        )
    ).json()
    prog = (
        await client.post(
            "/api/v1/programs",
            json={"name": "Prog", "organization_id": org_id, "portfolio_id": pf["id"]},
            headers=auth["_authz"],
        )
    ).json()
    pm = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()

    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto heredado",
            "description": "Nace clasificado",
            "type": "transformation",
            "priority": 3,
            "organization_id": org_id,
            "program_id": prog["id"],
            "pm_id": pm["id"],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["portfolio_id"] == pf["id"]


async def test_el_proyecto_con_par_incoherente_se_rechaza(client, db_session) -> None:
    _, auth = await _admin(client, db_session, slug="pjincoh")
    org_id = await _org(client, auth)
    pf_a = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Cartera A"},
            headers=auth["_authz"],
        )
    ).json()
    pf_b = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Cartera B"},
            headers=auth["_authz"],
        )
    ).json()
    prog_a = (
        await client.post(
            "/api/v1/programs",
            json={"name": "Prog A", "organization_id": org_id, "portfolio_id": pf_a["id"]},
            headers=auth["_authz"],
        )
    ).json()
    pm = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()

    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto mentiroso",
            "description": "Dice dos cosas distintas",
            "type": "operation",
            "priority": 3,
            "organization_id": org_id,
            "program_id": prog_a["id"],
            "portfolio_id": pf_b["id"],
            "pm_id": pm["id"],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text


async def test_tc_la_solicitud_clasificada_pasa_su_clasificacion_al_proyecto(
    client, db_session
) -> None:
    """TC-199.2 — solicitud con portafolio/programa → proyecto con los dos."""
    t, auth = await _admin(client, db_session, slug="solher")
    org_id = await _org(client, auth)
    pf = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Cartera de la solicitud"},
            headers=auth["_authz"],
        )
    ).json()
    prog = (
        await client.post(
            "/api/v1/programs",
            json={"name": "Prog", "organization_id": org_id, "portfolio_id": pf["id"]},
            headers=auth["_authz"],
        )
    ).json()
    pm = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()

    # La solicitud se manda con el programa; el portafolio se autocompleta.
    sol = await client.post(
        "/api/v1/project-requests",
        json={
            "title": "Solicitud clasificada",
            "description": "Con su sitio en la jerarquía",
            "objective": "Que el proyecto nazca clasificado",
            "organization_id": org_id,
            "business_unit": "Dirección de Operaciones",
            "department": "Mejora continua",
            "program_id": prog["id"],
            "sponsor": "Quien paga",
            "sponsor_email": "sponsor@example.com",
            "benefits": "Ahorro",
            "scope": "Lo acordado",
        },
        headers=auth["_authz"],
    )
    assert sol.status_code == 201, sol.text
    cuerpo = sol.json()
    assert cuerpo["portfolio_id"] == pf["id"], (
        "La solicitud no autocompletó el portafolio desde su programa."
    )
    assert cuerpo["program_id"] == prog["id"]
    # El texto libre sobrevive: son las palabras del solicitante, no la
    # jerarquía de la plataforma.
    assert cuerpo["business_unit"] == "Dirección de Operaciones"

    revision = await client.post(
        f"/api/v1/project-requests/{cuerpo['id']}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    assert revision.status_code == 200, revision.text
    aprobada = await client.post(
        f"/api/v1/project-requests/{cuerpo['id']}/create-project",
        json={"pm_id": pm["id"]},
        headers=auth["_authz"],
    )
    assert aprobada.status_code in (200, 201), aprobada.text

    pr = (
        await db_session.execute(
            select(ProjectRequest).where(ProjectRequest.id == cuerpo["id"])
        )
    ).scalar_one()
    proyecto = (
        await db_session.execute(select(Project).where(Project.id == str(pr.project_id)))
    ).scalar_one()
    assert str(proyecto.portfolio_id) == pf["id"]
    assert str(proyecto.program_id) == prog["id"]

    acta = (
        await db_session.execute(
            select(ProjectCharter).where(ProjectCharter.project_id == proyecto.id)
        )
    ).scalar_one()
    assert str(acta.portfolio_id) == pf["id"], (
        "El acta y su proyecto no pueden decir cosas distintas sobre dónde vive "
        "el trabajo."
    )


# --------------------------------------------------------------------------
# 3. Papelera de dos pasos (ADR-017)
# --------------------------------------------------------------------------


async def test_el_borrado_permanente_declara_lo_que_se_lleva(client, db_session) -> None:
    """El preview separa tres cosas distintas de aceptar, y el segundo paso
    exige que el portafolio esté ya en la papelera."""
    t, auth = await _admin(client, db_session, slug="pfhard")
    org_id = await _org(client, auth)
    pf = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Se va"},
            headers=auth["_authz"],
        )
    ).json()
    prog = (
        await client.post(
            "/api/v1/programs",
            json={"name": "Prog", "organization_id": org_id, "portfolio_id": pf["id"]},
            headers=auth["_authz"],
        )
    ).json()
    en_programa = Project(
        tenant_id=t.id,
        organization_id=org_id,
        portfolio_id=pf["id"],
        program_id=prog["id"],
        folio="PRJ-EN",
        name="Cae con su programa",
        phase="execution",
    )
    directo = Project(
        tenant_id=t.id,
        organization_id=org_id,
        portfolio_id=pf["id"],
        folio="PRJ-DIR",
        name="Solo pierde la clasificación",
        phase="execution",
    )
    db_session.add_all([en_programa, directo])
    await db_session.commit()
    id_en_programa, id_directo = str(en_programa.id), str(directo.id)

    previa = await client.get(
        f"/api/v1/portfolios/{pf['id']}/hard-delete-preview", headers=auth["_authz"]
    )
    assert previa.status_code == 200, previa.text
    datos = previa.json()
    assert datos["cascades"] == {
        "programs": 1,
        "projects_in_programs": 1,
        "projects_direct": 1,
    }

    # Sin pasar antes por la papelera → 409.
    prematuro = await client.delete(
        f"/api/v1/portfolios/{pf['id']}/permanent?confirm={datos['confirm_slug']}",
        headers=auth["_authz"],
    )
    assert prematuro.status_code == 409, prematuro.text

    await client.delete(
        f"/api/v1/portfolios/{pf['id']}?force=true", headers=auth["_authz"]
    )

    # Con el slug equivocado → 400, con el preview fresco en `fields` para que
    # el modal pueda repintarse con datos de ahora (`core/hard_delete.py`).
    mal = await client.delete(
        f"/api/v1/portfolios/{pf['id']}/permanent?confirm=portfolio:otro-nombre",
        headers=auth["_authz"],
    )
    assert mal.status_code == 400
    assert "preview" in mal.json()["detail"]["fields"]

    bien = await client.delete(
        f"/api/v1/portfolios/{pf['id']}/permanent?confirm={datos['confirm_slug']}",
        headers=auth["_authz"],
    )
    assert bien.status_code == 204, bien.text

    # El endpoint escribió por su propia sesión: sin expirar, el mapa de
    # identidad de esta devolvería los valores de antes del borrado. Los ids se
    # capturaron arriba porque tras expirar leerlos sería IO en un contexto
    # síncrono.
    db_session.expire_all()

    # El del programa se fue; el directo sigue, sin clasificación.
    assert (
        await db_session.execute(select(Project).where(Project.id == id_en_programa))
    ).scalar_one_or_none() is None
    sobreviviente = (
        await db_session.execute(select(Project).where(Project.id == id_directo))
    ).scalar_one_or_none()
    assert sobreviviente is not None, (
        "Un proyecto que cuelga directo del portafolio no se borra por un "
        "cambio de taxonomía: se desreferencia."
    )
    assert sobreviviente.portfolio_id is None
    assert (
        await db_session.execute(select(Program).where(Program.id == prog["id"]))
    ).scalar_one_or_none() is None


async def test_el_borrado_permanente_suelta_las_solicitudes_que_lo_apuntan(
    client, db_session
) -> None:
    """Una solicitud puede clasificarse y no llegar nunca a proyecto.

    `project_requests.{portfolio_id, program_id}` son claves ajenas sin
    `ondelete`: sin soltarlas, el borrado permanente choca contra la restricción
    y devuelve un 500 a quien acababa de escribir el nombre para confirmar. Y se
    sueltan, no se borran: una solicitud es el registro de lo que alguien pidió.
    """
    t, auth = await _admin(client, db_session, slug="pfsol")
    org_id = await _org(client, auth)
    pf = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Con solicitud dentro"},
            headers=auth["_authz"],
        )
    ).json()
    prog = (
        await client.post(
            "/api/v1/programs",
            json={"name": "Prog", "organization_id": org_id, "portfolio_id": pf["id"]},
            headers=auth["_authz"],
        )
    ).json()
    sol = (
        await client.post(
            "/api/v1/project-requests",
            json={
                "title": "Nunca aprobada",
                "description": "Se queda en solicitud",
                "objective": "Probar el borrado",
                "organization_id": org_id,
                "business_unit": "Operaciones",
                "department": "Mejora",
                "program_id": prog["id"],
                "sponsor": "Quien pide",
                "sponsor_email": "pide@example.com",
                "benefits": "Ninguno todavía",
                "scope": "Lo pedido",
            },
            headers=auth["_authz"],
        )
    ).json()
    assert sol["portfolio_id"] == pf["id"]

    previa = await client.get(
        f"/api/v1/portfolios/{pf['id']}/hard-delete-preview", headers=auth["_authz"]
    )
    slug = previa.json()["confirm_slug"]
    await client.delete(f"/api/v1/portfolios/{pf['id']}?force=true", headers=auth["_authz"])
    r = await client.delete(
        f"/api/v1/portfolios/{pf['id']}/permanent?confirm={slug}",
        headers=auth["_authz"],
    )
    assert r.status_code == 204, r.text

    db_session.expire_all()
    quedo = (
        await db_session.execute(
            select(ProjectRequest).where(ProjectRequest.id == sol["id"])
        )
    ).scalar_one_or_none()
    assert quedo is not None, "La solicitud se borró; solo tenía que perder su sitio."
    assert quedo.portfolio_id is None
    assert quedo.program_id is None


# --------------------------------------------------------------------------
# 4. La migración 0109 no suelta columnas con datos
# --------------------------------------------------------------------------


def _cargar_migracion() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migracion_0109", MIGRACION)
    assert spec and spec.loader, f"No pude cargar {MIGRACION}"
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _tabla_previa(modelo: type, md: sa.MetaData, *, sumar: tuple[str, ...] = ()) -> sa.Table:
    """La tabla del modelo con las columnas que 0109 suelta, sin claves ajenas.

    Es el esquema de «antes»: los nombres y tipos se copian del modelo real
    —así la prueba sigue al esquema— y las columnas retiradas se vuelven a
    añadir a mano, porque el modelo ya no las tiene.
    """
    origen = modelo.__table__
    columnas = [
        c._copy()
        for c in origen.columns
        if c.name not in ("portfolio_id", "program_id") or c.name in sumar
    ]
    columnas += [sa.Column(nombre, sa.String(36), nullable=True) for nombre in sumar]
    return sa.Table(origen.name, md, *columnas)


def _esquema_previo(md: sa.MetaData) -> dict[str, sa.Table]:
    from app.models.organization import Program as Prog

    return {
        "programs": _tabla_previa(Prog, md, sumar=("department_id",)),
        "projects": _tabla_previa(
            Project, md, sumar=("business_unit_id", "department_id")
        ),
        "project_requests": _tabla_previa(
            ProjectRequest, md, sumar=("business_unit_id", "department_id")
        ),
        "project_charters": _tabla_previa(
            ProjectCharter, md, sumar=("business_unit_id", "department_id")
        ),
    }


def test_tc_la_migracion_suelta_las_columnas_cuando_estan_vacias(tmp_path: Path) -> None:
    """TC-199.3 — el camino normal: vacías, se sueltan, y la bajada las devuelve."""
    modulo = _cargar_migracion()
    md = sa.MetaData()
    tablas = _esquema_previo(md)
    motor = create_engine(f"sqlite:///{tmp_path / 'us199.db'}")
    try:
        with motor.begin() as cx:
            md.create_all(cx)
            cx.execute(
                tablas["programs"].insert(),
                [
                    {
                        "id": str(uuid4()),
                        "tenant_id": str(uuid4()),
                        "organization_id": str(uuid4()),
                        "portfolio_id": str(uuid4()),
                        "name": "Sin departamento",
                    }
                ],
            )

        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.upgrade()

        with motor.connect() as cx:
            inspector = sa.inspect(cx)
            for tabla, columna in modulo.A_SOLTAR:
                cols = {c["name"] for c in inspector.get_columns(tabla)}
                assert columna not in cols, f"{tabla}.{columna} sigue ahí"
            for tabla, columna, _ in modulo.A_CREAR:
                cols = {c["name"] for c in inspector.get_columns(tabla)}
                assert columna in cols, f"falta {tabla}.{columna}"

        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.downgrade()

        with motor.connect() as cx:
            inspector = sa.inspect(cx)
            for tabla, columna in modulo.A_SOLTAR:
                cols = {c["name"] for c in inspector.get_columns(tabla)}
                assert columna in cols, (
                    f"`downgrade` no devolvió {tabla}.{columna}. El job del CI "
                    "corre `downgrade base` y esto lo destaparía tarde."
                )
    finally:
        motor.dispose()


def test_tc_la_migracion_se_niega_si_queda_una_referencia_viva(tmp_path: Path) -> None:
    """TC-199.4 — con datos, para, y dice cuántos y dónde.

    «Nunca se usaron» es una afirmación sobre una instalación. Una migración que
    descarta en silencio datos que no esperaba es peor que una que no corre.
    """
    modulo = _cargar_migracion()
    md = sa.MetaData()
    tablas = _esquema_previo(md)
    motor = create_engine(f"sqlite:///{tmp_path / 'us199-residuo.db'}")
    try:
        with motor.begin() as cx:
            md.create_all(cx)
            cx.execute(
                tablas["projects"].insert(),
                [
                    {
                        "id": str(uuid4()),
                        "tenant_id": str(uuid4()),
                        "organization_id": str(uuid4()),
                        "business_unit_id": str(uuid4()),  # ← el residuo
                        "folio": "PRJ-RES",
                        "name": "Con unidad de negocio",
                        "phase": "planning",
                        "progress": 0,
                        "health_status": "green",
                        "health_source": "auto",
                        "manually_edited_fields": {},
                    }
                ],
            )

        with motor.begin() as cx, pytest.raises(RuntimeError) as exc:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.upgrade()
        assert "projects.business_unit_id" in str(exc.value)
        assert "audit_log" in str(exc.value)

        # Y no soltó nada: la columna sigue, con su fila.
        with motor.connect() as cx:
            cols = {c["name"] for c in sa.inspect(cx).get_columns("projects")}
            assert "business_unit_id" in cols
            assert cx.execute(sa.text("SELECT COUNT(*) FROM projects")).scalar() == 1
    finally:
        motor.dispose()


async def test_el_panel_de_la_organizacion_anida_programas_en_portafolios(
    client, db_session: AsyncSession
) -> None:
    """La sección de jerarquía del panel pasa a ser portafolio ⊃ programa."""
    _, auth = await _admin(client, db_session, slug="pfpanel")
    org_id = await _org(client, auth)
    pf = (
        await client.post(
            f"/api/v1/organizations/{org_id}/portfolios",
            json={"name": "Cartera del panel"},
            headers=auth["_authz"],
        )
    ).json()
    await client.post(
        "/api/v1/programs",
        json={"name": "Prog anidado", "organization_id": org_id, "portfolio_id": pf["id"]},
        headers=auth["_authz"],
    )

    r = await client.get(
        f"/api/v1/organizations/{org_id}/panel", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    datos = r.json()
    assert "business_units" not in datos
    assert len(datos["portfolios"]) == 1
    portafolio = datos["portfolios"][0]
    assert portafolio["name"] == "Cartera del panel"
    assert [p["name"] for p in portafolio["programs"]] == ["Prog anidado"]
    # La lista plana sigue estando, para quien solo necesita los programas.
    assert [p["name"] for p in datos["programs"]] == ["Prog anidado"]
    assert datos["programs"][0]["portfolio_id"] == pf["id"]
