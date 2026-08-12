"""MCS SUM-02 — el contenedor no vuelve a correr como root sin que se note.

> «Las imágenes de contenedor DEBEN ejecutarse con usuario sin privilegios.»

La auditoría R1 (`docs/archive/conformidad/2026-08-04-mcs-r1.md`) encontró que
`apps/api/Dockerfile` no tenía ninguna directiva `USER`: la imagen parte de
`python:3.12-slim`, cuyo usuario por defecto es `root`, y ahí se quedaba.

Esta suite es estática a propósito. Lo natural sería construir la imagen y
comprobar `id -u`, pero eso ata la suite de la API a un demonio Docker que ni
el CI de `api-tests-smoke` ni una máquina de desarrollo tienen levantados. Lo
que se vigila es lo que de verdad se revierte por descuido —que alguien añada
una etapa al final y el `USER` quede antes de ella, o que un `COPY` posterior
vuelva a dejar el árbol en manos de root—, y eso se lee del fichero.

Lo que NO comprueba, y conviene saberlo: que el usuario tenga permisos
suficientes en tiempo de ejecución. Eso solo lo demuestra un despliegue. El
razonamiento que se hizo en su lugar está escrito en el propio `Dockerfile`,
junto al `useradd`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"
LINEAS = DOCKERFILE.read_text(encoding="utf-8").splitlines()


def _instrucciones() -> list[tuple[int, str, str]]:
    """`(nº de línea, directiva, resto)` de cada instrucción, sin comentarios."""
    fuera = []
    for numero, linea in enumerate(LINEAS, start=1):
        limpia = linea.strip()
        if not limpia or limpia.startswith("#"):
            continue
        partes = limpia.split(maxsplit=1)
        fuera.append((numero, partes[0].upper(), partes[1] if len(partes) > 1 else ""))
    return fuera


INSTRUCCIONES = _instrucciones()


def _etapa_final() -> list[tuple[int, str, str]]:
    """Las instrucciones desde el último `FROM`, que es la imagen que se publica.

    Las etapas intermedias (`mpxj-build`, `temurin-jre`) sí corren como root y
    deben seguir haciéndolo: compilan y descargan. Solo importa la última.
    """
    ultimo_from = max(
        i for i, (_, directiva, _) in enumerate(INSTRUCCIONES) if directiva == "FROM"
    )
    return INSTRUCCIONES[ultimo_from:]


def test_la_etapa_final_declara_un_usuario():
    """Sin `USER`, el proceso corre como root — que es el defecto que R1 midió."""
    usuarios = [(n, resto) for n, d, resto in _etapa_final() if d == "USER"]
    assert usuarios, (
        "La etapa final del Dockerfile no declara `USER`: el proceso correría "
        "como root (MCS SUM-02). Ver el comentario junto al `useradd`."
    )


def test_el_usuario_no_es_root():
    """`USER root` cumpliría la letra del requisito y ninguna de sus intenciones."""
    for _, resto in [(n, r) for n, d, r in _etapa_final() if d == "USER"]:
        cuenta = resto.split(":")[0].strip()
        assert cuenta.lower() not in {"root", "0"}, (
            f"La etapa final declara `USER {resto}`. Un usuario sin privilegios "
            "no es root ni UID 0 (MCS SUM-02)."
        )


def test_el_usuario_existe_antes_de_usarse():
    """Un `USER` que nombra una cuenta inexistente arranca igual, con UID crudo.

    Docker no falla si la cuenta no está en `/etc/passwd`: corre con ese
    nombre como si fuera un UID numérico y el contenedor se comporta de forma
    difícil de diagnosticar. Se comprueba que algún `RUN` anterior la crea.
    """
    etapa = _etapa_final()
    for indice, (numero, directiva, resto) in enumerate(etapa):
        if directiva != "USER":
            continue
        cuenta = resto.split(":")[0].strip()
        creada = any(
            d == "RUN" and re.search(rf"\b(useradd|adduser)\b.*\b{re.escape(cuenta)}\b", r)
            for _, d, r in etapa[:indice]
        )
        assert creada, (
            f"`USER {cuenta}` (línea {numero}) no viene precedido de un `useradd` "
            f"que cree esa cuenta en la etapa final."
        )


@pytest.mark.parametrize("directiva", ["COPY", "ADD", "RUN"])
def test_nada_se_ejecuta_como_root_despues_del_cambio_de_usuario(directiva):
    """El orden es el control: `USER` al final no protege lo que va después.

    Un `RUN` posterior corre con privilegios y un `COPY` sin `--chown` deja el
    destino en manos de root, que es justo lo que SUM-02 quiere evitar. La
    excepción es un `COPY --chown` explícito: ese sí entrega la propiedad.
    """
    etapa = _etapa_final()
    tras_user = False
    for numero, actual, resto in etapa:
        if actual == "USER":
            tras_user = True
            continue
        if not tras_user or actual != directiva:
            continue
        if directiva in {"COPY", "ADD"} and "--chown" in resto:
            continue
        pytest.fail(
            f"`{directiva}` en la línea {numero} va después del `USER` de la etapa "
            f"final. Movelo antes, o añadile `--chown` si es un COPY/ADD "
            f"(MCS SUM-02)."
        )
