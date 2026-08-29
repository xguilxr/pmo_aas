#!/usr/bin/env python3
"""CTX-08 — el estado de la sesión se deriva, no se lee de un documento que envejece.

## El problema que resuelve

`HANDOFF.md` y `SPRINT.md` son lo primero que se lee en cada sesión y son
narrativa escrita a mano. Medido el 2026-08-28: los dos describían el PR #594
como abierto y esperando verificación. Estaba mergeado, y también el #595 y el
#598 — tres merges que ninguno de los dos documentos había visto. Una sesión
que arrancaba ese día empezaba a decidir sobre una premisa falsa, y nada la
contradecía: el sello de los dos decía «vigente».

Ese fallo no se arregla escribiendo mejor. Se arregla no escribiéndolo: la
rama, los commits, las migraciones y la frescura de los documentos ya están en
el repositorio, y derivarlos cuesta menos que mantenerlos sincronizados a mano.

Es el mismo criterio que `proximo_id.py` (MCA CTX-03: el contador se deriva, no
se almacena), aplicado al estado de la ronda en vez de al siguiente ID.

## Qué NO deriva, y por qué

**El propósito de la sesión.** Qué se está intentando y por qué es lo único que
no está en ningún dato del repositorio, y es exactamente lo que `HANDOFF.md`
aporta. Este script no lo reemplaza: le quita el trabajo de repetir lo que git
ya sabe, para que el handoff quede solo con lo que solo una persona puede
escribir.

**El estado de los issues.** Vive en GitHub y necesita red; este script corre
offline y no adivina. `gh issue list` sigue siendo la fuente.

Uso:

    python scripts/estado.py            # bloque de arranque de sesión
    python scripts/estado.py --json     # el mismo estado, para una herramienta
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
GESTION = DOCS / "project-management"

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8", errors="replace")

_RE_US = re.compile(r"\b(US|BUG|ENH)-(\d{3})\b")


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except OSError:
        return ""


def _frontmatter(ruta: Path) -> dict[str, str]:
    if not ruta.is_file():
        return {}
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    if not texto.startswith("---\n"):
        return {}
    cierre = texto.find("\n---", 4)
    if cierre == -1:
        return {}
    campos = {}
    for linea in texto[4:cierre].split("\n"):
        if ":" in linea:
            k, v = linea.split(":", 1)
            campos[k.strip()] = v.strip()
    return campos


def _dias(fecha_iso: str, hoy: date) -> int | None:
    try:
        return (hoy - date.fromisoformat(fecha_iso)).days
    except ValueError:
        return None


def recolectar(hoy: date | None = None) -> dict:
    hoy = hoy or date.today()

    rama = _git("rev-parse", "--abbrev-ref", "HEAD")
    base = "origin/main"
    cuenta = _git("rev-list", "--left-right", "--count", f"{base}...HEAD")
    detras, adelante = [*cuenta.split(), "?", "?"][:2]

    commits = [
        linea
        for linea in _git("log", "--oneline", "-8", "--no-merges").split("\n")
        if linea
    ]
    items_recientes: list[str] = []
    for linea in commits:
        for tipo, num in _RE_US.findall(linea):
            etiqueta = f"{tipo}-{num}"
            if etiqueta not in items_recientes:
                items_recientes.append(etiqueta)

    # Migraciones: la cabeza es el archivo de revisión más alto por nombre,
    # que en este repo lleva fecha y número correlativo (`20260820_0115_*`).
    versiones = sorted((RAIZ / "apps/api/alembic/versions").glob("*.py"))
    cabeza = versiones[-1].stem if versiones else "—"

    # Frescura de los dos documentos que se cargan siempre.
    frescura = []
    for ruta in (GESTION / "HANDOFF.md", GESTION / "SPRINT.md"):
        campos = _frontmatter(ruta)
        rev = campos.get("revisado", "")
        edad = _dias(rev, hoy) if rev else None
        ult_commit = _git("log", "-1", "--format=%ad", "--date=short", "--", str(ruta))
        frescura.append(
            {
                "documento": ruta.relative_to(RAIZ).as_posix(),
                "revisado": rev,
                "edad_dias": edad,
                "ultimo_commit": ult_commit,
                "deriva": bool(rev and ult_commit and ult_commit > rev),
            }
        )

    # Documentos vencidos: mismo criterio que check_docs.py, resumido.
    vencidos = []
    for archivo in sorted(DOCS.rglob("*.md")):
        campos = _frontmatter(archivo)
        if campos.get("estado") in {"archivado", "historico"}:
            continue
        rev, cada = campos.get("revisado", ""), campos.get("revisar_cada", "")
        m = re.match(r"(\d+)d", cada)
        if not (rev and m):
            continue
        try:
            limite = date.fromisoformat(rev) + timedelta(days=int(m.group(1)))
        except ValueError:
            continue
        if limite < hoy:
            vencidos.append(
                {
                    "documento": archivo.relative_to(RAIZ).as_posix(),
                    "retraso_dias": (hoy - limite).days,
                }
            )

    return {
        "fecha": hoy.isoformat(),
        "rama": rama,
        "base": base,
        "adelante_de_base": adelante,
        "detras_de_base": detras,
        "commits_recientes": commits[:5],
        "items_tocados": items_recientes[:8],
        "migracion_cabeza": cabeza,
        "migraciones_total": len(versiones),
        "frescura": frescura,
        "documentos_vencidos": vencidos,
    }


def _texto(e: dict) -> str:
    lineas: list[str] = []
    lineas.append(f"ESTADO · {e['fecha']}")
    lineas.append(
        f"  rama {e['rama']} · {e['adelante_de_base']} adelante / "
        f"{e['detras_de_base']} detrás de {e['base']}"
    )
    lineas.append(
        f"  migraciones {e['migraciones_total']} · cabeza {e['migracion_cabeza']}"
    )
    if e["items_tocados"]:
        lineas.append("  items en los últimos commits: " + ", ".join(e["items_tocados"]))

    avisos = []
    for f in e["frescura"]:
        nombre = Path(f["documento"]).name
        if f["deriva"]:
            avisos.append(
                f"{nombre} cambió el {f['ultimo_commit']} pero declara "
                f"revisado {f['revisado']}"
            )
        elif f["edad_dias"] is not None and f["edad_dias"] > 7:
            avisos.append(f"{nombre} tiene {f['edad_dias']} días")
    if avisos:
        lineas.append("  ⚠ contexto permanente: " + " · ".join(avisos))

    if e["documentos_vencidos"]:
        cuantos = len(e["documentos_vencidos"])
        peor = max(e["documentos_vencidos"], key=lambda d: d["retraso_dias"])
        lineas.append(
            f"  ⚠ {cuantos} documento(s) con revisión vencida "
            f"(el peor: {Path(peor['documento']).name}, "
            f"{peor['retraso_dias']} días)"
        )

    lineas.append("  siguiente ID: python scripts/proximo_id.py")
    lineas.append("  buscar en docs: python scripts/indexar.py buscar \"<términos>\"")
    return "\n".join(lineas)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="salida para herramientas")
    args = ap.parse_args()

    estado = recolectar()
    if args.json:
        print(json.dumps(estado, ensure_ascii=False, indent=1))
    else:
        print(_texto(estado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
