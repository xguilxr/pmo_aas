"""SEG-04 — autorización sobre el objeto, en un solo sitio.

> «La autorización DEBE verificarse a nivel de objeto, no únicamente de punto de
> acceso.»

El producto tiene las dos capas y solo una se aplicaba en todas partes:

- **Puerta** — `require_capability` / `require_authenticated` en `api/deps.py`.
  Contesta «¿este usuario puede hacer esta clase de cosa?».
- **Objeto** — `core/visibility.get_user_visibility`, que para un usuario
  `role_type='user'` acota los proyectos a sus `user_scope_assignments`.

La segunda estaba en el **listado** de proyectos y en ningún detalle. Un PM
asignado solo al proyecto A veía únicamente A en `GET /projects` y podía abrir
`GET /projects/{B}` y todos los módulos de B —riesgos, incidencias, documentos,
minutas, tareas, informes, contexto de IA— con solo tener el identificador. Y
el identificador no es un secreto: sale de un enlace compartido, de un informe
o de la barra de direcciones de un compañero.

## Por qué pasó, que importa más que el síntoma

`_get_project` estaba **copiado en seis archivos**, con dos órdenes de
argumentos distintos y dos de las copias sin filtrar `deleted_at`. Nadie
decidió dejar la capa de objeto fuera de cinco endpoints: se actualizó una
copia. Por eso el arreglo no es «añadir la comprobación en cinco sitios más»
sino **borrar las seis copias**, y por eso hay un trinquete que impide escribir
la séptima (`tests/test_seg04_autorizacion_objeto.py`).

## 404, no 403

Igual que el aislamiento entre inquilinos. Un 403 confirma que el proyecto
existe, y para quien no debería verlo esa confirmación ya es información: sirve
para enumerar la cartera de la organización contando identificadores.

## Lo que esto NO cubre

La autorización de **escritura** por rol dentro de un proyecto al que sí se
tiene acceso —quién puede cerrar un riesgo ajeno, por ejemplo— es otra
pregunta, y hoy la responde el modelo de capacidades. Aquí se resuelve la
anterior: si el objeto es alcanzable.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.core.visibility import get_user_visibility
from app.models.project import Project

if TYPE_CHECKING:  # pragma: no cover — solo para el verificador de tipos
    from app.api.deps import CurrentUser


async def proyecto_autorizado(
    db: AsyncSession, project_id: UUID | str, cu: CurrentUser | Any
) -> Project:
    """El proyecto, si este usuario puede verlo. `404` en cualquier otro caso.

    Las tres comprobaciones van juntas y **no se pueden llamar por separado**,
    que es justo lo que permitía que una se olvidara:

    1. existe y no está borrado;
    2. es del inquilino del usuario;
    3. está dentro del alcance del usuario (`user_scope_assignments`).

    El inquilino se deriva de `cu` y no se recibe como argumento. Las seis
    copias que esto sustituye lo recibían, con dos órdenes distintos
    —`(db, project_id, tenant_id)` y `(db, tenant_id, project_id)`—, y ese es
    el tipo de cosa que un día se llama al revés sin que nada falle: los dos
    son `UUID`.
    """
    tenant_id = cu.effective_tenant_id
    if tenant_id is None:
        raise not_found("Proyecto")

    proyecto = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == str(tenant_id),
                # Dos de las seis copias no filtraban esto, así que un proyecto
                # borrado seguía siendo alcanzable por informes y programaciones.
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if proyecto is None:
        raise not_found("Proyecto")

    alcance = await get_user_visibility(cu.user, db)
    if alcance.unrestricted:
        # admin, pm_sr y superadmin no tienen asignaciones y lo ven todo.
        # `unrestricted` mira el ROL, no si el conjunto está vacío: para un PM
        # sin asignaciones el conjunto vacío significa «no ve nada», y
        # confundir los dos casos deja al administrador fuera de su panel.
        return proyecto

    if str(proyecto.id) not in (alcance.project_ids or set()):
        raise not_found("Proyecto")

    return proyecto
