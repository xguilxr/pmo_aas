"""US-285 — los catálogos de proyecto que cada inquilino define por su cuenta.

Dos por ahora: `tipo_proyecto` y `fase_proyecto`. El modelo y el porqué de la
tabla están en `app/models/tenant_catalog.py`; aquí vive lo que se puede hacer
con ella.

## La siembra usa las claves canónicas de `dominio/proyecto.py`

No se inventan valores nuevos: se copian los que hoy están en el enum, con su
etiqueta y su orden. Así ningún `projects.type` ni `projects.phase` existente
queda apuntando a una clave que no está en el catálogo, y no hace falta migrar
una sola fila de datos.

Los valores sembrados **no** quedan marcados como intocables (D9, owner
2026-09-19): el inquilino los renombra, los reordena y los borra como
cualquier otro. Lo que la plataforma protege es lo que está en uso, no lo que
vino de fábrica.

## Qué no hace

No valida el contenido de `datos` por catálogo —eso es de US-287, cuando las
fases estrenen sus banderas— ni toca `projects`. Desactivar un valor en uso se
permite a propósito: lo que se prohíbe es **borrarlo**, porque dejaría
proyectos apuntando a nada. Un tipo desactivado desaparece del desplegable y
los proyectos que ya lo tienen lo siguen mostrando, que es la verdad.
"""
from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import business_rule, conflict, mensaje, not_found
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
    CATALOGOS,
    TenantCatalogValue,
)


def _clave_desde(etiqueta: str) -> str:
    """«Operación continua» → `operacion_continua`.

    La clave es lo que se guarda en `projects.type`, así que tiene que ser
    estable y sin acentos: un valor con tilde acaba escrito de dos formas y
    parte en dos cualquier `GROUP BY`.
    """
    sin_acentos = "".join(
        c
        for c in unicodedata.normalize("NFD", etiqueta.strip().lower())
        if not unicodedata.combining(c)
    )
    clave = re.sub(r"[^a-z0-9]+", "_", sin_acentos).strip("_")
    return clave[:64]


def siembra_de(catalogo: str) -> list[dict[str, object]]:
    """Los valores con los que nace un inquilino, en orden.

    Se derivan del enum, no se copian a mano: una fase nueva en
    `dominio/proyecto.py` aparece aquí sola, y no hay una segunda lista que se
    desincronice.
    """
    if catalogo == CATALOGO_TIPO_PROYECTO:
        return [
            {
                "clave": tipo,
                "etiqueta": ETIQUETAS_TIPO.get(tipo, tipo),
                "orden": i,
                "datos": {},
            }
            for i, tipo in enumerate(TIPOS)
        ]
    if catalogo == CATALOGO_FASE_PROYECTO:
        return [
            {
                "clave": fase,
                "etiqueta": ETIQUETAS_FASE.get(fase, fase),
                "orden": i,
                # US-287 las estrena; se siembran desde ya para que el catálogo
                # nazca completo y nadie tenga que rellenarlas después a mano.
                "datos": {
                    "terminal": fase in FASES_TERMINALES,
                    "activa": fase not in FASES_TERMINALES,
                },
            }
            for i, fase in enumerate(FASES)
        ]
    raise ValueError(f"Catálogo desconocido: {catalogo}")


def _validar_catalogo(catalogo: str) -> None:
    if catalogo not in CATALOGOS:
        raise not_found(f"Catálogo «{catalogo}»")


async def sembrar(db: AsyncSession, tenant_id: UUID | str) -> int:
    """Deja al inquilino con los valores de fábrica. Devuelve cuántos creó.

    Idempotente: solo agrega las claves que falten. Por eso se puede llamar al
    aprovisionar, después de un vaciado, o desde una migración sobre
    inquilinos que ya existen, sin comprobar antes cuál de los tres caso es.
    """
    tid = str(tenant_id)
    creados = 0
    for catalogo in CATALOGOS:
        existentes = set(
            (
                await db.execute(
                    select(TenantCatalogValue.clave).where(
                        TenantCatalogValue.tenant_id == tid,
                        TenantCatalogValue.catalogo == catalogo,
                    )
                )
            ).scalars().all()
        )
        for valor in siembra_de(catalogo):
            if valor["clave"] in existentes:
                continue
            db.add(
                TenantCatalogValue(
                    tenant_id=tid,
                    catalogo=catalogo,
                    clave=valor["clave"],
                    etiqueta=valor["etiqueta"],
                    orden=valor["orden"],
                    datos=valor["datos"],
                )
            )
            creados += 1
    await db.flush()
    return creados


