#!/usr/bin/env python3
"""Verificación automática del presupuesto de contexto permanente.

Cierra MCA CTX-05 («el presupuesto DEBE verificarse de forma automática») y
FLU-03 («lo que deba ocurrir siempre DEBE automatizarse; NO DEBE confiarse a
una instrucción»).

Motivo, de la auditoría MCA del 2026-08-03: `CLAUDE.md` §6 y §12 declaran dos
veces que `SPRINT.md` «nunca debe pasar de ~250 líneas» y lo llaman *regla
dura*. Estaba en 521. Un control confiado a que alguien se acuerde no es un
control (MCA-CORE §6.1).

Los umbrales viven en `conformidad.yaml`, no aquí (CTX-06: un hecho reside en
un solo artefacto).

Uso:
    python scripts/check_contexto.py            # falla si se supera un techo
    python scripts/check_contexto.py --informe  # solo mide, nunca falla
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent

# La consola de Windows usa cp1252 por omisión y destroza los acentos de este
# informe. En CI (Linux, UTF-8) es inocuo.
for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8", errors="replace")


def _chars(ruta: Path) -> int:
    """Caracteres, no bytes: es lo que correlaciona con tokens."""
    if not ruta.is_file():
        return 0
    return len(ruta.read_text(encoding="utf-8", errors="replace"))


def _descripciones_de_skills() -> int:
    """Solo el frontmatter `description` entra al contexto permanente.

    El cuerpo de una skill se carga cuando se invoca, no siempre.
    """
    total = 0
    for skill in sorted((RAIZ / ".claude" / "skills").glob("*/SKILL.md")):
        texto = skill.read_text(encoding="utf-8", errors="replace")
        if not texto.startswith("---"):
            continue
        cierre = texto.find("\n---", 3)
        if cierre == -1:
            continue
        frontmatter = yaml.safe_load(texto[3:cierre]) or {}
        total += len(str(frontmatter.get("description", "")))
    return total


def _epic_mediana() -> tuple[int, str]:
    """`CLAUDE.md` §1.4 obliga a cargar un epic por sesión, no todos.

    La mediana es el representante honesto: la media la inflan dos o tres
    epics grandes que rara vez se tocan.
    """
    epics = sorted((RAIZ / "docs" / "epics").glob("EP*.md"))
    if not epics:
        return 0, "(sin epics)"
    tamanos = sorted(_chars(e) for e in epics)
    return int(statistics.median(tamanos)), f"mediana de {len(epics)}"


def medir_contexto() -> tuple[int, list[tuple[str, int, str]]]:
    """Lo que se carga en toda sesión sin que nadie lo solicite.

    Puntos 1-4 son lectura obligatoria por `CLAUDE.md` §1, así que cuentan
    como contexto permanente conforme a MCA-CORE §3.2 aunque no los cargue
    el arnés.
    """
    epic_chars, epic_nota = _epic_mediana()
    partidas = [
        ("CLAUDE.md", _chars(RAIZ / "CLAUDE.md"), "carga automática del arnés"),
        (
            "docs/project-management/SPRINT.md",
            _chars(RAIZ / "docs/project-management/SPRINT.md"),
            "CLAUDE.md §1.3",
        ),
        ("docs/epics/EP0XX (uno)", epic_chars, f"CLAUDE.md §1.4 · {epic_nota}"),
        (
            "docs/project-management/HANDOFF.md",
            _chars(RAIZ / "docs/project-management/HANDOFF.md"),
            "CLAUDE.md §1.1",
        ),
        ("catálogo de skills", _descripciones_de_skills(), "solo descriptions"),
    ]
    return sum(p[1] for p in partidas), partidas


def cifras_vivas() -> list[tuple[str, int, str]]:
    """CTX-03: cifras que derivan del contenido real, en contexto permanente.

    Existe porque la propia remediación de la auditoría reintrodujo el fallo:
    al declarar los comandos de verificación se escribió «778 passed» en
    `CLAUDE.md`, que queda obsoleto con el siguiente test. Un fallo que ya se
    cometió una vez no se confía a la disciplina (MCA-CORE §6.1).

    Criterio: una cifra es VIVA si se presenta como estado actual. Es REGISTRO
    —admisible— solo si vive en una **viñeta de changelog fechada**, porque
    entonces es un asiento histórico y no envejece. Los límites declarados
    (250 líneas, 10 archivos) no derivan del contenido y no cuentan.

    La primera versión de esta función buscaba una fecha en las 25 líneas
    previas, y eso amnistiaba toda la tabla de CLAUDE.md §0.3 —cuyo encabezado
    lleva fecha—, que es justo donde el fallo había ocurrido. Un check con el
    punto ciego encima del problema no sirve. Ahora:

      * una fila de tabla nunca es registro: las tablas se leen como criterio
      * fuera de tablas, hay que encontrar el inicio de la viñeta que la
        contiene, y esa viñeta debe llevar la fecha
    """
    sospecha = re.compile(
        r"\b\d+\s*(passed|failed|skipped)\b"
        r"|\(\s*\d+\s+archivos?\s*\)"
        r"|\b\d+\s+(tablas|endpoints|migraciones|skills|epics)\b",
        re.I,
    )
    fecha = re.compile(r"20\d\d-\d\d-\d\d")
    encabezado = re.compile(r"^#{1,3} ")
    vineta = re.compile(r"^\s*[-*+] ")
    hallazgos: list[tuple[str, int, str]] = []

    for rel in (
        "CLAUDE.md",
        "docs/project-management/SPRINT.md",
        "docs/project-management/HANDOFF.md",
    ):
        ruta = RAIZ / rel
        if not ruta.is_file():
            continue
        lineas = ruta.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, linea in enumerate(lineas):
            m = sospecha.search(linea)
            if not m:
                continue

            if linea.lstrip().startswith("|"):
                hallazgos.append((rel, i + 1, m.group(0)))
                continue

            # Buscar el inicio de la viñeta que la contiene.
            j, es_registro = i, False
            while j >= 0 and j > i - 25:
                if encabezado.match(lineas[j]) or lineas[j].lstrip().startswith("|"):
                    break
                if vineta.match(lineas[j]):
                    es_registro = bool(fecha.search(lineas[j]))
                    break
                if not lineas[j].strip() and j != i:
                    break  # línea en blanco: fuera de la viñeta
                j -= 1
            if not es_registro:
                hallazgos.append((rel, i + 1, m.group(0)))
    return hallazgos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--informe",
        action="store_true",
        help="mide y reporta, pero devuelve 0 siempre",
    )
    args = parser.parse_args()

    conformidad = yaml.safe_load(
        (RAIZ / "conformidad.yaml").read_text(encoding="utf-8")
    )
    presupuesto = conformidad["presupuesto_contexto"]
    objetivo = presupuesto["permanente_max_chars"]
    techo = presupuesto["permanente_techo_ci_chars"]
    limites = conformidad["limites"]

    total, partidas = medir_contexto()
    fallos: list[str] = []

    print("Contexto permanente — lo que se carga en toda sesión")
    print("-" * 68)
    for nombre, chars, nota in partidas:
        print(f"  {nombre:<40} {chars:>7,}  {nota}")
    print("-" * 68)
    print(f"  {'TOTAL':<40} {total:>7,}  (~{total // 4:,} tokens)")
    print(f"  {'techo que CI hace cumplir':<40} {techo:>7,}")
    print(f"  {'objetivo declarado':<40} {objetivo:>7,}")

    if total > techo:
        fallos.append(
            f"contexto permanente {total:,} > techo {techo:,} "
            f"(+{total - techo:,}). Bajalo, o subí el techo en conformidad.yaml "
            f"con una razón escrita."
        )
    elif total > objetivo:
        print(
            f"\n  aviso: {total - objetivo:,} por encima del objetivo. "
            f"No falla — el techo es el trinquete. Ver docs/conformidad/plan.md "
            f"acciones 5-7."
        )

    # SPRINT.md: la «regla dura» de CLAUDE.md §6 y §12, hasta hoy sin nadie
    # que la ejecutara.
    sprint = RAIZ / "docs/project-management/SPRINT.md"
    lineas = len(sprint.read_text(encoding="utf-8", errors="replace").splitlines())
    objetivo_sprint = limites["sprint_md_max_lineas"]
    techo_sprint = limites["sprint_md_techo_ci_lineas"]

    print(f"\nSPRINT.md: {lineas} líneas (techo {techo_sprint}, objetivo {objetivo_sprint})")
    if lineas > techo_sprint:
        fallos.append(
            f"SPRINT.md {lineas} líneas > techo {techo_sprint}. "
            f"Ejecutá /handoff para archivar a SPRINT-DONE-HISTORY.md."
        )
    elif lineas > objetivo_sprint:
        print(
            f"  aviso: {lineas - objetivo_sprint} líneas por encima del objetivo."
        )

    # CTX-03 — cifras vivas en el contexto permanente.
    vivas = cifras_vivas()
    print(f"\nCifras vivas (CTX-03): {len(vivas)}")
    for rel, linea, txt in vivas:
        print(f"  {rel}:{linea}  «{txt}»")
    if vivas:
        fallos.append(
            f"{len(vivas)} cifra(s) que derivan del contenido real en el contexto "
            f"permanente. El criterio va en CLAUDE.md; la medición fechada, en "
            f"conformidad.yaml -> mediciones."
        )

    if fallos and not args.informe:
        print("\nFALLA:", file=sys.stderr)
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("\nOK" if not fallos else "\nOK (modo informe; había fallos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
