import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, validation_error
from app.core.visibility import get_user_visibility
from app.db.session import get_db
from app.models.metric_snapshot import MetricSnapshot
from app.models.modules import Risk
from app.models.organization import Organization, Program
from app.models.project import Project
from app.models.project_request import ProjectRequest
from app.models.user import User
from app.services.analytics.snapshots import (
    METRIC_FIELDS,
    aggregate_project_trends,
    snapshot_tenant,
)
from app.services.pdf_renderer import render_pdf
from app.services.plan_metadata import round_half_up
from app.services.progress_calculator import effective_progress_map
from app.services.reports.scoped_status import build_scope_status_context

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SCOPE_TYPES = ("tenant", "organization", "program", "project")


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


@router.get("/kpis")
async def kpis(
    organization_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    active_phases = ["planning", "execution", "support"]

    # Scoping por jerarquía (US-015): None = sin restricción (admin),
    # lista = sólo esos project_ids. Lista vacía = ningún proyecto visible.
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)
    role_restricted = role_ids is not None

    def scoped_projects():
        stmt = select(Project.id).where(
            Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
        )
        if organization_id:
            stmt = stmt.where(Project.organization_id == str(organization_id))
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
    change_requests_in_review = 0
    open_issues = 0
    try:
        from app.models.modules import ChangeRequest, Issue, Risk  # type: ignore

        def scope_risks(stmt):
            if organization_id and scoped_ids:
                return stmt.where(Risk.project_id.in_(scoped_ids))
            if organization_id and not scoped_ids:
                return stmt.where(Risk.project_id.in_(["__none__"]))  # vacío
            return stmt

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

        cr_stmt = select(ChangeRequest.id).where(
            ChangeRequest.tenant_id == tenant_id,
            ChangeRequest.status == "in_review",
        )
        if organization_id:
            cr_stmt = cr_stmt.where(
                ChangeRequest.project_id.in_(scoped_ids or ["__none__"])
            )
        change_requests_in_review = await _count(db, cr_stmt)

        iss_stmt = select(Issue.id).where(
            Issue.tenant_id == tenant_id,
            Issue.status.in_(["open", "in_progress", "on_hold"]),  # US-179
        )
        if organization_id:
            iss_stmt = iss_stmt.where(Issue.project_id.in_(scoped_ids or ["__none__"]))
        open_issues = await _count(db, iss_stmt)
    except Exception:
        pass

    budget_stmt = select(func.coalesce(func.sum(Project.budget), 0)).where(
        Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
    )
    if organization_id:
        budget_stmt = budget_stmt.where(
            Project.organization_id == str(organization_id)
        )
    if role_restricted:
        budget_stmt = budget_stmt.where(Project.id.in_(role_ids or ["__none__"]))
    budget_total: Decimal | None = (await db.execute(budget_stmt)).scalar_one()

    # ENH-109 — avance promedio derivado del plan (rollup WBS) con fallback
    # al campo manual para proyectos sin tareas. Se carga el set de proyectos
    # activos del scope y se promedia su avance efectivo en memoria.
    active_proj_stmt = select(Project).where(
        Project.tenant_id == tenant_id,
        Project.phase.in_(active_phases),
        Project.deleted_at.is_(None),
    )
    if organization_id:
        active_proj_stmt = active_proj_stmt.where(
            Project.organization_id == str(organization_id)
        )
    if role_restricted:
        active_proj_stmt = active_proj_stmt.where(
            Project.id.in_(role_ids or ["__none__"])
        )
    active_proj_rows = (await db.execute(active_proj_stmt)).scalars().all()
    eff = await effective_progress_map(db, list(active_proj_rows))
    progress_avg = (sum(eff.values()) / len(eff)) if eff else 0

    return {
        "active_projects": active_projects,
        "requests_in_review": requests_in_review,
        "open_risks": open_risks,
        "severe_risks": severe_risks,
        "change_requests_in_review": change_requests_in_review,
        "open_issues": open_issues,
        "budget_total": float(budget_total or 0),
        "progress_avg": float(progress_avg or 0),
    }


@router.get("/charts")
async def charts(
    organization_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)

    def scoped_where():
        base = [Project.tenant_id == tenant_id, Project.deleted_at.is_(None)]
        if organization_id:
            base.append(Project.organization_id == str(organization_id))
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

    return {
        "projects_by_phase": projects_by_phase,
        "progress_by_phase": progress_by_phase,
        "budget_by_type": budget_by_type,
        "portfolio_health": portfolio_health,
    }


@router.get("/plan-vs-actual")
async def plan_vs_actual(
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    phase: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Project).where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
    if organization_id:
        stmt = stmt.where(Project.organization_id == str(organization_id))
    if program_id:
        stmt = stmt.where(Project.program_id == str(program_id))
    if phase:
        stmt = stmt.where(Project.phase == phase)

    # Scoping por jerarquía (US-015): Project Managers ven sólo lo suyo.
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)
    if role_ids is not None:
        stmt = stmt.where(Project.id.in_(role_ids or ["__none__"]))

    # Orden: rojo primero
    health_order = {"red": 0, "yellow": 1, "green": 2}
    projects = (await db.execute(stmt)).scalars().all()
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

    # ENH-109 — progress_actual derivado del plan (rollup WBS) con fallback
    # al campo manual. `progress_plan` sigue siendo el avance esperado por
    # calendario (_plan_progress_for), que es otra cosa.
    eff = await effective_progress_map(db, list(projects))

    out = []
    for p in projects:
        pm_id = str(p.pm_id) if p.pm_id else None
        out.append(
            {
                "project_id": str(p.id),
                "folio": p.folio,
                "name": p.name,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "budget_plan": float(p.budget or 0),
                "budget_actual": float(p.actual_budget or 0),
                "progress_plan": _plan_progress_for(p),
                "progress_actual": round_half_up(eff[str(p.id)]),
                "health": p.health_status,
                "pm_id": pm_id,
                "pm_name": pm_names.get(pm_id) if pm_id else None,
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
    return max(0, min(100, int(elapsed * 100 / total)))


@router.get("/plan-vs-actual/export.csv")
async def plan_vs_actual_csv(
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    phase: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    data = await plan_vs_actual(organization_id, program_id, phase, cu, db)
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
        raise validation_error(f"scope inválido: {scope}")
    if scope == "tenant":
        return "tenant", str(tenant_id)
    if scope_id is None:
        raise validation_error(f"scope={scope} requiere el parámetro id")
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
        raise validation_error(f"metric inválido: {metric}")

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
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Matriz Organización × Salud (conteo de proyectos). No-admin: solo cuenta
    los proyectos que el usuario ve (US-162)."""
    tenant_id = _tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id)

    orgs = (
        await db.execute(
            select(Organization.id, Organization.name)
            .where(Organization.tenant_id == str(tenant_id))
            .order_by(Organization.name)
        )
    ).all()
    count_conds = [Project.tenant_id == str(tenant_id), Project.deleted_at.is_(None)]
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
    role_ids = await scoped_project_ids(cu, db, tenant_id)

    conds = [
        Project.tenant_id == str(tenant_id),
        Project.deleted_at.is_(None),
        Project.phase != "closed",
    ]
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
        Project.phase != "closed",
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
    """Árbol Organización → Programa → Proyecto (valor=presupuesto, color=salud)."""
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
        pgid = str(p.program_id) if p.program_id else "none"
        org_node = tree.setdefault(
            oid,
            {"id": oid, "name": org_names.get(oid, "Sin organización"), "children": {}},
        )
        prog_node = org_node["children"].setdefault(
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
        raise forbidden(detail="Solo un admin puede capturar snapshots")
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
