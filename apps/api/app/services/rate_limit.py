"""Rate limiting sencillo vía Redis INCR + EXPIRE (US-063).

Patrón intencionalmente minimalista — un sliding-window real requiere
sorted-sets o Lua scripting. Para el volumen esperado (auth endpoints,
~unidades/min por tenant) un counter por ventana fija es suficiente.

`check_and_increment(key, max_attempts, window_sec)`:
  - Incrementa `key` atómicamente en Redis.
  - Si el valor post-INCR > max_attempts → retorna False (bloqueado).
  - En el primer INCR fija EXPIRE de `window_sec`.
  - Si Redis está caído, devuelve True (fail-open): en auth preferimos
    que el flujo funcione aunque no podamos contabilizar, y loguear.

Los callers arman la key incluyendo el nombre del endpoint y la
dimensión (ip / email). Ejemplos: `rl:forgot:ip:1.2.3.4`,
`rl:reset:ip:1.2.3.4`.
"""
from __future__ import annotations

import logging
from functools import lru_cache

import redis

from app.core.config import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> redis.Redis | None:
    url = settings.REDIS_URL
    if not url:
        return None
    try:
        return redis.from_url(url, decode_responses=True, socket_timeout=2.0)
    except Exception as exc:
        log.warning("redis init failed: %s", exc)
        return None


def check_and_increment(
    key: str, *, max_attempts: int, window_sec: int
) -> bool:
    """Retorna True si el llamado queda dentro del límite; False si lo excede.

    Fail-open ante errores Redis (preferible a dejar a los users sin
    poder loguearse si Redis muere)."""
    client = _get_client()
    if client is None:
        return True
    try:
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_sec)
        return int(count) <= max_attempts
    except Exception as exc:
        log.warning("rate_limit check failed key=%s: %s", key, exc)
        return True


def reset(key: str) -> None:
    """Limpia el contador. Se llama al tener un éxito definitivo
    (p. ej. reset-password exitoso → permitir reintento normal en el
    futuro sin esperar la ventana)."""
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as exc:
        log.warning("rate_limit reset failed key=%s: %s", key, exc)
