"""US-222 / EP021 — Consumo de IA del inquilino.

Del artboard «Admin — IA», fila «Consumo / alertas». Es la única de las cinco
filas de ese artboard que no depende de ninguna decisión pendiente: `AIJob` ya
guarda tokens, modelo y proveedor desde US-057, y lo que faltaba era mirarlos. Las
otras cuatro están en `EP021-catalogo-de-ia.md` con sus preguntas.

Lo que estos tests cuidan:

1. **No hay dinero.** La tarifa de cada modelo la fija su proveedor, cambia cuando
   él la cambia y no vive aquí; un importe estimado se leería como el gasto.
2. **Un mes sin trabajos aparece con ceros.** Omitirlo dejaría huecos en la serie,
   y un hueco en una gráfica se lee como continuidad.
3. **Los fallidos van junto al total.** «120 trabajos» con treinta fallidos se lee
   como éxito y no lo es.
4. **Nada cruza de inquilino.**
"""
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.ai import AIJob
from app.services.consumo_ia import (
    MESES_DE_HISTORIA,
    consumo_por_mes,
    consumo_por_modelo,
    meses_hacia_atras,
    resumen,
)
from tests.factories import create_tenant


def test_la_ventana_va_del_mes_mas_viejo_al_mas_nuevo():
    """Es el orden en que se lee una serie de tiempo; devolverla al revés obliga
    a invertirla, que es donde se olvida."""
    ventana = meses_hacia_atras(date(2026, 3, 15), 4)
    assert ventana == [(2025, 12), (2026, 1), (2026, 2), (2026, 3)]


def test_la_ventana_cruza_el_año_sin_dar_mes_cero():
    assert meses_hacia_atras(date(2026, 1, 5), 2) == [(2025, 12), (2026, 1)]


