"""Change Approval workflow — EP019 (US-112 + US-113).

US-112 endpoints:
- GET /change-requests/{id}/approvers           — lista
- POST /change-requests/{id}/approvers          — agrega (draft/rejected only)
- DELETE /change-requests/{id}/approvers/{aid}  — quita

US-113 endpoints:
- POST /change-requests/{id}/submit-for-approval  — genera tokens + dispara emails
- GET  /public/approve/{token}                    — landing data (público, sin auth)
- POST /public/approve/{token}                    — registra decisión (público)

Status del Change extiende el conjunto existente con:
  draft → in_review → pending_approval → approved | rejected | implemented
Mantenemos compat con `in_review` / `approved` / `rejected` / `implemented`.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.config import settings
from app.core.errors import business_rule, conflict, forbidden, mensaje, not_found
from app.db.session import get_db
from app.models.area import Actor
from app.models.change_approval import ApprovalToken, ChangeApprover
from app.models.modules import ChangeRequest
from app.models.project import Project
from app.services.audit import write_audit

logger = logging.getLogger("pmoaas.change_approvals")

router = APIRouter(tags=["change_approvals"])
public_router = APIRouter(prefix="/public", tags=["public_approve"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


def _approval_secret() -> str:
    """Secreto para firmar tokens JWT. Usa APPROVAL_TOKEN_SECRET o cae a
    JWT_SECRET (compartido con auth) — el scope del token es distinto
    así que la colisión no es problema.
    """
    return settings.APPROVAL_TOKEN_SECRET or settings.JWT_SECRET


def _hash_token(jwt_str: str) -> str:
    return hashlib.sha256(jwt_str.encode("utf-8")).hexdigest()


# ---------- US-112 ----------


class ApproverCreate(BaseModel):
    actor_id: UUID
    role: Literal["primary", "secondary"] = "primary"


class ApproverRead(BaseModel):
    id: UUID
    change_id: UUID
    actor_id: UUID
    actor_name: str | None = None
    actor_email: str | None = None
    role: str
    status: str
    decided_at: datetime | None
    decision_note: str | None

    model_config = {"from_attributes": True}


def _check_can_modify_approvers(change: ChangeRequest) -> None:
    """CA3 — solo permitido en draft / rejected / in_review (estado
    inicial). Una vez `pending_approval` la lista queda congelada (CA4).
    """
    if change.status in {"pending_approval", "approved", "implemented"}:
        raise conflict(
            mensaje(
                que=f"No se puede modificar la lista de aprobadores en estado `{change.status}`",
                porque="Cambiar quién decide con el proceso en marcha invalidaría las respuestas ya dadas.",
                accion="Cancela la ronda de aprobación, ajusta la lista y vuelve a enviarla.",
            ),
            code="STATE_TRANSITION",
        )


async def _get_change(db: AsyncSession, change_id: UUID, tenant_id: UUID) -> ChangeRequest:
    c = (
        await db.execute(
            select(ChangeRequest).where(
                ChangeRequest.id == str(change_id),
                ChangeRequest.tenant_id == str(tenant_id),
                ChangeRequest.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if c is None:
        raise not_found("Change request")
    return c


async def _list_approvers_with_actors(
    db: AsyncSession, change_id: UUID
) -> list[ApproverRead]:
    rows = (
        await db.execute(
            select(ChangeApprover, Actor)
            .outerjoin(Actor, Actor.id == ChangeApprover.actor_id)
            .where(ChangeApprover.change_id == str(change_id))
            .order_by(ChangeApprover.created_at.asc())
        )
    ).all()
    return [
        ApproverRead(
            id=ap.id,
            change_id=ap.change_id,
            actor_id=ap.actor_id,
            actor_name=actor.name if actor else None,
            actor_email=actor.email if actor else None,
            role=ap.role,
            status=ap.status,
            decided_at=ap.decided_at,
            decision_note=ap.decision_note,
        )
        for ap, actor in rows
    ]


@router.get(
    "/change-requests/{change_id}/approvers",
    response_model=list[ApproverRead],
)
async def list_approvers(
    change_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_change(db, change_id, tenant_id)
    return await _list_approvers_with_actors(db, change_id)


@router.post(
    "/change-requests/{change_id}/approvers",
    response_model=ApproverRead,
    status_code=201,
)
async def add_approver(
    change_id: UUID,
    body: ApproverCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    change = await _get_change(db, change_id, tenant_id)
    _check_can_modify_approvers(change)
    # Valida que el actor exista en el tenant.
    actor = (
        await db.execute(
            select(Actor).where(
                Actor.id == str(body.actor_id),
                Actor.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if actor is None:
        raise not_found("Actor")
    # CA5: email es requerido para enviar el email de US-113.
    if not actor.email:
        raise business_rule(
            mensaje(
                que="El Actor no tiene email registrado — agrégalo antes de asignar como aprobador.",
                porque="La solicitud de aprobación viaja por correo y sin dirección no llega.",
                accion="Registra su correo en el directorio y vuelve a asignarlo.",
            ),
            code="ACTOR_EMAIL_MISSING",
        )
    # Idempotencia: si ya existe, devuélvelo en vez de duplicar.
    existing = (
        await db.execute(
            select(ChangeApprover).where(
                ChangeApprover.change_id == str(change_id),
                ChangeApprover.actor_id == str(body.actor_id),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        ap = existing
    else:
        ap = ChangeApprover(
            tenant_id=str(tenant_id),
            change_id=str(change_id),
            actor_id=str(body.actor_id),
            role=body.role,
            status="pending",
        )
        db.add(ap)
        await db.flush()
        await write_audit(
            db, action="change_approver.add", module="change_approvals",
            user_id=cu.id, tenant_id=tenant_id,
            entity_type="change_approver", entity_id=str(ap.id),
            details={"change_id": str(change_id), "actor_id": str(body.actor_id)},
        )
        await db.commit()
    return ApproverRead(
        id=ap.id,
        change_id=ap.change_id,
        actor_id=ap.actor_id,
        actor_name=actor.name,
        actor_email=actor.email,
        role=ap.role,
        status=ap.status,
        decided_at=ap.decided_at,
        decision_note=ap.decision_note,
    )


@router.delete(
    "/change-requests/{change_id}/approvers/{approver_id}",
    status_code=204,
)
async def remove_approver(
    change_id: UUID,
    approver_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    change = await _get_change(db, change_id, tenant_id)
    _check_can_modify_approvers(change)
    ap = (
        await db.execute(
            select(ChangeApprover).where(
                ChangeApprover.id == str(approver_id),
                ChangeApprover.change_id == str(change_id),
                ChangeApprover.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if ap is None:
        raise not_found("Aprobador")
    await write_audit(
        db, action="change_approver.remove", module="change_approvals",
        user_id=cu.id, tenant_id=tenant_id,
        entity_type="change_approver", entity_id=str(ap.id),
    )
    await db.delete(ap)
    await db.commit()
    return None


# ---------- US-113 ----------


def _build_approval_url(token: str) -> str:
    """URL del enlace de aprobación que viaja por correo.

    Se resolvía con `os.environ` sobre dos nombres y caía a
    `http://localhost:3000`. Con ninguna de las dos variables puesta, los
    correos de aprobación salían con enlaces a la máquina de quien los
    recibía — y el fallo no aparece en ningún registro: el correo se envía
    bien, y es al hacer clic cuando no pasa nada.

    Ahora sale de `Settings`, que ya declaraba `APP_BASE_URL` con el dominio de
    producción por defecto. Los dos nombres viejos se siguen aceptando por si
    algún despliegue los tiene puestos.
    """
    base = (
        settings.APP_PUBLIC_URL or settings.NEXT_PUBLIC_BASE_URL or settings.APP_BASE_URL
    ).rstrip("/")
    return f"{base}/approve/{token}"


def _send_approval_email(
    *,
    to_email: str,
    to_name: str,
    project_name: str,
    change: ChangeRequest,
    approve_url: str,
) -> None:
    """CA6+CA7 — envía email con 1 link (la decisión la elige el aprobador
    en la landing). Usa la infra de notifications de EP011 si está
    disponible; en dev/test se loguea para no bloquear el flujo.
    """
    subject = f"[Aprobación] {project_name} — Cambio: {change.title}"
    body_html = (
        f"<p>Hola {to_name},</p>"
        f"<p>Se solicita tu aprobación para el siguiente cambio del proyecto "
        f"<strong>{project_name}</strong>:</p>"
        f"<h2 style='margin:18px 0 6px;'>{change.title}</h2>"
        f"<p style='color:#5a5044;white-space:pre-wrap;'>{change.description or ''}</p>"
        f"<p><strong>Tipo:</strong> {change.type} · <strong>Folio:</strong> {change.folio}</p>"
        f"<p><strong>Impacto esperado:</strong><br>{change.impact or '—'}</p>"
        f"<p style='margin-top:24px;'>"
        f"<a href='{approve_url}' "
        f"style='display:inline-block;background:#2c6e3f;color:#fff;"
        f"text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600;'>"
        f"Revisar y decidir</a></p>"
        f"<p style='font-size:12px;color:#999;margin-top:24px;'>"
        f"Este enlace expira en 30 días.</p>"
    )
    try:
        from app.services.notifications import send_email  # type: ignore
    except Exception:
        send_email = None  # type: ignore
    if send_email is None:
        logger.info(
            "[approval-email-stub] to=%s subject=%s url=%s",
            to_email, subject, approve_url,
        )
        return
    try:
        send_email(to=to_email, subject=subject, html=body_html)  # type: ignore
    except Exception as exc:
        logger.exception("send_approval_email failed: %s", exc)


@router.post("/change-requests/{change_id}/submit-for-approval")
async def submit_for_approval(
    change_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """CA1 — genera 1 token JWT firmado por aprobador, scope `{change_id,
    actor_id, action_choice}`, expiry 30 días, dispara emails y mueve
    el Cambio a `pending_approval`.

    CA11 — re-trigger tras rechazo: tokens previos del mismo change_id
    se borran (CASCADE explícito) antes de crear los nuevos.
    """
    tenant_id = _tenant(cu)
    change = await _get_change(db, change_id, tenant_id)
    if change.status not in {"in_review", "rejected", "draft"}:
        raise conflict(
            mensaje(
                que=f"No se puede enviar a aprobación desde estado `{change.status}`",
                porque="Solo se envía lo que está en borrador o pendiente de corrección.",
                accion="Vuelve el cambio a borrador y envíalo desde ahí.",
            ),
            code="STATE_TRANSITION",
        )

    approvers = await _list_approvers_with_actors(db, change_id)
    if not approvers:
        raise business_rule(
            mensaje(
                que="Agrega al menos 1 aprobador antes de enviar a aprobación",
                porque="Un cambio sin aprobadores se quedaría esperando a nadie.",
                accion="Añade al menos una persona a la lista y vuelve a enviar.",
            ),
            code="NO_APPROVERS",
        )

    # CA11: invalida tokens previos.
    prev_tokens = (
        await db.execute(
            select(ApprovalToken).where(ApprovalToken.change_id == str(change_id))
        )
    ).scalars().all()
    for pt in prev_tokens:
        await db.delete(pt)
    # Reset de status individual de los approvers a pending.
    db_approvers = (
        await db.execute(
            select(ChangeApprover).where(
                ChangeApprover.change_id == str(change_id)
            )
        )
    ).scalars().all()
    for ap in db_approvers:
        ap.status = "pending"
        ap.decided_at = None
        ap.decision_note = None

    project = (
        await db.execute(
            select(Project).where(Project.id == str(change.project_id))
        )
    ).scalar_one_or_none()
    project_name = project.name if project else "Proyecto"

    # Genera tokens.
    secret = _approval_secret()
    expiry = datetime.now(UTC) + timedelta(days=30)
    issued: list[tuple[ApproverRead, str]] = []
    for ap in approvers:
        payload = {
            "scope": "change_approval",
            "change_id": str(change_id),
            "actor_id": str(ap.actor_id),
            "approver_id": str(ap.id),
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int(expiry.timestamp()),
        }
        jwt_str = jwt.encode(payload, secret, algorithm="HS256")
        token = ApprovalToken(
            tenant_id=str(tenant_id),
            change_id=str(change_id),
            actor_id=str(ap.actor_id),
            token_hash=_hash_token(jwt_str),
            expires_at=expiry,
        )
        db.add(token)
        issued.append((ap, jwt_str))

    change.status = "pending_approval"
    await write_audit(
        db, action="change.submit_for_approval", module="change_approvals",
        user_id=cu.id, tenant_id=tenant_id,
        entity_type="change_request", entity_id=str(change_id),
        details={"approvers": len(approvers)},
    )
    await db.commit()

    # Envía emails (post-commit para no bloquear si falla).
    sent: list[str] = []
    for ap, jwt_str in issued:
        if not ap.actor_email:
            continue
        _send_approval_email(
            to_email=ap.actor_email,
            to_name=ap.actor_name or "Aprobador",
            project_name=project_name,
            change=change,
            approve_url=_build_approval_url(jwt_str),
        )
        sent.append(ap.actor_email)
    return {"status": "pending_approval", "approvers": len(approvers), "emails_sent": sent}


class PublicApprovalInfo(BaseModel):
    change_id: UUID
    folio: str
    title: str
    description: str | None
    type: str
    impact: str | None
    project_name: str
    actor_name: str | None
    expires_at: datetime
    consumed_at: datetime | None
    action_taken: str | None


async def _resolve_token(
    db: AsyncSession, jwt_str: str
) -> tuple[ApprovalToken, dict]:
    """Decode + buscar la fila por token_hash. Lanza errores claros si
    el token está mal firmado, expiró o ya fue consumido."""
    secret = _approval_secret()
    try:
        payload = jwt.decode(jwt_str, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise conflict(mensaje(
            que="Este enlace ya expiró.",
            porque="Los enlaces de aprobación caducan para que uno reenviado no valga meses después.",
            accion="Pide a quien lo envió que genere uno nuevo.",
        ), code="TOKEN_EXPIRED") from exc
    except jwt.PyJWTError as exc:
        raise not_found("Token inválido") from exc
    if payload.get("scope") != "change_approval":
        raise not_found("Token inválido")
    token_hash = _hash_token(jwt_str)
    tk = (
        await db.execute(
            select(ApprovalToken).where(ApprovalToken.token_hash == token_hash)
        )
    ).scalar_one_or_none()
    if tk is None:
        raise not_found("Token desconocido — fue revocado.")
    return tk, payload


@public_router.get("/approve/{jwt_str}", response_model=PublicApprovalInfo)
async def get_approval_landing(
    jwt_str: str = Path(..., min_length=10),
    db: AsyncSession = Depends(get_db),
):
    tk, _payload = await _resolve_token(db, jwt_str)
    change = (
        await db.execute(
            select(ChangeRequest).where(ChangeRequest.id == str(tk.change_id))
        )
    ).scalar_one_or_none()
    if change is None:
        raise not_found("Cambio")
    project = (
        await db.execute(
            select(Project).where(Project.id == str(change.project_id))
        )
    ).scalar_one_or_none()
    actor = (
        await db.execute(select(Actor).where(Actor.id == str(tk.actor_id)))
    ).scalar_one_or_none()
    return PublicApprovalInfo(
        change_id=change.id,
        folio=change.folio,
        title=change.title,
        description=change.description,
        type=change.type,
        impact=change.impact,
        project_name=project.name if project else "",
        actor_name=actor.name if actor else None,
        expires_at=tk.expires_at,
        consumed_at=tk.consumed_at,
        action_taken=tk.action_taken,
    )


class PublicApprovalDecision(BaseModel):
    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=2000)


@public_router.post("/approve/{jwt_str}")
async def post_approval_decision(
    jwt_str: str,
    body: PublicApprovalDecision,
    db: AsyncSession = Depends(get_db),
):
    tk, _payload = await _resolve_token(db, jwt_str)
    if tk.consumed_at is not None:
        raise conflict(
            mensaje(
                que=f"Ya respondiste con `{tk.action_taken}`.",
                porque="Cada aprobador responde una vez para que el resultado no dependa del orden.",
                accion="Si te equivocaste, pide a quien coordina el cambio que reabra tu respuesta.",
            ), code="TOKEN_CONSUMED",
        )

    change = (
        await db.execute(
            select(ChangeRequest).where(ChangeRequest.id == str(tk.change_id))
        )
    ).scalar_one_or_none()
    if change is None:
        raise not_found("Cambio")
    if change.status != "pending_approval":
        raise conflict(
            mensaje(
                que=f"El Cambio está en estado `{change.status}`; ya no se aceptan respuestas.",
                porque="La decisión ya está tomada y registrada.",
                accion="Si hace falta revisarla, abre un cambio nuevo.",
            ),
            code="STATE_TRANSITION",
        )

    # Localiza el approver que corresponde a este actor.
    approver = (
        await db.execute(
            select(ChangeApprover).where(
                ChangeApprover.change_id == str(tk.change_id),
                ChangeApprover.actor_id == str(tk.actor_id),
            )
        )
    ).scalar_one_or_none()
    if approver is None:
        raise not_found("Aprobador")

    approver.status = "approved" if body.action == "approve" else "rejected"
    approver.decided_at = datetime.now(UTC)
    approver.decision_note = (body.note or "").strip() or None
    tk.consumed_at = datetime.now(UTC)
    tk.action_taken = body.action

    # CA5 — recalcula status del Cambio.
    others = (
        await db.execute(
            select(ChangeApprover).where(
                ChangeApprover.change_id == str(tk.change_id)
            )
        )
    ).scalars().all()
    statuses = [a.status for a in others]
    if body.action == "reject":
        # CA5: cualquier rechazo → Cambio = rejected. Tokens vivos quedan
        # invalidados (consumed_at) preventivamente.
        change.status = "rejected"
        change.approved_at = datetime.now(UTC)
        live_tokens = (
            await db.execute(
                select(ApprovalToken).where(
                    ApprovalToken.change_id == str(tk.change_id),
                    ApprovalToken.consumed_at.is_(None),
                )
            )
        ).scalars().all()
        now = datetime.now(UTC)
        for lt in live_tokens:
            lt.consumed_at = now
            lt.action_taken = "invalidated"
    elif all(s == "approved" for s in statuses):
        change.status = "approved"
        change.approved_at = datetime.now(UTC)

    await write_audit(
        db, action=f"change.approval_{body.action}", module="change_approvals",
        user_id=None, tenant_id=tk.tenant_id,
        entity_type="change_request", entity_id=str(tk.change_id),
        details={"actor_id": str(tk.actor_id), "via": "public_token"},
    )
    await db.commit()
    return {
        "ok": True,
        "action": body.action,
        "change_status": change.status,
    }
