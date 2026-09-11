#!/usr/bin/env python3
"""Diagnóstico (solo lectura) — por qué `DELETE /actors/{id}` rechaza a un
actor con "participaciones activas en proyectos" cuando en la UI no se ve
ninguna.

El check de `areas.py::delete_actor` cuenta CUALQUIER
`project_participations.is_active = true` del actor, sin filtrar por
organización ni por si el proyecto está cerrado/archivado. Este script
lista exactamente cuáles son, con su organización y fase, para saber si
el bloqueo es legítimo o un dato viejo (proyecto cerrado, u otra
organización).

Uso:

    DATABASE_URL=postgresql://... python scripts/diagnostico_participaciones_actor.py --actor <uuid>
    DATABASE_URL=postgresql://... python scripts/diagnostico_participaciones_actor.py --email correo@ejemplo.com
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
        "  cd .. && DATABASE_URL=... python scripts/diagnostico_participaciones_actor.py",
        file=sys.stderr,
    )
    sys.exit(1)

SQL = text(
    """
    SELECT
        pp.id AS participation_id,
        pp.is_active,
        pp.status,
        p.folio,
        p.name AS project_name,
        p.phase,
        org.name AS organization_name,
        a.id AS actor_id,
        a.name AS actor_name,
        a.organization_id AS actor_organization_id
    FROM project_participations pp
    JOIN projects p ON p.id = pp.project_id
    JOIN actors a ON a.id = pp.actor_id
    LEFT JOIN organizations org ON org.id = p.organization_id
    WHERE pp.is_active = true
      AND (:actor_id IS NULL OR a.id = :actor_id)
      AND (:email IS NULL OR lower(a.email) = lower(:email))
    ORDER BY p.phase, org.name, p.name
    """
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", default=None, help="UUID del actor.")
    parser.add_argument("--email", default=None, help="Correo del actor.")
    args = parser.parse_args()
    if not args.actor and not args.email:
        print("Pasa --actor <uuid> o --email <correo>.", file=sys.stderr)
        return 1

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Falta DATABASE_URL en el entorno.", file=sys.stderr)
        return 1

    engine = create_engine(database_url)
    with engine.connect() as conn:
        rows = conn.execute(SQL, {"actor_id": args.actor, "email": args.email}).mappings().all()

    if not rows:
        print("Sin participaciones activas — el borrado debería pasar. Si sigue")
        print("rechazando, revisa que el actor_id sea el correcto (puede haber")
        print("un duplicado con el mismo nombre en otra organización, DEC-038).")
        return 0

    print(f"{'actor':<28} {'organización del proyecto':<26} {'proyecto':<32} fase")
    for r in rows:
        mismatch = (
            "  <-- proyecto de OTRA organización que la del actor"
            if r["organization_name"] and str(r["actor_organization_id"]) not in (None, "")
            else ""
        )
        print(
            f"{r['actor_name']:<28} {r['organization_name'] or 'sin organización':<26} "
            f"{r['project_name']:<32} {r['phase']}{mismatch}"
        )
    print(f"\n{len(rows)} participación(es) activa(s) bloqueando el borrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
