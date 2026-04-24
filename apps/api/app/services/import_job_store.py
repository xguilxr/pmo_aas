"""US-070 — Redis helper para el wizard de import de tareas.

Guarda y recupera el parse preview (con TTL 1h) entre los endpoints
`POST /tasks/import/preview` y `POST /tasks/import/{job_id}/confirm`.

Patrón de key: `import:job:{job_id}`. Fail-loud (raise) si Redis está
caído — a diferencia de `rate_limit.py` que hace fail-open, acá la
pérdida de estado es crítica (no podés confirmar sin el preview).
"""
from __future__ import annotations

import json
import logging
import uuid

import redis

from app.core.config import settings

log = logging.getLogger(__name__)

JOB_TTL_SECONDS = 3600  # 1 hora — coincide con el issue #123 CA.


def _get_client() -> redis.Redis:
    """Lazy singleton. No cacheado con lru_cache porque queremos que
    cada request pueda detectar pérdida de conexión — el módulo se
    importa una vez pero el cliente se recrea si falla.

    Raises:
        RuntimeError: si `REDIS_URL` está vacío.
        redis.ConnectionError: si no se puede conectar.
    """
    url = settings.REDIS_URL
    if not url:
        raise RuntimeError("REDIS_URL no configurado — wizard de import requiere Redis")
    return redis.from_url(url, decode_responses=True, socket_timeout=2.0)


def _key(job_id: str) -> str:
    return f"import:job:{job_id}"


def create_job_id() -> str:
    return str(uuid.uuid4())


def save_preview(job_id: str, payload: dict) -> None:
    """Serializa `payload` como JSON y lo guarda con TTL 1h.

    El `payload` debe ser JSON-serializable. Raises si la serialización
    o el set en Redis fallan — el endpoint traduce a 500.
    """
    client = _get_client()
    data = json.dumps(payload, default=str)
    client.set(_key(job_id), data, ex=JOB_TTL_SECONDS)


def load_preview(job_id: str) -> dict | None:
    """Devuelve el payload guardado o `None` si el `job_id` no existe
    o el TTL expiró. El endpoint de confirm traduce `None` a `410 Gone`.
    """
    client = _get_client()
    raw = client.get(_key(job_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("import_job_store: JSON inválido para %s: %s", job_id, exc)
        return None


def delete_preview(job_id: str) -> None:
    """Remove del store post-confirm exitoso. No raise si no existía."""
    client = _get_client()
    try:
        client.delete(_key(job_id))
    except Exception as exc:
        log.warning("import_job_store delete failed %s: %s", job_id, exc)
