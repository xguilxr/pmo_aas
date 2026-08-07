from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# MCS SEG-01 / ASVS 2.1.3 — bcrypt **trunca a 72 bytes en silencio**, así que
# antes de esto dos contraseñas distintas de 103 y 108 caracteres que
# compartieran los primeros 72 abrían la misma cuenta. Comprobado, no supuesto.
#
# `bcrypt_sha256` resume con HMAC-SHA256 antes de pasar por bcrypt, así que no
# hay longitud que truncar. `bcrypt` se queda como **deprecado y no retirado**:
# los hashes existentes siguen verificando y se re-escriben al esquema nuevo la
# próxima vez que su dueño inicia sesión (`necesita_rehash`). Retirarlo dejaría
# fuera a todo el mundo de golpe.
_pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated=["bcrypt"],
    bcrypt_sha256__rounds=settings.BCRYPT_ROUNDS,
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def necesita_rehash(hashed: str) -> bool:
    """¿Este hash usa un esquema que ya no es el vigente?

    Se pregunta **después** de verificar y en el punto donde la contraseña en
    claro todavía existe —el inicio de sesión—, que es el único momento en que
    se puede reescribir sin pedírsela otra vez a nadie. Una migración de
    esquema que no se cablea aquí no migra nunca.
    """
    try:
        return bool(_pwd_context.needs_update(hashed))
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


#: Mínimo. **Decisión del owner 2026-08-07 (ADR-032): se queda en 8 con reglas
#: de composición**, sabiendo que ASVS 4.0.3 L1 pide 12 sin ellas. El residual
#: está escrito en el ADR y el mapeo lo declara ACEPTADO, no CUMPLE.
PASSWORD_POLICY_MIN_LEN = 8

#: Máximo, por ASVS 2.1.2. Antes no había ninguno, y «sin máximo» sonaba
#: generoso mientras bcrypt truncaba por detrás: lo que había en realidad era
#: un máximo de 72 bytes sin declarar y sin avisar.
PASSWORD_POLICY_MAX_LEN = 128


def validate_password_policy(password: str) -> tuple[bool, str | None]:
    """Return (ok, error_code). Policy: 8..128 chars, 1 upper, 1 digit, 1 symbol."""
    if len(password) < PASSWORD_POLICY_MIN_LEN:
        return False, "password_too_short"
    if len(password) > PASSWORD_POLICY_MAX_LEN:
        return False, "password_too_long"
    if not any(c.isupper() for c in password):
        return False, "password_missing_uppercase"
    if not any(c.isdigit() for c in password):
        return False, "password_missing_digit"
    symbols = set("!@#$%^&*()-_=+[]{};:,.<>/?|`~'\"\\")
    if not any(c in symbols for c in password):
        return False, "password_missing_symbol"
    return True, None
