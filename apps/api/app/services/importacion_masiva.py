"""US-216 — Aplica una importación masiva de proyectos o recursos.

Las reglas de columnas y de validez viven en `app/dominio/importacion.py` y no
saben de base de datos (MCS DEV-02). Aquí se leen los catálogos para detectar
duplicados y se escriben las filas válidas.

## Por qué el portafolio y el área se crean si no existen

Un Excel heredado trae los nombres que el cliente usa, no identificadores de esta
plataforma. Exigir que el portafolio exista antes convertiría la importación en
dos pasos —cree primero seis portafolios a mano, luego suba el archivo— y el
primero se hace mal porque nadie sabe todavía qué portafolios hay hasta ver el
archivo. Se crean con el nombre que trae la fila, que es exactamente el que el
cliente reconoce.

Lo que **no** se crea es un usuario: `pm_email` que no exista deja el proyecto
sin PM en vez de inventar una cuenta. Crear usuarios desde una importación de
proyectos daría acceso a la plataforma a direcciones tecleadas en un Excel, y eso
es una decisión de seguridad, no de carga de datos.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dominio import moneda as dominio_moneda
from app.dominio.importacion import (
    FilaLeida,
    marcar_duplicadas,
    normalizar,
    validar_fila,
)
from app.dominio.proyecto import PREPARACION
from app.models.area import Actor, Area
from app.models.organization import Organization, Portfolio, Program
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.services.folio import next_folio
from app.services.moneda_tenant import preferida as moneda_preferida


async def _existentes_de_proyecto(
    db: AsyncSession, tenant_id: UUID, organization_id: UUID
) -> dict[str, str]:
    """`nombre normalizado → nombre real` de los proyectos de la organización.

    Se acota a la organización y no al inquilino: dos organizaciones del mismo
    cliente pueden tener un «Portal de clientes» cada una, y son proyectos
    distintos. Comparar contra todo el inquilino marcaría uno como duplicado del
    otro y bloquearía una carga legítima.
    """
    filas = (
        await db.execute(
            select(Project.name).where(
                Project.tenant_id == str(tenant_id),
                Project.organization_id == str(organization_id),
                Project.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    return {normalizar(n): n for n in filas if n}


async def _existentes_de_recurso(
    db: AsyncSession, tenant_id: UUID
) -> dict[str, str]:
    """`clave normalizada → nombre` de los actores del inquilino.

    Aquí sí es por inquilino y no por organización: el catálogo de personas es
    compartido (Op A, 2026-05-07), y la misma persona puede trabajar en dos
    organizaciones del cliente. Duplicarla rompería su carga de capacidad, que se
    calcula por persona.

    Se indexa por correo **y** por nombre. Una fila con correo choca con quien
    tenga ese correo; una sin correo, con quien se llame igual — que es más
    grueso, y es lo que hay: sin correo no existe forma fina de decidir.
    """
    filas = (
        await db.execute(
            select(Actor.name, Actor.email).where(
                Actor.tenant_id == str(tenant_id), Actor.deleted_at.is_(None)
            )
        )
    ).all()
    salida: dict[str, str] = {}
    for nombre, correo in filas:
        if nombre:
            salida.setdefault(normalizar(nombre), nombre)
        if correo:
            salida[normalizar(correo)] = nombre or correo
    return salida


async def revisar(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    organization_id: UUID,
    clase: str,
    filas_crudas: list[tuple[int, dict[str, str | None]]],
) -> list[FilaLeida]:
    """Valida todas las filas y marca las duplicadas. No escribe nada.

    `filas_crudas` viene como `(línea del archivo, valores)`. La línea la pone
    quien leyó el archivo y no se recalcula aquí: es la del Excel, contando el
    encabezado, y es lo único que hace útil el número en el reporte.

    Se validan **todas** aunque la primera falle: un archivo de 23 proyectos con
    un error en el 7 tiene 22 filas buenas, y abortar entero obliga a arreglar y
    resubir a ciegas sin saber si hay más errores detrás.
    """
    filas = [validar_fila(linea, crudos, clase) for linea, crudos in filas_crudas]
    existentes = (
        await _existentes_de_proyecto(db, tenant_id, organization_id)
        if clase == "projects"
        else await _existentes_de_recurso(db, tenant_id)
    )
    marcar_duplicadas(filas, existentes, clase)
    return filas


async def _portafolio(
    db: AsyncSession, tenant_id: UUID, organization_id: UUID, nombre: str
) -> str:
    """El portafolio con ese nombre en la organización; lo crea si no existe."""
    existente = (
        await db.execute(
            select(Portfolio).where(
                Portfolio.tenant_id == str(tenant_id),
                Portfolio.organization_id == str(organization_id),
            )
        )
    ).scalars().all()
    for p in existente:
        if normalizar(p.name) == normalizar(nombre):
            return str(p.id)
    nuevo = Portfolio(
        tenant_id=str(tenant_id),
        organization_id=str(organization_id),
        name=nombre.strip(),
    )
    db.add(nuevo)
    await db.flush()
    return str(nuevo.id)


async def _programa(
    db: AsyncSession,
    tenant_id: UUID,
    organization_id: UUID,
    portfolio_id: str,
    nombre: str,
) -> str:
    """El programa con ese nombre dentro del portafolio; lo crea si no existe."""
    existente = (
        await db.execute(
            select(Program).where(
                Program.tenant_id == str(tenant_id),
                Program.portfolio_id == portfolio_id,
            )
        )
    ).scalars().all()
    for p in existente:
        if normalizar(p.name) == normalizar(nombre):
            return str(p.id)
    nuevo = Program(
        tenant_id=str(tenant_id),
        organization_id=str(organization_id),
        portfolio_id=portfolio_id,
        name=nombre.strip(),
    )
    db.add(nuevo)
    await db.flush()
    return str(nuevo.id)


async def _area(db: AsyncSession, tenant_id: UUID, nombre: str) -> str:
    existente = (
        await db.execute(
            select(Area).where(Area.tenant_id == str(tenant_id))
        )
    ).scalars().all()
    for a in existente:
        if normalizar(a.name) == normalizar(nombre):
            return str(a.id)
    nueva = Area(tenant_id=str(tenant_id), name=nombre.strip())
    db.add(nueva)
    await db.flush()
    return str(nueva.id)


async def _pm_por_correo(
    db: AsyncSession, tenant_id: UUID, correo: str
) -> str | None:
    filas = (
        await db.execute(
            select(User.id, User.email).where(User.tenant_id == str(tenant_id))
        )
    ).all()
    for uid, email in filas:
        if email and normalizar(email) == normalizar(correo):
            return str(uid)
    return None


async def aplicar(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    organization_id: UUID,
    clase: str,
    filas: list[FilaLeida],
) -> dict[str, object]:
    """Crea las filas **válidas**. Devuelve qué se creó y qué se saltó.

    Las duplicadas y las inválidas no se tocan. Lo que se devuelve incluye los
    identificadores creados: sin ellos, quien importó no puede ir a ver el
    resultado más que buscando a mano en un listado de 23.
    """
    creados: list[dict[str, str]] = []
    for fila in filas:
        if fila.estado != "valida":
            continue
        if clase == "projects":
            creados.append(
                await _crear_proyecto(db, tenant_id, organization_id, fila)
            )
        else:
            creados.append(await _crear_recurso(db, tenant_id, fila))
    return {
        "created": creados,
        "created_count": len(creados),
        # Los tres números van juntos, siempre. «18 creados» sin decir que 5
        # quedaron fuera es la misma mentira por omisión que un total de costo
        # sin las asignaciones sin tarifa (US-215).
        "skipped_invalid": sum(1 for f in filas if f.estado == "invalida"),
        "skipped_duplicate": sum(1 for f in filas if f.estado == "duplicada"),
    }


async def _crear_proyecto(
    db: AsyncSession, tenant_id: UUID, organization_id: UUID, fila: FilaLeida
) -> dict[str, str]:
    v = fila.valores
    portfolio_id = await _portafolio(
        db, tenant_id, organization_id, str(v["portfolio"])
    )
    program_id = (
        await _programa(
            db, tenant_id, organization_id, portfolio_id, str(v["program"])
        )
        if v.get("program")
        else None
    )
    pm_id = (
        await _pm_por_correo(db, tenant_id, str(v["pm_email"]))
        if v.get("pm_email")
        else None
    )
    folio = await next_folio(db, tenant_id=tenant_id, prefix="PRJ")
    proyecto = Project(
        tenant_id=str(tenant_id),
        organization_id=str(organization_id),
        portfolio_id=portfolio_id,
        program_id=program_id,
        folio=folio,
        name=str(v["name"]).strip(),
        # La descripción es obligatoria al crear por la API y aquí no viene en el
        # archivo. Se deja el rastro de dónde salió el proyecto en vez de una
        # cadena vacía: dentro de un mes, «importado el 12-ago» contesta la
        # pregunta que un campo vacío deja abierta.
        description=f"Importado en la carga masiva ({date.today().isoformat()}).",
        type=str(v["type"]),
        priority=int(v["priority"]),  # type: ignore[call-overload]
        phase=str(v.get("phase") or PREPARACION),
        sponsor=(str(v["sponsor"]).strip() if v.get("sponsor") else None),
        pm_id=pm_id,
        start_date=v.get("start_date") if isinstance(v.get("start_date"), date) else None,
        end_date=v.get("end_date") if isinstance(v.get("end_date"), date) else None,
        budget=v.get("budget"),
        currency=(
            str(v["currency"])
            if v.get("currency")
            else dominio_moneda.resolver(None, await moneda_preferida(db, tenant_id))
        ),
    )
    db.add(proyecto)
    await db.flush()
    if pm_id:
        db.add(
            ProjectMember(
                project_id=proyecto.id, user_id=pm_id, role_in_project="pm"
            )
        )
    return {"id": str(proyecto.id), "folio": folio, "name": proyecto.name}


async def _crear_recurso(
    db: AsyncSession, tenant_id: UUID, fila: FilaLeida
) -> dict[str, str]:
    v = fila.valores
    area_id = (
        await _area(db, tenant_id, str(v["area"])) if v.get("area") else None
    )
    actor = Actor(
        tenant_id=str(tenant_id),
        name=str(v["name"]).strip(),
        email=(str(v["email"]).strip() if v.get("email") else None),
        company=(str(v["company"]).strip() if v.get("company") else None),
        job_title=(str(v["job_title"]).strip() if v.get("job_title") else None),
        area_id=area_id,
        project_capacity_pct=v.get("project_capacity_pct") or 100,
        fte_cost_rate=v.get("fte_cost_rate"),
        cost_rate_period=(
            str(v["cost_rate_period"]) if v.get("cost_rate_period") else None
        ),
    )
    db.add(actor)
    await db.flush()
    return {"id": str(actor.id), "name": actor.name}


async def organizacion_valida(
    db: AsyncSession, tenant_id: UUID, organization_id: UUID
) -> bool:
    return (
        await db.execute(
            select(Organization.id).where(
                Organization.id == str(organization_id),
                Organization.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none() is not None
