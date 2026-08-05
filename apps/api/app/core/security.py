from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_ROUNDS)


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def _encode(payload: dict[str, Any], secret: str, ttl_sec: int) -> str:
    to_encode = payload.copy()
    now = datetime.now(UTC)
    to_encode.update({"iat": now, "exp": now + timedelta(seconds=ttl_sec)})
    return jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    *,
    subject: str | UUID,
    tenant_ids: list[str],
    active_tenant_id: str | None,
    is_superadmin: bool,
    roles: list[str],
) -> str:
    return _encode(
        {
            "sub": str(subject),
            "tenant_ids": [str(t) for t in tenant_ids],
            "active_tenant_id": str(active_tenant_id) if active_tenant_id else None,
            "is_superadmin": is_superadmin,
            "roles": roles,
            "type": "access",
        },
        secret=settings.JWT_SECRET,
        ttl_sec=settings.ACCESS_TOKEN_TTL_SEC,
    )


def create_refresh_token(*, subject: str | UUID, jti: str) -> str:
    return _encode(
        {"sub": str(subject), "jti": jti, "type": "refresh"},
        secret=settings.JWT_REFRESH_SECRET,
        ttl_sec=settings.REFRESH_TOKEN_TTL_SEC,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ValueError("invalid_token") from exc


def decode_refresh_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ValueError("invalid_refresh") from exc


PASSWORD_POLICY_MIN_LEN = 8


def validate_password_policy(password: str) -> tuple[bool, str | None]:
    """Return (ok, error_code). Policy: min 8 chars, 1 upper, 1 digit, 1 symbol."""
    if len(password) < PASSWORD_POLICY_MIN_LEN:
        return False, "password_too_short"
    if not any(c.isupper() for c in password):
        return False, "password_missing_uppercase"
    if not any(c.isdigit() for c in password):
        return False, "password_missing_digit"
    symbols = set("!@#$%^&*()-_=+[]{};:,.<>/?|`~'\"\\")
    if not any(c in symbols for c in password):
        return False, "password_missing_symbol"
    return True, None
