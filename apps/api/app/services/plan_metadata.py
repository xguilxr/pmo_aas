"""US-090 — auto-computa metadata MS Project-like sobre `tasks`.

Helpers usados desde el endpoint de tasks:
- `compute_outline_level(wbs_code)` → smallint desde `wbs_code.split('.').length`.
- `compute_duration_days(start, end)` → días inclusivos.
- `validate_duration_max_21(d)` → 422 si excede.
- `validate_predecessors(predecessors, all_tasks_by_wbs, current_wbs)` →
  cada wbs_code referenciado debe existir en el proyecto + DAG check.
- `recompute_successors_for_project(db, project_id)` → barre todas las
  tasks del proyecto y reconstruye sus arrays `successors`.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import mensaje, validation_error
from app.models.task import Task

DURATION_MAX_DAYS = 21


def compute_outline_level(wbs_code: str | None) -> int | None:
    """`wbs_code='1.2.3'` → 3. Sin wbs_code → None."""
    if not wbs_code:
        return None
    parts = [p for p in wbs_code.split(".") if p]
    return len(parts) or None


def compute_duration_days(start: date | None, end: date | None) -> int | None:
    """Días inclusivos: same-day → 1; start=01-01, end=01-05 → 5."""
    if start is None or end is None:
        return None
    delta = (end - start).days + 1
    return delta if delta >= 0 else None


def ensure_duration_max_21(value: int | None) -> None:
    """ENH-094: 21 días es recomendación, no regla dura. La función se
    mantiene para no romper imports existentes pero ya no levanta 422.
    Las actividades macro (meses) se permiten; el frontend muestra
    warning visual cuando `duration_days > DURATION_MAX_DAYS`."""
    return None


def duration_warning(value: int | None) -> str | None:
    """Devuelve mensaje de warning si la duración excede el máximo
    recomendado. None cuando está dentro del rango o la duración es
    desconocida."""
    if value is None or value <= DURATION_MAX_DAYS:
        return None
    return (
        f"duration_days excede el máximo recomendado de "
        f"{DURATION_MAX_DAYS} días (actual: {value}). Es válido para "
        "actividades macro, pero considera dividirla en sub-tareas si "
        "es operativa."
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
                mensaje(
                    que=f"predecessor wbs_code={s!r} no existe en el proyecto",
                    porque="La dependencia apunta a una tarea que no está en el plan.",
                    accion="Corrige el código en el archivo, o importa antes la tarea que falta.",
                )
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
                    mensaje(
                        que=f"predecessors forma ciclo (vía wbs_code={p!r})",
                        porque="Un ciclo de dependencias no tiene orden posible y el cronograma no se puede calcular.",
                        accion="Rompe el ciclo quitando una de las dependencias.",
                    )
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
            if not t.wbs_code:
                continue
            succ_by_wbs.setdefault(pred_wbs, []).append(t.wbs_code)
    # Asigna ordenado, dedupe, lista vacía si no hay.
    for t in rows:
        if t.wbs_code and t.wbs_code in succ_by_wbs:
            t.successors = sorted(set(succ_by_wbs[t.wbs_code]), key=wbs_sort_key)
        else:
            t.successors = []


def wbs_sort_key(wbs_code: str | None) -> tuple:
    """BUG-049 — natural sort por segmento. `1.10` > `1.2`. Segmentos no
    numéricos van al final (flag 1 vs 0) preservando orden lexicográfico."""
    if not wbs_code:
        return ((2,),)
    parts: list[tuple[int, int, str]] = []
    for seg in wbs_code.split("."):
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
        if t.wbs_code:
            out[t.wbs_code] = t
    return out


def round_half_up(value: float) -> int:
    """Redondeo aritmético estándar (0.5 → arriba), distinto del banker's
    rounding de `round()`. `92.5 → 93`, `61.67 → 62`. Lo usamos para que
    los % de avance mostrados coincidan con el promedio esperado."""
    return int(math.floor(value + 0.5))


def parent_wbs(wbs_code: str | None) -> str | None:
    """`'1.2.3'` → `'1.2'`; `'1'` → None (raíz); sin wbs_code → None."""
    if not wbs_code:
        return None
    parts = [p for p in wbs_code.split(".") if p]
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])


def nearest_ancestor_wbs(wbs_code: str | None, wbs_set: set[str]) -> str | None:
    """ENH-197 — ancestro EXISTENTE más cercano subiendo por prefijos.

    `'1.30.1'` → `'1.30'` si existe; si no, `'1'`; si ningún prefijo
    existe → None (raíz). Garantiza que "todo lo que empieza con 1.x
    cuelga de 1" aunque falten niveles intermedios en el plan."""
    pw = parent_wbs(wbs_code)
    while pw:
        if pw in wbs_set:
            return pw
        pw = parent_wbs(pw)
    return None


def compute_wbs_rollup(tasks: Iterable[Task]) -> dict[str, float]:
    """Rollup jerárquico de avance por WBS.

    El avance efectivo de una tarea CON hijos es el promedio simple del
    avance efectivo de sus hijos (recursivo, nivel por nivel). Una HOJA
    usa su `progress` almacenado (0..100). La jerarquía se deriva del
    código WBS: ENH-197 — cada tarea cuelga de su ancestro EXISTENTE
    más cercano ('1.30.1' sin '1.30' cuelga de '1'), no solo del padre
    directo. Tareas sin WBS o sin ningún ancestro → hojas raíz.

    Devuelve ``{str(task.id): avance_efectivo}`` para TODAS las tareas.
    """
    items = list(tasks)
    by_wbs: dict[str, Task] = {}
    for t in items:
        if t.wbs_code:
            by_wbs[t.wbs_code] = t
    wbs_set = set(by_wbs)
    children: dict[str, list[Task]] = {}
    for t in items:
        anc = nearest_ancestor_wbs(t.wbs_code, wbs_set)
        if anc and (t.wbs_code is None or anc != t.wbs_code):
            children.setdefault(anc, []).append(t)

    cache: dict[str, float] = {}

    def effective(t: Task) -> float:
        tid = str(t.id)
        cached = cache.get(tid)
        if cached is not None:
            return cached
        kids = children.get(t.wbs_code) if t.wbs_code else None
        if kids:
            value = sum(effective(k) for k in kids) / len(kids)
        else:
            value = float(t.progress or 0)
        cache[tid] = value
        return value

    return {str(t.id): effective(t) for t in items}


def compute_plan_rollup_progress(tasks: Iterable[Task]) -> float | None:
    """Avance general del proyecto = promedio simple del avance efectivo
    de los items de nivel más alto (raíces WBS).

    ``None`` si no hay tareas. Reproduce el criterio del owner: el avance
    general es el promedio de los WBS de nivel más alto, donde cada padre
    es el promedio recursivo de sus hijos.
    """
    items = list(tasks)
    if not items:
        return None
    rollup = compute_wbs_rollup(items)
    wbs_set = {t.wbs_code for t in items if t.wbs_code}
    # ENH-197: raíz = sin NINGÚN ancestro existente (consistente con el
    # attach por ancestro más cercano del rollup).
    roots = [t for t in items if nearest_ancestor_wbs(t.wbs_code, wbs_set) is None]
    if not roots:
        return None
    return sum(rollup[str(t.id)] for t in roots) / len(roots)
