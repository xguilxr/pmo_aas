"""US-213 — Los cortes de un periodo de reporte, a partir de la serie diaria.

Los mockups piden una «Tendencia bi-semanal» y un «Historial de cortes (snapshot
por periodo)». Las instantáneas se capturan **semanalmente** (`metric_snapshots`,
US-151) y la PMO reporta cada dos semanas: hay que enseñar un punto por periodo
de reporte, no uno por captura.

## Por qué se muestrea al leer y no al capturar

Porque bajar la frecuencia de captura es irreversible. Si el job pasara a correr
cada dos semanas, el día que alguien quiera ver la evolución semanal de un mes
concreto —la pregunta normal cuando algo se torció— no habría de dónde sacarla.
Capturando semanal y mostrando por periodo se tienen las dos, y cambiar la
cadencia de reporte no borra historia.

Es la misma razón por la que un almacén de series temporales guarda la
resolución fina y agrega en la consulta.

## Qué punto representa un periodo

El **último** de cada periodo, no el promedio. Un corte de reporte es una foto
del estado al cerrar el periodo: «al 4 de agosto la cartera iba al 63 %». El
promedio de las dos semanas no es ningún estado real, y presentarlo como el
corte convierte un dato verificable en uno que nadie puede reproducir abriendo
la aplicación ese día.

## MCS DEV-02 — sin base de datos

Recibe puntos con fecha y devuelve los que sobreviven.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from typing import TypeVar

_Punto = TypeVar("_Punto")


def cortes_por_periodo(
    puntos: list[_Punto],
    *,
    fecha_de: Callable[[_Punto], date],
    cadencia_dias: int,
    hoy: date,
) -> list[_Punto]:
    """Un punto por periodo de `cadencia_dias`, contando hacia atrás desde `hoy`.

    `fecha_de` extrae la fecha de un punto — así la regla sirve igual para las
    filas del modelo y para los diccionarios ya serializados, sin que este
    módulo conozca ninguna de las dos formas.

    Los periodos se anclan en **hoy** y no en el primer punto de la serie. El
    motivo es que el corte más reciente tiene que caer siempre en el último
    periodo: anclando en el primer punto, añadir un punto viejo al histórico
    correría todos los límites y la serie entera cambiaría de forma sin que nada
    hubiera pasado en la cartera.

    Con `cadencia_dias <= 0` devuelve la serie tal cual: no muestrear es un
    resultado válido —es lo que quiere quien pide la resolución fina— y no un
    error que merezca una excepción.
    """
    if cadencia_dias <= 0 or not puntos:
        return list(puntos)

    # `periodo(fecha)` = cuántos periodos completos hay entre esa fecha y hoy.
    # Todos los puntos del mismo periodo comparten el número, y el mayor de sus
    # fechas es el corte.
    def periodo(p: _Punto) -> int:
        return (hoy - fecha_de(p)).days // cadencia_dias

    por_periodo: dict[int, _Punto] = {}
    for p in puntos:
        n = periodo(p)
        actual = por_periodo.get(n)
        if actual is None or fecha_de(p) >= fecha_de(actual):
            por_periodo[n] = p

    # De más antiguo a más reciente: el número de periodo cuenta al revés.
    return [por_periodo[n] for n in sorted(por_periodo, reverse=True)]


def limites_del_periodo(
    *, cadencia_dias: int, hoy: date, periodos: int
) -> list[tuple[date, date]]:
    """`[(inicio, fin)]` de los últimos `periodos` periodos, del más viejo al de hoy.

    Sirve al «historial de cortes»: la tabla necesita nombrar el periodo aunque
    no haya ninguna instantánea dentro. Un periodo sin datos es información —el
    job no corrió, o el inquilino no existía— y omitirlo hace que la tabla
    parezca continua cuando tiene un hueco.
    """
    if cadencia_dias <= 0 or periodos <= 0:
        return []
    salida: list[tuple[date, date]] = []
    for n in range(periodos - 1, -1, -1):
        fin = hoy - timedelta(days=n * cadencia_dias)
        inicio = fin - timedelta(days=cadencia_dias - 1)
        salida.append((inicio, fin))
    return salida
