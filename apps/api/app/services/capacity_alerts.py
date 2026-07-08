"""US-184 — Alertas de capacidad (Revamp 1.0).

Reglas (diseño socio 2026-07-08, decisiones owner):
1. ``capacity_overload`` — recurso sobreasignado (demanda > capacidad +
   umbral rojo) en la ventana de 30 días (cubre "pico en las próximas
   2-4 semanas": la ventana month incluye asignaciones futuras).
2. ``capacity_key_resource_risk`` — recurso CLAVE con asignación activa
   en ≥3 proyectos amarillos/rojos.
3. ``capacity_solo_specialist`` — recurso marcado NO compartido
   (`is_shared_resource=false`) con >1 proyecto activo.

Destinatarios: los PMs de los proyectos afectados (audiencia accionable).
Canal: in-app (EP011); sin email por default para no hacer spam.
Dedupe: no se repite la misma alerta (tipo + actor) dentro de 7 días.

Triggers:
- Sweep semanal desde el snapshot job (analytics/snapshots.snapshot_tenant).
- Evaluación puntual del actor al crear/editar una participation con FTE%
  (fast-path en project_directory).
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.project import Project
from app.models.tenant import Tenant
from app.services.capacity import (
    _load_assignments,
    resource_capacity_summary,
    window_range,
)
from app.services.notifications import enqueue_notification

CAPACITY_OVERLOAD = "capacity_overload"
CAPACITY_KEY_RESOURCE_RISK = "capacity_key_resource_risk"
CAPACITY_SOLO_SPECIALIST = "capacity_solo_specialist"

DEDUPE_DAYS = 7
RESOURCES_LINK = "/pmo/resources"


async def _recent_alert_exists(
    db: AsyncSession, tenant_id: str, type_: str, actor_id: str
) -> bool:
    cutoff = datetime.now(UTC) - timedelta(days=DEDUPE_DAYS)
    count = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.tenant_id == tenant_id,
                Notification.type == type_,
                Notification.entity_type == "actor",
                Notification.entity_id == actor_id,
                Notification.created_at >= cutoff,
            )
        )
    ).scalar_one()
    return bool(count)


async def _pm_ids_for_projects(db: AsyncSession, project_ids: list[str]) -> list[str]:
    if not project_ids:
        return []
    rows = (
        await db.execute(
            select(Project.pm_id).where(Project.id.in_(project_ids))
        )
    ).scalars().all()
    return sorted({str(pm) for pm in rows if pm})


async def _emit(
    db: AsyncSession,
    tenant_id: str,
    *,
    type_: str,
    actor_id: str,
    title: str,
    body: str,
    project_ids: list[str],
    meta: dict,
) -> int:
    if await _recent_alert_exists(db, tenant_id, type_, actor_id):
        return 0
    recipients = await _pm_ids_for_projects(db, project_ids)
    sent = 0
    for uid in recipients:
        await enqueue_notification(
            db,
            tenant_id=tenant_id,
            user_id=uid,
            type=type_,
            title=title,
            body=body,
            entity_type="actor",
            entity_id=actor_id,
            link=RESOURCES_LINK,
            meta=meta,
            send_email=False,
        )
        sent += 1
    return sent


async def sweep_capacity_alerts(
    db: AsyncSession, tenant: Tenant, *, today: date | None = None
) -> int:
    """Evalúa las 3 reglas sobre todo el tenant. Devuelve # notifs creadas.
    NO hace commit (el caller agrupa con su transacción)."""
    tenant_id = str(tenant.id)
    summary = await resource_capacity_summary(db, tenant, window="month", today=today)
    resources = summary["resources"]
    if not resources:
        return 0

    overloaded = {r["actor_id"]: r for r in resources if r["color"] == "red"}
    key_resources = {r["actor_id"]: r for r in resources if r["is_key_resource"]}
    solo = {
        r["actor_id"]: r
        for r in resources
        if not r["is_shared_resource"] and r["projects_count"] > 1
    }
    watched = sorted({*overloaded, *key_resources, *solo})
    if not watched:
        return 0

    start, end = window_range("month", today)
    rows = await _load_assignments(db, tenant_id, start, end, actor_ids=watched)
    projects_by_actor: dict[str, list] = {}
    for r in rows:
        if r.status == "activa":
            projects_by_actor.setdefault(str(r.actor_id), []).append(r)

    created = 0
    for actor_id, res in overloaded.items():
        pids = sorted({str(r.project_id) for r in projects_by_actor.get(actor_id, [])})
        created += await _emit(
            db, tenant_id,
            type_=CAPACITY_OVERLOAD, actor_id=actor_id,
            title=f"Recurso sobreasignado: {res['name']}",
            body=(
                f"{res['name']} tiene {res['demand_pct']:.0f}% asignado contra "
                f"{res['capacity_pct']:.0f}% de capacidad para proyectos en los "
                f"próximos 30 días ({res['projects_count']} proyectos)."
            ),
            project_ids=pids,
            meta={"demand_pct": res["demand_pct"], "capacity_pct": res["capacity_pct"],
                  "window": "month"},
        )

    for actor_id, res in key_resources.items():
        troubled = sorted({
            str(r.project_id)
            for r in projects_by_actor.get(actor_id, [])
            if r.project_health in ("yellow", "red")
        })
        if len(troubled) < 3:
            continue
        created += await _emit(
            db, tenant_id,
            type_=CAPACITY_KEY_RESOURCE_RISK, actor_id=actor_id,
            title=f"Recurso clave en {len(troubled)} proyectos en riesgo: {res['name']}",
            body=(
                f"{res['name']} es recurso clave y participa en {len(troubled)} "
                "proyectos amarillos/rojos. Revisar prioridades en la vista de Recursos."
            ),
            project_ids=troubled,
            meta={"troubled_projects": len(troubled)},
        )

    for actor_id, res in solo.items():
        pids = sorted({str(r.project_id) for r in projects_by_actor.get(actor_id, [])})
        created += await _emit(
            db, tenant_id,
            type_=CAPACITY_SOLO_SPECIALIST, actor_id=actor_id,
            title=f"Dependencia de especialista único: {res['name']}",
            body=(
                f"{res['name']} está marcado como recurso NO compartido pero "
                f"participa en {res['projects_count']} proyectos activos."
            ),
            project_ids=pids,
            meta={"projects_count": res["projects_count"]},
        )
    return created


async def alert_actor_if_overloaded(
    db: AsyncSession, tenant: Tenant | None, actor_id: str
) -> int:
    """Fast-path al escribir una participation con FTE%: si el actor quedó
    sobreasignado (ventana 30 días) dispara la alerta 1 (con dedupe).
    NO hace commit."""
    if tenant is None:
        return 0
    summary = await resource_capacity_summary(db, tenant, window="month")
    res = next(
        (r for r in summary["resources"] if r["actor_id"] == str(actor_id)), None
    )
    if not res or res["color"] != "red":
        return 0
    start, end = window_range("month")
    rows = await _load_assignments(
        db, str(tenant.id), start, end, actor_ids=[str(actor_id)]
    )
    pids = sorted({str(r.project_id) for r in rows if r.status == "activa"})
    return await _emit(
        db, str(tenant.id),
        type_=CAPACITY_OVERLOAD, actor_id=str(actor_id),
        title=f"Recurso sobreasignado: {res['name']}",
        body=(
            f"{res['name']} tiene {res['demand_pct']:.0f}% asignado contra "
            f"{res['capacity_pct']:.0f}% de capacidad para proyectos."
        ),
        project_ids=pids,
        meta={"demand_pct": res["demand_pct"], "capacity_pct": res["capacity_pct"],
              "window": "month"},
    )
