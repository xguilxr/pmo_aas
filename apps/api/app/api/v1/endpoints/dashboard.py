import csv
import io
from datetime import date, timedelta
from typing import Any, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, mensaje, validation_error
from app.core.unidades import razon_a_pct
from app.core.visibility import get_user_visibility
from app.db.session import get_db
from app.dominio.moneda import agregar as agregar_por_moneda
from app.dominio.moneda import resolver as resolver_moneda
from app.dominio.proyecto import CERRADO, FASES_ACTIVAS
from app.models.metric_snapshot import MetricSnapshot
from app.models.modules import Risk
from app.models.organization import Organization, Portfolio, Program
from app.models.project import Project
from app.models.project_request import ProjectRequest
from app.models.user import User
from app.services.analytics.snapshots import (
    METRIC_FIELDS,
    aggregate_project_trends,
    snapshot_tenant,
)
from app.services.completitud import a_json as completitud_a_json
from app.services.completitud import completitud_de
from app.services.indicadores import avance_de_cartera
from app.services.moneda_tenant import preferida as moneda_preferida
from app.services.pdf_renderer import render_pdf
from app.services.plan_metadata import round_half_up
from app.services.progress_calculator import effective_progress_map
from app.services.reports.scoped_status import build_scope_status_context

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

#: US-201 — `portfolio` entra entre organización y programa. El orden de la
#: tupla es el de la jerarquía, no alfabético: lo consumen los desplegables.
SCOPE_TYPES = ("tenant", "organization", "portfolio", "program", "project")


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


