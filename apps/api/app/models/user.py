from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_users_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="es-MX")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # MCS SEG-01 · ASVS 8.3.3 — «clear language regarding collection and use of
    # supplied personal information … opt-in consent … before it is used».
    #
    # Se guardan las **dos** cosas y no solo la fecha: sin la versión, «aceptó»
    # no dice qué aceptó, y el día que cambie el aviso no habría forma de saber
    # a quién hay que volver a preguntarle. Con las dos, comparar contra
    # `AVISO_VIGENTE` responde la pregunta sola.
    #
    # Nulable: las cuentas que existen desde antes del aviso no han aceptado
    # nada, y decir que sí por ellas sería falsificar el consentimiento — que es
    # exactamente lo que el control quiere impedir.
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    privacy_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # US-059/US-060 (DEC-020): rol simplificado fijo — reemplaza jerarquía
    # dinámica del Role legacy. Valores: "admin" | "user" | "viewer".
    # Nullable para coexistir con registros pre-migración (0026).
    role_type: Mapped[str | None] = mapped_column(String(16))
