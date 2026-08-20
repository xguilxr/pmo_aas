"""US-214 / AM-16 — la membresía en un inquilino pasa a ser una tabla.

Hasta aquí un usuario pertenecía a uno (`users.tenant_id`). Los mockups piden un
selector de inquilino en el encabezado, y para eso la relación tiene que ser de
muchos a muchos.

## Por qué esto es un cambio de seguridad y no de modelo

Es la amenaza **AM-16** del modelo de amenazas, escrita antes de esta migración
(CLAUDE.md §0.3). Hasta US-214 el cambio de inquilino se autorizaba contra el
claim `tenant_ids` del JWT. Con un inquilino por usuario la lista era de un
elemento y el defecto no tenía consecuencia; con dos, **revocar una membresía no
surtiría efecto hasta que el token caduque** —una hora—. Esta tabla es la fuente
de verdad, y se consulta en el cambio y en cada petición.

## El relleno, y por qué esta vez sí

La migración **siembra una membresía por cada usuario con `tenant_id`**. No es
inventar un dato: es el mismo dato en su sitio nuevo, y sin él las dos lecturas
—`users.tenant_id` y la tabla— discreparían desde el primer día, con la tabla
diciendo que nadie pertenece a nada.

Es lo contrario del criterio de la 0114, y la diferencia es qué se sabe: allí la
tarifa del catálogo **no era** la tarifa del momento de asignar, así que copiarla
fechaba hoy una cifra de hace un año. Aquí el inquilino de origen **es** la
membresía; no hay nada que suponer.

## `users.tenant_id` no se toca

Sigue siendo el inquilino de origen: dónde se creó la cuenta y quién la
administra. Retirarlo obligaría a reescribir toda consulta que hoy lo use para
resolver el inquilino por defecto, y a decidir qué pasa con un usuario cuya única
membresía se revoca. La membresía **añade** inquilinos; no reemplaza el de origen.

## La bajada

Suelta el índice antes que la tabla —en Postgres soltar una tabla se lleva sus
índices y el `drop_index` posterior moriría con «index does not exist»— y pierde
las membresías **adicionales**: las de origen siguen en `users.tenant_id`, que no
se tocó. Es la pérdida esperable al retirar la capacidad de pertenecer a varios.

Revision ID: 20260820_0115
Revises: 20260820_0114
Create Date: 2026-08-20
"""
from __future__ import annotations

import logging
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0115"
down_revision: str | None = "20260820_0114"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.us214")


def upgrade() -> None:
    op.create_table(
        "user_tenant_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("granted_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_membership_user_tenant"),
    )
    op.create_index(
        "ix_membership_user_tenant",
        "user_tenant_memberships",
        ["user_id", "tenant_id"],
    )

    # Siembra: el inquilino de origen de cada usuario es su primera membresía.
    # Sin esto, la tabla diría que nadie pertenece a nada y la comprobación de
    # cada petición rechazaría a todo el mundo.
    bind = op.get_bind()
    filas = bind.execute(
        sa.text(
            "SELECT id, tenant_id FROM users WHERE tenant_id IS NOT NULL"
        )
    ).fetchall()
    for user_id, tenant_id in filas:
        bind.execute(
            sa.text(
                "INSERT INTO user_tenant_memberships (id, user_id, tenant_id) "
                "VALUES (:id, :u, :t)"
            ),
            {"id": str(uuid4()), "u": str(user_id), "t": str(tenant_id)},
        )
    log.info("US-214: %s membresías sembradas desde users.tenant_id", len(filas))


def downgrade() -> None:
    # Índice antes que tabla. Ver el encabezado.
    op.drop_index("ix_membership_user_tenant", table_name="user_tenant_memberships")
    op.drop_table("user_tenant_memberships")
