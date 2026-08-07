"""DAT-02 — todo identificador numérico expresa su unidad.

«Todo identificador numérico DEBE expresar su unidad **en el nombre o en su
tipo**».

La auditoría del 2026-08-03 lo dejó PARCIAL con el ejemplo puesto:
«`duration_days`, `allocation_pct`, `progress` llevan unidad en el nombre.
`budget` no». Al medir contra los 56 campos numéricos del modelo, el hueco era
mayor de lo que sugería esa frase — y `progress` estaba del lado equivocado:
lleva la palabra «avance», no la unidad, y no dice si vale 0 a 1 o 0 a 100.

## Las dos vías, y por qué aquí hacía falta la segunda

Renombrar `budget` a `budget_mxn` es un cambio de contrato: viaja en la API, lo
consume el frontend y está en los datos de inquilinos reales. Ya se pagó dos
veces ese precio con `wbs`→`wbs_code` y `amber_max`→`yellow_max`, cada uno con
su ADR, su migración y su ventana de compatibilidad.

El requisito admite la otra vía, y es la que se toma: **el tipo lo dice**.
`Mapped[Importe]` en vez de `Mapped[Decimal]` no toca el esquema, no toca el
contrato, y contesta la pregunta en el sitio donde se hace.

## Los que NO llevan tipo, y por qué eso también cumple

Un conteo, un ordinal y una coordenada de calendario llevan la unidad **en el
identificador**, que es la primera vía del requisito: `open_risks` cuenta
riesgos, `outline_level` es un nivel y `day_of_week` es un día de la semana.
Añadirles un tipo sería ruido que no informa de nada nuevo.

Eso se declara aquí con su motivo, y no se deja implícito: la diferencia entre
«cumple por la primera vía» y «se nos pasó» es exactamente lo que un auditor
externo va a preguntar.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.magnitudes import CATALOGO
from tests.test_dat01_magnitudes import POR_NOMBRE, campos_numericos

API = Path(__file__).resolve().parents[1]
MODELOS = API / "app" / "models"

#: Magnitud → alias de tipo que debe aparecer en la anotación.
ALIAS: dict[str, tuple[str, ...]] = {
    "importe": ("Importe",),
    "porcentaje": ("Porcentaje", "PorcentajeDecimal"),
    "escala": ("Escala",),
    "severidad": ("Severidad",),
}

#: Magnitudes que cumplen por la PRIMERA vía —el nombre— con el motivo escrito.
#: No es una lista de excepciones: es la mitad del requisito que no necesita
#: tipo porque el identificador ya lo dice.
POR_EL_NOMBRE: dict[str, str] = {
    "conteo": (
        "La unidad de un conteo es el sustantivo, y está en el identificador: "
        "`open_risks` cuenta riesgos, `tokens_in` cuenta tokens."
    ),
    "ordinal": (
        "`position`, `level` y `version` no miden: ordenan. Su «unidad» es la "
        "posición, que es lo que el nombre dice."
    ),
    "calendario": (
        "`day_of_week`, `hour_of_day` y `day_of_month` traen la unidad "
        "completa en el nombre — mejor de lo que la diría un tipo."
    ),
    "dias": "El sufijo `_days` es la unidad.",
    "milisegundos": "El sufijo `_ms` es la unidad.",
    "bytes": "El sufijo `_bytes` es la unidad.",
    "fraccion": (
        "No es unidad de ninguna columna: `fraccion_a_pct` la produce y la "
        "consume dentro de un cálculo, y nunca se guarda."
    ),
}


def _anotacion(campo: str) -> str:
    """La anotación `Mapped[...]` de `Clase.campo`, leída del modelo.

    Se busca dentro del cuerpo de la clase y no en el archivo entero: hay dos
    `budget` en `project.py` —uno `Numeric` y otro `String(8)`, que es una
    dimensión del semáforo— y confundirlos daría por bueno lo que no lo es.
    """
    clase, nombre = campo.split(".")
    for archivo in sorted(MODELOS.rglob("*.py")):
        texto = archivo.read_text(encoding="utf-8")
        m = re.search(rf"^class {re.escape(clase)}\b.*?(?=^class |\Z)", texto, re.M | re.S)
        if not m:
            continue
        d = re.search(rf"^\s+{re.escape(nombre)}\s*:\s*Mapped\[(.+?)\]\s*=", m.group(0), re.M)
        if d:
            return d.group(1)
    return ""


@pytest.mark.parametrize(
    "campo,magnitud",
    sorted((c, m) for c, m in POR_NOMBRE.items() if m in ALIAS),
)
def test_el_tipo_dice_la_unidad(campo: str, magnitud: str) -> None:
    """Los 16 cuyo nombre no puede decirla sin romper contrato."""
    anotacion = _anotacion(campo)
    assert anotacion, f"No se encontró la anotación de `{campo}` en el modelo."
    assert any(a in anotacion for a in ALIAS[magnitud]), (
        f"`{campo}` es {magnitud} y su anotación es `Mapped[{anotacion}]`. "
        f"Ni el nombre ni el tipo dicen la unidad, que es lo que DAT-02 pide. "
        f"Usa {' o '.join(ALIAS[magnitud])} de `app.core.magnitudes`.\n\n"
        f"Unidad canónica: {CATALOGO[magnitud].unidad} ({CATALOGO[magnitud].rango})."
    )


def test_las_magnitudes_que_cumplen_por_el_nombre_dicen_por_que() -> None:
    """Distinguir «cumple por la primera vía» de «se nos pasó».

    Sin el motivo escrito, las dos se ven igual desde fuera — y la segunda es
    un hueco que alguien tiene que descubrir leyendo el modelo entero.
    """
    usadas = set(POR_NOMBRE.values())
    for magnitud in usadas:
        assert magnitud in ALIAS or magnitud in POR_EL_NOMBRE, (
            f"«{magnitud}» clasifica campos y no dice si cumple por el nombre "
            f"o por el tipo."
        )
    for magnitud, porque in POR_EL_NOMBRE.items():
        # El criterio es que CITE el nombre, no que sea largo. Un umbral de
        # caracteres premia la prosa y deja pasar cuarenta palabras que no
        # nombran nada; «El sufijo `_days` es la unidad» son treinta y uno y
        # dice todo lo que hay que decir.
        assert re.search(r"`[^`]+`", porque), (
            f"«{magnitud}» cumple «por el nombre» y no cita ninguno. Sin el "
            f"identificador delante, «está en el nombre» no se puede comprobar."
        )


def test_ninguna_magnitud_esta_en_las_dos_listas() -> None:
    """Cumplir «por el nombre» y «por el tipo» a la vez es no haber decidido."""
    ambas = set(ALIAS) & set(POR_EL_NOMBRE)
    assert not ambas, f"Declaradas por las dos vías: {sorted(ambas)}"


def test_todo_campo_numerico_cumple_por_alguna_via() -> None:
    """El barrido completo, derivado del árbol.

    Es el que impide que esto sea una foto: un campo numérico nuevo que no
    lleve la unidad en el nombre ni esté clasificado hace fallar la prueba con
    su nombre delante.
    """
    hallados = campos_numericos()
    assert len(hallados) >= 50, (
        f"El barrido encontró {len(hallados)} campos. Dejó de encontrarlos."
    )

    incumplen: list[str] = []
    for campo, por_sufijo in hallados.items():
        if por_sufijo:
            continue  # la unidad está en el sufijo del nombre
        magnitud = POR_NOMBRE.get(campo)
        if magnitud is None:
            incumplen.append(f"{campo} — sin magnitud declarada")
        elif magnitud in ALIAS and not any(
            a in _anotacion(campo) for a in ALIAS[magnitud]
        ):
            incumplen.append(f"{campo} — {magnitud} sin el tipo que lo dice")

    assert not incumplen, (
        "Campos numéricos que no expresan su unidad ni en el nombre ni en el "
        "tipo:\n  " + "\n  ".join(sorted(incumplen))
    )


def test_los_tipos_de_magnitud_no_cambian_el_esquema() -> None:
    """La razón por la que esta vía es barata: no toca la base.

    `Annotated[Decimal, ...]` es `Decimal` para SQLAlchemy, así que la columna
    sale idéntica. Si algún día dejara de serlo, el cambio sería de esquema y
    exigiría migración — y esta prueba lo diría antes que la base.
    """
    from app.models.metric_snapshot import MetricSnapshot
    from app.models.project import Project

    columnas = {c.name: str(c.type) for c in Project.__table__.columns}
    assert columnas["budget"] == "NUMERIC(14, 2)"
    assert columnas["actual_budget"] == "NUMERIC(14, 2)"
    assert columnas["progress"] == "SMALLINT"
    assert columnas["priority"] == "SMALLINT"

    snap = {c.name: str(c.type) for c in MetricSnapshot.__table__.columns}
    assert snap["avg_progress"] == "NUMERIC(5, 2)"
    assert snap["budget_plan"] == "NUMERIC(16, 2)"
