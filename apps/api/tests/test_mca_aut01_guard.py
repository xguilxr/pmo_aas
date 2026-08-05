"""Trinquete del guard de acciones irreversibles (MCA AUT-01).

El guard vive en `scripts/guard_irreversible.py` y hasta hoy no tenía prueba:
se comprobaba a mano, que es exactamente lo que MCA-CORE §6.1 no acepta como
control. Esta suite fija la decisión esperada por comando.

**Por qué `deny` y no `ask` para lo destructivo.** Verificado en vivo el
2026-08-04: con los permisos de la sesión relajados, un `ask` del hook no abre
diálogo y el comando se ejecuta igual. `deny` sí frena en cualquier modo. Si
alguien mueve una migración o un borrado recursivo de vuelta a `PREGUNTAR`,
esta prueba se pone roja.

Los comandos van en este archivo y no en la línea de órdenes a propósito: el
propio guard bloquea el intento de probarlo desde la terminal.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
GUARD = RAIZ / "scripts" / "guard_irreversible.py"


def _decidir(comando: str) -> str | None:
    """Devuelve la decisión del guard, o None si deja pasar el comando."""
    salida = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps({"tool_input": {"command": comando}}),
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    if not salida:
        return None
    return json.loads(salida)["hookSpecificOutput"]["permissionDecision"]


DENEGADOS = [
    "git push --force origin claude/x",
    "git push origin claude/x --force",  # el orden no lo salva
    "git commit --no-verify -m x",
    "git push origin main",
    "git push origin HEAD:main",
    "alembic upgrade head",
    "cd apps/api && alembic downgrade -1",
    "psql -c 'DROP TABLE projects'",
    "psql -c 'truncate table audit_log'",  # minúsculas también
    "rm -rf apps/web/.next",
    "git reset --hard HEAD~1",
    "git clean -fd",
    "git branch -D claude/x",
]

PREGUNTADOS = [
    "git push --force-with-lease origin claude/x",
    "gh issue close 554",
    "git commit --amend -m x",
]

LIBRES = [
    "pytest -q",
    "git status",
    "git branch -d claude/x",  # `-d` comprueba el merge; no es lo mismo que `-D`
    "gh issue view 554",
    "git push origin claude/mi-rama",
    "rm apps/web/basura.txt",  # borrado simple, sin -r ni -f
]


@pytest.mark.parametrize("comando", DENEGADOS)
def test_lo_irreversible_se_deniega(comando: str) -> None:
    assert _decidir(comando) == "deny", comando


@pytest.mark.parametrize("comando", PREGUNTADOS)
def test_lo_reversible_con_esfuerzo_pregunta(comando: str) -> None:
    assert _decidir(comando) == "ask", comando


@pytest.mark.parametrize("comando", LIBRES)
def test_el_trabajo_normal_no_se_estorba(comando: str) -> None:
    assert _decidir(comando) is None, comando


def test_la_razon_acompana_a_la_decision() -> None:
    """Un bloqueo sin motivo obliga a leer el script para entenderlo."""
    salida = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps({"tool_input": {"command": "rm -rf /"}}),
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    razon = json.loads(salida)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "BLOQUEADO" in razon
    assert len(razon) > 40


def test_entrada_inutilizable_no_interfiere() -> None:
    """Sin comando que inspeccionar, el guard se aparta en vez de romper."""
    for entrada in ["", "{}", '{"tool_input":{}}', "no es json"]:
        proceso = subprocess.run(
            [sys.executable, str(GUARD)],
            input=entrada,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proceso.returncode == 0, entrada
        assert proceso.stdout.strip() == "", entrada
