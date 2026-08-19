"""US-198 — el portafolio como agrupador, y la regla que lo mantiene coherente.

Tres cosas que probar, y son de naturaleza distinta:

1. **La regla de consistencia** (`services/jerarquia.py`): que un proyecto no
   pueda reportar a un programa y contar en otro portafolio. Se ejerce el
   servicio directo porque es donde vive la regla; los endpoints la consumen en
   US-199.
2. **El portafolio por defecto**: que dar de alta un programa por la API siga
   funcionando aunque `portfolio_id` sea `NOT NULL` y el payload todavía no lo
   traiga.
3. **El relleno de la migración 0108**: que los programas que ya existían
   acaben en el «Portafolio General» de **su** organización, y que los proyectos
   hereden el portafolio de su programa.

El tercero se ejerce corriendo `upgrade()` y `downgrade()` de verdad, con datos
sembrados antes, siguiendo el patrón de `test_dat06_migracion_0101.py`. La razón
está escrita allí y vale igual aquí: `alembic upgrade head` sobre una base limpia
prueba que el esquema se construye, no que una migración de **datos** haga lo
suyo — el bucle del relleno recorre cero filas en una base vacía.

**Por qué el relleno se ejerce sobre SQLite y no sobre Postgres.** El esquema de
«antes» se construye aquí a mano, y en Postgres las claves ajenas de `portfolios`
exigirían levantar además `tenants`, `organizations`, `users` y `actors` —con el
ciclo `actors/areas/teams` que ya avisa `conftest`— para probar un `UPDATE`. El
DDL contra el motor de producción lo cubre el job `api-migrations-postgres`
(`upgrade head` / `downgrade base` / `upgrade head`); lo que ese job **no** puede
cubrir es esto, porque su base no tiene filas. Son mitades distintas y aquí está
la que falta.

Las columnas del esquema de «antes» se **copian de los modelos**, no se
transcriben: si mañana `programs.organization_id` se renombra, esta prueba se
construye con el nombre nuevo y el relleno falla aquí en vez de en el despliegue.
Es la lección de la 0098 (ejercitar SQL de migración contra un sujeto inventado
no prueba nada), aplicada sin pagar el esquema completo.
"""
from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession

from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.core.errors import AppError
from app.models.organization import Organization, Portfolio, Program
from app.models.project import Project
from app.models.project_charter import ProjectCharter
from app.models.project_request import ProjectRequest
from app.services.jerarquia import (
    NOMBRE_PORTAFOLIO_GENERAL,
    portafolio_general,
    resolver_portafolio,
    validar_portafolio_de_organizacion,
)
from tests.factories import (
    create_admin_role,
    create_portfolio,
    create_program,
    create_tenant,
    create_user,
    login,
)

RAIZ_API = Path(__file__).resolve().parents[1]
MIGRACION = RAIZ_API / "alembic" / "versions" / "20260819_0108_portfolios.py"


# --------------------------------------------------------------------------
# 1. La regla de consistencia
# --------------------------------------------------------------------------


async def _org(db: AsyncSession, tenant_id: str, nombre: str = "Org A") -> Organization:
    org = Organization(tenant_id=tenant_id, name=nombre, is_active=True)
    db.add(org)
    await db.flush()
    return org


async def test_tc_portafolio_programa_y_proyecto_coherentes(db_session: AsyncSession) -> None:
    """TC-198.1 — portafolio → programa dentro → proyecto con ambos: consistente."""
    t = await create_tenant(db_session, slug="us198-a", name="US198 A")
    org = await _org(db_session, t.id)
    pf = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org.id, name="Transformación 2026"
    )
    prog = await create_program(
        db_session,
        tenant_id=t.id,
        organization_id=org.id,
        portfolio_id=str(pf.id),
        name="Prog Core",
    )

    # Con programa y sin portafolio: se autocompleta con el del programa.
    resuelto = await resolver_portafolio(
        db_session, tenant_id=t.id, program_id=prog.id, portfolio_id=None
    )
    assert resuelto == str(pf.id), (
        "Asignar programa tiene que autocompletar el portafolio; si no, el "
        "proyecto queda fuera de la vista ejecutiva de su propio portafolio."
    )

    # Con los dos y coincidiendo: se respeta.
    assert (
        await resolver_portafolio(
            db_session, tenant_id=t.id, program_id=prog.id, portfolio_id=str(pf.id)
        )
        == str(pf.id)
    )

    # Sin programa: el portafolio que venga, incluido ninguno.
    assert (
        await resolver_portafolio(
            db_session, tenant_id=t.id, program_id=None, portfolio_id=str(pf.id)
        )
        == str(pf.id)
    )
    assert (
        await resolver_portafolio(
            db_session, tenant_id=t.id, program_id=None, portfolio_id=None
        )
        is None
    )


