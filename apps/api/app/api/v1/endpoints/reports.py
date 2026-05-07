"""Project Reports — CRUD y listado (US-022, EP006).

Complementa al draft-con-IA existente en `/ai/projects/{id}/reports/draft`
(EP008) con CRUD manual y un listado paginable por proyecto.
"""
import re
from datetime import UTC, date, datetime
from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.ai import Report
from app.models.project import Project
from app.models.report_history import ReportHistory
from app.services.audit import write_audit
from app.services.operational_reports import (
    build_avance_context,
    build_seguimiento_context,
)
from app.services.pdf_renderer import render_pdf

router = APIRouter(tags=["reports"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


async def _get_project(db: AsyncSession, tenant_id: UUID, project_id: UUID) -> Project:
    p = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id), Project.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")
    return p


ReportPeriod = Literal["daily", "weekly", "monthly"]
ReportStatus = Literal["draft", "sent"]


DEFAULT_SECTIONS = {
    "resumen_ejecutivo": "",
    "avance_plan": "",
    "acciones_pendientes": "",
    "decisiones_requeridas": "",
    "riesgos_top": "",
}


class ReportCreate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    period: ReportPeriod | None = None
    recipients: list[EmailStr] = []
    sections: dict[str, str] | None = None


class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    period: ReportPeriod | None = None
    recipients: list[EmailStr] | None = None
    sections: dict[str, str] | None = None


class ReportRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    period: str | None
    status: str
    recipients: list[str]
    sections: dict
    generated_by_ai: bool
    generator: str = "manual"
    cut_off_date: date | None = None
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/projects/{project_id}/reports", response_model=list[ReportRead])
async def list_reports(
    project_id: UUID,
    status: str | None = Query(default=None),
    period: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, tenant_id, project_id)
    stmt = (
        select(Report)
        .where(Report.tenant_id == str(tenant_id), Report.project_id == str(project_id))
        .order_by(Report.created_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(Report.status == status)
    if period:
        stmt = stmt.where(Report.period == period)
    rows = (await db.execute(stmt)).scalars().all()
    return [ReportRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/reports",
    response_model=ReportRead,
    status_code=201,
)
async def create_report(
    project_id: UUID,
    body: ReportCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Crea un reporte manual (borrador). Secciones pre-llenadas con las
    sugeridas en US-022 si no se envían."""
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)

    default_title = (
        f"Reporte {project.folio} — "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}"
    )
    rep = Report(
        tenant_id=str(tenant_id),
        project_id=str(project.id),
        title=body.title or default_title,
        period=body.period,
        sections=body.sections or dict(DEFAULT_SECTIONS),
        recipients=[str(e) for e in body.recipients],
        status="draft",
        generated_by_ai=False,
        created_by=cu.id,
    )
    db.add(rep)
    await db.flush()
    await write_audit(
        db,
        action="report.create",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report",
        entity_id=str(rep.id),
        details={"period": body.period},
    )
    await db.commit()
    return ReportRead.model_validate(rep)


@router.get("/reports/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id), Report.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    return ReportRead.model_validate(rep)


@router.patch("/reports/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: UUID,
    body: ReportUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id), Report.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    if rep.status == "sent":
        from app.core.errors import business_rule

        raise business_rule("Un reporte enviado no puede editarse")
    data = body.model_dump(exclude_unset=True)
    if "recipients" in data and data["recipients"] is not None:
        data["recipients"] = [str(e) for e in data["recipients"]]
    for field, value in data.items():
        setattr(rep, field, value)
    await write_audit(
        db,
        action="report.update",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report",
        entity_id=str(rep.id),
    )
    await db.commit()
    return ReportRead.model_validate(rep)


# ---- EP014 US-038/039: reportes ejecutables sin IA ----

class AvanceGenerate(BaseModel):
    cut_off_date: date | None = None
    # ENH-063: período canónico para filtrar contenido del reporte.
    # 1 / 7 / 14 / 30 / 90 días. Default 7 (1 semana).
    period_days: int | None = Field(default=None, ge=1, le=365)


class SeguimientoGenerate(BaseModel):
    cut_off_date: date | None = None
    window_days: int = Field(default=14, ge=1, le=90)
    # ENH-063: alias canónico que sobrescribe window_days si viene.
    period_days: int | None = Field(default=None, ge=1, le=365)


# ENH-063: ventana default cuando el caller no especifica.
_DEFAULT_PERIOD_DAYS = 7


def _sanitize_filename_part(value: str) -> str:
    """Replace whitespace with underscore and strip forbidden filename chars."""
    cleaned = re.sub(r"\s+", "_", value.strip())
    cleaned = re.sub(r"[\\/:*?\"<>|]", "", cleaned)
    return cleaned or "sin_nombre"


def _report_filename(tipo: str, project_name: str, ts: datetime) -> str:
    """Build filename per ENH-014: `Reporte de {Tipo} - {Nombre} - {datetime}.pdf`."""
    safe_name = _sanitize_filename_part(project_name)
    stamp = ts.strftime("%Y-%m-%d_%H-%M-%S")
    return f"Reporte de {tipo} - {safe_name} - {stamp}.pdf"


def _pdf_response(pdf: bytes, filename: str, *, inline: bool = False) -> Response:
    disposition_type = "inline" if inline else "attachment"
    ascii_fallback = (
        filename.encode("ascii", "replace").decode("ascii").replace("?", "_")
    )
    encoded = quote(filename)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'{disposition_type}; filename="{ascii_fallback}"; '
                f"filename*=UTF-8''{encoded}"
            )
        },
    )


async def _tenant_name(db: AsyncSession, tenant_id: UUID) -> str | None:
    from app.models.tenant import Tenant

    return (
        await db.execute(select(Tenant.name).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()


@router.post("/projects/{project_id}/reports/avance")
async def generate_avance_report(
    project_id: UUID,
    body: AvanceGenerate | None = None,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Genera Reporte de Avance (Python, sin IA). Devuelve el PDF y guarda
    un row en `reports` con generator='avance' + snapshot del contexto."""
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    cut_off = (body.cut_off_date if body else None) or datetime.now(UTC).date()
    # ENH-063: período → window_days. Default 7d (1 semana).
    window_days = (
        (body.period_days if body and body.period_days else None)
        or _DEFAULT_PERIOD_DAYS
    )

    context = await build_avance_context(
        db, tenant_id, project.id, cut_off, window_days=window_days
    )
    context["tenant_name"] = await _tenant_name(db, tenant_id)

    pdf = render_pdf("reports/avance.html", context)

    rep = Report(
        tenant_id=str(tenant_id),
        project_id=str(project.id),
        title=f"Reporte de Avance — {project.folio} — {cut_off.isoformat()}",
        period=None,
        generator="avance",
        cut_off_date=cut_off,
        sections=context,
        recipients=[],
        status="draft",
        generated_by_ai=False,
        created_by=cu.id,
    )
    db.add(rep)
    await db.flush()
    # US-092: registrar en historial de reportes generados.
    db.add(
        ReportHistory(
            tenant_id=str(tenant_id),
            project_id=str(project.id),
            report_type="avance",
            generated_by_user_id=str(cu.id),
            source_report_id=str(rep.id),
            file_size_bytes=len(pdf) if pdf else None,
        )
    )
    await write_audit(
        db,
        action="report.generate.avance",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report",
        entity_id=str(rep.id),
        details={"cut_off_date": cut_off.isoformat()},
    )
    await db.commit()

    filename = _report_filename("Avance", project.name, datetime.now(UTC))
    return _pdf_response(pdf, filename)


@router.get("/reports/{report_id}/avance/download")
async def download_avance_report(
    report_id: UUID,
    inline: bool = Query(default=False),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Re-descarga un Reporte de Avance previamente generado (usa
    contexto persistido en `sections`). Con `?inline=true` devuelve
    `Content-Disposition: inline` para preview en el navegador (ENH-014)."""
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id),
                Report.tenant_id == str(tenant_id),
                Report.generator == "avance",
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    ctx = dict(rep.sections or {})
    ctx["tenant_name"] = await _tenant_name(db, tenant_id)
    pdf = render_pdf("reports/avance.html", ctx)
    project = await _get_project(db, tenant_id, UUID(rep.project_id))
    stamp = rep.created_at if rep.created_at else datetime.now(UTC)
    filename = _report_filename("Avance", project.name, stamp)
    return _pdf_response(pdf, filename, inline=inline)


@router.post("/projects/{project_id}/reports/seguimiento")
async def generate_seguimiento_report(
    project_id: UUID,
    body: SeguimientoGenerate | None = None,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Reporte de Seguimiento (Python, sin IA). Ver US-039."""
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    cut_off = (body.cut_off_date if body else None) or datetime.now(UTC).date()
    # ENH-063: period_days (canónico) > window_days (legacy) > default.
    if body and body.period_days:
        window_days = body.period_days
    else:
        window_days = (body.window_days if body else 14) or 14

    context = await build_seguimiento_context(
        db, tenant_id, project.id, cut_off, window_days=window_days,
    )
    context["tenant_name"] = await _tenant_name(db, tenant_id)
    pdf = render_pdf("reports/seguimiento.html", context)

    rep = Report(
        tenant_id=str(tenant_id),
        project_id=str(project.id),
        title=f"Reporte de Seguimiento — {project.folio} — {cut_off.isoformat()}",
        period=None,
        generator="seguimiento",
        cut_off_date=cut_off,
        sections=context,
        recipients=[],
        status="draft",
        generated_by_ai=False,
        created_by=cu.id,
    )
    db.add(rep)
    await db.flush()
    # US-092: registrar en historial.
    db.add(
        ReportHistory(
            tenant_id=str(tenant_id),
            project_id=str(project.id),
            report_type="seguimiento",
            generated_by_user_id=str(cu.id),
            source_report_id=str(rep.id),
            file_size_bytes=len(pdf) if pdf else None,
        )
    )
    await write_audit(
        db,
        action="report.generate.seguimiento",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report",
        entity_id=str(rep.id),
        details={"cut_off_date": cut_off.isoformat(), "window_days": window_days},
    )
    await db.commit()

    filename = _report_filename("Seguimiento", project.name, datetime.now(UTC))
    return _pdf_response(pdf, filename)


@router.get("/reports/{report_id}/seguimiento/download")
async def download_seguimiento_report(
    report_id: UUID,
    inline: bool = Query(default=False),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id),
                Report.tenant_id == str(tenant_id),
                Report.generator == "seguimiento",
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    ctx = dict(rep.sections or {})
    ctx["tenant_name"] = await _tenant_name(db, tenant_id)
    pdf = render_pdf("reports/seguimiento.html", ctx)
    project = await _get_project(db, tenant_id, UUID(rep.project_id))
    stamp = rep.created_at if rep.created_at else datetime.now(UTC)
    filename = _report_filename("Seguimiento", project.name, stamp)
    return _pdf_response(pdf, filename, inline=inline)


@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id), Report.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    if rep.status == "sent":
        from app.core.errors import business_rule

        raise business_rule("Un reporte enviado no puede eliminarse")
    await db.delete(rep)
    await write_audit(
        db,
        action="report.delete",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report",
        entity_id=str(report_id),
    )
    await db.commit()
    return Response(status_code=204)


# ============================================================================
# US-092 — Historial de reportes generados.
# ============================================================================

class ReportHistoryRead(BaseModel):
    id: UUID
    project_id: UUID
    report_type: str
    generated_at: datetime
    generated_by_user_id: UUID | None
    file_size_bytes: int | None
    scheduled_report_id: UUID | None
    source_report_id: UUID | None
    # Embedded mini para que la UI muestre nombre del autor sin extra
    # request a /users.
    generated_by_name: str | None = None

    model_config = {"from_attributes": True}


@router.get(
    "/projects/{project_id}/report-history",
    response_model=list[ReportHistoryRead],
)
async def list_report_history(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-092: lista paginada (50 por default) ordenada `generated_at DESC`."""
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    rows = (
        await db.execute(
            select(ReportHistory)
            .where(
                ReportHistory.tenant_id == str(tenant_id),
                ReportHistory.project_id == str(project.id),
            )
            .order_by(ReportHistory.generated_at.desc())
            .limit(50)
        )
    ).scalars().all()
    # Enriquecer con nombre del autor (1 SELECT batch).
    from app.models.user import User

    user_ids = {str(r.generated_by_user_id) for r in rows if r.generated_by_user_id}
    users_by_id: dict[str, User] = {}
    if user_ids:
        urows = (
            await db.execute(select(User).where(User.id.in_(user_ids)))
        ).scalars().all()
        users_by_id = {str(u.id): u for u in urows}
    out: list[ReportHistoryRead] = []
    for r in rows:
        u = users_by_id.get(str(r.generated_by_user_id)) if r.generated_by_user_id else None
        item = ReportHistoryRead.model_validate(r)
        if u:
            item.generated_by_name = u.full_name or u.email
        elif r.scheduled_report_id:
            item.generated_by_name = "Automático (scheduler)"
        out.append(item)
    return out


@router.get("/report-history/{history_id}/download")
async def download_report_history(
    history_id: UUID,
    inline: bool = Query(default=False),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-092: re-renderiza el PDF desde el `Report.sections` snapshot
    asociado. En una iteración futura, si `file_key` está poblado, se
    devolverá el binario archivado en R2 directamente.
    """
    tenant_id = _tenant(cu)
    h = (
        await db.execute(
            select(ReportHistory).where(
                ReportHistory.id == str(history_id),
                ReportHistory.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if h is None:
        raise not_found("Reporte de historial")
    if h.source_report_id is None:
        raise not_found("Snapshot del reporte (no se puede re-renderizar)")
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(h.source_report_id),
                Report.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte fuente")
    template = (
        "reports/avance.html" if h.report_type == "avance" else "reports/seguimiento.html"
    )
    ctx = dict(rep.sections or {})
    ctx["tenant_name"] = await _tenant_name(db, tenant_id)
    pdf = render_pdf(template, ctx)
    project = await _get_project(db, tenant_id, UUID(h.project_id))
    label = "Avance" if h.report_type == "avance" else "Seguimiento"
    filename = _report_filename(label, project.name, h.generated_at)
    return _pdf_response(pdf, filename, inline=inline)


# ============================================================================
# US-093 — Creación de reporte con IA (3a vista de ENH-055).
# ============================================================================

class AIGenerateBody(BaseModel):
    base: str = Field(default="avance", pattern="^(avance|seguimiento|custom)$")
    period_end: date | None = None
    include_kpis: bool = True
    include_tasks: bool = True
    include_raid: bool = True
    include_milestones: bool = True
    free_notes: str = Field(default="", max_length=4000)
    save_to_history: bool = False

    # ENH-071: filtros configurables sobre el listado del reporte. Todos
    # opcionales — cuando van vacíos no aplican (back-compat con el flujo
    # anterior). Persisten por usuario en localStorage del frontend; el
    # backend solo los recibe, no los persiste.
    date_from: date | None = None
    date_to: date | None = None
    area_ids: list[UUID] | None = None
    assignee_actor_ids: list[UUID] | None = None
    criticalities: list[str] | None = None  # low|medium|high|critical
    statuses: list[str] | None = None       # not_started|in_progress|done|...
    severities: list[str] | None = None     # risks: low|medium|high|critical


class AIGenerateResponse(BaseModel):
    html: str
    history_id: str | None = None


# US-101: reglas globales de orden compartidas entre el reporte IA y la
# UI de listas (consumidas por ENH-071 / ENH-072 como default sort).
REPORT_GLOBAL_ORDER_RULES = (
    "Agrupa los items por área del proyecto. Dentro de cada área, ordena "
    "por fecha fin (end_date) priorizando las fechas más cercanas a hoy "
    "primero (más urgente arriba). Items sin área van al final bajo "
    "'Sin área asignada'."
)

_AI_REPORT_SYSTEM_PROMPT = (
    "Eres un asistente PMO senior. Redacta un reporte de proyecto en HTML "
    "limpio (sin <html>/<body> wrappers, sólo el bloque interno) en español. "
    "Usa <h2> para títulos de sección, <p>/<ul> para contenido. Sé conciso, "
    "directo y orientado a decisiones. "
    # ENH-064: foco default en hitos / críticas / retrasadas.
    "Por defecto enfócate en (en este orden): (1) hitos del proyecto, "
    "(2) tareas con criticidad 'high' o 'critical', y (3) tareas retrasadas "
    "(end_date < hoy y status != 'done'). No incluyas tareas de baja "
    "prioridad ni completadas a menos que el usuario lo pida explícitamente "
    "en sus notas adicionales. Mantén el reporte breve (no más de 6-8 "
    "secciones cortas). "
    # US-101: regla global de orden para todo output del módulo de reportes.
    f"REGLA DE ORDEN OBLIGATORIA: {REPORT_GLOBAL_ORDER_RULES}"
)


@router.post(
    "/projects/{project_id}/reports/ai-generate",
    response_model=AIGenerateResponse,
)
async def ai_generate_report(
    project_id: UUID,
    body: AIGenerateBody,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-093: genera un reporte custom con IA.

    Estrategia:
    1. Construye contexto base (avance/seguimiento) según `body.base`.
    2. Filtra el contexto a las secciones solicitadas.
    3. Llama al LLM del tenant con el JSON + free_notes.
    4. Envuelve en HTML estilizado y devuelve.
    5. Si `save_to_history=true`, persiste un Report + ReportHistory para
       que aparezca en la vista Historial (US-092).
    """
    import json

    from app.core.errors import business_rule, service_unavailable
    from app.services.ai.platform_config import resolve_groq_config
    from app.services.ai.provider import generate_for_tenant
    from app.services.ai.tenant_ai import load_tenant_ai
    from app.services.operational_reports import build_seguimiento_context

    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)

    tenant_cfg = await load_tenant_ai(db, tenant_id)
    if tenant_cfg.mode == "disabled":
        raise business_rule(
            "El tenant no tiene IA configurada (ai_mode=disabled)"
        )

    # US-101: unifica con el code path de minutas (workers/tasks/ai.py:252)
    # — el endpoint debe resolver la config Groq y pasarla explícita al
    # provider; sin esto el caller falla con `groq_no_api_key`.
    platform_groq = None
    if tenant_cfg.mode == "platform":
        platform_groq = await resolve_groq_config(db)
        if platform_groq is None:
            raise service_unavailable(
                "El proveedor de IA (Groq) no está disponible: falta la API "
                "key en plataforma.",
                code="ai_provider_unavailable",
            )

    cut_off = body.period_end or datetime.now(UTC).date()
    if body.base == "seguimiento":
        context = await build_seguimiento_context(db, tenant_id, project.id, cut_off, 14)
    else:
        context = await build_avance_context(db, tenant_id, project.id, cut_off)

    # ENH-071: filtros configurables sobre el listado del reporte.
    area_set = {str(a) for a in (body.area_ids or [])}
    actor_set = {str(a) for a in (body.assignee_actor_ids or [])}
    crit_set = set(body.criticalities or [])
    status_set = set(body.statuses or [])
    sev_set = set(body.severities or [])
    d_from, d_to = body.date_from, body.date_to

    def _in_date_window(iso: str | None) -> bool:
        if not iso or (d_from is None and d_to is None):
            return True
        try:
            d = date.fromisoformat(iso)
        except ValueError:
            return True
        if d_from and d < d_from:
            return False
        if d_to and d > d_to:
            return False
        return True

    def _task_matches(t: dict) -> bool:
        if area_set and (t.get("area_id") not in area_set):
            return False
        if actor_set and (t.get("assignee_actor_id") not in actor_set):
            return False
        if crit_set and (t.get("criticality") not in crit_set):
            return False
        if status_set and (t.get("status") not in status_set):
            return False
        if not _in_date_window(t.get("end_date")):
            return False
        return True

    def _risk_matches(r: dict) -> bool:
        if sev_set and (r.get("severity") not in sev_set):
            return False
        if status_set and (r.get("status") not in status_set):
            return False
        return True

    def _issue_matches(i: dict) -> bool:
        if status_set and (i.get("status") not in status_set):
            return False
        if not _in_date_window(i.get("committed_date")):
            return False
        return True

    filtered: dict = {}
    if body.include_kpis:
        filtered["kpis"] = context.get("kpis") or context.get("metrics") or {}
    if body.include_tasks:
        # ENH-064: prefiere focus_tasks (hitos/críticas/retrasadas top 20)
        # antes que la lista cruda; mantiene el reporte conciso.
        raw_tasks = (
            context.get("focus_tasks")
            or context.get("tasks")
            or context.get("activities")
            or []
        )
        filtered["tasks"] = [t for t in raw_tasks if _task_matches(t)]
        filtered["tasks_total"] = len(raw_tasks)
        filtered["tasks_filtered"] = len(filtered["tasks"])
    # ENH-064: incluye siempre el priority_summary cuando esté disponible.
    if context.get("priority_summary"):
        filtered["priority_summary"] = context["priority_summary"]
    if body.include_raid:
        raw_risks = context.get("top_risks") or context.get("risks") or []
        raw_issues = context.get("open_aids") or context.get("issues") or []
        filtered["raid"] = {
            "risks": [r for r in raw_risks if _risk_matches(r)],
            "issues": [i for i in raw_issues if _issue_matches(i)],
        }
    if body.include_milestones:
        filtered["milestones"] = context.get("milestones") or []

    user_prompt = (
        f"Proyecto: {project.name} ({project.folio}).\n"
        f"Período hasta {cut_off.isoformat()}.\n"
        f"Datos del proyecto (JSON):\n{json.dumps(filtered, ensure_ascii=False, default=str)[:6000]}\n\n"
        f"Notas adicionales del usuario:\n{body.free_notes or '(ninguna)'}\n\n"
        "Devuelve HTML limpio sin <html>/<body>."
    )

    try:
        res = await generate_for_tenant(
            user_prompt,
            system=_AI_REPORT_SYSTEM_PROMPT,
            tenant_ai_mode=tenant_cfg.mode,
            platform_groq_config=platform_groq,
            byo_config=tenant_cfg.byo,
            tenant_ollama_config=tenant_cfg.legacy_ollama,
            tenant_id=str(tenant_id),
        )
        body_html = (res.text or "").strip()
    except Exception as exc:
        raise business_rule(f"La IA falló al generar el reporte: {exc}") from exc

    full_html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:system-ui,sans-serif;color:#1f2937;"
        "line-height:1.5;padding:24px;max-width:760px;margin:0 auto}"
        "h1{font-size:20px}h2{font-size:16px;margin-top:18px;"
        "border-bottom:1px solid #e5e7eb;padding-bottom:4px}"
        "ul{margin:6px 0 12px 18px}p{margin:6px 0}"
        ".meta{color:#6b7280;font-size:12px;margin-bottom:16px}</style></head><body>"
        f"<h1>{project.name}</h1>"
        f"<p class='meta'>Folio {project.folio} · {cut_off.isoformat()} · Generado con IA</p>"
        f"{body_html}"
        "</body></html>"
    )

    history_id: str | None = None
    if body.save_to_history:
        rep = Report(
            tenant_id=str(tenant_id),
            project_id=str(project.id),
            title=f"Reporte IA — {project.folio} — {cut_off.isoformat()}",
            period=None,
            generator="ai",
            cut_off_date=cut_off,
            sections={"_html": full_html, "_base": body.base},
            recipients=[],
            status="draft",
            generated_by_ai=True,
            created_by=cu.id,
        )
        db.add(rep)
        await db.flush()
        h = ReportHistory(
            tenant_id=str(tenant_id),
            project_id=str(project.id),
            report_type=body.base if body.base != "custom" else "ai_custom",
            generated_by_user_id=str(cu.id),
            source_report_id=str(rep.id),
            file_size_bytes=len(full_html.encode("utf-8")),
        )
        db.add(h)
        await db.flush()
        history_id = str(h.id)
        await write_audit(
            db,
            action="report.generate.ai",
            module="reports",
            user_id=cu.id,
            tenant_id=tenant_id,
            entity_type="report",
            entity_id=str(rep.id),
            details={"base": body.base},
        )
        await db.commit()

    return AIGenerateResponse(html=full_html, history_id=history_id)
