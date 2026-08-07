from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PasswordResetToken(Base):
    """Token de un solo uso para 'forgot password' (US-063).

    Sólo se persiste el SHA-256 del token (token_hash). El valor en claro
    se envía por email y no se vuelve a ver. El registro se marca
    `used_at` al consumirlo; intentos posteriores fallan aunque el token
    no haya expirado.
    """

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("idx_prt_user_unused", "user_id", "used_at"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AdminOtpCode(Base):
    """Código de un solo uso para el segundo factor de administración (ASVS 4.3.1).

    Se guarda **solo el SHA-256** del código, igual que `PasswordResetToken`: si
    la base se filtra, los códigos vivos no sirven. Son seis dígitos, así que el
    resumen no protege de una tabla precalculada — protege de que un volcado de
    la base entregue códigos utilizables tal cual, que es el caso realista.

    `desafio` es lo que ata el código a **una** petición de inicio de sesión
    concreta (ASVS 2.7.3: «only usable once, and only for the original
    authentication request»). Sin él, un código pedido en una pestaña serviría
    para completar el inicio de sesión que otra persona empezó en otra parte.

    `intentos` existe porque seis dígitos son un millón de combinaciones y eso se
    prueba entero en minutos. El límite es lo que hace que el factor valga algo.
    """

    __tablename__ = "admin_otp_codes"
    __table_args__ = (
        Index("idx_otp_desafio_vivo", "desafio", "used_at"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    desafio: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
