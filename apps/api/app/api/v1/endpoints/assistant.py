"""Asistente IA conversacional global (US-165, EP008).

Endpoint sincrónico para el widget flotante:

- ``POST /assistant/chat`` — manda un mensaje + contexto de página, crea o
  continúa una conversación, llama al provider del tenant (json_mode) y
  persiste el turno. Devuelve ``{conversation_id, message, actions}``.
- ``GET  /assistant/conversations`` — lista las conversaciones del usuario.
- ``GET  /assistant/conversations/{id}`` — historial de una conversación.
- ``DELETE /assistant/conversations/{id}`` — borra una conversación.

Gateado por el modo IA del tenant (igual que el resto de EP008): si está
``disabled`` devuelve 409. Las acciones son de solo lectura/navegación.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import AppError, forbidden, not_found
from app.db.session import get_db
from app.models.assistant import AssistantConversation, AssistantMessage
from app.services.ai.assistant import (
    ASSISTANT_SYSTEM,
    build_assistant_prompt,
    parse_assistant_reply,
)
from app.services.ai.platform_config import resolve_groq_config
from app.services.ai.provider import generate_for_tenant
from app.services.ai.tenant_ai import load_tenant_ai

router = APIRouter(prefix="/assistant", tags=["assistant"])


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: UUID | None = None
    page_context: str | None = Field(default=None, max_length=8000)


class ChatAction(BaseModel):
    type: str
    path: str | None = None
    label: str | None = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: str
    actions: list[ChatAction] = Field(default_factory=list)


class MessageRead(BaseModel):
    id: UUID
    role: str
    content: str
    actions: list = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationRead(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationRead):
    messages: list[MessageRead] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


async def _get_owned_conversation(
    db: AsyncSession, conversation_id: UUID, tenant_id: UUID, user_id: UUID
) -> AssistantConversation:
    conv = (
        await db.execute(
            select(AssistantConversation).where(
                AssistantConversation.id == str(conversation_id),
                AssistantConversation.tenant_id == str(tenant_id),
                AssistantConversation.user_id == str(user_id),
            )
        )
    ).scalar_one_or_none()
    if conv is None:
        raise not_found("Conversación")
    return conv


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(
    body: ChatRequest,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    tenant_id = _tenant(cu)
    cfg = await load_tenant_ai(db, tenant_id)
    if cfg.mode == "disabled":
        raise AppError(409, "AI_DISABLED", "La IA está deshabilitada en este tenant")

    # Conversación: continúa la existente (validada por dueño) o crea una.
    if body.conversation_id is not None:
        conv = await _get_owned_conversation(db, body.conversation_id, tenant_id, cu.id)
    else:
        conv = AssistantConversation(
            tenant_id=str(tenant_id),
            user_id=str(cu.id),
            title=body.message.strip()[:80] or "Conversación",
        )
        db.add(conv)
        await db.flush()

    # Historial previo para multi-turno.
    prior = (
        await db.execute(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == str(conv.id))
            .order_by(AssistantMessage.created_at)
        )
    ).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in prior]

    prompt = build_assistant_prompt(body.message, body.page_context, history)
    platform_cfg = await resolve_groq_config(db) if cfg.mode == "platform" else None

    try:
        result = await generate_for_tenant(
            prompt,
            system=ASSISTANT_SYSTEM,
            tenant_ai_mode=cfg.mode,
            platform_groq_config=platform_cfg,
            byo_config=cfg.byo,
            tenant_id=str(tenant_id),
            json_mode=True,
        )
    except Exception as exc:
        raise AppError(
            502,
            "AI_PROVIDER_ERROR",
            "El proveedor IA falló al generar la respuesta",
            {"error": str(exc)[:200]},
        ) from exc

    message, actions = parse_assistant_reply(result.text or "")

    # Persiste ambos turnos.
    db.add(
        AssistantMessage(
            conversation_id=str(conv.id), role="user", content=body.message, actions=[]
        )
    )
    db.add(
        AssistantMessage(
            conversation_id=str(conv.id),
            role="assistant",
            content=message,
            actions=actions,
        )
    )
    conv.updated_at = datetime.now(UTC)
    await db.commit()

    return ChatResponse(
        conversation_id=UUID(str(conv.id)),
        message=message,
        actions=[ChatAction(**a) for a in actions],
    )


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationRead]:
    tenant_id = _tenant(cu)
    rows = (
        await db.execute(
            select(AssistantConversation)
            .where(
                AssistantConversation.tenant_id == str(tenant_id),
                AssistantConversation.user_id == str(cu.id),
            )
            .order_by(desc(AssistantConversation.updated_at))
            .limit(50)
        )
    ).scalars().all()
    return [ConversationRead.model_validate(r) for r in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    tenant_id = _tenant(cu)
    conv = await _get_owned_conversation(db, conversation_id, tenant_id, cu.id)
    msgs = (
        await db.execute(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == str(conv.id))
            .order_by(AssistantMessage.created_at)
        )
    ).scalars().all()
    detail = ConversationDetail.model_validate(conv)
    detail.messages = [MessageRead.model_validate(m) for m in msgs]
    return detail


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_owned_conversation(db, conversation_id, tenant_id, cu.id)
    await db.execute(
        delete(AssistantConversation).where(
            AssistantConversation.id == str(conversation_id)
        )
    )
    await db.commit()
    return Response(status_code=204)
