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
from app.models.ai_report_template import AIReportTemplate
from app.models.project import Project
from app.models.report_history import ReportHistory
from app.services.audit import write_audit
from app.services.html_report_renderer import render_report_html
from app.services.operational_reports import (
    build_avance_context,
    build_seguimiento_context,
)
from app.services.pdf_renderer import render_pdf

router = APIRouter(tags=["reports"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


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


@router.delete("/report-history/{history_id}", status_code=204)
async def delete_report_history(
    history_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-081: borra una entry del historial (house-keeping). También
    borra el `Report` source si todavía existe — el user pidió liberar
    espacio explícitamente."""
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
    source_id = h.source_report_id
    await db.delete(h)
    if source_id is not None:
        rep = (
            await db.execute(
                select(Report).where(
                    Report.id == str(source_id),
                    Report.tenant_id == str(tenant_id),
                )
            )
        ).scalar_one_or_none()
        if rep is not None:
            await db.delete(rep)
    await write_audit(
        db,
        action="report_history.delete",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="report_history",
        entity_id=str(history_id),
        details={"source_report_id": str(source_id) if source_id else None},
    )
    await db.commit()
    return Response(status_code=204)


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
    project = await _get_project(db, tenant_id, UUID(h.project_id))
    # BUG-055: AI reports guardan HTML en sections["_html"]; servir directo
    # (no usan los templates de Avance/Seguimiento).
    # BUG-059: si el reporte fue tweakeado (US-109), `rep.html_content`
    # tiene la última versión. Sin esto el preview servía el HTML viejo
    # almacenado en sections["_html"] desde la generación inicial.
    if rep.generator == "ai" or h.report_type == "ai_custom":
        html = (
            rep.html_content
            or (rep.sections or {}).get("_html")
            or ""
        )
        filename = _report_filename("IA", project.name, h.generated_at)
        # Para HTML preferimos sufijo .html en lugar de .pdf; el inline=true
        # abre directo en el browser, attachment fuerza descarga.
        ascii_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename).rstrip(".")
        if not ascii_name.lower().endswith(".html"):
            ascii_name = re.sub(r"\.pdf$", "", ascii_name) + ".html"
        utf_name = quote(re.sub(r"\.pdf$", "", filename) + ".html")
        disposition = "inline" if inline else "attachment"
        return Response(
            content=html.encode("utf-8"),
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f"{disposition}; filename=\"{ascii_name}\"; "
                    f"filename*=UTF-8''{utf_name}"
                )
            },
        )
    template = (
        "reports/avance.html" if h.report_type == "avance" else "reports/seguimiento.html"
    )
    ctx = dict(rep.sections or {})
    ctx["tenant_name"] = await _tenant_name(db, tenant_id)
    pdf = render_pdf(template, ctx)
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

    # ENH-085: separar Filtros vs Instrucciones — la IA necesita jerarquía
    # explícita para no diluir las free_notes en los 6000 chars de datos.
    # Resolvemos los nombres de áreas (legibles) si vinieron area_ids.
    from app.models.area import Area

    area_name_map: dict[str, str] = {}
    if area_set:
        arows = (
            await db.execute(
                select(Area.id, Area.name).where(Area.id.in_(area_set))
            )
        ).all()
        area_name_map = {str(aid): (name or "—") for aid, name in arows}

    filter_lines: list[str] = []
    if area_set:
        names = sorted(area_name_map.get(a, a) for a in area_set)
        filter_lines.append(f"Áreas: {', '.join(names)}")
    if crit_set:
        filter_lines.append(f"Criticidad: {', '.join(sorted(crit_set))}")
    if status_set:
        filter_lines.append(f"Status: {', '.join(sorted(status_set))}")
    if sev_set:
        filter_lines.append(f"Severidad: {', '.join(sorted(sev_set))}")
    if d_from or d_to:
        filter_lines.append(
            f"Fechas: {d_from.isoformat() if d_from else '—'} → "
            f"{d_to.isoformat() if d_to else '—'}"
        )
    filters_summary_text = "\n".join(filter_lines) if filter_lines else "(sin filtros adicionales)"

    user_prompt = (
        f"Proyecto: {project.name} ({project.folio}).\n"
        f"Período hasta {cut_off.isoformat()}.\n"
        "\n<DATOS_DEL_PROYECTO>\n"
        f"{json.dumps(filtered, ensure_ascii=False, default=str)[:6000]}\n"
        "</DATOS_DEL_PROYECTO>\n"
        "\n<FILTROS_APLICADOS>\n"
        "Los datos arriba YA están recortados según estos filtros. No "
        "menciones items que NO aparezcan en el JSON.\n"
        f"{filters_summary_text}\n"
        "</FILTROS_APLICADOS>\n"
        "\n<INSTRUCCIONES_DEL_USUARIO>\n"
        "DEBES OBEDECER ESTAS INSTRUCCIONES POR ENCIMA DE LAS REGLAS GENERALES. "
        "Si no hay instrucciones, sigue las reglas del system prompt.\n"
        f"{body.free_notes.strip() if body.free_notes else '(ninguna)'}\n"
        "</INSTRUCCIONES_DEL_USUARIO>\n"
        "\n<FORMATO_DE_SALIDA>\n"
        "HTML limpio en español, sin <html>/<body>. Usa <h2>/<p>/<ul>.\n"
        "</FORMATO_DE_SALIDA>"
    )

    try:
        res = await generate_for_tenant(
            user_prompt,
            system=_AI_REPORT_SYSTEM_PROMPT,
            tenant_ai_mode=tenant_cfg.mode,
            platform_groq_config=platform_groq,
            byo_config=tenant_cfg.byo,
            tenant_id=str(tenant_id),
        )
        body_html = (res.text or "").strip()
    except Exception as exc:
        # BUG-057: si el provider falla, propagamos un mensaje útil al user
        # y registramos el traceback completo para debugging server-side.
        import logging

        logging.getLogger("app.reports.ai").exception(
            "AI generate failed for tenant=%s project=%s mode=%s",
            tenant_id, project.id, tenant_cfg.mode,
        )
        msg = str(exc).strip()
        if not msg:
            # Excepciones tipo httpx con response body vacío → caemos a repr.
            msg = repr(exc) or type(exc).__name__
        # Si la excepción trae un response HTTP, anexa status + body trimmed.
        resp = getattr(exc, "response", None)
        if resp is not None:
            status = getattr(resp, "status_code", None)
            try:
                body_text = resp.text if hasattr(resp, "text") else ""
            except Exception:
                body_text = ""
            if status or body_text:
                snippet = (body_text or "")[:240]
                msg = f"{msg} [HTTP {status}] {snippet}".strip()
        raise business_rule(
            f"La IA falló al generar el reporte ({type(exc).__name__}): {msg}"
        ) from exc

    # ENH-085: bloque de "Filtros activos" en el header — transparencia
    # para el lector (sabe qué dataset alimentó la IA).
    if filter_lines:
        filters_chips_html = (
            "<div class='filters'>"
            + "<span class='filter-label'>Filtros activos:</span>"
            + "".join(f"<span class='chip'>{line}</span>" for line in filter_lines)
            + "</div>"
        )
    else:
        filters_chips_html = ""

    # BUG-056: estilos alineados al DS y al base.html de PDF (DM Sans +
    # JetBrains Mono, paleta var(--chrome|--muted|--border)). El HTML se
    # sirve tanto online (ENH-073) como en download/preview (BUG-055).
    full_html = (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<title>Reporte IA — {project.name}</title>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&"
        "family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>"
        "<style>"
        ":root{--chrome:#182e4e;--accent:#2563eb;--muted:#6b7280;"
        "--border:#e5e7eb;--surface:#ffffff;--app:#f8fafc;"
        "--info-bg:#eef2ff;--info-fg:#3730a3;--info-border:#c7d2fe;"
        "--text:#111827;--text-soft:#1f2937}"
        "*{box-sizing:border-box}"
        "html,body{margin:0;padding:0}"
        "body{font-family:'DM Sans','Helvetica Neue',Helvetica,Arial,sans-serif;"
        "color:var(--text);line-height:1.55;background:var(--app);"
        "padding:32px 16px;font-size:14px}"
        "main{max-width:780px;margin:0 auto;background:var(--surface);"
        "border:1px solid var(--border);border-radius:14px;"
        "box-shadow:0 1px 2px rgba(15,23,42,0.04);padding:32px 36px}"
        "header{margin-bottom:24px;padding-bottom:18px;border-bottom:1px solid var(--border)}"
        ".tag{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:11px;"
        "letter-spacing:.04em;text-transform:uppercase;padding:3px 8px;border-radius:999px;"
        "background:var(--info-bg);color:var(--info-fg);border:1px solid var(--info-border);"
        "margin-bottom:10px}"
        "h1{font-size:24px;color:var(--chrome);margin:0 0 6px;font-weight:600;letter-spacing:-.01em}"
        ".meta{color:var(--muted);font-size:12.5px;margin:0;"
        "font-family:'JetBrains Mono',monospace}"
        "h2{font-size:17px;color:var(--chrome);margin:28px 0 8px;font-weight:600;"
        "border-bottom:1px solid var(--border);padding-bottom:4px}"
        "h3{font-size:14.5px;color:var(--text-soft);margin:18px 0 6px;font-weight:600}"
        "p{margin:8px 0}"
        "ul,ol{margin:8px 0 14px 22px;padding:0}"
        "li{margin:3px 0}"
        "table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13.5px}"
        "th,td{border:1px solid var(--border);padding:6px 10px;text-align:left;vertical-align:top}"
        "th{background:var(--app);color:var(--chrome);font-weight:600}"
        "code,pre{font-family:'JetBrains Mono',monospace;font-size:12.5px;"
        "background:var(--app);border:1px solid var(--border);border-radius:6px}"
        "code{padding:1px 5px}"
        "pre{padding:10px 12px;overflow-x:auto}"
        "blockquote{margin:10px 0;padding:6px 14px;border-left:3px solid var(--info-border);"
        "background:var(--info-bg);color:var(--info-fg);border-radius:0 6px 6px 0}"
        ".filters{margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}"
        ".filter-label{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);"
        "text-transform:uppercase;letter-spacing:.04em;margin-right:4px}"
        ".chip{display:inline-block;font-size:11.5px;padding:3px 9px;border-radius:999px;"
        "background:var(--app);border:1px solid var(--border);color:var(--text-soft)}"
        "@media print{body{background:white;padding:0}main{box-shadow:none;border:none;padding:0}}"
        "</style></head><body><main>"
        "<header>"
        "<span class='tag'>Reporte · IA</span>"
        f"<h1>{project.name}</h1>"
        f"<p class='meta'>Folio {project.folio} · Corte {cut_off.isoformat()} · Generado con IA</p>"
        f"{filters_chips_html}"
        "</header>"
        f"{body_html}"
        "</main></body></html>"
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


# ============================================================================
# ENH-080 — Plantillas reusables del reporte IA.
# ============================================================================


class AIReportTemplateConfig(BaseModel):
    """Config persistida para regenerar el reporte. Espejo de los campos
    relevantes de AIGenerateBody (sin `period_end`, que siempre se calcula
    en el momento de generar)."""

    include_kpis: bool = True
    include_tasks: bool = True
    include_raid: bool = True
    include_milestones: bool = True
    free_notes: str = Field(default="", max_length=4000)
    area_ids: list[UUID] | None = None
    assignee_actor_ids: list[UUID] | None = None
    criticalities: list[str] | None = None
    statuses: list[str] | None = None
    severities: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None


class AIReportTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    base: str = Field(default="avance", pattern="^(avance|seguimiento|custom)$")
    config: AIReportTemplateConfig = Field(default_factory=AIReportTemplateConfig)


class AIReportTemplateRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    base: str
    config: dict
    created_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get(
    "/projects/{project_id}/ai-report-templates",
    response_model=list[AIReportTemplateRead],
)
async def list_ai_report_templates(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    rows = (
        await db.execute(
            select(AIReportTemplate)
            .where(
                AIReportTemplate.tenant_id == str(tenant_id),
                AIReportTemplate.project_id == str(project.id),
            )
            .order_by(AIReportTemplate.created_at.desc())
        )
    ).scalars().all()
    return [AIReportTemplateRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/ai-report-templates",
    response_model=AIReportTemplateRead,
    status_code=201,
)
async def create_ai_report_template(
    project_id: UUID,
    body: AIReportTemplateCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    tpl = AIReportTemplate(
        tenant_id=str(tenant_id),
        project_id=str(project.id),
        name=body.name.strip(),
        base=body.base,
        config=body.config.model_dump(mode="json"),
        created_by=cu.id,
        created_at=datetime.now(UTC),
    )
    db.add(tpl)
    await db.flush()
    await write_audit(
        db,
        action="ai_report_template.create",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="ai_report_template",
        entity_id=str(tpl.id),
        details={"name": tpl.name, "base": tpl.base},
    )
    await db.commit()
    await db.refresh(tpl)
    return AIReportTemplateRead.model_validate(tpl)


@router.delete(
    "/ai-report-templates/{template_id}",
    status_code=204,
)
async def delete_ai_report_template(
    template_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    tpl = (
        await db.execute(
            select(AIReportTemplate).where(
                AIReportTemplate.id == str(template_id),
                AIReportTemplate.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if tpl is None:
        raise not_found("Plantilla de reporte IA")
    await db.delete(tpl)
    await write_audit(
        db,
        action="ai_report_template.delete",
        module="reports",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="ai_report_template",
        entity_id=str(template_id),
    )
    await db.commit()
    return Response(status_code=204)


# ========== US-111 / ENH-089 — render HTML interactivo ==========


def _project_render_data(
    project: Project, context: dict
) -> dict:
    """Adapta el contexto de `build_avance_context` al shape que espera
    `render_report_html`. El contexto incluye listas de Task/Risk/Issue/
    ChangeRequest ya enriquecidas con `owner` resuelto.
    """
    progress = round(project.progress or 0)
    summary = context.get("priority_summary") or {}
    delayed = summary.get("delayed", 0)
    milestones_pending = summary.get("milestones", 0) - len(
        context.get("milestones_done", [])
    )
    risks = context.get("risks") or []
    issues = context.get("issues") or []
    changes = context.get("changes") or []
    risks_high = sum(
        1 for r in risks if (getattr(r, "severity", 0) or 0) >= 12
    )
    on_time_total = max(1, project.tasks_total if hasattr(project, "tasks_total") else 0)
    on_time_pct = max(0, 100 - round((delayed / on_time_total) * 100)) if on_time_total else 0
    tasks_focus = context.get("focus_tasks") or []

    def _task_row(t):
        owner = getattr(t, "assignee_name", None) or getattr(t, "owner_name", None)
        end = getattr(t, "end_date", None)
        status = getattr(t, "status", "") or ""
        if status == "in_progress":
            status = "En curso"
        elif status == "done":
            status = "Hecho"
        elif status == "not_started":
            status = "Pendiente"
        # ENH-064 — anota retraso como sufijo para que el filtro KPI
        # "retrasada" funcione (busca el texto en la fila).
        delayed_now = (
            end is not None
            and end < datetime.now(UTC).date()
            and status != "Hecho"
        )
        if delayed_now:
            status += " (retrasada)"
        return {
            "name": getattr(t, "name", "") or "",
            "owner": owner or "—",
            "status": status,
            "end_date": end.isoformat() if end else None,
            "progress": int(getattr(t, "progress", 0) or 0),
        }

    return {
        "kpis": {
            "progress": progress,
            "on_time_pct": on_time_pct,
            "delayed_count": delayed,
            "risks_high": risks_high,
            "milestones_pending": max(0, milestones_pending),
        },
        "tasks": [_task_row(t) for t in tasks_focus],
        "risks": [
            {
                "title": getattr(r, "title", "") or "",
                "owner": getattr(r, "owner_name", None) or "—",
                "severity": "alta" if (getattr(r, "severity", 0) or 0) >= 12
                else ("media" if (getattr(r, "severity", 0) or 0) >= 6 else "baja"),
                "status": getattr(r, "status", "") or "",
            }
            for r in risks
        ],
        "issues": [
            {
                "title": getattr(i, "title", "") or "",
                "owner": getattr(i, "owner_name", None) or "—",
                "priority": f"P{getattr(i, 'priority', '') or '—'}",
                "status": getattr(i, "status", "") or "",
            }
            for i in issues
        ],
        "changes": [
            {
                "title": getattr(c, "title", "") or "",
                "type": getattr(c, "type", "") or "—",
                "status": getattr(c, "status", "") or "",
                "requester": getattr(c, "requester_name", None) or "—",
            }
            for c in changes
        ],
    }


@router.get("/reports/{report_id}/render-html")
async def render_report_html_endpoint(
    report_id: UUID,
    refresh: bool = Query(default=False),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-111 — devuelve el HTML standalone del reporte.

    Si el `Report.html_content` ya está populado y `refresh=false`,
    devuelve el HTML guardado (incluye tweaks de US-109 si los hubo).
    Con `refresh=true` regenera desde data del proyecto.
    """
    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id),
                Report.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    if rep.html_content and not refresh:
        return Response(
            content=rep.html_content,
            media_type="text/html; charset=utf-8",
        )
    project = await _get_project(db, tenant_id, UUID(str(rep.project_id)))
    cut_off = rep.cut_off_date or datetime.now(UTC).date()
    context = await build_avance_context(db, tenant_id, project.id, cut_off)
    data = _project_render_data(project, context)
    html = render_report_html(
        title=rep.title or f"Reporte — {project.folio}",
        project_name=project.name,
        project_folio=project.folio,
        generated_at=datetime.now(UTC),
        summary_html=str((rep.sections or {}).get("executive_summary") or ""),
        **data,
    )
    rep.html_content = html
    await db.commit()
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.post("/projects/{project_id}/reports/render-default-html")
async def render_default_report_html(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-109 CA2 — devuelve el HTML default sobre data del proyecto SIN
    crear un Report (uso: arranque del flujo "Generar nuevo reporte"
    para que el render exista desde el inicio antes del tweak IA).
    """
    tenant_id = _tenant(cu)
    project = await _get_project(db, tenant_id, project_id)
    cut_off = datetime.now(UTC).date()
    context = await build_avance_context(db, tenant_id, project.id, cut_off)
    data = _project_render_data(project, context)
    html = render_report_html(
        title=f"Reporte — {project.folio}",
        project_name=project.name,
        project_folio=project.folio,
        generated_at=datetime.now(UTC),
        **data,
    )
    return Response(content=html, media_type="text/html; charset=utf-8")


# ========== ENH-089 — export reportes en HTML/PDF/TXT ==========


@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: UUID,
    format: str = Query(default="html", pattern="^(html|pdf|txt)$"),
    inline: bool = Query(default=False),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-089 — descarga el reporte en el formato seleccionado.

    - `html` (CA1, default): HTML standalone con filtros embebidos.
    - `pdf` (CA2): WeasyPrint sobre el HTML; el `@media print` oculta
      los inputs de filtro y los `<details>` quedan abiertos por
      paginación.
    - `txt` (CA3): texto plano flatten (vía `html_to_text`) — útil para
      minutas que se pegan en email.
    """
    from fastapi.responses import Response as _Resp

    from app.services.pdf_renderer import html_to_pdf, html_to_text

    tenant_id = _tenant(cu)
    rep = (
        await db.execute(
            select(Report).where(
                Report.id == str(report_id),
                Report.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if rep is None:
        raise not_found("Reporte")
    # Si no hay HTML guardado, regenera vía US-111 endpoint.
    html_content = rep.html_content
    if not html_content:
        project = await _get_project(db, tenant_id, UUID(str(rep.project_id)))
        cut_off = rep.cut_off_date or datetime.now(UTC).date()
        context = await build_avance_context(db, tenant_id, project.id, cut_off)
        data = _project_render_data(project, context)
        html_content = render_report_html(
            title=rep.title or f"Reporte — {project.folio}",
            project_name=project.name,
            project_folio=project.folio,
            generated_at=datetime.now(UTC),
            summary_html=str((rep.sections or {}).get("executive_summary") or ""),
            **data,
        )
        rep.html_content = html_content
        await db.commit()

    base_name = re.sub(r"[^A-Za-z0-9_-]+", "_", rep.title or "reporte")[:80] or "reporte"

    if format == "html":
        # US-111 rework: `inline=true` permite preview en tab nueva.
        disposition = "inline" if inline else "attachment"
        return _Resp(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'{disposition}; filename="{base_name}.html"',
            },
        )
    if format == "txt":
        text = html_to_text(html_content)
        return _Resp(
            content=text,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{base_name}.txt"',
            },
        )
    # pdf
    pdf = html_to_pdf(html_content)
    return _Resp(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}.pdf"',
        },
    )
