"""MCS INF-03 — copias de seguridad automáticas de la base de datos.

La auditoría lo dejó NO CONFORME y el owner lo confirmó el 2026-08-06: **no
había ninguna**. Es el requisito abierto con el peor desenlace posible — el
resto degradan el producto; este pierde el trabajo de los clientes.

## Por qué una copia propia y no solo la de Railway

Railway hace copias en sus planes de pago, y son útiles. No bastan por dos
motivos que importan justo el día que hacen falta:

- **Viven en el mismo proveedor que la base.** Un fallo de cuenta —facturación,
  suspensión, borrado accidental del servicio— se lleva las dos cosas a la vez.
- **No se pueden verificar desde aquí.** MCS INF-03 pide que las copias
  existan; declararlas apoyándose en algo que este repositorio no puede
  comprobar es exactamente lo que el marco llama evidencia anotada.

Esta copia va al **almacenamiento de objetos** que el producto ya usa para
documentos (Cloudflare R2), que es un proveedor distinto del de la base. No
sustituye a la de Railway: la complementa, y es la que se puede verificar.

## Qué se guarda y cómo

`pg_dump` en formato **custom** (`-Fc`): comprimido, y restaurable con
`pg_restore` de forma selectiva —una sola tabla si hace falta— en vez de tener
que tragarse el volcado entero.

La clave lleva la fecha en formato ordenable (`AAAA-MM-DD`), así que listar el
prefijo sale ordenado por antigüedad sin tener que mirar metadatos.

## Retención

Se conservan **30 días**. Las más viejas se borran en la misma ejecución: una
retención que solo escribe crece hasta que alguien mira la factura, y entonces
lo que se recorta es la retención entera.

## Lo que esta copia NO cubre, dicho aquí

Los **documentos subidos** no entran: viven en el mismo almacenamiento de
objetos y volcarlos ahí no añadiría nada. Su durabilidad es la que da R2
(multizona), y está anotado en `runbooks/infra/uploads-storage.md`.

## Una copia que no se restaura no es una copia

`docs/runbooks/infra/respaldo-restauracion.md` tiene el procedimiento y —lo que
de verdad importa— la **prueba de restauración**, que es lo único que convierte
un archivo en el almacenamiento en una copia de seguridad. Sin ejecutarla, esto
son ficheros de los que nadie sabe si sirven.
"""
from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings

logger = logging.getLogger("pmoaas.respaldo")

#: Prefijo bajo el que viven las copias en el almacenamiento de objetos.
PREFIJO = "respaldos/postgres"

#: Días que se conservan. Ver el encabezado: la limpieza corre en la misma
#: ejecución que la copia, no en un trabajo aparte que se olvida de encender.
RETENCION_DIAS = 30

#: `pg_dump` puede tardar en una base grande. El tope evita que un volcado
#: colgado retenga el worker indefinidamente; que falle y se reintente al día
#: siguiente es mejor que un proceso que no vuelve.
TIEMPO_MAXIMO_SEGUNDOS = 1800


class RespaldoError(RuntimeError):
    """La copia no se pudo producir o no se pudo guardar."""


def _cliente_s3() -> Any:
    """El cliente de objetos, en un solo sitio y con la excusa escrita.

    `document_storage._get_s3_client` no está anotado —es pasivo de la línea
    base de `mypy --strict`— y llamarlo desde código tipado da
    `no-untyped-call`. Anotarlo allí obligaría a verificar el cuerpo de ese
    módulo entero, que es otro trabajo; concentrar aquí la única excepción
    deja las dos funciones de abajo limpias y la deuda visible en una línea.

    La importación va dentro porque `document_storage` arrastra `boto3`, y el
    proceso web no debería pagarlo por importar este módulo.
    """
    from app.services.document_storage import _get_s3_client

    return _get_s3_client()  # type: ignore[no-untyped-call]


def clave_del_dia(momento: datetime | None = None) -> str:
    """`respaldos/postgres/AAAA-MM-DD.dump`.

    Fecha ordenable a propósito: listar el prefijo sale ordenado por antigüedad
    sin leer metadatos, que es lo que hace barata la limpieza por retención.
    """
    cuando = momento or datetime.now(UTC)
    return f"{PREFIJO}/{cuando:%Y-%m-%d}.dump"


