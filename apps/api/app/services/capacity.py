"""US-183 — Motor de saturación de recursos (capacidad consumible).

La saturación NO vive en el recurso: vive en la relación recurso-proyecto
(`project_participations`, US-183) cruzada contra la capacidad disponible
para proyectos del recurso (`actors.project_capacity_pct`, US-182).

Reglas (diseño Revamp 1.0, decisiones owner 2026-07-08):
- Solo participations con ``status='activa'`` suman demanda; las
  tentativas se reportan aparte; las vencidas (fuera de ventana) no
  cuentan.
- La demanda se compara contra ``project_capacity_pct``, NUNCA contra 100.
- ``allocation_pct`` NULL = asignación sin cuantificar: no suma, pero se
  reporta (`unquantified`) para que las vistas muestren cobertura de datos.
- Ventanas temporales: today / week / 3weeks / month — una asignación
  cuenta si su rango [start_date, end_date] intersecta la ventana (rangos
  NULL = abiertos).
- Colores (umbrales por tenant en settings.capacity_thresholds):
  sobreasignación en PUNTOS porcentuales — over > red_over (default 10)
  → rojo; over > yellow_over (default 0) → amarillo; si no, verde.

Niveles de agregación: individual, por función de portafolio (rol), por
área y por sub-área (team). La dimensión "recursos" del semáforo de salud
(US-180) se activa con `project_resources_dimension`.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unidades import pct_a_fte, razon_a_pct
from app.dominio.proyecto import CERRADO
from app.models.area import Actor, Area, Team
from app.models.project import Project
from app.models.project_participation import ProjectParticipation
from app.models.tenant import Tenant

WINDOWS = ("today", "week", "3weeks", "month")

DEFAULT_CAPACITY_THRESHOLDS = {"yellow_over": 0, "red_over": 10}


def get_capacity_thresholds(tenant: Tenant | None) -> dict[str, float]:
    merged = dict(DEFAULT_CAPACITY_THRESHOLDS)
    raw = ((tenant.settings or {}).get("capacity_thresholds")) if tenant else None
    if isinstance(raw, dict):
        for k in merged:
            v = raw.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                merged[k] = v
    return merged


def window_range(window: str, today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    days = {"today": 0, "week": 7, "3weeks": 21, "month": 30}.get(window, 7)
    return today, today + timedelta(days=days)


def overload_color(over: float, t: dict[str, float]) -> str:
    if over > t["red_over"]:
        return "red"
    if over > t["yellow_over"]:
        return "yellow"
    return "green"


def _window_overlap(start: date, end: date):
    """Condición SQLAlchemy: la participación intersecta [start, end]."""
    return and_(
        or_(
            ProjectParticipation.start_date.is_(None),
            ProjectParticipation.start_date <= end,
        ),
        or_(
            ProjectParticipation.end_date.is_(None),
            ProjectParticipation.end_date >= start,
        ),
    )


async def _load_assignments(
    db: AsyncSession,
    tenant_id: str,
    start: date,
    end: date,
    *,
    actor_ids: list[str] | None = None,
    project_id: str | None = None,
    project_ids: list[str] | None = None,
) -> list[Any]:
    """Participations activas/tentativas que intersectan la ventana, con
    actor y proyecto hidratados (filas planas)."""
    stmt = (
        select(
            ProjectParticipation.actor_id,
            ProjectParticipation.project_id,
            ProjectParticipation.allocation_pct,
            ProjectParticipation.status,
            ProjectParticipation.is_critical,
            ProjectParticipation.assignment_type,
            ProjectParticipation.start_date,
            ProjectParticipation.end_date,
            Project.name.label("project_name"),
            Project.folio.label("project_folio"),
            Project.health_status.label("project_health"),
        )
        .join(Project, Project.id == ProjectParticipation.project_id)
        .where(
            ProjectParticipation.tenant_id == tenant_id,
            ProjectParticipation.status.in_(("activa", "tentativa")),
            Project.deleted_at.is_(None),
            Project.phase != CERRADO,
            _window_overlap(start, end),
        )
    )
    if actor_ids is not None:
        stmt = stmt.where(ProjectParticipation.actor_id.in_(actor_ids or ["__none__"]))
    if project_id is not None:
        stmt = stmt.where(ProjectParticipation.project_id == project_id)
    if project_ids is not None:
        stmt = stmt.where(
            ProjectParticipation.project_id.in_(project_ids or ["__none__"])
        )
    return (await db.execute(stmt)).all()


# --- US-186: organigrama con utilización (matriz mensual) -------------------

_MES = ("Ene", "Feb", "Mar", "Abr", "May", "Jun",
        "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")


def _month_windows(months: int, today: date) -> list[tuple[str, date, date]]:
    """[(label 'Jul 2026', primer día, último día)] empezando el mes actual."""
    out = []
    y, m = today.year, today.month
    for _ in range(months):
        start = date(y, m, 1)
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        end = date(ny, nm, 1) - timedelta(days=1)
        out.append((f"{_MES[m - 1]} {y}", start, end))
        y, m = ny, nm
    return out


async def scope_project_ids(
    db: AsyncSession, tenant_id: str, scope_type: str, scope_id: str | None
) -> list[str]:
    """Proyectos activos (fase != closed) del scope project|program|
    organization|tenant."""
    conds = [
        Project.tenant_id == tenant_id,
        Project.deleted_at.is_(None),
        Project.phase != CERRADO,
    ]
    if scope_type == "project":
        conds.append(Project.id == scope_id)
    elif scope_type == "program":
        conds.append(Project.program_id == scope_id)
    elif scope_type == "organization":
        conds.append(Project.organization_id == scope_id)
    rows = (await db.execute(select(Project.id).where(*conds))).scalars().all()
    return [str(r) for r in rows]


async def monthly_utilization(
    db: AsyncSession,
    tenant: Tenant,
    *,
    scope_type: str,
    scope_id: str | None = None,
    months: int = 12,
    today: date | None = None,
) -> dict[str, Any]:
    """US-186 — utilización mensual por recurso dentro de un scope.

    Por cada recurso con asignaciones ACTIVAS en los proyectos del scope:
    %FTE por mes (suma de allocation_pct de asignaciones que intersectan
    el mes, solo proyectos del scope), %FTE total tenant del mes actual
    (todos sus proyectos), y conteo de meses en alerta (>=80 amarillo,
    >100 rojo según capacity_thresholds del reporte, fijos por diseño).
    """
    today = today or date.today()
    tenant_id = str(tenant.id)
    windows = _month_windows(months, today)
    horizon_start, horizon_end = windows[0][1], windows[-1][2]

    pids = await scope_project_ids(db, tenant_id, scope_type, scope_id)
    if not pids:
        return {"months": [w[0] for w in windows], "rows": []}

    scope_rows = [
        r
        for r in await _load_assignments(
            db, tenant_id, horizon_start, horizon_end, project_ids=pids
        )
        if r.status == "activa"
    ]
    actor_ids = sorted({str(r.actor_id) for r in scope_rows})
    if not actor_ids:
        return {"months": [w[0] for w in windows], "rows": []}

    # Total tenant del mes actual (todos los proyectos del recurso).
    cur_start, cur_end = windows[0][1], windows[0][2]
    tenant_rows = [
        r
        for r in await _load_assignments(
            db, tenant_id, cur_start, cur_end, actor_ids=actor_ids
        )
        if r.status == "activa"
    ]

    def _overlaps(r: Any, start: date, end: date) -> bool:
        s_ok = r.start_date is None or r.start_date <= end
        e_ok = r.end_date is None or r.end_date >= start
        return s_ok and e_ok

    actors = (
        await db.execute(
            select(Actor).where(Actor.id.in_(actor_ids)).order_by(Actor.name)
        )
    ).scalars().all()
    area_names = {
        str(i): n for i, n in (
            await db.execute(select(Area.id, Area.name).where(Area.tenant_id == tenant_id))
        ).all()
    }
    team_names = {
        str(i): n for i, n in (
            await db.execute(select(Team.id, Team.name).where(Team.tenant_id == tenant_id))
        ).all()
    }
    actor_names = {str(a.id): a.name for a in actors}
    by_actor_scope: dict[str, list[Any]] = {}
    for r in scope_rows:
        by_actor_scope.setdefault(str(r.actor_id), []).append(r)
    total_current: dict[str, float] = {}
    for r in tenant_rows:
        if r.allocation_pct is not None:
            aid = str(r.actor_id)
            total_current[aid] = total_current.get(aid, 0.0) + float(r.allocation_pct)

    rows: list[dict[str, Any]] = []
    for a in actors:
        aid = str(a.id)
        mine = by_actor_scope.get(aid, [])
        per_month: list[float] = []
        for _, m_start, m_end in windows:
            val = sum(
                float(r.allocation_pct)
                for r in mine
                if r.allocation_pct is not None and _overlaps(r, m_start, m_end)
            )
            per_month.append(round(val, 1))
        alert_months = sum(1 for v in per_month if v >= 80)
        rows.append({
            "actor_id": aid,
            "name": a.name,
            "discipline": a.discipline,
            "job_title": a.job_title,
            "resource_type": a.resource_type,
            "area": area_names.get(str(a.area_id), "") if a.area_id else "",
            "team": team_names.get(str(a.team_id), "") if a.team_id else "",
            "manager": (
                actor_names.get(str(a.manager_actor_id), "")
                if a.manager_actor_id
                else ""
            ),
            "capacity_pct": float(a.project_capacity_pct or 0),
            "is_key_resource": bool(a.is_key_resource),
            "scope_current_pct": per_month[0],
            "tenant_current_pct": round(total_current.get(aid, 0.0), 1),
            "projects_count": len({str(r.project_id) for r in mine}),
            "per_month": per_month,
            "alert_months": alert_months,
        })
    rows.sort(key=lambda r: (-r["alert_months"], -r["scope_current_pct"], r["name"]))
    return {"months": [w[0] for w in windows], "rows": rows}


# --- US-208: carga semanal (heatmap persona × semana del mockup) -----------

#: El horizonte por defecto del mockup. Doce semanas es lo que cabe en pantalla
#: sin scroll horizontal y lo que un plan trimestral abarca.
SEMANAS_POR_DEFECTO = 12

_MES_CORTO = ("ene", "feb", "mar", "abr", "may", "jun",
              "jul", "ago", "sep", "oct", "nov", "dic")


def _semanas(cantidad: int, today: date) -> list[tuple[str, date, date]]:
    """`[(etiqueta 's33', lunes, domingo)]` desde la semana en curso.

    La etiqueta es el número de semana ISO, que es lo que el mockup dibuja y lo
    que una PMO usa para hablar de fechas («lo movemos a la s37»). Se empieza en
    el lunes de la semana actual y no en hoy: media semana como primera columna
    daría un porcentaje que no se puede comparar con las de al lado.
    """
    lunes = today - timedelta(days=today.weekday())
    salida = []
    for i in range(cantidad):
        inicio = lunes + timedelta(weeks=i)
        fin = inicio + timedelta(days=6)
        salida.append((f"s{inicio.isocalendar().week}", inicio, fin))
    return salida


def _meses_del_horizonte(
    semanas: list[tuple[str, date, date]],
) -> list[tuple[str, date, date]]:
    """Los meses que las semanas tocan, para «capacidad vs demanda».

    Se derivan del horizonte y no se piden aparte: dos rangos distintos en la
    misma pantalla —doce semanas arriba, cuatro meses abajo— son dos preguntas
    que se leen como una.
    """
    vistos: list[tuple[str, date, date]] = []
    for _, inicio, _fin in semanas:
        clave = (inicio.year, inicio.month)
        if vistos and (vistos[-1][1].year, vistos[-1][1].month) == clave:
            continue
        primero = date(inicio.year, inicio.month, 1)
        ny, nm = (inicio.year + 1, 1) if inicio.month == 12 else (inicio.year, inicio.month + 1)
        vistos.append((_MES_CORTO[inicio.month - 1], primero, date(ny, nm, 1) - timedelta(days=1)))
    return vistos


def _intersecta(r: Any, inicio: date, fin: date) -> bool:
    """La participación toca [inicio, fin]. Sin fechas se considera vigente:
    una asignación sin plazo es indefinida, no inexistente."""
    return (r.start_date is None or r.start_date <= fin) and (
        r.end_date is None or r.end_date >= inicio
    )


async def weekly_load(
    db: AsyncSession,
    tenant: Tenant,
    *,
    weeks: int = SEMANAS_POR_DEFECTO,
    organization_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """US-208 — carga por persona y por semana, en % de FTE asignado.

    Es el heatmap del artboard «Recursos › Capacidad». Devuelve además lo que
    los otros tres paneles del mockup necesitan, y en la misma respuesta:

    - `capacity_vs_demand` — demanda asignada contra capacidad, por mes.
    - `shared_critical` — quién está en más proyectos a la vez.
    - `suggested` — la lectura de lo anterior, en una frase.

    ## Por qué todo en una respuesta

    Los cuatro paneles miran las **mismas** asignaciones. Con un endpoint por
    panel, cuatro consultas leen la misma tabla y —peor— pueden leerla en
    momentos distintos: el heatmap diría que alguien está al 160 % mientras el
    panel de al lado ya no lo lista como crítico. Un solo corte no puede
    contradecirse consigo mismo.

    ## Las filas de equipo son un promedio, no una suma

    El mockup pinta «Equipo QA (6) · 120». Sumar los seis daría 720 %, que no
    significa nada: la pregunta de una fila de equipo es «¿el equipo está
    saturado?», y eso es el promedio de sus miembros. Se dice en el contrato
    (`kind: "team"`, `members`) para que la pantalla pueda rotularlo.
    """
    today = today or date.today()
    tenant_id = str(tenant.id)
    umbrales = get_capacity_thresholds(tenant)
    semanas = _semanas(max(1, weeks), today)
    horizonte_inicio, horizonte_fin = semanas[0][1], semanas[-1][2]

    actor_stmt = select(Actor).where(
        Actor.tenant_id == tenant_id,
        Actor.deleted_at.is_(None),
        Actor.is_active.is_(True),
    )
    if organization_id:
        # Los actores sin organización entran igual: son el catálogo compartido
        # del inquilino, y excluirlos haría desaparecer del heatmap a quien
        # trabaja para varias organizaciones — que es justo el caso crítico.
        actor_stmt = actor_stmt.where(
            or_(
                Actor.organization_id == organization_id,
                Actor.organization_id.is_(None),
            )
        )
    actores = list((await db.execute(actor_stmt.order_by(Actor.name))).scalars().all())
    vacio: dict[str, Any] = {
        "weeks": [
            {"label": e, "start": i.isoformat(), "end": f.isoformat()}
            for e, i, f in semanas
        ],
        "rows": [],
        "capacity_vs_demand": [],
        "shared_critical": [],
        "suggested": [],
        "unquantified_resources": 0,
    }
    if not actores:
        return vacio

    ids = [str(a.id) for a in actores]
    # La demanda de cada recurso considera **todos** sus proyectos, no solo los
    # de la organización filtrada: alguien saturado lo está por la suma de todo
    # lo que tiene encima. Es la misma regla que `/projects/{id}/resource-load`.
    filas = [
        r
        for r in await _load_assignments(
            db, tenant_id, horizonte_inicio, horizonte_fin, actor_ids=ids
        )
        if r.status == "activa"
    ]
    por_actor: dict[str, list[Any]] = {}
    for r in filas:
        por_actor.setdefault(str(r.actor_id), []).append(r)

    equipos = {
        str(i): n
        for i, n in (
            await db.execute(select(Team.id, Team.name).where(Team.tenant_id == tenant_id))
        ).all()
    }
    areas = {
        str(i): n
        for i, n in (
            await db.execute(select(Area.id, Area.name).where(Area.tenant_id == tenant_id))
        ).all()
    }

    def por_semana(asignaciones: list[Any]) -> list[float]:
        return [
            round(
                sum(
                    float(r.allocation_pct)
                    for r in asignaciones
                    if r.allocation_pct is not None and _intersecta(r, inicio, fin)
                ),
                1,
            )
            for _, inicio, fin in semanas
        ]

    filas_salida: list[dict[str, Any]] = []
    # Asignados **sin** `%` capturado. No entran en el heatmap y no se callan:
    # una fila en cero para alguien que sí está asignado se lee como «libre»,
    # cuando lo que pasa es que no se sabe cuánto pesa. Y es accionable —hay que
    # capturar el FTE—, así que la pantalla lo dice.
    sin_cuantificar = 0
    for a in actores:
        aid = str(a.id)
        mias = por_actor.get(aid, [])
        # Solo quien tiene alguna señal. Un catálogo de cuarenta y ocho actores
        # de los que diez están asignados daría treinta y ocho filas en cero, y
        # el heatmap se lee peor con ellas que sin ellas.
        if not mias:
            continue
        serie = por_semana(mias)
        # La participación existe pero ninguna lleva `allocation_pct`: es el
        # caso del PM que la sincronización de membresía (US-118) asigna sola.
        if not any(serie):
            sin_cuantificar += 1
            continue
        capacidad = float(a.project_capacity_pct or 0)
        filas_salida.append(
            {
                "kind": "actor",
                "id": aid,
                "name": a.name,
                "discipline": a.discipline,
                "area": areas.get(str(a.area_id), "") if a.area_id else "",
                "team_id": str(a.team_id) if a.team_id else None,
                "team": equipos.get(str(a.team_id), "") if a.team_id else "",
                "capacity_pct": capacidad,
                "per_week": serie,
                "peak_pct": max(serie) if serie else 0.0,
                "projects_count": len({str(r.project_id) for r in mias}),
                "is_key_resource": bool(a.is_key_resource),
                "is_shared_resource": bool(a.is_shared_resource),
                # El desglose de la celda del mockup («click: proyectos que
                # componen la carga») se resuelve en el cliente con esto, sin
                # una ida al servidor por celda.
                "assignments": [
                    {
                        "project_id": str(r.project_id),
                        "project_name": r.project_name,
                        "project_folio": r.project_folio,
                        "allocation_pct": (
                            float(r.allocation_pct) if r.allocation_pct is not None else None
                        ),
                        "start_date": r.start_date.isoformat() if r.start_date else None,
                        "end_date": r.end_date.isoformat() if r.end_date else None,
                        "is_critical": bool(r.is_critical),
                    }
                    for r in mias
                ],
            }
        )

    # Filas de equipo: el promedio de sus miembros presentes en el heatmap.
    por_equipo: dict[str, list[dict[str, Any]]] = {}
    for f in filas_salida:
        if f["team_id"]:
            por_equipo.setdefault(str(f["team_id"]), []).append(f)
    for tid, miembros in sorted(por_equipo.items(), key=lambda kv: equipos.get(kv[0], "")):
        # Con un solo miembro la fila de equipo repetiría la suya.
        if len(miembros) < 2:
            continue
        promedio = [
            round(sum(m["per_week"][i] for m in miembros) / len(miembros), 1)
            for i in range(len(semanas))
        ]
        filas_salida.append(
            {
                "kind": "team",
                "id": tid,
                "name": equipos.get(tid, "Equipo"),
                "discipline": None,
                "area": "",
                "team_id": tid,
                "team": equipos.get(tid, ""),
                "members": len(miembros),
                "capacity_pct": round(
                    sum(m["capacity_pct"] for m in miembros) / len(miembros), 1
                ),
                "per_week": promedio,
                "peak_pct": max(promedio) if promedio else 0.0,
                "projects_count": len(
                    {
                        p["project_id"]
                        for m in miembros
                        for p in m["assignments"]
                    }
                ),
                "is_key_resource": False,
                "is_shared_resource": False,
                "assignments": [],
            }
        )

    # Lo más saturado arriba: el heatmap existe para encontrar el fuego.
    filas_salida.sort(key=lambda f: (-float(f["peak_pct"]), str(f["name"])))

    # --- capacidad vs demanda, por mes -------------------------------------
    solo_personas = [f for f in filas_salida if f["kind"] == "actor"]
    capacidad_fte = pct_a_fte(sum(float(f["capacity_pct"]) for f in solo_personas))
    # Las asignaciones de los recursos que **sí** salen en el heatmap. Sumar
    # todas incluiría a los sin cuantificar, y la demanda mensual dejaría de
    # cuadrar con las columnas de arriba.
    ids_en_heatmap = {str(f["id"]) for f in solo_personas}
    filas_en_heatmap = [r for r in filas if str(r.actor_id) in ids_en_heatmap]
    cap_vs_dem = []
    for etiqueta, inicio, fin in _meses_del_horizonte(semanas):
        demanda = sum(
            float(r.allocation_pct)
            for r in filas_en_heatmap
            if r.allocation_pct is not None and _intersecta(r, inicio, fin)
        )
        cap_vs_dem.append(
            {
                "label": etiqueta,
                # En FTE y no en porcentaje: «38.6 de 35 personas» se entiende
                # sin conversión, y «3860 % de 3500 %» no. La conversión tiene
                # nombre (DAT-04): un `/ 100` suelto no dice de qué a qué.
                "demand_fte": pct_a_fte(demanda),
                "capacity_fte": round(capacidad_fte, 1),
            }
        )

    # --- recursos críticos compartidos -------------------------------------
    # «Compartido» aquí es medido, no declarado: estar en tres proyectos a la vez
    # lo es, tenga o no la marca `is_shared_resource` puesta a mano. El umbral es
    # dos porque con uno no hay nada que compartir.
    compartidos = sorted(
        (f for f in solo_personas if int(f["projects_count"]) >= 2),
        key=lambda f: (-int(f["projects_count"]), -float(f["peak_pct"]), str(f["name"])),
    )[:5]
    criticos = [
        {
            "actor_id": f["id"],
            "name": f["name"],
            "discipline": f["discipline"],
            "projects_count": f["projects_count"],
            "projects": sorted(
                {str(p["project_name"]) for p in f["assignments"]}
            ),
            "peak_pct": f["peak_pct"],
        }
        for f in compartidos
    ]

    # --- lo que hay que hacer con todo esto --------------------------------
    # Derivado, no escrito: la frase nombra el recurso y las semanas concretas
    # donde se pasa de su capacidad. Un consejo genérico («revisa la carga») no
    # es una acción, y un consejo inventado es peor que ninguno.
    sugerencias: list[str] = []
    for f in filas_salida[:2]:
        capacidad = float(f["capacity_pct"])
        if capacidad <= 0:
            continue
        excedidas = [
            semanas[i][0]
            for i, v in enumerate(f["per_week"])
            if v - capacidad > umbrales["red_over"]
        ]
        if not excedidas:
            continue
        rango = (
            f"{excedidas[0]} a {excedidas[-1]}" if len(excedidas) > 1 else excedidas[0]
        )
        sugerencias.append(
            f"{f['name']} pasa de su capacidad ({capacidad:.0f}%) en "
            f"{rango}: pico de {float(f['peak_pct']):.0f}%. Renivelar o mover "
            f"lo que empieza en {excedidas[0]}."
        )

    return {
        "weeks": [
            {"label": e, "start": i.isoformat(), "end": f.isoformat()}
            for e, i, f in semanas
        ],
        "rows": filas_salida,
        "capacity_vs_demand": cap_vs_dem,
        "shared_critical": criticos,
        "suggested": sugerencias,
        "unquantified_resources": sin_cuantificar,
    }


def _summarize_actor(
    actor: Actor, rows: list[Any], t: dict[str, float]
) -> dict[str, Any]:
    active = [r for r in rows if r.status == "activa"]
    demand = sum(float(r.allocation_pct) for r in active if r.allocation_pct is not None)
    tentative = sum(
        float(r.allocation_pct)
        for r in rows
        if r.status == "tentativa" and r.allocation_pct is not None
    )
    unquantified = sum(1 for r in active if r.allocation_pct is None)
    capacity = float(actor.project_capacity_pct or 0)
    over = demand - capacity
    return {
        "actor_id": str(actor.id),
        "name": actor.name,
        "discipline": actor.discipline,
        "resource_type": actor.resource_type,
        "seniority": actor.seniority,
        "scarcity_level": actor.scarcity_level,
        "area_id": str(actor.area_id) if actor.area_id else None,
        "team_id": str(actor.team_id) if actor.team_id else None,
        "organization_id": str(actor.organization_id) if actor.organization_id else None,
        "is_key_resource": bool(actor.is_key_resource),
        "is_shared_resource": bool(actor.is_shared_resource),
        "capacity_pct": capacity,
        "demand_pct": round(demand, 2),
        "tentative_pct": round(tentative, 2),
        "gap_pct": round(capacity - demand, 2),
        "over_pct": round(max(over, 0), 2),
        "projects_count": len({r.project_id for r in active}),
        "unquantified_count": unquantified,
        "color": overload_color(over, t),
    }


async def resource_capacity_summary(
    db: AsyncSession,
    tenant: Tenant,
    *,
    window: str = "week",
    organization_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Nivel 1-3: saturación individual + agregados por rol/área/equipo."""
    t = get_capacity_thresholds(tenant)
    start, end = window_range(window, today)
    tenant_id = str(tenant.id)

    actor_stmt = select(Actor).where(
        Actor.tenant_id == tenant_id,
        Actor.deleted_at.is_(None),
        Actor.is_active.is_(True),
    )
    if organization_id:
        actor_stmt = actor_stmt.where(
            or_(Actor.organization_id == organization_id, Actor.organization_id.is_(None))
        )
    actors = (await db.execute(actor_stmt)).scalars().all()
    if not actors:
        return {"window": window, "start": start.isoformat(), "end": end.isoformat(),
                "resources": [], "by_discipline": [], "by_area": [], "by_team": []}

    rows = await _load_assignments(
        db, tenant_id, start, end, actor_ids=[str(a.id) for a in actors]
    )
    by_actor: dict[str, list[Any]] = {}
    for r in rows:
        by_actor.setdefault(str(r.actor_id), []).append(r)

    resources = [
        _summarize_actor(a, by_actor.get(str(a.id), []), t) for a in actors
    ]
    # Solo recursos con alguna señal (asignación o clasificación) para no
    # inundar la vista con actores-contacto del catálogo.
    resources = [
        r for r in resources
        if r["projects_count"] > 0 or r["unquantified_count"] > 0
        or r["tentative_pct"] > 0 or r["discipline"] or r["resource_type"]
    ]
    resources.sort(key=lambda r: r["gap_pct"])

    def _aggregate(key: str) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, float]] = {}
        for r in resources:
            k = r[key]
            if not k:
                continue
            b = buckets.setdefault(k, {"capacity": 0.0, "demand": 0.0, "count": 0, "overloaded": 0})
            b["capacity"] += r["capacity_pct"]
            b["demand"] += r["demand_pct"]
            b["count"] += 1
            if r["color"] != "green":
                b["overloaded"] += 1
        out = []
        for k, b in buckets.items():
            over = b["demand"] - b["capacity"]
            out.append({
                key: k,
                "capacity_pct": round(b["capacity"], 2),
                "demand_pct": round(b["demand"], 2),
                "gap_pct": round(b["capacity"] - b["demand"], 2),
                "resources": int(b["count"]),
                "overloaded": int(b["overloaded"]),
                "color": overload_color(over, t),
            })
        out.sort(key=lambda x: x["gap_pct"])
        return out

    by_area = _aggregate("area_id")
    by_team = _aggregate("team_id")
    # Hidratar nombres de área/equipo.
    area_names = {
        str(i): n for i, n in (
            await db.execute(select(Area.id, Area.name).where(Area.tenant_id == tenant_id))
        ).all()
    }
    team_names = {
        str(i): n for i, n in (
            await db.execute(select(Team.id, Team.name).where(Team.tenant_id == tenant_id))
        ).all()
    }
    for b in by_area:
        b["name"] = area_names.get(b["area_id"], "—")
    for b in by_team:
        b["name"] = team_names.get(b["team_id"], "—")
    # ENH-198: nombres de área/equipo también POR PERSONA — habilita el
    # filtro por área/sub-área en la lista de personas y el % de uso
    # (asignación teórica vs FTE) sin lookups extra en el cliente.
    for r in resources:
        r["area_name"] = area_names.get(r["area_id"] or "", None)
        r["team_name"] = team_names.get(r["team_id"] or "", None)
        r["usage_pct"] = (
            razon_a_pct(r["demand_pct"], r["capacity_pct"])
            if r["capacity_pct"] > 0
            else None
        )

    return {
        "window": window,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "thresholds": t,
        "resources": resources,
        # D-8: la clave de salida sigue al campo. Dejar `by_function`
        # con el campo ya renombrado reintroduce el desajuste que ADR-021
        # existe para cerrar.
        "by_discipline": _aggregate("discipline"),
        "by_area": by_area,
        "by_team": by_team,
    }


