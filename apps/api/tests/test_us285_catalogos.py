"""US-285 — la infraestructura de catálogos por inquilino.

La tabla, la siembra y el servicio. La API es US-286 y la pantalla US-287; aquí
solo se prueba lo que está debajo de las dos.
"""
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dominio.proyecto import (
    ETIQUETAS_FASE,
    ETIQUETAS_TIPO,
    FASES,
    FASES_TERMINALES,
    TIPOS,
)
from app.models.tenant_catalog import (
    CATALOGO_FASE_PROYECTO,
    CATALOGO_TIPO_PROYECTO,
    TenantCatalogValue,
)
from app.services import catalogos
from tests.factories import create_tenant


@pytest.mark.asyncio
async def test_us285_la_siembra_deja_el_catalogo_canonico(db_session):
    """TC-001: los valores que hoy están en el enum, con su etiqueta y su orden.

    `create_tenant` ya siembra —desde US-286 un inquilino sin catálogos no puede
    dar de alta un proyecto, así que un inquilino de prueba sin ellos sería un
    estado que en producción no existe—. Lo que se comprueba aquí es el
    contenido; el conteo vive en la prueba de idempotencia.
    """
    tenant = await create_tenant(db_session)
    await db_session.commit()

    tipos = await catalogos.listar(db_session, tenant.id, CATALOGO_TIPO_PROYECTO)
    assert [v.clave for v in tipos] == list(TIPOS)
    assert [v.etiqueta for v in tipos] == [ETIQUETAS_TIPO[t] for t in TIPOS]

    fases = await catalogos.listar(db_session, tenant.id, CATALOGO_FASE_PROYECTO)
    assert [v.clave for v in fases] == list(FASES)
    assert [v.etiqueta for v in fases] == [ETIQUETAS_FASE[f] for f in FASES]


@pytest.mark.asyncio
async def test_us285_las_fases_nacen_con_sus_banderas(db_session):
    """`terminal` y `activa` se siembran desde ya, aunque las estrene US-287.

    Sembrarlas después obligaría a alguien a rellenarlas a mano, y una fase sin
    banderas no se puede interpretar: no se sabría si cuenta como activa en los
    KPIs.
    """
    tenant = await create_tenant(db_session)
    await db_session.commit()

    fases = await catalogos.listar(db_session, tenant.id, CATALOGO_FASE_PROYECTO)
    por_clave = {v.clave: v.datos for v in fases}
    for fase in FASES:
        terminal = fase in FASES_TERMINALES
        assert por_clave[fase]["terminal"] is terminal
        assert por_clave[fase]["activa"] is (not terminal)


@pytest.mark.asyncio
async def test_us285_sembrar_dos_veces_no_duplica(db_session):
    """Idempotente: se llama al aprovisionar, tras un vaciado y desde la migración."""
    tenant = await create_tenant(db_session)
    await db_session.commit()

    # `create_tenant` ya sembró, así que la primera llamada explícita ya no
    # crea nada: es justo la propiedad que importa.
    assert await catalogos.sembrar(db_session, tenant.id) == 0
    await db_session.commit()
    tipos = await catalogos.listar(db_session, tenant.id, CATALOGO_TIPO_PROYECTO)
    assert len(tipos) == len(TIPOS)


@pytest.mark.asyncio
async def test_us285_la_clave_es_unica_por_inquilino_y_catalogo(db_session):
    """TC-002: lo impide la base, no solo el servicio."""
    tenant = await create_tenant(db_session)
    for _ in range(2):
        db_session.add(
            TenantCatalogValue(
                tenant_id=str(tenant.id),
                catalogo=CATALOGO_TIPO_PROYECTO,
                clave="mantenimiento",
                etiqueta="Mantenimiento",
            )
        )
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_us285_dos_inquilinos_pueden_usar_la_misma_clave(db_session):
    """La unicidad es por inquilino: no hay un espacio de nombres global."""
    a = await create_tenant(db_session, slug="acme", name="Acme")
    b = await create_tenant(db_session, slug="globex", name="Globex")
    for tenant in (a, b):
        db_session.add(
            TenantCatalogValue(
                tenant_id=str(tenant.id),
                catalogo=CATALOGO_TIPO_PROYECTO,
                clave="mantenimiento",
                etiqueta="Mantenimiento",
            )
        )
    await db_session.commit()
    filas = (
        await db_session.execute(
            select(TenantCatalogValue).where(
                TenantCatalogValue.clave == "mantenimiento"
            )
        )
    ).scalars().all()
    assert len(filas) == 2


@pytest.mark.asyncio
async def test_us285_reordenar_reescribe_el_orden_completo(db_session):
    """TC-003."""
    tenant = await create_tenant(db_session)
    await db_session.commit()

    al_reves = list(reversed(TIPOS))
    await catalogos.reordenar(
        db_session, tenant.id, CATALOGO_TIPO_PROYECTO, list(al_reves)
    )
    await db_session.commit()

    tipos = await catalogos.listar(db_session, tenant.id, CATALOGO_TIPO_PROYECTO)
    assert [v.clave for v in tipos] == list(al_reves)


