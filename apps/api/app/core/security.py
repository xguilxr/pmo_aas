from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.contrasenas_filtradas import esta_filtrada
from app.core.errors import mensaje

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
    """Return (ok, error_code). Policy: 8..128 chars, 1 upper, 1 digit, 1 symbol,
    y que no esté en el conjunto de contraseñas filtradas (ASVS 2.1.7).

    El contraste contra las filtradas va **aquí dentro** y no en cada endpoint a
    propósito: hay seis sitios que fijan una contraseña —cambio, restablecimiento,
    alta por administrador, alta de inquilino, y dos del superadministrador— y un
    control que hay que acordarse de llamar seis veces es un control que va a
    faltar en el séptimo. Va el último de los cinco porque es el único que
    cuesta una búsqueda en un conjunto de 23.000 entradas.
    """
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
    if esta_filtrada(password):
        return False, "password_breached"
    return True, None


def mensaje_de_politica(codigo: str | None) -> str:
    """Las tres partes de LEN-02 para cada motivo de rechazo.

    Existe porque `password_breached` no se puede explicar con el texto que
    había. Los seis sitios decían variantes de «no cumple la política… usa
    mayúsculas, números y símbolos», y a quien escribió `Password1!` —que las
    lleva todas— ese texto le dice que haga exactamente lo que ya hizo.

    De paso arregla una evidencia que no era cierta: el alta de usuario ya
    prometía «y que no sea una contraseña común» antes de que nada lo
    comprobara.
    """
    if codigo == "password_breached":
        return mensaje(
            que="Esa contraseña aparece en filtraciones públicas conocidas.",
            porque=(
                "Cumple las reglas, pero es de las que un atacante prueba primero: "
                "casi todo el mundo satisface «mayúscula, número y símbolo» de la "
                "misma forma, y esa contraseña es una de las que salen."
            ),
            accion=(
                "Elige una que no derive de una palabra común. Tres o cuatro "
                "palabras sin relación entre sí son más seguras y más fáciles de "
                "recordar que sustituir letras por símbolos."
            ),
        )
    if codigo == "password_too_long":
        return mensaje(
            que=f"La contraseña pasa de {PASSWORD_POLICY_MAX_LEN} caracteres.",
            porque="Es el máximo declarado por la plataforma.",
            accion=f"Recórtala a {PASSWORD_POLICY_MAX_LEN} caracteres o menos.",
        )
    return mensaje(
        que="La contraseña no cumple la política de la plataforma.",
        porque=(
            f"Se exigen al menos {PASSWORD_POLICY_MIN_LEN} caracteres con una "
            f"mayúscula, un número y un símbolo. Es lo que encarece adivinarla."
        ),
        accion="Añade lo que falte y vuelve a guardar.",
    )
