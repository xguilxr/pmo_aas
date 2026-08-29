"""DOC-06 — todo cambio de código verifica su impacto documental, o lo declara.

> «La integración de un cambio DEBE verificar el impacto documental. La
> ausencia de impacto DEBE declararse explícitamente y quedar registrada.»

`CLAUDE.md` §0.2 ya lo pide, en palabras: «si un commit cambia comportamiento,
schema o endpoints descritos en una epic, actualiza la epic en el mismo
bloque». Es una instrucción, no un control — y este repositorio tiene un
principio para exactamente ese caso (MCA FLU-03): «lo que deba ocurrir siempre
DEBE automatizarse; NO DEBE confiarse a una instrucción».

La auditoría del 2026-08-28 lo confirmó sin ambigüedad: `mapa-backend.md`,
`mapa-frontend.md`, ocho epics y `DECISIONS.md` llevaban entre 1 y 15 días de
diferencia entre su último commit real y su `revisado` declarado — cambiaron y
nadie los volvió a sellar. `HANDOFF.md` y `SPRINT.md` describieron un PR como
abierto durante nueve días después de mergearse. El patrón se repite porque
recordar «actualiza la epic» es exactamente el tipo de paso que se salta bajo
presión, y nada lo notaba.

## Qué hace

Toma el rango de commits de un PR (o cualquier rango explícito), mira qué
archivos cambiaron, y los cruza contra `ZONAS` — un mapa de directorios y
archivos de código a la epic que los describe, tomado de las tablas de
`mapa-backend.md` / `mapa-frontend.md` y de la tabla «Anclas concretas» de la
skill `cerrar-item`. Si el rango tocó una zona y **no** tocó el doc de la epic
correspondiente, lo informa.

**No falla nunca.** Mismo argumento que `DOC-07` en `check_docs.py`: esto exige
juicio —¿el cambio de verdad describe comportamiento nuevo, o fue un refactor
interno que §0.2 exime explícitamente?— y un gate que se pone rojo por algo que
a veces está bien equivocarse termina desactivado en una semana. Automatiza la
mitad mecánica (detectar la zona tocada) y deja la mitad de juicio (decidir si
hacía falta) donde siempre estuvo: en quien cierra el cambio.

Los commits `refactor`/`chore`/`style`/`test` puros —los que §7 ya exime de
tocar una epic— no generan aviso.

## Qué NO hace, y por qué

**No es exhaustivo.** `ZONAS` es un punto de partida, no un catálogo completo:
cubre las áreas de mayor superficie de cada epic, no cada archivo. Una ruta sin
mapear no genera falso positivo —simplemente no se vigila todavía—, así que el
fallo seguro es de menos cobertura, nunca de una alarma que no aplica.
Ampliarla es mantenimiento esperado, igual que `DB-CHANGES.md` es un registro
que crece con cada epic que toca schema.

**No declara «sin impacto» por ti.** La segunda mitad del requisito —que la
ausencia de impacto quede registrada— la satisface el propio commit: un
`refactor(api): ...` ya es la declaración explícita de que no hay impacto de
producto, y por eso queda exento sin más trámite.

Uso:

    python scripts/check_impacto_documental.py                     # origin/main...HEAD
    python scripts/check_impacto_documental.py --rango a...b       # rango explícito
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8", errors="replace")

#: Zona de código → epic(s) que la describen. Prefijo más largo gana, así que
#: un archivo específico puede afinar lo que dice un directorio más general.
#: Fuente: `docs/architecture/mapa-{backend,frontend}.md` y la tabla «Anclas
#: concretas» de la skill `cerrar-item`. Ampliar aquí cuando una epic gane
#: superficie nueva — un directorio sin entrada simplemente no se vigila.
ZONAS: dict[str, tuple[str, ...]] = {
    # backend — modelos
    "apps/api/app/models/user.py": ("EP001",),
    "apps/api/app/models/auth.py": ("EP001",),
    "apps/api/app/models/user_scope_assignment.py": ("EP001",),
    "apps/api/app/models/user_tenant_membership.py": ("EP001",),
    "apps/api/app/models/organization.py": ("EP002",),
    "apps/api/app/models/project_request.py": ("EP003",),
    "apps/api/app/models/project_charter.py": ("EP003",),
    "apps/api/app/models/project.py": ("EP005",),
    "apps/api/app/models/plan_baseline.py": ("EP005",),
    "apps/api/app/models/task.py": ("EP005",),
    "apps/api/app/models/modules.py": ("EP006", "EP019"),
    "apps/api/app/models/area.py": ("EP017",),
    "apps/api/app/models/project_participation.py": ("EP017",),
    "apps/api/app/models/project_role.py": ("EP017",),
    "apps/api/app/models/project_artifact.py": ("EP018",),
    "apps/api/app/models/metric_snapshot.py": ("EP004",),
    # backend — servicios (directorio: cualquier archivo dentro cuenta)
    "apps/api/app/services/ai/catalogo.py": ("EP021",),
    "apps/api/app/services/ai/": ("EP008",),
    "apps/api/app/services/msproject/": ("EP009",),
    "apps/api/app/services/project_health.py": ("EP005",),
    "apps/api/app/services/capacity.py": ("EP017",),
    # backend — endpoints
    "apps/api/app/api/v1/endpoints/auth.py": ("EP001",),
    "apps/api/app/api/v1/endpoints/dashboard.py": ("EP004",),
    "apps/api/app/api/v1/endpoints/organizations.py": ("EP002",),
    "apps/api/app/api/v1/endpoints/project_requests.py": ("EP003",),
    "apps/api/app/api/v1/endpoints/projects.py": ("EP005",),
    "apps/api/app/api/v1/endpoints/project_charters.py": ("EP003",),
    "apps/api/app/api/v1/endpoints/modules.py": ("EP006",),
    "apps/api/app/api/v1/endpoints/admin_panel.py": ("EP007",),
    "apps/api/app/api/v1/endpoints/admin_users.py": ("EP007",),
    "apps/api/app/api/v1/endpoints/admin_ai.py": ("EP008",),
    "apps/api/app/api/v1/endpoints/superadmin_ai.py": ("EP008",),
    "apps/api/app/api/v1/endpoints/ai.py": ("EP008",),
    "apps/api/app/api/v1/endpoints/ai_context.py": ("EP008",),
    "apps/api/app/api/v1/endpoints/assistant.py": ("EP008",),
    "apps/api/app/api/v1/endpoints/ai_plantillas.py": ("EP021",),
    "apps/api/app/api/v1/endpoints/superadmin.py": ("EP010",),
    "apps/api/app/api/v1/endpoints/superadmin_panel.py": ("EP010",),
    "apps/api/app/api/v1/endpoints/areas.py": ("EP017",),
    "apps/api/app/api/v1/endpoints/project_directory.py": ("EP017",),
    "apps/api/app/api/v1/endpoints/capacity.py": ("EP017",),
    "apps/api/app/api/v1/endpoints/project_artifacts.py": ("EP018",),
    "apps/api/app/api/v1/endpoints/change_approvals.py": ("EP019",),
    "apps/api/app/api/v1/endpoints/risk_actions.py": ("EP006",),
    "apps/api/app/api/v1/endpoints/reports.py": ("EP020",),
    "apps/api/app/api/v1/endpoints/report_templates.py": ("EP020",),
    "apps/api/app/api/v1/endpoints/report_builder.py": ("EP020",),
    "apps/api/app/api/v1/endpoints/report_builder_chat.py": ("EP020",),
    "apps/api/app/api/v1/endpoints/scheduled_reports.py": ("EP020",),
    "apps/api/app/api/v1/endpoints/tasks.py": ("EP005",),
    # backend — migraciones: casi siempre acompañan una epic con schema nuevo
    "apps/api/alembic/versions/": ("DB-CHANGES",),
    # frontend — rutas (grupo `(app)`)
    "apps/web/app/(app)/dashboard": ("EP004",),
    "apps/web/app/(app)/pmo/requests": ("EP003",),
    "apps/web/app/(app)/pmo/organizations": ("EP002",),
    "apps/web/app/(app)/pmo/programs": ("EP002",),
    "apps/web/app/(app)/pmo/projects": ("EP005",),
    "apps/web/app/(app)/pmo/board": ("EP019",),
    "apps/web/app/(app)/pmo/resources": ("EP017",),
    "apps/web/app/(app)/pmo/reports": ("EP020",),
    "apps/web/app/(app)/pmo/imports": ("EP017",),
    "apps/web/app/(app)/admin": ("EP007",),
    "apps/web/app/(app)/superadmin": ("EP010",),
}

#: `DB-CHANGES` no es una epic — es el registro de schema por epic
#: (`docs/epics/DB-CHANGES.md`). Se trata como una epic más para el cruce:
#: tocar una migración sin tocar ese registro es la misma clase de olvido.
_DOC_POR_CLAVE = {
    "DB-CHANGES": "docs/epics/DB-CHANGES.md",
}


def _doc_de_epic(clave: str) -> str:
    return _DOC_POR_CLAVE.get(clave, f"docs/epics/{clave}-")


#: Tipos que §7 ya exime de tocar una epic: no cambian comportamiento de
#: producto. Mismos tipos que `check_commits.py::TIPOS`, el subconjunto que
#: aquí importa — duplicado a propósito, son scripts independientes.
_TIPOS_EXENTOS = {"refactor", "chore", "style", "test"}
_RE_ASUNTO = re.compile(r"^(?P<tipo>[a-z]+)(?:\([^)]*\))?!?:")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=RAIZ, capture_output=True, text=True, check=False
    ).stdout


def _archivos_cambiados(rango: str) -> list[str]:
    salida = _git("diff", "--name-only", rango)
    return [linea.strip() for linea in salida.splitlines() if linea.strip()]


def _solo_commits_exentos(rango: str) -> bool:
    asuntos = [l for l in _git("log", "--format=%s", rango).splitlines() if l.strip()]
    if not asuntos:
        return False
    for asunto in asuntos:
        if asunto.startswith(("Merge ", "Revert ")):
            continue
        m = _RE_ASUNTO.match(asunto)
        if not m or m["tipo"] not in _TIPOS_EXENTOS:
            return False
    return True


def _zona_de(ruta: str) -> tuple[str, ...]:
    mejor: tuple[str, ...] = ()
    mejor_largo = -1
    for prefijo, epics in ZONAS.items():
        if ruta.startswith(prefijo) and len(prefijo) > mejor_largo:
            mejor, mejor_largo = epics, len(prefijo)
    return mejor


def evaluar(rango: str) -> dict[str, list[str]]:
    """Epic → archivos que la tocaron, para las epics sin su doc en el mismo rango."""
    cambiados = _archivos_cambiados(rango)
    if not cambiados:
        return {}

    tocadas: dict[str, list[str]] = {}
    for ruta in cambiados:
        for epic in _zona_de(ruta):
            tocadas.setdefault(epic, []).append(ruta)

    docs_tocados = {r for r in cambiados if r.startswith("docs/")}
    return {
        epic: archivos
        for epic, archivos in tocadas.items()
        if not any(d.startswith(_doc_de_epic(epic)) for d in docs_tocados)
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--rango", default="origin/main...HEAD", help="rango de git diff (triple punto)"
    )
    args = ap.parse_args()

    if _solo_commits_exentos(args.rango):
        print("OK — el rango son solo commits refactor/chore/style/test (§7 los exime)")
        return 0

    faltantes = evaluar(args.rango)
    if not faltantes:
        print("OK — ninguna zona mapeada quedó sin su doc en el mismo rango")
        return 0

    print(f"DOC-06 — {len(faltantes)} epic(s)/registro(s) con código tocado y su doc no:\n")
    for clave, archivos in sorted(faltantes.items()):
        doc = _doc_de_epic(clave)
        print(f"  {clave} — no se tocó {doc}*")
        for ruta in archivos[:5]:
            print(f"    · {ruta}")
        if len(archivos) > 5:
            print(f"    · … y {len(archivos) - 5} más")
    print(
        "\nSi el cambio de verdad no afecta el doc, es una llamada de juicio — "
        "no un error. Ver CLAUDE.md §0.2. (Informativo: DOC-06 no falla el CI.)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
