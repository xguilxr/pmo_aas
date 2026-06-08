"""US-167 — Asignaciones de visibilidad positivas para usuarios PM.

Por defecto los usuarios con role_type='user' (PM) no ven nada hasta que
se les asigna explícitamente acceso a una org, programa o proyecto.
La visibilidad hereda hacia abajo:
- Org → todos sus programas y proyectos.
- Program → todos sus proyectos (y la org queda visible como contexto).
- Project → solo ese proyecto (org y programa quedan visibles como contexto).

Admin y pm_sr ignoran esta tabla — siempre ven todo.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid

ScopeType = Literal["organization", "program", "project"]


class UserScopeAssignment(Base):
    __tablename__ = "user_scope_assignments"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "scope_type", "scope_id",
            name="uq_user_scope_assignment",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 'organization' | 'program' | 'project'
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # FK lógico al id del scope (org/program/project) — no forzado en DB
    # porque apunta a tablas distintas según scope_type.
    scope_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
