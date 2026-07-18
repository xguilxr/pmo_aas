"""US-190 — Revisión de calidad del plan ("plan linter").

Feedback cliente 16-jul item 4: al terminar el plan debe haber una
revisión de calidad — estructura del WBS, cierre de sección con hito,
registro de actividades críticas, duraciones acotadas, etc. — para
habilitar un buen look-ahead.

`review_plan(tasks)` es una función pura sobre las tareas del proyecto.
Devuelve observaciones accionables:

    {code, severity: error|warning|info, message, items: [wbs/nombre], count}

y `plan_quality_score(observations)` un resumen 0-100 para la UI.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import date

from app.models.task import Task
from app.services.plan_metadata import (
    DURATION_MAX_DAYS,
    nearest_ancestor_wbs,
    parent_wbs,
    wbs_sort_key,
)

_MAX_ITEMS = 10


def _obs(
    code: str,
    severity: str,
    message: str,
    items: list[str] | None = None,
    count: int | None = None,
) -> dict:
    items = items or []
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "items": items[:_MAX_ITEMS],
        "count": count if count is not None else len(items),
    }


def _label(t: Task) -> str:
    return f"{t.wbs} · {t.name}" if t.wbs else t.name


def review_plan(tasks: Iterable[Task], today: date | None = None) -> list[dict]:
    """Corre todos los checks y devuelve las observaciones (vacío = plan
    sano). `today` inyectable para tests."""
    items = list(tasks)
    today = today or date.today()
    out: list[dict] = []
    if not items:
        return [
            _obs(
                "PLAN_EMPTY", "error",
                "El plan no tiene tareas. Importá o creá el plan primero.",
                count=1,
            )
        ]

    with_wbs = [t for t in items if t.wbs]
    wbs_set = {t.wbs for t in with_wbs}
    children: dict[str, list[Task]] = {}
    for t in with_wbs:
        anc = nearest_ancestor_wbs(t.wbs, wbs_set)
        if anc:
            children.setdefault(anc, []).append(t)
    parents = set(children)
    leaves = [t for t in items if not t.wbs or t.wbs not in parents]

    # --- Estructura WBS ---
    no_wbs = [t.name for t in items if not t.wbs]
    if no_wbs:
        out.append(
            _obs(
                "WBS_MISSING", "warning",
                f"{len(no_wbs)} tarea(s) sin código WBS: quedan fuera de la "
                "jerarquía (avance, agrupado y Gantt).",
                no_wbs,
            )
        )
    dups = [w for w, n in Counter(t.wbs for t in with_wbs).items() if n > 1]
    if dups:
        out.append(
            _obs(
                "WBS_DUPLICATED", "error",
                f"WBS duplicados ({len(dups)}): rompen predecesoras, hitos "
                "relacionados y el merge del import.",
                sorted(dups, key=wbs_sort_key),
            )
        )
    orphans = sorted(
        {
            t.wbs
            for t in with_wbs
            if (pw := parent_wbs(t.wbs)) and pw not in wbs_set
        },
        key=wbs_sort_key,
    )
    if orphans:
        out.append(
            _obs(
                "WBS_ORPHAN_LEVELS", "warning",
                f"{len(orphans)} WBS cuyo nivel padre directo no existe "
                "(ej. 1.30.1 sin fila 1.30): cuelgan del ancestro más "
                "cercano, pero conviene completar la numeración.",
                [str(w) for w in orphans],
            )
        )
    # Huecos de numeración por nivel (1.1, 1.3 sin 1.2).
    gaps: list[str] = []
    by_parent: dict[str | None, list[int]] = {}
    for t in with_wbs:
        seg = str(t.wbs).split(".")[-1]
        if seg.isdigit():
            by_parent.setdefault(parent_wbs(t.wbs), []).append(int(seg))
    for parent, nums in by_parent.items():
        expected = set(range(1, max(nums) + 1))
        missing = sorted(expected - set(nums))
        prefix = f"{parent}." if parent else ""
        gaps.extend(f"{prefix}{m}" for m in missing[:3])
    if gaps:
        out.append(
            _obs(
                "WBS_GAPS", "info",
                f"Numeración WBS con huecos ({len(gaps)}): no rompe nada, "
                "pero un plan consecutivo se lee mejor (botón Auto-WBS).",
                gaps,
            )
        )

    # --- Hitos ---
    milestones = [t for t in items if t.is_milestone]
    if not milestones:
        out.append(
            _obs(
                "NO_MILESTONES", "warning",
                "El plan no tiene ningún hito: sin hitos no hay puntos de "
                "control para el look-ahead ni cierre de fases.",
                count=1,
            )
        )
    else:
        # Cierre de sección: cada sección raíz debería contener ≥1 hito.
        roots = sorted(
            (w for w in parents if nearest_ancestor_wbs(w, wbs_set) is None),
            key=wbs_sort_key,
        )

        def _descendants(w: str) -> list[Task]:
            acc: list[Task] = []
            stack = [w]
            while stack:
                cur = stack.pop()
                for ch in children.get(cur, []):
                    acc.append(ch)
                    if ch.wbs:
                        stack.append(ch.wbs)
            return acc

        no_close = [
            w
            for w in roots
            if not any(d.is_milestone for d in _descendants(w))
        ]
        if no_close:
            out.append(
                _obs(
                    "SECTION_NO_MILESTONE", "warning",
                    f"{len(no_close)} sección(es) sin hito de cierre: cada "
                    "fase/sección debería terminar en un hito verificable.",
                    [str(w) for w in no_close],
                )
            )

    # --- Actividades críticas ---
    if not any(getattr(t, "is_critical", False) for t in items):
        out.append(
            _obs(
                "NO_CRITICAL_TASKS", "warning",
                "Ninguna tarea está marcada como crítica: identificá la "
                "ruta crítica para priorizar el seguimiento.",
                count=1,
            )
        )

    # --- Duraciones y fechas (sobre hojas; los padres son resumen) ---
    long_tasks = [
        _label(t)
        for t in leaves
        if not t.is_milestone and (t.duration_days or 0) > DURATION_MAX_DAYS
    ]
    if long_tasks:
        out.append(
            _obs(
                "LONG_TASKS", "warning",
                f"{len(long_tasks)} tarea(s) operativas de más de "
                f"{DURATION_MAX_DAYS} días: dividilas en sub-tareas para "
                "poder medir avance semanal (look-ahead).",
                long_tasks,
            )
        )
    no_dates = [
        _label(t)
        for t in leaves
        if not t.is_milestone and (t.start_date is None or t.end_date is None)
    ]
    if no_dates:
        out.append(
            _obs(
                "MISSING_DATES", "warning",
                f"{len(no_dates)} tarea(s) sin fecha de inicio o fin: sin "
                "fechas no entran al Gantt ni al look-ahead.",
                no_dates,
            )
        )
    no_owner = [
        _label(t)
        for t in leaves
        if not t.is_milestone
        and t.assignee_actor_id is None
        and t.owner_id is None
        and t.area_id is None
    ]
    if no_owner:
        out.append(
            _obs(
                "NO_OWNER", "info",
                f"{len(no_owner)} tarea(s) sin responsable ni área: nadie "
                "las va a reportar en el seguimiento.",
                no_owner,
            )
        )
    stale = [
        _label(t)
        for t in leaves
        if not t.is_milestone
        and t.end_date is not None
        and t.end_date < today
        and (t.progress or 0) == 0
        and t.status in ("not_started", None)
    ]
    if stale:
        out.append(
            _obs(
                "OVERDUE_NOT_STARTED", "info",
                f"{len(stale)} tarea(s) vencidas sin avance ni cambio de "
                "estado: actualizá el plan o replanificá sus fechas.",
                stale,
            )
        )

    return out


_SEVERITY_WEIGHT = {"error": 15, "warning": 5, "info": 2}


def plan_quality_score(observations: list[dict]) -> int:
    """0-100 simple: resta por observación según severidad (floor 0)."""
    penalty = sum(_SEVERITY_WEIGHT.get(o.get("severity", "info"), 2) for o in observations)
    return max(0, 100 - penalty)
