"""DEC-032 — el label configurable de organización queda retirado.

Reemplaza a `test_enh190_org_label.py`, que probaba lo contrario: que un
inquilino podía renombrar «Organización» a «Portafolio» en la interfaz. ADR-037
volvió eso inválido —Portafolio es ahora una entidad **dentro** de la
organización— y el label dejaba dos niveles seguidos llamados igual.

Este archivo es el trinquete del retiro. No prueba que algo funcione: prueba que
algo **siga sin volver**, que es el único test que un retiro puede tener. Sin él,
un `settings["org_label"] = ...` reintroducido en cualquier handler pasa
inadvertido: no rompe nada, solo vuelve a exponer un ajuste que ya no debería
poder elegirse.
"""
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine

from alembic.migration import MigrationContext
from alembic.operations import Operations
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="acme"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


@pytest.mark.asyncio
async def test_los_ajustes_ya_no_exponen_el_label(client, db_session):
    """Ni el ajuste de administración ni el branding compartido lo devuelven."""
    _, auth = await _admin(client, db_session)

    r = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert r.status_code == 200
    assert "org_label" not in r.json()["settings"]

    b = await client.get("/api/v1/me/tenant-branding", headers=auth["_authz"])
    assert b.status_code == 200
    assert "org_label" not in b.json()
    # Lo que sí sigue viajando por el mismo endpoint, y por el mismo motivo
    # (dato de presentación que toda pantalla necesita): la moneda preferida.
    assert "preferred_currency" in b.json()


@pytest.mark.asyncio
async def test_mandarlo_falla_con_una_razon_en_vez_de_ignorarse(client, db_session):
    """Lo que un cliente con el bundle viejo va a hacer.

    El defecto de Pydantic con un campo que no conoce es **ignorarlo**: sin el
    rechazo explícito, esta petición devolvería 200 y la etiqueta no se
    aplicaría. Un ajuste que se elige y no pasa nada es peor que un error,
    porque no hay nada que investigar.
    """
    _, auth = await _admin(client, db_session, slug="clientco")

    r = await client.patch(
        "/api/v1/admin/settings",
        json={"org_label": "portfolios"},
        headers=auth["_authz"],
    )
    # 422 y no 400: `business_rule` de la casa es una regla de negocio con
    # mensaje accionable, y ese es su código.
    assert r.status_code == 422, r.text
    texto = str(r.json()["detail"])
    # El mensaje dice qué pasó, por qué y qué hacer (contrato de `mensaje()`).
    assert "ADR-037" in texto
    assert "org_label" in texto

    # Y no se escribió nada por el camino.
    g = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert "org_label" not in g.json()["settings"]


