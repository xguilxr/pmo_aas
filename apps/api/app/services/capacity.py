"""US-183 — Motor de saturación de recursos (capacidad consumible).

La saturación NO vive en el recurso: vive en la relación recurso-proyecto
(`project_participations`, US-183) cruzada contra la capacidad disponible
para proyectos del recurso (`actors.project_capacity_pct`, US-182).

Reglas (diseño Revamp 1.0, decisiones owner 2026-07-08):
- Solo participations con ``status='activa'`` suman demanda; las
  tentativas se reportan aparte; las vencidas (fuera de ventana) no
  cuentan.
- La demanda se compara contra ``project_capacity_pct``, NUNCA contra 100.
- ``allocation_pct`` NULL = asignación sin cuantificar: no suma, pero se
  reporta (`unquantified`) para que las vistas muestren cobertura de datos.
- Ventanas temporales: today / week / 3weeks / month — una asignación
  cuenta si su rango [start_date, end_date] intersecta la ventana (rangos
  NULL = abiertos).
- Colores (umbrales por tenant en settings.capacity_thresholds):
  sobreasignación en PUNTOS porcentuales — over > red_over (default 10)
  → rojo; over > yellow_over (default 0) → amarillo; si no, verde.

Niveles de agregación: individual, por función de portafolio (rol), por
área y por sub-área (team). La dimensión "recursos" del semáforo de salud
(US-180) se activa con `project_resources_dimension`.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Actor, Area, Team
from app.models.project import Project
from app.models.project_participation import ProjectParticipation
from app.models.tenant import Tenant

WINDOWS = ("today", "week", "3weeks", "month")

DEFAULT_CAPACITY_THRESHOLDS = {"yellow_over": 0, "red_over": 10}


def get_capacity_thresholds(tenant: Tenant | None) -> dict[str, float]:
    merged = dict(DEFAULT_CAPACITY_THRESHOLDS)
    raw = ((tenant.settings or {}).get("capacity_thresholds")) if tenant else None
    if isinstance(raw, dict):
        for k in merged:
            v = raw.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                merged[k] = v
    return merged


def window_range(window: str, today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    days = {"today": 0, "week": 7, "3weeks": 21, "month": 30}.get(window, 7)
    return today, today + timedelta(days=days)


def overload_color(over: float, t: dict[str, float]) -> str:
    if over > t["red_over"]:
        return "red"
    if over > t["yellow_over"]:
        return "yellow"
    return "green"


def _window_overlap(start: date, end: date):
    """Condición SQLAlchemy: la participación intersecta [start, end]."""
    return and_(
        or_(
            ProjectParticipation.start_date.is_(None),
            ProjectParticipation.start_date <= end,
        ),
        or_(
            ProjectParticipation.end_date.is_(None),
            ProjectParticipation.end_date >= start,
        ),
    )


async def _load_assignments(
    db: AsyncSession,
    tenant_id: str,
    start: date,
    end: date,
    *,
    actor_ids: list[str] | None = None,
    project_id: str | None = None,
) -> list[Any]:
    """Participations activas/tentativas que intersectan la ventana, con
    actor y proyecto hidratados (filas planas)."""
    stmt = (
        select(
            ProjectParticipation.actor_id,
            ProjectParticipation.project_id,
            ProjectParticipation.allocation_pct,
            ProjectParticipation.status,
            ProjectParticipation.is_critical,
            ProjectParticipation.assignment_type,
            ProjectParticipation.start_date,
            ProjectParticipation.end_date,
            Project.name.label("project_name"),
            Project.folio.label("project_folio"),
            Project.health_status.label("project_health"),
        )
        .join(Project, Project.id == ProjectParticipation.project_id)
        .where(
            ProjectParticipation.tenant_id == tenant_id,
            ProjectParticipation.status.in_(("activa", "tentativa")),
            Project.deleted_at.is_(None),
            Project.phase != "closed",
            _window_overlap(start, end),
        )
    )
    if actor_ids is not None:
        stmt = stmt.where(ProjectParticipation.actor_id.in_(actor_ids or ["__none__"]))
    if project_id is not None:
        stmt = stmt.where(ProjectParticipation.project_id == project_id)
    return (await db.execute(stmt)).all()


def _summarize_actor(
    actor: Actor, rows: list[Any], t: dict[str, float]
) -> dict[str, Any]:
    active = [r for r in rows if r.status == "activa"]
    demand = sum(float(r.allocation_pct) for r in active if r.allocation_pct is not None)
    tentative = sum(
        float(r.allocation_pct)
        for r in rows
        if r.status == "tentativa" and r.allocation_pct is not None
    )
    unquantified = sum(1 for r in active if r.allocation_pct is None)
    capacity = float(actor.project_capacity_pct or 0)
    over = demand - capacity
    return {
        "actor_id": str(actor.id),
        "name": actor.name,
        "portfolio_function": actor.portfolio_function,
        "resource_type": actor.resource_type,
        "seniority": actor.seniority,
        "scarcity_level": actor.scarcity_level,
        "area_id": str(actor.area_id) if actor.area_id else None,
        "team_id": str(actor.team_id) if actor.team_id else None,
        "organization_id": str(actor.organization_id) if actor.organization_id else None,
        "is_key_resource": bool(actor.is_key_resource),
        "is_shared_resource": bool(actor.is_shared_resource),
        "capacity_pct": capacity,
        "demand_pct": round(demand, 2),
        "tentative_pct": round(tentative, 2),
        "gap_pct": round(capacity - demand, 2),
        "over_pct": round(max(over, 0), 2),
        "projects_count": len({r.project_id for r in active}),
        "unquantified_count": unquantified,
        "color": overload_color(over, t),
    }


async def resource_capacity_summary(
    db: AsyncSession,
    tenant: Tenant,
    *,
    window: str = "week",
    organization_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Nivel 1-3: saturación individual + agregados por rol/área/equipo."""
    t = get_capacity_thresholds(tenant)
    start, end = window_range(window, today)
    tenant_id = str(tenant.id)

    actor_stmt = select(Actor).where(
        Actor.tenant_id == tenant_id,
        Actor.deleted_at.is_(None),
        Actor.is_active.is_(True),
    )
    if organization_id:
        actor_stmt = actor_stmt.where(
            or_(Actor.organization_id == organization_id, Actor.organization_id.is_(None))
        )
    actors = (await db.execute(actor_stmt)).scalars().all()
    if not actors:
        return {"window": window, "start": start.isoformat(), "end": end.isoformat(),
                "resources": [], "by_function": [], "by_area": [], "by_team": []}

    rows = await _load_assignments(
        db, tenant_id, start, end, actor_ids=[str(a.id) for a in actors]
    )
    by_actor: dict[str, list[Any]] = {}
    for r in rows:
        by_actor.setdefault(str(r.actor_id), []).append(r)

    resources = [
        _summarize_actor(a, by_actor.get(str(a.id), []), t) for a in actors
    ]
    # Solo recursos con alguna señal (asignación o clasificación) para no
    # inundar la vista con actores-contacto del catálogo.
    resources = [
        r for r in resources
        if r["projects_count"] > 0 or r["unquantified_count"] > 0
        or r["tentative_pct"] > 0 or r["portfolio_function"] or r["resource_type"]
    ]
    resources.sort(key=lambda r: r["gap_pct"])

    def _aggregate(key: str) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, float]] = {}
        for r in resources:
            k = r[key]
            if not k:
                continue
            b = buckets.setdefault(k, {"capacity": 0.0, "demand": 0.0, "count": 0, "overloaded": 0})
            b["capacity"] += r["capacity_pct"]
            b["demand"] += r["demand_pct"]
            b["count"] += 1
            if r["color"] != "green":
                b["overloaded"] += 1
        out = []
        for k, b in buckets.items():
            over = b["demand"] - b["capacity"]
            out.append({
                key: k,
                "capacity_pct": round(b["capacity"], 2),
                "demand_pct": round(b["demand"], 2),
                "gap_pct": round(b["capacity"] - b["demand"], 2),
                "resources": int(b["count"]),
                "overloaded": int(b["overloaded"]),
                "color": overload_color(over, t),
            })
        out.sort(key=lambda x: x["gap_pct"])
        return out

    by_area = _aggregate("area_id")
    by_team = _aggregate("team_id")
    # Hidratar nombres de área/equipo.
    area_names = {
        str(i): n for i, n in (
            await db.execute(select(Area.id, Area.name).where(Area.tenant_id == tenant_id))
        ).all()
    }
    team_names = {
        str(i): n for i, n in (
            await db.execute(select(Team.id, Team.name).where(Team.tenant_id == tenant_id))
        ).all()
    }
    for b in by_area:
        b["name"] = area_names.get(b["area_id"], "—")
    for b in by_team:
        b["name"] = team_names.get(b["team_id"], "—")

    return {
        "window": window,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "thresholds": t,
        "resources": resources,
        "by_function": _aggregate("portfolio_function"),
        "by_area": by_area,
        "by_team": by_team,
    }


