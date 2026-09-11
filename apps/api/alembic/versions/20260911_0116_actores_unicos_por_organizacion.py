"""FASE-6 del revamp v2 (DEC-038 / D1) — un actor único por organización, no
por tenant.

## El problema que resuelve

`uq_actors_tenant_email` es `(tenant_id, email)`: hoy un correo no puede
existir en dos organizaciones del mismo tenant. El punto 5 del feedback del
owner es explícito al contrario — "si la misma persona participa en otra
organización, se tiene que volver a dar de alta ahí: es un registro nuevo e
independiente, no el mismo recurso compartido entre organizaciones". La
unicidad por tenant se lo impide con un 409 que no debería dispararse.

## Por qué esta migración no fusiona ni borra nada

Cambiar el constraint no crea duplicados por sí solo — los duplicados que ya
existen (la misma persona con filas en dos organizaciones, "porque dos
organizaciones se juntaron", según el owner) siguen siendo filas separadas
hoy mismo, porque el modelo YA tiene `organization_id`; lo único que impedía
tenerlos era el índice único por tenant. Lo que sí puede haber, y esta
migración no toca, son duplicados **dentro de la misma organización**
—mismo `(tenant_id, organization_id, email)` en más de una fila—: si existen,
el `create_unique_constraint` de abajo falla al correr, y por diseño: es la
señal de que hay que resolverlos primero (`scripts/diagnostico_actores_por_org.py`,
US-251, y su fusión en `scripts/fusionar_actores_duplicados.py`, US-E de esta
fase) antes de imponer la regla nueva. No es una migración que se pueda
correr a ciegas en producción sin mirar esa lista antes.

## La bajada

Inversa exacta del constraint. Igual que el `upgrade`, puede fallar si para
entonces existen dos organizaciones distintas con el mismo `(tenant_id,
email)` — sembradas después de que este constraint lo permitiera —, y esa es
la misma razón por la que bajar esta migración no es gratis una vez que se
usó la capacidad nueva (ver DEC-038, "Reversible: no del todo").

Revision ID: 20260911_0116
Revises: 20260820_0115
Create Date: 2026-09-11
"""
from __future__ import annotations

from alembic import op

revision: str = "20260911_0116"
down_revision: str | None = "20260820_0115"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_actors_tenant_email", "actors", type_="unique")
    op.create_unique_constraint(
        "uq_actors_org_email", "actors", ["tenant_id", "organization_id", "email"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_actors_org_email", "actors", type_="unique")
    op.create_unique_constraint(
        "uq_actors_tenant_email", "actors", ["tenant_id", "email"]
    )
