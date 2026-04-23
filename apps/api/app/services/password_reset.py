"""Password reset tokens — emisión y verificación (US-063).

El flujo:

1. `issue_reset_token(user_id)` genera 32 bytes aleatorios (base64 url-safe)
   y persiste SÓLO el SHA-256 en `password_reset_tokens`. Devuelve el
   token en claro — éste viaja en el email y nunca más se vuelve a ver.
2. `consume_reset_token(plain)` computa el SHA-256, busca el registro,
   valida que esté vivo y sin usar, y lo marca `used_at`. Retorna el
   `user_id` propietario.
3. Tokens expiran en `TOKEN_TTL_MIN` minutos (default 30).

El token no incluye el user_id en sí — sólo es una cadena aleatoria
grande. La FK al user vive en la BD. Esto evita que un usuario pueda
forzar tokens para otros users (un UUID v4 predecible sería vulnerable
a enumeración, un HMAC con user_id dentro filtra información al
exponerse el token).
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import PasswordResetToken

TOKEN_TTL_MIN: int = 30
TOKEN_BYTES: int = 32  # 32 bytes de entropía → 43 chars base64 url-safe


def _hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


async def issue_reset_token(
    db: AsyncSession, *, user_id: UUID | str, ip_address: str | None = None
) -> str:
    """Crea un token nuevo, persiste su hash, devuelve el plaintext.

    No anula tokens previos del mismo user — el último emitido y
    no-usado se consume, los anteriores caducan solos. Si el user spamea
    el endpoint, el rate-limit los frena antes de inundar la tabla.
    """
    plain = secrets.token_urlsafe(TOKEN_BYTES)
    now = datetime.now(UTC)
    token_row = PasswordResetToken(
        token_hash=_hash_token(plain),
        user_id=str(user_id),
        expires_at=now + timedelta(minutes=TOKEN_TTL_MIN),
        used_at=None,
        ip_address=ip_address,
        created_at=now,
    )
    db.add(token_row)
    await db.flush()
    return plain


async def consume_reset_token(
    db: AsyncSession, *, plain: str
) -> PasswordResetToken | None:
    """Busca el token por hash y lo marca usado si está vivo.

    Retorna el row (con `user_id`) o None. El caller decide qué hacer
    con None (endpoint responde 400 genérico, sin revelar si el token
    no existió vs expiró vs ya estaba usado — igual para todos los
    fallos por seguridad)."""
    if not plain or len(plain) < 20:
        return None
    h = _hash_token(plain)
    row = (
        await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == h)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    now = datetime.now(UTC)
    expires_at = row.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at is not None and expires_at < now:
        return None
    if row.used_at is not None:
        return None
    row.used_at = now
    await db.flush()
    return row
