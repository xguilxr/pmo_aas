"""US-222 / EP021 — Cuánta IA consume un inquilino.

Del artboard «Admin — IA», fila «Consumo / alertas». Es la única de las cinco
filas de ese artboard que no depende de ninguna decisión pendiente: `AIJob` ya
guarda los tokens, el modelo y el proveedor de cada trabajo desde US-057, y lo que
faltaba era mirarlos.

## Por qué no hay costo en pesos

Convertir tokens a dinero exige la tarifa de cada modelo de cada proveedor, con
fecha. Esa tabla no está en ningún sitio de este repositorio, cambia cuando el
proveedor la cambia, y **no la controlamos**: un número estimado con una tarifa de
hace seis meses se leería como el gasto y no lo sería. Se cuentan tokens, que es
el dato que sí es nuestro, y quien tenga la tarifa hace la multiplicación con
información fresca.

Es el mismo criterio que `dominio/moneda.py` con la conversión entre monedas: no
se convierte sin un tipo de cambio con fecha, porque el resultado deja de ser un
dato y pasa a ser una estimación.

## Por qué por mes calendario

Igual que el consumo del plan (US-221) y por lo mismo: es lo que espera quien lee
una factura. Una ventana móvil de treinta días da un número que baja sin que nadie
haya hecho nada.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIJob

#: Cuántos meses de historia se devuelven. Seis porque es lo que hace falta para
#: ver una tendencia sin que la respuesta crezca sin techo.
MESES_DE_HISTORIA = 6


def _primer_dia(anio: int, mes: int) -> datetime:
    return datetime(anio, mes, 1, tzinfo=UTC)


def _mes_anterior(anio: int, mes: int) -> tuple[int, int]:
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def meses_hacia_atras(hoy: date, cuantos: int) -> list[tuple[int, int]]:
    """`(año, mes)` del mes en curso y los anteriores, del más viejo al más nuevo.

    Del más viejo al más nuevo porque es el orden en que se lee una serie de
    tiempo, y devolverlo al revés obliga a quien la pinta a invertirla — que es
    donde se olvida.
    """
    salida = [(hoy.year, hoy.month)]
    for _ in range(cuantos - 1):
        salida.append(_mes_anterior(*salida[-1]))
    return list(reversed(salida))


async def consumo_por_mes(
    db: AsyncSession, tenant_id: UUID, *, hoy: date | None = None
) -> list[dict[str, object]]:
    """Trabajos y tokens por mes, del más viejo al más nuevo.

    Un mes **sin trabajos aparece con ceros** y no se omite. Omitirlo dejaría la
    serie con huecos, y una gráfica de huecos se lee como si el consumo hubiera
    seguido plano cuando en realidad fue cero — o al revés. Aquí el cero es un
    dato: nadie usó la IA ese mes.
    """
    hoy = hoy or datetime.now(UTC).date()
    ventana = meses_hacia_atras(hoy, MESES_DE_HISTORIA)
    desde = _primer_dia(*ventana[0])

    # Se agrupa en Python y no con `strftime`/`to_char`, que son funciones de
    # dialecto: la suite corre sobre SQLite y producción sobre Postgres, así que
    # una rama por motor deja la mitad del código probada en un solo sitio — y es
    # la mitad de producción la que no se prueba. El precio es traer tres columnas
    # de los trabajos de seis meses de **un** inquilino, que es acotado.
    filas = (
        await db.execute(
            select(AIJob.created_at, AIJob.tokens_in, AIJob.tokens_out).where(
                AIJob.tenant_id == str(tenant_id),
                AIJob.created_at >= desde,
            )
        )
    ).all()
    por_clave: dict[str, tuple[int, int, int]] = {}
    for creado, entrada, sal in filas:
        if creado is None:
            continue
        clave = f"{creado.year:04d}-{creado.month:02d}"
        n_previo, e_previo, s_previo = por_clave.get(clave, (0, 0, 0))
        por_clave[clave] = (
            n_previo + 1,
            e_previo + int(entrada or 0),
            s_previo + int(sal or 0),
        )

    salida: list[dict[str, object]] = []
    for anio, mes in ventana:
        clave = f"{anio:04d}-{mes:02d}"
        trabajos, entrada, sal = por_clave.get(clave, (0, 0, 0))
        salida.append(
            {
                "month": clave,
                "jobs": trabajos,
                "tokens_in": entrada,
                "tokens_out": sal,
                "tokens_total": entrada + sal,
            }
        )
    return salida


async def consumo_por_modelo(
    db: AsyncSession, tenant_id: UUID, *, hoy: date | None = None
) -> list[dict[str, object]]:
    """Tokens del **mes en curso** repartidos por modelo, del que más consume al que menos.

    Por modelo y no por proveedor: dos modelos del mismo proveedor cuestan
    distinto, y el que se cambia cuando el gasto molesta es el modelo. El
    proveedor viaja al lado para no obligar a adivinarlo.
    """
    hoy = hoy or datetime.now(UTC).date()
    desde = _primer_dia(hoy.year, hoy.month)
    filas = (
        await db.execute(
            select(
                AIJob.model_used,
                AIJob.provider,
                func.count(),
                func.coalesce(func.sum(AIJob.tokens_in), 0)
                + func.coalesce(func.sum(AIJob.tokens_out), 0),
            )
            .where(AIJob.tenant_id == str(tenant_id), AIJob.created_at >= desde)
            .group_by(AIJob.model_used, AIJob.provider)
        )
    ).all()
    # Se ordena sobre las tuplas de la consulta y no sobre los diccionarios
    # armados: ahí `tokens` ya es un entero, y ordenar después obligaría a
    # convertir un `object` en cada comparación.
    ordenadas = sorted(filas, key=lambda f: int(f[3] or 0), reverse=True)
    return [
        {
            # `None` cuando el trabajo falló antes de saber qué modelo lo iba a
            # atender. Se muestra como «sin modelo» y no se descarta: son
            # trabajos que ocurrieron.
            "model": modelo,
            "provider": proveedor,
            "jobs": int(n),
            "tokens_total": int(tokens or 0),
        }
        for modelo, proveedor, n, tokens in ordenadas
    ]


async def resumen(
    db: AsyncSession, tenant_id: UUID, *, hoy: date | None = None
) -> dict[str, object]:
    """El consumo de IA, listo para la pantalla de administración.

    **Sin costo en dinero, a propósito.** Ver el encabezado del módulo: la tarifa
    de cada modelo no está aquí, cambia cuando el proveedor la cambia y no la
    controlamos. Se cuentan tokens y trabajos, que son datos nuestros.
    """
    hoy = hoy or datetime.now(UTC).date()
    meses = await consumo_por_mes(db, tenant_id, hoy=hoy)
    actual = meses[-1] if meses else {"jobs": 0, "tokens_total": 0}
    fallidos = int(
        (
            await db.execute(
                select(func.count())
                .select_from(AIJob)
                .where(
                    AIJob.tenant_id == str(tenant_id),
                    AIJob.created_at >= _primer_dia(hoy.year, hoy.month),
                    AIJob.status == "failed",
                )
            )
        ).scalar()
        or 0
    )
    return {
        "current_month": actual["month"] if meses else None,
        "jobs_this_month": actual["jobs"],
        "tokens_this_month": actual["tokens_total"],
        # Los fallidos van con el total y no aparte: «120 trabajos este mes» con
        # treinta fallidos es una cifra que se lee como éxito y no lo es. Es la
        # misma pareja que el costo con `without_rate` (US-215) y el total de
        # importación con `skipped_invalid` (US-216).
        "failed_this_month": fallidos,
        "by_month": meses,
        "by_model": await consumo_por_modelo(db, tenant_id, hoy=hoy),
        "note": (
            "Se cuentan tokens y trabajos, no dinero: la tarifa de cada modelo la "
            "fija su proveedor y no vive en la plataforma. Con los tokens y la "
            "tarifa vigente, el cálculo se hace con información fresca."
        ),
    }
