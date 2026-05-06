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
from app.models.modules import ChangeRequest, Issue, Risk
from app.models.organization import Organization, Program
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.services.report_kpis import (
    compute_kpis,
    default_period_start,
    kpis_have_any_value,
)


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
    done = sum(1 for t in all_tasks if t.status == "done" or (t.progress or 0) >= 100)
    in_progress = sum(1 for t in all_tasks if t.status == "in_progress")
    not_started = sum(1 for t in all_tasks if t.status == "not_started")
    avg_progress = (
        round(sum((t.progress or 0) for t in all_tasks) / total_tasks)
        if total_tasks > 0
        else 0
    )

    # Hitos
    milestones = [t for t in all_tasks if t.is_milestone]
    period_start = cut_off_date - timedelta(days=window_days)
    milestones_done = sorted(
        [
            t
            for t in milestones
            if (t.status == "done" or (t.progress or 0) >= 100)
            and t.end_date is not None
            and period_start <= t.end_date <= cut_off_date
        ],
        key=lambda t: t.end_date or date.min,
    )
    milestones_upcoming = sorted(
        [
            t
            for t in milestones
            if t.status != "done" and (t.progress or 0) < 100 and t.end_date is not None and t.end_date >= cut_off_date
        ],
        key=lambda t: t.end_date or date.max,
    )[:10]

    # Riesgos top
    risk_rows = (
        await db.execute(
            select(Risk)
            .where(
                Risk.tenant_id == str(tenant_id),
                Risk.project_id == str(project_id),
                Risk.deleted_at.is_(None),
                Risk.status.notin_(["closed", "materialized"]),
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
                Issue.status.notin_(["resolved", "closed"]),
            )
            .order_by(Issue.priority.desc().nullslast() if hasattr(Issue.priority, "nullslast") else Issue.priority.desc())
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
            "progress": project.progress or 0,
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

    Unifica tareas del plan (no cerradas) y AIDs tipo `action` abiertas,
    y las reparte en: vencidas, en curso (dentro de la ventana anterior)
    y próximas (dentro de la ventana siguiente). Dentro de cada bucket
    agrupa por responsable.
    """
    project = await _get_project(db, tenant_id, project_id)
    window_end = cut_off_date + timedelta(days=window_days)
    window_start = cut_off_date - timedelta(days=window_days)

    pm = await _user(db, project.pm_id)

    task_rows = (
        await db.execute(
            select(Task).where(
                Task.project_id == str(project_id),
                Task.status.notin_(["done", "cancelled"]),
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

    items: list[dict[str, Any]] = []
    for t in task_rows:
        due = t.end_date
        items.append({
            "source": "task",
            "folio": t.wbs,
            "title": t.name,
            "status": t.status,
            "due_date": due.isoformat() if due else None,
            "owner_key": str(t.owner_id) if t.owner_id else "unassigned",
            "progress": t.progress or 0,
            "overdue_days": (cut_off_date - due).days if due and due < cut_off_date else 0,
        })
    for a in action_rows:
        due = a.committed_date
        items.append({
            "source": "action",
            "folio": a.folio,
            "title": a.title,
            "status": a.status,
            "due_date": due.isoformat() if due else None,
            "owner_key": str(a.owner_id) if a.owner_id else "unassigned",
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
        buckets: dict[str, list[dict[str, Any]]] = {}
        for it in arr:
            buckets.setdefault(it["owner_key"], []).append(it)
        return [
            {
                "owner_name": owner_map.get(k, "—"),
                "owner_key": k,
                "rows": sorted(
                    v, key=lambda x: (x["due_date"] or "", x["title"] or "")
                ),
            }
            for k, v in sorted(
                buckets.items(),
                key=lambda kv: (kv[0] == "unassigned", owner_map.get(kv[0], "")),
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
    }
