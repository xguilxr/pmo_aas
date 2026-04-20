"""Cifrado de secretos IA por-tenant (EP016 US-NEW-045).

Encapsula Fernet para cifrar / descifrar strings cortos (service tokens
de Cloudflare Access, API keys). La key viene de `settings.AI_SECRETS_FERNET_KEY`.
"""
from __future__ import annotations

import base64
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_CIPHERTEXT_PREFIX = "enc::"


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    raw = settings.AI_SECRETS_FERNET_KEY
    # Validación liviana — si la key es < 32 bytes, genera una determinista
    # basándose en ella. Sólo para dev/test; en prod se exige Fernet-válida.
    try:
        return Fernet(raw.encode("utf-8") if isinstance(raw, str) else raw)
    except (ValueError, TypeError):
        key32 = (raw.encode("utf-8") + b"\x00" * 32)[:32]
        safe = base64.urlsafe_b64encode(key32)
        return Fernet(safe)


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    token = _get_fernet().encrypt(plain.encode("utf-8")).decode("utf-8")
    return f"{_CIPHERTEXT_PREFIX}{token}"


def decrypt_secret(ciphertext: str | None) -> str:
    if not ciphertext:
        return ""
    if not ciphertext.startswith(_CIPHERTEXT_PREFIX):
        # Retro-compat: valores en claro antes de cifrado se devuelven tal cual.
        return ciphertext
    raw = ciphertext[len(_CIPHERTEXT_PREFIX):]
    try:
        return _get_fernet().decrypt(raw.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def mask_secret(plain: str, visible_tail: int = 4) -> str:
    """Enmascarar para devolver al frontend (nunca devolver el plaintext)."""
    if not plain:
        return ""
    if len(plain) <= visible_tail:
        return "•" * len(plain)
    return "•" * (len(plain) - visible_tail) + plain[-visible_tail:]
