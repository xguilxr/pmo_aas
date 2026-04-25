"""US-078 — modelo opt-out para membership user↔organización.

Default: el user del tenant tiene acceso a TODAS las organizaciones
del tenant. Si el admin quiere excluirlo de una org puntual, inserta
una fila aquí. Crear/borrar la fila la hace el admin desde
`/admin/users/{id}` con la capability `users.manage`.

El filtrado efectivo (que el user X no vea proyectos de la org Y) se
deja como ENH separado — esta US solo almacena el dato. Ver
`docs/epics/EP002-org-hierarchy.md` (sección post-DEC-024).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid


class OrganizationUserExclusion(Base):
    __tablename__ = "organization_user_exclusions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "organization_id", name="uq_org_user_excl_pair"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
