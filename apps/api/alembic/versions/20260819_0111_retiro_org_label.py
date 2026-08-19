"""DEC-032 — se retira `tenants.settings.org_label` (ENH-190).

ENH-190 permitía a un inquilino renombrar «Organización» a «Portafolio» en toda
la interfaz. Era una etiqueta cosmética y estaba bien pensada: hay clientes que
gestionan su propia cartera y no reconocen la palabra «organización».

ADR-037 la dejó inválida. «Portafolio» pasó a ser una entidad **dentro** de la
organización, así que un inquilino con `org_label="portfolios"` vería dos niveles
seguidos llamados igual —«Portafolio → Portafolio → Programa»— en el árbol, en
los filtros y en los desplegables. No es una etiqueta confusa: es una jerarquía
ilegible. El inventario de la reestructura ya lo anticipaba
(`docs/epics/drafts/reestructura-inventario.md` §ENH-190: «retirar»).

## Por qué hay migración para una clave de JSON

Porque sin ella la clave se queda escrita y sin lectores, y una clave con valor
`"portfolios"` en `settings` es una invitación a que alguien la vuelva a leer
dentro de seis meses sin saber por qué se retiró.

Y porque el conteo es la única forma de contestar la pregunta que importa:
**¿alguien la estaba usando?** El registro dice cuántos inquilinos la tenían y
con qué valor. Si sale alguno con `"portfolios"`, ese cliente va a ver el cambio
de nombre y hay que avisarle; si no sale ninguno, no hay nada que comunicar.

## La bajada no restaura el valor, y da igual

`downgrade()` no puede devolver la etiqueta: el valor viejo se borra y no queda
dónde guardarlo (una tabla de residuo para una etiqueta de UI es peor que el
problema). Lo que hace la bajada es dejar la clave ausente, que es exactamente
lo que `get_org_label` interpretaba como el default «organizations» — el mismo
estado visible que tendría el 100 % de los inquilinos si nadie la hubiera
tocado. Para un dato de presentación con default, «ausente» y «restaurado al
default» son el mismo estado.

Lo que la bajada **sí** deja disponible es el conteo en el registro de la subida,
por si hubiera que reponer a mano un inquilino concreto.

Revision ID: 20260819_0111
Revises: 20260819_0110
Create Date: 2026-08-19
"""
from __future__ import annotations

import json
import logging
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "20260819_0111"
down_revision: str | None = "20260819_0110"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.dec032")

#: La clave que se va. Escrita literal y no importada de `tenant_settings.py`:
#: ese módulo acaba de dejar de conocerla, y una migración tiene que seguir
#: corriendo igual el día que el símbolo ya no exista.
CLAVE = "org_label"

#: El valor que motivó el retiro. Se cuenta aparte del resto porque es el único
#: que produce una interfaz distinta —y por tanto el único que hay que comunicar.
VALOR_RETIRADO = "portfolios"


def _ajustes(crudo: Any) -> dict[str, Any] | None:
    """`tenants.settings` como dict, o `None` si no hay nada que tocar.

    La columna es `JSON`, y según el driver llega ya deserializada (psycopg con
    `jsonb`) o como texto (algunos caminos de SQLite). Se aceptan las dos formas
    en vez de asumir una: una migración que sólo funciona con el driver de
    producción no se puede ensayar.
    """
    if crudo is None:
        return None
    if isinstance(crudo, dict):
        return dict(crudo)
    if isinstance(crudo, (str, bytes)):
        try:
            cargado = json.loads(crudo)
        except (ValueError, TypeError):
            return None
        return dict(cargado) if isinstance(cargado, dict) else None
    return None


def _soltar_clave(bind: sa.Connection) -> dict[str, int]:
    """Borra `settings.org_label` de todos los inquilinos. Devuelve el conteo
    por valor encontrado, para dejarlo en el registro."""
    filas = bind.execute(sa.text("SELECT id, settings FROM tenants")).all()
    conteo: dict[str, int] = {}
    for tenant_id, crudo in filas:
        ajustes = _ajustes(crudo)
        if ajustes is None or CLAVE not in ajustes:
            continue
        valor = str(ajustes.pop(CLAVE))
        conteo[valor] = conteo.get(valor, 0) + 1
        bind.execute(
            sa.text("UPDATE tenants SET settings = :s WHERE id = :id"),
            {"s": json.dumps(ajustes), "id": tenant_id},
        )
    return conteo


def upgrade() -> None:
    conteo = _soltar_clave(op.get_bind())
    if not conteo:
        log.info("DEC-032 — ningún inquilino tenía `settings.org_label`.")
        return

    afectados = conteo.get(VALOR_RETIRADO, 0)
    log.warning(
        "DEC-032 — `settings.org_label` borrado. Valores encontrados: %s. "
        "Inquilinos que verán el cambio de nombre en la interfaz: %d.",
        conteo,
        afectados,
    )


def downgrade() -> None:
    # La clave ausente es el default que leía `get_org_label` (ver el encabezado):
    # no hay nada que restaurar y no se inventa un valor.
    log.info(
        "DEC-032 — la bajada no repone `settings.org_label`: su ausencia era el "
        "default. El conteo de la subida está en el registro si hay que reponer "
        "un inquilino a mano."
    )
