"""CFG-04 — la gramática de los mensajes de commit está verificada, no descrita.

La auditoría dejó el requisito PARCIAL con una observación que vale la pena
leer entera: **37 de los últimos 40 commits ya cumplían** Conventional Commits,
y no había `commitlint` ni hook. El hábito estaba; el control no. `CLAUDE.md` §4
describe el formato, y una convención descrita es una instrucción — que es
justo lo que MCA FLU-03 dice que no basta.

Esta suite prueba el validador contra casos, no contra el historial: un gate que
solo se puede ejercer haciendo un commit es un gate que nadie prueba, y encima
sus fallos aparecen en el peor momento.

Los casos negativos son los que importan, y están elegidos por lo que de verdad
aparece: el tipo inventado, el asunto de 133 caracteres que no cabe en un
`git log --oneline`, y el cuerpo pegado al asunto sin línea en blanco —que hace
que git trate el bloque entero como asunto y rompe cualquier listado.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(RAIZ / "scripts"))
from check_commits import MAX_ASUNTO, TIPOS, revisar  # noqa: E402


@pytest.mark.parametrize(
    "asunto",
    [
        "feat(api): US-051 — endpoint /exports/minutes (refs #43)",
        "fix(web): BUG-006 — sidebar muestra items admin a usuarios plain",
        "docs(sprint): mueve BUG-006 de INBOX a Bloque 18",
        "chore: limpieza de artefactos",  # sin alcance: el alcance es opcional
        "feat(api,web): US-176 — orden manual del plan",  # multicapa, como el historial
        "feat(api)!: se retira el campo `wbs`",  # ruptura
        "refactor(services/ai): extrae el cliente",  # alcance con barra
    ],
)
def test_acepta_lo_que_el_repositorio_ya_escribe(asunto: str) -> None:
    """Si el gate rechazara el estilo vigente, la respuesta sería desactivarlo.

    Los casos salen del historial real, incluidos los alcances con coma —que
    son como está escrita buena parte de la historia multicapa— y el `!` de
    ruptura, que aún no se usa pero es parte del estándar que el marco nombra.
    """
    assert revisar(asunto) == []


@pytest.mark.parametrize(
    ("mensaje", "esperado"),
    [
        ("workflow: introduce DoD checklist", "no sigue"),
        ("Add files via upload", "no sigue"),
        ("arreglado el bug del sidebar", "no sigue"),
        ("feat(API): US-1 — alcance en mayúsculas", "no sigue"),
        ("feat(api web): US-1 — alcance con espacio", "no sigue"),
        ("feat(api):", "no sigue"),
        ("", "vacío"),
        # 120 caracteres literales, NO `"x" * MAX_ASUNTO`: la primera versión
        # de este caso derivaba su longitud de la constante que debía vigilar,
        # así que subir el máximo a 100.000 lo hacía pasar igual. La mutación
        # sobrevivió y por eso el número está escrito.
        ("feat(api): " + "x" * 120, "máximo es"),
        ("feat(api): asunto\ncuerpo pegado", "línea en blanco"),
    ],
)
def test_rechaza_lo_que_ensucia_el_historial(mensaje: str, esperado: str) -> None:
    motivos = revisar(mensaje)
    assert motivos, f"debería rechazar: {mensaje!r}"
    assert any(esperado in m for m in motivos), motivos


def test_el_cuerpo_bien_separado_pasa() -> None:
    """El caso simétrico del anterior: sin él, el gate podría rechazar todo
    mensaje con cuerpo y nadie lo notaría hasta el primer commit largo.
    """
    assert revisar("fix(api): OPS-01 — registros estructurados\n\nEl porqué, en tres párrafos.\n") == []


def test_no_estorba_a_los_commits_que_genera_git() -> None:
    """`Merge pull request #580 …` lo escribe GitHub, no una persona.

    Rechazarlo pondría en rojo todo PR hecho con «merge commit» y la reacción
    sería desactivar el job.
    """
    assert revisar("Merge pull request #580 from xguilxr/claude/x") == []
    assert revisar('Revert "feat(api): US-1 — algo"') == []


def test_no_exige_mas_que_el_estandar() -> None:
    """El requisito dice Conventional Commits, no la plantilla local.

    `CLAUDE.md` §4 pide además el ID y el `(refs #N)`. Exigirlo aquí bloquearía
    trabajo legítimo —los commits de conformidad referencian `MCS SEG-05` y no
    un issue— y un gate que bloquea trabajo legítimo se desactiva.
    """
    assert revisar("docs(seguridad): SEG-05 — política de divulgación") == []
    assert revisar("chore: sube la versión de ruff") == []


def test_el_maximo_del_asunto_cabe_en_un_listado() -> None:
    """El número, aparte, porque el caso de arriba ya no puede vigilarlo.

    100 es el máximo de `commitlint` por convención y lo que cabe cómodo en un
    `git log --oneline` a 120 columnas. Subirlo es una decisión, no un retoque.
    """
    assert MAX_ASUNTO == 100


def test_los_tipos_son_los_de_claude_md() -> None:
    """Que la lista no se desincronice de la que el repositorio documenta."""
    documentados = {"feat", "fix", "docs", "refactor", "test", "chore", "wip"}
    assert documentados <= set(TIPOS), (
        f"Tipos de `CLAUDE.md` §4 que el validador rechazaría: {documentados - set(TIPOS)}"
    )


def test_el_hook_esta_versionado_y_es_ejecutable() -> None:
    """Un hook en `.git/hooks/` no se versiona y no llega a nadie más.

    Por eso vive en `.githooks/`: activarlo tiene que ser un comando, no un
    procedimiento a copiar del README.
    """
    hook = RAIZ / ".githooks" / "commit-msg"
    assert hook.is_file(), "El hook `commit-msg` desapareció de `.githooks/`."
    assert hook.stat().st_mode & 0o111, (
        "El hook no tiene permiso de ejecución: git lo ignora en silencio, que "
        "es la peor forma de fallar."
    )


def test_el_gate_corre_de_verdad_sobre_un_mensaje() -> None:
    """De extremo a extremo: el script, invocado como lo invoca el hook.

    Prueba lo que las de arriba no pueden —que el archivo se lea, que los
    comentarios de git se descarten y que el código de salida sea el que git
    mira— sin lo cual el hook podría estar roto con la suite en verde.
    """
    guion = RAIZ / "scripts" / "check_commits.py"
    with_temp = Path(subprocess.check_output(["mktemp"], text=True).strip())
    try:
        with_temp.write_text(
            "feat(api): US-1 — algo\n# Please enter the commit message...\n", encoding="utf-8"
        )
        assert subprocess.run([sys.executable, str(guion), "--archivo", str(with_temp)]).returncode == 0

        with_temp.write_text("arreglado el bug\n", encoding="utf-8")
        assert subprocess.run(
            [sys.executable, str(guion), "--archivo", str(with_temp)],
            capture_output=True,
        ).returncode == 1
    finally:
        with_temp.unlink(missing_ok=True)
