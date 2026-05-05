"""Schema compartido para el preview de hard-delete (US-088)."""
from __future__ import annotations

from pydantic import BaseModel


class HardDeletePreview(BaseModel):
    entity_type: str
    entity_id: str
    entity_name: str
    is_active: bool
    confirm_slug: str
    cascades: dict[str, int]
    blockers: list[str] = []
