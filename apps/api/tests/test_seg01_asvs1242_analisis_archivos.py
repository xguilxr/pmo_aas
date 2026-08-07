"""MCS SEG-01 · ASVS 12.4.2 — lo que se sube se analiza antes de guardarse.

«Verify that files obtained from untrusted sources are scanned by antivirus
scanners to prevent upload and serving of known malicious content.»

## Lo que enseñó medir

El control tiene dos mitades y solo una necesita motor antivirus.

La que **no** lo necesita era un agujero real: `_resolve_mime` tomaba el tipo de
la cabecera del navegador, con respaldo en la extensión del nombre — las dos las
escribe quien sube el archivo—. Un ejecutable renombrado a `.pdf` y anunciado
como `application/pdf` entraba, se guardaba con extensión `.pdf` y se servía
después con `Content-Type: application/pdf`. Para eso no hace falta un
antivirus: hace falta mirar los bytes. §1 y §3.

La que sí lo necesita —contenido conocido como malicioso— exige una base de
firmas que se actualiza a diario, y eso no se escribe en Python. §2 fija que el
enganche funcione y, sobre todo, que **cuando no hay motor se sepa**: un control
que no corre y no deja rastro es indistinguible de uno que corre y no encuentra
nada.
"""
from __future__ import annotations

import pytest

from app.services import analisis_archivos as av
from app.services.analisis_archivos import (
    ArchivoRechazadoError,
    analiza,
    estado_del_analisis,
    verifica_firma,
)

PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
ZIP = b"PK\x03\x04\x14\x00\x06\x00"
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF"
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
EXE = b"MZ\x90\x00\x03\x00\x00\x00"
ELF = b"\x7fELF\x02\x01\x01\x00"


# ---------------------------------------------------------------------------
# §1 — Los bytes tienen que corresponder con lo que el archivo dice ser
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "datos,ext",
    [
        (PDF, "pdf"), (ZIP, "xlsx"), (ZIP, "docx"), (ZIP, "pptx"),
        (OLE, "xls"), (OLE, "doc"), (PNG, "png"), (JPG, "jpg"),
        (b"nombre,importe\nA,10\n", "csv"), (b"cualquier texto", "txt"),
    ],
)
def test_asvs1242_lo_legitimo_pasa(datos, ext):
    """Sin esto la defensa se quita en dos semanas por romper las subidas."""
    verifica_firma(datos, ext)


@pytest.mark.parametrize(
    "nombre,datos,ext",
    [
        ("ejecutable de Windows disfrazado de PDF", EXE, "pdf"),
        ("ejecutable de Linux disfrazado de PDF", ELF, "pdf"),
        ("ejecutable disfrazado de CSV", EXE, "csv"),
        ("ejecutable disfrazado de TXT", EXE, "txt"),
        ("guion disfrazado de CSV", b"#!/bin/sh\nrm -rf /\n", "csv"),
        ("ZIP que dice ser PDF", ZIP, "pdf"),
        ("PDF que dice ser XLSX", PDF, "xlsx"),
        ("basura que dice ser PNG", b"no soy una imagen", "png"),
    ],
)
def test_asvs1242_lo_disfrazado_se_rechaza(nombre, datos, ext):
    with pytest.raises(ArchivoRechazadoError):
        verifica_firma(datos, ext)


def test_asvs1242_el_csv_admite_cualquier_texto():
    """Un CSV no tiene firma: cualquier byte de texto vale.

    Lo que se comprueba en su lugar es lo contrario —que NO empiece por una
    firma binaria conocida—, que es como se cuela un ejecutable llamado
    `datos.csv`. El caso legítimo tiene que seguir pasando.
    """
    verifica_firma("nombre;importe\nÑandú;10,50\n".encode(), "csv")
    verifica_firma(b"\xef\xbb\xbfcon BOM,1\n", "csv")  # Excel escribe BOM


# ---------------------------------------------------------------------------
# §2 — El motor: se usa si está, y si no está se sabe
# ---------------------------------------------------------------------------


def test_asvs1242_sin_motor_se_deja_pasar_pero_se_declara(monkeypatch):
    """`permitir` es lo honesto mientras no haya motor. Lo que no vale es
    fingir que se analizó: el resultado lo dice."""
    monkeypatch.setattr(av.settings, "CLAMAV_URL", "")
    resultado = analiza(PDF, "pdf")
    assert resultado.analizado is False
    assert resultado.motor == "ninguno"


