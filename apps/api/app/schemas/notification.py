"""Schemas Pydantic para notificaciones (US-027)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: UUID
    type: str
    title: str
    body: str | None
    entity_type: str | None
    entity_id: str | None
    link: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCount(BaseModel):
    count: int


class NotificationPreferencesIn(BaseModel):
    # Kill-switch global; si False, no se manda ningún email (no importa
    # el override por tipo).
    email_enabled: bool | None = None
    # Override por tipo: "email_and_inapp" | "inapp_only".
    by_type: dict[str, str] | None = None


class NotificationPreferencesOut(BaseModel):
    email_enabled: bool
    by_type: dict[str, str]