def _url_sincrona() -> str:
    """`pg_dump` no habla el dialecto asíncrono de SQLAlchemy.

    `DATABASE_URL` puede venir con `+asyncpg` o `+psycopg`; se normaliza al
    esquema que entiende `libpq`.
    """
    url = settings.DATABASE_URL
    # De más largo a más corto, y no es orden estético: con `+psycopg` primero,
    # un `postgresql+psycopg2://` se convertía en `postgresql2://` — una URL
    # que `libpq` no reconoce, ignora, y sustituye por el socket local. El
    # fallo resultante habla de un rol inexistente y no menciona la causa.
    # Lo encontró la prueba, no la lectura.
    for sufijo in ("+psycopg2", "+asyncpg", "+psycopg"):
        url = url.replace(sufijo, "")
    return url


def volcar() -> bytes:
    """El volcado de la base, en memoria.

    En formato custom (`-Fc`): comprimido y restaurable de forma selectiva con
    `pg_restore`. Un `.sql` plano obligaría a restaurar todo o a editar el
    fichero a mano el día del incidente, que es el peor momento para editar
    nada.
    """
    try:
        proceso = subprocess.run(
            ["pg_dump", "--format=custom", "--no-owner", "--no-acl", _url_sincrona()],
            capture_output=True,
            timeout=TIEMPO_MAXIMO_SEGUNDOS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RespaldoError(
            "`pg_dump` no está en el contenedor. Sin él no hay copia: "
            "añadí `postgresql-client` a la imagen del worker."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RespaldoError(
            f"El volcado excedió {TIEMPO_MAXIMO_SEGUNDOS}s y se abortó."
        ) from exc

    if proceso.returncode != 0:
        detalle = proceso.stderr.decode("utf-8", errors="replace")[:300]
        raise RespaldoError(f"`pg_dump` falló ({proceso.returncode}): {detalle}")
    if not proceso.stdout:
        # Un volcado vacío con código 0 es el fallo silencioso de esta función:
        # subiría un fichero de cero bytes que parece una copia hasta el día
        # que alguien intente restaurarlo.
        raise RespaldoError("`pg_dump` devolvió un volcado vacío.")
    return proceso.stdout


def guardar(datos: bytes, clave: str) -> None:
    """Sube el volcado al almacenamiento de objetos."""
    _cliente_s3().put_object(
        Bucket=settings.S3_BUCKET,
        Key=clave,
        Body=datos,
        ContentType="application/octet-stream",
    )


def limpiar_antiguos(hoy: datetime | None = None) -> int:
    """Borra las copias que superan la retención. Devuelve cuántas.

    Corre en la misma ejecución que la copia y no en un trabajo aparte: una
    retención que vive en su propio programado es una retención que alguien
    apaga sin darse cuenta, y lo que se descubre después es la factura.
    """
    cliente = _cliente_s3()
    corte = (hoy or datetime.now(UTC)) - timedelta(days=RETENCION_DIAS)
    listado = cliente.list_objects_v2(Bucket=settings.S3_BUCKET, Prefix=PREFIJO)
    borradas = 0
    for objeto in listado.get("Contents", []):
        nombre = objeto["Key"].rsplit("/", 1)[-1].removesuffix(".dump")
        try:
            fecha = datetime.strptime(nombre, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            # Algo que no sigue el patrón: no se toca. Borrar por descarte es
            # cómo una limpieza se lleva por delante lo que no le tocaba.
            continue
        if fecha < corte:
            cliente.delete_object(Bucket=settings.S3_BUCKET, Key=objeto["Key"])
            borradas += 1
    return borradas


def respaldar() -> dict[str, object]:
    """Copia del día: volcar, guardar y limpiar. Devuelve el resultado.

    El diccionario no es adorno: es lo que se emite al registro estructurado, y
    con `bytes` a la vista una copia que encoge de golpe se ve sin abrirla.
    """
    clave = clave_del_dia()
    datos = volcar()
    guardar(datos, clave)
    borradas = limpiar_antiguos()
    resultado = {"clave": clave, "bytes": len(datos), "borradas": borradas}
    logger.info("respaldo completado", extra=resultado)
    return resultado
