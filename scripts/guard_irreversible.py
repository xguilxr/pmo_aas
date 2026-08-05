#!/usr/bin/env python3
"""Exige confirmación humana ante acciones irreversibles.

Cierra MCA AUT-01: «toda acción irreversible DEBE requerir confirmación humana
explícita».

Se ejecuta como hook `PreToolUse` sobre Bash (ver `.claude/settings.json`). Lee
el JSON del hook por stdin y devuelve una decisión de permiso.

**Por qué un hook y no solo `permissions`.** Las reglas de `permissions` hacen
coincidencia por PREFIJO: `Bash(git push --force*)` no atrapa
`git push origin main --force`, que es exactamente igual de destructivo. Este
guard mira el comando completo con expresiones regulares.

Y por qué no basta escribirlo en CLAUDE.md: MCA-CORE §6.1 — «un control que
existe pero no se ejecuta automáticamente es PARCIAL. La disciplina humana no
es un control».

**Por qué lo destructivo se deniega en vez de preguntarse (2026-08-04).** Al
verificar el guard en vivo salió que `ask` no frena nada si la sesión corre con
los permisos relajados: `alembic downgrade --help` y `git branch -D` se
ejecutaron sin diálogo alguno, mientras que un `deny` sí bloqueó. O sea que
`ask` depende de en qué modo abriste la sesión — y eso es disciplina humana,
justo lo que MCA-CORE §6.1 no acepta como control. `deny` sobrevive a cualquier
modo, así que lo irreversible de verdad vive ahí. El precio es que el owner
corre a mano sus migraciones y sus borrados; se pagó a sabiendas.

En `PREGUNTAR` queda solo lo reversible-con-esfuerzo: reescribir historia de una
branch propia, enmendar un commit, cerrar un issue. Si algo de eso se cuela por
un modo permisivo, se deshace.

**Falso positivo conocido.** El guard mira la cadena completa del comando, así
que un `git commit -m "...alembic upgrade..."` se bloquea aunque solo esté
*hablando* de una migración. Pasó al commitear este mismo cambio. La salida es
escribir el mensaje en un archivo y usar `git commit -F`, no relajar el patrón:
distinguir «ejecuta» de «menciona» exigiría analizar el shell, y el precio de
equivocarse hacia el lado permisivo es una base de datos.

Decisiones:
  deny  -> irreversible, o prohibido por CLAUDE.md; lo corre el humano aparte
  ask   -> reversible con esfuerzo; se muestra y se pide confirmación
  (nada) -> el resto sigue el flujo normal de permisos
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

# ── Irreversible o prohibido: se deniega ─────────────────────────────────────
DENEGAR: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bgit\b.*\bpush\b.*(?<!-)--force(?!-with-lease)\b"),
        "CLAUDE.md §8: `git push --force` a secas puede pisar trabajo del owner. "
        "Usá `--force-with-lease`.",
    ),
    (
        re.compile(r"--no-verify\b"),
        "CLAUDE.md §4: no se saltan los hooks. Si uno falla, se arregla la causa.",
    ),
    (
        re.compile(r"\bgit\b.*\bpush\b.*\b(origin\s+)?(HEAD:)?main\b"),
        "CLAUDE.md §8: `main` es productiva y no se pushea directo. Va por branch y PR.",
    ),
    (
        re.compile(r"\balembic\b.*\b(upgrade|downgrade)\b"),
        "Migración de base de datos: altera el schema y puede perder datos. "
        "La corre el owner, que es quien sabe contra qué entorno está apuntando.",
    ),
    (
        re.compile(r"\b(DROP|TRUNCATE)\s+(TABLE|DATABASE|SCHEMA)\b", re.I),
        "Destruye datos sin vuelta atrás. Si de verdad hace falta, lo corre el owner.",
    ),
    (
        re.compile(r"\brm\b\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+"),
        "Borrado recursivo o forzado. Borrá lo que sobre a mano, o pedí ruta por ruta.",
    ),
    (
        re.compile(r"\bgit\b.*\b(reset\s+--hard|clean\s+-[a-z]*f)"),
        "Descarta cambios del árbol de trabajo sin recuperación. "
        "Si el árbol quedó sucio, se revisa qué hay antes de tirarlo.",
    ),
    (
        re.compile(r"\bgit\b.*\bbranch\b.*\s-D\b"),
        "Borra una branch sin comprobar que esté mergeada. Usá `-d`, que sí comprueba.",
    ),
]

# ── Reversible con esfuerzo: se pide confirmación ────────────────────────────
PREGUNTAR: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bgit\b.*\bpush\b.*--force-with-lease\b"),
        "Reescribe historia remota. Confirmá que la branch es tuya y que nadie más la tocó.",
    ),
    (
        re.compile(r"\bgh\b.*\bissue\b.*\bclose\b"),
        "CLAUDE.md: Claude NUNCA cierra un issue. Lo cierra el owner al verificar el fix.",
    ),
    (
        re.compile(r"\bgit\b.*\bcommit\b.*--amend\b"),
        "CLAUDE.md §4: no se hace `--amend` sobre commits ya pusheados.",
    ),
]


def _en_main() -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, timeout=10,
        )
        return r.stdout.decode("utf-8", "replace").strip() == "main"
    except Exception:
        return False


def _responder(decision: str, razon: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": razon,
            }
        },
        sys.stdout,
    )
    sys.stdout.write("\n")


def main() -> int:
    try:
        datos = json.load(sys.stdin)
    except Exception:
        return 0  # sin entrada utilizable: no interferir

    comando = str((datos.get("tool_input") or {}).get("command") or "")
    if not comando:
        return 0

    for patron, razon in DENEGAR:
        if patron.search(comando):
            _responder("deny", f"BLOQUEADO — {razon}")
            return 0

    for patron, razon in PREGUNTAR:
        if patron.search(comando):
            _responder("ask", f"Acción irreversible (MCA AUT-01) — {razon}")
            return 0

    # `git push` PELADO estando en main es push directo a productiva.
    #
    # Solo aplica cuando el comando no nombra un ref: `git push` o
    # `git push origin` empujan la rama actual. `git push origin claude/x` nombra
    # su destino y no es asunto de esta regla — el push a main explícito ya lo
    # atrapa DENEGAR más arriba.
    m = re.search(r"\bgit\b\s+push\b(?P<resto>.*)", comando)
    if m:
        tokens = [t for t in m.group("resto").split() if not t.startswith("-")]
        if len(tokens) <= 1 and _en_main():
            _responder(
                "deny",
                "BLOQUEADO — CLAUDE.md §8: estás en `main`, que es productiva y no se "
                "pushea directo. Creá una branch.",
            )
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
