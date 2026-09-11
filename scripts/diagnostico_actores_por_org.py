#!/usr/bin/env python3
"""FASE-2 del revamp v2, paso 3 — diagnóstico (solo lectura) de actores
duplicados entre organizaciones.

## Qué problema mira

El owner reporta actores que se ven repetidos entre organizaciones "que se
juntaron" en Recursos. Este script no corrige nada: lista, por tenant, los
`actors` cuyo email (normalizado a minúsculas) aparece en más de una
organización, para que la fase 6 (unicidad por organización, decisión D1)
decida cuál copia sobrevive con datos reales delante.

La organización de un actor no es una columna directa: se resuelve por
`area_id` (asignación directa) o, si no tiene, por `team_id -> teams.area_id`.
Un área con `organization_id IS NULL` es global (BUG-061) y no cuenta como
organización propia — se reporta como `sin_organizacion`.

## Por qué no toca datos

La decisión de cuál fila sobrevive depende de D1 (fase 6): unicidad por
organización, con su propia migración. Corregir aquí sería adivinar antes de
que exista la regla.

Uso:

    DATABASE_URL=postgresql://... python scripts/diagnostico_actores_por_org.py
    DATABASE_URL=postgresql://... python scripts/diagnostico_actores_por_org.py --tenant <slug>
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
        "  cd .. && DATABASE_URL=... python scripts/diagnostico_actores_por_org.py",
        file=sys.stderr,
    )
    sys.exit(1)

# Resuelve la organización de un actor por `area_id` directo o, si no tiene,
# por `team_id -> teams.area_id`. `areas.organization_id IS NULL` = área
# global (BUG-061): no identifica organización propia.
SQL = text(
    """
    WITH actor_org AS (
        SELECT
            a.id AS actor_id,
            a.tenant_id,
            a.name AS actor_name,
            lower(trim(a.email)) AS email_norm,
            COALESCE(area_directa.organization_id, area_via_team.organization_id) AS organization_id
        FROM actors a
        LEFT JOIN areas area_directa ON area_directa.id = a.area_id
        LEFT JOIN teams t ON t.id = a.team_id
        LEFT JOIN areas area_via_team ON area_via_team.id = t.area_id
        WHERE a.email IS NOT NULL AND trim(a.email) <> ''
    ),
    duplicados AS (
        SELECT tenant_id, email_norm
        FROM actor_org
        GROUP BY tenant_id, email_norm
        HAVING count(DISTINCT actor_id) > 1
    )
    SELECT
        tn.slug AS tenant_slug,
        ao.email_norm AS email,
        ao.actor_id,
        ao.actor_name,
        ao.organization_id,
        org.name AS organization_name,
        (
            SELECT count(*)
            FROM project_participations pp
            JOIN projects p ON p.id = pp.project_id
            WHERE pp.actor_id = ao.actor_id
              AND p.status NOT IN ('archived', 'cancelled')
        ) AS n_participaciones_activas
    FROM actor_org ao
    JOIN duplicados d ON d.tenant_id = ao.tenant_id AND d.email_norm = ao.email_norm
    JOIN tenants tn ON tn.id = ao.tenant_id
    LEFT JOIN organizations org ON org.id = ao.organization_id
    WHERE (:tenant_slug IS NULL OR tn.slug = :tenant_slug)
    ORDER BY tn.slug, ao.email_norm, ao.actor_id
    """
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant", default=None, help="Filtra por slug de un solo tenant."
    )
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Falta DATABASE_URL en el entorno.", file=sys.stderr)
        return 1

    engine = create_engine(database_url)
    with engine.connect() as conn:
        rows = conn.execute(SQL, {"tenant_slug": args.tenant}).mappings().all()

    if not rows:
        print("Sin actores duplicados entre organizaciones.")
        return 0

    print(
        f"{'tenant':<20} {'email':<32} {'actor_id':<38} {'organización':<28} activas"
    )
    for r in rows:
        org_label = r["organization_name"] or "sin_organizacion"
        print(
            f"{r['tenant_slug']:<20} {r['email']:<32} {r['actor_id']:<38} "
            f"{org_label:<28} {r['n_participaciones_activas']}"
        )
    print(f"\n{len(rows)} filas — {len(set((r['tenant_slug'], r['email']) for r in rows))} email(s) duplicados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
