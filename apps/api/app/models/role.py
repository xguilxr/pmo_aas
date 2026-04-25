# DEPRECATED US-077 + DEC-024 — el modelo de permisos pasó de
# (role × module × action) a 5 capabilities admin (`tenant.manage`,
# `ai.configure`, `users.manage`, `organizations.delete`, `audit.read`).
# `Role.permissions` JSON se ignora desde US-076 (`CurrentUser.has_capability`).
# Las tablas `roles` y `user_roles` quedan vivas como compat, pero la UI
# `/admin/roles/*` y los endpoints `admin_roles.py` se borraron en US-077.
# Borrado físico de las tablas → US-081 (Sprint 7) tras validación.
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Role(Base, TimestampMixin):
    """DEPRECATED US-077 — borrar en US-081 (Sprint 7)."""
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),)

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permissions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class UserRole(Base):
    """DEPRECATED US-077 — borrar en US-081 (Sprint 7)."""

    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
