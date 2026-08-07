"""MCS SEG-01 · ASVS 12.4.2 — lo que se sube se analiza antes de guardarse.

«Verify that files obtained from untrusted sources are scanned by antivirus
scanners to prevent upload and serving of known malicious content.»

## Dos controles, no uno

Al medir salió que el problema tenía dos mitades, y solo una necesita motor
antivirus:

**1. El tipo declarado no se comprobaba contra los bytes.** `_resolve_mime` lo
tomaba de la cabecera que manda el navegador, con respaldo en la extensión del
nombre. Las dos las escribe quien sube el archivo. Un ejecutable renombrado a
`.pdf` y anunciado como `application/pdf` entraba, se guardaba con extensión
`.pdf` y se servía después con `Content-Type: application/pdf`. Eso no hace
falta un antivirus para cerrarlo: hace falta **mirar los bytes**, y es lo que
`verifica_firma` hace. Va siempre, sin configurar nada.

**2. El contenido conocido como malicioso.** Eso sí necesita motor, y un motor
no se puede escribir en Python: hace falta una base de firmas que se actualiza a
diario. `analiza` habla con **ClamAV** por su protocolo `INSTREAM` si
`CLAMAV_URL` está configurado.

## Qué pasa si no hay motor configurado

Se declara y se registra, no se finge. `POLITICA_SIN_MOTOR` dice qué hacer:

* `permitir` (por defecto) — se guarda y se **anota** que no se analizó. Es lo
  honesto mientras no haya motor: fallar cerrado dejaría el producto sin subida
  de documentos el día que se despliegue, que es peor y más probable que el
  daño que evita.
* `rechazar` — no se guarda nada que no se haya podido analizar. Es lo correcto
  en cuanto el motor exista y para quien trate documentos de terceros.

La diferencia con no hacer nada es que **está escrito**: `estado_del_analisis()`
lo reporta y el mapeo ASVS cita el estado real del despliegue, en vez de un
«sí» que nadie puede comprobar.
"""
from __future__ import annotations

import logging
import socket
import struct
from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.config import settings

log = logging.getLogger(__name__)

#: Firma → extensiones que puede llevar. Solo los formatos que el producto
#: acepta; lo demás ya lo rechaza la lista blanca de tipos.
#:
#: `xlsx`, `docx` y `pptx` son ZIP por dentro, así que comparten firma: la
#: comprobación distingue «esto es un ZIP» de «esto es un ejecutable», que es
#: lo que importa. Distinguir un `.docx` de un `.xlsx` exigiría abrir el ZIP y
#: no aporta nada — los dos son igual de inofensivos como bytes.
_FIRMAS: tuple[tuple[bytes, frozenset[str]], ...] = (
    (b"%PDF-", frozenset({"pdf"})),
    (b"PK\x03\x04", frozenset({"xlsx", "docx", "pptx"})),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", frozenset({"xls", "doc", "ppt"})),
    (b"\x89PNG\r\n\x1a\n", frozenset({"png"})),
    (b"\xff\xd8\xff", frozenset({"jpg"})),
)

#: Extensiones sin firma propia: son texto y cualquier byte es válido. No se
#: comprueban por firma sino por lo contrario — que NO empiecen por una firma
#: binaria conocida, que es como se cuela un ejecutable llamado `datos.csv`.
_SIN_FIRMA = frozenset({"csv", "txt"})

#: Comienzos que no puede tener un archivo que dice ser de este producto,
#: cualquiera que sea su extensión.
_EJECUTABLES: tuple[tuple[bytes, str], ...] = (
    (b"MZ", "ejecutable de Windows"),
    (b"\x7fELF", "ejecutable de Linux"),
    (b"\xca\xfe\xba\xbe", "ejecutable de macOS"),
    (b"\xcf\xfa\xed\xfe", "ejecutable de macOS"),
    (b"#!", "guion con intérprete"),
    (b"\xd4\xc3\xb2\xa1", "captura de red"),
)

#: Qué hacer cuando no hay motor antivirus configurado. Ver el docstring.
POLITICA_SIN_MOTOR = "permitir"


class ArchivoRechazadoError(ValueError):
    """El archivo no pasa el análisis."""


@dataclass(frozen=True)
class Resultado:
    """Qué se hizo con el archivo y con qué motor."""

    analizado: bool
    motor: str
    detalle: str = ""