async def _count(db: AsyncSession, stmt) -> int:
    return (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0


async def scoped_project_ids(
    cu: CurrentUser,
    db: AsyncSession,
    tenant_id: UUID,
    organization_id: UUID | None = None,
) -> list[str] | None:
    """Devuelve IDs de proyectos visibles al usuario (US-168).

    `None` = sin restricción (admin/pm_sr/superadmin).
    Lista (puede ser vacía) = sólo esos project_ids para rol PM (user).
    Visibilidad derivada de UserScopeAssignment con herencia org→prog→proj.
    """
    if cu.is_admin_equivalent:
        return None  # sin restricción adicional

    visibility = await get_user_visibility(cu.user, db)
    if visibility.unrestricted:
        return None

    ids = visibility.project_ids or set()
    if organization_id:
        # Intersectar: solo proyectos visibles en la org solicitada
        org_projs = (
            await db.execute(
                select(Project.id).where(
                    Project.tenant_id == tenant_id,
                    Project.organization_id == str(organization_id),
                    Project.deleted_at.is_(None),
                    Project.id.in_(ids) if ids else Project.id.is_(None),
                )
            )
        ).scalars().all()
        return [str(i) for i in org_projs]

    return list(ids)


def _condiciones_jerarquia(
    *,
    organization_id: UUID | None = None,
    portfolio_id: UUID | None = None,
    program_id: UUID | None = None,
) -> list[Any]:
    """Las condiciones de la cascada organización → portafolio → programa.

    Un solo sitio para los tres niveles, y no un `if` por endpoint: el dashboard
    tiene siete superficies que filtran igual, y la que se olvide de un nivel no
    falla — devuelve **más** filas de las pedidas, que en un KPI se lee como un
    número y no como un error. Es la misma clase de fallo silencioso que US-202
    cerró con las constantes de fase.

    Los tres niveles se acumulan, y una combinación incoherente
    (`portfolio_id` + un `program_id` de otro portafolio) devuelve vacío en vez
    de rechazar: un filtro no es una escritura, y quien cruza dos filtros que no
    se tocan está explorando, no equivocándose.

    Devuelve condiciones y no un `Select` porque la mitad de las superficies
    construye su propia lista para reutilizarla en varias consultas
    (`charts` hace cuatro con la misma base).
    """
    conds: list[Any] = []
    if organization_id:
        conds.append(Project.organization_id == str(organization_id))
    if portfolio_id:
        conds.append(Project.portfolio_id == str(portfolio_id))
    if program_id:
        conds.append(Project.program_id == str(program_id))
    return conds


#: `_filtro_jerarquia` devuelve **el mismo tipo** que recibe. Sin esto, un
#: `select(Project)` que pasa por el helper sale como `Select[Any]` y el
#: `Sequence[Project]` de la otra punta se vuelve `Sequence[Any]`: mypy deja de
#: ver los atributos del proyecto y el helper apagaría el tipado de sus siete
#: llamadores.
_Consulta = TypeVar("_Consulta", bound=Select[Any])


def _filtro_jerarquia(
    stmt: _Consulta,
    *,
    organization_id: UUID | None = None,
    portfolio_id: UUID | None = None,
    program_id: UUID | None = None,
) -> _Consulta:
    """`_condiciones_jerarquia` aplicado a una consulta sobre `Project`."""
    conds = _condiciones_jerarquia(
        organization_id=organization_id,
        portfolio_id=portfolio_id,
        program_id=program_id,
    )
    return stmt.where(*conds) if conds else stmt


@router.get("/kpis")
async def kpis(
    organization_id: UUID | None = Query(default=None),
    # US-201 — la cascada del dashboard: organización → portafolio → programa.
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    active_phases = list(FASES_ACTIVAS)

    # Scoping por jerarquía (US-015): None = sin restricción (admin),
    # lista = sólo esos project_ids. Lista vacía = ningún proyecto visible.
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)
    role_restricted = role_ids is not None

    def scoped_projects() -> Select[Any]:
        stmt = _filtro_jerarquia(
            select(Project.id).where(
                Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
            ),
            organization_id=organization_id,
            portfolio_id=portfolio_id,
            program_id=program_id,
        )
        if role_restricted:
            stmt = stmt.where(Project.id.in_(role_ids or ["__none__"]))
        return stmt

    # IDs de proyectos del scope actual para filtrar módulos
    scoped_ids_rows = (await db.execute(scoped_projects())).scalars().all()
    scoped_ids = [str(i) for i in scoped_ids_rows]

    active_projects = await _count(
        db,
        scoped_projects().where(Project.phase.in_(active_phases)),
    )
    req_stmt = select(ProjectRequest.id).where(
        ProjectRequest.tenant_id == tenant_id, ProjectRequest.status == "in_review"
    )
    if organization_id:
        req_stmt = req_stmt.where(
            ProjectRequest.organization_id == str(organization_id)
        )
    # Solicitudes: a los no-admins se les muestran solo las que ellos crearon
    if role_restricted:
        req_stmt = req_stmt.where(ProjectRequest.requested_by == str(cu.id))
    requests_in_review = await _count(db, req_stmt)

    # Conteos de módulos — se calculan si existen las tablas (EP006). Defaults seguros.
    open_risks = 0
    severe_risks = 0
    severe_risks_unassigned = 0
    change_requests_in_review = 0
    open_issues = 0
    try:
        from app.models.modules import ChangeRequest, Issue, Risk  # type: ignore

        # US-206 — se filtra ante **cualquier** nivel de la cascada, no solo
        # ante la organización. Antes, elegir un portafolio con «todas las
        # organizaciones» dejaba los riesgos sin filtrar: la tarjeta de riesgos
        # severos contaba la cartera entera junto a un avance que sí era del
        # portafolio. Un número mayor de lo pedido no falla, se lee.
        filtrando = bool(organization_id or portfolio_id or program_id)

        def scope_risks(stmt: _Consulta) -> _Consulta:
            if not filtrando:
                return stmt
            return stmt.where(Risk.project_id.in_(scoped_ids or ["__none__"]))

        open_risks = await _count(
            db,
            scope_risks(
                select(Risk.id).where(Risk.tenant_id == tenant_id, Risk.status != "resolved")  # US-179
            ),
        )
        severe_risks = await _count(
            db,
            scope_risks(
                select(Risk.id).where(
                    Risk.tenant_id == tenant_id,
                    Risk.status != "resolved",  # US-179
                    Risk.severity >= 13,
                )
            ),
        )
        # US-206 — de los severos, los que no tiene nadie. El mockup lo pone
        # como pie de la tarjeta y es el dato que la vuelve accionable: siete
        # riesgos severos es un estado, dos sin responsable es una tarea.
        #
        # Sin responsable son los **dos** campos vacíos: `owner_id` es el
        # usuario legacy y `owner_actor_id` el actor del catálogo (ENH-079).
        # Mirar solo uno contaría como huérfano lo que sí tiene dueño.
        severe_risks_unassigned = await _count(
            db,
            scope_risks(
                select(Risk.id).where(
                    Risk.tenant_id == tenant_id,
                    Risk.status != "resolved",
                    Risk.severity >= 13,
                    Risk.owner_id.is_(None),
                    Risk.owner_actor_id.is_(None),
                )
            ),
        )

        cr_stmt = select(ChangeRequest.id).where(
            ChangeRequest.tenant_id == tenant_id,
            ChangeRequest.status == "in_review",
        )
        if filtrando:
            cr_stmt = cr_stmt.where(
                ChangeRequest.project_id.in_(scoped_ids or ["__none__"])
            )
        change_requests_in_review = await _count(db, cr_stmt)

        iss_stmt = select(Issue.id).where(
            Issue.tenant_id == tenant_id,
            Issue.status.in_(["open", "in_progress", "on_hold"]),  # US-179
        )
        if filtrando:
            iss_stmt = iss_stmt.where(Issue.project_id.in_(scoped_ids or ["__none__"]))
        open_issues = await _count(db, iss_stmt)
    except Exception:
        pass

    # Sin `coalesce`: `SUM` sobre cero filas devuelve NULL, y eso es
    # exactamente el dato —«no hay presupuesto que sumar»—. El `coalesce(…, 0)`
    # que había aquí convertía el hueco en un cero dentro de la propia consulta,
    # que es el defecto de DAT-12 una capa más abajo de donde se suele buscar.
    # La anotación de abajo ya decía `Decimal | None`; era el SQL el que lo
    # hacía imposible.
    #
    # BUG-092 — y se agrupa POR MONEDA. Una cartera con un proyecto en pesos y
    # otro en euros no tiene un presupuesto total: sumar 1.000 y 1.000 para
    # escribir «2.000» es inventar un número que no existe en ninguna parte.
    # `dominio.moneda.agregar` no ofrece la forma de hacerlo mal.
    budget_stmt = select(Project.currency, func.sum(Project.budget)).where(
        Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
    ).group_by(Project.currency)
    budget_stmt = _filtro_jerarquia(
        budget_stmt,
        organization_id=organization_id,
        portfolio_id=portfolio_id,
        program_id=program_id,
    )
    if role_restricted:
        budget_stmt = budget_stmt.where(Project.id.in_(role_ids or ["__none__"]))
    preferida = await moneda_preferida(db, tenant_id)
    budget_por_moneda = agregar_por_moneda(
        (resolver_moneda(codigo, preferida), importe)
        for codigo, importe in (await db.execute(budget_stmt)).all()
    )

    # US-206 — lo consumido, para que la tarjeta diga «consumido X · restante
    # Y» en vez de solo el total. Agrupado por moneda por lo mismo que el
    # presupuesto (BUG-092): no hay un consumido único cuando hay dos monedas.
    #
    # `actual_budget` es lo declarado, no lo derivado de un plan de costos: hoy
    # es el único dato de gasto que existe. El costo por participación es
    # US-215, y cuando llegue esta suma se sustituye, no se acompaña.
    consumido_stmt = _filtro_jerarquia(
        select(Project.currency, func.sum(Project.actual_budget)).where(
            Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
        ).group_by(Project.currency),
        organization_id=organization_id,
        portfolio_id=portfolio_id,
        program_id=program_id,
    )
    if role_restricted:
        consumido_stmt = consumido_stmt.where(Project.id.in_(role_ids or ["__none__"]))
    consumido_por_moneda = agregar_por_moneda(
        (resolver_moneda(codigo, preferida), importe)
        for codigo, importe in (await db.execute(consumido_stmt)).all()
    )

    # ENH-109 — avance promedio derivado del plan (rollup WBS) con fallback
    # al campo manual para proyectos sin tareas. Se carga el set de proyectos
    # activos del scope y se promedia su avance efectivo en memoria.
    active_proj_stmt = select(Project).where(
        Project.tenant_id == tenant_id,
        Project.phase.in_(active_phases),
        Project.deleted_at.is_(None),
    )
    active_proj_stmt = _filtro_jerarquia(
        active_proj_stmt,
        organization_id=organization_id,
        portfolio_id=portfolio_id,
        program_id=program_id,
    )
    if role_restricted:
        active_proj_stmt = active_proj_stmt.where(
            Project.id.in_(role_ids or ["__none__"])
        )
    active_proj_rows = (await db.execute(active_proj_stmt)).scalars().all()
    eff = await effective_progress_map(db, list(active_proj_rows))
    # DAT-09: definición única en `indicadores.avance_de_cartera`. La regla
    # —sin proyectos es «—» y no cero por ciento— vive ahí y no aquí, que es
    # por lo que la instantánea diaria pudo quedarse sin ella.
    progress_avg = avance_de_cartera(list(eff.values()))
    # US-206 — el avance **esperado por calendario** de los mismos proyectos.
    # La tarjeta del mockup enfrenta los dos («68% / 61%, −7 pts vs plan») y
    # la resta solo significa algo si los dos lados cubren el mismo conjunto:
    # por eso sale de `active_proj_rows` y no de otra consulta.
    #
    # `_plan_progress_for` es la definición única del avance por calendario, la
    # misma que usa `plan-vs-actual` fila a fila. Duplicar la fórmula aquí es
    # cómo las dos superficies acabarían discrepando en el mismo número.
    plan_avg = avance_de_cartera(
        [float(_plan_progress_for(p)) for p in active_proj_rows]
    )

    return {
        "active_projects": active_projects,
        "requests_in_review": requests_in_review,
        "open_risks": open_risks,
        "severe_risks": severe_risks,
        "change_requests_in_review": change_requests_in_review,
        "open_issues": open_issues,
        # `SUM` sobre cero filas devuelve NULL, que significa «no hay nada que
        # sumar» y no «suman cero». Un presupuesto de 0 declarado sí llega como
        # 0 y se muestra como 0: la distinción es justo la de DAT-12.
        # BUG-092 — un importe por moneda, y `null` cuando no hay ninguno.
        # La forma del dato es la que impide volver a sumar peras con manzanas
        # aguas abajo: no hay un total al que caerse.
        "budget_by_currency": {m: float(v) for m, v in budget_por_moneda.items()},
        # Se conserva mientras haya una sola moneda en juego, que es el caso de
        # todos los inquilinos de hoy. Con varias vale `null`, y la pantalla
        # pinta el desglose. Ventana de compatibilidad, no duplicidad
        # permanente: se retira cuando ningún consumidor lo lea.
        "budget_total": (
            float(next(iter(budget_por_moneda.values())))
            if len(budget_por_moneda) == 1
            else None
        ),
        "progress_avg": float(progress_avg) if progress_avg is not None else None,
        # US-206 — el par que hace legible el avance. `null` cuando no hay
        # proyectos activos: «—» y no «0 %», la regla de DAT-09 que vive en
        # `avance_de_cartera`.
        "plan_progress_avg": float(plan_avg) if plan_avg is not None else None,
        "budget_consumed_by_currency": {
            m: float(v) for m, v in consumido_por_moneda.items()
        },
        "severe_risks_unassigned": severe_risks_unassigned,
    }


@router.get("/charts")
async def charts(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)

    def scoped_where() -> list[Any]:
        base = [Project.tenant_id == tenant_id, Project.deleted_at.is_(None)]
        base += _condiciones_jerarquia(
            organization_id=organization_id,
            portfolio_id=portfolio_id,
            program_id=program_id,
        )
        if role_ids is not None:
            base.append(Project.id.in_(role_ids or ["__none__"]))
        return base

    rows = (
        await db.execute(
            select(Project.phase, func.count(Project.id))
            .where(*scoped_where())
            .group_by(Project.phase)
        )
    ).all()
    projects_by_phase = dict(rows)

    # ENH-109 — avance por fase derivado del plan (rollup WBS) con fallback
    # al campo manual. Promedio en memoria sobre los proyectos del scope.
    proj_rows = (
        await db.execute(select(Project).where(*scoped_where()))
    ).scalars().all()
    eff = await effective_progress_map(db, list(proj_rows))
    phase_values: dict[str, list[float]] = {}
    for p in proj_rows:
        phase_values.setdefault(p.phase, []).append(eff[str(p.id)])
    progress_by_phase = {
        phase: (sum(vals) / len(vals)) for phase, vals in phase_values.items()
    }

    rows = (
        await db.execute(
            select(Project.type, func.coalesce(func.sum(Project.budget), 0))
            .where(*scoped_where())
            .group_by(Project.type)
        )
    ).all()
    budget_by_type = {t or "unspecified": float(b) for t, b in rows}

    rows = (
        await db.execute(
            select(Project.health_status, func.count(Project.id))
            .where(*scoped_where())
            .group_by(Project.health_status)
        )
    ).all()
    portfolio_health = dict(rows)

    # US-206 — las otras dos distribuciones del mockup. «Por programa» y «por
    # sponsor» contestan preguntas que las dos de arriba no: quién coordina
    # esto y quién lo pidió.
    #
    # `LEFT JOIN` y no `JOIN`: los proyectos sin programa son un grupo real
    # —los que cuelgan del portafolio sin que nadie los coordine (DEC-030)— y
    # un `INNER JOIN` los haría desaparecer del gráfico sin dejar rastro. El
    # mockup los pinta como «Sin programa» y por eso la clave es `null`, que la
    # pantalla rotula; devolver la etiqueta ya traducida metería vocabulario de
    # interfaz en el contrato.
    filas_programa = (
        await db.execute(
            select(Program.name, func.count(Project.id))
            .select_from(Project)
            .outerjoin(Program, Project.program_id == Program.id)
            .where(*scoped_where())
            .group_by(Program.name)
        )
    ).all()
    projects_by_program = {(nombre or ""): conteo for nombre, conteo in filas_programa}

    # El sponsor es texto libre en el proyecto, no una entidad: se agrupa por
    # el valor tal cual. Los vacíos caen en la misma clave `""` que el programa
    # ausente, y por el mismo motivo.
    filas_sponsor = (
        await db.execute(
            select(Project.sponsor, func.count(Project.id))
            .where(*scoped_where())
            .group_by(Project.sponsor)
        )
    ).all()
    projects_by_sponsor = {(nombre or ""): conteo for nombre, conteo in filas_sponsor}

    return {
        "projects_by_phase": projects_by_phase,
        "progress_by_phase": progress_by_phase,
        "budget_by_type": budget_by_type,
        "portfolio_health": portfolio_health,
        "projects_by_program": projects_by_program,
        "projects_by_sponsor": projects_by_sponsor,
    }


@router.get("/tops")
async def tops(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    limite: int = Query(default=5, ge=1, le=20),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[dict[str, Any]]]:
    """US-206 — los proyectos que hay que mirar primero.

    Dos listas cortas: los que acumulan riesgos severos y los que van más
    atrasados respecto de su calendario. El mockup las pone al lado de los KPIs
    porque un número agregado dice que algo pasa y estas dicen **dónde**.

    ## Por qué se calculan aquí y no en la pantalla

    El atraso se podría derivar en el cliente: `plan-vs-actual` ya devuelve
    `progress_plan` y `progress_actual` por proyecto. Se calcula aquí porque
    entonces la definición de «atraso» viviría en dos sitios, y la primera vez
    que alguien cambie el redondeo o el trato de los proyectos sin fechas las
    dos superficies dirían números distintos del mismo proyecto. Es la misma
    razón por la que `avance_de_cartera` existe (DAT-09).

    La tercera lista del mockup —sobrecarga de recursos— no está aquí: sale de
    `/capacity/summary`, que ya devuelve los recursos ordenados por holgura y
    sabe de umbrales por inquilino. Duplicarla sería reimplementar eso peor.
    """
    tenant_id = _tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)

    conds = [
        Project.tenant_id == tenant_id,
        Project.deleted_at.is_(None),
        Project.phase != CERRADO,
    ]
    conds += _condiciones_jerarquia(
        organization_id=organization_id,
        portfolio_id=portfolio_id,
        program_id=program_id,
    )
    if role_ids is not None:
        conds.append(Project.id.in_(role_ids or ["__none__"]))
    proyectos = list((await db.execute(select(Project).where(*conds))).scalars().all())
    por_id = {str(p.id): p for p in proyectos}

    # --- por riesgos severos -------------------------------------------------
    # Solo proyectos activos y del scope: un riesgo severo en un proyecto
    # cerrado no es una cosa que mirar hoy.
    severos: dict[str, int] = {}
    if por_id:
        filas = (
            await db.execute(
                select(Risk.project_id, func.count(Risk.id))
                .where(
                    Risk.tenant_id == tenant_id,
                    Risk.status != "resolved",
                    Risk.severity >= 13,
                    Risk.project_id.in_(list(por_id)),
                )
                .group_by(Risk.project_id)
            )
        ).all()
        severos = {str(pid): conteo for pid, conteo in filas}

    por_riesgo: list[dict[str, Any]] = [
        {
            "project_id": pid,
            "folio": por_id[pid].folio,
            "name": por_id[pid].name,
            "health": por_id[pid].health_status,
            "severe_risks": conteo,
        }
        for pid, conteo in severos.items()
    ]
    # Desempate por nombre y no por identificador: dos proyectos con tres
    # severos cada uno tienen que salir en el mismo orden en cada carga, o la
    # lista parece cambiar sola entre dos refrescos.
    por_riesgo.sort(key=lambda r: (-int(r["severe_risks"]), str(r["name"])))

    # --- por atraso ----------------------------------------------------------
    # El avance real es el del rollup del plan con caída al campo manual
    # (ENH-109); el de plan es el esperado por calendario. La resta es la
    # desviación en puntos, negativa cuando va atrasado.
    eff = await effective_progress_map(db, proyectos)
    por_atraso: list[dict[str, Any]] = []
    for p in proyectos:
        # Sin fechas no hay calendario contra el que comparar, y
        # `_plan_progress_for` devuelve 0: un proyecto al 40 % sin fechas
        # saldría como «+40 pts adelantado», que es peor que no decir nada.
        if not p.start_date or not p.end_date:
            continue
        plan = _plan_progress_for(p)
        real = round_half_up(eff[str(p.id)])
        por_atraso.append(
            {
                "project_id": str(p.id),
                "folio": p.folio,
                "name": p.name,
                "health": p.health_status,
                "progress_plan": plan,
                "progress_actual": real,
                "delta_pts": int(real - plan),
            }
        )
    por_atraso = [r for r in por_atraso if int(r["delta_pts"]) < 0]
    por_atraso.sort(key=lambda r: (int(r["delta_pts"]), str(r["name"])))

    return {
        "by_risk": por_riesgo[:limite],
        "by_delay": por_atraso[:limite],
    }


