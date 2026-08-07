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


def excede(key: str, *, max_attempts: int) -> bool:
    """`True` si el contador **ya** superó el límite, sin tocarlo.

    Existe para AM-09. El inicio de sesión no puede usar
    `check_and_increment` en la puerta: contaría también los intentos que
    salen bien, y una oficina detrás de un NAT —donde decenas de personas
    comparten IP y aciertan la contraseña— se quedaría fuera. Lo que se cuenta
    ahí son los **fallos**, así que hace falta consultar antes y sumar después.

    Fail-open ante errores de Redis, por lo mismo que `check_and_increment`:
    preferimos no poder contabilizar a dejar a todos sin iniciar sesión.
    """
    client = _get_client()
    if client is None:
        return False
    try:
        actual = client.get(key)
        return actual is not None and int(actual) >= max_attempts
    except Exception as exc:
        log.warning("rate_limit peek failed key=%s: %s", key, exc)
        return False


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


#: ASVS 11.1.4 — peticiones por cuenta y por minuto.
#:
#: El número sale de contar contra el uso real, no de una corazonada: la carga
#: del tablero es la pantalla que más pide de toda la aplicación, y son decenas
#: de peticiones, no cientos. 600/min deja **veinte veces** ese margen y sigue
#: cortando lo que el control persigue: recorrer la cartera entera a máxima
#: velocidad, que con páginas de 100 son 60.000 filas por minuto sin freno.
#:
#: Generoso a propósito. Un límite que corta a alguien trabajando se sube al
#: día siguiente hasta que deja de servir; uno que nadie legítimo alcanza
#: sobrevive, y es el que sigue ahí cuando hace falta.
PRESUPUESTO_POR_MINUTO = 600
_VENTANA_PRESUPUESTO_SEC = 60


def verifica_presupuesto(user_id: str) -> bool:
    """`True` si esta petición cabe en el presupuesto de la cuenta.

    Fail-open ante Redis caído, como todo lo demás de este módulo: dejar a
    todos los inquilinos sin API porque el limitador no puede contar sería un
    daño mayor y más probable que el que este control evita.
    """
    return check_and_increment(
        f"rl:api:user:{user_id}",
        max_attempts=PRESUPUESTO_POR_MINUTO,
        window_sec=_VENTANA_PRESUPUESTO_SEC,
    )