async def resource_conflicts(
    db: AsyncSession,
    tenant: Tenant,
    *,
    window: str = "3weeks",
    organization_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Nivel 4 — gobernanza: recursos sobreasignados con los proyectos en
    choque, para decidir prioridad / pausa / replaneación."""
    summary = await resource_capacity_summary(
        db, tenant, window=window, organization_id=organization_id, today=today
    )
    start, end = window_range(window, today)
    overloaded = [r for r in summary["resources"] if r["color"] != "green"]
    if not overloaded:
        return {"window": window, "conflicts": []}

    rows = await _load_assignments(
        db, str(tenant.id), start, end, actor_ids=[r["actor_id"] for r in overloaded]
    )
    by_actor: dict[str, list[Any]] = {}
    for r in rows:
        if r.status == "activa":
            by_actor.setdefault(str(r.actor_id), []).append(r)

    conflicts = []
    for res in overloaded:
        assignments = by_actor.get(res["actor_id"], [])
        projects = [
            {
                "project_id": str(a.project_id),
                "name": a.project_name,
                "folio": a.project_folio,
                "health": a.project_health,
                "allocation_pct": float(a.allocation_pct) if a.allocation_pct is not None else None,
                "is_critical": bool(a.is_critical),
                "start_date": a.start_date.isoformat() if a.start_date else None,
                "end_date": a.end_date.isoformat() if a.end_date else None,
            }
            for a in assignments
        ]
        projects.sort(key=lambda p: -(p["allocation_pct"] or 0))
        # Recomendación simple v1: liberar del proyecto con menor
        # allocation no-crítico, o cuantificar los sin FTE.
        releasable = [p for p in projects if not p["is_critical"] and p["allocation_pct"]]
        if res["unquantified_count"]:
            recommendation = (
                f"Cuantificar {res['unquantified_count']} asignación(es) sin FTE% "
                "antes de decidir."
            )
        elif releasable:
            p = releasable[-1]
            recommendation = (
                f"Liberar/reducir {p['allocation_pct']:.0f}% en {p['folio']} "
                f"({p['name']}) — es la asignación no-crítica menor."
            )
        else:
            recommendation = "Todas las asignaciones son críticas: escalar prioridad al comité."
        conflicts.append({
            **res,
            "projects": projects,
            "recommendation": recommendation,
        })
    return {
        "window": window,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "conflicts": conflicts,
    }


async def project_resources_dimension(
    db: AsyncSession,
    tenant: Tenant | None,
    project_id: str,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Dimensión "recursos" del semáforo de salud (hook US-180 → US-183).

    Rojo: ≥1 recurso CLAVE del proyecto sobreasignado (>red_over) o ≥3
    recursos sobreasignados. Amarillo: ≥1 sobreasignado. N/A: el proyecto
    no tiene asignaciones cuantificadas.
    """
    t = get_capacity_thresholds(tenant)
    start, end = window_range("3weeks", today)
    tenant_id = str(tenant.id) if tenant else None

    proj_rows = await _load_assignments(db, tenant_id, start, end, project_id=project_id)
    actor_ids = sorted({str(r.actor_id) for r in proj_rows if r.status == "activa"})
    quantified = [r for r in proj_rows if r.status == "activa" and r.allocation_pct is not None]
    if not actor_ids or not quantified:
        return {
            "key": "resources", "color": None,
            "summary": "Sin asignaciones con FTE% en este proyecto",
            "causes": [], "metrics": {},
        }

    actors = (
        await db.execute(select(Actor).where(Actor.id.in_(actor_ids)))
    ).scalars().all()
    # Demanda TOTAL del recurso (todos sus proyectos), no solo este.
    all_rows = await _load_assignments(db, tenant_id, start, end, actor_ids=actor_ids)
    by_actor: dict[str, list[Any]] = {}
    for r in all_rows:
        by_actor.setdefault(str(r.actor_id), []).append(r)

    overloaded: list[dict[str, Any]] = []
    key_overloaded = 0
    for a in actors:
        s = _summarize_actor(a, by_actor.get(str(a.id), []), t)
        if s["color"] != "green":
            overloaded.append(s)
            if s["is_key_resource"]:
                key_overloaded += 1

    if key_overloaded >= 1 or len(overloaded) >= 3:
        color = "red"
    elif overloaded:
        color = "yellow"
    else:
        color = "green"

    causes = [
        {
            "type": "resource_overloaded",
            "what": f"{o['name']} al {o['demand_pct']:.0f}% (capacidad {o['capacity_pct']:.0f}%)",
            "owner": o["name"],
            "due_date": None,
            "days": None,
        }
        for o in sorted(overloaded, key=lambda x: x["gap_pct"])[:5]
    ]
    return {
        "key": "resources",
        "color": color,
        "summary": (
            f"{len(overloaded)} recurso(s) sobreasignado(s)"
            + (f" · {key_overloaded} clave" if key_overloaded else "")
            if overloaded
            else f"{len(actor_ids)} recurso(s) dentro de capacidad"
        ),
        "causes": causes,
        "metrics": {
            "resources": len(actor_ids),
            "overloaded": len(overloaded),
            "key_overloaded": key_overloaded,
        },
    }