async def test_tc_proyecto_con_programa_de_otro_portafolio_se_rechaza(
    db_session: AsyncSession,
) -> None:
    """TC-198.2 — par incoherente: el programa es de A y el portafolio es B."""
    t = await create_tenant(db_session, slug="us198-b", name="US198 B")
    org = await _org(db_session, t.id)
    pf_a = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org.id, name="Portafolio A"
    )
    pf_b = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org.id, name="Portafolio B"
    )
    prog_a = await create_program(
        db_session,
        tenant_id=t.id,
        organization_id=org.id,
        portfolio_id=str(pf_a.id),
        name="Prog A",
    )

    with pytest.raises(AppError) as exc:
        await resolver_portafolio(
            db_session, tenant_id=t.id, program_id=prog_a.id, portfolio_id=str(pf_b.id)
        )
    assert "programa" in str(exc.value.detail).lower()


async def test_el_programa_de_otro_inquilino_no_resuelve_portafolio(
    db_session: AsyncSession,
) -> None:
    """El filtro por inquilino no es decoración: sin él, un id ajeno resolvería
    el portafolio de otro y el proyecto acabaría contando en la cartera de otra
    empresa."""
    t1 = await create_tenant(db_session, slug="us198-c1", name="US198 C1")
    t2 = await create_tenant(db_session, slug="us198-c2", name="US198 C2")
    org2 = await _org(db_session, t2.id, nombre="Org de T2")
    prog_ajeno = await create_program(
        db_session, tenant_id=t2.id, organization_id=org2.id, name="Ajeno"
    )

    with pytest.raises(AppError):
        await resolver_portafolio(
            db_session, tenant_id=t1.id, program_id=prog_ajeno.id, portfolio_id=None
        )


async def test_el_portafolio_tiene_que_ser_de_la_organizacion_indicada(
    db_session: AsyncSession,
) -> None:
    """La jerarquía es un árbol: un portafolio de la organización A no agrupa
    nada de la B, o los conteos por organización dejan de sumar."""
    t = await create_tenant(db_session, slug="us198-d", name="US198 D")
    org_a = await _org(db_session, t.id, nombre="Org A")
    org_b = await _org(db_session, t.id, nombre="Org B")
    pf_a = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org_a.id, name="Portafolio de A"
    )

    await validar_portafolio_de_organizacion(
        db_session, tenant_id=t.id, organization_id=org_a.id, portfolio_id=str(pf_a.id)
    )
    with pytest.raises(AppError):
        await validar_portafolio_de_organizacion(
            db_session, tenant_id=t.id, organization_id=org_b.id, portfolio_id=str(pf_a.id)
        )
    # Sin portafolio no hay nada que validar (el campo es opcional en proyectos).
    await validar_portafolio_de_organizacion(
        db_session, tenant_id=t.id, organization_id=org_b.id, portfolio_id=None
    )


async def test_el_portafolio_general_se_reusa_no_se_duplica(db_session: AsyncSession) -> None:
    """Dos llamadas devuelven el mismo: un segundo «Portafolio General» chocaría
    con el índice único, y el fallo saldría en el alta de un programa."""
    t = await create_tenant(db_session, slug="us198-e", name="US198 E")
    org = await _org(db_session, t.id)
    primero = await portafolio_general(db_session, tenant_id=t.id, organization_id=org.id)
    segundo = await portafolio_general(db_session, tenant_id=t.id, organization_id=org.id)
    assert str(primero.id) == str(segundo.id)
    assert primero.name == NOMBRE_PORTAFOLIO_GENERAL

    cuantos = (
        await db_session.execute(
            select(sa.func.count())
            .select_from(Portfolio)
            .where(Portfolio.tenant_id == t.id, Portfolio.organization_id == org.id)
        )
    ).scalar()
    assert cuantos == 1



async def test_el_portafolio_general_borrado_se_revive(db_session: AsyncSession) -> None:
    """Si alguien borró el cajón por defecto, el alta siguiente lo revive.

    Las otras dos salidas son peores: crear un segundo choca con el índice único
    (el alta devuelve un 500), y devolverlo borrado mete el programa nuevo en un
    portafolio que ninguna pantalla lista — el programa desaparece sin aviso.
    """
    t = await create_tenant(db_session, slug="us198-f", name="US198 F")
    org = await _org(db_session, t.id)
    pf = await portafolio_general(db_session, tenant_id=t.id, organization_id=org.id)
    pf.deleted_at = datetime.now(UTC)
    pf.is_active = False
    await db_session.flush()

    revivido = await portafolio_general(db_session, tenant_id=t.id, organization_id=org.id)
    assert str(revivido.id) == str(pf.id)
    assert revivido.deleted_at is None
    assert revivido.is_active is True

