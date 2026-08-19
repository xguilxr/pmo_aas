"""SEG-04 — la autorización se verifica sobre el OBJETO, no solo en la puerta.

> «La autorización DEBE verificarse a nivel de objeto, no únicamente de punto de
> acceso.»

CRÍTICA en la auditoría, y el hueco era real y explotable **dentro del mismo
inquilino**. El modelo tiene dos capas y solo una se aplicaba en todas partes:

- **Puerta:** `require_capability` / `require_authenticated`. Contesta «¿este
  usuario puede hacer esta clase de cosa?». Se aplicaba siempre.
- **Objeto:** `get_user_visibility`, que para un usuario `role_type='user'`
  acota los proyectos a los de sus `user_scope_assignments`. **Se aplicaba en
  el listado y no en el detalle.**

El síntoma exacto: un PM asignado solo al proyecto A veía únicamente A en
`GET /projects`, y a la vez podía pedir `GET /projects/{B}` y **todos** los
módulos de B —riesgos, incidencias, documentos, minutas, tareas, informes,
contexto de IA— porque el resolvedor de proyecto solo comprobaba `tenant_id`.

Y estaba **duplicado en seis archivos**. Seis copias de `_get_project` con la
misma comprobación incompleta: `ai_context`, `modules`, `projects`, `reports`,
`scheduled_minutes` y `scheduled_reports`. Esa es la razón de fondo de que la
capa de objeto se aplicara en un sitio y no en los otros — no hubo una decisión
de dejarla fuera, hubo seis copias y una sola se actualizó.

Esta suite es la demostración del hueco convertida en trinquete: si alguien
vuelve a resolver un proyecto sin pasar por la comprobación compartida, estos
casos se ponen rojos.

**Devuelve 404 y no 403**, igual que el aislamiento entre inquilinos: un 403
confirma que el proyecto existe, y para quien no debería verlo eso ya es
información.
"""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.project import Project
from app.models.user_scope_assignment import UserScopeAssignment
from tests.factories import create_admin_role, create_tenant, create_user, login

RAIZ_API = Path(__file__).resolve().parents[1]


async def _dos_proyectos_y_un_pm(client, db_session):
    """Un PM asignado SOLO al proyecto A, y un proyecto B del mismo inquilino.

    Mismo inquilino a propósito: el aislamiento entre inquilinos ya lo cubre
    `test_seg08_aislamiento_tenants`. Lo que aquí se prueba es lo otro, que es
    lo que estaba abierto — dentro de la misma organización.
    """
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth_admin = await login(client, "admin", "Str0ng-Admin-1!")
    org_id = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgSeg04"}, headers=auth_admin["_authz"]
        )
    ).json()["id"]

    proyectos = []
    for i, nombre in enumerate(("Asignado", "Ajeno")):
        p = Project(
            tenant_id=t.id, organization_id=org_id,
            folio=f"PRJ-SEG04-{i:03d}", name=nombre,
            phase="ejecucion", health_status="green",
            budget=Decimal("100000"), progress=10, type="innovacion",
        )
        db_session.add(p)
        proyectos.append(p)

    await db_session.commit()

    # `role_type="user"` es el PM: el rol al que `user_scope_assignments` acota.
    # `admin` y `pm_sr` ignoran la tabla y ven todo.
    pm = await create_user(
        db_session, tenant=t, username="pmseg04", email="pm04@acme.example.com",
        password="Str0ng-Pm04-1!", role_type="user",
    )
    db_session.add(
        UserScopeAssignment(
            tenant_id=t.id, user_id=pm.id,
            scope_type="project", scope_id=str(proyectos[0].id),
        )
    )
    await db_session.commit()

    auth_pm = await login(client, "pmseg04", "Str0ng-Pm04-1!")
    return auth_pm, str(proyectos[0].id), str(proyectos[1].id)


@pytest.mark.asyncio
async def test_el_listado_ya_respetaba_el_alcance(client, db_session):
    """La mitad que sí funcionaba. Se comprueba para que el arreglo no la rompa.

    Sin este caso, hacer que el detalle respete el alcance podría romper el
    listado sin que nada avise, y el requisito quedaría igual de abierto por el
    otro lado.
    """
    auth_pm, asignado, ajeno = await _dos_proyectos_y_un_pm(client, db_session)

    r = await client.get("/api/v1/projects", headers=auth_pm["_authz"])
    assert r.status_code == 200
    cuerpo = r.json()
    visibles = {p["id"] for p in (cuerpo["items"] if isinstance(cuerpo, dict) else cuerpo)}
    assert asignado in visibles
    assert ajeno not in visibles


