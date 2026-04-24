"""US-069 — Parser MPP nativo vía MPXJ (Java).

MPXJ (net.sf.mpxj) lee el formato binario propietario .mpp que MS Project
usa desde 2002. No existe una port pura en Python; la librería canónica
es Java. En vez de agregar JPype (bridge Python↔Java con dependencia a
JVM compartido) corremos MPXJ como subprocess:

    java -cp "/opt/mpxj/lib/*:/opt/mpxj/cli" MpxjCli <input.mpp>

El wrapper `MpxjCli.java` (ver `mpxj_cli/MpxjCli.java`) se compila en la
etapa de build del Dockerfile y emite un JSON con la misma forma que
produce `xlsx_task_parser.parse_xlsx`. Eso permite reusar el mismo
adaptador en `endpoints/tasks.py` sin tocar el loop de persistencia.

Errores del CLI (archivo corrupto, versión de MSP no soportada, JVM
crash) se traducen a `ValueError` con mensaje acotado. El timeout por
defecto es 60s y se ajusta con `MPP_PARSE_TIMEOUT_SECONDS`.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

from app.services.xlsx_task_parser import ParsedTask, XlsxParseResult

logger = logging.getLogger(__name__)

# Classpath default para producción (set en Dockerfile). El Java runtime
# expande el wildcard `*` automáticamente.
DEFAULT_CLI_CP = "/opt/mpxj/lib/*:/opt/mpxj/cli"
DEFAULT_TIMEOUT_SECONDS = 60


def _classpath() -> str:
    return os.environ.get("MPXJ_CLI_CP", DEFAULT_CLI_CP)


def _timeout() -> int:
    raw = os.environ.get("MPP_PARSE_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        return max(5, int(raw))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _parse_date(v: object) -> date | None:
    if v is None or v == "":
        return None
    try:
        return datetime.fromisoformat(str(v)).date()
    except ValueError:
        return None


def _row_to_task(row: dict) -> ParsedTask:
    return ParsedTask(
        row_number=int(row.get("row_number") or 0),
        name=str(row.get("name") or "").strip(),
        wbs=(row.get("wbs") or None),
        start_date=_parse_date(row.get("start_date")),
        end_date=_parse_date(row.get("end_date")),
        duration_days=(
            int(row["duration_days"]) if row.get("duration_days") is not None else None
        ),
        progress=int(row.get("progress") or 0),
        is_milestone=bool(row.get("is_milestone")),
        predecessors_raw=(row.get("predecessors_raw") or None),
        resources_raw=(row.get("resources_raw") or None),
    )


def parse_mpp(data: bytes) -> XlsxParseResult:
    """Parsea un .mpp y devuelve el mismo shape que `parse_xlsx`.

    El endpoint usa el adaptador `_TaskShim` de `endpoints/tasks.py` sobre
    este resultado para reusar el loop de persistencia existente.

    Raises:
        ValueError: archivo inválido, CLI no disponible o timeout.
    """
    if not data:
        raise ValueError("archivo vacío")

    if shutil.which("java") is None:
        # Más útil que dejar caer el FileNotFoundError del Popen: permite
        # al endpoint traducir a 503 y al runbook explicar qué falta.
        raise ValueError(
            "Java runtime no disponible en el contenedor. "
            "Ver docs/runbooks/infra/mpp-import.md."
        )

    with tempfile.NamedTemporaryFile(suffix=".mpp", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        try:
            proc = subprocess.run(
                ["java", "-cp", _classpath(), "MpxjCli", tmp_path],
                capture_output=True,
                timeout=_timeout(),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning(
                "MPP parsing timed out after %ss (file_size=%s)",
                _timeout(),
                len(data),
            )
            raise ValueError(
                f"parsing MPP excedió el timeout de {_timeout()}s"
            ) from exc
        except FileNotFoundError as exc:
            raise ValueError(
                "Java runtime no disponible en el contenedor."
            ) from exc

        if proc.returncode != 0:
            # stderr truncado: evitamos filtrar paths del host al cliente.
            stderr_snippet = proc.stderr.decode("utf-8", errors="replace")[:200]
            logger.warning("MPXJ CLI returncode=%s stderr=%s", proc.returncode, stderr_snippet)
            raise ValueError(
                "archivo MPP corrupto o versión de MS Project no soportada"
            )

        try:
            payload = json.loads(proc.stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:
            logger.exception("MPXJ CLI emitió JSON inválido")
            raise ValueError("respuesta inesperada del parser MPP") from exc

        result = XlsxParseResult()
        for row in payload.get("tasks", []):
            try:
                result.tasks.append(_row_to_task(row))
            except Exception as exc:
                result.errors.append(
                    {"row": row.get("row_number"), "error": str(exc)}
                )

        if not result.tasks and not result.errors:
            # El archivo se abrió pero no tenía tareas utilizables (solo
            # el root / summary). Lo tratamos como error de usuario.
            raise ValueError("el archivo MPP no contiene tareas importables")

        return result
    finally:
        Path(tmp_path).unlink(missing_ok=True)
