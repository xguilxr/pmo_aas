"""US-240 / ADR-003 (update 2026-08-27) — FKs de `tenant_id` faltantes.

Primer paso de la oleada **W3** (`docs/epics/drafts/reestructura-modelo-datos.md`
§8): antes de activar RLS por tabla (US-241/242) hace falta que **toda** tabla
tenant-scoped tenga un FK real de `tenant_id` a `tenants.id`. Una policy
`USING (tenant_id = current_setting('app.tenant_id', true))` confía en el valor
de la columna tal cual está; si esa columna puede apuntar a un tenant que no
existe (o a ninguno), la policy no lo detecta — solo filtra, no valida.

## El inventario

De las ~40 columnas `tenant_id` del esquema, **13 tablas** no tenían el FK:
`change_approvers`, `approval_tokens` (`models/change_approval.py`),
`plan_baselines`, `risks`, `issues`, `change_requests`, `documents`, `lessons`,
`meeting_minutes` (las seis últimas comparten `_ModuleBase` en
`models/modules.py` — un solo cambio de modelo, seis tablas físicas), `risk_actions`,
`ai_jobs`, `reports` y `tasks`. El resto ya lo tenía desde que se creó su tabla.

**Hallazgo de paso, no alcance nuevo:** `ai_jobs` y `reports` no tenían **ningún**
FK — ni a `tenants` ni a `projects` (`reports.project_id` es `String(36)` suelto).
`superadmin.py::hard_delete_tenant` borra la fila de `tenants` confiando en que
"cascada elimina todo" (comentario en el propio endpoint) — pero esa cascada es
100% de FK de Postgres, no de `relationship()` de SQLAlchemy (`Tenant` no
declara ninguna). Sin FK, esas dos tablas quedaban huérfanas tras un hard-delete.
Este `ON DELETE CASCADE` lo cierra igual que a las demás.

`audit_log.tenant_id` es la única excepción: **`ON DELETE SET NULL`**, no
`CASCADE`. El registro es de solo anexado (AM-08) — la fila que audita el
propio `tenant.hard_delete` no puede desaparecer con el tenant que describe.
La columna ya era nullable (eventos platform-wide del superadmin), así que
`SET NULL` no cambia su contrato.

## Por qué se para antes de escribir el constraint

Ninguna de estas columnas estuvo nunca protegida por FK, así que no hay
garantía de que todos los valores existentes apunten a un tenant real —
sobre todo en datos de prueba o de un seed viejo. `_huerfanos()` cuenta antes
de tocar el esquema y la migración **falla con la lista completa** si
encuentra alguno: adivinar a qué tenant reasignar una fila huérfana sería
inventar un dato, no repararlo. Mismo criterio que la migración 0108 con
`programs.portfolio_id`.

## La rama de SQLite

SQLite no soporta `ALTER TABLE ... ADD CONSTRAINT` sin recrear la tabla, y no
hace falta emularlo aquí: el esquema de tests nace de
`Base.metadata.create_all`, que ya lee el FK desde el modelo actualizado en
este mismo commit. Lo que sí corre en los dos motores es el conteo de
huérfanos — es una lectura, no DDL.

Lo que esta migración **no** hace: activar RLS. Eso es US-241 (jerarquía) y
US-242 (proyectos) — el aislamiento real sigue siendo solo de capa de
aplicación hasta que esas dos cierren (`security-multitenant.md` §1).

Revision ID: 20260827_0116
Revises: 20260820_0115
Create Date: 2026-08-27
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0116"
down_revision: str | None = "20260820_0115"
branch_labels = None
depends_on = None

#: (tabla, ondelete). Todas menos `audit_log` son CASCADE — coincide con el
#: resto del esquema (`grep ForeignKey(\"tenants.id\"` da 30/30 en CASCADE).
TABLAS_TENANT_ID: tuple[tuple[str, str], ...] = (
    ("change_approvers", "CASCADE"),
    ("approval_tokens", "CASCADE"),
    ("plan_baselines", "CASCADE"),
    ("risks", "CASCADE"),
    ("issues", "CASCADE"),
    ("change_requests", "CASCADE"),
    ("documents", "CASCADE"),
    ("lessons", "CASCADE"),
    ("meeting_minutes", "CASCADE"),
    ("risk_actions", "CASCADE"),
    ("ai_jobs", "CASCADE"),
    ("reports", "CASCADE"),
    ("tasks", "CASCADE"),
    ("audit_log", "SET NULL"),
)


def _huerfanos(bind: sa.Connection, tabla: str) -> int:
    """Filas de `tabla` cuyo `tenant_id` no existe en `tenants`.

    El nombre de tabla se interpola porque no hay forma de parametrizar un
    identificador en SQL; los únicos valores que llegan aquí salen de
    `TABLAS_TENANT_ID`, nunca de entrada externa.
    """
    total = bind.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {tabla} t WHERE t.tenant_id IS NOT NULL "
            f"AND NOT EXISTS (SELECT 1 FROM tenants x WHERE x.id = t.tenant_id)"
        )
    ).scalar()
    return int(total or 0)


def upgrade() -> None:
    bind = op.get_bind()

    huerfanos = {tabla: _huerfanos(bind, tabla) for tabla, _ in TABLAS_TENANT_ID}
    con_huerfanos = {k: v for k, v in huerfanos.items() if v}
    if con_huerfanos:
        raise RuntimeError(
            f"tenant_id apunta a un tenant inexistente en: {con_huerfanos}. "
            "Corrige o borra esas filas antes de reintentar — la migración no "
            "adivina a qué tenant pertenecen."
        )

    if bind.dialect.name != "sqlite":
        for tabla, ondelete in TABLAS_TENANT_ID:
            op.create_foreign_key(
                f"fk_{tabla}_tenant_id",
                tabla,
                "tenants",
                ["tenant_id"],
                ["id"],
                ondelete=ondelete,
            )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name != "sqlite":
        for tabla, _ in TABLAS_TENANT_ID:
            op.drop_constraint(f"fk_{tabla}_tenant_id", tabla, type_="foreignkey")
