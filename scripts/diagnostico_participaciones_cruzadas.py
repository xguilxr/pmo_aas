#!/usr/bin/env python3
"""US-273 — participaciones activas entre organizaciones distintas.

## Qué problema mira

DEC-044 (BUG-103): un `Actor` con `organization_id` puesto solo participa en
proyectos de esa organización; con `organization_id` nulo es un recurso
global del inquilino y sirve a cualquiera. La API ya no deja crear un cruce,
pero las filas creadas antes siguen ahí: son las que el owner reportó al no
poder retirar un recurso de su organización.

Este script las lista por inquilino y por organización, y —solo con
`--apply`— las desactiva.

## Qué NO toca

- Las participaciones de un actor global: para él ningún proyecto es ajeno.
- Las participaciones ya inactivas: no hay nada que apagar.
- Las de proyectos en fase terminal (`cerrado`, `cancelado`), salvo que se
  pidan con `--incluir-cerrados`. Apagarlas reescribe historia: esa persona
  sí trabajó ahí. Y además no estorban — `delete_actor` (BUG-104) tampoco las
  cuenta al decidir si un recurso se puede retirar. El reporte las lista
  aparte para que la decisión sea visible.
- Los proyectos, los actores y las asignaciones de área. Un cruce se
  desactiva; nada se borra. Si la decisión fue la equivocada, se revierte
  poniendo `is_active = true` en las filas que el reporte nombra.

## Por qué `--dry-run` es el default

Es un `UPDATE` sobre datos de clientes. `--dry-run` (el default) imprime qué
haría sin tocar nada. `--apply` lo ejecuta en una transacción y deja una fila
en `audit_log` por inquilino, con la lista de participaciones apagadas —sin
ella, mañana nadie puede reconstruir qué desapareció ni por qué.

`scripts/guard_irreversible.py` impide que Claude Code lo corra con
`--apply`: lo corre el owner, a mano, después de leer la salida del
`--dry-run`.

Uso:

    DATABASE_URL=postgresql://... python scripts/diagnostico_participaciones_cruzadas.py
    DATABASE_URL=postgresql://... python scripts/diagnostico_participaciones_cruzadas.py --tenant acme
    DATABASE_URL=postgresql://... python scripts/diagnostico_participaciones_cruzadas.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print(
        "Falta sqlalchemy en este entorno. Corre con el venv de apps/api:\n"
        "  cd apps/api && pip install -r requirements.txt\n"
        "  cd .. && DATABASE_URL=... python scripts/diagnostico_participaciones_cruzadas.py",
        file=sys.stderr,
    )
    sys.exit(1)

#: `IS DISTINCT FROM` y no `!=`: con un nulo de un lado, `!=` devuelve nulo y
#: la fila se cae del resultado. El actor global ya está excluido por el
#: `IS NOT NULL` de arriba, pero un proyecto sin organización no lo estaría.
SQL = text(
    """
    SELECT
        t.slug                AS tenant_slug,
        pp.id                 AS participation_id,
        a.id                  AS actor_id,
        a.name                AS actor_name,
        orga.name             AS actor_org,
        p.folio               AS folio,
        p.name                AS project_name,
        p.phase               AS phase,
        orgp.name             AS project_org
    FROM project_participations pp
    JOIN actors a       ON a.id = pp.actor_id
    JOIN projects p     ON p.id = pp.project_id
    JOIN tenants t      ON t.id = pp.tenant_id
    LEFT JOIN organizations orga ON orga.id = a.organization_id
    LEFT JOIN organizations orgp ON orgp.id = p.organization_id
    WHERE pp.is_active = true
      AND a.deleted_at IS NULL
      AND p.deleted_at IS NULL
      AND a.organization_id IS NOT NULL
      AND p.organization_id IS DISTINCT FROM a.organization_id
      AND (:tenant IS NULL OR t.slug = :tenant)
    ORDER BY t.slug, orga.name, a.name, p.name
    """
)

#: Las mismas dos de `app.dominio.proyecto.FASES_TERMINALES`. Se repiten aquí
#: porque el script corre con `sqlalchemy` pelado, sin la aplicación cargada;
#: si se agrega una tercera fase terminal, esta lista se queda corta y el
#: script apagaría historia. El trinquete que las ata vive en
#: `tests/test_us273_participaciones_cruzadas.py`.
FASES_TERMINALES = ("cerrado", "cancelado")


def partir_por_fase(filas: list[dict]) -> tuple[list[dict], list[dict]]:
    """(en curso, cerradas). La segunda no se toca sin `--incluir-cerrados`."""
    en_curso = [f for f in filas if f["phase"] not in FASES_TERMINALES]
    cerradas = [f for f in filas if f["phase"] in FASES_TERMINALES]
    return en_curso, cerradas


def agrupar(filas: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """Las filas por (inquilino, organización del actor).

    El corte es por la organización **del actor**, no la del proyecto: quien
    lee este reporte está intentando limpiar su catálogo de recursos, y lo que
    necesita saber es a cuántos de los suyos les sobra una asignación.
    """
    fuera: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for fila in filas:
        clave = (fila["tenant_slug"], fila["actor_org"] or "sin organización")
        fuera[clave].append(fila)
    return dict(fuera)


def formatear(grupos: dict[tuple[str, str], list[dict]]) -> list[str]:
    """El reporte en líneas. Se devuelve en vez de imprimirse para poder
    comprobarlo sin una base de datos delante."""
    lineas: list[str] = []
    for (inquilino, organizacion), filas in sorted(grupos.items()):
        actores = {f["actor_id"] for f in filas}
        lineas.append(
            f"[{inquilino}] {organizacion}: {len(filas)} participación(es) "
            f"cruzada(s) en {len(actores)} recurso(s)"
        )
        for f in filas:
            lineas.append(
                f"    {f['actor_name']:<28} → {f['folio']} {f['project_name']} "
                f"({f['project_org'] or 'sin organización'}, {f['phase']})"
            )
    return lineas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default=None, help="Slug del inquilino.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Desactiva las participaciones cruzadas. Sin esto no se toca nada.",
    )
    parser.add_argument(
        "--incluir-cerrados",
        action="store_true",
        help=(
            "Incluye las de proyectos cerrados o cancelados. Por default se "
            "listan aparte y no se tocan: apagarlas reescribe historia."
        ),
    )
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Falta DATABASE_URL en el entorno.", file=sys.stderr)
        return 1

    engine = create_engine(database_url)
    with engine.connect() as conn:
        filas = [
            dict(r) for r in conn.execute(SQL, {"tenant": args.tenant}).mappings().all()
        ]

    if not filas:
        print("Sin participaciones cruzadas. Nada que limpiar.")
        return 0

    en_curso, cerradas = partir_por_fase(filas)
    alcance = filas if args.incluir_cerrados else en_curso

    if cerradas:
        print(
            f"Aparte: {len(cerradas)} participación(es) en proyectos cerrados o "
            "cancelados."
        )
        for linea in formatear(agrupar(cerradas)):
            print(f"  {linea}")
        print(
            "  "
            + (
                "Incluidas en el alcance por --incluir-cerrados."
                if args.incluir_cerrados
                else "No se tocan: esa persona sí trabajó ahí. Usá "
                "--incluir-cerrados si querés apagarlas igual."
            )
        )
        print()

    if not alcance:
        print("No queda nada en el alcance. Nada que limpiar.")
        return 0

    grupos = agrupar(alcance)
    for linea in formatear(grupos):
        print(linea)
    print(
        f"\nTotal en el alcance: {len(alcance)} participación(es) en "
        f"{len(grupos)} organización(es)."
    )

    if not args.apply:
        print("\n--dry-run (default): no se tocó nada. Repetí con --apply.")
        return 0

    por_inquilino: dict[str, list[dict]] = defaultdict(list)
    for fila in alcance:
        por_inquilino[fila["tenant_slug"]].append(fila)

    with engine.begin() as conn:
        res = conn.execute(
            text(
                # `is_primary` también: `derived_assignment.py` ordena por
                # `is_primary.desc(), is_active.desc()` sin filtrar
                # `is_active`, así que una cruzada apagada que siguiera siendo
                # primary le ganaría a la participación legítima y la limpieza
                # no cambiaría nada de lo que el usuario ve.
                "UPDATE project_participations "
                "SET is_active = false, is_primary = false "
                "WHERE id = ANY(:ids)"
            ),
            {"ids": [f["participation_id"] for f in alcance]},
        )
        for inquilino, suyas in por_inquilino.items():
            conn.execute(
                text(
                    "INSERT INTO audit_log "
                    "(tenant_id, actor_type, action, module, entity_type, details) "
                    "SELECT id, 'humano', 'participacion.limpieza_cruzada', "
                    "'actors', 'tenant', CAST(:details AS json) "
                    "FROM tenants WHERE slug = :slug"
                ),
                {
                    "slug": inquilino,
                    "details": json.dumps(
                        {
                            "origen": "scripts/diagnostico_participaciones_cruzadas.py",
                            "regla": "DEC-044",
                            "desactivadas": [
                                {
                                    "participation_id": str(f["participation_id"]),
                                    "actor_id": str(f["actor_id"]),
                                    "actor": f["actor_name"],
                                    "organizacion_del_actor": f["actor_org"],
                                    "proyecto": f"{f['folio']} {f['project_name']}",
                                    "organizacion_del_proyecto": f["project_org"],
                                }
                                for f in suyas
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            )
    print(f"\nAplicado: {res.rowcount} participación(es) desactivada(s).")
    print("Queda registrado en audit_log como `participacion.limpieza_cruzada`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
