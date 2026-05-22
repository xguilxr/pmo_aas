"""ENH-103 — Match participantes de minuta ↔ actores del proyecto.

Reglas:

- Match case-insensitive, fuzzy (``SequenceMatcher`` ratio ≥ 0.85) por
  nombre completo contra los `Actor` ligados al proyecto vía
  `project_participations`.
- Match exitoso → el participante queda enriquecido con
  ``actor_id`` + ``match_status="matched"`` + ``verified=True``.
- Sin match → crea un nuevo ``Actor`` con ``auto_created=True,
  verified=False`` y lo agrega al proyecto vía
  ``ProjectParticipation`` con rol "guest" (sin team / sin área / no
  primary). El participante queda enriquecido con el nuevo
  ``actor_id`` + ``match_status="auto_created"`` + ``verified=False``.

El caller controla el commit. Esta función solo hace ``db.add`` +
``db.flush`` para asignar IDs.
"""
from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Actor
from app.models.project_participation import ProjectParticipation

# Umbral de similitud para considerar match exitoso. Conservador para
# evitar falsos positivos cuando hay nombres parecidos.
_MATCH_THRESHOLD: float = 0.85


def _normalize(name: str | None) -> str:
    """Lowercase + trim + strip diacritics (NFD). Así "María López"
    matchea con "maria lopez" sin bajar el umbral fuzzy.
    """
    raw = (name or "").strip().lower()
    nfd = unicodedata.normalize("NFD", raw)
    return "".join(ch for ch in nfd if not unicodedata.combining(ch))


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


async def match_participants(
    db: AsyncSession,
    *,
    project_id: UUID | str,
    tenant_id: UUID | str,
    participants: list[dict[str, Any]],
    created_by: UUID | str | None = None,
) -> list[dict[str, Any]]:
    """Enriquece la lista de participantes con match contra los actores
    del proyecto. Retorna una nueva lista con los mismos dicts más los
    campos ``actor_id``, ``match_status``, ``verified``.

    Items sin ``name`` o con name vacío se devuelven sin cambios.
    """
    if not participants:
        return []

    # Carga todos los actores ligados al proyecto vía participations.
    # Tomamos el snapshot de una sola pasada — el matcher es por minuta.
    rows = (
        await db.execute(
            select(Actor)
            .join(
                ProjectParticipation,
                ProjectParticipation.actor_id == Actor.id,
            )
            .where(
                ProjectParticipation.project_id == str(project_id),
                ProjectParticipation.is_active.is_(True),
                Actor.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    candidates: list[tuple[Actor, str]] = [
        (a, _normalize(a.name)) for a in rows
    ]

    out: list[dict[str, Any]] = []
    for raw in participants:
        if not isinstance(raw, dict):
            out.append(raw)
            continue
        # Preserva todos los campos originales — el matcher solo agrega.
        enriched: dict[str, Any] = dict(raw)
        name = _normalize(raw.get("name"))
        if not name:
            out.append(enriched)
            continue

        # Si ya viene con actor_id explícito (cliente lo resolvió), no
        # re-matchear. Solo asegurar match_status/verified.
        existing_actor_id = raw.get("actor_id")
        if existing_actor_id:
            enriched.setdefault("match_status", "matched")
            enriched.setdefault("verified", True)
            out.append(enriched)
            continue

        # Fuzzy match: el mejor candidato con ratio >= umbral.
        best: tuple[float, Actor | None] = (0.0, None)
        for actor, norm in candidates:
            r = _ratio(name, norm)
            if r > best[0]:
                best = (r, actor)

        if best[1] is not None and best[0] >= _MATCH_THRESHOLD:
            actor = best[1]
            enriched["actor_id"] = str(actor.id)
            enriched["match_status"] = "matched"
            enriched["verified"] = bool(actor.verified)
            out.append(enriched)
            continue

        # Sin match → crear actor auto_created + participation guest.
        new_actor = Actor(
            tenant_id=str(tenant_id),
            name=(raw.get("name") or "").strip()[:200],
            email=(raw.get("email") or None),
            is_active=True,
            is_lead=False,
            auto_created=True,
            verified=False,
            created_by=created_by,
        )
        db.add(new_actor)
        await db.flush()

        participation = ProjectParticipation(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            actor_id=str(new_actor.id),
            is_primary=False,
            is_active=True,
            is_area_lead=False,
            created_by=created_by,
        )
        db.add(participation)
        await db.flush()

        # Lo agregamos al pool de candidatos para que duplicados dentro
        # de la misma minuta matcheen contra él en lugar de crear otro.
        candidates.append((new_actor, _normalize(new_actor.name)))

        enriched["actor_id"] = str(new_actor.id)
        enriched["match_status"] = "auto_created"
        enriched["verified"] = False
        out.append(enriched)

    return out