@router.get("/plan-vs-actual")
async def plan_vs_actual(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    phase: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Una fila por proyecto: la fila de la **vista maestra** (US-207).

    El nombre es histórico. Empezó siendo la tabla «Plan vs Real» del tablero y
    US-207 la convirtió en la fila del control tower: los mismos proyectos con
    las dieciséis columnas del mockup en vez de seis. No se renombró la ruta
    porque el CSV de exportación se comparte por enlace y renombrarla rompería
    los que ya están guardados, a cambio de nada que el usuario note.

    Catorce de las dieciséis columnas del mockup salen de aquí; «Completitud»
    entró con US-210. Las dos que faltan —«Próximo hito» y «Reporte»— son
    US-211.
    """
    tenant_id = _tenant(cu)
    stmt = _filtro_jerarquia(
        select(Project).where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None)),
        organization_id=organization_id,
        portfolio_id=portfolio_id,
        program_id=program_id,
    )
    if phase:
        stmt = stmt.where(Project.phase == phase)

    # Scoping por jerarquía (US-015): Project Managers ven sólo lo suyo.
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)
    if role_ids is not None:
        stmt = stmt.where(Project.id.in_(role_ids or ["__none__"]))

    # Orden: rojo primero
    health_order = {"red": 0, "yellow": 1, "green": 2}
    projects = list((await db.execute(stmt)).scalars().all())
    projects.sort(key=lambda p: health_order.get(p.health_status, 99))

    # Pre-cargar nombres de PM (BUG-003: columna PM Asignado).
    pm_ids = sorted({p.pm_id for p in projects if p.pm_id})
    pm_names: dict[str, str] = {}
    if pm_ids:
        rows = (
            await db.execute(
                select(User.id, User.full_name).where(User.id.in_(pm_ids))
            )
        ).all()
        pm_names = {str(i): n for i, n in rows}

    # US-207 — los nombres de la jerarquía, en dos consultas y no una por fila.
    # La tabla tiene veintitrés filas hoy y ninguna razón para no tener
    # doscientas: una consulta por fila es el patrón que hace que una vista
    # maestra tarde ocho segundos el día que el cliente crece.
    pf_ids = sorted({p.portfolio_id for p in projects if p.portfolio_id})
    pf_names: dict[str, str] = {}
    if pf_ids:
        pf_names = {
            str(i): n
            for i, n in (
                await db.execute(
                    select(Portfolio.id, Portfolio.name).where(Portfolio.id.in_(pf_ids))
                )
            ).all()
        }
    # La organización, porque `/pmo` puede estar en «todas» (US-205): sin este
    # nombre, cuatro organizaciones dan filas indistinguibles y la tabla miente
    # por omisión. El mockup no lleva la columna porque dibuja una organización
    # concreta en el header.
    org_ids = sorted({p.organization_id for p in projects if p.organization_id})
    org_names: dict[str, str] = {}
    if org_ids:
        org_names = {
            str(i): n
            for i, n in (
                await db.execute(
                    select(Organization.id, Organization.name).where(
                        Organization.id.in_(org_ids)
                    )
                )
            ).all()
        }

    pg_ids = sorted({p.program_id for p in projects if p.program_id})
    pg_names: dict[str, str] = {}
    if pg_ids:
        pg_names = {
            str(i): n
            for i, n in (
                await db.execute(
                    select(Program.id, Program.name).where(Program.id.in_(pg_ids))
                )
            ).all()
        }

    # Riesgos e issues abiertos por proyecto. Dos agrupaciones, no dos por fila.
    #
    # `try` porque los módulos son de EP006 y el resto del endpoint funciona sin
    # ellos: una tabla que no existe deja las dos columnas en cero, que es lo
    # que había antes de que existieran. Mismo criterio que en `/kpis`.
    ids_visibles = [str(p.id) for p in projects]
    riesgos_por_proyecto: dict[str, int] = {}
    issues_por_proyecto: dict[str, int] = {}
    if ids_visibles:
        try:
            from app.models.modules import Issue

            riesgos_por_proyecto = {
                str(pid): n
                for pid, n in (
                    await db.execute(
                        select(Risk.project_id, func.count(Risk.id))
                        .where(
                            Risk.tenant_id == tenant_id,
                            Risk.status != "resolved",  # US-179
                            Risk.project_id.in_(ids_visibles),
                        )
                        .group_by(Risk.project_id)
                    )
                ).all()
            }
            issues_por_proyecto = {
                str(pid): n
                for pid, n in (
                    await db.execute(
                        select(Issue.project_id, func.count(Issue.id))
                        .where(
                            Issue.tenant_id == tenant_id,
                            Issue.status.in_(["open", "in_progress", "on_hold"]),
                            Issue.project_id.in_(ids_visibles),
                        )
                        .group_by(Issue.project_id)
                    )
                ).all()
            }
        except Exception:
            pass

    # ENH-109 — progress_actual derivado del plan (rollup WBS) con fallback
    # al campo manual. `progress_plan` sigue siendo el avance esperado por
    # calendario (_plan_progress_for), que es otra cosa.
    eff = await effective_progress_map(db, list(projects))
    preferida_pva = await moneda_preferida(db, tenant_id)
    # US-210 — la columna «Compl.». Se **deriva**: un porcentaje guardado se
    # queda viejo el día que alguien edita el proyecto por un camino que se
    # olvidó de recalcularlo, y entonces la columna dice 96 % de un proyecto al
    # que le faltan tres campos.
    completitudes = await completitud_de(db, list(projects))

    out = []
    for p in projects:
        pm_id = str(p.pm_id) if p.pm_id else None
        out.append(
            {
                "project_id": str(p.id),
                "folio": p.folio,
                "name": p.name,
                # BUG-092 — cada fila lleva su moneda, ya resuelta. Sin ella la
                # tabla vuelve a rotular todo con la misma, que es el bug.
                "currency": resolver_moneda(p.currency, preferida_pva),
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "budget_plan": float(p.budget or 0),
                "budget_actual": float(p.actual_budget or 0),
                "progress_plan": _plan_progress_for(p),
                "progress_actual": round_half_up(eff[str(p.id)]),
                "health": p.health_status,
                # US-207 — de dónde viene la salud. La columna es clicable y
                # abre el desglose del cálculo, y para eso hay que saber si el
                # color lo puso la regla o una persona (US-180/US-191).
                "health_source": p.health_source,
                "pm_id": pm_id,
                "pm_name": pm_names.get(pm_id) if pm_id else None,
                # --- US-207: las columnas de la vista maestra ---------------
                "organization_id": str(p.organization_id) if p.organization_id else None,
                "organization_name": (
                    org_names.get(str(p.organization_id)) if p.organization_id else None
                ),
                "portfolio_id": str(p.portfolio_id) if p.portfolio_id else None,
                "portfolio_name": (
                    pf_names.get(str(p.portfolio_id)) if p.portfolio_id else None
                ),
                "program_id": str(p.program_id) if p.program_id else None,
                "program_name": (
                    pg_names.get(str(p.program_id)) if p.program_id else None
                ),
                "type": p.type,
                "phase": p.phase,
                "priority": p.priority,
                "open_risks": riesgos_por_proyecto.get(str(p.id), 0),
                "open_issues": issues_por_proyecto.get(str(p.id), 0),
                # «Últ. act.» del mockup. Es cuándo cambió el **registro**, no
                # cuándo alguien reportó: la distinción importa y la columna la
                # dice así. El estatus de reporte es US-211.
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                # US-210 — el porcentaje y **qué falta**. El detalle viaja con
                # la fila porque el checklist se pinta al abrir la celda, y una
                # ida al servidor por proyecto para saberlo es la razón por la
                # que nadie lo abriría.
                "completeness": (
                    completitud_a_json(completitudes[str(p.id)])
                    if str(p.id) in completitudes
                    else None
                ),
            }
        )
    return out


def _plan_progress_for(p: Project) -> int:
    if not p.start_date or not p.end_date:
        return 0
    from datetime import date

    today = date.today()
    if today <= p.start_date:
        return 0
    if today >= p.end_date:
        return 100
    total = (p.end_date - p.start_date).days or 1
    elapsed = (today - p.start_date).days
    return max(0, min(100, int(razon_a_pct(elapsed, total, decimales=0))))


@router.get("/plan-vs-actual/export.csv")
async def plan_vs_actual_csv(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    phase: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    # El CSV es la misma tabla: se delega para que no puedan divergir — un
    # export que filtra distinto de la pantalla es un informe que no cuadra.
    data = await plan_vs_actual(
        organization_id, portfolio_id, program_id, phase, cu, db
    )
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "folio", "name", "pm_name", "end_date", "budget_plan",
            "budget_actual", "progress_plan", "progress_actual", "health",
        ],
    )
    writer.writeheader()
    for row in data:
        writer.writerow({k: row.get(k, "") or "" for k in writer.fieldnames})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plan_vs_actual.csv"},
    )


# ============================================================================
# US-152 — Analytics para dashboards N1/N2 (tendencias, matriz de riesgos,
# heatmap, treemap) + captura on-demand de snapshots.
# ============================================================================


def _resolve_scope(scope: str, scope_id: UUID | None, tenant_id: UUID) -> tuple[str, str]:
    if scope not in SCOPE_TYPES:
        raise validation_error(mensaje(
            que=f"scope inválido: {scope}",
            porque="El alcance decide qué se agrega y solo hay los declarados.",
            accion="Usa uno de los alcances admitidos.",
        ))
    if scope == "tenant":
        return "tenant", str(tenant_id)
    if scope_id is None:
        raise validation_error(mensaje(
            que=f"scope={scope} requiere el parámetro id",
            porque="Sin identificador no se sabe de qué organización o programa se pide el dato.",
            accion="Añade el `id` del alcance elegido.",
        ))
    return scope, str(scope_id)


async def _visible_in_scope(
    db: AsyncSession,
    tenant_id: UUID,
    scope_type: str,
    scope_id: str,
    role_ids: list[str],
) -> list[str]:
    """Intersección de los proyectos del scope con los que el usuario ve."""
    conds = _scope_project_conditions(scope_type, scope_id, tenant_id)
    ids = [
        str(i) for i in (await db.execute(select(Project.id).where(*conds))).scalars().all()
    ]
    allowed = set(role_ids)
    return [i for i in ids if i in allowed]


def _scope_project_conditions(scope_type: str, scope_id: str, tenant_id: UUID) -> list:
    conds = [Project.tenant_id == str(tenant_id), Project.deleted_at.is_(None)]
    if scope_type == "organization":
        conds.append(Project.organization_id == scope_id)
    elif scope_type == "portfolio":
        # US-201 — el portafolio agrega **todos** sus proyectos: los de sus
        # programas y los que cuelgan directo de él. Filtrar por los programas
        # del portafolio dejaría fuera justo a los segundos.
        conds.append(Project.portfolio_id == scope_id)
    elif scope_type == "program":
        conds.append(Project.program_id == scope_id)
    elif scope_type == "project":
        conds.append(Project.id == scope_id)
    return conds


@router.get("/trends")
async def trends(
    scope: str = Query(default="tenant"),
    id: UUID | None = Query(default=None),
    metric: str | None = Query(default=None),
    weeks: int = Query(default=12, ge=1, le=104),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Serie histórica de un scope leída de `metric_snapshots` (US-151).

    Admin: serie precomputada del scope. No-admin: serie agregada desde los
    snapshots de los proyectos que el usuario ve dentro del scope (US-162)."""
    tenant_id = _tenant(cu)
    scope_type, scope_id = _resolve_scope(scope, id, tenant_id)
    if metric and metric not in METRIC_FIELDS:
        raise validation_error(mensaje(
            que=f"metric inválido: {metric}",
            porque="Solo se pueden graficar las métricas declaradas.",
            accion="Elige una de las métricas que ofrece la pantalla.",
        ))

    since = date.today() - timedelta(weeks=weeks)
    role_ids = await scoped_project_ids(cu, db, tenant_id)
    if role_ids is None:
        rows = (
            await db.execute(
                select(MetricSnapshot)
                .where(
                    MetricSnapshot.tenant_id == str(tenant_id),
                    MetricSnapshot.scope_type == scope_type,
                    MetricSnapshot.scope_id == scope_id,
                    MetricSnapshot.snapshot_date >= since,
                )
                .order_by(MetricSnapshot.snapshot_date)
            )
        ).scalars().all()
    else:
        visible = await _visible_in_scope(db, tenant_id, scope_type, scope_id, role_ids)
        rows = await aggregate_project_trends(db, tenant_id, visible, since)

    fields = [metric] if metric else list(METRIC_FIELDS)
    series = []
    for r in rows:
        point: dict = {"snapshot_date": r.snapshot_date.isoformat()}
        for f in fields:
            val = getattr(r, f)
            point[f] = float(val) if val is not None else 0
        series.append(point)
    return {
        "scope": scope_type,
        "scope_id": scope_id,
        "metric": metric,
        "series": series,
    }


@router.get("/risk-matrix")
async def risk_matrix(
    scope: str = Query(default="tenant"),
    id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Conteo de riesgos abiertos por celda (probabilidad × impacto), en vivo."""
    tenant_id = _tenant(cu)
    scope_type, scope_id = _resolve_scope(scope, id, tenant_id)

    conds = _scope_project_conditions(scope_type, scope_id, tenant_id)
    role_ids = await scoped_project_ids(cu, db, tenant_id)
    if role_ids is not None:
        conds.append(Project.id.in_(role_ids or ["__none__"]))
    pids = [
        str(i) for i in (await db.execute(select(Project.id).where(*conds))).scalars().all()
    ]

    cells = []
    total = 0
    if pids:
        rows = (
            await db.execute(
                select(Risk.probability, Risk.impact, func.count(Risk.id))
                .where(
                    Risk.project_id.in_(pids),
                    Risk.status != "resolved",  # US-179
                    Risk.probability.is_not(None),
                    Risk.impact.is_not(None),
                )
                .group_by(Risk.probability, Risk.impact)
            )
        ).all()
        for prob, imp, cnt in rows:
            cells.append(
                {"probability": int(prob), "impact": int(imp), "count": int(cnt)}
            )
            total += int(cnt)
    return {"cells": cells, "total": total}


@router.get("/heatmap")
async def heatmap(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Matriz Organización × Salud (conteo de proyectos). No-admin: solo cuenta
    los proyectos que el usuario ve (US-162).

    US-201 — acepta la cascada de la jerarquía. Con un portafolio elegido, las
    filas siguen siendo organizaciones y casi siempre queda una: es correcto, un
    portafolio pertenece a una organización, y la matriz sirve para confirmar
    dónde está lo que se está mirando.
    """
    tenant_id = _tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)

    orgs = (
        await db.execute(
            select(Organization.id, Organization.name)
            .where(Organization.tenant_id == str(tenant_id))
            .order_by(Organization.name)
        )
    ).all()
    count_conds = [Project.tenant_id == str(tenant_id), Project.deleted_at.is_(None)]
    count_conds += _condiciones_jerarquia(
        organization_id=organization_id,
        portfolio_id=portfolio_id,
        program_id=program_id,
    )
    if role_ids is not None:
        count_conds.append(Project.id.in_(role_ids or ["__none__"]))
    counts = (
        await db.execute(
            select(
                Project.organization_id,
                Project.health_status,
                func.count(Project.id),
            )
            .where(*count_conds)
            .group_by(Project.organization_id, Project.health_status)
        )
    ).all()

    by_org = {
        str(oid): {
            "org_id": str(oid),
            "org_name": oname,
            "green": 0,
            "yellow": 0,
            "red": 0,
            "total": 0,
        }
        for oid, oname in orgs
    }
    for org_id, health, cnt in counts:
        entry = by_org.get(str(org_id))
        if entry is None or health not in ("green", "yellow", "red"):
            continue
        entry[health] += int(cnt)
        entry["total"] += int(cnt)
    return {"rows": list(by_org.values())}


@router.get("/health-matrix")
async def health_matrix(
    organization_id: UUID | None = Query(default=None),
    portfolio_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-181 — matriz Proyecto × Dimensión de salud (heatmap ejecutivo).

    Refresca el color auto (US-180) de los proyectos visibles antes de
    responder. Solo proyectos activos (fase != closed). No-admin: solo
    proyectos que el usuario ve.
    """
    from app.models.tenant import Tenant
    from app.services.project_health import refresh_health_bulk

    tenant_id = _tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)

    conds = [
        Project.tenant_id == str(tenant_id),
        Project.deleted_at.is_(None),
        Project.phase != CERRADO,
    ]
    # US-201 — la cascada. Importa más aquí que en otras superficies: esta matriz
    # tiene una fila por proyecto, y sin filtro un inquilino con cien proyectos
    # activos devuelve cien filas para que alguien busque tres.
    conds += _condiciones_jerarquia(
        organization_id=organization_id,
        portfolio_id=portfolio_id,
        program_id=program_id,
    )
    if role_ids is not None:
        conds.append(Project.id.in_(role_ids or ["__none__"]))
    projects = (
        await db.execute(select(Project).where(*conds).order_by(Project.name))
    ).scalars().all()

    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    health_map = await refresh_health_bulk(db, tenant, list(projects))
    await db.commit()

    org_names = {
        str(oid): name
        for oid, name in (
            await db.execute(
                select(Organization.id, Organization.name).where(
                    Organization.tenant_id == str(tenant_id)
                )
            )
        ).all()
    }

    rows = []
    for p in projects:
        entry = health_map.get(str(p.id), {})
        rows.append(
            {
                "project_id": str(p.id),
                "folio": p.folio,
                "name": p.name,
                "organization_id": str(p.organization_id),
                "organization_name": org_names.get(str(p.organization_id)),
                "health_status": p.health_status,
                "health_source": p.health_source,
                "priority": p.priority,
                "dims": entry.get("dims", {}),
            }
        )
    return {"rows": rows}


@router.get("/health-evaluations")
async def portfolio_health_evaluations(
    limit_per_project: int = Query(default=8, ge=1, le=24),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-192 — evaluaciones de salud recientes de TODOS los proyectos
    visibles (para el reporte de salud del portafolio). Misma visibilidad
    que /health-matrix."""
    from app.models.project import ProjectHealthEvaluation

    tenant_id = _tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id)
    conds = [
        Project.tenant_id == str(tenant_id),
        Project.deleted_at.is_(None),
        Project.phase != CERRADO,
    ]
    if role_ids is not None:
        conds.append(Project.id.in_(role_ids or ["__none__"]))
    project_ids = [
        str(r) for r in (await db.execute(select(Project.id).where(*conds))).scalars()
    ]
    if not project_ids:
        return {"rows": []}
    evals = (
        await db.execute(
            select(ProjectHealthEvaluation)
            .where(ProjectHealthEvaluation.project_id.in_(project_ids))
            .order_by(
                ProjectHealthEvaluation.project_id,
                ProjectHealthEvaluation.evaluated_at.desc(),
                ProjectHealthEvaluation.created_at.desc(),
            )
        )
    ).scalars().all()
    rows: list[dict] = []
    seen: dict[str, int] = {}
    for e in evals:
        pid = str(e.project_id)
        if seen.get(pid, 0) >= limit_per_project:
            continue
        seen[pid] = seen.get(pid, 0) + 1
        rows.append(
            {
                "project_id": pid,
                "evaluated_at": e.evaluated_at.isoformat(),
                "schedule": e.schedule,
                "budget": e.budget,
                "risks": e.risks,
                "decisions": e.decisions,
                "resources": e.resources,
                "overall": e.overall,
                "note": e.note,
            }
        )
    return {"rows": rows}


@router.get("/treemap")
async def treemap(
    scope: str = Query(default="tenant"),
    id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Árbol Organización → Portafolio → Programa → Proyecto (valor=presupuesto,
    color=salud).

    US-201 — el portafolio entra como nivel propio, no como etiqueta del
    programa: un proyecto puede colgar del portafolio **sin** programa, y sin ese
    nivel esos proyectos aparecían bajo «Sin programa» de la organización, al
    lado de los que no están clasificados en nada. Eran dos situaciones distintas
    dibujadas igual.
    """
    tenant_id = _tenant(cu)
    scope_type, scope_id = _resolve_scope(scope, id, tenant_id)
    conds = _scope_project_conditions(scope_type, scope_id, tenant_id)
    role_ids = await scoped_project_ids(cu, db, tenant_id)
    if role_ids is not None:
        conds.append(Project.id.in_(role_ids or ["__none__"]))
    projects = (
        await db.execute(
            select(
                Project.id,
                Project.name,
                Project.folio,
                Project.organization_id,
                Project.portfolio_id,
                Project.program_id,
                Project.budget,
                Project.health_status,
            ).where(*conds)
        )
    ).all()

    org_names = {
        str(i): n
        for i, n in (
            await db.execute(
                select(Organization.id, Organization.name).where(
                    Organization.tenant_id == str(tenant_id)
                )
            )
        ).all()
    }
    pf_names = {
        str(i): n
        for i, n in (
            await db.execute(
                select(Portfolio.id, Portfolio.name).where(
                    Portfolio.tenant_id == str(tenant_id)
                )
            )
        ).all()
    }
    prog_names = {
        str(i): n
        for i, n in (
            await db.execute(
                select(Program.id, Program.name).where(
                    Program.tenant_id == str(tenant_id)
                )
            )
        ).all()
    }

    tree: dict = {}
    for p in projects:
        oid = str(p.organization_id) if p.organization_id else "none"
        pfid = str(p.portfolio_id) if p.portfolio_id else "none"
        pgid = str(p.program_id) if p.program_id else "none"
        org_node = tree.setdefault(
            oid,
            {"id": oid, "name": org_names.get(oid, "Sin organización"), "children": {}},
        )
        pf_node = org_node["children"].setdefault(
            pfid,
            {
                "id": pfid,
                "name": pf_names.get(pfid, "Sin clasificar"),
                "children": {},
            },
        )
        prog_node = pf_node["children"].setdefault(
            pgid,
            {"id": pgid, "name": prog_names.get(pgid, "Sin programa"), "children": []},
        )
        prog_node["children"].append(
            {
                "id": str(p.id),
                "name": p.name,
                "folio": p.folio,
                "value": float(p.budget or 0),
                "health": p.health_status,
            }
        )

    out = []
    for org_node in tree.values():
        for pf_node in org_node["children"].values():
            pf_node["children"] = list(pf_node["children"].values())
        org_node["children"] = list(org_node["children"].values())
        out.append(org_node)
    return {"tree": out}


@router.post("/snapshots/capture")
async def capture_snapshots(
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Captura on-demand del snapshot de HOY para el tenant (seed/backfill del
    punto inicial; el job semanal llena hacia adelante). Admin-equivalente."""
    tenant_id = _tenant(cu)
    if not cu.is_admin_equivalent:
        raise forbidden(detail=mensaje(
            que="Solo un admin puede capturar snapshots",
            porque="Una instantánea entra en la serie histórica de toda la organización.",
            accion="Pídeselo a quien administre tu organización.",
        ))
    written = await snapshot_tenant(db, str(tenant_id), date.today())
    return {"date": date.today().isoformat(), "rows": written}


@router.post("/reports/portfolio")
async def portfolio_status_report(
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-160 — Reporte de Status Nivel 1 (Portafolio/PMO) en PDF. Vive fuera
    del Report Builder; agrega KPIs, salud, tendencias, matriz de riesgos y
    comparativa de organizaciones. No-admin: limitado a sus proyectos (US-162)."""
    tenant_id = _tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id)
    ctx = await build_scope_status_context(
        db, tenant_id, "tenant", None, restrict_project_ids=role_ids
    )
    pdf = render_pdf("reports/scope_status.html", ctx)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="status-portafolio.pdf"'},
    )