async def listar(
    db: AsyncSession,
    tenant_id: UUID | str,
    catalogo: str,
    *,
    incluir_inactivos: bool = False,
) -> list[TenantCatalogValue]:
    """Los valores del catálogo, en su orden. Los borrados nunca salen."""
    _validar_catalogo(catalogo)
    stmt = select(TenantCatalogValue).where(
        TenantCatalogValue.tenant_id == str(tenant_id),
        TenantCatalogValue.catalogo == catalogo,
        TenantCatalogValue.deleted_at.is_(None),
    )
    if not incluir_inactivos:
        stmt = stmt.where(TenantCatalogValue.activo.is_(True))
    return list(
        (
            await db.execute(
                stmt.order_by(TenantCatalogValue.orden, TenantCatalogValue.etiqueta)
            )
        ).scalars().all()
    )


async def obtener(
    db: AsyncSession, tenant_id: UUID | str, valor_id: UUID | str
) -> TenantCatalogValue:
    valor = (
        await db.execute(
            select(TenantCatalogValue).where(
                TenantCatalogValue.id == str(valor_id),
                TenantCatalogValue.tenant_id == str(tenant_id),
                TenantCatalogValue.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if valor is None:
        raise not_found("Valor de catálogo")
    return valor


async def crear(
    db: AsyncSession,
    tenant_id: UUID | str,
    catalogo: str,
    *,
    etiqueta: str,
    clave: str | None = None,
    datos: dict[str, object] | None = None,
) -> TenantCatalogValue:
    """Un valor nuevo, al final del orden.

    La clave se deriva de la etiqueta salvo que se pase. Al final y no al
    principio: quien agrega un tipo no está diciendo que sea el más
    importante, y reordenar es una acción aparte.
    """
    _validar_catalogo(catalogo)
    etiqueta = etiqueta.strip()
    if not etiqueta:
        raise business_rule(
            mensaje(
                que="El valor necesita una etiqueta",
                porque="Es lo que se lee en el desplegable; sin ella la fila es invisible.",
                accion="Escribe el nombre con el que quieres verlo.",
            )
        )
    clave_final = (clave or _clave_desde(etiqueta)).strip()
    if not clave_final:
        raise business_rule(
            mensaje(
                que="De esa etiqueta no sale una clave utilizable",
                porque=(
                    "La clave es lo que se guarda en el proyecto y solo admite "
                    "letras, números y guion bajo."
                ),
                accion="Usa una etiqueta con al menos una letra o número.",
            )
        )
    choque = (
        await db.execute(
            select(TenantCatalogValue).where(
                TenantCatalogValue.tenant_id == str(tenant_id),
                TenantCatalogValue.catalogo == catalogo,
                TenantCatalogValue.clave == clave_final,
            )
        )
    ).scalar_one_or_none()
    if choque is not None:
        raise conflict(
            mensaje(
                que=f"Ya existe un valor con la clave «{clave_final}»",
                porque="Dos valores con la misma clave serían indistinguibles al clasificar.",
                accion=(
                    "Elige otro nombre, o reactiva el que ya existe si estaba "
                    "desactivado."
                ),
            )
        )
    ultimo = (
        await db.execute(
            select(func.max(TenantCatalogValue.orden)).where(
                TenantCatalogValue.tenant_id == str(tenant_id),
                TenantCatalogValue.catalogo == catalogo,
            )
        )
    ).scalar()
    valor = TenantCatalogValue(
        tenant_id=str(tenant_id),
        catalogo=catalogo,
        clave=clave_final,
        etiqueta=etiqueta,
        orden=(ultimo or 0) + 1,
        datos=datos or {},
    )
    db.add(valor)
    await db.flush()
    return valor


async def editar(
    db: AsyncSession,
    valor: TenantCatalogValue,
    *,
    etiqueta: str | None = None,
    activo: bool | None = None,
    datos: dict[str, object] | None = None,
) -> TenantCatalogValue:
    """Cambia lo que se puede cambiar. La clave **no** está en la lista.

    Renombrar una clave dejaría huérfano a todo lo que la referencia —cada
    `projects.type` que la tenga guardada— y no hay forma de saberlo desde
    aquí. Lo que la gente quiere cambiar es el nombre que ve, y ese es
    `etiqueta`.
    """
    if etiqueta is not None:
        limpia = etiqueta.strip()
        if not limpia:
            raise business_rule(
                mensaje(
                    que="El valor necesita una etiqueta",
                    porque="Es lo que se lee en el desplegable.",
                    accion="Escribe el nombre con el que quieres verlo.",
                )
            )
        valor.etiqueta = limpia
    if activo is not None:
        valor.activo = activo
    if datos is not None:
        valor.datos = datos
    await db.flush()
    return valor


async def reordenar(
    db: AsyncSession,
    tenant_id: UUID | str,
    catalogo: str,
    claves_en_orden: list[str],
) -> list[TenantCatalogValue]:
    """Reescribe el orden completo del catálogo.

    Se pide la lista entera y no un «mover arriba»: con movimientos sueltos, dos
    pestañas abiertas dejan un orden que ninguna de las dos pidió. La lista
    tiene que nombrar a todos los valores vivos —si falta uno, el orden
    resultante sería ambiguo y no se adivina.
    """
    _validar_catalogo(catalogo)
    valores = await listar(db, tenant_id, catalogo, incluir_inactivos=True)
    por_clave = {v.clave: v for v in valores}
    faltan = set(por_clave) - set(claves_en_orden)
    sobran = set(claves_en_orden) - set(por_clave)
    if faltan or sobran:
        raise business_rule(
            mensaje(
                que="La lista de orden no coincide con el catálogo",
                porque=(
                    "Reordenar reescribe el orden completo; con valores de más "
                    "o de menos, el resultado sería ambiguo."
                ),
                accion=(
                    "Manda todas las claves del catálogo, una sola vez cada una."
                    + (f" Faltan: {sorted(faltan)}." if faltan else "")
                    + (f" No existen: {sorted(sobran)}." if sobran else "")
                ),
            )
        )
    for posicion, clave in enumerate(claves_en_orden):
        por_clave[clave].orden = posicion
    await db.flush()
    return await listar(db, tenant_id, catalogo, incluir_inactivos=True)


async def etiquetas(
    db: AsyncSession, tenant_id: UUID | str, catalogo: str
) -> dict[str, str]:
    """`clave → etiqueta`, incluidos los inactivos.

    Los inactivos también: un proyecto que quedó con un tipo retirado tiene que
    seguir mostrando su nombre. Esconderlo no lo cambia, solo lo hace ilegible.
    """
    return {
        v.clave: v.etiqueta
        for v in await listar(db, tenant_id, catalogo, incluir_inactivos=True)
    }


async def validar(
    db: AsyncSession, tenant_id: UUID | str, catalogo: str, clave: str | None
) -> None:
    """Lanza si `clave` no es un valor **activo** del catálogo del inquilino.

    US-286. Un nulo pasa: no todos los proyectos declaran su tipo, y exigirlo
    aquí sería cambiar una regla de negocio de contrabando.

    Se comprueba contra el catálogo y no contra el enum del dominio porque el
    enum es solo la siembra: lo que vale hoy para este inquilino es lo que él
    tenga en su tabla, que puede incluir valores propios y excluir los de
    fábrica que haya desactivado.
    """
    if clave is None or not str(clave).strip():
        return
    valores = await listar(db, tenant_id, catalogo)
    if str(clave) in {v.clave for v in valores}:
        return
    nombre = {
        CATALOGO_TIPO_PROYECTO: "tipo de proyecto",
        CATALOGO_FASE_PROYECTO: "fase de proyecto",
    }.get(catalogo, catalogo)
    disponibles = ", ".join(v.clave for v in valores) or "ninguno"
    raise business_rule(
        mensaje(
            que=f"«{clave}» no es un {nombre} de tu catálogo",
            porque=(
                "El valor tiene que existir y estar activo en el catálogo del "
                "inquilino; si no, ninguna pantalla sabría cómo llamarlo."
            ),
            accion=(
                f"Usa uno de los que hay ({disponibles}), o agrégalo en "
                "Administración → Catálogos."
            ),
        ),
        code="VALOR_FUERA_DE_CATALOGO",
    )
