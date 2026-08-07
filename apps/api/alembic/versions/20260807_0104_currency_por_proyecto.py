"""BUG-092 — la moneda pasa a vivir en el proyecto, no en un ajuste que nadie leía.

`tenant.settings.currency` ofrecía MXN, USD y EUR y **el formulario que la
guardaba era el único sitio que la leía**. Las diez superficies que muestran
dinero traían `currency: "MXN"` escrito a mano, así que un inquilino en dólares
—el propio sembrado crea uno— veía sus importes rotulados en pesos.

Decisión del owner (2026-08-07): la preferida se queda a nivel de inquilino
como **valor inicial**, y la moneda efectiva la elige cada **proyecto**, que es
donde vive un presupuesto de verdad. La solicitud la lleva también, porque su
importe precede al proyecto y tiene que llegar con él.

**Nulable, y el nulo significa algo.** No es «sin moneda»: es «la que diga el
inquilino». Rellenar las filas existentes con `MXN` habría congelado la
respuesta de hoy y roto justo lo que se viene a arreglar — un inquilino que
cambie su preferida espera que sus proyectos sin elección la sigan.

`VARCHAR(3)` porque son códigos ISO 4217. La lista admitida vive en
`app/dominio/moneda.py` y no en una restricción de columna: ampliarla es un
cambio de producto de una línea, y una restricción obligaría a una migración
para añadir la cuarta.

Revision ID: 20260807_0104
Revises: 20260806_0103
Create Date: 2026-08-07
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260807_0104"
down_revision: str | None = "20260806_0103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for tabla in ("projects", "project_requests"):
        op.add_column(tabla, sa.Column("currency", sa.String(3), nullable=True))


def downgrade() -> None:
    # Reversible sin pérdida de otros datos, **con pérdida de la elección**: al
    # quitar la columna, los proyectos que hubieran escogido una moneda distinta
    # de la preferida vuelven a mostrarse con la del inquilino. Queda escrito
    # porque el runbook de DES-02 §3.3 manda leer esta función antes de bajar.
    for tabla in ("projects", "project_requests"):
        op.drop_column(tabla, "currency")
