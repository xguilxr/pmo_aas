"""US-090 — auto-computa metadata MS Project-like sobre `tasks`.

Helpers usados desde el endpoint de tasks:
- `compute_outline_level(wbs)` → smallint desde `wbs.split('.').length`.
- `compute_duration_days(start, end)` → días inclusivos.
- `validate_duration_max_21(d)` → 422 si excede.
- `validate_predecessors(predecessors, all_tasks_by_wbs, current_wbs)` →
  cada wbs referenciado debe existir en el proyecto + DAG check.
- `recompute_successors_for_project(db, project_id)` → barre todas las
  tasks del proyecto y reconstruye sus arrays `successors`.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import validation_error
from app.models.task import Task

DURATION_MAX_DAYS = 21


def compute_outline_level(wbs: str | None) -> int | None:
    """`wbs='1.2.3'` → 3. Sin wbs → None."""
    if not wbs:
        return None
    parts = [p for p in wbs.split(".") if p]
    return len(parts) or None


def compute_duration_days(start: date | None, end: date | None) -> int | None:
    """Días inclusivos: same-day → 1; start=01-01, end=01-05 → 5."""
    if start is None or end is None:
        return None
    delta = (end - start).days + 1
    return delta if delta >= 0 else None


def ensure_duration_max_21(value: int | None) -> None:
    """Levanta 422 si excede el máximo. None pasa sin validar."""
    if value is None:
        return
    if value > DURATION_MAX_DAYS:
        raise validation_error(
            f"duration_days excede el máximo de {DURATION_MAX_DAYS} días "
            f"(actual: {value}). Acorta start_date / end_date."
        )


def validate_predecessors(
    predecessors: list[str] | None,
    by_wbs: dict[str, Task],
    current_wbs: str | None,
) -> list[str]:
    """Cada referencia debe existir + no formar ciclo. Devuelve lista
    sanitizada (strip + dedupe + sin self)."""
    if not predecessors:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for p in predecessors:
        s = (p or "").strip()
        if not s or s == current_wbs or s in seen:
            continue
        if s not in by_wbs:
            raise validation_error(
                f"predecessor wbs={s!r} no existe en el proyecto"
            )
        cleaned.append(s)
        seen.add(s)
    # Cycle detection: simple DFS desde cada predecessor por sus propios
    # predecessors. Si alguna ruta llega a `current_wbs` → ciclo.
    if current_wbs:
        visiting: set[str] = set()

        def has_path_to_current(node_wbs: str) -> bool:
            if node_wbs == current_wbs:
                return True
            if node_wbs in visiting:
                return False
            visiting.add(node_wbs)
            t = by_wbs.get(node_wbs)
            if t is None:
                return False
            for parent in (t.predecessors or []):
                if has_path_to_current(parent):
                    return True
            return False

        for p in cleaned:
            if has_path_to_current(p):
                raise validation_error(
                    f"predecessors forma ciclo (vía wbs={p!r})"
                )
    return cleaned


async def recompute_successors_for_project(
    db: AsyncSession, project_id: str
) -> None:
    """Recorre todas las tasks del proyecto y reconstruye sus
    `successors` desde los `predecessors` de las demás. Idempotente."""
    rows = (
        await db.execute(select(Task).where(Task.project_id == str(project_id)))
    ).scalars().all()
    succ_by_wbs: dict[str, list[str]] = {}
    for t in rows:
        for pred_wbs in (t.predecessors or []):
            if not t.wbs:
                continue
            succ_by_wbs.setdefault(pred_wbs, []).append(t.wbs)
    # Asigna ordenado, dedupe, lista vacía si no hay.
    for t in rows:
        if t.wbs and t.wbs in succ_by_wbs:
            t.successors = sorted(set(succ_by_wbs[t.wbs]), key=wbs_sort_key)
        else:
            t.successors = []


def wbs_sort_key(wbs: str | None) -> tuple:
    """BUG-049 — natural sort por segmento. `1.10` > `1.2`. Segmentos no
    numéricos van al final (flag 1 vs 0) preservando orden lexicográfico."""
    if not wbs:
        return ((2,),)
    parts: list[tuple[int, int, str]] = []
    for seg in wbs.split("."):
        s = seg.strip()
        if s.isdigit():
            parts.append((0, int(s), ""))
        else:
            parts.append((1, 0, s))
    return tuple(parts)


def collect_by_wbs(tasks: Iterable[Task], exclude_id: str | None = None) -> dict[str, Task]:
    out: dict[str, Task] = {}
    for t in tasks:
        if exclude_id and str(t.id) == exclude_id:
            continue
        if t.wbs:
            out[t.wbs] = t
    return out
