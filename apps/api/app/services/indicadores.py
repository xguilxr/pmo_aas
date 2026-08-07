"""DAT-09 — cada indicador, definido una sola vez.

> «Cada indicador DEBE definirse una sola vez en el código. NO DEBE
> reimplementarse por consumidor».

La auditoría lo dejó PARCIAL con la mitad medida: «la salud se calcula en
`services/project_health.py`, una sola vez ✓. Otros indicadores no auditados».
Auditados los demás contra las fichas de `07-FICHAS-INDICADORES.md`, salieron
cuatro reimplementaciones, y una de ellas ya había producido el fallo que este
requisito existe para evitar.

## El que ya estaba roto: el avance de la cartera

La ficha, firmada por el owner el 2026-08-06, dice: «Sin proyectos → `null`,
que se pinta «—». **Cero proyectos no es cero por ciento**». Se corrigió en
`dashboard.py`, que es donde se vio.

`analytics/snapshots.py` calculaba **el mismo indicador** con su propia
división y su propio `else 0`, y no se tocó. Resultado: el tablero dice «—» y
la instantánea de ese mismo día guarda `0`. La gráfica de tendencia de los
informes lee instantáneas, así que **dibujaba una caída a cero** en carteras
recién creadas. Dos consumidores, dos fórmulas, y la corrección solo alcanzó a
uno — que es literalmente lo que DAT-09 describe.

Divergían también en el redondeo: sin redondear en el tablero, a dos decimales
en la instantánea.

## Los otros tres

- **El promedio por cubo** (`gantt_renderer`, `engine`): dos divisiones
  idénticas publicando la clave `avg_progress` en informes que alguien lee. No
  es el avance de la ficha —el grano es el cubo, no el proyecto— y por eso
  aquí se llama por su nombre.
- **Los días de retraso**: la misma expresión escrita dos veces en
  `operational_reports.py`, con 17 líneas de diferencia.
- **El porcentaje a tiempo**: una sola implementación, pero con el recorte a
  `[0, 100]` disperso en la llamada.

## Qué NO entra aquí

La **salud** sigue en `project_health.py`, que ya era su definición única. Traer
aquí una función que solo se llama desde un sitio no añade nada y aleja la
regla de su rúbrica. DAT-09 pide una definición por indicador, no un archivo
que las junte todas.
"""
from __future__ import annotations

from datetime import date

from app.core.magnitudes import Porcentaje
from app.core.unidades import razon_a_pct


def avance_de_cartera(avances: list[float]) -> float | None:
    """Promedio de los avances de los proyectos activos. `progress_avg`.

    **`None` cuando no hay proyectos**, y no cero: la ficha lo firma así y el
    motivo es que un tablero recién estrenado no es una cartera parada en seco.
    Quien lo presente decide si pinta «—» (DAT-12); quien lo guarde necesita
    poder guardar la ausencia, y por eso `metric_snapshots.avg_progress` admite
    nulo desde la migración 0103.

    Sin redondear a propósito: la ficha distingue este indicador de
    `avg_progress` justamente en eso, y redondear aquí borraría la diferencia
    que el documento se molesta en explicar.
    """
    if not avances:
        return None
    return sum(avances) / len(avances)


def promedio_de_avance(suma: float, cuantos: int) -> float:
    """Media de avances dentro de un cubo (un mes, un área). Un decimal.

    **No es `avance_de_cartera`.** El grano es el cubo y el denominador son las
    tareas del cubo, no los proyectos. Se llama distinto porque es distinto;
    que las dos claves de salida se llamen `avg_progress` es deuda de nombres
    anotada en la ficha, no una señal de que sean lo mismo.

    Recibe suma y cuántos —y no la lista— porque es lo que los dos únicos
    consumidores tienen en la mano: ambos acumulan sobre un diccionario de
    cubos y nunca conservan los valores sueltos. Pedirles la lista los
    obligaría a guardarla solo para llamar aquí.

    Devuelve `0.0` y no `None` porque un cubo existe solo si tiene elementos:
    el cubo vacío no ocurre por «no hay datos», ocurre por un error de quien
    llama, y se prefiere que se vea el cero a que reviente un informe.
    """
    if cuantos <= 0:
        return 0.0
    return round(suma / cuantos, 1)


def dias_de_retraso(compromiso: date | None, corte: date) -> int:
    """Días vencidos respecto al corte. Nunca negativo.

    Estaba escrito dos veces en `operational_reports.py`, a diecisiete líneas
    de distancia: una para tareas y otra para acciones. Dos copias de la misma
    resta divergen en cuanto una de las dos aprende algo — un calendario
    laboral, un huso horario— y la otra no.

    **La referencia es la fecha planeada ACTUAL**, no una línea base. Es
    decisión del owner (ficha, 2026-08-06): la plataforma es de gestión
    flexible, no de cumplimiento, así que mover una fecha reajusta el retraso.
    """
    if compromiso is None or compromiso >= corte:
        return 0
    return (corte - compromiso).days


def porcentaje_a_tiempo(total: int, retrasadas: int) -> Porcentaje:
    """`(total − retrasadas) / total`, recortado a [0, 100]. `on_time_pct`.

    El recorte va aquí y no en quien llama porque es parte de la definición:
    `retrasadas` puede venir de un conteo con otro filtro que el de `total`
    —ya pasó, ENH-146— y sin el recorte el indicador sale negativo o por
    encima de cien, que es peor que salir tope.

    Sin tareas devuelve 0 y no `None`: «cero tareas» aquí significa que no hay
    plan, y el informe que lo muestra ya distingue ese caso antes de pedirlo.
    """
    if total <= 0:
        return 0
    return max(0, min(100, round(razon_a_pct(total - retrasadas, total))))
