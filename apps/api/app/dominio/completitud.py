"""US-210 — Cuánto de un proyecto está capturado, y qué falta.

El artboard «Portafolio — Vista maestra» lleva una columna «Compl.» con un
porcentaje por proyecto, y «Onboarding masivo» pide un «checklist de onboarding».
Son la misma cosa vista de dos maneras: el porcentaje es el resumen y el
checklist, el detalle.

## Para qué sirve un porcentaje de completitud

Para saber de qué proyectos **se puede** hablar. Un proyecto sin fechas no tiene
desviación de calendario; uno sin presupuesto no tiene consumo; uno sin PM no
tiene a quién preguntarle. En un tablero, esos proyectos no salen mal: salen
**vacíos**, y un hueco se lee como un cero. Antes de que alguien pregunte «¿por
qué el avance de la cartera bajó?», la respuesta suele ser «porque entraron seis
proyectos sin capturar».

Es también la única lista de tareas honesta después de una importación masiva
(US-216): veintitrés proyectos cargados de un Excel llegan con lo que traía el
Excel, y esto dice qué falta en cada uno.

## Por qué se deriva y NO se guarda

Un porcentaje guardado se queda viejo. Habría que recalcularlo en cada edición
del proyecto, en cada tarea nueva, en cada participación, en cada riesgo — y el
día que se olvide uno de esos caminos, la columna dice 96 % de un proyecto al
que le faltan tres campos. Derivarlo cuesta unas consultas agrupadas y no puede
desincronizarse: es la misma razón por la que el avance del plan se calcula y no
se persiste (ENH-109).

## MCS DEV-02 — aquí no entra SQLAlchemy

Este módulo recibe **hechos** (¿tiene fechas? ¿tiene tareas?) y devuelve el
veredicto. Quién los averigua es la capa de datos. Así la regla se puede probar
sin base de datos y no se duplica en las tres superficies que la muestran.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.unidades import razon_a_pct_piso

#: Qué grupo de la ficha cubre cada requisito. Sirve para agrupar el checklist
#: en la interfaz: «te falta el calendario» es más accionable que seis casillas
#: sueltas.
Grupo = Literal["identidad", "responsables", "calendario", "dinero", "gobierno"]


@dataclass(frozen=True)
class Requisito:
    """Un dato mínimo del proyecto, con su nombre en la interfaz."""

    clave: str
    etiqueta: str
    grupo: Grupo
    #: Qué se pierde sin él. Va al checklist: una casilla sin consecuencia se
    #: ignora, y la consecuencia es lo que hace que alguien lo capture.
    porque: str


#: Los requisitos mínimos, en el orden en que se piden al dar de alta.
#:
#: **Todos pesan igual.** Ponderarlos exige defender por qué el sponsor vale el
#: doble que el presupuesto, y esa discusión no tiene respuesta: los dos son
#: obligatorios o no lo son. Un porcentaje con pesos secretos es peor que uno
#: plano, porque nadie puede reproducirlo.
#:
#: **No incluye `name`, `folio` ni `phase`.** Son NOT NULL en el modelo: un
#: proyecto sin nombre no existe, y una casilla que nunca puede fallar infla el
#: porcentaje sin decir nada. La completitud mide lo que **puede** faltar.
REQUISITOS: tuple[Requisito, ...] = (
    Requisito(
        "type",
        "Tipo de proyecto",
        "identidad",
        "sin tipo no entra en la distribución por tipo ni en el presupuesto por tipo",
    ),
    Requisito(
        "priority",
        "Prioridad",
        "identidad",
        "sin prioridad no se puede ordenar qué se atiende antes",
    ),
    Requisito(
        "portfolio_id",
        "Portafolio",
        "identidad",
        "sin portafolio el proyecto no aparece en ninguna cartera: queda "
        "colgando de la organización y fuera de los reportes de nivel intermedio",
    ),
    Requisito(
        "pm_id",
        "Project Manager",
        "responsables",
        "sin PM no hay a quién preguntarle, y el proyecto no aparece en la "
        "carga de nadie",
    ),
    Requisito(
        "sponsor",
        "Sponsor",
        "responsables",
        "sin sponsor no entra en la distribución por sponsor, que es la "
        "pregunta «¿quién pidió esto?»",
    ),
    Requisito(
        "start_date",
        "Fecha de inicio",
        "calendario",
        "sin fecha de inicio no hay avance esperado por calendario, así que el "
        "proyecto no puede salir como atrasado ni como adelantado",
    ),
    Requisito(
        "end_date",
        "Fecha de fin",
        "calendario",
        "sin fecha de fin no hay contra qué medir el plan ni cuándo cerrar",
    ),
    Requisito(
        "budget",
        "Presupuesto",
        "dinero",
        "sin presupuesto el proyecto suma cero al total de la cartera, y un "
        "cero se lee como «gratis» y no como «no capturado»",
    ),
    Requisito(
        "charter",
        "Acta de constitución",
        "gobierno",
        "sin acta no está escrito qué se acordó hacer",
    ),
    Requisito(
        "plan",
        "Plan con actividades",
        "gobierno",
        "sin actividades el avance es el campo manual y no el del plan: nadie "
        "puede ver de dónde sale el porcentaje",
    ),
    Requisito(
        "recursos",
        "Recursos asignados",
        "gobierno",
        "sin participaciones el proyecto no consume capacidad de nadie, así "
        "que no aparece en el heatmap ni en los conflictos",
    ),
)

#: Cuántos requisitos hay. Se deriva de la tupla y no se escribe: un requisito
#: nuevo cambiaría el denominador y una constante escrita se quedaría vieja
#: (MCA CTX-03).
TOTAL = len(REQUISITOS)


@dataclass(frozen=True)
class Faltante:
    clave: str
    etiqueta: str
    grupo: Grupo
    porque: str


@dataclass(frozen=True)
class Completitud:
    """El veredicto: cuánto está y qué falta."""

    #: 0-100, entero. Redondeo hacia abajo a propósito: con diez de once
    #: requisitos, «90 %» es más honesto que «91 %» — el proyecto no está casi
    #: completo, le falta algo.
    pct: int
    presentes: int
    total: int
    faltantes: tuple[Faltante, ...]

    @property
    def completo(self) -> bool:
        return not self.faltantes


def evaluar(hechos: dict[str, bool]) -> Completitud:
    """El veredicto a partir de un mapa `clave del requisito → está presente`.

    Una clave ausente en `hechos` cuenta como **faltante**, no como presente:
    quien no averiguó el dato no puede afirmar que está. Es la diferencia entre
    «no lo tiene» y «no lo miré», y colapsarlas hacia el lado optimista es cómo
    un porcentaje acaba diciendo 100 % de un proyecto vacío.
    """
    faltantes = tuple(
        Faltante(r.clave, r.etiqueta, r.grupo, r.porque)
        for r in REQUISITOS
        if not hechos.get(r.clave, False)
    )
    presentes = TOTAL - len(faltantes)
    return Completitud(
        # DAT-04 — la conversión de razón a porcentaje tiene nombre, y el nombre
        # dice que trunca. El redondeo aquí no es formato: es la diferencia
        # entre «91 %» y «90 %» de un proyecto al que le falta un dato.
        pct=razon_a_pct_piso(presentes, TOTAL),
        presentes=presentes,
        total=TOTAL,
        faltantes=faltantes,
    )
