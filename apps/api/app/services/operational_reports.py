"""Armadores de contexto para reportes ejecutables sin IA (EP014).

- `build_avance_context`: Reporte de Avance de Proyecto (US-038).
- `build_seguimiento_context`: Reporte de Seguimiento de Actividades
  agrupadas por responsable (US-039).
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.models.area import Area
from app.models.modules import ChangeRequest, Issue, Risk
from app.models.organization import Organization, Program
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.services.plan_metadata import (
    compute_plan_rollup_progress,
    round_half_up,
)
from app.services.report_kpis import (
    compute_kpis,
    default_period_start,
    kpis_have_any_value,
)


def _is_completed(t: Task) -> bool:
    return t.status == "completed" or (t.progress or 0) >= 100


def _is_completed_late(t: Task) -> bool:
    """US-177 — tarea COMPLETADA pero cerrada tarde (`closed_at > end_date`).
    Tag amarillo "Completada con atraso". Sin `closed_at` no hay dato."""
    if t.end_date is None or not _is_completed(t):
        return False
    closed = getattr(t, "closed_at", None)
    return closed is not None and closed > t.end_date


def _is_delayed(t: Task, today: date) -> bool:
    """US-177 — tarea ATRASADA (rojo): NO completada y con `end_date < hoy`.

    La distinción de US-177: una tarea ya completada que cerró tarde NO es
    "Atrasada" (es "Completada con atraso", ver `_is_completed_late`); aquí
    sólo cuentan las pendientes vencidas, que son las accionables.
    """
    if t.end_date is None or _is_completed(t):
        return False
    return t.end_date < today


def _is_critical_task(t: Task) -> bool:
    """ENH-064 — criticidad alta o crítica."""
    return getattr(t, "criticality", None) in ("high", "critical")


def prioritize_tasks(
    tasks: list[Task],
    today: date,
    top_n: int = 20,
) -> list[Task]:
    """ENH-064 — devuelve `tasks` reordenadas: hitos > críticas > retrasadas
    > resto. Truncado a `top_n` para que el reporte sea conciso.

    El orden dentro de cada bucket preserva el orden de entrada (estable).
    Una tarea aparece sólo una vez (deduplicación por id).
    """
    seen: set = set()
    out: list[Task] = []

    def _push(predicate):
        for t in tasks:
            if t.id in seen:
                continue
            if predicate(t):
                seen.add(t.id)
                out.append(t)

    _push(lambda t: bool(t.is_milestone))
    _push(_is_critical_task)
    _push(lambda t: _is_delayed(t, today))
    _push(lambda t: True)  # resto, en orden original
    return out[:top_n]


def _period_label(days: int) -> str:
    """ENH-063 — etiqueta humana para el período."""
    if days <= 1:
        return "1 día"
    if days <= 7:
        return "1 semana"
    if days <= 14:
        return "2 semanas"
    if days <= 30:
        return "1 mes"
    if days <= 90:
        return "3 meses"
    return f"{days} días"


async def _get_project(db: AsyncSession, tenant_id: UUID, project_id: UUID) -> Project:
    row = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == str(tenant_id),
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise not_found("Proyecto")
    return row


async def _user(db: AsyncSession, user_id: UUID | None) -> dict[str, str | None] | None:
    if user_id is None:
        return None
    row = (
        await db.execute(
            select(User.full_name, User.email).where(User.id == str(user_id))
        )
    ).first()
    if row is None:
        return None
    return {"full_name": row[0], "email": row[1]}


async def build_avance_context(
    db: AsyncSession,
    tenant_id: UUID,
    project_id: UUID,
    cut_off_date: date,
    window_days: int = 14,
) -> dict[str, Any]:
    """Contexto para Reporte de Avance (sin IA).

    `window_days` (ENH-063) define el rango hacia atrás para hitos
    cerrados y eventos del período. Default 14d para back-compat.
    """
    project = await _get_project(db, tenant_id, project_id)

    org = (
        await db.execute(
            select(Organization.name).where(Organization.id == project.organization_id)
        )
    ).scalar_one_or_none()
    prog = None
    if project.program_id:
        prog = (
            await db.execute(
                select(Program.name).where(Program.id == project.program_id)
            )
        ).scalar_one_or_none()
    pm = await _user(db, project.pm_id)

    # Tareas
    all_tasks = (
        await db.execute(
            select(Task).where(Task.project_id == str(project_id))
        )
    ).scalars().all()
    total_tasks = len(all_tasks)
    done = sum(1 for t in all_tasks if t.status == "completed" or (t.progress or 0) >= 100)
    in_progress = sum(1 for t in all_tasks if t.status == "in_progress")
    not_started = sum(1 for t in all_tasks if t.status == "not_started")
    # ENH-109 — avance derivado del plan (rollup WBS: padre = promedio de
    # hijos, general = promedio de los WBS de nivel más alto).
    _rollup_progress = compute_plan_rollup_progress(all_tasks)
    avg_progress = (
        round_half_up(_rollup_progress) if _rollup_progress is not None else 0
    )

    # Hitos
    milestones = [t for t in all_tasks if t.is_milestone]
    period_start = cut_off_date - timedelta(days=window_days)

    # ENH-064: foco en hitos / críticas / retrasadas.
    n_milestones = len(milestones)
    n_critical = sum(1 for t in all_tasks if _is_critical_task(t))
    n_delayed = sum(1 for t in all_tasks if _is_delayed(t, cut_off_date))
    priority_summary = {
        "milestones": n_milestones,
        "critical": n_critical,
        "delayed": n_delayed,
    }
    focus_tasks = prioritize_tasks(all_tasks, cut_off_date, top_n=20)
    milestones_done = sorted(
        [
            t
            for t in milestones
            if (t.status == "completed" or (t.progress or 0) >= 100)
            and t.end_date is not None
            and period_start <= t.end_date <= cut_off_date
        ],
        key=lambda t: t.end_date or date.min,
    )
    # ENH-082: cota superior del listado de hitos próximos = mismo
    # window_days que el resto del reporte (antes era ilimitado, lo que
    # mostraba hitos a meses de distancia aunque el user pidiera 1 mes).
    upcoming_end = cut_off_date + timedelta(days=window_days)
    milestones_upcoming = sorted(
        [
            t
            for t in milestones
            if t.status != "completed"
            and (t.progress or 0) < 100
            and t.end_date is not None
            and cut_off_date <= t.end_date <= upcoming_end
        ],
        key=lambda t: (t.end_date or date.max),
    )[:10]

    # Riesgos top
    risk_rows = (
        await db.execute(
            select(Risk)
            .where(
                Risk.tenant_id == str(tenant_id),
                Risk.project_id == str(project_id),
                Risk.deleted_at.is_(None),
                Risk.status != "resolved",  # US-179: terminal unificado.
            )
            .order_by(Risk.severity.desc().nullslast() if hasattr(Risk.severity, "nullslast") else Risk.severity.desc())
            .limit(5)
        )
    ).scalars().all()

    # AIDs abiertas
    aid_rows = (
        await db.execute(
            select(Issue)
            .where(
                Issue.tenant_id == str(tenant_id),
                Issue.project_id == str(project_id),
                Issue.deleted_at.is_(None),
                Issue.status != "resolved",  # US-179: terminal unificado.
            )
            .limit(15)
        )
    ).scalars().all()
    # Resolver nombres de owners
    owner_ids = {i.owner_id for i in aid_rows if i.owner_id}
    owner_map: dict[str, str] = {}
    if owner_ids:
        rows = (
            await db.execute(
                select(User.id, User.full_name).where(User.id.in_(owner_ids))
            )
        ).all()
        owner_map = {str(uid): (name or "—") for uid, name in rows}

    # ENH-082: resolver área para hitos / risks / issues. Una sola
    # query batch sobre todas las area_ids referenciadas.
    area_ids: set[str] = set()
    for t in milestones_upcoming:
        if t.area_id:
            area_ids.add(str(t.area_id))
    for r in risk_rows:
        if r.area_id:
            area_ids.add(str(r.area_id))
    for i in aid_rows:
        if i.area_id:
            area_ids.add(str(i.area_id))
    area_map: dict[str, str] = {}
    if area_ids:
        arows = (
            await db.execute(
                select(Area.id, Area.name).where(Area.id.in_(area_ids))
            )
        ).all()
        area_map = {str(aid): (name or "—") for aid, name in arows}

    def _area_name(aid) -> str:
        return area_map.get(str(aid), "—") if aid else "—"

    # ENH-082: orden definitivo. Issues: due asc nullslast, priority desc.
    aid_rows = sorted(
        aid_rows,
        key=lambda i: (
            (i.committed_date or date.max),
            -(i.priority or 0),
        ),
    )
    # ENH-082: hitos próximos ya están ordenados por end_date; estabilizamos
    # por área para el caso de empates en fecha.
    milestones_upcoming = sorted(
        milestones_upcoming,
        key=lambda t: (t.end_date or date.max, _area_name(t.area_id)),
    )

    # Cambios en revisión
    changes_in_review = (
        await db.execute(
            select(ChangeRequest).where(
                ChangeRequest.tenant_id == str(tenant_id),
                ChangeRequest.project_id == str(project_id),
                ChangeRequest.deleted_at.is_(None),
                ChangeRequest.status == "in_review",
            )
        )
    ).scalars().all()

    # US-087: KPIs estructurados del período. Campos sin datos quedan
    # en None y la plantilla los oculta.
    kpis_period_start = default_period_start(cut_off_date)
    kpis = await compute_kpis(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        period_start=kpis_period_start,
        period_end=cut_off_date,
    )

    # ENH-063: etiqueta legible del período para el header.
    period_label = _period_label(window_days)
    return {
        "title": f"Reporte de Avance — {project.folio} ({period_label})",
        "cut_off_date": cut_off_date.isoformat(),
        "period_days": window_days,
        "period_label": period_label,
        "period_start": period_start.isoformat(),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        # ENH-064: resumen + focus tasks (top 20 prioritizadas).
        "priority_summary": priority_summary,
        "focus_tasks": [
            {
                "wbs_code": t.wbs_code,
                "name": t.name,
                "is_milestone": bool(t.is_milestone),
                "criticality": getattr(t, "criticality", None),
                # ENH-097: boolean explicito expuesto en el payload (paralelo al enum).
                "is_critical": bool(getattr(t, "is_critical", False)),
                "status": t.status,
                "end_date": t.end_date.isoformat() if t.end_date else None,
                "progress": t.progress or 0,
                "delayed": _is_delayed(t, cut_off_date),
                # ENH-071: campos para filtrado en el endpoint de reportes IA.
                "area_id": str(t.area_id) if t.area_id else None,
                "assignee_actor_id": (
                    str(t.assignee_actor_id) if t.assignee_actor_id else None
                ),
            }
            for t in focus_tasks
        ],
        "kpis": kpis,
        "kpis_visible": kpis_have_any_value(kpis),
        "project": {
            "id": str(project.id),
            "folio": project.folio,
            "name": project.name,
            "description": project.description,
            "phase": project.phase,
            "health_status": project.health_status,
            "type": project.type,
            "priority": project.priority,
            "organization_name": org,
            "program_name": prog,
            "pm_name": pm["full_name"] if pm else None,
            "pm_email": pm["email"] if pm else None,
            "sponsor": project.sponsor,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "budget": float(project.budget or 0),
            "actual_budget": float(project.actual_budget or 0),
            # ENH-109 — avance derivado del plan; manual como fallback sin plan.
            "progress": avg_progress if total_tasks > 0 else (project.progress or 0),
        },
        "plan": {
            "total_tasks": total_tasks,
            "done": done,
            "in_progress": in_progress,
            "not_started": not_started,
            "avg_progress": avg_progress,
        },
        "milestones_done": [
            {
                "name": t.name,
                "end_date": t.end_date.isoformat() if t.end_date else None,
                "progress": t.progress or 0,
            }
            for t in milestones_done
        ],
        "milestones_upcoming": [
            {
                "name": t.name,
                "end_date": t.end_date.isoformat() if t.end_date else None,
                "progress": t.progress or 0,
                # ENH-082: área responsable, status y delayed flag.
                "area_name": _area_name(t.area_id),
                "status": t.status,
                "delayed": _is_delayed(t, cut_off_date),
            }
            for t in milestones_upcoming
        ],
        "top_risks": [
            {
                "folio": r.folio,
                "title": r.title,
                "severity": r.severity,
                "status": r.status,
                "probability": r.probability,
                "impact": r.impact,
                "mitigation_strategy": r.mitigation_strategy,
                # ENH-082: área + due_date.
                "area_name": _area_name(r.area_id),
                "due_date": r.due_date.isoformat() if r.due_date else None,
            }
            for r in risk_rows
        ],
        "open_aids": [
            {
                "folio": i.folio,
                "title": i.title,
                "type": i.type,
                "status": i.status,
                "priority": i.priority,
                "committed_date": i.committed_date.isoformat() if i.committed_date else None,
                "owner_name": owner_map.get(str(i.owner_id), "—") if i.owner_id else "—",
                # ENH-082: área responsable como fallback cuando no hay owner.
                "area_name": _area_name(i.area_id),
                "overdue": bool(
                    i.committed_date
                    and i.committed_date < cut_off_date
                    and i.status not in ("resolved", "closed")
                ),
            }
            for i in aid_rows
        ],
        "changes_in_review": len(changes_in_review),
    }


async def build_seguimiento_context(
    db: AsyncSession,
    tenant_id: UUID,
    project_id: UUID,
    cut_off_date: date,
    window_days: int = 14,
) -> dict[str, Any]:
    """Contexto para Reporte de Seguimiento (acciones por responsable).

    Reparte las tareas del plan (no cerradas) en: vencidas, en curso
    (dentro de la ventana anterior) y próximas (dentro de la ventana
    siguiente). ENH-154: las AIDs tipo `action` abiertas ya no se mezclan
    en esos buckets; se listan completas en su propia sección "Acciones"
    (`groups_actions`). Dentro de cada bloque agrupa por área.
    """
    project = await _get_project(db, tenant_id, project_id)
    window_end = cut_off_date + timedelta(days=window_days)
    window_start = cut_off_date - timedelta(days=window_days)

    pm = await _user(db, project.pm_id)

    task_rows = (
        await db.execute(
            select(Task).where(
                Task.project_id == str(project_id),
                Task.status.notin_(["completed", "cancelled"]),
            )
        )
    ).scalars().all()
    action_rows = (
        await db.execute(
            select(Issue).where(
                Issue.tenant_id == str(tenant_id),
                Issue.project_id == str(project_id),
                Issue.deleted_at.is_(None),
                Issue.type == "action",
                Issue.status.notin_(["resolved", "closed"]),
            )
        )
    ).scalars().all()

    owner_ids: set = {t.owner_id for t in task_rows if t.owner_id}
    owner_ids |= {a.owner_id for a in action_rows if a.owner_id}
    owner_map: dict[str, str] = {"unassigned": "Sin responsable"}
    if owner_ids:
        rows = (
            await db.execute(
                select(User.id, User.full_name).where(User.id.in_(owner_ids))
            )
        ).all()
        for uid, name in rows:
            owner_map[str(uid)] = name or "—"

    # ENH-083: agrupamos por área (no por owner). Resolver area_id → name
    # con una sola query batch.
    area_ids: set = {t.area_id for t in task_rows if t.area_id}
    area_ids |= {a.area_id for a in action_rows if a.area_id}
    area_map: dict[str, str] = {}
    if area_ids:
        arows = (
            await db.execute(
                select(Area.id, Area.name).where(Area.id.in_(area_ids))
            )
        ).all()
        area_map = {str(aid): (name or "—") for aid, name in arows}

    unassigned_area = "Sin área asignada"

    def _area_label(area_id) -> str:
        return area_map.get(str(area_id), unassigned_area) if area_id else unassigned_area

    items: list[dict[str, Any]] = []
    for t in task_rows:
        due = t.end_date
        items.append({
            "source": "task",
            "folio": t.wbs_code,
            "title": t.name,
            "status": t.status,
            "due_date": due.isoformat() if due else None,
            "owner_name": owner_map.get(str(t.owner_id), "—") if t.owner_id else "—",
            "area_name": _area_label(t.area_id),
            "progress": t.progress or 0,
            "overdue_days": (cut_off_date - due).days if due and due < cut_off_date else 0,
        })
    # ENH-154: las acciones (AID type=action) dejan de mezclarse con las
    # tareas en los buckets de Actividades; van a su propia sección
    # "Acciones" con TODAS las abiertas (sin filtro de ventana).
    actions_items: list[dict[str, Any]] = []
    for a in action_rows:
        due = a.committed_date
        actions_items.append({
            "source": "action",
            "folio": a.folio,
            "title": a.title,
            "status": a.status,
            "due_date": due.isoformat() if due else None,
            "owner_name": owner_map.get(str(a.owner_id), "—") if a.owner_id else "—",
            "area_name": _area_label(a.area_id),
            "progress": None,
            "overdue_days": (cut_off_date - due).days if due and due < cut_off_date else 0,
        })

    overdue = [i for i in items if i["due_date"] and i["overdue_days"] > 0]
    in_progress = [
        i
        for i in items
        if i["due_date"]
        and window_start.isoformat() <= i["due_date"] <= cut_off_date.isoformat()
        and i["overdue_days"] == 0
    ]
    upcoming = [
        i
        for i in items
        if i["due_date"]
        and cut_off_date.isoformat() < i["due_date"] <= window_end.isoformat()
    ]

    def group(arr: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # ENH-083: agrupar por área; "Sin área asignada" siempre al final.
        # Items dentro de cada bloque ordenados por fecha asc.
        buckets: dict[str, list[dict[str, Any]]] = {}
        for it in arr:
            buckets.setdefault(it["area_name"], []).append(it)
        return [
            {
                "area_name": k,
                "rows": sorted(
                    v, key=lambda x: (x["due_date"] or "", x["title"] or "")
                ),
            }
            for k, v in sorted(
                buckets.items(),
                key=lambda kv: (kv[0] == unassigned_area, kv[0]),
            )
        ]

    period_label = _period_label(window_days)
    return {
        "title": f"Reporte de Seguimiento — {project.folio} ({period_label})",
        "cut_off_date": cut_off_date.isoformat(),
        "window_days": window_days,
        "period_days": window_days,
        "period_label": period_label,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "project": {
            "id": str(project.id),
            "folio": project.folio,
            "name": project.name,
            "phase": project.phase,
            "health_status": project.health_status,
            "pm_name": pm["full_name"] if pm else None,
        },
        "counts": {
            "overdue": len(overdue),
            "in_progress": len(in_progress),
            "upcoming": len(upcoming),
            "total": len(overdue) + len(in_progress) + len(upcoming),
        },
        "groups_overdue": group(overdue),
        "groups_in_progress": group(in_progress),
        "groups_upcoming": group(upcoming),
        "groups_actions": group(actions_items),
    }


# US-147 — Reporte Look-ahead: solo actividades en ventana [hoy, hoy+ventana].
async def build_look_ahead_context(
    db: AsyncSession,
    tenant_id: UUID,
    project_id: UUID,
    window_value: int,
    window_unit: str,
) -> dict[str, Any]:
    """Contexto para Reporte Look-ahead.

    Selecciona tasks cuyo `start_date` o `end_date` cae dentro de
    `[hoy, hoy+ventana]`. Excluye las que ya están vencidas
    (`end_date < hoy`). Sin agrupar por área ni responsable — un
    listado plano ordenado por end_date asc, start_date asc.

    Args:
        window_value: número de unidades de ventana hacia adelante.
        window_unit: "days" | "weeks" | "months".
    """
    project = await _get_project(db, tenant_id, project_id)
    today = datetime.now(UTC).date()
    multipliers = {"days": 1, "weeks": 7, "months": 30}
    if window_unit not in multipliers:
        raise ValueError(f"window_unit invalid: {window_unit!r}")
    days = window_value * multipliers[window_unit]
    window_end = today + timedelta(days=days)

    all_tasks = (
        await db.execute(
            select(Task).where(
                Task.tenant_id == str(tenant_id),
                Task.project_id == str(project_id),
            )
        )
    ).scalars().all()

    in_window: list[dict[str, Any]] = []
    for t in all_tasks:
        # Excluye vencidas (end_date < hoy).
        if t.end_date is not None and t.end_date < today:
            continue
        starts_in = (
            t.start_date is not None and today <= t.start_date <= window_end
        )
        ends_in = (
            t.end_date is not None and today <= t.end_date <= window_end
        )
        if not (starts_in or ends_in):
            continue
        in_window.append({
            "id": str(t.id),
            "wbs_code": t.wbs_code,
            "name": t.name,
            # Serializa fechas a ISO string para que `sections` (JSONB)
            # sea persistible sin custom encoder.
            "start_date": t.start_date.isoformat() if t.start_date else None,
            "end_date": t.end_date.isoformat() if t.end_date else None,
            "progress": t.progress or 0,
            "status": t.status,
            "is_milestone": t.is_milestone,
            "is_critical": bool(t.is_critical),
        })

    in_window.sort(
        key=lambda r: (
            r["end_date"] or "9999-12-31",
            r["start_date"] or "9999-12-31",
        )
    )

    unit_label = {"days": "días", "weeks": "semanas", "months": "meses"}[window_unit]
    window_label = f"{window_value} {unit_label} ({today.isoformat()} → {window_end.isoformat()})"

    return {
        "project": {
            "id": str(project.id),
            "folio": project.folio,
            "name": project.name,
        },
        "window_value": window_value,
        "window_unit": window_unit,
        "window_label": window_label,
        "period_start": today.isoformat(),
        "period_end": window_end.isoformat(),
        "tasks": in_window,
    }