@pytest.mark.asyncio
async def test_el_rechazo_no_arrastra_los_ajustes_que_si_existen(client, db_session):
    """Un cliente viejo manda `org_label` **junto** con ajustes válidos. La
    petición entera falla y no se guarda nada: media escritura aplicada es peor
    que ninguna, porque nadie sabe qué mitad quedó."""
    _, auth = await _admin(client, db_session, slug="mixedco")

    r = await client.patch(
        "/api/v1/admin/settings",
        json={"org_label": "portfolios", "locale": "en-US"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text

    g = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert g.json()["settings"].get("locale") != "en-US"


@pytest.mark.asyncio
async def test_el_servicio_ya_no_ofrece_los_accesores(client, db_session):
    """El trinquete de verdad: los símbolos no existen.

    Un handler nuevo que quiera exponer el label tendría que reescribirlos, y eso
    es visible en revisión. Mientras esta comprobación pase, el retiro se
    sostiene solo.
    """
    from app.services import tenant_settings

    for simbolo in (
        "ORG_LABEL_VALUES",
        "DEFAULT_ORG_LABEL",
        "get_org_label",
        "set_org_label",
    ):
        assert not hasattr(tenant_settings, simbolo), (
            f"`tenant_settings.{simbolo}` volvió: DEC-032 retiró el label "
            "configurable de organización."
        )


# ---------------------------------------------------------------------------
# La migración 0111
# ---------------------------------------------------------------------------

MIGRACION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260819_0111_retiro_org_label.py"
)


def _cargar_migracion() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migracion_0111", MIGRACION)
    assert spec and spec.loader, f"No pude cargar {MIGRACION}"
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _tabla_tenants(md: sa.MetaData) -> sa.Table:
    """La forma mínima de `tenants` que la migración toca.

    Se declara aquí y no se copia del modelo a propósito: la migración lee
    `id` y `settings` con SQL crudo, así que lo que hay que ejercer es
    exactamente eso. Si el modelo ganara columnas, la migración seguiría
    corriendo igual.
    """
    return sa.Table(
        "tenants",
        md,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("settings", sa.JSON, nullable=False),
    )


def test_la_migracion_borra_la_clave_y_no_toca_el_resto(tmp_path: Path) -> None:
    """El caso que importa: la clave se va y **lo demás sobrevive**.

    Es el error fácil de esta migración — reescribir `settings` con un dict
    nuevo en vez de con el mismo menos una clave— y no falla: el inquilino
    pierde su idioma, su moneda y su color de marca en silencio.
    """
    modulo = _cargar_migracion()
    md = sa.MetaData()
    tenants = _tabla_tenants(md)

    motor = create_engine(f"sqlite:///{tmp_path / 'dec032.db'}")
    ids = {clave: str(uuid4()) for clave in ("con", "default", "sin", "vacio")}
    try:
        with motor.begin() as cx:
            md.create_all(cx)
            cx.execute(
                tenants.insert(),
                [
                    # El que motivó el retiro, con ajustes que deben sobrevivir.
                    {
                        "id": ids["con"],
                        "slug": "clientco",
                        "name": "ClientCo",
                        "settings": {
                            "org_label": "portfolios",
                            "locale": "es-MX",
                            "currency": "MXN",
                            "primary_color": "#123456",
                        },
                    },
                    # Uno que la tenía puesta en el default explícito.
                    {
                        "id": ids["default"],
                        "slug": "acme",
                        "name": "Acme",
                        "settings": {"org_label": "organizations", "locale": "en-US"},
                    },
                    # Uno que nunca la tocó.
                    {
                        "id": ids["sin"],
                        "slug": "otra",
                        "name": "Otra",
                        "settings": {"locale": "es-MX"},
                    },
                    # Y el borde: ajustes vacíos.
                    {"id": ids["vacio"], "slug": "nueva", "name": "Nueva", "settings": {}},
                ],
            )

        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.upgrade()

        with motor.connect() as cx:
            filas = {
                str(i): modulo._ajustes(s) or {}
                for i, s in cx.execute(sa.text("SELECT id, settings FROM tenants")).all()
            }

        for clave, ajustes in filas.items():
            assert "org_label" not in ajustes, f"quedó la clave en {clave}"

        # Lo que NO se tocó.
        con = filas[ids["con"]]
        assert con == {
            "locale": "es-MX",
            "currency": "MXN",
            "primary_color": "#123456",
        }, "la migración se llevó ajustes que no eran suyos"
        assert filas[ids["default"]] == {"locale": "en-US"}
        assert filas[ids["sin"]] == {"locale": "es-MX"}
        assert filas[ids["vacio"]] == {}

        # Idempotente: correrla otra vez no cambia nada ni falla.
        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.upgrade()

        # Y la bajada no repone el valor, a propósito (ver el encabezado de la
        # migración): la clave ausente ES el default que leía el accesor viejo.
        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.downgrade()

        with motor.connect() as cx:
            despues = {
                str(i): modulo._ajustes(s) or {}
                for i, s in cx.execute(sa.text("SELECT id, settings FROM tenants")).all()
            }
        assert despues == filas
    finally:
        motor.dispose()


def test_la_migracion_cuenta_quien_la_tenia(tmp_path: Path) -> None:
    """El conteo es la razón de ser de esta migración: contesta «¿alguien la
    estaba usando?». Sin él el retiro se despliega a ciegas y nadie sabe a qué
    cliente hay que avisarle del cambio de nombre."""
    modulo = _cargar_migracion()
    md = sa.MetaData()
    tenants = _tabla_tenants(md)

    motor = create_engine(f"sqlite:///{tmp_path / 'dec032_conteo.db'}")
    try:
        with motor.begin() as cx:
            md.create_all(cx)
            cx.execute(
                tenants.insert(),
                [
                    {
                        "id": str(uuid4()),
                        "slug": f"t{i}",
                        "name": f"T{i}",
                        "settings": {"org_label": valor},
                    }
                    for i, valor in enumerate(
                        ["portfolios", "portfolios", "organizations"]
                    )
                ],
            )

        with motor.begin() as cx:
            conteo = modulo._soltar_clave(cx)

        assert conteo == {"portfolios": 2, "organizations": 1}
    finally:
        motor.dispose()


def test_los_ajustes_llegan_como_texto_o_como_dict(tmp_path: Path) -> None:
    """`tenants.settings` es `JSON`, y según el driver llega deserializado o como
    cadena. La migración acepta las dos formas; si solo aceptara `dict`, en el
    driver equivocado no borraría nada y **pasaría en verde**."""
    modulo = _cargar_migracion()

    assert modulo._ajustes({"org_label": "portfolios"}) == {"org_label": "portfolios"}
    assert modulo._ajustes(json.dumps({"org_label": "portfolios"})) == {
        "org_label": "portfolios"
    }
    assert modulo._ajustes(None) is None
    assert modulo._ajustes("no es json") is None
    # Un JSON válido que no es un objeto tampoco: no hay clave que sacar.
    assert modulo._ajustes("[1, 2]") is None