def verifica_firma(datos: bytes, ext: str) -> None:
    """Los bytes tienen que corresponder con lo que el archivo dice ser.

    Lanza `ArchivoRechazadoError` si no. Es la mitad del control que no necesita
    motor, y la que cierra el agujero real: hasta ahora el tipo salía de la
    cabecera del navegador y del nombre del archivo, que los escribe quien sube.
    """
    if not datos:
        return

    for magia, que_es in _EJECUTABLES:
        if datos.startswith(magia):
            raise ArchivoRechazadoError(
                f"el contenido es un {que_es}, no un documento «.{ext}»"
            )

    if ext in _SIN_FIRMA:
        return  # texto: cualquier byte vale, y los ejecutables ya cayeron arriba

    for magia, extensiones in _FIRMAS:
        if datos.startswith(magia):
            if ext in extensiones:
                return
            raise ArchivoRechazadoError(
                f"el contenido no corresponde con «.{ext}»: "
                f"los bytes son de {'/'.join(sorted(extensiones))}"
            )

    raise ArchivoRechazadoError(
        f"el contenido no tiene la firma de un «.{ext}»"
    )


def _analiza_con_clamav(datos: bytes, url: str) -> Resultado:
    """Protocolo `INSTREAM` de clamd: `zINSTREAM\\0`, trozos con su longitud en
    big-endian, y un tamaño cero para cerrar.

    Se habla el protocolo directamente y no por `pyclamd` para no añadir una
    dependencia por veinte líneas —y porque el paquete no se mantiene—.
    """
    partes = urlparse(url)
    destino = (partes.hostname or "localhost", partes.port or 3310)
    with socket.create_connection(destino, timeout=10.0) as s:
        s.sendall(b"zINSTREAM\0")
        for i in range(0, len(datos), 8192):
            trozo = datos[i : i + 8192]
            s.sendall(struct.pack("!L", len(trozo)) + trozo)
        s.sendall(struct.pack("!L", 0))
        respuesta = s.recv(4096).decode("utf-8", errors="replace").strip("\0 \n")

    if respuesta.endswith("OK"):
        return Resultado(analizado=True, motor="clamav", detalle=respuesta)
    if "FOUND" in respuesta:
        raise ArchivoRechazadoError(f"el antivirus detectó contenido malicioso: {respuesta}")
    raise RuntimeError(f"respuesta inesperada de clamd: {respuesta[:200]}")


def analiza(datos: bytes, ext: str) -> Resultado:
    """Comprueba firma y, si hay motor, analiza el contenido.

    Lanza `ArchivoRechazadoError` si el archivo no debe guardarse.
    """
    verifica_firma(datos, ext)

    url = getattr(settings, "CLAMAV_URL", "") or ""
    if not url:
        if POLITICA_SIN_MOTOR == "rechazar":
            raise ArchivoRechazadoError(
                "no hay motor antivirus configurado y la política es no guardar "
                "lo que no se puede analizar"
            )
        # Se anota. Un control que no corre y no deja rastro es indistinguible
        # de uno que corre y no encuentra nada.
        log.info("ASVS 12.4.2 — sin CLAMAV_URL: %d bytes .%s guardados sin analizar", len(datos), ext)
        return Resultado(analizado=False, motor="ninguno", detalle="sin motor configurado")

    try:
        return _analiza_con_clamav(datos, url)
    except ArchivoRechazadoError:
        raise
    except Exception as exc:  # el motor está caído o no responde
        log.error("ASVS 12.4.2 — el motor antivirus no respondió (%s): %s", url, exc)
        if POLITICA_SIN_MOTOR == "rechazar":
            raise ArchivoRechazadoError(
                "el motor antivirus no respondió y la política es no guardar lo "
                "que no se puede analizar"
            ) from exc
        return Resultado(analizado=False, motor="clamav", detalle=f"no respondió: {exc}")


def estado_del_analisis() -> dict[str, object]:
    """Qué está pasando de verdad en este despliegue.

    Existe para que el mapeo ASVS pueda citar el estado real y no un «sí» que
    nadie puede comprobar, y para que `/health` lo pueda exponer si hace falta.
    """
    url = getattr(settings, "CLAMAV_URL", "") or ""
    return {
        "firma_verificada": True,
        "motor": "clamav" if url else "ninguno",
        "politica_sin_motor": POLITICA_SIN_MOTOR,
    }