@pytest.mark.asyncio
async def test_us285_reordenar_con_la_lista_incompleta_falla_y_dice_que_falta(
    db_session,
):
    """Con valores de menos el orden sería ambiguo, así que no se adivina."""
    from app.core.errors import AppError

    tenant = await create_tenant(db_session)
    await db_session.commit()

    with pytest.raises(AppError) as fallo:
        await catalogos.reordenar(
            db_session, tenant.id, CATALOGO_TIPO_PROYECTO, [TIPOS[0]]
        )
    assert "Faltan" in fallo.value.detail["detail"]


@pytest.mark.asyncio
async def test_us285_crear_deriva_la_clave_de_la_etiqueta(db_session):
    """«Operación continua» → `operacion_continua`, sin acentos ni espacios."""
    tenant = await create_tenant(db_session)
    valor = await catalogos.crear(
        db_session, tenant.id, CATALOGO_TIPO_PROYECTO, etiqueta="Operación continua"
    )
    await db_session.commit()
    assert valor.clave == "operacion_continua"
    assert valor.etiqueta == "Operación continua"


@pytest.mark.asyncio
async def test_us285_crear_pone_el_valor_nuevo_al_final(db_session):
    """Agregar un tipo no es decir que sea el más importante."""
    tenant = await create_tenant(db_session)
    await catalogos.sembrar(db_session, tenant.id)
    await catalogos.crear(
        db_session, tenant.id, CATALOGO_TIPO_PROYECTO, etiqueta="Mantenimiento"
    )
    await db_session.commit()

    tipos = await catalogos.listar(db_session, tenant.id, CATALOGO_TIPO_PROYECTO)
    assert tipos[-1].clave == "mantenimiento"


@pytest.mark.asyncio
async def test_us285_crear_rechaza_la_clave_repetida(db_session):
    from app.core.errors import AppError

    tenant = await create_tenant(db_session)
    await db_session.commit()

    with pytest.raises(AppError):
        await catalogos.crear(
            db_session, tenant.id, CATALOGO_TIPO_PROYECTO, etiqueta="Transformación"
        )


@pytest.mark.asyncio
async def test_us285_un_catalogo_que_no_existe_no_se_crea_al_vuelo(db_session):
    """Un error de dedo crearía un catálogo fantasma que nadie lista."""
    from app.core.errors import AppError

    tenant = await create_tenant(db_session)
    with pytest.raises(AppError):
        await catalogos.crear(
            db_session, tenant.id, "color_favorito", etiqueta="Azul"
        )


@pytest.mark.asyncio
async def test_us285_desactivar_lo_saca_del_listado_pero_no_de_las_etiquetas(
    db_session,
):
    """Un proyecto con un tipo retirado tiene que seguir mostrando su nombre."""
    tenant = await create_tenant(db_session)
    await db_session.commit()

    tipos = await catalogos.listar(db_session, tenant.id, CATALOGO_TIPO_PROYECTO)
    await catalogos.editar(db_session, tipos[0], activo=False)
    await db_session.commit()

    visibles = await catalogos.listar(db_session, tenant.id, CATALOGO_TIPO_PROYECTO)
    assert tipos[0].clave not in [v.clave for v in visibles]
    assert tipos[0].clave in await catalogos.etiquetas(
        db_session, tenant.id, CATALOGO_TIPO_PROYECTO
    )


@pytest.mark.asyncio
async def test_us285_editar_cambia_la_etiqueta_y_nunca_la_clave(db_session):
    """Renombrar la clave dejaría huérfano a cada `projects.type` que la tenga."""
    tenant = await create_tenant(db_session)
    await db_session.commit()

    tipos = await catalogos.listar(db_session, tenant.id, CATALOGO_TIPO_PROYECTO)
    clave_original = tipos[0].clave
    await catalogos.editar(db_session, tipos[0], etiqueta="Transformación digital")
    await db_session.commit()

    assert tipos[0].etiqueta == "Transformación digital"
    assert tipos[0].clave == clave_original


def test_us285_la_migracion_siembra_lo_mismo_que_el_dominio():
    """Trinquete de la copia deliberada.

    La migración repite los valores en vez de importarlos, para que una fase
    nueva no cambie retroactivamente lo que hizo. Eso está bien mientras las dos
    listas **deban** ser iguales; el día que dejen de serlo, esta prueba obliga
    a decidirlo por escrito en vez de descubrirlo en una base recién creada.
    """
    ruta = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260919_0117_catalogos_por_inquilino.py"
    )
    spec = importlib.util.spec_from_file_location("mig0117", ruta)
    assert spec is not None and spec.loader is not None
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    assert [c for c, _ in mig.TIPOS] == list(TIPOS)
    assert [e for _, e in mig.TIPOS] == [ETIQUETAS_TIPO[t] for t in TIPOS]
    assert [c for c, _, _ in mig.FASES] == list(FASES)
    assert [e for _, e, _ in mig.FASES] == [ETIQUETAS_FASE[f] for f in FASES]
    assert [t for _, _, t in mig.FASES] == [f in FASES_TERMINALES for f in FASES]