async def resource_conflicts(
    db: AsyncSession,
    tenant: Tenant,
    *,
    window: str = "3weeks",
    organization_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Nivel 4 — gobernanza: recursos sobreasignados con los proyectos en
    choque, para decidir prioridad / pausa / replaneación."""
    summary = await resource_capacity_summary(
        db, tenant, window=window, organization_id=organization_id, today=today
    )
    start, end = window_range(window, today)
    overloaded = [r for r in summary["resources"] if r["color"] != "green"]
    if not overloaded:
        return {"window": window, "conflicts": []}

    rows = await _load_assignments(
        db, str(tenant.id), start, end, actor_ids=[r["actor_id"] for r in overloaded]
    )
    by_actor: dict[str, list[Any]] = {}
    for r in rows:
        if r.status == "activa":
            by_actor.setdefault(str(r.actor_id), []).append(r)

    conflicts = []
    for res in overloaded:
        assignments = by_actor.get(res["actor_id"], [])
        projects = [
            {
                "project_id": str(a.project_id),
                "name": a.project_name,
                "folio": a.project_folio,
                "health": a.project_health,
                "allocation_pct": float(a.allocation_pct) if a.allocation_pct is not None else None,
                "is_critical": bool(a.is_critical),
                "start_date": a.start_date.isoformat() if a.start_date else None,
                "end_date": a.end_date.isoformat() if a.end_date else None,
            }
            for a in assignments
        ]
        projects.sort(key=lambda p: -(p["allocation_pct"] or 0))
        # Recomendación simple v1: liberar del proyecto con menor
        # allocation no-crítico, o cuantificar los sin FTE.
        releasable = [p for p in projects if not p["is_critical"] and p["allocation_pct"]]
        if res["unquantified_count"]:
            recommendation = (
                f"Cuantificar {res['unquantified_count']} asignación(es) sin FTE% "
                "antes de decidir."
            )
        elif releasable:
            p = releasable[-1]
            recommendation = (
                f"Liberar/reducir {p['allocation_pct']:.0f}% en {p['folio']} "
                f"({p['name']}) — es la asignación no-crítica menor."
            )
        else:
            recommendation = "Todas las asignaciones son críticas: escalar prioridad al comité."
        conflicts.append({
            **res,
            "projects": projects,
            "recommendation": recommendation,
        })
    return {
        "window": window,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "conflicts": conflicts,
    }


async def project_resources_dimension(
    db: AsyncSession,
    tenant: Tenant | None,
    project_id: str,
    *,
    today: date | None = None,
    umbrales: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Dimensión "recursos" del semáforo de salud (hook US-180 → US-183).

    Rojo: `red_key_overloaded` recursos CLAVE sobreasignados (>`red_over`) o
    `yellow_overloaded_count` sobreasignados en total. Amarillo: alguno
    sobreasignado. N/A: el proyecto no tiene asignaciones cuantificadas.

    **D-4 (2026-08-05): los umbrales llegan de fuera.** Antes esta función los
    leía de `capacity_thresholds` y las dos cuentas —un recurso clave, tres en
    total— estaban escritas a fuego aquí, de modo que la única de las cinco
    dimensiones de salud que no se podía ajustar era esta. `umbrales` viene de
    `health_thresholds["resources"]`; sin él se cae a `capacity_thresholds`,
    que es lo que usa la **vista de capacidad** —otra pregunta: allí se colorea
    a una persona, aquí a un proyecto—.
    """
    t = umbrales or get_capacity_thresholds(tenant)
    start, end = window_range("3weeks", today)
    tenant_id = str(tenant.id) if tenant else None

    proj_rows = await _load_assignments(db, tenant_id, start, end, project_id=project_id)
    actor_ids = sorted({str(r.actor_id) for r in proj_rows if r.status == "activa"})
    quantified = [r for r in proj_rows if r.status == "activa" and r.allocation_pct is not None]
    if not actor_ids or not quantified:
        return {
            "key": "resources", "color": None,
            "summary": "Sin asignaciones con FTE% en este proyecto",
            "causes": [], "metrics": {},
        }

    actors = (
        await db.execute(select(Actor).where(Actor.id.in_(actor_ids)))
    ).scalars().all()
    # Demanda TOTAL del recurso (todos sus proyectos), no solo este.
    all_rows = await _load_assignments(db, tenant_id, start, end, actor_ids=actor_ids)
    by_actor: dict[str, list[Any]] = {}
    for r in all_rows:
        by_actor.setdefault(str(r.actor_id), []).append(r)

    overloaded: list[dict[str, Any]] = []
    key_overloaded = 0
    for a in actors:
        s = _summarize_actor(a, by_actor.get(str(a.id), []), t)
        if s["color"] != "green":
            overloaded.append(s)
            if s["is_key_resource"]:
                key_overloaded += 1

    if (
        key_overloaded >= t.get("red_key_overloaded", 1)
        or len(overloaded) >= t.get("yellow_overloaded_count", 3)
    ):
        color = "red"
    elif overloaded:
        color = "yellow"
    else:
        color = "green"

    causes = [
        {
            "type": "resource_overloaded",
            "what": f"{o['name']} al {o['demand_pct']:.0f}% (capacidad {o['capacity_pct']:.0f}%)",
            "owner": o["name"],
            "due_date": None,
            "days": None,
        }
        for o in sorted(overloaded, key=lambda x: x["gap_pct"])[:5]
    ]
    return {
        "key": "resources",
        "color": color,
        "summary": (
            f"{len(overloaded)} recurso(s) sobreasignado(s)"
            + (f" · {key_overloaded} clave" if key_overloaded else "")
            if overloaded
            else f"{len(actor_ids)} recurso(s) dentro de capacidad"
        ),
        "causes": causes,
        "metrics": {
            "resources": len(actor_ids),
            "overloaded": len(overloaded),
            "key_overloaded": key_overloaded,
        },
    }