async def _trabajo(db, tenant_id, *, cuando, modelo="llama-3", tokens=(10, 5), estado="done"):
    db.add(
        AIJob(
            tenant_id=str(tenant_id),
            kind="progress_report",
            status=estado,
            input={},
            model_used=modelo,
            provider="groq",
            tokens_in=tokens[0],
            tokens_out=tokens[1],
            created_at=cuando,
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_un_mes_sin_trabajos_sale_con_ceros(client, db_session):
    """Omitirlo dejaría la serie con huecos, y un hueco se lee como si el consumo
    hubiera seguido plano. Aquí el cero es un dato: nadie usó la IA ese mes."""
    t = await create_tenant(db_session)
    hoy = date(2026, 8, 20)
    await _trabajo(db_session, t.id, cuando=datetime(2026, 8, 5, tzinfo=UTC))

    meses = await consumo_por_mes(db_session, t.id, hoy=hoy)
    assert len(meses) == MESES_DE_HISTORIA
    assert [m["month"] for m in meses][-1] == "2026-08"
    assert meses[-1]["jobs"] == 1
    # Los cinco anteriores existen y valen cero.
    assert all(m["jobs"] == 0 for m in meses[:-1])
    assert all(m["tokens_total"] == 0 for m in meses[:-1])


@pytest.mark.asyncio
async def test_los_tokens_se_suman_por_mes(client, db_session):
    t = await create_tenant(db_session)
    hoy = date(2026, 8, 20)
    await _trabajo(db_session, t.id, cuando=datetime(2026, 8, 2, tzinfo=UTC), tokens=(100, 40))
    await _trabajo(db_session, t.id, cuando=datetime(2026, 8, 9, tzinfo=UTC), tokens=(30, 10))
    await _trabajo(db_session, t.id, cuando=datetime(2026, 7, 9, tzinfo=UTC), tokens=(7, 3))

    meses = {m["month"]: m for m in await consumo_por_mes(db_session, t.id, hoy=hoy)}
    assert meses["2026-08"]["jobs"] == 2
    assert meses["2026-08"]["tokens_in"] == 130
    assert meses["2026-08"]["tokens_out"] == 50
    assert meses["2026-08"]["tokens_total"] == 180
    assert meses["2026-07"]["tokens_total"] == 10


@pytest.mark.asyncio
async def test_un_trabajo_sin_tokens_cuenta_como_trabajo(client, db_session):
    """Un trabajo que falló antes de consumir tokens ocurrió: descartarlo haría
    que el conteo de trabajos y el de tokens hablaran de conjuntos distintos."""
    t = await create_tenant(db_session)
    hoy = date(2026, 8, 20)
    db_session.add(
        AIJob(
            tenant_id=str(t.id),
            kind="minute_from_transcript",
            status="failed",
            input={},
            created_at=datetime(2026, 8, 3, tzinfo=UTC),
        )
    )
    await db_session.flush()
    meses = {m["month"]: m for m in await consumo_por_mes(db_session, t.id, hoy=hoy)}
    assert meses["2026-08"]["jobs"] == 1
    assert meses["2026-08"]["tokens_total"] == 0


@pytest.mark.asyncio
async def test_el_reparto_por_modelo_va_del_que_mas_consume_al_que_menos(
    client, db_session
):
    """Por modelo y no por proveedor: dos modelos del mismo proveedor cuestan
    distinto, y el que se cambia cuando el gasto molesta es el modelo."""
    t = await create_tenant(db_session)
    hoy = date(2026, 8, 20)
    await _trabajo(
        db_session, t.id, cuando=datetime(2026, 8, 2, tzinfo=UTC),
        modelo="grande", tokens=(1000, 500),
    )
    await _trabajo(
        db_session, t.id, cuando=datetime(2026, 8, 3, tzinfo=UTC),
        modelo="chico", tokens=(10, 5),
    )
    filas = await consumo_por_modelo(db_session, t.id, hoy=hoy)
    assert [f["model"] for f in filas] == ["grande", "chico"]
    assert filas[0]["tokens_total"] == 1500
    # El proveedor viaja al lado para no obligar a adivinarlo.
    assert filas[0]["provider"] == "groq"


@pytest.mark.asyncio
async def test_el_reparto_por_modelo_es_del_mes_en_curso(client, db_session):
    t = await create_tenant(db_session)
    hoy = date(2026, 8, 20)
    await _trabajo(db_session, t.id, cuando=datetime(2026, 7, 30, tzinfo=UTC), modelo="viejo")
    assert await consumo_por_modelo(db_session, t.id, hoy=hoy) == []


@pytest.mark.asyncio
async def test_un_modelo_nulo_se_muestra_y_no_se_descarta(client, db_session):
    """`None` cuando el trabajo falló antes de saber qué modelo lo iba a atender.
    Son trabajos que ocurrieron."""
    t = await create_tenant(db_session)
    hoy = date(2026, 8, 20)
    db_session.add(
        AIJob(
            tenant_id=str(t.id),
            kind="progress_report",
            status="failed",
            input={},
            created_at=datetime(2026, 8, 3, tzinfo=UTC),
        )
    )
    await db_session.flush()
    filas = await consumo_por_modelo(db_session, t.id, hoy=hoy)
    assert len(filas) == 1
    assert filas[0]["model"] is None


@pytest.mark.asyncio
async def test_el_resumen_pone_los_fallidos_junto_al_total(client, db_session):
    """«120 trabajos este mes» con treinta fallidos se lee como éxito y no lo es."""
    t = await create_tenant(db_session)
    hoy = date(2026, 8, 20)
    await _trabajo(db_session, t.id, cuando=datetime(2026, 8, 2, tzinfo=UTC))
    await _trabajo(
        db_session, t.id, cuando=datetime(2026, 8, 3, tzinfo=UTC), estado="failed"
    )
    d = await resumen(db_session, t.id, hoy=hoy)
    assert d["jobs_this_month"] == 2
    assert d["failed_this_month"] == 1
    assert d["current_month"] == "2026-08"


@pytest.mark.asyncio
async def test_el_resumen_no_devuelve_dinero(client, db_session):
    """La tarifa de cada modelo la fija su proveedor, cambia cuando él la cambia y
    no vive aquí. Un importe estimado se leería como el gasto y no lo sería."""
    t = await create_tenant(db_session)
    d = await resumen(db_session, t.id, hoy=date(2026, 8, 20))
    plano = str(d).lower()
    for palabra in ("cost", "costo", "amount", "importe", "currency", "moneda"):
        assert palabra not in plano, palabra
    # Y lo dice, para que nadie lo busque.
    assert "tarifa" in str(d["note"]).lower()


@pytest.mark.asyncio
async def test_el_consumo_de_otro_inquilino_no_cuenta(client, db_session):
    t = await create_tenant(db_session)
    otro = await create_tenant(db_session, slug="beta", name="Beta")
    hoy = date(2026, 8, 20)
    await _trabajo(db_session, otro.id, cuando=datetime(2026, 8, 2, tzinfo=UTC), tokens=(999, 999))
    d = await resumen(db_session, t.id, hoy=hoy)
    assert d["jobs_this_month"] == 0
    assert d["tokens_this_month"] == 0


@pytest.mark.asyncio
async def test_lo_anterior_a_la_ventana_no_entra(client, db_session):
    t = await create_tenant(db_session)
    hoy = date(2026, 8, 20)
    viejo = datetime(2026, 8, 1, tzinfo=UTC) - timedelta(days=400)
    await _trabajo(db_session, t.id, cuando=viejo, tokens=(500, 500))
    meses = await consumo_por_mes(db_session, t.id, hoy=hoy)
    assert sum(int(m["tokens_total"]) for m in meses) == 0
