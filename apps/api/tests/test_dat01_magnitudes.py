"""DAT-01 — cada magnitud del dominio tiene unidad canónica en el glosario.

«Cada magnitud del dominio DEBE tener una unidad canónica declarada en el
glosario».

La auditoría del 2026-08-03 lo puso NO CONFORME con una frase: «sin unidades
canónicas; el glosario es borrador». El glosario dejó de ser borrador el
2026-08-04, pero seguía sin decir **en qué se mide** nada: definía qué es una
fase, un riesgo o el avance, y ninguna de las 326 líneas decía si `progress`
vale 0–1 o 0–100.

Aquí se comprueban tres cosas, y la tercera es la que hace que esto no
envejezca:

1. El glosario §7 declara cada magnitud con unidad y rango.
2. `app/core/magnitudes.py` dice exactamente lo mismo. Un catálogo que puede
   desincronizarse de su declaración no es un catálogo — es el modo de fallo de
   `check_contraste.py` cuando llevaba su propia copia de los colores.
3. **Toda columna numérica del modelo cae en alguna magnitud.** Sin esto, la
   declaración cubre lo que había el día que se escribió, y el campo 57 entra
   sin unidad sin que nada avise. Es la diferencia entre «declarado» y
   «declarado y vigente».
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from app.core.magnitudes import CATALOGO

RAIZ = Path(__file__).resolve().parents[3]
API = Path(__file__).resolve().parents[1]
GLOSARIO = RAIZ / "docs" / "dominio" / "02-GLOSARIO.md"

#: Tipos de columna que representan un número. `Boolean` no está: un booleano
#: no tiene unidad, tiene dos valores.
TIPOS_NUMERICOS = {
    "Integer",
    "BigInteger",
    "SmallInteger",
    "Float",
    "Numeric",
    "DECIMAL",
}

#: Cómo se reconoce la magnitud **por el nombre**, que es la primera vía que
#: DAT-02 admite. El orden importa: `file_size_bytes` casa con `_bytes` antes
#: que con nada más.
SUFIJOS: tuple[tuple[str, str], ...] = (
    ("_pct", "porcentaje"),
    ("_ms", "milisegundos"),
    ("_days", "dias"),
    ("_bytes", "bytes"),
)

#: Los que NO llevan la unidad en el nombre. Cada uno dice su magnitud, y la
#: prueba de DAT-02 exige además que la lleven **en el tipo**.
#:
#: Es una lista escrita a mano y eso tiene un límite conocido: prueba «estos
#: están clasificados», no «solo estos existen». Lo segundo lo cubre el barrido
#: de abajo, que deriva los campos del árbol y falla ante cualquiera que no
#: aparezca ni aquí ni en `SUFIJOS`.
POR_NOMBRE: dict[str, str] = {
    # Dinero
    "Project.budget": "importe",
    "Project.actual_budget": "importe",
    "ProjectRequest.budget": "importe",
    "MetricSnapshot.budget_plan": "importe",
    "MetricSnapshot.budget_actual": "importe",
    "Actor.fte_cost_rate": "importe",
    # Avance — porcentaje 0–100, y el nombre no lo dice
    "Project.progress": "porcentaje",
    "Task.progress": "porcentaje",
    "MetricSnapshot.avg_progress": "porcentaje",
    # Escalas ordinales 1–5
    "Risk.probability": "escala",
    "Risk.impact": "escala",
    "Issue.priority": "escala",
    "Project.priority": "escala",
    "ProjectCharter.priority": "escala",
    "Task.priority": "escala",
    # Producto de dos escalas: 1–25
    "Risk.severity": "severidad",
    # Conteos. La unidad es el sustantivo y ya está en el identificador.
    "AIJob.tokens_in": "conteo",
    "AIJob.tokens_out": "conteo",
    "MetricSnapshot.projects_total": "conteo",
    "MetricSnapshot.projects_active": "conteo",
    "MetricSnapshot.health_green": "conteo",
    "MetricSnapshot.health_yellow": "conteo",
    "MetricSnapshot.health_red": "conteo",
    "MetricSnapshot.open_risks": "conteo",
    "MetricSnapshot.severe_risks": "conteo",
    "MetricSnapshot.open_issues": "conteo",
    "MetricSnapshot.changes_in_review": "conteo",
    "MetricSnapshot.requests_in_review": "conteo",
    "MetricSnapshot.tasks_total": "conteo",
    "MetricSnapshot.tasks_done": "conteo",
    "MetricSnapshot.milestones_due_7": "conteo",
    "MetricSnapshot.milestones_due_14": "conteo",
    "MetricSnapshot.milestones_due_30": "conteo",
    "User.failed_login_attempts": "conteo",
    # ASVS 4.3.1 — intentos gastados de un código de segundo factor.
    "AdminOtpCode.intentos": "conteo",
    # Ordinales: ordenan, no miden.
    "Task.position": "ordinal",
    "Task.outline_level": "ordinal",
    "ReportSection.level": "ordinal",
    "ReportBuilderTemplate.level": "ordinal",
    "Document.version": "ordinal",
    "FolioSequence.last_number": "ordinal",
    # Coordenadas de calendario.
    "ScheduledMinute.day_of_week": "calendario",
    "ScheduledMinute.hour_of_day": "calendario",
    "ScheduledMinute.day_of_month": "calendario",
    "ScheduledReport.day_of_week": "calendario",
    "ScheduledReport.hour_of_day": "calendario",
    "ScheduledReport.day_of_month": "calendario",
    "FolioSequence.year": "calendario",
}


def campos_numericos() -> dict[str, str]:
    """`Modelo.campo` → magnitud derivada del nombre, o «» si no se deriva.

    Se recorre el árbol de `app/models` en vez de importar los modelos: así el
    barrido ve los campos aunque el módulo no se pueda importar sin base de
    datos, y no depende del orden de registro de SQLAlchemy.
    """
    hallados: dict[str, str] = {}
    for archivo in sorted((API / "app" / "models").rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for clase in (n for n in ast.walk(arbol) if isinstance(n, ast.ClassDef)):
            for sent in clase.body:
                nombre = valor = None
                if isinstance(sent, ast.AnnAssign) and isinstance(sent.target, ast.Name):
                    nombre, valor = sent.target.id, sent.value
                elif (
                    isinstance(sent, ast.Assign)
                    and len(sent.targets) == 1
                    and isinstance(sent.targets[0], ast.Name)
                ):
                    nombre, valor = sent.targets[0].id, sent.value
                if not nombre or valor is None:
                    continue

                texto = ast.unparse(valor)
                if "mapped_column" not in texto and "Column" not in texto:
                    continue

                citados = {n.id for n in ast.walk(valor) if isinstance(n, ast.Name)} | {
                    n.attr for n in ast.walk(valor) if isinstance(n, ast.Attribute)
                }
                if not (citados & TIPOS_NUMERICOS):
                    continue
                # Las claves ajenas y la propia son identificadores de fila, no
                # magnitudes: no hay nada que medir en ellas.
                if nombre == "id" or nombre.endswith("_id"):
                    continue

                magnitud = ""
                for sufijo, clave in SUFIJOS:
                    if nombre.endswith(sufijo):
                        magnitud = clave
                        break
                hallados[f"{clase.name}.{nombre}"] = magnitud
    return hallados


def _tabla_del_glosario() -> dict[str, tuple[str, str]]:
    """Magnitud → (unidad, rango), leídos de la tabla del §7."""
    texto = GLOSARIO.read_text(encoding="utf-8")
    inicio = texto.index("## 7. Magnitudes y unidades canónicas")
    fin = texto.index("### 7.1", inicio)
    filas: dict[str, tuple[str, str]] = {}
    for linea in texto[inicio:fin].splitlines():
        m = re.match(r"^\|\s*\*\*(.+?)\*\*\s*\|(.+?)\|(.+?)\|", linea)
        if m:
            filas[m.group(1).strip().lower()] = (m.group(2).strip(), m.group(3).strip())
    return filas


# --------------------------------------------------------------------------


def test_el_glosario_declara_las_magnitudes_con_unidad_y_rango() -> None:
    """DAT-01 al pie de la letra: la declaración vive en el glosario."""
    filas = _tabla_del_glosario()
    assert len(filas) >= 11, (
        f"El §7 del glosario declara {len(filas)} magnitudes. La tabla se "
        f"encogió o dejó de leerse."
    )
    for magnitud, (unidad, rango) in filas.items():
        assert unidad, f"«{magnitud}» no declara unidad canónica."
        assert rango, (
            f"«{magnitud}» no declara rango. Sin rango, dos personas que lean "
            f"el mismo número siguen pudiendo entenderlo distinto: es lo que "
            f"pasa con la severidad, que va de 1 a 25 y no de 1 a 5."
        )


def test_el_catalogo_del_codigo_no_se_separa_del_glosario() -> None:
    """El módulo refleja la tabla. Si divergen, uno de los dos miente.

    Es el agujero que tuvo `check_contraste.py` mientras llevaba su propia
    copia de los colores: medía bien contra un valor que ya no era el vigente.
    """
    filas = _tabla_del_glosario()
    del_codigo = {m.clave for m in CATALOGO.values()}
    # El glosario rotula en castellano con mayúscula; el código usa la clave.
    del_glosario = {k.replace("í", "i").replace("ó", "o") for k in filas}
    assert del_codigo == del_glosario, (
        f"Glosario y catálogo no coinciden.\n"
        f"  solo en el código:   {sorted(del_codigo - del_glosario)}\n"
        f"  solo en el glosario: {sorted(del_glosario - del_codigo)}"
    )
    for clave, (unidad, rango) in (
        (k.replace("í", "i").replace("ó", "o"), v) for k, v in filas.items()
    ):
        assert CATALOGO[clave].unidad == unidad, (
            f"«{clave}»: el glosario dice «{unidad}» y el código "
            f"«{CATALOGO[clave].unidad}»."
        )
        assert CATALOGO[clave].rango == rango, (
            f"«{clave}»: el rango difiere entre glosario y código."
        )


def test_cada_magnitud_dice_por_que_esa_unidad() -> None:
    """Una unidad sin motivo escrito es la que alguien cambia «porque daba igual»."""
    for clave, magnitud in CATALOGO.items():
        assert len(magnitud.porque) > 80, (
            f"«{clave}» no explica por qué esa unidad y no otra. El motivo es "
            f"lo que impide que el siguiente la cambie sin darse cuenta de que "
            f"cambia el significado del número."
        )


def test_toda_columna_numerica_cae_en_una_magnitud() -> None:
    """Lo que convierte la declaración en vigente y no en una foto.

    Deriva los campos del árbol: una lista escrita a mano no puede probar «están
    todos», prueba «están los que recordé listar». Si mañana entra un campo
    numérico sin unidad, esta prueba lo nombra.
    """
    hallados = campos_numericos()
    assert len(hallados) >= 50, (
        f"El barrido encontró {len(hallados)} campos numéricos. Dejó de "
        f"encontrarlos y estaría pasando por no mirar."
    )

    sin_clasificar = [
        campo
        for campo, por_sufijo in hallados.items()
        if not por_sufijo and campo not in POR_NOMBRE
    ]
    assert not sin_clasificar, (
        "Estos campos numéricos no tienen magnitud declarada:\n  "
        + "\n  ".join(sorted(sin_clasificar))
        + "\n\nDAT-01 pide unidad canónica para cada magnitud del dominio. "
        "Añádelo a `POR_NOMBRE` con su magnitud, o dale un nombre que la diga "
        "(`_pct`, `_days`, `_ms`, `_bytes`)."
    )

    desconocidas = {
        m for m in POR_NOMBRE.values() if m not in CATALOGO
    } | {m for m in hallados.values() if m and m not in CATALOGO}
    assert not desconocidas, (
        f"Magnitudes citadas que el catálogo no declara: {sorted(desconocidas)}"
    )


def test_la_clasificacion_no_arrastra_campos_que_ya_no_existen() -> None:
    """La otra dirección: `POR_NOMBRE` tampoco puede envejecer.

    Una entrada que sobrevive al campo que clasificaba es ruido que hace pasar
    la prueba por motivos falsos, y es como una línea base deja de significar
    nada.
    """
    hallados = set(campos_numericos())
    fantasmas = sorted(set(POR_NOMBRE) - hallados)
    assert not fantasmas, (
        "Estas entradas clasifican campos que ya no están en el modelo:\n  "
        + "\n  ".join(fantasmas)
    )
