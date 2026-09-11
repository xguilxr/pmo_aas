#!/usr/bin/env python3
"""FASE-6 del revamp v2, commit 5 (US-E) — fusiona actores duplicados dentro
de la misma organización, después de la migración de DEC-038 (D1).

## Qué problema mira

Antes de la migración `20260911_0116` (`uq_actors_tenant_email` →
`uq_actors_org_email`), la unicidad de un actor era por tenant. Si el mismo
correo ya estaba en dos organizaciones del mismo tenant, la migración falla
al crear el nuevo constraint — ese caso lo lista
`scripts/diagnostico_actores_por_org.py` antes de correrla.

Este script resuelve el caso que queda **dentro** de la nueva regla: dos
filas de `actors` con el mismo `(tenant_id, organization_id, email)` — la
migración ya no puede producirlas, pero datos cargados antes de ella (o
importados por nombre, sin correo, y luego editados) pueden dejarlas.

## Qué hace

Para cada grupo `(tenant_id, organization_id, email)` con más de un actor
activo:

1. Conserva el que tenga más `project_participations` con `status = 'activa'`
   (empate: el más antiguo, por `created_at`).
2. Reasigna las `project_participations` de los demás al que se conserva.
3. Marca los demás `is_active = False`. **No los borra** — es una fusión,
   no una limpieza: si la decisión fue la equivocada, se revierte a mano
   reactivando y reasignando de vuelta.

## Por qué `--dry-run` es el default

Es un `UPDATE` masivo sobre datos de clientes. `--dry-run` (default)
imprime qué haría sin tocar nada; `--apply` lo ejecuta en una transacción.
`scripts/guard_irreversible.py` bloquea que Claude Code lo corra con
`--apply` — lo corre el owner, a mano, después de revisar la salida de
`--dry-run` en el PR.

Uso:

    DATABASE_URL=postgresql://... python scripts/fusionar_actores_duplicados.py
    DATABASE_URL=postgresql://... python scripts/fusionar_actores_duplicados.py --tenant <slug>
    DATABASE_URL=postgresql://... python scripts/fusionar_actores_duplicados.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print(
        "Falta sqlalchemy en este entorno. Corre con el venv de apps/api:\n"
        "  cd apps/api && pip install -r requirements.txt\n"
        "  cd .. && DATABASE_URL=... python scripts/fusionar_actores_duplicados.py",
        file=sys.stderr,
    )
    sys.exit(1)

# Agrupa por (tenant, organización, correo) — la regla de DEC-038 — y cuenta
# participaciones activas de cada actor para decidir cuál sobrevive.
SQL_GRUPOS = text(
    """
    SELECT
        a.tenant_id,
        tn.slug AS tenant_slug,
        a.organization_id,
        org.name AS organization_name,
        lower(trim(a.email)) AS email_norm,
        a.id AS actor_id,
        a.name AS actor_name,
        a.created_at,
        (
            SELECT count(*)
            FROM project_participations pp
            WHERE pp.actor_id = a.id AND pp.status = 'activa'
        ) AS n_participaciones_activas
    FROM actors a
    JOIN tenants tn ON tn.id = a.tenant_id
    LEFT JOIN organizations org ON org.id = a.organization_id
    WHERE a.email IS NOT NULL AND trim(a.email) <> ''
      AND a.deleted_at IS NULL
      AND a.is_active = true
      AND (:tenant_slug IS NULL OR tn.slug = :tenant_slug)
    """
)


def _agrupar(rows: list) -> dict[tuple, list]:
    grupos: dict[tuple, list] = {}
    for r in rows:
        clave = (r["tenant_id"], r["organization_id"], r["email_norm"])
        grupos.setdefault(clave, []).append(r)
    return {k: v for k, v in grupos.items() if len(v) > 1}


def _elegir_sobreviviente(actores: list) -> dict:
    """Más participaciones activas gana; empate, el más antiguo."""
    return sorted(
        actores,
        key=lambda a: (-a["n_participaciones_activas"], a["created_at"]),
    )[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default=None, help="Filtra por slug de un solo tenant.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica la fusión. Sin esto, solo imprime qué haría (default).",
    )
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Falta DATABASE_URL en el entorno.", file=sys.stderr)
        return 1

    engine = create_engine(database_url)
    with engine.connect() as conn:
        rows = conn.execute(SQL_GRUPOS, {"tenant_slug": args.tenant}).mappings().all()

    grupos = _agrupar(rows)
    if not grupos:
        print("Sin actores duplicados dentro de la misma organización.")
        return 0

    plan: list[tuple[str, str, str, list[str]]] = []
    for (tenant_id, organization_id, email), actores in grupos.items():
        sobreviviente = _elegir_sobreviviente(actores)
        perdedores = [a for a in actores if a["actor_id"] != sobreviviente["actor_id"]]
        plan.append((tenant_id, sobreviviente["actor_id"], email, [p["actor_id"] for p in perdedores]))
        org_label = actores[0]["organization_name"] or "sin_organización"
        print(
            f"[{actores[0]['tenant_slug']}] {email} en «{org_label}»: "
            f"conserva {sobreviviente['actor_name']} ({sobreviviente['actor_id']}, "
            f"{sobreviviente['n_participaciones_activas']} activas) — "
            f"fusiona {len(perdedores)}: "
            + ", ".join(f"{p['actor_name']} ({p['actor_id']})" for p in perdedores)
        )

    total_perdedores = sum(len(perdedores) for _, _, _, perdedores in plan)
    print(f"\n{len(plan)} grupo(s), {total_perdedores} actor(es) a fusionar.")

    if not args.apply:
        print("\n--dry-run (default): nada se tocó. Corre con --apply para ejecutar.")
        return 0

    with engine.begin() as conn:
        for _tenant_id, sobreviviente_id, _email, perdedores in plan:
            for perdedor_id in perdedores:
                conn.execute(
                    text(
                        "UPDATE project_participations SET actor_id = :sobreviviente "
                        "WHERE actor_id = :perdedor"
                    ),
                    {"sobreviviente": sobreviviente_id, "perdedor": perdedor_id},
                )
                conn.execute(
                    text("UPDATE actors SET is_active = false WHERE id = :perdedor"),
                    {"perdedor": perdedor_id},
                )
    print("\nAplicado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
