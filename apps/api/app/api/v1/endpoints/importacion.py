"""US-216 — Importación masiva de proyectos y recursos.

Del artboard «Onboarding masivo — Importación»: subir Excel/CSV → mapear
columnas → validar → confirmar. Cierra el bloque B5: «la carga inicial de 23
proyectos sin captura manual».

## Qué importa esto y qué no

Proyectos y recursos, al nivel de la organización. Los **planes** ya tienen su
importador —`/projects/{id}/tasks/import`, con vista previa, mapeo de columnas y
ayuda de IA (US-070, US-188)— y es por proyecto porque un WBS es del proyecto: el
`1.2` de uno no es el `1.2` de otro. Duplicar aquí ese camino daría dos
importadores de lo mismo que divergen con el primer arreglo.

## Los dos pasos, y por qué son dos

`preview` valida y **no escribe**; `confirm` escribe lo que el preview aprobó. La
vista previa existe porque una importación masiva es la operación menos
reversible del producto: 23 proyectos creados mal se borran de uno en uno. Ver
antes lo que va a pasar es lo que la hace segura.

El preview se guarda en Redis con una hora de vida, igual que el wizard de
tareas. Si expira, el `confirm` responde 404 y hay que volver a subir el archivo
— y es correcto: los catálogos pueden haber cambiado en esa hora, y confirmar
contra una validación vieja crearía duplicados que el preview había descartado.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import business_rule, forbidden, mensaje, not_found
from app.core.unidades import mebibytes
from app.db.session import get_db
from app.dominio.importacion import (
    CLASES,
    COLUMNAS,
    emparejar_columnas,
    resumen,
)
from app.services import importacion_masiva
from app.services.audit import write_audit
from app.services.import_ai import extract_raw_rows
from app.services.import_job_store import (
    create_job_id,
    delete_preview,
    load_preview,
    save_preview,
)

router = APIRouter(prefix="/imports", tags=["imports"])

#: Mismo techo que el wizard de tareas. Un archivo de 23 proyectos pesa
#: kilobytes; el límite está para el caso en que alguien suba otra cosa.
MAX_MB = 10

#: Techo de filas por archivo. Es generoso a propósito —una cartera grande son
#: cientos, no decenas de miles— y existe para que un archivo equivocado no
#: intente crear cien mil proyectos antes de que alguien lo note.
MAX_FILAS = 2000


def _tenant(cu: CurrentUser) -> UUID:
    # `effective_tenant_id` es texto; se convierte aquí y no en cada llamada, para
    # que todo este módulo hable de UUID y no mezcle las dos representaciones.
    if cu.effective_tenant_id is None:
        raise forbidden()
    return UUID(str(cu.effective_tenant_id))


def _clase_valida(clase: str) -> str:
    if clase not in CLASES:
        raise business_rule(
            mensaje(
                que=f"«{clase}» no es algo que se pueda importar",
                porque="Solo hay dos catálogos de carga masiva: proyectos y "
                "recursos. Los planes se importan por proyecto, desde su plan.",
                accion=f"Usa una de: {', '.join(CLASES)}.",
            )
        )
    return clase


def _origen(content_type: str, filename: str) -> str:
    ct = (content_type or "").lower()
    fn = (filename or "").lower()
    if (
        ct == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        or fn.endswith(".xlsx")
    ):
        return "xlsx"
    if ct in {"text/csv", "application/csv"} or fn.endswith(".csv"):
        return "csv"
    raise HTTPException(
        status_code=415,
        detail={
            "code": "UNSUPPORTED_MEDIA_TYPE",
            "hint": "La carga masiva acepta .xlsx y .csv. Para un plan de "
            "proyecto (incluido MS Project) usa el importador del plan.",
        },
    )


@router.get("/columns")
async def import_columns(
    kind: str = Query(description="projects | resources"),
    cu: CurrentUser = Depends(require_authenticated()),
) -> dict[str, Any]:
    """US-216 — qué columnas espera el archivo, con su ayuda y sus valores.

    Es la fuente de la plantilla descargable y del mapeo manual. Se sirve desde
    el backend y no se escribe en el frontend porque el vocabulario cerrado —los
    tipos de proyecto, las fases, las unidades de tarifa— vive en el dominio: dos
    listas separadas divergen en cuanto se añade un tipo.

    La **plantilla pequeña** del artboard es esta misma lista filtrada por
    `obligatoria`, no otra plantilla. Así no puede desincronizarse de la grande.
    """
    clase = _clase_valida(kind)
    _tenant(cu)
    return {
        "kind": clase,
        "columns": [
            {
                "key": c.clave,
                "label": c.etiqueta,
                "required": c.obligatoria,
                "help": c.ayuda,
                "aliases": list(c.alias),
                "values": list(c.valores),
                "type": c.tipo,
            }
            for c in COLUMNAS[clase]
        ],
    }


@router.post("/preview")
async def preview_import(
    kind: str = Form(description="projects | resources"),
    organization_id: UUID = Form(),
    file: UploadFile = File(),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """US-216 — valida el archivo entero y **no escribe nada**.

    Devuelve fila por fila su estado y sus problemas. Se validan **todas** aunque
    la primera falle: un archivo de 23 proyectos con un error en el 7 tiene 22
    filas buenas, y abortar entero obliga a arreglar y resubir a ciegas sin saber
    si hay más errores detrás — que es el bucle que hace abandonar una
    importación.
    """
    clase = _clase_valida(kind)
    tenant_id = _tenant(cu)
    if not await importacion_masiva.organizacion_valida(db, tenant_id, organization_id):
        raise not_found("Organización")

    origen = _origen(file.content_type or "", file.filename or "")
    datos = await file.read()
    if not datos:
        raise business_rule(
            mensaje(
                que="El archivo está vacío",
                porque="No hay ninguna fila que importar.",
                accion="Comprueba que subiste el archivo correcto.",
            )
        )
    if len(datos) > mebibytes(MAX_MB):
        raise HTTPException(
            status_code=413,
            detail={"code": "PAYLOAD_TOO_LARGE", "max_mb": MAX_MB},
        )

    try:
        crudas = extract_raw_rows(origen, datos, limit=MAX_FILAS + 1)
    except ValueError as exc:
        raise business_rule(
            mensaje(
                que=f"El archivo {origen.upper()} no se pudo leer: {exc}",
                porque="El contenido no coincide con el formato que anuncia su "
                "extensión.",
                accion="Expórtalo de nuevo desde su aplicación y vuelve a subirlo.",
            )
        )
    if not crudas:
        raise business_rule(
            mensaje(
                que="El archivo no tiene filas",
                porque="La primera fila tiene que ser la de encabezados y "
                "debajo al menos una fila de datos.",
                accion="Descarga la plantilla y úsala como base.",
            )
        )

    encabezados = [(c or "").strip() for c in crudas[0]]
    cuerpo = crudas[1 : MAX_FILAS + 1]
    truncado = len(crudas) - 1 > MAX_FILAS
    mapeo = emparejar_columnas(encabezados, clase)

    # Sin las obligatorias no hay nada que validar fila por fila: el error es del
    # archivo, no de las filas, y decirlo así evita un reporte de 23 filas
    # inválidas por la misma causa.
    faltan = [
        c.etiqueta
        for c in COLUMNAS[clase]
        if c.obligatoria and mapeo.get(c.clave) is None
    ]
    if faltan:
        raise business_rule(
            mensaje(
                que=f"Faltan columnas obligatorias: {', '.join(faltan)}",
                porque="Sin ellas no se puede crear ninguna fila, así que "
                "validar el resto no diría nada útil.",
                accion="Descarga la plantilla, o renombra los encabezados de tu "
                "archivo para que coincidan.",
            )
        )

    reconocidos = {c for c in mapeo.values() if c}
    indices = {
        clave: encabezados.index(cabecera)
        for clave, cabecera in mapeo.items()
        if cabecera is not None and cabecera in encabezados
    }
    # El número que se reporta es la **línea real del archivo**, contando el
    # encabezado. Enumerar las filas ya filtradas desplazaría los números en
    # cuanto hubiera una fila vacía en medio, y entonces «revisa la fila 12» no
    # apuntaría a la fila 12 del Excel — que es lo único que ese número sirve
    # para hacer.
    filas_crudas = [
        (
            linea,
            {
                clave: (fila[i] if i < len(fila) else None)
                for clave, i in indices.items()
            },
        )
        for linea, fila in enumerate(cuerpo, start=2)
        # Una fila totalmente vacía es el relleno que deja Excel al final de una
        # hoja; contarla como inválida llenaría el reporte de ruido.
        if any((c or "").strip() for c in fila)
    ]

    filas = await importacion_masiva.revisar(
        db,
        tenant_id=tenant_id,
        organization_id=organization_id,
        clase=clase,
        filas_crudas=filas_crudas,
    )

    job_id = create_job_id()
    save_preview(
        job_id,
        {
            "kind": clase,
            "organization_id": str(organization_id),
            "tenant_id": str(tenant_id),
            "rows": [
                {
                    "numero": f.numero,
                    "valores": f.valores,
                    "estado": f.estado,
                    "problemas": [
                        {"columna": p.columna, "mensaje": p.mensaje}
                        for p in f.problemas
                    ],
                    "choca_con": f.choca_con,
                }
                for f in filas
            ],
        },
    )

    return {
        "job_id": job_id,
        "kind": clase,
        # Los encabezados que el archivo trae y el sistema no reconoce. Se
        # devuelven para que la interfaz los pueda mapear a mano: descartarlos en
        # silencio deja al usuario sin saber que su columna «Owner» se ignoró.
        "unmapped_headers": [
            h for h in encabezados if h and h not in reconocidos
        ],
        "mapping": mapeo,
        "summary": resumen(filas),
        "truncated": truncado,
        "max_rows": MAX_FILAS,
        "rows": [
            {
                "row": f.numero,
                "state": f.estado,
                "name": f.valores.get("name"),
                "values": {k: str(v) for k, v in f.valores.items()},
                "problems": [
                    {"column": p.columna, "message": p.mensaje} for p in f.problemas
                ],
                "conflicts_with": f.choca_con,
            }
            for f in filas
        ],
    }


@router.post("/{job_id}/confirm", status_code=201)
async def confirm_import(
    job_id: str,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """US-216 — crea las filas válidas del preview.

    Las **inválidas y las duplicadas no se tocan**. Una duplicada no se
    actualiza, y esa es la decisión con más consecuencias de esta US: una
    importación se corre dos veces —se cayó la red, alguien la repitió, el
    archivo llegó corregido— y actualizar en silencio pisaría lo que alguien
    editó a mano después de la primera corrida. El caso concreto: se importa, el
    PM corrige las fechas en la aplicación, alguien resube el Excel original y
    las fechas vuelven atrás sin que nadie se enterase.

    El preview se borra al confirmar. Confirmar dos veces el mismo trabajo daría
    el doble de proyectos, y es exactamente el error que la detección de
    duplicados no puede atrapar dentro de la misma transacción.
    """
    tenant_id = _tenant(cu)
    guardado = load_preview(job_id)
    if guardado is None:
        raise not_found("Vista previa de importación")
    # El preview lleva el inquilino que lo creó: un `job_id` es un UUID y no un
    # secreto, y sin esta comprobación quien lo adivinara escribiría en otro
    # inquilino.
    if guardado.get("tenant_id") != str(tenant_id):
        raise not_found("Vista previa de importación")

    from app.dominio.importacion import FilaLeida, Problema

    filas = [
        FilaLeida(
            numero=int(r["numero"]),
            valores=dict(r["valores"]),
            estado=r["estado"],
            problemas=[
                Problema(p["columna"], p["mensaje"]) for p in r.get("problemas", [])
            ],
            choca_con=r.get("choca_con"),
        )
        for r in guardado.get("rows", [])
    ]
    # Las fechas y los números viajaron a Redis como texto. Se reconvierten aquí
    # y no se re-valida el archivo: lo que el usuario aprobó es este preview.
    _rehidratar(filas, guardado["kind"])

    resultado = await importacion_masiva.aplicar(
        db,
        tenant_id=tenant_id,
        organization_id=UUID(guardado["organization_id"]),
        clase=guardado["kind"],
        filas=filas,
    )
    await write_audit(
        db,
        tenant_id=tenant_id,
        user_id=cu.id,
        action=f"import.{guardado['kind']}",
        entity_type="organization",
        entity_id=guardado["organization_id"],
        details={
            "created": resultado["created_count"],
            "skipped_invalid": resultado["skipped_invalid"],
            "skipped_duplicate": resultado["skipped_duplicate"],
        },
    )
    await db.commit()
    delete_preview(job_id)
    return resultado


def _rehidratar(filas: list[Any], clase: str) -> None:
    """Devuelve a su tipo los valores que Redis guardó como texto.

    Se hace sobre el preview guardado y no revalidando el archivo: el archivo ya
    no está, y lo que el usuario aprobó es este preview. Un valor que no se pueda
    reconvertir se descarta en lugar de tumbar la confirmación — ya pasó la
    validación una vez, y perder un presupuesto opcional es mejor que perder las
    23 filas.
    """
    from datetime import date

    from app.dominio.importacion import COLUMNAS

    tipos = {c.clave: c.tipo for c in COLUMNAS.get(clase, ())}
    for fila in filas:
        for clave, valor in list(fila.valores.items()):
            tipo = tipos.get(clave, "texto")
            if not isinstance(valor, str):
                continue
            try:
                if tipo == "fecha":
                    fila.valores[clave] = date.fromisoformat(valor[:10])
                elif tipo == "entero":
                    fila.valores[clave] = int(float(valor))
                elif tipo == "decimal":
                    fila.valores[clave] = float(valor)
            except ValueError:
                del fila.valores[clave]