def test_asvs1242_sin_motor_la_firma_se_comprueba_igual(monkeypatch):
    """La mitad que no necesita motor no depende de que haya motor.

    Es lo que impide que «no tenemos antivirus» acabe significando «no se mira
    nada de lo que se sube».
    """
    monkeypatch.setattr(av.settings, "CLAMAV_URL", "")
    with pytest.raises(ArchivoRechazadoError):
        analiza(EXE, "pdf")


def test_asvs1242_con_politica_rechazar_no_se_guarda_sin_analizar(monkeypatch):
    monkeypatch.setattr(av.settings, "CLAMAV_URL", "")
    monkeypatch.setattr(av, "POLITICA_SIN_MOTOR", "rechazar")
    with pytest.raises(ArchivoRechazadoError):
        analiza(PDF, "pdf")


def test_asvs1242_el_motor_que_detecta_algo_rechaza(monkeypatch):
    monkeypatch.setattr(av.settings, "CLAMAV_URL", "tcp://clamav:3310")
    monkeypatch.setattr(
        av, "_analiza_con_clamav",
        lambda datos, url: (_ for _ in ()).throw(
            ArchivoRechazadoError("el antivirus detectó contenido malicioso: Eicar-Test FOUND")
        ),
    )
    with pytest.raises(ArchivoRechazadoError, match="malicioso"):
        analiza(PDF, "pdf")


def test_asvs1242_el_motor_limpio_deja_pasar(monkeypatch):
    monkeypatch.setattr(av.settings, "CLAMAV_URL", "tcp://clamav:3310")
    monkeypatch.setattr(
        av, "_analiza_con_clamav",
        lambda datos, url: av.Resultado(analizado=True, motor="clamav", detalle="stream: OK"),
    )
    resultado = analiza(PDF, "pdf")
    assert resultado.analizado is True


def test_asvs1242_el_motor_caido_no_tumba_la_subida(monkeypatch):
    """Con la política por defecto, un ClamAV caído no puede dejar al producto
    sin subida de documentos — pero el resultado dice que no se analizó."""
    monkeypatch.setattr(av.settings, "CLAMAV_URL", "tcp://clamav:3310")
    monkeypatch.setattr(
        av, "_analiza_con_clamav",
        lambda datos, url: (_ for _ in ()).throw(ConnectionRefusedError("caído")),
    )
    resultado = analiza(PDF, "pdf")
    assert resultado.analizado is False
    assert "no respondió" in resultado.detalle


def test_asvs1242_el_estado_es_consultable():
    """El mapeo ASVS cita el estado real del despliegue y no un «sí»."""
    estado = estado_del_analisis()
    assert estado["firma_verificada"] is True
    assert estado["motor"] in ("clamav", "ninguno")
    assert estado["politica_sin_motor"] in ("permitir", "rechazar")


# ---------------------------------------------------------------------------
# §3 — De punta a punta: no se guarda un ejecutable disfrazado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs1242_el_endpoint_rechaza_un_ejecutable_disfrazado(
    client, db_session, tmp_path, monkeypatch
):
    """El agujero concreto que este control cierra.

    Antes, el tipo salía de la cabecera que manda el navegador: se declaraba
    `application/pdf`, se guardaba como `.pdf` y se servía con ese
    `Content-Type`. Ahora se miran los bytes.
    """
    from app.services.document_storage import save_document

    monkeypatch.setattr(av.settings, "CLAMAV_URL", "")
    from app.core.config import settings as cfg

    monkeypatch.setattr(cfg, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(cfg, "STORAGE_PATH", str(tmp_path))

    class _Upload:
        content_type = "application/pdf"
        filename = "informe.pdf"

        async def read(self):
            return EXE + b"\x00" * 200

    from app.core.errors import AppError

    with pytest.raises(AppError) as exc:
        await save_document("t1", "p1", _Upload(), "d1")
    assert exc.value.status_code == 400
    assert not list(tmp_path.rglob("*.pdf")), "No puede quedar nada escrito"


@pytest.mark.asyncio
async def test_asvs1242_el_endpoint_guarda_un_pdf_de_verdad(
    client, db_session, tmp_path, monkeypatch
):
    from app.core.config import settings as cfg
    from app.services.document_storage import save_document

    monkeypatch.setattr(av.settings, "CLAMAV_URL", "")
    monkeypatch.setattr(cfg, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(cfg, "STORAGE_PATH", str(tmp_path))

    class _Upload:
        content_type = "application/pdf"
        filename = "informe.pdf"

        async def read(self):
            return PDF + b"contenido del informe" * 10

    url, mime = await save_document("t1", "p1", _Upload(), "d2")
    assert mime == "application/pdf"
    assert list(tmp_path.rglob("*.pdf")), "El PDF legítimo tiene que guardarse"
