"""US-241 / ADR-003 — quién puede pedirle a Postgres que vea todos los tenants.

RLS confía en `current_setting('app.tenant_id', true)`: cada policy compara la
columna `tenant_id` de la fila contra ese valor. Un valor de tenant normal solo
ve sus propias filas; el centinela `ALCANCE_PLATAFORMA` (`'*'`, ver ADR-003 —
"centinela robustecido") hace que la policy vea todas.

Esta es la única función del código que puede escribir el centinela, y solo lo
hace si quien llama pasa `alcance_plataforma=True` **explícito** — nunca por
inferencia de un valor de `tenant_id` que venga de la petición. El único call
site permitido es `api/deps.py::get_superadmin`; `test_us241_rls_trinquete.py`
lo comprueba con un grep literal (no ve un bucle ni una lista de nombres —
LESSONS.md, 2026-08-19).
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

#: El valor que la policy reconoce como "todos los tenants". No es un UUID
#: válido, así que no puede colisionar con un `tenant_id` real.
ALCANCE_PLATAFORMA = "*"

log = logging.getLogger("pmoaas.tenant_context")


def _es_postgres() -> bool:
    # SQLite (tests) no tiene `set_config` ni RLS. El filtro de capa de
    # aplicación (`WHERE tenant_id = ...`) sigue siendo lo que protege ahí;
    # esta función es un no-op fuera de Postgres.
    return settings.database_url_async.startswith("postgresql")


async def fijar_tenant_actual(
    db: AsyncSession, tenant_id: str | None, *, alcance_plataforma: bool = False
) -> None:
    """Fija `app.tenant_id` para el resto de la transacción actual.

    - `tenant_id=None` y `alcance_plataforma=False`: no fija nada. Sin GUC,
      `current_setting(..., true)` da `NULL` y ninguna policy hace match — la
      sesión no ve ninguna fila tenant-scoped. Fail-closed por diseño: es el
      estado de login, de un superadmin sin `join-as-admin`, o de cualquier
      ruta que todavía no resolvió tenant.
    - `tenant_id=<uuid-str>`: fija ese valor. El camino de cualquier request
      normal — nunca pasa `alcance_plataforma=True`.
    - `alcance_plataforma=True`: fija el centinela, sin importar qué traiga
      `tenant_id`. Ver el docstring del módulo para las capas que acotan esto.

    Se usa `SELECT set_config(...)` con bind parameter, no `SET LOCAL`
    interpolado: concatenar el valor en el SQL violaría `security-
    multitenant.md` §7 (sin `f"... {var}"`). El tercer argumento de
    `set_config` (`true` = `is_local`) es el equivalente funcional de
    `SET LOCAL`: dura la transacción, no la conexión.
    """
    if not _es_postgres():
        return

    if alcance_plataforma:
        log.warning("tenant_context.alcance_plataforma_activado")
        valor = ALCANCE_PLATAFORMA
    elif tenant_id is not None:
        valor = tenant_id
    else:
        return

    await db.execute(
        text("SELECT set_config('app.tenant_id', :val, true)"), {"val": valor}
    )
