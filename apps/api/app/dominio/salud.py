"""MCS DEV-02 — las reglas del semáforo, sin base de datos de por medio.

Estas cinco reglas deciden de qué color sale un proyecto, y son **la parte del
producto que más se mira**. Estaban en `services/project_health.py`, que
importa `AsyncSession`: verificarlas sin base de datos era posible y nadie lo
había hecho, porque el archivo entero olía a consulta.

Aquí no hay consultas. Cada función recibe **los números ya contados** y
devuelve un color; contar los vencidos, los riesgos severos y las decisiones
estancadas sigue siendo trabajo de `project_health.py`, que es acceso a datos.

La separación no es estética. Un umbral mal calibrado se descubre probando
combinaciones —ochenta casos de cronograma tardan milisegundos así y minutos
con una base de por medio—, y `US-196` recalibró estos números precisamente
porque en una cartera real casi todo salía amarillo.

**El orden de las comparaciones importa y está probado**: primero el rojo. Con
el amarillo delante, un proyecto en rojo saldría amarillo, y esa es la clase de
error que nadie ve hasta que alguien pregunta por qué un proyecto hundido está
en ámbar.
"""
from __future__ import annotations

from typing import Any

#: Orden de gravedad. Verde < amarillo < rojo, y se compara por este rango y no
#: alfabéticamente — «green» < «red» < «yellow» en texto pondría el rojo en
#: medio.
_RANGO_COLOR = {"green": 0, "yellow": 1, "red": 2}


#: Calibración del owner, 2026-08-05 (D-4). Dos criterios detrás de los números:
#:
#: 1. **El amarillo no puede dispararse con el primer caso.** Cuatro de las cinco
#:    dimensiones ponían el piso en 0 o 1 —un riesgo severo, una decisión
#:    estancada, cualquier sobreasignación mayor que cero—, y en una cartera real
#:    eso deja casi todo en amarillo permanente. Un semáforo que siempre está
#:    amarillo dejó de informar, que es peor que no tenerlo.
#: 2. **Los rojos se mueven poco.** El rojo ya discriminaba; lo que no
#:    discriminaba era el amarillo.
#:
#: Son un punto de partida razonado, **no medido contra una cartera real**. Por
#: eso son configurables por inquilino (`tenant.settings.health_thresholds`): si
#: los datos dicen otra cosa, se ajustan sin tocar código.
DEFAULT_HEALTH_THRESHOLDS: dict[str, dict[str, float]] = {
    "schedule": {
        "yellow_overdue_pct": 10,
        "red_overdue_pct": 25,
        "yellow_overdue_milestones": 1,
        # 3 → 2: tres hitos perdidos es enterarse tarde.
        "red_overdue_milestones": 2,
    },
    # El presupuesto ya no se mide contra sí mismo, sino contra el avance.
    # Ver `_budget_dimension`.
    "budget": {"yellow_burn_index": 1.15, "red_burn_index": 1.30},
    "risks": {
        # 1 → 2: un riesgo severo (P×I ≥ 13) es la operación normal de un
        # proyecto vivo, no una señal.
        "yellow_severe": 2,
        "red_severe": 3,
        "yellow_open_issues": 8,
        "red_open_issues": 15,
    },
    # 1 → 2: una decisión esperando no vuelve amarillo un proyecto entero.
    "decisions": {"stale_days": 14, "yellow_stale": 2, "red_stale": 3},
    # Antes vivían en `tenant.settings.capacity_thresholds`, otra llave, y las
    # dos cuentas estaban escritas a fuego en `capacity.py`. Un administrador
    # que quisiera ajustar la salud tenía que saber que una de las cinco
    # dimensiones se configuraba en otro sitio, y eso no lo adivina nadie.
    #
    # `capacity_thresholds` sigue existiendo para la **vista de capacidad**, que
    # responde otra pregunta: allí se colorea a una *persona*, aquí a un
    # *proyecto*. Que el proyecto sea más tolerante (5 pp) que la vista de
    # personas (0 pp) es deliberado: alguien 3 pp por encima merece salir en la
    # pantalla de capacidad, no volver amarillo el proyecto.
    "resources": {
        "yellow_over": 5,
        "red_over": 15,
        "yellow_overloaded_count": 3,
        "red_key_overloaded": 1,
    },
}


def umbrales_efectivos(ajustes: dict[str, Any] | None) -> dict[str, dict[str, float]]:
    """Umbrales por defecto con el ajuste del inquilino encima.

    Recibe **el diccionario de ajustes** y no el inquilino: es lo único que la
    regla usa de verdad, y pedir el modelo ataría el dominio a la base sin
    ganar nada. Es la diferencia entre «esta función necesita una fila» y
    «esta función necesita unos umbrales».

    La fusión es tolerante a propósito: una llave desconocida o un valor no
    numérico en `tenant.settings` se ignora en vez de reventar. Ese
    diccionario lo edita un administrador desde un formulario, y un semáforo
    que deja de pintarse por una llave mal escrita es peor que uno que usa el
    valor por defecto.
    """
    merged = {dim: dict(vals) for dim, vals in DEFAULT_HEALTH_THRESHOLDS.items()}
    raw = (ajustes or {}).get("health_thresholds")
    if isinstance(raw, dict):
        for dim, vals in raw.items():
            if dim in merged and isinstance(vals, dict):
                for k, v in vals.items():
                    if k in merged[dim] and isinstance(v, (int, float)) and not isinstance(v, bool):
                        merged[dim][k] = v
    return merged


def peor_color(colors: list[str | None]) -> str:
    present = [c for c in colors if c in _RANGO_COLOR]
    if not present:
        return "green"
    return max(present, key=lambda c: _RANGO_COLOR[c])


def color_de_cronograma(t: dict[str, float], overdue_pct: float, overdue_ms: int) -> str:
    if overdue_ms >= t["red_overdue_milestones"] or overdue_pct >= t["red_overdue_pct"]:
        return "red"
    if overdue_ms >= t["yellow_overdue_milestones"] or overdue_pct >= t["yellow_overdue_pct"]:
        return "yellow"
    return "green"


def color_de_presupuesto(t: dict[str, float], burn_index: float) -> str:
    if burn_index >= t["red_burn_index"]:
        return "red"
    if burn_index >= t["yellow_burn_index"]:
        return "yellow"
    return "green"


def color_de_riesgos(t: dict[str, float], severe: int, open_issues: int) -> str:
    if severe >= t["red_severe"] or open_issues >= t["red_open_issues"]:
        return "red"
    if severe >= t["yellow_severe"] or open_issues >= t["yellow_open_issues"]:
        return "yellow"
    return "green"


def color_de_decisiones(t: dict[str, float], stale: int) -> str:
    if stale >= t["red_stale"]:
        return "red"
    if stale >= t["yellow_stale"]:
        return "yellow"
    return "green"