@pytest.mark.asyncio
async def test_el_detalle_no_deja_entrar_a_un_proyecto_ajeno(client, db_session):
    """El agujero, en una petición.

    El PM veía un solo proyecto en el listado y podía abrir el otro con su ID.
    El ID no es un secreto: sale de un enlace compartido, de un informe, o de
    contar hacia arriba.
    """
    auth_pm, _asignado, ajeno = await _dos_proyectos_y_un_pm(client, db_session)

    r = await client.get(f"/api/v1/projects/{ajeno}", headers=auth_pm["_authz"])
    assert r.status_code == 404, (
        f"Un PM sin asignación abrió un proyecto ajeno ({r.status_code}). "
        f"404 y no 403: un 403 confirma que el proyecto existe."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ruta",
    [
        "/api/v1/projects/{id}",
        "/api/v1/projects/{id}/risks",
        "/api/v1/projects/{id}/issues",
        "/api/v1/projects/{id}/change-requests",
        "/api/v1/projects/{id}/documents",
        "/api/v1/projects/{id}/meeting-minutes",
        "/api/v1/projects/{id}/tasks",
        "/api/v1/projects/{id}/reports",
        "/api/v1/projects/{id}/gantt",
        "/api/v1/projects/{id}/plan/quality",
        "/api/v1/projects/{id}/charter",
    ],
)
async def test_ningun_modulo_del_proyecto_ajeno_es_alcanzable(
    client, db_session, ruta: str
) -> None:
    """Cada módulo por separado, porque cada uno resolvía el proyecto por su
    cuenta.

    Con seis copias de `_get_project`, arreglar una no arregla las otras cinco,
    y una prueba que solo mirara el detalle daría el requisito por cerrado con
    los módulos abiertos.
    """
    auth_pm, _asignado, ajeno = await _dos_proyectos_y_un_pm(client, db_session)

    r = await client.get(ruta.format(id=ajeno), headers=auth_pm["_authz"])
    assert r.status_code == 404, (
        f"`{ruta}` devolvió {r.status_code} sobre un proyecto fuera del alcance "
        f"del usuario. La comprobación de objeto no se está aplicando ahí."
    )


@pytest.mark.asyncio
async def test_el_proyecto_asignado_sigue_siendo_alcanzable(client, db_session):
    """El caso simétrico, y el que impide 'arreglarlo' negando todo.

    Un control de autorización que niega de más se detecta el primer día y se
    revierte entero, hueco incluido.
    """
    auth_pm, asignado, _ajeno = await _dos_proyectos_y_un_pm(client, db_session)

    for ruta in (
        f"/api/v1/projects/{asignado}",
        f"/api/v1/projects/{asignado}/risks",
        f"/api/v1/projects/{asignado}/tasks",
    ):
        r = await client.get(ruta, headers=auth_pm["_authz"])
        assert r.status_code == 200, f"`{ruta}` negó el proyecto asignado ({r.status_code})"


@pytest.mark.asyncio
async def test_el_administrador_sigue_viendo_todo(client, db_session):
    """`admin` y `pm_sr` no tienen asignaciones y deben verlo todo.

    Es el caso que rompe si se aplica el alcance sin mirar el rol: un conjunto
    vacío de asignaciones significa «sin restricción» para ellos y «no ve nada»
    para un PM, y confundirlos deja al administrador fuera de su propio panel.
    """
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin2", email="admin2@acme.example.com",
        password="Str0ng-Admin-2!", roles=[admin_role],
    )
    auth = await login(client, "admin2", "Str0ng-Admin-2!")
    org_id = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgSeg04b"}, headers=auth["_authz"]
        )
    ).json()["id"]
    p = Project(
        tenant_id=t.id, organization_id=org_id, folio="PRJ-SEG04-B",
        name="Sin asignar a nadie", phase="ejecucion", health_status="green",
        budget=Decimal("1"), progress=0, type="innovacion",
    )
    db_session.add(p)
    await db_session.commit()

    r = await client.get(f"/api/v1/projects/{p.id}", headers=auth["_authz"])
    assert r.status_code == 200