# --------------------------------------------------------------------------
# 2. El alta de programa por la API sigue funcionando
# --------------------------------------------------------------------------


async def test_alta_de_programa_cae_en_el_portafolio_general(client, db_session) -> None:
    """`portfolio_id` es NOT NULL y el payload no lo trae todavía (US-199): el
    alta tiene que resolver el «Portafolio General» sola, o la pantalla de
    programas queda rota entre esta US y la siguiente."""
    t = await create_tenant(db_session, slug="us198-api", name="US198 API")
    rol = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="adm198",
        email="adm198@pmoaas.example.com",
        password="Str0ng-R-1!",
        roles=[rol],
    )
    await db_session.commit()
    auth = await login(client, "adm198@pmoaas.example.com", "Str0ng-R-1!")

    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "Org API"}, headers=auth["_authz"]
        )
    ).json()

    r = await client.post(
        "/api/v1/programs",
        json={"name": "Programa nuevo", "organization_id": org["id"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text

    prog = (
        await db_session.execute(select(Program).where(Program.id == r.json()["id"]))
    ).scalar_one()
    assert prog.portfolio_id is not None
    pf = (
        await db_session.execute(select(Portfolio).where(Portfolio.id == prog.portfolio_id))
    ).scalar_one()
    assert pf.name == NOMBRE_PORTAFOLIO_GENERAL
    assert str(pf.organization_id) == org["id"]


# --------------------------------------------------------------------------
# 3. El relleno de la migración 0108
# --------------------------------------------------------------------------


def _cargar_migracion() -> ModuleType:
    """Importa el módulo por ruta: `alembic/versions/` no es un paquete."""
    spec = importlib.util.spec_from_file_location("migracion_0108", MIGRACION)
    assert spec and spec.loader, f"No pude cargar {MIGRACION}"
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _tabla_previa(
    modelo: type,
    md: sa.MetaData,
    *,
    quitar: tuple[str, ...] = (),
    sumar: tuple[str, ...] = (),
) -> sa.Table:
    """La tabla del modelo como estaba **antes** de la 0108, sin claves ajenas.

    Los nombres y los tipos se copian del modelo real —es lo que hace que la
    prueba siga al esquema— y las restricciones se dejan fuera a propósito: lo
    que se ejerce es un `UPDATE`, y arrastrar las claves ajenas obligaría a
    levantar media base para no probar nada más.

    `quitar` saca lo que la 0108 añade. `sumar` devuelve lo que la **0109**
    soltó después: la 0108 cuenta las referencias de BU/departamento, así que
    cuando corrió esas columnas existían, y el modelo de hoy ya no las declara.
    """
    origen = modelo.__table__
    # `_copy()` y no el constructor de `Column`: hay que arrastrar también los
    # valores por defecto (`is_active`, los `timestamps`), y un `ColumnDefault`
    # ya ligado a otra columna no se puede pasar al constructor. Es el mismo
    # mecanismo que usa SQLAlchemy internamente para reflejar una tabla.
    columnas = [c._copy() for c in origen.columns if c.name not in quitar]
    columnas += [sa.Column(nombre, sa.String(36), nullable=True) for nombre in sumar]
    return sa.Table(origen.name, md, *columnas)


#: Un proyecto necesita más que su portafolio para existir: estas son las
#: columnas `NOT NULL` sin valor por defecto en el esquema.
def _proyecto(**campos: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": str(uuid4()),
        "folio": "PRJ-000",
        "name": "Proyecto",
        "phase": "planning",
        "progress": 0,
        "health_status": "green",
        "health_source": "auto",
        "manually_edited_fields": {},
    }
    base.update(campos)
    return base


def test_tc_la_migracion_reagrupa_los_programas_existentes(tmp_path: Path) -> None:
    """TC-198.3 — sobre una copia con programas: todos con «Portafolio General»
    de **su** organización, y los proyectos con el portafolio de su programa."""
    modulo = _cargar_migracion()
    md = sa.MetaData()
    programs = _tabla_previa(Program, md, quitar=("portfolio_id",), sumar=("department_id",))
    projects = _tabla_previa(
        Project, md, quitar=("portfolio_id",), sumar=("business_unit_id", "department_id")
    )
    _tabla_previa(
        ProjectRequest,
        md,
        quitar=("portfolio_id", "program_id"),
        sumar=("business_unit_id", "department_id"),
    )
    _tabla_previa(
        ProjectCharter,
        md,
        quitar=("portfolio_id", "program_id"),
        sumar=("business_unit_id", "department_id"),
    )

    t1, t2 = str(uuid4()), str(uuid4())
    org_a, org_b, org_c = str(uuid4()), str(uuid4()), str(uuid4())
    prog_a1, prog_a2, prog_b, prog_c = (str(uuid4()) for _ in range(4))

    motor = create_engine(f"sqlite:///{tmp_path / 'us198.db'}")
    try:
        with motor.begin() as cx:
            md.create_all(cx)
            cx.execute(
                programs.insert(),
                [
                    # Dos programas de la MISMA organización: tienen que caer en
                    # el mismo portafolio, no en uno cada uno.
                    {"id": prog_a1, "tenant_id": t1, "organization_id": org_a, "name": "A1"},
                    {"id": prog_a2, "tenant_id": t1, "organization_id": org_a, "name": "A2"},
                    # Otra organización del mismo inquilino: portafolio propio.
                    {"id": prog_b, "tenant_id": t1, "organization_id": org_b, "name": "B"},
                    # Otro inquilino: el aislamiento es lo que se comprueba aquí.
                    {"id": prog_c, "tenant_id": t2, "organization_id": org_c, "name": "C"},
                ],
            )
            cx.execute(
                projects.insert(),
                [
                    _proyecto(
                        tenant_id=t1, organization_id=org_a, program_id=prog_a1, folio="P-1"
                    ),
                    _proyecto(
                        tenant_id=t1, organization_id=org_b, program_id=prog_b, folio="P-2"
                    ),
                    # Sin programa: se queda sin portafolio, y eso es correcto —
                    # no hay de dónde deducirlo.
                    _proyecto(
                        tenant_id=t1, organization_id=org_a, program_id=None, folio="P-3"
                    ),
                ],
            )

        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.upgrade()

        with motor.connect() as cx:
            portafolios = cx.execute(
                sa.text("SELECT id, tenant_id, organization_id, name FROM portfolios")
            ).all()
            assert len(portafolios) == 3, (
                "Se esperaba un «Portafolio General» por organización CON "
                f"programas (3), y salieron {len(portafolios)}. Uno por programa "
                "significa que el relleno no agrupa; uno solo, que no aísla."
            )
            assert {p.name for p in portafolios} == {modulo.NOMBRE_PORTAFOLIO_GENERAL}
            por_org = {p.organization_id: p.id for p in portafolios}
            assert set(por_org) == {org_a, org_b, org_c}

            progs = dict(
                cx.execute(sa.text("SELECT id, portfolio_id FROM programs")).all()
            )
            assert progs[prog_a1] == por_org[org_a]
            assert progs[prog_a2] == por_org[org_a], (
                "Dos programas de la misma organización acabaron en portafolios "
                "distintos: el relleno crea uno por programa."
            )
            assert progs[prog_b] == por_org[org_b]
            assert progs[prog_c] == por_org[org_c]
            assert all(v is not None for v in progs.values()), (
                "Quedó un programa sin portafolio; en Postgres el `SET NOT NULL` "
                "de esta misma migración habría fallado."
            )

            proys = dict(
                cx.execute(sa.text("SELECT folio, portfolio_id FROM projects")).all()
            )
            assert proys["P-1"] == por_org[org_a], (
                "El proyecto no heredó el portafolio de su programa: nace "
                "violando la regla de consistencia de `jerarquia.py`."
            )
            assert proys["P-2"] == por_org[org_b]
            assert proys["P-3"] is None, (
                "Un proyecto sin programa no tiene de dónde deducir portafolio; "
                "inventarle uno sería clasificarlo por su cuenta."
            )

        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.downgrade()

        with motor.connect() as cx:
            tablas = sa.inspect(cx).get_table_names()
            assert "portfolios" not in tablas, "`downgrade` dejó la tabla nueva."
            for tabla in ("programs", "projects"):
                columnas = {c["name"] for c in sa.inspect(cx).get_columns(tabla)}
                assert "portfolio_id" not in columnas, (
                    f"`downgrade` dejó `{tabla}.portfolio_id`. El job del CI corre "
                    "`downgrade base` y esto lo destaparía tarde."
                )
    finally:
        motor.dispose()
