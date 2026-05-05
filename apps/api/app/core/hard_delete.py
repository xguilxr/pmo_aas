"""Hard-delete helpers (US-088).

Patrón two-step:
  1. UI llama `DELETE` clásico → entidad pasa a `is_active=False` (soft).
  2. UI llama `DELETE /<entity>/{id}/permanent?confirm=<slug>` → físico.

El helper sólo encapsula:
  - cómputo del slug determinístico que el usuario debe re-tipear,
  - chequeo de `is_active=False` antes de permitir hard delete,
  - chequeo de match slug (devuelve preview en `fields` si falla).

La cascada misma se implementa en cada endpoint: el modelo de FK varía
(algunas relaciones tienen `ondelete="CASCADE"` y otras no — ver ADR-017).
"""
from __future__ import annotations

import re

from app.core.errors import conflict, validation_error

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def confirm_slug(entity_type: str, entity_name: str) -> str:
    """Slug determinístico que el usuario debe re-tipear para confirmar.

    Formato: ``<type>:<nombre-normalizado-40c>``. Ej.: ``program:duplicado-2``.

    Es estable (mismo input → mismo slug) para que el frontend pueda
    pre-renderizarlo en el modal y validar input on-change.
    """
    name = entity_name.strip().lower()
    safe = _SLUG_RE.sub("-", name).strip("-")[:40] or "unnamed"
    return f"{entity_type}:{safe}"


def ensure_inactive(is_active: bool, label: str) -> None:
    """Bloquea hard delete si la entidad sigue activa (forzar soft primero)."""
    if is_active:
        raise conflict(
            f"{label} debe estar desactivado antes de eliminarse permanentemente. "
            "Usa el borrado normal primero (segunda confirmación).",
            code="MUST_DEACTIVATE_FIRST",
        )


def ensure_confirm(provided: str, expected: str, preview: dict | None = None) -> None:
    """Valida que el slug recibido por query coincida con el esperado.

    Si no, lanza 400 con el preview de cascada en `fields` para que el
    cliente pueda re-renderizar el modal con datos frescos.
    """
    if provided != expected:
        fields: dict = {"expected": expected}
        if preview is not None:
            fields["preview"] = preview
        raise validation_error(
            "confirm slug no coincide con el esperado",
            fields=fields,
        )
