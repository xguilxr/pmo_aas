"""US-180 — Salud única híbrida del proyecto.

Un solo semáforo (`projects.health_status`, verde/amarillo/rojo) con dos
fuentes posibles:

- ``auto`` (default): el color lo mantiene este servicio a partir de
  reglas por dimensión — cronograma, presupuesto, riesgos/issues,
  decisiones pendientes y recursos — con umbrales por tenant
  (``tenant.settings.health_thresholds``, mismo patrón que
  ``task_load_thresholds``).
- ``manual``: el PM lo declara (razón obligatoria en amarillo/rojo). El
  motor deja de sobreescribir el color hasta que el PM vuelve a ``auto``.

Reemplaza la dualidad `health_status` + `status_rag` (ENH-101): la
migración 0091 absorbe el RAG declarado como override manual y dropea la
columna vieja.

Frescura del valor ``auto``: se recalcula al leer el detalle del proyecto,
al leer ``GET /projects/{id}/health-detail``, en el snapshot semanal
(US-151) y en los agregados de dashboard que llaman al bulk. Entre
recálculos, los agregados SQL que leen la columna pueden tener staleness
acotada (documentado en el draft del batch Revamp 1.0).

La dimensión ``resources`` queda N/A hasta que exista `allocation_pct`
en participations (US-183); este servicio ya expone el hook.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Actor
from app.models.modules import Issue, Risk
from app.models.project import Project
from app.models.task import Task
from app.models.tenant import Tenant

# Mismo umbral de severidad que analytics/snapshots.py (P×I >= 13).
SEVERE_THRESHOLD = 13

# Estados "vivos" de RAID post US-179 (4 estados canónicos).
OPEN_RAID_STATUSES = ("open", "in_progress", "on_hold")

HEALTH_COLORS = ("green", "yellow", "red")
_COLOR_RANK = {"green": 0, "yellow": 1, "red": 2}

DIMENSION_LABELS: dict[str, str] = {
    "schedule": "Cronograma",
    "budget": "Presupuesto",
    "risks": "Riesgos / Issues",
    "decisions": "Decisiones",
    "resources": "Recursos",
}

DEFAULT_HEALTH_THRESHOLDS: dict[str, dict[str, float]] = {
    "schedule": {
        "yellow_overdue_pct": 10,
        "red_overdue_pct": 25,
        "yellow_overdue_milestones": 1,
        "red_overdue_milestones": 3,
    },
    "budget": {"yellow_ratio": 0.9, "red_ratio": 1.0},
    "risks": {
        "yellow_severe": 1,
        "red_severe": 3,
        "yellow_open_issues": 8,
        "red_open_issues": 15,
    },
    "decisions": {"stale_days": 14, "yellow_stale": 1, "red_stale": 3},
}


def get_health_thresholds(tenant: Tenant | None) -> dict[str, dict[str, float]]:
    """Umbrales efectivos: defaults con override por tenant (deep-merge
    tolerante — claves desconocidas o valores no numéricos se ignoran)."""
    merged = {dim: dict(vals) for dim, vals in DEFAULT_HEALTH_THRESHOLDS.items()}
    raw = ((tenant.settings or {}).get("health_thresholds")) if tenant else None
    if isinstance(raw, dict):
        for dim, vals in raw.items():
            if dim in merged and isinstance(vals, dict):
                for k, v in vals.items():
                    if k in merged[dim] and isinstance(v, (int, float)) and not isinstance(v, bool):
                        merged[dim][k] = v
    return merged


def worst_color(colors: list[str | None]) -> str:
    present = [c for c in colors if c in _COLOR_RANK]
    if not present:
        return "green"
    return max(present, key=lambda c: _COLOR_RANK[c])


def _schedule_color(t: dict[str, float], overdue_pct: float, overdue_ms: int) -> str:
    if overdue_ms >= t["red_overdue_milestones"] or overdue_pct >= t["red_overdue_pct"]:
        return "red"
    if overdue_ms >= t["yellow_overdue_milestones"] or overdue_pct >= t["yellow_overdue_pct"]:
        return "yellow"
    return "green"


def _budget_color(t: dict[str, float], ratio: float) -> str:
    if ratio > t["red_ratio"]:
        return "red"
    if ratio >= t["yellow_ratio"]:
        return "yellow"
    return "green"


def _risks_color(t: dict[str, float], severe: int, open_issues: int) -> str:
    if severe >= t["red_severe"] or open_issues >= t["red_open_issues"]:
        return "red"
    if severe >= t["yellow_severe"] or open_issues >= t["yellow_open_issues"]:
        return "yellow"
    return "green"


def _decisions_color(t: dict[str, float], stale: int) -> str:
    if stale >= t["red_stale"]:
        return "red"
    if stale >= t["yellow_stale"]:
        return "yellow"
    return "green"


async def _schedule_dimension(
    db: AsyncSession, project_id: str, t: dict[str, float], today: date
) -> dict[str, Any]:
    open_cond = Task.status != "completed"
    overdue_cond = and_(open_cond, Task.end_date.is_not(None), Task.end_date < today)
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(case((open_cond, 1), else_=0)), 0),
                func.coalesce(func.sum(case((overdue_cond, 1), else_=0)), 0),
                func.coalesce(
                    func.sum(case((and_(overdue_cond, Task.is_milestone.is_(True)), 1), else_=0)), 0
                ),
            ).where(Task.project_id == project_id)
        )
    ).one()
    open_tasks, overdue, overdue_ms = int(row[0]), int(row[1]), int(row[2])
    overdue_pct = round(overdue * 100 / open_tasks, 1) if open_tasks else 0.0
    color = _schedule_color(t, overdue_pct, overdue_ms)

    causes: list[dict[str, Any]] = []
    if overdue:
        rows = (
            await db.execute(
                select(Task.name, Task.end_date, Task.is_milestone, Actor.name.label("owner"))
                .outerjoin(Actor, Actor.id == Task.assignee_actor_id)
                .where(Task.project_id == project_id, overdue_cond)
                .order_by(Task.is_milestone.desc(), Task.end_date.asc())
                .limit(5)
            )
        ).all()
        for r in rows:
            causes.append(
                {
                    "type": "milestone_overdue" if r.is_milestone else "task_overdue",
                    "what": r.name,
                    "owner": r.owner,
                    "due_date": r.end_date.isoformat() if r.end_date else None,
                    "days": (today - r.end_date).days if r.end_date else None,
                }
            )
    summary = (
        f"{overdue} de {open_tasks} tareas abiertas atrasadas ({overdue_pct}%)"
        + (f" · {overdue_ms} hito(s) vencido(s)" if overdue_ms else "")
        if open_tasks
        else "Sin tareas abiertas"
    )
    return {"key": "schedule", "color": color, "summary": summary, "causes": causes,
            "metrics": {"open_tasks": open_tasks, "overdue": overdue,
                        "overdue_pct": overdue_pct, "overdue_milestones": overdue_ms}}


def _budget_dimension(project: Project, t: dict[str, float]) -> dict[str, Any]:
    budget = float(project.budget or 0)
    if budget <= 0:
        return {"key": "budget", "color": None, "summary": "Sin presupuesto configurado",
                "causes": [], "metrics": {}}
    actual = float(project.actual_budget or 0)
    ratio = actual / budget
    color = _budget_color(t, ratio)
    pct = round(ratio * 100, 1)
    causes = []
    if color != "green":
        causes.append({"type": "budget_burn", "what": f"Consumo {pct}% del presupuesto",
                       "owner": None, "due_date": None, "days": None})
    return {"key": "budget", "color": color,
            "summary": f"Consumido {pct}% (real {actual:,.0f} / plan {budget:,.0f})",
            "causes": causes, "metrics": {"ratio": round(ratio, 3), "pct": pct}}


async def _risks_dimension(
    db: AsyncSession, project_id: str, t: dict[str, float]
) -> dict[str, Any]:
    open_risk = Risk.status.in_(OPEN_RAID_STATUSES)
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(case((open_risk, 1), else_=0)), 0),
                func.coalesce(
                    func.sum(case((and_(open_risk, Risk.severity >= SEVERE_THRESHOLD), 1), else_=0)), 0
                ),
            ).where(Risk.project_id == project_id)
        )
    ).one()
    open_risks, severe = int(row[0]), int(row[1])
    open_issues = (
        await db.execute(
            select(func.count(Issue.id)).where(
                Issue.project_id == project_id,
                Issue.type == "issue",
                Issue.status.in_(OPEN_RAID_STATUSES),
            )
        )
    ).scalar_one()
    color = _risks_color(t, severe, int(open_issues))

    causes: list[dict[str, Any]] = []
    if severe:
        rows = (
            await db.execute(
                select(Risk.title, Risk.severity, Risk.due_date, Actor.name.label("owner"))
                .outerjoin(Actor, Actor.id == Risk.owner_actor_id)
                .where(Risk.project_id == project_id, open_risk, Risk.severity >= SEVERE_THRESHOLD)
                .order_by(Risk.severity.desc())
                .limit(3)
            )
        ).all()
        for r in rows:
            causes.append({"type": "severe_risk", "what": r.title, "owner": r.owner,
                           "due_date": r.due_date.isoformat() if r.due_date else None,
                           "days": None, "severity": r.severity})
    return {"key": "risks", "color": color,
            "summary": f"{severe} riesgo(s) severo(s) · {open_risks} abiertos · {open_issues} issues abiertos",
            "causes": causes,
            "metrics": {"open_risks": open_risks, "severe_risks": severe,
                        "open_issues": int(open_issues)}}


async def _decisions_dimension(
    db: AsyncSession, project_id: str, t: dict[str, float], now: datetime
) -> dict[str, Any]:
    cutoff = now - timedelta(days=int(t["stale_days"]))
    open_dec = and_(Issue.type == "decision", Issue.status.in_(OPEN_RAID_STATUSES))
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(case((open_dec, 1), else_=0)), 0),
                func.coalesce(
                    func.sum(case((and_(open_dec, Issue.reported_at <= cutoff), 1), else_=0)), 0
                ),
            ).where(Issue.project_id == project_id)
        )
    ).one()
    open_count, stale = int(row[0]), int(row[1])
    color = _decisions_color(t, stale)

    causes: list[dict[str, Any]] = []
    if open_count:
        rows = (
            await db.execute(
                select(Issue.title, Issue.reported_at, Issue.committed_date, Actor.name.label("owner"))
                .outerjoin(Actor, Actor.id == Issue.owner_actor_id)
                .where(Issue.project_id == project_id, open_dec)
                .order_by(Issue.reported_at.asc())
                .limit(5)
            )
        ).all()
        for r in rows:
            reported = r.reported_at
            if reported is not None and reported.tzinfo is None:
                reported = reported.replace(tzinfo=UTC)
            days_open = (now - reported).days if reported else None
            causes.append({"type": "pending_decision", "what": r.title, "owner": r.owner,
                           "due_date": r.committed_date.isoformat() if r.committed_date else None,
                           "days": days_open})
    return {"key": "decisions", "color": color,
            "summary": f"{open_count} decisión(es) abiertas · {stale} con más de {int(t['stale_days'])} días",
            "causes": causes, "metrics": {"open": open_count, "stale": stale}}


async def _resources_dimension(
    db: AsyncSession, tenant: Tenant | None, project_id: str, today: date
) -> dict[str, Any]:
    # US-183: la dimensión vive en services/capacity.py (demanda total del
    # recurso en TODOS sus proyectos vs project_capacity_pct). N/A si el
    # proyecto no tiene asignaciones cuantificadas.
    from app.services.capacity import project_resources_dimension

    return await project_resources_dimension(db, tenant, project_id, today=today)


_SUGGESTED_ACTIONS = {
    "milestone_overdue": "Replanear el hito o escalar el bloqueo",
    "task_overdue": "Revisar la tarea con el responsable",
    "pending_decision": "Escalar la decisión al sponsor/comité",
    "severe_risk": "Revisar/activar el plan de mitigación",
    "budget_burn": "Revisar forecast y solicitar control de cambio",
    "resource_overloaded": "Revisar conflicto de capacidad (vista Recursos)",
}


def _build_focus(dimensions: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    """Tarjetas "foco PM": las causas top de las dimensiones no-verdes,
    con responsable, fecha compromiso y siguiente acción sugerida."""
    items: list[dict[str, Any]] = []
    for dim in dimensions:
        if dim["color"] not in ("yellow", "red"):
            continue
        for c in dim["causes"]:
            items.append({
                "dimension": dim["key"],
                "dimension_label": DIMENSION_LABELS[dim["key"]],
                "color": dim["color"],
                "what": c["what"],
                "type": c["type"],
                "owner": c.get("owner"),
                "due_date": c.get("due_date"),
                "days": c.get("days"),
                "suggested_action": _SUGGESTED_ACTIONS.get(c["type"], "Revisar con el equipo"),
            })
    items.sort(key=lambda i: (_COLOR_RANK[i["color"]], i["days"] or 0), reverse=True)
    return items[:limit]


async def compute_project_health_detail(
    db: AsyncSession, tenant: Tenant | None, project: Project,
    *, today: date | None = None,
) -> dict[str, Any]:
    """Cálculo detallado (con causas) de las 5 dimensiones + color global."""
    today = today or date.today()
    now = datetime.now(UTC)
    t = get_health_thresholds(tenant)
    pid = str(project.id)
    dimensions = [
        await _schedule_dimension(db, pid, t["schedule"], today),
        _budget_dimension(project, t["budget"]),
        await _risks_dimension(db, pid, t["risks"]),
        await _decisions_dimension(db, pid, t["decisions"], now),
        await _resources_dimension(db, tenant, pid, today),
    ]
    for d in dimensions:
        d["label"] = DIMENSION_LABELS[d["key"]]
    computed = worst_color([d["color"] for d in dimensions])
    return {
        "computed": computed,
        "dimensions": dimensions,
        "focus": _build_focus(dimensions),
    }


def apply_auto_health(project: Project, computed: str) -> bool:
    """Si la fuente es auto y el color cambió, lo aplica. Devuelve True si
    hubo cambio (el caller decide commit)."""
    if getattr(project, "health_source", "auto") == "manual":
        return False
    if project.health_status != computed:
        project.health_status = computed
        return True
    return False


async def refresh_health_bulk(
    db: AsyncSession, tenant: Tenant | None, projects: list[Project],
    *, today: date | None = None,
) -> dict[str, dict[str, Any]]:
    """Versión bulk (queries agrupadas, sin causas) para snapshots y
    dashboards. Aplica el color auto sobre los `Project` recibidos (el
    caller hace commit). Devuelve {project_id: {computed, dims}}."""
    if not projects:
        return {}
    today = today or date.today()
    now = datetime.now(UTC)
    t = get_health_thresholds(tenant)
    ids = [str(p.id) for p in projects]

    open_cond = Task.status != "completed"
    overdue_cond = and_(open_cond, Task.end_date.is_not(None), Task.end_date < today)
    task_rows = (
        await db.execute(
            select(
                Task.project_id,
                func.coalesce(func.sum(case((open_cond, 1), else_=0)), 0),
                func.coalesce(func.sum(case((overdue_cond, 1), else_=0)), 0),
                func.coalesce(
                    func.sum(case((and_(overdue_cond, Task.is_milestone.is_(True)), 1), else_=0)), 0
                ),
            ).where(Task.project_id.in_(ids)).group_by(Task.project_id)
        )
    ).all()
    tasks_by_pid = {str(r[0]): (int(r[1]), int(r[2]), int(r[3])) for r in task_rows}

    open_risk = Risk.status.in_(OPEN_RAID_STATUSES)
    risk_rows = (
        await db.execute(
            select(
                Risk.project_id,
                func.coalesce(
                    func.sum(case((and_(open_risk, Risk.severity >= SEVERE_THRESHOLD), 1), else_=0)), 0
                ),
            ).where(Risk.project_id.in_(ids)).group_by(Risk.project_id)
        )
    ).all()
    severe_by_pid = {str(r[0]): int(r[1]) for r in risk_rows}

    cutoff = now - timedelta(days=int(t["decisions"]["stale_days"]))
    open_issue_cond = Issue.status.in_(OPEN_RAID_STATUSES)
    issue_rows = (
        await db.execute(
            select(
                Issue.project_id,
                func.coalesce(
                    func.sum(case((and_(open_issue_cond, Issue.type == "issue"), 1), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    open_issue_cond,
                                    Issue.type == "decision",
                                    Issue.reported_at <= cutoff,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            ).where(Issue.project_id.in_(ids)).group_by(Issue.project_id)
        )
    ).all()
    issues_by_pid = {str(r[0]): (int(r[1]), int(r[2])) for r in issue_rows}

    out: dict[str, dict[str, Any]] = {}
    for p in projects:
        pid = str(p.id)
        open_tasks, overdue, overdue_ms = tasks_by_pid.get(pid, (0, 0, 0))
        overdue_pct = round(overdue * 100 / open_tasks, 1) if open_tasks else 0.0
        budget = float(p.budget or 0)
        dims = {
            "schedule": _schedule_color(t["schedule"], overdue_pct, overdue_ms),
            "budget": (
                _budget_color(t["budget"], float(p.actual_budget or 0) / budget)
                if budget > 0
                else None
            ),
            "risks": _risks_color(
                t["risks"], severe_by_pid.get(pid, 0), issues_by_pid.get(pid, (0, 0))[0]
            ),
            "decisions": _decisions_color(t["decisions"], issues_by_pid.get(pid, (0, 0))[1]),
            "resources": None,
        }
        computed = worst_color(list(dims.values()))
        apply_auto_health(p, computed)
        out[pid] = {"computed": computed, "dims": dims}
    return out
