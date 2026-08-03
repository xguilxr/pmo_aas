#!/usr/bin/env python3
"""Deriva el próximo identificador libre (US / BUG / ENH).

Cierra MCA CTX-03: «el contexto permanente NO DEBE contener cifras vivas ni
inventarios que deriven del contenido real».

Hasta el 2026-08-03 el contador vivía como una línea «Próximo libre: …» dentro
de `SPRINT.md`, que se carga en toda sesión. Una cifra viva en el contexto
permanente envejece entre sesiones, y este repositorio ya pagó ese fallo: el
batch del 2026-06-06 eligió ENH-109..112 / BUG-062 contra una base desfasada
y produjo IDs duplicados (los canónicos son ENH-155..158 / BUG-077).

**Por qué no basta `gh issue list`.** Muchos batches se ejecutaron por chat sin
crear issues («0.1 solucionar > documentar»). Medido el 2026-08-03:

    gh issue list        -> US-170, BUG-083, ENH-179
    git log              -> US-193, BUG-091, ENH-202
    SPRINT.md + HISTORY  -> US-193, BUG-091, ENH-202

Derivar solo de GitHub habría devuelto US-171 y colisionado con 23 IDs. Por eso
se unen todas las fuentes y se toma el máximo.

Uso:
    python scripts/proximo_id.py            # próximo libre por prefijo
    python scripts/proximo_id.py --detalle  # además, el máximo de cada fuente
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PREFIJOS = ("US", "BUG", "ENH")
PAT = re.compile(r"\b(US|BUG|ENH)-(\d{3,4})\b")

# Documentos donde viven los IDs de batches ejecutados por chat, sin issue.
DOCS = (
    "docs/project-management/SPRINT.md",
    "docs/project-management/SPRINT-DONE-HISTORY.md",
)

for _f in (sys.stdout, sys.stderr):
    if hasattr(_f, "reconfigure"):
        _f.reconfigure(encoding="utf-8", errors="replace")


def _maximos(texto: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for pref, num in PAT.findall(texto):
        out[pref] = max(out.get(pref, 0), int(num))
    return out


def _de_github() -> tuple[dict[str, int], str | None]:
    """Títulos de issues. Devuelve (máximos, aviso)."""
    try:
        r = subprocess.run(
            ["gh", "issue", "list", "--state", "all", "--limit", "1000", "--json", "title"],
            capture_output=True, timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}, "gh no disponible: no se consultó GitHub"
    if r.returncode != 0:
        return {}, "gh falló (¿sin autenticar o sin red?): no se consultó GitHub"
    return _maximos(r.stdout.decode("utf-8", "replace")), None


def _de_git() -> dict[str, int]:
    r = subprocess.run(["git", "log", "--pretty=%s%n%b"], capture_output=True, cwd=RAIZ)
    return _maximos(r.stdout.decode("utf-8", "replace"))


def _de_docs() -> dict[str, int]:
    txt = ""
    for d in DOCS:
        p = RAIZ / d
        if p.is_file():
            txt += p.read_text(encoding="utf-8", errors="replace")
    for p in (RAIZ / "docs" / "epics").glob("EP*.md"):
        txt += p.read_text(encoding="utf-8", errors="replace")
    return _maximos(txt)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--detalle", action="store_true", help="muestra el máximo por fuente")
    args = ap.parse_args()

    gh, aviso = _de_github()
    fuentes = {"GitHub (issues)": gh, "git log": _de_git(), "SPRINT.md + epics": _de_docs()}

    if aviso:
        print(f"aviso: {aviso}. El resultado puede quedarse corto.", file=sys.stderr)

    if args.detalle:
        print("Máximo por fuente")
        print("-" * 52)
        for nombre, d in fuentes.items():
            detalle = "  ".join(f"{p}-{d.get(p, 0):03d}" for p in PREFIJOS)
            print(f"  {nombre:<20} {detalle}")
        print("-" * 52)

    print("Próximo libre")
    for p in PREFIJOS:
        usado = max((d.get(p, 0) for d in fuentes.values()), default=0)
        print(f"  {p}-{usado + 1:03d}")

    print(
        "\nDerivado, no almacenado (MCA CTX-03). Si vas a elegir IDs, corré esto\n"
        "contra `origin/main` actualizado: `git fetch origin main`.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