def test_no_quedan_resolvedores_de_proyecto_por_su_cuenta() -> None:
    """La causa de fondo: seis copias de la misma comprobación incompleta.

    No hubo una decisión de dejar la capa de objeto fuera de cinco endpoints;
    hubo seis copias de `_get_project` y solo una se actualizó. Mientras se
    pueda escribir la séptima, el requisito vuelve a abrirse sin que nadie lo
    note.
    """
    copias = []
    for archivo in sorted((RAIZ_API / "app").rglob("*.py")):
        if archivo.name == "autorizacion.py":
            continue  # es la comprobación compartida
        texto = archivo.read_text(encoding="utf-8")
        for m in re.finditer(r"^async def (_get_project\w*)\(", texto, re.M):
            copias.append(f"{archivo.relative_to(RAIZ_API)}: {m.group(1)}")
    assert not copias, (
        "Resolvedores de proyecto locales, que es como la comprobación de "
        "objeto se quedó fuera de cinco endpoints:\n" + "\n".join(copias)
    )


@pytest.mark.asyncio
async def test_un_pm_sin_ninguna_asignacion_no_alcanza_nada(client, db_session):
    """El estado POR DEFECTO de un usuario nuevo, y el que más fácil se cuela.

    `VisibilityScope` usa `None` para «sin restricción» y el conjunto vacío
    para «no ve nada». Escribir la comprobación como `if not
    alcance.project_ids` confunde los dos: un PM recién creado, sin ninguna
    asignación, pasaría a verlo todo. Y es el estado en que nace cada usuario.

    Lo encontró la verificación por mutación — la suite entera seguía verde con
    ese cambio puesto.
    """
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin3", email="admin3@acme.example.com",
        password="Str0ng-Admin-3!", roles=[admin_role],
    )
    auth = await login(client, "admin3", "Str0ng-Admin-3!")
    org_id = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgSeg04c"}, headers=auth["_authz"]
        )
    ).json()["id"]
    p = Project(
        tenant_id=t.id, organization_id=org_id, folio="PRJ-SEG04-C",
        name="De nadie", phase="ejecucion", health_status="green",
        budget=Decimal("1"), progress=0, type="innovacion",
    )
    db_session.add(p)
    await db_session.commit()

    # Sin una sola `UserScopeAssignment`.
    await create_user(
        db_session, tenant=t, username="pmsinnada", email="pmsn@acme.example.com",
        password="Str0ng-Pmsn-1!", role_type="user",
    )
    auth_pm = await login(client, "pmsinnada", "Str0ng-Pmsn-1!")

    r = await client.get(f"/api/v1/projects/{p.id}", headers=auth_pm["_authz"])
    assert r.status_code == 404, (
        f"Un PM sin ninguna asignación alcanzó un proyecto ({r.status_code}). "
        f"El conjunto vacío significa «no ve nada», no «sin restricción»."
    )


@pytest.mark.asyncio
async def test_un_proyecto_borrado_deja_de_ser_alcanzable(client, db_session):
    """Dos de las seis copias no filtraban `deleted_at`.

    Las de `reports` y `scheduled_reports`, justamente: un proyecto borrado
    seguía dejándose generar informes y programaciones. Se comprueba con el
    administrador, para que el caso mida el borrado y no el alcance.
    """
    from datetime import UTC, datetime

    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin4", email="admin4@acme.example.com",
        password="Str0ng-Admin-4!", roles=[admin_role],
    )
    auth = await login(client, "admin4", "Str0ng-Admin-4!")
    org_id = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgSeg04d"}, headers=auth["_authz"]
        )
    ).json()["id"]
    p = Project(
        tenant_id=t.id, organization_id=org_id, folio="PRJ-SEG04-D",
        name="Borrado", phase="ejecucion", health_status="green",
        budget=Decimal("1"), progress=0, type="innovacion",
        deleted_at=datetime.now(UTC),
    )
    db_session.add(p)
    await db_session.commit()

    for ruta in (f"/api/v1/projects/{p.id}", f"/api/v1/projects/{p.id}/reports"):
        r = await client.get(ruta, headers=auth["_authz"])
        assert r.status_code == 404, f"`{ruta}` alcanzó un proyecto borrado ({r.status_code})"
